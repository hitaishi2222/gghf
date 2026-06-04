"""Filesystem helpers for storage path resolution, directory creation, and backups."""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import Optional


class StorageManager:
    """Manage storage paths, directory creation, and GGUF backups."""

    def __init__(
        self,
        storage_root: Optional[Path] = None,
        gguf_root: Optional[Path] = None,
    ) -> None:
        self.storage_root = storage_root or Path("/storage")
        self.gguf_root = gguf_root or self.storage_root

    # ---- path helpers ----

    def hf_model_path(self, repo_id: str) -> Path:
        """Resolve the path for a cached HF repository."""
        return self.storage_root / self._safe_repo_id(repo_id)

    def gguf_model_path(self, repo_id: str) -> Path:
        """Resolve the root path for a model's GGUF artifacts."""
        return self.gguf_root / self._safe_repo_id(repo_id)

    def gguf_current_path(self, repo_id: str) -> Path:
        """Resolve the path of the current GGUF file."""
        return self.gguf_model_path(repo_id) / "current.gguf"

    def gguf_backups_dir(self, repo_id: str) -> Path:
        """Resolve the backups directory for a model."""
        return self.gguf_model_path(repo_id) / "backups"

    # ---- directory management ----

    def ensure_directories(self, repo_id: str) -> None:
        """Create all directories needed for a model's HF cache and GGUF output."""
        self.hf_model_path(repo_id).mkdir(parents=True, exist_ok=True)
        self.gguf_model_path(repo_id).mkdir(parents=True, exist_ok=True)
        self.gguf_backups_dir(repo_id).mkdir(parents=True, exist_ok=True)

    # ---- backup ----

    def create_backup(self, repo_id: str) -> Path:
        """Copy current.gguf to backups/ with a timestamp suffix.

        Raises FileNotFoundError if current.gguf does not exist.
        """
        current = self.gguf_current_path(repo_id)
        if not current.exists():
            raise FileNotFoundError(
                f"No GGUF file at {current} — nothing to back up."
            )
        backups = self.gguf_backups_dir(repo_id)
        backups.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_path = backups / f"current_{timestamp}.gguf"
        shutil.copy2(str(current), str(backup_path))
        return backup_path

    # ---- status ----

    def get_model_status(self, repo_id: str) -> dict:
        """Return a summary dict for a model including sizes and existence flags."""
        hf_path = self.hf_model_path(repo_id)
        gguf_path = self.gguf_current_path(repo_id)

        hf_size = self._dir_size(hf_path) if hf_path.is_dir() else 0
        gguf_size = gguf_path.stat().st_size if gguf_path.exists() else 0

        return {
            "repo_id": repo_id,
            "hf_exists": hf_path.is_dir(),
            "gguf_exists": gguf_path.exists(),
            "hf_size": hf_size,
            "gguf_size": gguf_size,
        }

    # ---- private helpers ----

    @staticmethod
    def _safe_repo_id(repo_id: str) -> str:
        """Normalise a repo_id into a safe directory name (org/repo)."""
        return repo_id.replace("/", os.sep)

    @staticmethod
    def _dir_size(path: Path) -> int:
        """Total size of all files under *path* in bytes."""
        total = 0
        for dirpath, _dirnames, filenames in os.walk(path):
            for fname in filenames:
                fp = Path(dirpath) / fname
                if fp.is_file():
                    total += fp.stat().st_size
        return total
