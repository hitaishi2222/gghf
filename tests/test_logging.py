"""Tests for the structured logging module."""
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from gghf.config import Config
from gghf.utils.logging import get_logger


@pytest.fixture()
def config_dir(tmp_path: Path) -> Path:
    """Provide a temporary config dir for logging."""
    d = tmp_path / ".config" / "gghf"
    d.mkdir(parents=True)
    return d


@pytest.fixture()
def logs_dir(config_dir: Path) -> Path:
    return config_dir / "logs"


@pytest.fixture()
def env_patch(monkeypatch, logs_dir: Path, config_dir: Path):
    """Patch environment so gghf uses a temp config dir."""
    monkeypatch.setenv("GGHF_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("GGHF_LOGS_DIR", str(logs_dir))
    return logs_dir


class TestLoggerCreation:
    def test_logger_returns_configured_logger(self, env_patch: Path):
        logger = get_logger("app")
        assert logger is not None
        assert logger.name == "gghf.app"
        assert len(logger.handlers) > 0

    def test_logger_returns_same_instance_on_repeat_calls(self, env_patch: Path):
        l1 = get_logger("app")
        l2 = get_logger("app")
        assert l1 is l2


class TestLogFiles:
    def test_app_log_file_created(self, env_patch: Path):
        logger = get_logger("app")
        logger.info("test message")
        log_file = env_patch / "app.log"
        assert log_file.exists()
        text = log_file.read_text()
        assert "test message" in text

    def test_download_log_file_created(self, env_patch: Path):
        logger = get_logger("download")
        logger.info("download test")
        log_file = env_patch / "download.log"
        assert log_file.exists()
        assert "download test" in log_file.read_text()

    def test_conversion_log_file_created(self, env_patch: Path):
        logger = get_logger("conversion")
        logger.info("conversion test")
        log_file = env_patch / "conversion.log"
        assert log_file.exists()
        assert "conversion test" in log_file.read_text()

    def test_update_log_file_created(self, env_patch: Path):
        logger = get_logger("update")
        logger.info("update test")
        log_file = env_patch / "update.log"
        assert log_file.exists()
        assert "update test" in log_file.read_text()

    def test_unknown_feature_uses_app_log(self, env_patch: Path):
        logger = get_logger("some_feature")
        logger.info("feature test")
        # Unknown feature should default to app.log
        log_file = env_patch / "app.log"
        assert log_file.exists()
        assert "feature test" in log_file.read_text()
