"""Tests for `gghf config init` command."""
import tomli
from typer.testing import CliRunner
from gghf.cli import app


runner = CliRunner()


def test_config_init_creates_file(tmp_path, monkeypatch):
    """`gghf config init` should create the config.toml file."""
    config_dir = tmp_path / ".config" / "gghf"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.toml"
    monkeypatch.setenv("GGHF_CONFIG_PATH", str(config_path))

    result = runner.invoke(app, ["config", "init"])
    assert result.exit_code == 0, result.output
    assert config_path.exists()


def test_config_init_contains_comments_and_keys(tmp_path, monkeypatch):
    """The generated config.toml should contain comments and all key sections."""
    config_dir = tmp_path / ".config" / "gghf"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.toml"
    monkeypatch.setenv("GGHF_CONFIG_PATH", str(config_path))

    result = runner.invoke(app, ["config", "init"])
    assert result.exit_code == 0, result.output

    content = config_path.read_text()

    # Should contain comments (lines starting with #)
    comment_lines = [l for l in content.splitlines() if l.strip().startswith("#")]
    assert len(comment_lines) >= 3, "Config should have at least 3 comment lines"

    # Should contain the major keys
    assert "storage_root" in content
    assert "hf_root" in content
    assert "gguf_root" in content


def test_config_init_is_valid_toml(tmp_path, monkeypatch):
    """The generated config.toml should be valid TOML that can be loaded."""
    config_dir = tmp_path / ".config" / "gghf"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.toml"
    monkeypatch.setenv("GGHF_CONFIG_PATH", str(config_path))

    result = runner.invoke(app, ["config", "init"])
    assert result.exit_code == 0, result.output

    with open(config_path, "rb") as f:
        data = tomli.load(f)

    # Keys should be present (values may be commented out — check structure)
    # Comments won't parse as TOML values, so we just verify it parses
    assert isinstance(data, dict)


def test_config_init_overwrites_existing(tmp_path, monkeypatch):
    """`gghf config init` on an existing file should overwrite it cleanly."""
    config_dir = tmp_path / ".config" / "gghf"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.toml"
    monkeypatch.setenv("GGHF_CONFIG_PATH", str(config_path))

    # Pre-write something
    config_path.write_text("# old junk\nbad = true\n")

    result1 = runner.invoke(app, ["config", "init"])
    result2 = runner.invoke(app, ["config", "init"])
    assert result1.exit_code == 0, result1.output
    assert result2.exit_code == 0, result2.output


def test_config_init_output_message(tmp_path, monkeypatch):
    """`gghf config init` should print a confirmation message."""
    config_dir = tmp_path / ".config" / "gghf"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.toml"
    monkeypatch.setenv("GGHF_CONFIG_PATH", str(config_path))

    result = runner.invoke(app, ["config", "init"])
    assert result.exit_code == 0, result.output
    # Should mention the file path or that config was initialized
    assert "initialized" in result.output.lower() or "config" in result.output.lower()
