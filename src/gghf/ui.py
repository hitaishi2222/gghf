"""Rich UI helpers — tables, prompts, and formatting for Typer commands."""

from __future__ import annotations

import io
from typing import Any, List, Optional, Sequence

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

_console = Console()


# ── Table builders ──────────────────────────────────────────────────────────


def render_model_table(
    models: List[dict[str, Any]],
) -> Table:
    """Build a Rich Table showing tracked-model info.

    Columns: repo_id, hf_commit, status, added_at (formatted), size.
    """
    table = Table(title="Tracked Models", show_header=True, show_lines=True)
    table.add_column("Repo ID", style="cyan", max_width=40)
    table.add_column("HF Commit", style="magenta", max_width=12)
    table.add_column("Status", style="green")
    table.add_column("Size")
    table.add_column("Added")

    for m in models:
        repo_id = m.get("repo_id", "")
        commit = (m.get("hf_commit") or "—")[:12]
        status = m.get("status", "unknown")
        size = format_size(m.get("hf_size", 0))
        added = m.get("added_at")
        added_str = _human_time(added) if added else "—"
        table.add_row(repo_id, commit, status, size, added_str)

    if not models:
        table.add_row("—", "—", "—", "—", "—")

    return table


def render_gguf_history(conversions: List[dict[str, Any]]) -> Table:
    """Build a Rich Table showing GGUF conversion provenance."""
    table = Table(title="Conversion History", show_header=True, show_lines=True)
    table.add_column("Quantization", style="yellow")
    table.add_column("HF Commit", style="magenta", max_width=12)
    table.add_column("GGUF Commit", style="blue", max_width=12)
    table.add_column("Timestamp")

    for c in conversions:
        table.add_row(
            c.get("quantization", "—"),
            (c.get("gguf_commit") or c.get("hf_commit") or "—")[:12],
            (c.get("hf_commit") or "—")[:12],
            _human_time(c.get("timestamp")),
        )

    if not conversions:
        table.add_row("—", "—", "—", "—")

    return table


def render_status_table(models: List[dict[str, Any]]) -> Table:
    """Build a compact table for the ``gghf status`` command."""
    table = Table(title="Model Status", show_header=True)
    table.add_column("Repo ID", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("HF Cache Size")
    table.add_column("GGUF Size")

    for m in models:
        table.add_row(
            m.get("repo_id", "—"),
            m.get("status", "—"),
            format_size(m.get("hf_size", 0)),
            format_size(m.get("gguf_size", 0)),
        )

    if not models:
        table.add_row("—", "—", "—", "—")

    return table


# ── Size formatting ────────────────────────────────────────────────────────


def format_size(n: int | float) -> str:
    """Convert bytes to a human-readable string (e.g. ``1.0 GiB``)."""
    if n == 0:
        return "0 B"

    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    magnitude = len(units) - 1

    abs_n = abs(n)
    # Pick the largest unit where the value is >= 1.0
    exponent = 0
    for i in range(1, magnitude + 1):
        if abs_n >= 1024**i:
            exponent = i
        else:
            break
    divisor = 1024**exponent
    value = n / divisor
    unit = units[exponent]

    if exponent == 0:
        return f"{int(n)} {unit}"
    return f"{value:.1f} {unit}"


# ── Prompt helpers ─────────────────────────────────────────────────────────


def prompt_input(message: str, default: Optional[str] = None) -> str:
    """Ask the user for text input, with an optional default."""
    return Prompt.ask(message, default=default or "")


def prompt_confirm(message: str, default: bool = False) -> bool:
    """Ask the user for a yes/no confirmation."""
    return Confirm.ask(message, default=default)


def prompt_select(
    message: str,
    options: Sequence[str],
    default: Optional[int] = None,
) -> str:
    """Present a numbered list and return the selected option string."""
    for i, opt in enumerate(options, 1):
        _console.print(f"  [bold]{i}[/].  {opt}")
    choice = Prompt.ask(
        f"\n  {message}",
        choices=[str(i) for i in range(1, len(options) + 1)],
        default=str(default) if default is not None else None,
    )
    return options[int(choice) - 1]


# ── Private helpers ────────────────────────────────────────────────────────


def _human_time(timestamp: float | None) -> str:
    """Format a Unix timestamp as a human-readable date, or '—' if None."""
    if timestamp is None:
        return "—"
    from datetime import datetime

    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M")
