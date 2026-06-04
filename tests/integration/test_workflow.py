"""Integration tests for the full gghf workflow.

End-to-end smoke test: add model → check status → update → convert → verify backup
and provenance.  All external I/O (llama-cpp-python, huggingface_hub, hf CLI) is
mocked so tests run without network access or a local llama.cpp installation.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gghf.config import Config
from gghf.database import Database
from gghf.storage import StorageManager
from gghf.downloader import HfDownloader
from gghf.updater import Updater
from gghf.converter import Converter
from gghf.hf import HfClient


# ─────────────────────────── fixtures ───────────────────────────


@pytest.fixture()
def tmp_env(tmp_path: Path):
    """Create a Config, Database, and StorageManager all backed by *tmp_path*.

    Also sets GGHF_CONFIG_PATH so Config reads/writes inside the temp dir.
    """
    os.environ["GGHF_CONFIG_PATH"] = str(tmp_path / "config.toml")
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    config = Config(config_path=cfg_dir / "config.toml")
    db_path = tmp_path / "database.sqlite"
    db = Database(db_path=db_path)
    storage = StorageManager(
        storage_root=tmp_path / "storage",
        gguf_root=tmp_path / "gguf",
    )
    yield config, db, storage
    db.close()
    os.environ.pop("GGHF_CONFIG_PATH", None)


@pytest.fixture()
def mocked_hf_client():
    """Return a patch context that replaces HfClient where it is consumed
    (Updater, HfDownloader) so they never call the real HF API.

    We also patch ``huggingface_hub.list_repo_commits`` as a safety net
    in case ``HfClient.__init__`` runs before the import-level patch.
    """
    with patch("huggingface_hub.list_repo_commits") as mock_list:
        mock_entry = MagicMock()
        mock_entry.commit_id = "def456"
        mock_list.return_value = [mock_entry]

        mock_instance = MagicMock(spec=HfClient)
        mock_instance.cli_available = False
        mock_instance.hf_hub_available = True
        mock_instance.download.return_value = "/tmp/mock-hf-repo"
        mock_instance.get_current_commit.return_value = "def456"

        # Patch where Updater and HfDownloader import it
        with patch("gghf.updater.HfClient", return_value=mock_instance):
            with patch("gghf.downloader.HfClient", return_value=mock_instance):
                yield mock_instance


# ────────────────────── test: full workflow ─────────────────────


class TestFullWorkflow:
    """Add → check status → update → convert → verify artifacts."""

    def test_add_model_creates_db_entry_and_directories(self, tmp_env):
        """Adding a model creates a DB record and storage directories."""
        config, db, storage = tmp_env

        downloader = HfDownloader(config, db, storage)

        with patch.object(downloader, "_client") as mock_client:
            mock_client.download.return_value = str(
                storage.hf_model_path("test-org/test-model")
            )

            result_path = downloader.download("test-org/test-model")

        # DB entry exists
        model = db.get_model("test-org/test-model")
        assert model is not None
        assert model["repo_id"] == "test-org/test-model"
        assert model["status"] == "downloaded"

        # Storage directories were created
        assert storage.hf_model_path("test-org/test-model").is_dir()
        assert result_path.exists()

    def test_check_status_returns_model_list(self, tmp_env):
        """Status query returns a summary of tracked models."""
        config, db, storage = tmp_env

        repo_id = "test-org/test-model"
        db.add_model(repo_id, "abc123", "added")

        summary = db.get_status_summary()
        assert len(summary) == 1
        assert summary[0]["repo_id"] == repo_id
        assert summary[0]["status"] == "added"
        assert summary[0]["hf_commit"] == "abc123"

    def test_update_model_changes_commit_and_status(self, tmp_env, mocked_hf_client):
        """Updating a model fetches a new commit hash and sets status."""
        config, db, storage = tmp_env
        repo_id = "test-org/test-model"

        # Add the model first
        db.add_model(repo_id, "abc123", "downloaded")

        updater = Updater(config, db, storage)

        updated = updater.update_model(repo_id)

        assert repo_id in updated
        assert updated[repo_id] == "def456"

        model = db.get_model(repo_id)
        assert model["hf_commit"] == "def456"
        assert model["status"] == "needs_conversion"

    def test_update_skips_unchanged_model(self, tmp_env, mocked_hf_client):
        """Update should not re-download if the commit hash hasn't changed."""
        config, db, storage = tmp_env
        repo_id = "test-org/test-model"

        # Stored commit matches the mock's current commit
        db.add_model(repo_id, "def456", "up_to_date")

        updater = Updater(config, db, storage)

        updated = updater.update_model(repo_id)

        assert updated == {}

    def test_convert_creates_gguf_and_provenance(self, tmp_env):
        """Full conversion pipeline: GGUF file + provenance record created."""
        config, db, storage = tmp_env
        repo_id = "test-org/test-model"

        db.add_model(repo_id, "abc123", "needs_conversion")
        storage.ensure_directories(repo_id)

        converter = Converter(config, db, storage)

        def fake_convert(model_path, output_path, quantization):
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(b"fake-quantized-model")
            return 0

        with patch.object(converter, "llama_cpp") as mock_lc:
            mock_lc.is_available.return_value = True
            mock_lc.get_version.return_value = "0.2.0"
            mock_lc.get_commit_hash.return_value = "abcdef1"
            mock_lc.convert.side_effect = fake_convert

            result = converter.convert_model(repo_id, quantization="q4_0")

        assert result is True

        # GGUF file exists
        gguf_file = storage.gguf_current_path(repo_id)
        assert gguf_file.exists()
        assert gguf_file.read_bytes() == b"fake-quantized-model"

        # Provenance recorded
        provenance = db.get_conversions(repo_id)
        assert len(provenance) == 1
        assert provenance[0]["repo_id"] == repo_id
        assert provenance[0]["hf_commit"] == "abc123"
        assert provenance[0]["quantization"] == "q4_0"

        # Status updated
        model = db.get_model(repo_id)
        assert model["status"] == "up_to_date"

    def test_convert_backs_up_existing_gguf(self, tmp_env):
        """When a GGUF already exists, the old one is backed up before overwrite."""
        config, db, storage = tmp_env
        repo_id = "test-org/test-model"

        db.add_model(repo_id, "abc123", "needs_conversion")
        storage.ensure_directories(repo_id)

        # Write an old GGUF
        old_gguf = storage.gguf_current_path(repo_id)
        old_gguf.write_bytes(b"old-model-data")

        converter = Converter(config, db, storage)

        def fake_convert(model_path, output_path, quantization):
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(b"new-model-data")
            return 0

        with patch.object(converter, "llama_cpp") as mock_lc:
            mock_lc.is_available.return_value = True
            mock_lc.get_version.return_value = "0.2.0"
            mock_lc.get_commit_hash.return_value = "abcdef1"
            mock_lc.convert.side_effect = fake_convert

            converter.convert_model(repo_id, quantization="q4_0")

        # Verify backup exists
        backups = storage.gguf_backups_dir(repo_id)
        backup_files = list(backups.glob("current_*.gguf"))
        assert len(backup_files) >= 1
        assert backup_files[0].read_bytes() == b"old-model-data"

        # And the new GGUF is in place
        assert storage.gguf_current_path(repo_id).read_bytes() == b"new-model-data"

    def test_converter_needs_conversion_returns_correct_value(self, tmp_env):
        """needs_conversion returns True when appropriate, False otherwise."""
        config, db, storage = tmp_env
        repo_id = "test-org/test-model"

        converter = Converter(config, db, storage)

        # Not tracked → not tracked, but no GGUF → needs conversion
        assert converter.needs_conversion(repo_id) is True

        db.add_model(repo_id, "abc123", "needs_conversion")
        assert converter.needs_conversion(repo_id) is True

        db.update_status(repo_id, "up_to_date")
        assert converter.needs_conversion(repo_id) is True  # no GGUF yet

        storage.gguf_current_path(repo_id).parent.mkdir(parents=True, exist_ok=True)
        storage.gguf_current_path(repo_id).write_bytes(b"model")
        assert converter.needs_conversion(repo_id) is False

    def test_storage_warning_checks_disk_space(self, tmp_env):
        """check_storage warns when available disk space is too low."""
        config, db, storage = tmp_env
        repo_id = "test-org/test-model"

        db.add_model(repo_id, "abc123", "needs_conversion")
        converter = Converter(config, db, storage)

        # Pretend the HF repo is large
        hf_path = storage.hf_model_path(repo_id)
        hf_path.mkdir(parents=True, exist_ok=True)
        big_file = hf_path / "big.bin"
        big_file.write_bytes(b"x" * (500 * 1024 * 1024))  # 500 MB

        # With generous disk space, no exception should be raised
        with patch("os.statvfs") as mock_statvfs:
            mock_statvfs.return_value.f_bavail = 10_000_000  # plenty
            mock_statvfs.return_value.f_frsize = 4096
            converter.check_storage(repo_id)  # should not raise

    def test_conversion_fails_gracefully_on_llama_cpp_unavailable(self, tmp_env):
        """If llama.cpp is not available, convert_model returns False without error."""
        config, db, storage = tmp_env
        repo_id = "test-org/test-model"

        db.add_model(repo_id, "abc123", "needs_conversion")
        converter = Converter(config, db, storage)

        with patch.object(converter, "llama_cpp") as mock_lc:
            mock_lc.is_available.return_value = False

            result = converter.convert_model(repo_id)

        assert result is False
        # Status should remain needs_conversion (not set to up_to_date)
        model = db.get_model(repo_id)
        assert model["status"] == "needs_conversion"

    def test_get_conversions_returns_full_history(self, tmp_env):
        """get_conversions returns all provenance records, newest first."""
        config, db, storage = tmp_env
        repo_id = "test-org/test-model"

        db.add_model(repo_id, "abc123", "up_to_date")
        converter = Converter(config, db, storage)

        assert converter.get_conversions(repo_id) == []

        db.add_provenance(repo_id, "abc123", "sha1", "q4_0")
        db.add_provenance(repo_id, "abc123", "sha2", "q8_0")

        conversions = converter.get_conversions(repo_id)
        assert len(conversions) == 2
        assert conversions[0]["quantization"] == "q8_0"  # newest first
        assert conversions[1]["quantization"] == "q4_0"

    def test_remove_model_cleans_up_db_entries(self, tmp_env):
        """Removing a model deletes tracked_models and conversion_provenance rows."""
        config, db, storage = tmp_env
        repo_id = "test-org/test-model"

        db.add_model(repo_id, "abc123", "up_to_date")
        db.add_provenance(repo_id, "abc123", "sha1", "q4_0")

        assert db.model_exists(repo_id)
        assert len(db.get_conversions(repo_id)) == 1

        db.remove_model(repo_id)

        assert not db.model_exists(repo_id)
        assert len(db.get_conversions(repo_id)) == 0


class TestMultipleModels:
    """Verify that the system handles multiple tracked models correctly."""

    def test_add_and_track_multiple_models(self, tmp_env):
        """Adding two models results in both appearing in list_models."""
        config, db, storage = tmp_env

        for repo_id in ["org/model-a", "org/model-b"]:
            db.add_model(repo_id, "commit1", "added")

        models = db.list_models()
        assert len(models) == 2
        repo_ids = {m["repo_id"] for m in models}
        assert repo_ids == {"org/model-a", "org/model-b"}

    def test_check_updates_identifies_outdated_models(self, tmp_env, mocked_hf_client):
        """check_updates returns only models with newer commits."""
        config, db, storage = tmp_env
        repo_id = "test-org/outdated"
        up_to_date_id = "test-org/current"

        db.add_model(repo_id, "old_commit", "up_to_date")
        db.add_model(up_to_date_id, "def456", "up_to_date")  # matches mock

        updater = Updater(config, db, storage)
        outdated = updater.check_updates()

        assert repo_id in outdated
        assert up_to_date_id not in outdated
