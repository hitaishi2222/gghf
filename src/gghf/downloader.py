"""High-level Hugging Face repository download orchestration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from gghf.config import Config
from gghf.database import Database
from gghf.hf import HfClient
from gghf.storage import StorageManager

logger = logging.getLogger(__name__)


class HfDownloader:
    """Orchestrate downloading HF repos and updating tracking state."""

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

    def download(
        self,
        repo_id: str,
        token: Optional[str] = None,
    ) -> Path:
        """Download a HF model repository.

        1. Ensures storage directories exist.
        2. Downloads the repo via the best available tool.
        3. Records the download in the database (status = "downloaded").

        Returns the path to the downloaded repository.
        """
        local_dir = str(self.storage_manager.hf_model_path(repo_id))
        logger.info("Downloading %s to %s", repo_id, local_dir)

        self.storage_manager.ensure_directories(repo_id)

        resolved = self._client.download(
            repo_id=repo_id,
            local_dir=local_dir,
            token=token or self.config.hf_token or None,
        )

        if self.database is not None:
            self.database.add_model(
                repo_id=repo_id,
                hf_commit="",
                status="downloaded",
            )

        logger.info("Download complete for %s", repo_id)
        return Path(resolved)
