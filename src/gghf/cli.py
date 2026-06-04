from typing import Optional

import typer
from importlib.metadata import version as get_version
from rich.console import Console
from rich.panel import Panel

from gghf.config import Config
from gghf.database import Database
from gghf.menu import run_menu
from gghf.storage import StorageManager
from gghf.ui import format_size, render_model_table, render_status_table

app = typer.Typer(
    name="gghf",
    help="Manage Hugging Face model repositories and generate GGUF files locally.",
    add_help_option=True,
    add_completion=False,
)


def _version_callback(value: bool):
    if value:
        print(get_version("gghf"))
        raise typer.Exit()

console = Console()


# ── Callback: no subcommand → interactive menu ──────────────────────────────


@app.callback(invoke_without_command=True)
def callback(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", help="Show the version", is_eager=True, callback=_version_callback
    ),
):
    if ctx.invoked_subcommand is None:
        console.print(
            Panel(
                "[bold]gghf[/bold] — HF → GGUF Manager",
                subtitle="Launching interactive menu…",
                style="blue",
            )
        )
        console.print()
        run_menu()


# ── Subcommand: add ─────────────────────────────────────────────────────────


@app.command()
def add(
    repo_id: str = typer.Option(
        ..., "--repo-id", help="Hugging Face model repo ID (e.g. org/model-name)"
    ),
):
    """Add and download a Hugging Face model."""
    config = Config()
    db = Database(config.config_dir / "database.sqlite")
    storage = StorageManager(
        storage_root=config.storage_root,
        gguf_root=config.gguf_root,
    )

    if db.model_exists(repo_id):
        console.print(f"[yellow]Model {repo_id} is already tracked.[/yellow]")
        db.close()
        return

    console.print(f"[cyan]Downloading {repo_id} …[/cyan]")
    from gghf.downloader import HfDownloader

    downloader = HfDownloader(config=config, database=db, storage_manager=storage)
    try:
        path = downloader.download(repo_id, token=config.hf_token or None)
    except Exception as exc:
        console.print(f"[red]Download failed: {exc}[/red]")
        db.close()
        return

    db.add_model(repo_id=repo_id, hf_commit="", status="downloaded")
    console.print(f"[green]✓ Downloaded to {path}[/green]")
    db.close()


# ── Subcommand: update ──────────────────────────────────────────────────────


@app.command()
def update():
    """Check and download updates for all tracked models."""
    config = Config()
    db = Database(config.config_dir / "database.sqlite")
    storage = StorageManager(
        storage_root=config.storage_root,
        gguf_root=config.gguf_root,
    )

    models = db.list_models()
    if not models:
        console.print("[yellow]No models tracked. Add one first.[/yellow]")
        db.close()
        return

    from gghf.updater import Updater

    updater = Updater(config=config, database=db, storage_manager=storage)
    outdated = updater.check_updates()

    if not outdated:
        console.print("[green]All tracked models are up to date.[/green]")
        db.close()
        return

    console.print(f"[yellow]{len(outdated)} model(s) have updates:[/yellow]")
    for repo_id, new_commit in outdated.items():
        console.print(f"  {repo_id} → {new_commit[:12]}")

    for repo_id in outdated:
        console.print(f"[cyan]Updating {repo_id} …[/cyan]")
        try:
            updater.update_model(repo_id, token=config.hf_token or None)
            console.print(f"[green]✓ {repo_id} updated[/green]")
        except Exception as exc:
            console.print(f"[red]✗ {repo_id}: {exc}[/red]")

    db.close()


# ── Subcommand: convert ─────────────────────────────────────────────────────


