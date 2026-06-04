"""GGUF conversion for Hugging Face models."""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import Optional

from gghf.config import Config
from gghf.database import Database
from gghf.exceptions import InsufficientStorage, ConversionFailed
from gghf.llama_cpp import LlamaCpp
from gghf.storage import StorageManager
from gghf.ui import format_size, prompt_confirm
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

    def check_storage(self, repo_id: str, quantization: str = "q4_0") -> None:
        """Check available disk space before conversion.

        Raises ``InsufficientStorage`` when available space is below
        the estimated GGUF output size, unless the user confirms
        they want to proceed anyway.
        """
        estimated = self.estimate_gguf_size(repo_id)
        if estimated == 0:
            return  # nothing to estimate

        # Determine the quantization factor for sizing
        quant_factors: dict[str, float] = {
            "q2_k": 0.25,
            "q3_k": 0.35,
            "q4_0": 0.50,
            "q4_1": 0.55,
            "q5_0": 0.60,
            "q5_1": 0.65,
            "q8_0": 0.95,
            "f16": 1.0,
        }
        factor = quant_factors.get(quantization, 0.50)
        required = int(estimated * factor)

        # Check available disk space on the GGUF root partition
        try:
            stat = os.statvfs(str(self.config.gguf_root))
            available = stat.f_bavail * stat.f_frsize
        except OSError:
            self.logger.warning("Could not check disk space — proceeding without warning")
            return

        if available >= required:
            return

        self.logger.warning(
            "Low disk space: need %s but only %s available",
            format_size(required),
            format_size(available),
        )
        console_msg = (
            f"Low disk space warning:\n"
            f"  Estimated GGUF size:  {format_size(required)}\n"
            f"  Available disk space: {format_size(available)}\n"
            f"  Continue anyway?"
        )
        if not prompt_confirm(console_msg, default=False):
            raise InsufficientStorage(required=required, available=available)

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

        # Check disk space before converting
        self.check_storage(repo_id, quantization=quantization)

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

        if model_info is None:
            # Not tracked – if there is no GGUF, it would need conversion
            return not self.storage.gguf_current_path(repo_id).exists()

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
