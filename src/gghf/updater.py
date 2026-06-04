"""Incremental updater for tracked Hugging Face models."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from gghf.config import Config
from gghf.database import Database
from gghf.hf import HfClient
from gghf.storage import StorageManager

logger = logging.getLogger(__name__)


class Updater:
    """Check tracked models against their latest HF commits and update them."""

    def __init__(
        self,
        config: Optional[Config] = None,
        database: Optional[Database] = None,
        storage_manager: Optional[StorageManager] = None,
    ) -> None:
        self.config = config or Config()
        self.database = database
        self.storage_manager = storage_manager or StorageManager(
            storage_root=self.config.storage_root,
            gguf_root=self.config.gguf_root,
        )
        self._client: HfClient = HfClient()

    # ---- public API ----

    def check_updates(self) -> dict[str, str]:
        """Return a dict of repo_id -> current_commit for all outdated models."""
        if self.database is None:
            return {}

        outdated: dict[str, str] = {}
        for model in self.database.list_models():
            current = self._client.get_current_commit(model["repo_id"])
            stored = model.get("hf_commit") or ""
            if current and current != stored:
                outdated[model["repo_id"]] = current

        return outdated

    def list_outdated(self) -> dict[str, str]:
        """Alias for ``check_updates`` for explicit naming."""
        return self.check_updates()

    def update_model(
        self,
        repo_id: str,
        token: Optional[str] = None,
    ) -> dict[str, str]:
        """Update a single model: re-download if newer commit exists.

        Returns a dict of repo_id -> current_commit for updated models.
        Updates status to ``"needs_conversion"`` and writes the new commit hash.
        """
        current = self._client.get_current_commit(repo_id)
        stored = self.database.get_model(repo_id)

        if stored and stored.get("hf_commit") == current:
            logger.info("%s is already up-to-date", repo_id)
            return {}

        if self.database is None:
            raise RuntimeError("No database connected — cannot update model.")

        self._client.download(
            repo_id=repo_id,
            local_dir=str(self.storage_manager.hf_model_path(repo_id)),
            token=token or self.config.hf_token or None,
        )

        self.database.update_commit(repo_id, current)
        self.database.update_status(repo_id, "needs_conversion")

        logger.info("Updated %s → commit %s (status: needs_conversion)", repo_id, current)
        return {repo_id: current}