@app.command()
def convert(
    repo_id: str = typer.Option(
        ..., "--repo-id", help="Hugging Face model repo ID to convert"
    ),
    quantization: str = typer.Option(
        "q4_0", "-q", "--quant", help="Quantization scheme (default: q4_0)"
    ),
):
    """Convert a tracked model to GGUF format."""
    config = Config()
    db = Database(config.config_dir / "database.sqlite")
    storage = StorageManager(
        storage_root=config.storage_root,
        gguf_root=config.gguf_root,
    )

    if not db.model_exists(repo_id):
        console.print(f"[red]Model {repo_id} is not tracked.[/red]")
        db.close()
        return

    from gghf.converter import Converter

    converter = Converter(config=config, db=db, storage=storage)
    if not converter.llama_cpp.is_available():
        console.print("[red]llama.cpp is not installed. Cannot convert.[/red]")
        db.close()
        return

    console.print(f"[cyan]Converting {repo_id} to {quantization} GGUF …[/cyan]")
    success = converter.convert_model(repo_id, quantization=quantization)
    if success:
        console.print(f"[green]✓ {repo_id} converted to {quantization} GGUF[/green]")
    else:
        console.print(f"[red]✗ Conversion failed for {repo_id}[/red]")

    db.close()


# ── Subcommand: status ──────────────────────────────────────────────────────


@app.command()
def status():
    """Show a summary of all tracked models."""
    config = Config()
    db = Database(config.config_dir / "database.sqlite")
    storage = StorageManager(
        storage_root=config.storage_root,
        gguf_root=config.gguf_root,
    )

    models = db.list_models()
    if not models:
        console.print("[yellow]No models tracked.[/yellow]")
        db.close()
        return

    summaries = []
    for m in models:
        summary = storage.get_model_status(m["repo_id"])
        summary.update(m)
        summaries.append(summary)

    console.print(render_status_table(summaries))
    db.close()


# ── Subcommand: config ──────────────────────────────────────────────────────

_config_app = typer.Typer(
    name="config",
    help="View and edit gghf configuration.",
    add_help_option=True,
)


@_config_app.command()
def init():
    """Create a config.toml file with defaults and helpful comments.

    The config file is written to ~/.config/gghf/config.toml (or the
    path set in the GGHF_CONFIG_PATH environment variable).  All values
    are commented out by default so you can uncomment and edit them.
    """
    cfg = Config()

    config_dir = cfg.config_path.parent
    config_dir.mkdir(parents=True, exist_ok=True)

    # Build a commented TOML template with explanations
    template = f"""# ═══════════════════════════════════════════════════════════
# gghf Configuration
# ═══════════════════════════════════════════════════════════
#
# This file controls where gghf stores your Hugging Face model
# downloads and generated GGUF files.
#
#  • Un-comment any value you want to change (remove the leading #)
#  • Paths use shell-tilde expansion — write ~/ or $HOME/
#  • Leave it all commented to use the built-in defaults shown below
#
# ═══════════════════════════════════════════════════════════
# storage_root  — base directory for downloaded HF repositories
# hf_root       — where Hugging Face cached models are stored
# gguf_root     — where converted GGUF files are written
# hf_token      — your Hugging Face access token (required for private repos)
# ═══════════════════════════════════════════════════════════
#
# storage_root = "/storage"                    # base dir for HF repos
# hf_root      = "{cfg.hf_root}"              # HF cache directory
# gguf_root    = "{cfg.gguf_root}"            # GGUF output directory
# hf_token     = ""                            # HF access token (leave blank or set HF_TOKEN env var)
#
"""
    cfg.config_path.write_text(template)
    console.print(f"[green]✓[/green] Config written to [bold]{cfg.config_path}[/bold]")
    console.print(f"[dim]Edit it to override defaults. All values are commented out.[/dim]")


@_config_app.command()
def show():
    """Display the current configuration values."""
    cfg = Config()
    console.print("[bold]gghf Configuration[/bold]")
    console.print(f"  storage_root  : {cfg.storage_root}")
    console.print(f"  hf_root       : {cfg.hf_root}")
    console.print(f"  gguf_root     : {cfg.gguf_root}")
    token_display = cfg.hf_token if not cfg.hf_token else f"{'*' * len(cfg.hf_token)}"
    console.print(f"  hf_token      : {token_display or '(not set)'}")
    console.print(f"  config_path   : {cfg.config_path}")
    if not cfg.config_path.exists():
        console.print("[dim]Note: No config file exists yet. Run 'gghf config init' to create one.[/dim]")
    else:
        console.print(f"[dim]Config file loaded from {cfg.config_path}[/dim]")


app.add_typer(_config_app)


if __name__ == "__main__":
    app()
