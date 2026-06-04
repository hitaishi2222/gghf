# gghf Core Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working Python CLI that manages Hugging Face model repositories and generates GGUF files locally.

**Architecture:** TDD with bite-sized tasks. Go one step at a time — complete each step fully before moving to the next. Typer handles both interactive (menu loop) and non-interactive (subcommand) modes. Rich provides tables, prompts, and formatting used by all modes — no separate TUI/CLI split. huggingface_hub for repo sync, llama-cpp-python for GGUF conversion. A SQLite database tracks state and provenance.

**Tech Stack:** Python 3.11+, Typer, Rich, huggingface_hub, llama-cpp-python, SQLite3, pytest.

**Code Generation Rules:**

1. Always use the `edit` tool when a file already exists — never overwrite existing files with `write`.
2. Go through the steps of each task one after another, thinking through each step before moving to the next. Complete a step fully before starting the next.
3. Run all tests after each task and verify they pass before marking the task complete.

---

## Current Progress

| Task | Name              | Status                                      | Tests   | Graph Updated? |
| ---- | ----------------- | ------------------------------------------- | ------- | -------------- |
| 1    | Project Skeleton  | ✅ Complete                                 | ✅ Pass | N/A            |
| 2    | Configuration     | ✅ Complete                                 | ✅ Pass | ?              |
| 3    | Database          | ✅ Complete                                 | ✅ Pass | ?              |
| 4    | Storage           | ✅ Complete                                 | ✅ Pass | ?              |
| 5    | Logging           | ✅ Complete                                 | ✅ Pass | ?              |
| 6    | Downloader        | ✅ Complete                                 | ✅ Pass | ?              |
| 7    | Updater           | ✅ Complete                                 | ✅ Pass | ?              |
| 8    | Llama.cpp         | ✅ Complete                                 | ✅ Pass | ?              |
| 9    | Converter         | ✅ Complete                                 | ✅ Pass | ?              |
| 10   | UI Helpers        | ✅ Complete                                 | ✅ Pass | ?              |
| 11   | Interactive Menu  | ✅ Complete                                 | ✅ Pass | ✅             |
| 12   | Typer Subcommands | ✅ Complete                                 | ✅ Pass | ✅             |
| 13   | Private Repos     | ⚠️ Partial — code exists, no explicit tests | ❌ Skip | ?              |
| 14   | Storage Warning   | ❌ Not implemented                          | ❌ Skip | —              |
| 15   | Integration Tests | ❌ Not implemented                          | ❌ Skip | —              |
| 16   | Packaging         | ⚠️ Partial — basic pyproject.toml           | ❌ Skip | ?              |

**Current: 104 passing, 0 failing tests. Tasks 1–12 complete, Tasks 13–16 remaining.**

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

---

## Task 7: Hugging Face Repository Updater

**Goal:** Incrementally update tracked models by comparing stored commit hashes with current ones.

**Files:**

- Create: `src/gghf/updater.py`

- [ ] **Step 1:** Write tests: update a model that has a newer commit available, skip models already up-to-date, detect when a model needs conversion after update.
- [ ] **Step 2:** Run tests and confirm they fail.
- [ ] **Step 3:** Implement `Updater` class. Methods: `get_current_commit` (query HF for latest commit), `check_updates` (compare stored vs current), `update_model` (sync repo, update DB, set status to "needs_conversion"), `list_outdated`.
- [ ] **Step 4:** Run tests and confirm they pass.

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

---

## Task 10: Rich UI Helpers — Tables, Prompts, and Formatting

**Goal:** Provide Rich-based rendering for tables and user prompts, used by all Typer commands (both interactive and non-interactive). No separate TUI layer — Rich works directly inside Typer subcommands.

**Files:**

- Create: `src/gghf/ui.py`
- Modify: `src/gghf/database.py` (add query helper for status summary)
- Test: `tests/test_ui.py`

- [ ] **Step 1:** Write tests: render a table with model repo_id, commit, status, and storage size; render a GGUF history table; format sizes in human-readable units; confirm/select prompts return user choices.
- [ ] **Step 2:** Run tests and confirm they fail.
- [ ] **Step 3:** Implement `src/gghf/ui.py` with: `render_model_table`, `render_gguf_history`, `format_size` (Rich `Table` builders); `prompt_input`, `prompt_confirm`, `prompt_select` (Rich Prompt/TextPrompt wrappers). All functions are plain — no TUI framework, just Rich.
- [ ] **Step 4:** Run tests and confirm they pass.

---

## Task 11: Interactive Menu Loop — Typer + Rich

**Goal:** When invoked with no subcommand, `gghf` runs an interactive menu loop (7 options) built entirely with Rich — same UI helpers from Task 10, no separate TUI layer.

