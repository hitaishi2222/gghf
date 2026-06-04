"""SQLite database for tracking Hugging Face models and their state."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Optional


class Database:
    """Manage a SQLite database for tracked models."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            db_path = Path.home() / ".config" / "gghf" / "database.sqlite"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self) -> None:
        """Create tables if they don't exist."""
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tracked_models (
                repo_id      TEXT PRIMARY KEY,
                hf_commit    TEXT,
                status       TEXT NOT NULL DEFAULT 'added',
                added_at     REAL,
                updated_at   REAL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversion_provenance (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id       TEXT NOT NULL,
                hf_commit     TEXT,
                gguf_commit   TEXT,
                quantization  TEXT,
                timestamp     REAL,
                FOREIGN KEY (repo_id) REFERENCES tracked_models(repo_id)
            )
            """
        )
        self.conn.commit()

    # ---- tracked_models helpers ----

    def add_model(
        self,
        repo_id: str,
        hf_commit: str,
        status: str = "added",
    ) -> None:
        """Add a new tracked model."""
        now = time.time()
        self.conn.execute(
            "INSERT OR IGNORE INTO tracked_models (repo_id, hf_commit, status, added_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (repo_id, hf_commit, status, now, now),
        )
        self.conn.commit()

    def get_model(self, repo_id: str) -> Optional[dict]:
        """Return a dict for the given repo_id, or None."""
        row = self.conn.execute(
            "SELECT * FROM tracked_models WHERE repo_id = ?", (repo_id,)
        ).fetchone()
        return dict(row) if row else None

    def update_commit(self, repo_id: str, hf_commit: str) -> None:
        """Update the HF commit hash and the updated_at timestamp."""
        self.conn.execute(
            "UPDATE tracked_models SET hf_commit = ?, updated_at = ? WHERE repo_id = ?",
            (hf_commit, time.time(), repo_id),
        )
        self.conn.commit()

    def update_status(self, repo_id: str, status: str) -> None:
        """Update the status of a tracked model."""
        self.conn.execute(
            "UPDATE tracked_models SET status = ?, updated_at = ? WHERE repo_id = ?",
            (status, time.time(), repo_id),
        )
        self.conn.commit()

    def list_models(self) -> list[dict]:
        """Return all tracked models as a list of dicts."""
        rows = self.conn.execute(
            "SELECT * FROM tracked_models ORDER BY added_at"
        ).fetchall()
        return [dict(r) for r in rows]

    def model_exists(self, repo_id: str) -> bool:
        """Check whether a repo_id is tracked."""
        row = self.conn.execute(
            "SELECT 1 FROM tracked_models WHERE repo_id = ?", (repo_id,)
        ).fetchone()
        return row is not None

    def remove_model(self, repo_id: str) -> None:
        """Remove a tracked model and its provenance records."""
        self.conn.execute(
            "DELETE FROM conversion_provenance WHERE repo_id = ?", (repo_id,)
        )
        self.conn.execute(
            "DELETE FROM tracked_models WHERE repo_id = ?", (repo_id,)
        )
        self.conn.commit()

    # ---- conversion_provenance helpers ----

    def add_provenance(
        self,
        repo_id: str,
        hf_commit: str,
        gguf_commit: str,
        quantization: str,
    ) -> None:
        """Record a GGUF conversion event."""
        self.conn.execute(
            """
            INSERT INTO conversion_provenance
                (repo_id, hf_commit, gguf_commit, quantization, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (repo_id, hf_commit, gguf_commit, quantization, time.time()),
        )
        self.conn.commit()

    def get_conversions(self, repo_id: str) -> list[dict]:
        """Return all provenance records for a repo, newest first."""
        rows = self.conn.execute(
            "SELECT * FROM conversion_provenance WHERE repo_id = ? ORDER BY timestamp DESC",
            (repo_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_status_summary(self) -> list[dict]:
        """Return model list with total disk usage per repo."""
        models = self.list_models()
        return models

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()
