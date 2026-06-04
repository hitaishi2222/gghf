"""Tests for the Hugging Face repository downloader."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gghf.downloader import HfDownloader, HfClient


class TestHfClient:
    """Tests for the HfClient thin wrapper."""

    def test_detect_hf_cli_available(self):
        """HfClient should detect that 'hf' CLI is available."""
        with patch("shutil.which", return_value="/usr/bin/hf"):
            client = HfClient()
            assert client.cli_available is True

    def test_detect_hf_cli_unavailable(self):
        """HfClient should fall back when 'hf' CLI is not installed."""
        with patch("shutil.which", return_value=None):
            client = HfClient()
            assert client.cli_available is False

    @patch("shutil.which", return_value="/usr/bin/hf")
    def test_download_uses_cli_when_available(self, mock_which, tmp_path):
        """When 'hf' CLI is available, download should invoke it."""
        client = HfClient()
        repo_id = "test-org/test-repo"
        local_dir = tmp_path / "repo"

        with patch.object(client, "_download_with_cli") as mock_cli:
            client.download(repo_id, str(local_dir))
            mock_cli.assert_called_once_with(repo_id, str(local_dir), None)

    @patch("shutil.which", return_value=None)
    @patch("huggingface_hub.snapshot_download")
    def test_download_falls_back_to_hub_api(self, mock_snapshot, _mock_which, tmp_path):
        """When 'hf' CLI is unavailable, use huggingface_hub API."""
        client = HfClient()
        repo_id = "test-org/test-repo"
        local_dir = tmp_path / "repo"

        client.download(repo_id, str(local_dir), token="fake-token")
        mock_snapshot.assert_called_once()
        call_kwargs = mock_snapshot.call_args[1]
        assert call_kwargs["repo_id"] == repo_id
        assert call_kwargs["local_dir"] == str(local_dir)
        assert call_kwargs["token"] == "fake-token"


class TestHfDownloader:
    """Tests for the higher-level HfDownloader."""

    @pytest.fixture
    def config(self, tmp_path):
        """Create a temporary config for testing."""
        from gghf.config import Config

        cfg = Config(config_path=tmp_path / "config.toml")
        cfg._storage_root = tmp_path / "storage"
        return cfg

    def test_download_triggers_download_and_db_update(
        self, config, tmp_path, monkeypatch
    ):
        """HfDownloader.download should download the repo and update the DB."""
        from gghf.database import Database

        db_path = tmp_path / "database.sqlite"
        db = Database(db_path)

        downloader = HfDownloader(config=config, database=db)

        # Mock the client so we don't actually download anything
        mock_client = MagicMock()
        monkeypatch.setattr(downloader, "_client", mock_client)

        downloader.download("test-org/test-model")

        mock_client.download.assert_called_once()
        kwargs = mock_client.download.call_args[1]
        assert kwargs["repo_id"] == "test-org/test-model"
        # Check that DB was updated
        model = db.get_model("test-org/test-model")
        assert model is not None
        assert model["status"] == "downloaded"

    def test_download_fallback_when_client_unavailable(self, config, tmp_path, monkeypatch):
        """If no HfClient is available at all, download should raise."""
        from gghf.database import Database

        db_path = tmp_path / "database.sqlite"
        db = Database(db_path)

        downloader = HfDownloader(config=config, database=db)

        # Mock client detection to fail
        with patch.object(HfClient, "cli_available", False):
            with patch("huggingface_hub.snapshot_download") as mock_snap:
                mock_snap.return_value = str(tmp_path / "repo")
                downloader.download("test-org/test-model")
                mock_snap.assert_called_once()
