"""Tests for Typer subcommands (Task 12)."""

from __future__ import annotations

import subprocess
import sys

import pytest


def _gghf():
    """Run gghf via python -m subprocess for reliable import."""
    return [
        sys.executable, "-m", "gghf.cli",
    ]


def test_add_help():
    """gghf add --help exits with code 0 and shows options."""
    result = subprocess.run(_gghf() + ["add", "--help"], capture_output=True, text=True)
    assert result.returncode == 0, f"exit code {result.returncode}: {result.stderr}"
    assert "--repo-id" in result.stdout


def test_status_shows_table():
    """gghf status prints a table (even if empty)."""
    result = subprocess.run(_gghf() + ["status"], capture_output=True, text=True)
    assert result.returncode == 0, f"exit code {result.returncode}: {result.stderr}"
    # Either prints a table (with "Model Status" title) or warns no models
    assert "Model Status" in result.stdout or "No models tracked" in result.stdout or "—" in result.stdout


def test_config_show():
    """gghf config show prints config values."""
    result = subprocess.run(_gghf() + ["config", "show"], capture_output=True, text=True)
    assert result.returncode == 0, f"exit code {result.returncode}: {result.stderr}"
    assert "storage_root" in result.stdout.lower() or "/storage" in result.stdout


def test_update_help():
    """gghf update --help exits with code 0."""
    result = subprocess.run(_gghf() + ["update", "--help"], capture_output=True, text=True)
    assert result.returncode == 0, f"exit code {result.returncode}: {result.stderr}"


def test_convert_help():
    """gghf convert --help exits with code 0 and shows options."""
    result = subprocess.run(_gghf() + ["convert", "--help"], capture_output=True, text=True)
    assert result.returncode == 0, f"exit code {result.returncode}: {result.stderr}"
    assert "--repo-id" in result.stdout


def test_add_no_repo_id_shows_help():
    """gghf add with no --repo-id shows usage info."""
    result = subprocess.run(_gghf() + ["add"], capture_output=True, text=True)
    # Typer shows help on missing required args
    assert "Usage" in result.stdout or "Missing option" in result.stdout or "Error" in result.stdout or result.returncode != 0
