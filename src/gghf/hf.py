"""Thin wrapper for Hugging Face CLI and API tools."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Optional


class HfClient:
    """Detect available HF tools and expose download methods.

    Prefers the ``hf`` CLI when installed; falls back to
    ``huggingface_hub.snapshot_download`` otherwise.
    """

    def __init__(self) -> None:
        self._hf_bin: Optional[str] = shutil.which("hf")
        self._hf_hub_available: bool = self._check_hf_hub()

    @property
    def cli_available(self) -> bool:
        """Whether the ``hf`` CLI is installed."""
        return self._hf_bin is not None

    @property
    def hf_hub_available(self) -> bool:
        """Whether ``huggingface_hub`` is importable."""
        return self._hf_hub_available

    def get_current_commit(self, repo_id: str) -> str:
        """Return the current commit hash for *repo_id* on the ``main`` branch."""
        if self.hf_hub_available:
            from huggingface_hub import list_repo_commits

            commits = list(list_repo_commits(repo_id, limit=1))
            if commits:
                return commits[0].commit_id

        # Fallback: try the hf CLI
        if self.cli_available:
            import os

            env = dict(os.environ)
            result = subprocess.run(
                [self._hf_bin, "model", "info", repo_id, "--json"],
                capture_output=True,
                text=True,
                env=env,
            )
            if result.returncode == 0:
                import json

                data = json.loads(result.stdout)
                # The hf CLI model-info JSON may vary; best-effort parse.
                return data.get("sha", "")

        return ""

    def download(
        self,
        repo_id: str,
        local_dir: str,
        token: Optional[str] = None,
    ) -> Path:
        """Download a HF repository to *local_dir*.

        Returns the resolved local directory path.
        """
        if self.cli_available:
            return self._download_with_cli(repo_id, local_dir, token)
        if self.hf_hub_available:
            return self._download_with_hub_api(repo_id, local_dir, token)
        raise RuntimeError(
            "No Hugging Face download tool available. "
            "Install the ``hf`` CLI or the ``huggingface_hub`` Python package."
        )

    # ---- private helpers ----

    def _download_with_cli(
        self,
        repo_id: str,
        local_dir: str,
        token: Optional[str],
    ) -> Path:
        """Download using the ``hf`` CLI."""
        cmd = [self._hf_bin, "repo", "download", repo_id, local_dir]
        if token:
            env = dict(__import__("os").environ)
            env["HF_TOKEN"] = token
            result = subprocess.run(cmd, env=env, check=True)
        else:
            result = subprocess.run(cmd, check=True)
        return Path(local_dir)

    def _download_with_hub_api(
        self,
        repo_id: str,
        local_dir: str,
        token: Optional[str],
    ) -> Path:
        """Download using the ``huggingface_hub`` Python API."""
        from huggingface_hub import snapshot_download

        return Path(
            snapshot_download(
                repo_id=repo_id,
                local_dir=local_dir,
                token=token,
            )
        )

    @staticmethod
    def _check_hf_hub() -> bool:
        """Return True if ``huggingface_hub`` can be imported."""
        try:
            import huggingface_hub  # noqa: F401

            return True
        except ImportError:
            return False
