# gghf

**gghf** — Manage Hugging Face model repositories and generate GGUF files locally.

A Python CLI that downloads, tracks, updates, and converts Hugging Face models to GGUF format for use with local LLM inference engines like llama.cpp.

## Features

- 📥 Download models from Hugging Face Hub (with resume support)
- 🔄 Incremental update tracking via commit hashes
- 🔄 Convert models to GGUF with multiple quantization schemes
- 📊 Interactive menu and non-interactive subcommand modes
- 🔒 Private repository support via HF token
- 💾 Storage management with GGUF backups
- 📝 Full provenance tracking (llama.cpp version, HF commit, timestamps)

## Installation

```bash
pip install -e .
```

### Requirements

- Python 3.11+
- [llama.cpp](https://github.com/ggerganov/llama.cpp) installed (for `llama-quantize` or `convert.py`)

## Usage

### Interactive Mode

```bash
gghf
```

### Subcommands

```bash
gghf add --repo-id org/model-name        # Add and download a model
gghf update                               # Check for updates on all tracked models
gghf convert --repo-id org/model-name     # Convert a model to GGUF
gghf status                               # View tracked models summary
gghf config show                          # View current configuration
```

### Version

```bash
gghf --version
```

## Configuration

Configuration is stored at `~/.config/gghf/config.toml`.

Environment variables that override config:

- `HF_TOKEN` — Hugging Face API token for private repos
- `GGHF_STORAGE_ROOT` — Base directory for model storage
- `GGHF_HF_ROOT` — Hugging Face cache directory
- `GGHF_GGUF_ROOT` — GGUF output directory

## Project Structure

```
src/gghf/
├── cli.py       # Typer CLI entry point
├── config.py    # Configuration management
├── database.py  # SQLite state tracking
├── downloader.py # HF model downloader
├── hf.py        # HF client abstraction
├── llama_cpp.py # llama.cpp integration
├── menu.py      # Interactive menu
├── storage.py   # Filesystem utilities
├── converter.py # GGUF conversion
└── ui.py        # Rich UI helpers
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE).