**Files:**

- Create: `src/gghf/menu.py`
- Modify: `src/gghf/cli.py`

- [ ] **Step 1:** Write tests for the menu loop: `run_menu` displays options, `select_model_from_list` lets user pick a tracked model, `confirm_action` gates destructive steps.
- [ ] **Step 2:** Run tests and confirm they fail.
- [ ] **Step 3:** Implement `src/gghf/menu.py`: a single `run_menu()` function that loops through 7 options (add, update, convert, manage GGUF, status, settings, quit). Each option calls the appropriate Typer-command logic using the same backend functions — just different callers (menu vs. CLI subcommand).
- [ ] **Step 4:** Update `cli.py`: when no subcommand is given, call `run_menu()`. Typer Rich integration handles all rendering.
- [ ] **Step 5:** Run tests and confirm they pass.

> **Status: Implementation exists but tests fail** — `input()` in the menu's "Press Enter to continue" prompt hits pytest's stdin capture. Fix: mock `builtins.input` in tests or replace `input()` with `prompt_select` from ui.py.

---

## Task 12: Typer Subcommands — Add, Update, Convert, Status, Config

**Goal:** Provide all functionality as Typer subcommands for non-interactive / scripting use. Uses the same backend functions and Rich UI helpers from Tasks 10–11.

**Files:**

- Modify: `src/gghf/cli.py`

- [ ] **Step 1:** Write tests: `gghf add --repo-id X` adds a model, `gghf update` updates all tracked models, `gghf convert --repo-id X` converts a model, `gghf status` prints a summary, `gghf config show` prints config.
- [ ] **Step 2:** Run tests and confirm they fail.
- [ ] **Step 3:** Add Typer subcommands to `cli.py`: `add`, `update`, `convert`, `status`, `config`. Each calls the same backend functions used by the interactive menu, rendering tables via Rich helpers from Task 10. Non-interactive commands print tables to stdout; interactive menu renders them with Rich's terminal capabilities.
- [ ] **Step 4:** Run tests and confirm they pass.

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

> **Status: Partially done** — `hf_token` attribute exists in Config and is used by the downloader/menu. Explicit unit tests for token masking and private repo download are needed.

---

## Task 14: Storage Warning Before Conversion

**Goal:** Warn about required disk space before converting, estimate output size, and ask for confirmation.

**Files:**

- Create: `src/gghf/exceptions.py`

- [ ] **Step 1:** Write tests: estimate disk space for a model, warn when available space is insufficient, require confirmation before proceeding.
- [ ] **Step 2:** Run tests and confirm they fail.
- [ ] **Step 3:** Implement `StorageWarning` check: calculate model repo size, estimate GGUF size (roughly model-size \* quantization-factor), compare with available disk space, prompt confirmation. Add custom exceptions in `exceptions.py` for `InsufficientStorage`, `ConversionFailed`.
- [ ] **Step 4:** Run tests and confirm they pass.

> **Status: Not implemented** — no `exceptions.py` exists yet. The menu calls `converter.estimate_gguf_size()` but no disk-space check is in place.

---

## Task 15: Integration Tests and End-to-End Smoke Test

**Goal:** Write integration tests that verify the full workflow: add model, check status, update, convert, verify backup exists.

**Files:**

- Create: `tests/integration/test_workflow.py`

- [ ] **Step 1:** Write integration tests: fixture that creates a temp config + DB + storage dir; add a model, verify DB entry, check status output, run conversion (mocked llama.cpp), verify GGUF file created, verify backup file created, verify provenance stored.
- [ ] **Step 2:** Run tests and confirm they fail.
- [ ] **Step 3:** Mock `llama-cpp-python` and `huggingface_hub` to make tests run without actual downloads or conversions. Implement the test fixtures and test methods.
- [ ] **Step 4:** Run tests and confirm they pass.

> **Status: Not implemented** — `tests/integration/` directory does not exist yet.

---

## Task 16: Packaging and Installation Verification

**Goal:** Verify the package installs correctly via `pip install -e .` and the CLI works after installation.

**Files:**

- Modify: `pyproject.toml` (add readme, license, classifiers, optional extras)

- [ ] **Step 1:** Write a test that installs the package in a subprocess and runs `gghf --version`.
- [ ] **Step 2:** Run test and confirm it fails (not yet installable).
- [ ] **Step 3:** Add missing pyproject.toml fields: readme, license, classifiers, python_requires, optional dependencies. Verify `pip install -e .` works.
- [ ] **Step 4:** Run test and confirm it passes.

> **Status: Partially done** — `pyproject.toml` has basic metadata but is missing readme, license, and classifiers.

---
