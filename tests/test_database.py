import tempfile
from pathlib import Path

from gghf.database import Database


class TestDatabaseCreate:
    def test_create_database(self, tmp_path: Path):
        db_path = tmp_path / "database.sqlite"
        db = Database(db_path=db_path)
        assert db_path.exists()

    def test_table_exists(self, tmp_path: Path):
        db_path = tmp_path / "database.sqlite"
        db = Database(db_path=db_path)
        cursor = db.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tracked_models'"
        )
        assert cursor.fetchone() is not None


class TestDatabaseAddModel:
    def test_add_model(self, tmp_path: Path):
        db = Database(db_path=tmp_path / "db.sqlite")
        db.add_model("test/repo", "abc123", "added")
        row = db.get_model("test/repo")
        assert row is not None
        assert row["repo_id"] == "test/repo"
        assert row["hf_commit"] == "abc123"
        assert row["status"] == "added"

    def test_add_model_sets_timestamps(self, tmp_path: Path):
        db = Database(db_path=tmp_path / "db.sqlite")
        db.add_model("test/repo", "abc123", "added")
        row = db.get_model("test/repo")
        assert row["added_at"] is not None
        assert row["updated_at"] is not None


class TestDatabaseModelExists:
    def test_model_exists_true(self, tmp_path: Path):
        db = Database(db_path=tmp_path / "db.sqlite")
        db.add_model("test/repo", "abc123", "added")
        assert db.model_exists("test/repo") is True

    def test_model_exists_false(self, tmp_path: Path):
        db = Database(db_path=tmp_path / "db.sqlite")
        assert db.model_exists("nonexistent") is False


class TestDatabaseUpdateCommit:
    def test_update_commit(self, tmp_path: Path):
        db = Database(db_path=tmp_path / "db.sqlite")
        db.add_model("test/repo", "abc123", "added")
        db.update_commit("test/repo", "def456")
        row = db.get_model("test/repo")
        assert row["hf_commit"] == "def456"

    def test_update_commit_updated_at_changes(self, tmp_path: Path):
        import time

        db = Database(db_path=tmp_path / "db.sqlite")
        db.add_model("test/repo", "abc123", "added")
        old_updated = db.get_model("test/repo")["updated_at"]
        time.sleep(0.05)
        db.update_commit("test/repo", "def456")
        new_updated = db.get_model("test/repo")["updated_at"]
        assert new_updated > old_updated


class TestDatabaseListModels:
    def test_list_models_empty(self, tmp_path: Path):
        db = Database(db_path=tmp_path / "db.sqlite")
        assert db.list_models() == []

    def test_list_models_multiple(self, tmp_path: Path):
        db = Database(db_path=tmp_path / "db.sqlite")
        db.add_model("org/model-a", "aaa", "added")
        db.add_model("org/model-b", "bbb", "needs_conversion")
        models = db.list_models()
        assert len(models) == 2
        repo_ids = {m["repo_id"] for m in models}
        assert "org/model-a" in repo_ids
        assert "org/model-b" in repo_ids


class TestDatabaseRemoveModel:
    def test_remove_model(self, tmp_path: Path):
        db = Database(db_path=tmp_path / "db.sqlite")
        db.add_model("test/repo", "abc123", "added")
        db.remove_model("test/repo")
        assert db.get_model("test/repo") is None
        assert db.list_models() == []
