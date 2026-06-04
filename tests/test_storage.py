from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from gghf.storage import StorageManager


class TestStorageManagerPaths:
    def test_hf_model_path(self, tmp_path: Path):
        sm = StorageManager(storage_root=tmp_path)
        path = sm.hf_model_path("org/repo")
        assert path == tmp_path / "org" / "repo"

    def test_gguf_model_path(self, tmp_path: Path):
        sm = StorageManager(gguf_root=tmp_path)
        path = sm.gguf_model_path("org/repo")
        assert path == tmp_path / "org" / "repo"

    def test_gguf_current_path(self, tmp_path: Path):
        sm = StorageManager(gguf_root=tmp_path)
        path = sm.gguf_current_path("org/repo")
        assert path == tmp_path / "org" / "repo" / "current.gguf"

    def test_gguf_backups_dir(self, tmp_path: Path):
        sm = StorageManager(gguf_root=tmp_path)
        d = sm.gguf_backups_dir("org/repo")
        assert d == tmp_path / "org" / "repo" / "backups"


class TestStorageManagerEnsureDirectories:
    def test_creates_all_dirs(self, tmp_path: Path):
        sm = StorageManager(storage_root=tmp_path, gguf_root=tmp_path / "gguf")
        sm.ensure_directories("org/repo")
        assert (tmp_path / "org" / "repo").is_dir()
        assert (tmp_path / "gguf" / "org" / "repo").is_dir()
        assert (tmp_path / "gguf" / "org" / "repo" / "backups").is_dir()


class TestStorageManagerCreateBackup:
    def test_create_backup(self, tmp_path: Path):
        gguf_root = tmp_path
        sm = StorageManager(gguf_root=gguf_root)
        model_dir = gguf_root / "org" / "repo"
        model_dir.mkdir(parents=True)
        current = model_dir / "current.gguf"
        current.write_text("fake gguf data")

        backup_path = sm.create_backup("org/repo")
        assert backup_path.exists()
        assert "backups" in str(backup_path)
        assert backup_path.read_text() == "fake gguf data"

    def test_backup_has_timestamp_suffix(self, tmp_path: Path):
        gguf_root = tmp_path
        sm = StorageManager(gguf_root=gguf_root)
        model_dir = gguf_root / "org" / "repo"
        model_dir.mkdir(parents=True)
        current = model_dir / "current.gguf"
        current.write_text("data")

        backup_path = sm.create_backup("org/repo")
        # The filename should contain a timestamp pattern (e.g. _20240101_120000)
        fname = backup_path.name
        assert "_" in fname
        assert fname.endswith(".gguf")

    def test_backup_fails_without_current_file(self, tmp_path: Path):
        sm = StorageManager(gguf_root=tmp_path)
        with pytest.raises(FileNotFoundError):
            sm.create_backup("nonexistent/repo")


class TestStorageManagerGetModelStatus:
    def test_returns_info_dict(self, tmp_path: Path):
        sm = StorageManager(storage_root=tmp_path, gguf_root=tmp_path / "gguf")
        # Create some dirs and a dummy file
        hf_dir = tmp_path / "org" / "repo"
        hf_dir.mkdir(parents=True)
        (hf_dir / "config.json").write_text("{}")
        gguf_dir = tmp_path / "gguf" / "org" / "repo"
        gguf_dir.mkdir(parents=True)
        (gguf_dir / "current.gguf").write_text("x" * 1024)

        status = sm.get_model_status("org/repo")
        assert status["repo_id"] == "org/repo"
        assert "hf_size" in status
        assert "gguf_size" in status
        assert status["hf_exists"] is True
        assert status["gguf_exists"] is True

    def test_missing_model_returns_zeros(self, tmp_path: Path):
        sm = StorageManager(storage_root=tmp_path, gguf_root=tmp_path / "gguf")
        status = sm.get_model_status("missing/repo")
        assert status["repo_id"] == "missing/repo"
        assert status["hf_exists"] is False
        assert status["gguf_exists"] is False
