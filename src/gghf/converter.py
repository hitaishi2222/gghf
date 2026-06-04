"""GGUF conversion for Hugging Face models."""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Optional

from gghf.config import Config
from gghf.database import Database
from gghf.llama_cpp import LlamaCpp
from gghf.storage import StorageManager
from gghf.utils.logging import get_logger


class Converter:
    """Convert HF model repositories to GGUF format."""

    def __init__(
        self,
        config: Config,
        db: Database,
        storage: StorageManager,
    ) -> None:
        self.config = config
        self.db = db
        self.storage = storage
        self.llama_cpp = LlamaCpp()
        self.logger = get_logger("conversion")

    # ---- public API ----

    def convert_model(
        self,
        repo_id: str,
        quantization: str = "q4_0",
    ) -> bool:
        """Convert a model repo to GGUF.

        1. Back up existing ``current.gguf`` if present.
        2. Invoke ``llama-quantize`` (or convert.py).
        3. Record provenance in the database.
        4. Update status to ``up_to_date``.

        Returns ``True`` on success, ``False`` on failure.
        """
        if not self.llama_cpp.is_available():
            self.logger.warning("llama.cpp not available — skipping conversion of %s", repo_id)
            return False

        # Ensure directories exist
        self.storage.ensure_directories(repo_id)

        # Back up existing GGUF if present
        current_path = self.storage.gguf_current_path(repo_id)
        if current_path.exists():
            try:
                backup_path = self.storage.create_backup(repo_id)
                self.logger.info("Backed up %s → %s", current_path, backup_path)
            except FileNotFoundError:
                self.logger.warning("Backup failed for %s — proceeding anyway", repo_id)

        # Get current commit
        model_info = self.db.get_model(repo_id)
        hf_commit = model_info["hf_commit"] if model_info else "unknown"

        # Run conversion
        self.logger.info("Converting %s to %s GGUF …", repo_id, quantization)
        exit_code = self.llama_cpp.convert(
            model_path=str(self.storage.hf_model_path(repo_id)),
            output_path=str(current_path),
            quantization=quantization,
        )

        if exit_code != 0:
            self.logger.error("Conversion failed for %s (exit code %d)", repo_id, exit_code)
            self.db.update_status(repo_id, "needs_conversion")
            return False

        # Record provenance
        gguf_commit = self.llama_cpp.get_commit_hash()
        version = self.llama_cpp.get_version()
        self.logger.info(
            "Conversion complete: %s (llama.cpp %s, commit %s)",
            repo_id,
            version,
            gguf_commit,
        )
        self.db.add_provenance(
            repo_id=repo_id,
            hf_commit=hf_commit,
            gguf_commit=gguf_commit,
            quantization=quantization,
        )
        self.db.update_status(repo_id, "up_to_date")
        return True

    def get_conversions(self, repo_id: str) -> list[dict]:
        """Return conversion history for a repo."""
        return self.db.get_conversions(repo_id)

    def needs_conversion(self, repo_id: str) -> bool:
        """Return True if a model needs GGUF conversion."""
        model_info = self.db.get_model(repo_id)
        if not model_info:
            return False

        if model_info["status"] == "needs_conversion":
            return True

        gguf_path = self.storage.gguf_current_path(repo_id)
        if not gguf_path.exists():
            return True

        return False

    def estimate_gguf_size(self, repo_id: str) -> int:
        """Estimate the GGUF output size based on the HF repo size.

        Rough heuristic: GGUF ≈ HF repo size × 0.5 (for q4_0 quantization).
        Returns 0 if the repo doesn't exist.
        """
        status = self.storage.get_model_status(repo_id)
        hf_size = status.get("hf_size", 0)
        # Rough approximation — varies by quantization
        return max(hf_size // 2, 0)
