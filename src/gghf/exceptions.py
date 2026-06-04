"""Custom exceptions for gghf."""

from __future__ import annotations

from gghf.ui import format_size


class InsufficientStorage(RuntimeError):
    """Raised when available disk space is less than the estimated GGUF output size."""

    def __init__(self, required: int, available: int) -> None:
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient storage: need {format_size(required)}, "
            f"but only {format_size(available)} available."
        )


class ConversionFailed(RuntimeError):
    """Raised when llama.cpp conversion returns a non-zero exit code."""

    def __init__(self, repo_id: str, exit_code: int) -> None:
        self.repo_id = repo_id
        self.exit_code = exit_code
        super().__init__(
            f"Conversion failed for {repo_id} (exit code {exit_code})."
        )
