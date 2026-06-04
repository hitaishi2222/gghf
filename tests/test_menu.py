"""Tests for the interactive menu loop (Task 11)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from gghf.menu import (
    _action_add_model,
    _action_convert_model,
    _action_download_updates,
    _action_manage_gguf,
    _action_settings,
    _action_status,
    _do_convert,
    run_menu,
)


# ── run_menu ───────────────────────────────────────────────────────────────


class TestRunMenu:
    """The menu loop dispatches to the correct action handlers."""

    def _mock_env(self):
        """Return (config, db, storage) mock objects."""
        config = MagicMock()
        config.storage_root = MagicMock()
        config.hf_root = MagicMock()
        config.gguf_root = MagicMock()
        config.hf_token = None
        config.config_dir = MagicMock()
        config.config_dir.__truediv__ = lambda self, other: MagicMock()

        db = MagicMock()
        db.list_models.return_value = []
        db.model_exists.return_value = False
        db.add_model = MagicMock()

        storage = MagicMock()
        storage.hf_model_path.return_value = MagicMock()
        storage.gguf_root = MagicMock()
        storage.storage_root = MagicMock()

        return config, db, storage

    @patch("builtins.input")
    @patch("gghf.menu.prompt_select")
    def test_exits_on_exit_choice(self, mock_select, mock_input):
        mock_select.return_value = "Exit"
        config, db, storage = self._mock_env()
        run_menu(config=config, db=db, storage=storage)
        # Should break out of loop — exits without error
        db.close.assert_called()

    @patch("builtins.input")
    @patch("gghf.menu.prompt_select")
    def test_calls_add_model(self, mock_select, mock_input):
        mock_select.side_effect = ["Add Model", "Exit"]
        config, db, storage = self._mock_env()
        with patch("gghf.menu._action_add_model") as m:
            run_menu(config=config, db=db, storage=storage)
            m.assert_called_once_with(config, db, storage)

    @patch("builtins.input")
    @patch("gghf.menu.prompt_select")
    def test_calls_download_updates(self, mock_select, mock_input):
        mock_select.side_effect = ["Download Updates", "Exit"]
        config, db, storage = self._mock_env()
        with patch("gghf.menu._action_download_updates") as m:
            run_menu(config=config, db=db, storage=storage)
            m.assert_called_once_with(config, db, storage)

    @patch("builtins.input")
    @patch("gghf.menu.prompt_select")
    def test_calls_convert_model(self, mock_select, mock_input):
        mock_select.side_effect = ["Convert Model", "Exit"]
        config, db, storage = self._mock_env()
        with patch("gghf.menu._action_convert_model") as m:
            run_menu(config=config, db=db, storage=storage)
            m.assert_called_once_with(config, db, storage)

    @patch("builtins.input")
    @patch("gghf.menu.prompt_select")
    def test_calls_manage_gguf(self, mock_select, mock_input):
        mock_select.side_effect = ["Manage GGUFs", "Exit"]
        config, db, storage = self._mock_env()
        with patch("gghf.menu._action_manage_gguf") as m:
            run_menu(config=config, db=db, storage=storage)
            m.assert_called_once_with(config, db, storage)

    @patch("builtins.input")
    @patch("gghf.menu.prompt_select")
    def test_calls_status(self, mock_select, mock_input):
        mock_select.side_effect = ["Model Status", "Exit"]
        config, db, storage = self._mock_env()
        with patch("gghf.menu._action_status") as m:
            run_menu(config=config, db=db, storage=storage)
            m.assert_called_once_with(config, db, storage)

    @patch("builtins.input")
    @patch("gghf.menu.prompt_select")
    def test_calls_settings(self, mock_select, mock_input):
        mock_select.side_effect = ["Settings", "Exit"]
        config, db, storage = self._mock_env()
        with patch("gghf.menu._action_settings") as m:
            run_menu(config=config, db=db, storage=storage)
            m.assert_called_once_with(config)


# ── _action_add_model ─────────────────────────────────────────────────────


class TestActionAddModel:
    def test_no_repo_id_cancels(self):
        config, db, storage = MagicMock(), MagicMock(), MagicMock()
        with patch("gghf.menu.prompt_input", return_value=""):
            _action_add_model(config, db, storage)
        db.add_model.assert_not_called()

    def test_already_tracked(self):
        config, db, storage = MagicMock(), MagicMock(), MagicMock()
        db.model_exists.return_value = True
        with patch("gghf.menu.prompt_input", return_value="org/model"):
            _action_add_model(config, db, storage)
        # Should not download or add to DB
        # (the mock downloader won't be called)

    def test_calls_downloader(self):
        config, db, storage = MagicMock(), MagicMock(), MagicMock()
        db.model_exists.return_value = False
        with patch("gghf.menu.HfDownloader") as MockDownloader:
            downloader = MagicMock()
            downloader.download.return_value = "/tmp/model"
            MockDownloader.return_value = downloader
            with patch("gghf.menu.prompt_input", return_value="org/model"):
                with patch("gghf.menu.prompt_confirm", return_value=False):
                    _action_add_model(config, db, storage)
                    db.add_model.assert_called_once()


# ── _action_download_updates ──────────────────────────────────────────────


class TestActionDownloadUpdates:
    def test_no_models(self):
        config, db, storage = MagicMock(), MagicMock(), MagicMock()
        db.list_models.return_value = []
        with patch("gghf.menu.prompt_select"):
            _action_download_updates(config, db, storage)

    def test_all_up_to_date(self):
        config, db, storage = MagicMock(), MagicMock(), MagicMock()
        db.list_models.return_value = [{"repo_id": "org/model"}]
        with patch("gghf.menu.Updater") as MockUpdater:
            updater = MagicMock()
            updater.check_updates.return_value = {}
            MockUpdater.return_value = updater
            with patch("gghf.menu.prompt_select"):
                _action_download_updates(config, db, storage)


# ── _action_convert_model ─────────────────────────────────────────────────


class TestActionConvertModel:
    def test_no_models(self):
        config, db, storage = MagicMock(), MagicMock(), MagicMock()
        db.list_models.return_value = []
        with patch("gghf.menu.prompt_select"):
            _action_convert_model(config, db, storage)


# ── _action_manage_gguf ──────────────────────────────────────────────────


class TestActionManageGguf:
    def test_no_models(self):
        config, db, storage = MagicMock(), MagicMock(), MagicMock()
        db.list_models.return_value = []
        with patch("gghf.menu.prompt_select"):
            _action_manage_gguf(config, db, storage)


# ── _action_status ────────────────────────────────────────────────────────


class TestActionStatus:
    def test_no_models(self):
        config, db, storage = MagicMock(), MagicMock(), MagicMock()
        db.list_models.return_value = []
        storage.get_model_status.return_value = {}
        with patch("gghf.menu.prompt_select"):
            _action_status(config, db, storage)


# ── _action_settings ─────────────────────────────────────────────────────


class TestActionSettings:
    def test_calls_save_on_path_change(self):
        config = MagicMock()
        config.storage_root = "/tmp/storage"
        with patch("gghf.menu.prompt_select", return_value="Storage Root:         /tmp/storage"):
            with patch("gghf.menu.prompt_input", return_value="/new/storage"):
                _action_settings(config)
                config.save.assert_called()
