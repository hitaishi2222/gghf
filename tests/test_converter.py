"""Tests for the GGUF Converter."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gghf.converter import Converter
from gghf.config import Config
from gghf.database import Database
from gghf.storage import StorageManager
from gghf.llama_cpp import LlamaCpp


# --- helpers ---

@pytest.fixture()
def tmp_env(tmp_path: Path):
    """Return a temporary Config, Database, and StorageManager backed by tmp_path."""
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


# --- test: conversion with mocked llama.cpp ---

class TestConverterConvert:
    """Converter.convert_model behaviour."""

    def test_convert_model_creates_gguf_and_provenance(self, tmp_env):
        """Convert a model → GGUF, create provenance record."""
        config, db, storage = tmp_env
        repo_id = "test-org/test-model"

        db.add_model(repo_id, "abc123", "needs_conversion")
        storage.ensure_directories(repo_id)

        converter = Converter(config, db, storage)

        def fake_convert(model_path, output_path, quantization):
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(b"fake-llama-quantize-output")
            return 0

        with patch.object(converter, "llama_cpp") as mock_lc:
            mock_lc.is_available.return_value = True
            mock_lc.get_version.return_value = "0.2.0"
            mock_lc.get_commit_hash.return_value = "abcdef1"
            mock_lc.convert.side_effect = fake_convert

            result = converter.convert_model(repo_id, quantization="q4_0")

        assert result is True
        gguf_file = storage.gguf_current_path(repo_id)
        assert gguf_file.exists()

        provenance = db.get_conversions(repo_id)
        assert len(provenance) == 1
        assert provenance[0]["repo_id"] == repo_id
        assert provenance[0]["hf_commit"] == "abc123"
        assert provenance[0]["quantization"] == "q4_0"

    def test_convert_backs_up_existing_gguf(self, tmp_env):
        """Existing current.gguf is backed up before overwrite."""
        config, db, storage = tmp_env
        repo_id = "test-org/test-model"

        db.add_model(repo_id, "abc123", "needs_conversion")
        storage.ensure_directories(repo_id)

        # Create an existing GGUF
        gguf_file = storage.gguf_current_path(repo_id)
        gguf_file.parent.mkdir(parents=True, exist_ok=True)
        gguf_file.write_text("old model")

        converter = Converter(config, db, storage)

        def fake_convert(model_path, output_path, quantization):
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(b"fake-llama-quantize-output")
            return 0

        with patch.object(converter, "llama_cpp") as mock_lc:
            mock_lc.is_available.return_value = True
            mock_lc.get_version.return_value = "0.2.0"
            mock_lc.get_commit_hash.return_value = "abcdef1"
            mock_lc.convert.side_effect = fake_convert

            converter.convert_model(repo_id, quantization="q4_0")

        backups_dir = storage.gguf_backups_dir(repo_id)
        backup_files = list(backups_dir.glob("current_*.gguf"))
        assert len(backup_files) >= 1
        # The backed-up file should contain the old content
        assert backup_files[0].read_text() == "old model"

    def test_convert_returns_false_when_llama_cpp_not_available(self, tmp_env):
        """Should return False when llama.cpp is not available."""
        config, db, storage = tmp_env
        repo_id = "test-org/test-model"
        db.add_model(repo_id, "abc123", "needs_conversion")

        converter = Converter(config, db, storage)

        with patch.object(converter, "llama_cpp") as mock_lc:
            mock_lc.is_available.return_value = False

            result = converter.convert_model(repo_id)

        assert result is False

    def test_convert_returns_false_on_conversion_failure(self, tmp_env):
        """Should return False when the conversion command fails."""
        config, db, storage = tmp_env
        repo_id = "test-org/test-model"
        db.add_model(repo_id, "abc123", "needs_conversion")

        converter = Converter(config, db, storage)

        with patch.object(converter, "llama_cpp") as mock_lc:
            mock_lc.is_available.return_value = True
            mock_lc.convert.return_value = 1

            result = converter.convert_model(repo_id)

        assert result is False

    def test_convert_skips_if_no_provenance_and_gguf_exists(self, tmp_env):
        """Should skip conversion if status is not needs_conversion and GGUF exists."""
        config, db, storage = tmp_env
        repo_id = "test-org/test-model"

        db.add_model(repo_id, "abc123", "up_to_date")
        storage.ensure_directories(repo_id)
        storage.gguf_current_path(repo_id).parent.mkdir(parents=True, exist_ok=True)
        storage.gguf_current_path(repo_id).write_text("existing")

        converter = Converter(config, db, storage)

        # needs_conversion should return False since status is up_to_date and GGUF exists
        assert converter.needs_conversion(repo_id) is False


# --- test: needs_conversion ---

class TestConverterNeedsConversion:
    """Converter.needs_conversion logic."""

    def test_needs_conversion_when_status_is_needs_conversion(self, tmp_env):
        config, db, storage = tmp_env
        repo_id = "test-org/test-model"
        db.add_model(repo_id, "abc123", "needs_conversion")
        converter = Converter(config, db, storage)
        assert converter.needs_conversion(repo_id) is True

    def test_needs_conversion_when_no_gguf_exists(self, tmp_env):
        config, db, storage = tmp_env
        repo_id = "test-org/test-model"
        db.add_model(repo_id, "abc123", "added")
        converter = Converter(config, db, storage)
        assert converter.needs_conversion(repo_id) is True

    def test_does_not_need_conversion_when_up_to_date_and_gguf_exists(self, tmp_env):
        config, db, storage = tmp_env
        repo_id = "test-org/test-model"
        db.add_model(repo_id, "abc123", "up_to_date")
        storage.ensure_directories(repo_id)
        storage.gguf_current_path(repo_id).parent.mkdir(parents=True, exist_ok=True)
        storage.gguf_current_path(repo_id).write_text("model")
        converter = Converter(config, db, storage)
        assert converter.needs_conversion(repo_id) is False


# --- test: get_conversions ---

class TestConverterGetConversions:
    """Converter.get_conversions returns provenance records."""

    def test_returns_provenance_list(self, tmp_env):
        config, db, storage = tmp_env
        repo_id = "test-org/test-model"
        db.add_model(repo_id, "abc123", "up_to_date")

        converter = Converter(config, db, storage)
        conversions = converter.get_conversions(repo_id)
        assert conversions == []

        db.add_provenance(repo_id, "abc123", "def456", "q4_0")
        conversions = converter.get_conversions(repo_id)
        assert len(conversions) == 1
        assert conversions[0]["quantization"] == "q4_0"
