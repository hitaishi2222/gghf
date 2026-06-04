"""Packaging and installation verification tests."""

import subprocess
import sys


def test_gghf_version_after_install():
    """Test that gghf --version works after pip install -e ."""
    # Install the package in editable mode
    project_root = str(__import__("pathlib").Path(__file__).resolve().parent.parent)
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", project_root],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"pip install -e . failed: {result.stderr}"

    # Verify the CLI entry point works
    result = subprocess.run(
        ["gghf", "--version"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"gghf --version failed: {result.stderr}"
    assert "0.1.0" in result.stdout, f"Expected version '0.1.0' in output: {result.stdout}"


def test_help_flag_works():
    """Test that gghf --help works after installation."""
    result = subprocess.run(
        ["gghf", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"gghf --help failed: {result.stderr}"
    assert "gghf" in result.stdout.lower()
    assert "add" in result.stdout.lower()
    assert "update" in result.stdout.lower()
    assert "convert" in result.stdout.lower()


def test_subcommands_available():
    """Test that all expected subcommands are registered."""
    result = subprocess.run(
        ["gghf", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    stdout = result.stdout.lower()
    expected = ["add", "update", "convert", "status", "config"]
    for cmd in expected:
        assert cmd in stdout, f"Expected subcommand '{cmd}' not found in help output"
