"""Tests for the Hugging Face repository updater."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gghf.database import Database
from gghf.updater import Updater


class TestUpdater:
    """Tests for the Updater class."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a temporary database."""
        return Database(tmp_path / "database.sqlite")

    @pytest.fixture
    def config(self, tmp_path):
        """Create a temporary config."""
        from gghf.config import Config

        cfg = Config(config_path=tmp_path / "config.toml")
        cfg._storage_root = tmp_path / "storage"
        return cfg

    @pytest.fixture
    def updater(self, config, db):
        """Build an Updater with mocked HF client."""
        return Updater(config=config, database=db)

    # ---- check_updates ----

    def test_check_updates_detects_newer_commit(self, updater, db):
        """check_updates should list a model as outdated when HF reports a newer commit."""
        db.add_model("test-org/test-model", hf_commit="old", status="downloaded")

        # Mock the HF client's get_current_commit to return a different hash
        with patch.object(updater._client, "get_current_commit", return_value="new"):
            outdated = updater.check_updates()

        assert "test-org/test-model" in outdated
        assert outdated["test-org/test-model"] == "new"

    def test_check_updates_skips_up_to_date(self, updater, db):
        """Models already at the latest commit should not appear in the result."""
        db.add_model("test-org/test-model", hf_commit="same", status="downloaded")

        with patch.object(updater._client, "get_current_commit", return_value="same"):
            outdated = updater.check_updates()

        assert outdated == {}

    # ---- update_model ----

    def test_update_model_changes_status_to_needs_conversion(self, updater, db):
        """After updating a model, its status should become 'needs_conversion'."""
        db.add_model("test-org/test-model", hf_commit="old", status="downloaded")

        with patch.object(updater._client, "get_current_commit", return_value="newer"):
            with patch.object(updater._client, "download"):
                outdated = updater.update_model("test-org/test-model")

        assert "test-org/test-model" in outdated
        model = db.get_model("test-org/test-model")
        assert model["status"] == "needs_conversion"
        assert model["hf_commit"] == "newer"

    def test_update_model_skips_already_current(self, updater, db):
        """Models already up-to-date should be skipped."""
        db.add_model("test-org/test-model", hf_commit="same", status="downloaded")

        with patch.object(updater._client, "get_current_commit", return_value="same"):
            outdated = updater.update_model("test-org/test-model")

        assert outdated == {}

    # ---- list_outdated ----

    def test_list_outdated_returns_all_outdated_models(self, updater, db):
        """list_outdated should return all models with a newer commit."""
        db.add_model("model/a", hf_commit="old1", status="downloaded")
        db.add_model("model/b", hf_commit="old2", status="downloaded")
        db.add_model("model/c", hf_commit="latest", status="downloaded")

        def fake_commit(repo_id):
            if repo_id == "model/c":
                return "latest"
            return "new_" + repo_id

        with patch.object(updater._client, "get_current_commit", side_effect=fake_commit):
            outdated = updater.list_outdated()

        assert set(outdated) == {"model/a", "model/b"}
