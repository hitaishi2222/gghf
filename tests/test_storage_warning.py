"""Tests for storage warning — disk-space checks before GGUF conversion."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from gghf.config import Config
from gghf.converter import Converter
from gghf.database import Database
from gghf.storage import StorageManager
from gghf.exceptions import InsufficientStorage, ConversionFailed


# ── Custom exceptions ──────────────────────────────────────────────────────


class TestCustomExceptions:
    """Verify custom exception classes exist and behave correctly."""

    def test_insufficient_storage_inherits_from_runtime_error(self):
        """InsufficientStorage should be a RuntimeError subclass."""
        assert issubclass(InsufficientStorage, RuntimeError)

    def test_conversion_failed_inherits_from_runtime_error(self):
        """ConversionFailed should be a RuntimeError subclass."""
        assert issubclass(ConversionFailed, RuntimeError)

    def test_insufficient_storage_has_message(self):
        """InsufficientStorage should carry a descriptive message."""
        # Use binary-friendly values so format_size rounds to clean numbers.
        # 5 GiB = 5 * 1024**3 bytes, 1 GiB = 1 * 1024**3 bytes
        exc = InsufficientStorage(
            required=5 * 1024**3,
            available=1 * 1024**3,
        )
        assert "5.0 GiB" in str(exc)
        assert "1.0 GiB" in str(exc)

    def test_conversion_failed_has_message(self):
        """ConversionFailed should carry a descriptive message."""
        exc = ConversionFailed("model_name", exit_code=1)
        assert "model_name" in str(exc)
        assert "exit code 1" in str(exc)


# ── Helpers ────────────────────────────────────────────────────────────────


def _make_converter(tmp_path: str) -> Converter:
    """Build a Converter with temp dirs for testing."""
    config = Config()
    db = Database(tmp_path / "test_db.sqlite")
    storage = StorageManager(
        storage_root=tmp_path / "storage",
        gguf_root=tmp_path / "gguf",
    )
    return Converter(config=config, db=db, storage=storage)


# ── Storage check ──────────────────────────────────────────────────────────


class TestStorageCheck:
    """Tests for the storage-check logic before conversion."""

    def test_check_storage_passes_when_enough_space(
        self, tmp_path, monkeypatch
    ):
        """When available space exceeds estimate, no exception is raised."""
        converter = _make_converter(tmp_path)

        # Make available space huge so the check passes
        monkeypatch.setattr("gghf.storage.os.statvfs", lambda _: MagicMock(f_bavail=999999))

        converter.check_storage("some-repo", quantization="q4_0")
        # Should complete without raising

    def test_check_storage_raises_when_insufficient_space(
        self, tmp_path, monkeypatch
    ):
        """When available space is below estimate, InsufficientStorage is raised."""
        converter = _make_converter(tmp_path)

        # Create HF model files so estimate_gguf_size returns non-zero
        hf_dir = converter.storage.hf_model_path("some-repo")
        hf_dir.mkdir(parents=True, exist_ok=True)
        (hf_dir / "model.bin").write_bytes(b"x" * 100_000_000)  # 100 MB

        # Make available space tiny (~10 bytes)
        fake_stat = MagicMock(f_bavail=10, f_frsize=4096)
        monkeypatch.setattr("gghf.converter.os.statvfs", lambda _: fake_stat)

        # Mock prompt_confirm to return False (user declines)
        with patch("gghf.converter.prompt_confirm", return_value=False):
            with pytest.raises(InsufficientStorage):
                converter.check_storage("some-repo", quantization="q4_0")

    def test_check_storage_accepts_user_confirmation(
        self, tmp_path, monkeypatch
    ):
        """When user confirms despite insufficient space, conversion is allowed."""
        converter = _make_converter(tmp_path)

        fake_stat = MagicMock(f_bavail=10)
        monkeypatch.setattr("gghf.converter.os.statvfs", lambda _: fake_stat)

        # Monkey-patch prompt_confirm to return True
        with patch("gghf.converter.prompt_confirm", return_value=True):
            # Should not raise even with insufficient space
            converter.check_storage("some-repo", quantization="q4_0")

    def test_check_storage_blocks_without_confirmation(
        self, tmp_path, monkeypatch
    ):
        """When user declines, InsufficientStorage is raised even if asked."""
        converter = _make_converter(tmp_path)

        # Create HF model files so estimate_gguf_size returns non-zero
        hf_dir = converter.storage.hf_model_path("some-repo")
        hf_dir.mkdir(parents=True, exist_ok=True)
        (hf_dir / "model.bin").write_bytes(b"x" * 100_000_000)  # 100 MB

        fake_stat = MagicMock(f_bavail=10, f_frsize=4096)
        monkeypatch.setattr("gghf.converter.os.statvfs", lambda _: fake_stat)

        with patch("gghf.converter.prompt_confirm", return_value=False):
            with pytest.raises(InsufficientStorage):
                converter.check_storage("some-repo", quantization="q4_0")

    def test_estimate_gguf_size_returns_zero_for_missing_repo(
        self, tmp_path
    ):
        """When repo doesn't exist, estimate returns 0."""
        converter = _make_converter(tmp_path)
        result = converter.estimate_gguf_size("nonexistent/repo")
        assert result == 0

    def test_estimate_gguf_size_proportional_to_hf_size(self, tmp_path):
        """Estimate is roughly half the HF repo size (q4_0 factor)."""
        converter = _make_converter(tmp_path)
        status = converter.storage.get_model_status("existing/repo")
        # Create a fake HF dir with known size
        hf_path = converter.storage.hf_model_path("existing/repo")
        hf_path.mkdir(parents=True, exist_ok=True)
        test_file = hf_path / "dummy.bin"
        test_file.write_bytes(b"x" * 1_000_000)  # 1 MiB
        estimated = converter.estimate_gguf_size("existing/repo")
        assert estimated > 0
        # Roughly half of HF size (1 MiB / 2 = ~500 KiB)
        assert 400_000 <= estimated <= 600_000


# ── Converter integration ─────────────────────────────────────────────────


class TestConverterStorageWarning:
    """Verify convert_model calls check_storage before converting."""

    def test_check_storage_called_before_conversion(
        self, tmp_path, monkeypatch
    ):
        """check_storage should be invoked inside convert_model."""
        converter = _make_converter(tmp_path)

        # Mock llama_cpp so conversion succeeds
        mock_llama = MagicMock()
        mock_llama.is_available.return_value = True
        mock_llama.convert.return_value = 0
        mock_llama.get_version.return_value = "0.2.0"
        mock_llama.get_commit_hash.return_value = "abc123"
        converter.llama_cpp = mock_llama

        # Make sure estimate_gguf_size returns a plausible number
        monkeypatch.setattr(
            converter.storage, "get_model_status",
            lambda repo_id: {"hf_size": 1_000_000_000},
        )

        converter.db.add_model("test/model", "abcdef123456", "needs_conversion")

        with patch("gghf.converter.prompt_confirm", return_value=True):
            result = converter.convert_model("test/model")

        # check_storage should have been called (no exception raised)
        assert result is True
