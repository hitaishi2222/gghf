import shutil
import subprocess


def _gghf_cmd():
    """Return the path to the gghf CLI, falling back to python -m."""
    if (path := shutil.which("gghf")):
        return [path]
    return ["python", "-c", "from gghf.cli import app; app(['--help'])"]


def test_help_shows_gghf():
    """Test that gghf --help exits with code 0 and mentions 'gghf' in output."""
    cmd = _gghf_cmd()
    result = subprocess.run(cmd + ["--help"], capture_output=True, text=True)
    assert result.returncode == 0, f"gghf --help exited with code {result.returncode}: {result.stderr}"
    assert "gghf" in result.stdout.lower(), f"'gghf' not found in help output: {result.stdout}"
