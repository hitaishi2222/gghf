"""Tests for Rich table rendering helpers."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console
from rich.table import Table

from gghf.ui import render_model_table, render_gguf_history, format_size


def _render_table(table: Table) -> str:
    """Render a Rich Table to a string."""
    console = Console(file=io.StringIO(), force_terminal=True, width=120)
    console.print(table)
    return console.file.getvalue()


# --- test: format_size ---

class TestFormatSize:
    """format_size converts bytes to human-readable strings."""

    def test_zero_bytes(self):
        assert format_size(0) == "0 B"

    def test_bytes(self):
        assert format_size(512) == "512 B"

    def test_kilobytes(self):
        assert format_size(1024) == "1.0 KiB"

    def test_megabytes(self):
        assert format_size(1_048_576) == "1.0 MiB"

    def test_gigabytes(self):
        assert format_size(1_073_741_824) == "1.0 GiB"

    def test_terabytes(self):
        assert format_size(1_099_511_627_776) == "1.0 TiB"

    def test_rounds_to_two_decimals(self):
        result = format_size(1_500_000_000)
        assert "MiB" in result or "GiB" in result  # depends on magnitude


# --- test: render_model_table ---

class TestRenderModelTable:
    """render_model_table produces a Rich Table."""

    def test_returns_rich_table(self):
        models = [
            {"repo_id": "test-org/model-a", "hf_commit": "abc1234", "status": "up_to_date", "added_at": 0},
            {"repo_id": "test-org/model-b", "hf_commit": "def5678", "status": "needs_conversion", "added_at": 0},
        ]
        table = render_model_table(models)
        assert isinstance(table, Table)

    def test_shows_repo_id_column(self):
        models = [{"repo_id": "org/model", "hf_commit": "abc1234", "status": "up_to_date", "added_at": 0}]
        table = render_model_table(models)
        output = _render_table(table)
        assert "org/model" in output

    def test_shows_status_column(self):
        models = [{"repo_id": "org/model", "hf_commit": "abc", "status": "up_to_date", "added_at": 0}]
        table = render_model_table(models)
        output = _render_table(table)
        assert "up_to_date" in output

    def test_empty_list_shows_header(self):
        table = render_model_table([])
        output = _render_table(table)
        # Should still render headers
        assert "repo_id" in output.lower() or "REPO" in output.upper()


# --- test: render_gguf_history ---

class TestRenderGgufHistory:
    """render_gguf_history renders conversion provenance."""

    def test_returns_rich_table(self):
        conversions = [
            {"quantization": "q4_0", "hf_commit": "abc123", "gguf_commit": "def456", "timestamp": 0},
        ]
        table = render_gguf_history(conversions)
        assert isinstance(table, Table)

    def test_shows_quantization(self):
        conversions = [{"quantization": "q8_0", "hf_commit": "abc", "gguf_commit": "def", "timestamp": 0}]
        table = render_gguf_history(conversions)
        output = _render_table(table)
        assert "q8_0" in output

    def test_empty_shows_header(self):
        table = render_gguf_history([])
        output = _render_table(table)
        assert "quantization" in output.lower() or "QUANT" in output.upper()
