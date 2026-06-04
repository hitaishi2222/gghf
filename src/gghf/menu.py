"""Interactive menu loop for gghf — Typer + Rich (no separate TUI layer)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from gghf.config import Config
from gghf.converter import Converter
from gghf.database import Database
from gghf.downloader import HfDownloader
from gghf.storage import StorageManager
from gghf.updater import Updater
from gghf.ui import (
    format_size,
    prompt_confirm,
    prompt_input,
    prompt_select,
    render_gguf_history,
    render_model_table,
    render_status_table,
)

console = Console()


# ── Main menu ──────────────────────────────────────────────────────────────


def run_menu(
    config: Optional[Config] = None,
    db: Optional[Database] = None,
    storage: Optional[StorageManager] = None,
) -> None:
    """Run the interactive menu loop.

    Options:
      1. Add Model
      2. Download Updates
      3. Convert Model
      4. Manage GGUFs
      5. Model Status
      6. Settings
      7. Exit
    """
    config = config or Config()
    db = db or Database(config.config_dir / "database.sqlite")
    if storage is None:
        storage = StorageManager(
            storage_root=config.storage_root,
            gguf_root=config.gguf_root,
        )

    while True:
        console.print(
            Panel(
                "[bold]gghf[/bold] — HF → GGUF Manager",
                subtitle="Interactive Menu",
                style="blue",
            )
        )
        console.print()

        menu_options = [
            "Add Model",
            "Download Updates",
            "Convert Model",
            "Manage GGUFs",
            "Model Status",
            "Settings",
            "Exit",
        ]

        choice = prompt_select(
            "Select an option",
            menu_options,
            default=None,
        )

        if choice == "Exit":
            console.print("[green]Goodbye![/green]")
            db.close()
            break

        # Dispatch to the selected option
        if choice == "Add Model":
            _action_add_model(config, db, storage)
        elif choice == "Download Updates":
            _action_download_updates(config, db, storage)
        elif choice == "Convert Model":
            _action_convert_model(config, db, storage)
        elif choice == "Manage GGUFs":
            _action_manage_gguf(config, db, storage)
        elif choice == "Model Status":
            _action_status(config, db, storage)
        elif choice == "Settings":
            _action_settings(config)

        console.print()
        console.print("[dim]Press Enter to continue…[/dim]")
        try:
            input()
        except KeyboardInterrupt:
            pass


# ── Menu action handlers ───────────────────────────────────────────────────


def _action_add_model(
    config: Config,
    db: Database,
    storage: StorageManager,
) -> None:
    """Prompt for a repo ID, download the model, and record it."""
    repo_id = prompt_input("[bold]Enter Hugging Face repo ID[/bold] (e.g. org/model-name)")
    if not repo_id.strip():
        console.print("[yellow]Cancelled — no repo ID provided.[/yellow]")
        return

    if db.model_exists(repo_id):
        console.print(f"[yellow]Model {repo_id} is already tracked.[/yellow]")
        return

    # Download
    console.print(f"[cyan]Downloading {repo_id} …[/cyan]")
    downloader = HfDownloader(config=config, database=db, storage_manager=storage)
    try:
        path = downloader.download(repo_id, token=config.hf_token or None)
    except Exception as exc:
        console.print(f"[red]Download failed: {exc}[/red]")
        return

    # Auto-register in DB
    db.add_model(repo_id=repo_id, hf_commit="", status="downloaded")
    console.print(f"[green]✓ Downloaded to {path}[/green]")

    # Ask about immediate conversion
    if prompt_confirm("Convert to GGUF now?", default=False):
        _do_convert(config, db, storage, repo_id)


def _action_download_updates(
    config: Config,
    db: Database,
    storage: StorageManager,
) -> None:
    """Check all tracked models for updates and download newer versions."""
    if not db.list_models():
        console.print("[yellow]No models tracked. Add one first.[/yellow]")
        return

    updater = Updater(config=config, database=db, storage_manager=storage)
    outdated = updater.check_updates()

    if not outdated:
        console.print("[green]All tracked models are up to date.[/green]")
        return

    console.print(f"[yellow]{len(outdated)} model(s) have updates:[/yellow]")
    for repo_id, new_commit in outdated.items():
        console.print(f"  {repo_id} → {new_commit[:12]}")

    if not prompt_confirm("Download updates?", default=True):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    for repo_id in outdated:
        console.print(f"[cyan]Updating {repo_id} …[/cyan]")
        try:
            updater.update_model(repo_id, token=config.hf_token or None)
            console.print(f"[green]✓ {repo_id} updated[/green]")
        except Exception as exc:
            console.print(f"[red]✗ {repo_id}: {exc}[/red]")


def _action_convert_model(
    config: Config,
    db: Database,
    storage: StorageManager,
) -> None:
    """List models needing conversion and let the user pick one."""
    models = db.list_models()
    if not models:
        console.print("[yellow]No models tracked.[/yellow]")
        return

    # Filter to models that need conversion
    converter = Converter(config=config, db=db, storage=storage)
    needs_conv = [m["repo_id"] for m in models if converter.needs_conversion(m["repo_id"])]

    if not needs_conv:
        console.print("[green]No models need conversion.[/green]")
        return

    selected = prompt_select(
        "Select a model to convert",
        needs_conv,
    )
    _do_convert(config, db, storage, selected)


def _action_manage_gguf(
    config: Config,
    db: Database,
    storage: StorageManager,
) -> None:
    """Sub-menu for GGUF management: view history, remove current GGUF."""
    models = db.list_models()
    if not models:
        console.print("[yellow]No models tracked.[/yellow]")
        return

    gguf_options = [
        "View Conversion History",
        "Remove Current GGUF",
        "Back",
    ]

    sub_choice = prompt_select(
        "GGUF Management",
        gguf_options,
    )

    if sub_choice == "View Conversion History":
        repo_id = prompt_select(
            "Select a model",
            [m["repo_id"] for m in models],
        )
        conversions = db.get_conversions(repo_id)
        console.print(render_gguf_history(conversions))

    elif sub_choice == "Remove Current GGUF":
        repo_id = prompt_select(
            "Select a model",
            [m["repo_id"] for m in models],
        )
        gguf_path = storage.gguf_current_path(repo_id)
        if not gguf_path.exists():
            console.print("[yellow]No current GGUF for this model.[/yellow]")
        elif prompt_confirm(f"Remove {gguf_path}?", default=False):
            gguf_path.unlink()
            db.update_status(repo_id, "needs_conversion")
            console.print("[green]GGUF removed. Model marked for conversion.[/green]")
        # Back

    elif sub_choice == "Back":
        pass  # return to main menu


def _action_status(
    config: Config,
    db: Database,
    storage: StorageManager,
) -> None:
    """Show a summary table of all tracked models with their disk usage."""
    models = db.list_models()
    if not models:
        console.print("[yellow]No models tracked.[/yellow]")
        return

    summaries = []
    for m in models:
        summary = storage.get_model_status(m["repo_id"])
        summary.update(m)
        summaries.append(summary)

    console.print(render_status_table(summaries))


def _action_settings(config: Config) -> None:
    """Simple settings editor: view / change storage paths and token."""
    settings_options = [
        f"Storage Root:         {config.storage_root}",
        f"HF Cache Root:        {config.hf_root}",
        f"GGUF Output Root:     {config.gguf_root}",
        f"HF Token:             {'(set)' if config.hf_token else '(not set)'}",
        "Back",
    ]

    choice = prompt_select(
        "Settings",
        settings_options,
    )

    if choice == settings_options[0]:
        new_path = prompt_input("New storage root path", default=str(config.storage_root))
        config.storage_root = Path(new_path)
        config.save()
        console.print("[green]Storage root updated.[/green]")
    elif choice == settings_options[1]:
        new_path = prompt_input("New HF cache root", default=str(config.hf_root))
        config.hf_root = Path(new_path)
        config.save()
        console.print("[green]HF cache root updated.[/green]")
    elif choice == settings_options[2]:
        new_path = prompt_input("New GGUF output root", default=str(config.gguf_root))
        config.gguf_root = Path(new_path)
        config.save()
        console.print("[green]GGUF root updated.[/green]")
    elif choice == settings_options[3]:
        token = prompt_input("Enter HF token", default="(masked)")
        if token and token != "(masked)":
            config.hf_token = token
            config.save()
            console.print("[green]Token saved.[/green]")
        else:
            console.print("[yellow]Token unchanged.[/yellow]")

    # Back — return to main menu


# ── Shared conversion logic ───────────────────────────────────────────────


def _do_convert(
    config: Config,
    db: Database,
    storage: StorageManager,
    repo_id: str,
) -> None:
    """Run the actual conversion after user confirmation."""
    if not db.model_exists(repo_id):
        console.print(f"[red]Model {repo_id} is not tracked.[/red]")
        return

    converter = Converter(config=config, db=db, storage=storage)

    if not converter.llama_cpp.is_available():
        console.print("[red]llama.cpp is not installed. Cannot convert.[/red]")
        return

    estimated = converter.estimate_gguf_size(repo_id)
    console.print(f"[cyan]Estimated GGUF size: {format_size(estimated)}[/cyan]")

    quant_options = ["q4_0", "q4_1", "q5_0", "q5_1", "q8_0", "f16"]
    quant = prompt_select("Select quantization", quant_options, default=0)

    if not prompt_confirm(f"Convert {repo_id} to {quant}?"):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    success = converter.convert_model(repo_id, quantization=quant)
    if success:
        console.print(f"[green]✓ {repo_id} converted to {quant} GGUF[/green]")
    else:
        console.print(f"[red]✗ Conversion failed for {repo_id}[/red]")
