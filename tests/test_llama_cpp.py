"""Tests for llama.cpp detection and version retrieval."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from gghf.llama_cpp import LlamaCpp


class TestLlamaCpp:
    """Tests for the LlamaCpp class."""

    def test_is_available_when_binary_found(self):
        """LlamaCpp.is_available should return True when the binary exists."""
        with patch("shutil.which", return_value="/usr/bin/llama-quantize"):
            lc = LlamaCpp()
            assert lc.is_available() is True

    def test_is_unavailable_when_binary_missing(self):
        """LlamaCpp.is_available should return False when the binary is missing."""
        with patch("shutil.which", return_value=None):
            lc = LlamaCpp()
            assert lc.is_available() is False

    def test_get_version(self):
        """LlamaCpp.get_version should parse the version string."""
        with patch("shutil.which", return_value="/usr/bin/llama-quantize"):
            with patch(
                "subprocess.run",
                return_value=type(
                    "Popen",
                    (),
                    {
                        "stdout": "llama-quantize version 0.8.0 (abc123)\n",
                        "returncode": 0,
                    },
                )(),
            ):
                lc = LlamaCpp()
                version = lc.get_version()
                assert "0.8.0" in version

    def test_get_commit_hash(self):
        """LlamaCpp.get_commit_hash should return a short hash string."""
        with patch("shutil.which", return_value="/usr/bin/llama-quantize"):
            with patch(
                "subprocess.run",
                return_value=type(
                    "Popen",
                    (),
                    {"stdout": "abc123def\n", "returncode": 0},
                )(),
            ):
                lc = LlamaCpp()
                commit = lc.get_commit_hash()
                assert len(commit) == 7  # short hash

    def test_get_version_fallback_to_convert_py(self):
        """Should fall back to convert.py when llama-quantize is not found."""
        with patch("shutil.which", side_effect=["", "/usr/bin/convert.py"]):
            with patch(
                "subprocess.run",
                return_value=type(
                    "Popen", (), {"stdout": "version 1.0.0\n", "returncode": 0}
                )(),
            ):
                lc = LlamaCpp()
                version = lc.get_version()
                assert "1.0.0" in version

    def test_get_version_returns_empty_when_unavailable(self):
        """Should return empty string when no tool is available."""
        with patch("shutil.which", return_value=None):
            lc = LlamaCpp()
            assert lc.get_version() == ""

    def test_get_commit_hash_returns_empty_when_unavailable(self):
        """Should return empty string when no tool is available."""
        with patch("shutil.which", return_value=None):
            lc = LlamaCpp()
            assert lc.get_commit_hash() == ""
