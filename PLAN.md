# gghf Core Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working Python CLI that manages Hugging Face model repositories and generates GGUF files locally.

**Architecture:** TDD with bite-sized tasks. Each task produces a self-contained, committed change. The package uses Typer for CLI, Rich for interactive menus, huggingface_hub for repo sync, and llama-cpp-python for GGUF conversion. A SQLite database tracks state and provenance.

**Tech Stack:** Python 3.11+, Typer, Rich, huggingface_hub, llama-cpp-python, SQLite3, pytest.

---

## Task 1: Project Skeleton — package layout, pyproject.toml, and CLI entry point

**Goal:** Establish a working Python package with proper dependency declarations and an entry point that launches the interactive TUI.

**Files:**
- Create: `pyproject.toml`
- Create: `src/gghf/__init__.py`
- Create: `src/gghf/cli.py`
- Create: `tests/__init__.py`

- [x] **Step 1:** Create `pyproject.toml` with package metadata, dependencies (rich, typer, huggingface_hub, llama-cpp-python), entry point `gghf = "gghf.cli:app"`, and project version 0.1.0.
- [x] **Step 2:** Create `src/gghf/__init__.py` with a `__version__` constant read from package metadata.
- [x] **Step 3:** Create `src/gghf/cli.py` with a Typer application. Print the main menu when invoked without subcommands. Add `--help` flag.
- [x] **Step 4:** Create empty `tests/__init__.py`.
- [x] **Step 5:** Write a test that runs `gghf --help` via subprocess and asserts exit code 0 and that "gghf" appears in stdout.
- [x] **Step 6:** Run the test and confirm it fails (package doesn't exist yet).
- [x] **Step 7:** Write minimal stub implementation so `gghf --help` works.
- [x] **Step 8:** Run the test and confirm it passes.
- [x] **Step 9:** Stage all files and commit with message "feat: add project skeleton with CLI entry point".

---

## Task 2: Configuration Management

**Goal:** Provide a `Config` class that reads/writes `~/.config/gghf/config.toml` with sensible defaults.

**Files:**
- Create: `src/gghf/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1:** Write tests for the Config class: default values for storage_root, hf_cache_root, gguf_root, config_dir, hf_token; save and reload; override via env vars.
- [ ] **Step 2:** Run tests and confirm they fail (config.py doesn't exist).
- [ ] **Step 3:** Implement `Config` class with attributes matching the defaults: `storage_root` = `/storage`, `hf` = `~/.local/share/hf-cache`, `gguf` = `~/.local/share/gguf`, `config_dir` = `~/.config/gghf`. Use `tomllib` to read and `tomli_w` to write.
- [ ] **Step 4:** Run tests and confirm they pass.
- [ ] **Step 5:** Commit with message "feat: add configuration management with TOML support".

---

## Task 3: Database Schema — tracked models

**Goal:** Create a SQLite database at `~/.config/gghf/database.sqlite` with tables for tracked models and their state.

**Files:**
- Create: `src/gghf/database.py`
- Test: `tests/test_database.py`

- [ ] **Step 1:** Write tests: create database, add a model (repo_id, hf_commit, status), query models, update commit hash, check if model exists.
- [ ] **Step 2:** Run tests and confirm they fail.
- [ ] **Step 3:** Implement `Database` class using `sqlite3`. Create `tracked_models` table with columns: `repo_id` (PK), `hf_commit`, `status`, `added_at`, `updated_at`. Provide methods: `add_model`, `get_model`, `update_commit`, `list_models`, `model_exists`, `remove_model`.
- [ ] **Step 4:** Run tests and confirm they pass.
- [ ] **Step 5:** Commit with message "feat: add SQLite database for model tracking".

---

## Task 4: Filesystem Utilities

**Goal:** Provide helpers for storage path resolution, directory creation, and backup management.

**Files:**
- Create: `src/gghf/storage.py`
- Test: `tests/test_storage.py`

- [ ] **Step 1:** Write tests: resolve model paths under storage_root, create directories, create a backup with timestamp, verify backups directory exists.
- [ ] **Step 2:** Run tests and confirm they fail.
- [ ] **Step 3:** Implement `StorageManager` class. Methods: `hf_model_path`, `gguf_model_path`, `gguf_current_path`, `gguf_backups_dir`, `create_backup` (copies current.gguf to backups/ with timestamp suffix), `ensure_directories` (creates all needed dirs), `get_model_status`.
- [ ] **Step 4:** Run tests and confirm they pass.
- [ ] **Step 5:** Commit with message "feat: add storage path management and backup helpers".

---

## Task 5: Logging Setup

**Goal:** Configure structured logging to `~/.config/gghf/logs/` with per-feature log files.

**Files:**
- Create: `src/gghf/utils/logging.py`
- Test: `tests/test_logging.py`

- [ ] **Step 1:** Write tests: logger returns a configured logger, log file exists after first log, log files are named correctly (app.log, download.log, conversion.log, update.log).
- [ ] **Step 2:** Run tests and confirm they fail.
- [ ] **Step 3:** Implement `get_logger(name)` that creates or retrieves a logger. If name maps to download/conversion/update, route to the corresponding log file. All logs go to `~/.config/gghf/logs/`. Use standard logging with a file handler and a console handler.
- [ ] **Step 4:** Run tests and confirm they pass.
- [ ] **Step 5:** Commit with message "feat: add structured logging to feature-specific log files".

---

## Task 6: Hugging Face Repository Downloader

**Goal:** Download and sync HF model repositories with resume support, preferring `hf` CLI when available and falling back to `huggingface_hub`.

**Files:**
- Create: `src/gghf/downloader.py`
- Create: `src/gghf/hf.py`
- Test: `tests/test_downloader.py`

- [ ] **Step 1:** Write tests: download a model to the correct path, resume partial download, detect if `hf` CLI is available, fall back to `huggingface_hub` API, handle private repos with token.
- [ ] **Step 2:** Run tests and confirm they fail.
- [ ] **Step 3:** Implement `HfDownloader` in `downloader.py`. Use `hf` CLI with `--resume` when available, otherwise use `snapshot_download` from `huggingface_hub`. Pass token for private repos. Log progress.
- [ ] **Step 4:** Implement `HfClient` in `hf.py` — a thin wrapper that detects available CLI tools and exposes `download(repo_id, token)`.
- [ ] **Step 5:** Run tests and confirm they pass.
- [ ] **Step 6:** Commit with message "feat: add HF repository downloader with resume support".

---

## Task 7: Hugging Face Repository Updater

**Goal:** Incrementally update tracked models by comparing stored commit hashes with current ones.

**Files:**
- Create: `src/gghf/updater.py`

- [ ] **Step 1:** Write tests: update a model that has a newer commit available, skip models already up-to-date, detect when a model needs conversion after update.
- [ ] **Step 2:** Run tests and confirm they fail.
- [ ] **Step 3:** Implement `Updater` class. Methods: `get_current_commit` (query HF for latest commit), `check_updates` (compare stored vs current), `update_model` (sync repo, update DB, set status to "needs_conversion"), `list_outdated`.
- [ ] **Step 4:** Run tests and confirm they pass.
- [ ] **Step 5:** Commit with message "feat: add incremental model updater with commit tracking".

---

## Task 8: LLama.cpp Integration

**Goal:** Detect installed llama.cpp, retrieve its version and commit hash, and expose a conversion function.

**Files:**
- Create: `src/gghf/llama_cpp.py`
- Test: `tests/test_llama_cpp.py`

- [ ] **Step 1:** Write tests: detect if llama.cpp is installed, get version string, get commit hash, run conversion command on a test model path.
- [ ] **Step 2:** Run tests and confirm they fail.
- [ ] **Step 3:** Implement `LlamaCpp` class. Methods: `is_available` (check for `llama-quantize` or `convert.py`), `get_version` (parse `llama-quantize --version`), `get_commit_hash` (read `.git/HEAD` or last commit from install), `convert` (invoke the correct llama.cpp tool).
- [ ] **Step 4:** Run tests and confirm they pass.
- [ ] **Step 5:** Commit with message "feat: add llama.cpp detection and version retrieval".

---

## Task 9: GGUF Conversion

**Goal:** Convert a HF model repo to GGUF, back up the old GGUF, store conversion provenance (llama.cpp version, commit hash, HF commit hash, timestamp).

**Files:**
- Create: `src/gghf/converter.py`
- Test: `tests/test_converter.py`

- [ ] **Step 1:** Write tests: convert a model to GGUF, backup existing GGUF before overwriting, store provenance in DB, skip conversion if llama.cpp is not available, warn about storage before converting.
- [ ] **Step 2:** Run tests and confirm they fail.
- [ ] **Step 3:** Implement `Converter` class. Methods: `convert_model` (invoke llama.cpp convert, write to current.gguf, backup old file, insert provenance row), `get_conversions` (list past conversions for a model), `needs_conversion` (check if status is "needs_conversion" or GGUF doesn't exist).
- [ ] **Step 4:** Run tests and confirm they pass.
- [ ] **Step 5:** Commit with message "feat: add GGUF conversion with backup and provenance tracking".

---

## Task 10: Model Status and Rich Tables

**Goal:** Display model status, storage usage, and conversion history using Rich tables.

**Files:**
- Create: `src/gghf/tui/tables.py`
- Modify: `src/gghf/database.py` (add query helper for status summary)
- Test: `tests/test_tables.py`

- [ ] **Step 1:** Write tests: render a table with model repo_id, commit, status, and storage size; render a GGUF history table; format sizes in human-readable units.
- [ ] **Step 2:** Run tests and confirm they fail.
- [ ] **Step 3:** Implement table rendering functions: `render_model_table`, `render_gguf_history`, `format_size`. Each takes model data and returns a Rich `Table` object.
- [ ] **Step 4:** Run tests and confirm they pass.
- [ ] **Step 5:** Commit with message "feat: add Rich table rendering for model status".

---

## Task 11: Interactive TUI — Menu System

**Goal:** Build the full interactive terminal UI with Rich, implementing all 7 main menu items and their submenus.

**Files:**
- Create: `src/gghf/tui/prompts.py`
- Create: `src/gghf/tui/menus.py`
- Modify: `src/gghf/cli.py`

- [ ] **Step 1:** Write tests for the prompt system: input_with_default, confirm_action, select_from_list, menu_loop.
- [ ] **Step 2:** Run tests and confirm they fail.
- [ ] **Step 3:** Implement `prompts.py`: `input_with_default`, `confirm_action`, `select_from_list`, `error_box`, `info_box`.
- [ ] **Step 4:** Implement `menus.py`: `main_menu` (7 options), `add_model_menu`, `update_model_menu`, `convert_model_menu`, `manage_gguf_menu`, `model_status_menu`, `settings_menu`. Each invokes the appropriate backend logic and displays results.
- [ ] **Step 5:** Update `cli.py` to launch the TUI when no subcommand is given.
- [ ] **Step 6:** Run tests and confirm they pass.
- [ ] **Step 7:** Commit with message "feat: add interactive TUI with full menu system".

---

## Task 12: Direct CLI Commands

**Goal:** Provide all functionality as Typer subcommands (add, update, convert, status, config) for non-interactive use.

**Files:**
- Modify: `src/gghf/cli.py`

- [ ] **Step 1:** Write tests: `gghf add --repo-id X` adds a model, `gghf update` updates all tracked models, `gghf convert --repo-id X` converts a model, `gghf status` prints a summary, `gghf config show` prints config.
- [ ] **Step 2:** Run tests and confirm they fail.
- [ ] **Step 3:** Add Typer subcommands to `cli.py`: `add`, `update`, `convert`, `status`, `config`. Each routes to the appropriate backend function with appropriate flags and output.
- [ ] **Step 4:** Run tests and confirm they pass.
- [ ] **Step 5:** Commit with message "feat: add direct CLI subcommands for all operations".

---

## Task 13: Private Repository Support

**Goal:** Handle private HF repos via token storage in config and authentication during download.

**Files:**
- Modify: `src/gghf/config.py`
- Modify: `src/gghf/downloader.py`

- [ ] **Step 1:** Write tests: save HF token to config, use token when downloading private repos, token is masked in logs and output.
- [ ] **Step 2:** Run tests and confirm they fail.
- [ ] **Step 3:** Add `hf_token` to Config (stored as env var `HF_TOKEN` or config file). Update downloader to pass token to both CLI and API paths. Mask token in log output.
- [ ] **Step 4:** Run tests and confirm they pass.
- [ ] **Step 5:** Commit with message "feat: add private repository support with token management".

---

## Task 14: Storage Warning Before Conversion

**Goal:** Warn about required disk space before converting, estimate output size, and ask for confirmation.

**Files:**
- Create: `src/gghf/exceptions.py`

- [ ] **Step 1:** Write tests: estimate disk space for a model, warn when available space is insufficient, require confirmation before proceeding.
- [ ] **Step 2:** Run tests and confirm they fail.
- [ ] **Step 3:** Implement `StorageWarning` check: calculate model repo size, estimate GGUF size (roughly model-size * quantization-factor), compare with available disk space, prompt confirmation. Add custom exceptions in `exceptions.py` for `InsufficientStorage`, `ConversionFailed`.
- [ ] **Step 4:** Run tests and confirm they pass.
- [ ] **Step 5:** Commit with message "feat: add storage warning before GGUF conversion".

---

## Task 15: Integration Tests and End-to-End Smoke Test

**Goal:** Write integration tests that verify the full workflow: add model, check status, update, convert, verify backup exists.

**Files:**
- Create: `tests/integration/test_workflow.py`

- [ ] **Step 1:** Write integration tests: fixture that creates a temp config + DB + storage dir; add a model, verify DB entry, check status output, run conversion (mocked llama.cpp), verify GGUF file created, verify backup file created, verify provenance stored.
- [ ] **Step 2:** Run tests and confirm they fail.
- [ ] **Step 3:** Mock `llama-cpp-python` and `huggingface_hub` to make tests run without actual downloads or conversions. Implement the test fixtures and test methods.
- [ ] **Step 4:** Run tests and confirm they pass.
- [ ] **Step 5:** Commit with message "test: add integration tests for full workflow".

---

## Task 16: Packaging and Installation Verification

**Goal:** Verify the package installs correctly via `pip install -e .` and the CLI works after installation.

**Files:**
- Modify: `pyproject.toml` (add readme, license, classifiers, optional extras)

- [ ] **Step 1:** Write a test that installs the package in a subprocess and runs `gghf --version`.
- [ ] **Step 2:** Run test and confirm it fails (not yet installable).
- [ ] **Step 3:** Add missing pyproject.toml fields: readme, license, classifiers, python_requires, optional dependencies. Verify `pip install -e .` works.
- [ ] **Step 4:** Run test and confirm it passes.
- [ ] **Step 5:** Commit with message "chore: finalize packaging and verify installation".

---
