import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(
    name="gghf",
    help="Manage Hugging Face model repositories and generate GGUF files locally.",
    add_help_option=True,
)


def _main_menu() -> None:
    console = Console()
    menu = """
 1. Add Model
 2. Download Updates
 3. Convert Model
 4. Manage GGUFs
 5. Model Status
 6. Settings
 7. Exit
"""
    console.print(Panel("[bold]gghf[/bold] — HF → GGUF Manager", subtitle="Main Menu"))
    console.print(menu)


@app.command()
def main():
    """Launch the interactive gghf menu."""
    _main_menu()


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        _main_menu()


if __name__ == "__main__":
    app()
