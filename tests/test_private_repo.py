"""Tests for private repository support — token masking and config token usage."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gghf.config import Config, mask_token
from gghf.downloader import HfDownloader
from gghf.database import Database
from gghf.storage import StorageManager


# ── Token masking ────────────────────────────────────────────────────────────


class TestMaskToken:
    """Tests for the mask_token utility."""

    def test_mask_token_hides_middle_characters(self):
        """mask_token should keep prefix + last 4 chars, mask the rest."""
        from gghf.config import mask_token

        result = mask_token("hf_sk_abc123def456ghi789")
        assert result == "hf_sk***i789"

    def test_mask_token_empty_string(self):
        """Empty string should stay empty."""
        from gghf.config import mask_token

        assert mask_token("") == ""

    def test_mask_token_short_token(self):
        """Short tokens (≤8 chars) should be fully masked with ***."""
        from gghf.config import mask_token

        assert mask_token("short") == "***"
        assert mask_token("hf_12345") == "***"

    def test_mask_token_returns_none_if_given_none(self):
        """mask_token should return None when passed None."""
        from gghf.config import mask_token

        assert mask_token(None) is None


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def config_with_token(tmp_path: Path) -> Config:
    """Create a Config pre-loaded with an HF token from a TOML file."""
    config_path = tmp_path / "config.toml"
    config_path.write_text('hf_token = "hf_test_private_token_abc"\n')
    return Config(config_path=config_path)


# ── Downloader uses config token ────────────────────────────────────────────


class TestDownloaderConfigToken:
    """Tests that the downloader passes the config token to the HF client."""

    def test_downloader_passes_config_token_to_client(self, config_with_token, tmp_path, monkeypatch):
        """When no explicit token is given, downloader should pass config.hf_token."""
        db_path = tmp_path / "db.sqlite"
        db = Database(db_path)

        downloader = HfDownloader(
            config=config_with_token,
            database=db,
            storage_manager=StorageManager(
                storage_root=tmp_path / "storage",
                gguf_root=tmp_path / "gguf",
            ),
        )

        mock_client = MagicMock()
        monkeypatch.setattr(downloader, "_client", mock_client)

        downloader.download("private-org/private-model")

        call_kwargs = mock_client.download.call_args[1]
        assert call_kwargs["token"] == "hf_test_private_token_abc"

    def test_explicit_token_overrides_config(self, config_with_token, tmp_path, monkeypatch):
        """An explicit token argument should override the config token."""
        db_path = tmp_path / "db.sqlite"
        db = Database(db_path)

        downloader = HfDownloader(
            config=config_with_token,
            database=db,
            storage_manager=StorageManager(
                storage_root=tmp_path / "storage",
                gguf_root=tmp_path / "gguf",
            ),
        )

        mock_client = MagicMock()
        monkeypatch.setattr(downloader, "_client", mock_client)

        downloader.download(
            "private-org/private-model",
            token="explicit_token_xyz",
        )

        call_kwargs = mock_client.download.call_args[1]
        assert call_kwargs["token"] == "explicit_token_xyz"


# ── Token masking in display ─────────────────────────────────────────────────


class TestSettingsMasking:
    """Verify that token display in settings is masked."""

    def test_token_display_is_masked_in_config_settings(
        self, config_with_token, tmp_path
    ):
        """The config should be able to produce a masked token display string."""
        masked = mask_token(config_with_token.hf_token)
        assert "hf_test_private_token_abc" not in masked
        assert masked != config_with_token.hf_token
