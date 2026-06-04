"""Structured logging for gghf.

Feature-specific loggers (download, conversion, update) each get their own
log file under ``~/.config/gghf/logs/``.  Unknown feature names fall back to
``app.log``.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# Environment overrides (matching the convention used by Config).
# Resolved lazily so tests can patch the environment before first use.
def _config_dir() -> Path:
    return Path(os.environ.get("GGHF_CONFIG_DIR", Path.home() / ".config" / "gghf"))


def _logs_dir() -> Path:
    return Path(os.environ.get("GGHF_LOGS_DIR", _config_dir() / "logs"))

# Map feature names to log file names
_FEATURE_LOGS = {
    "app": "app.log",
    "download": "download.log",
    "conversion": "conversion.log",
    "update": "update.log",
}


def _log_filename(feature: str) -> str:
    """Return the log file name for a given feature name."""
    return _FEATURE_LOGS.get(feature, "app.log")


def get_logger(name: str) -> logging.Logger:
    """Get or create a named logger with file + console handlers.

    Parameters
    ----------
    name:
        Feature name.  Known names (app, download, conversion, update) each
        produce their own log file.  Unknown names default to ``app.log``.

    Returns
    -------
    logging.Logger
    """
    logger = logging.getLogger(f"gghf.{name}")
    logger.setLevel(logging.DEBUG)

    # Clear and re-add handlers so they point to the current logs dir.
    # This keeps tests happy (different temp dirs) while still returning
    # the same logger singleton via Python's logging registry.
    logger.handlers.clear()

    # File handler → feature-specific log file
    _logs_dir().mkdir(parents=True, exist_ok=True)
    log_file = _logs_dir() / _log_filename(name)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(fh)

    # Console handler (INFO and above)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(
        "[%(levelname)s] %(message)s",
    ))
    logger.addHandler(ch)

    return logger
