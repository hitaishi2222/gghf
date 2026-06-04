"""Detection and version retrieval for llama.cpp tools."""

from __future__ import annotations

import shutil
from pathlib import Path
import subprocess
from typing import Optional


class LlamaCpp:
    """Detect installed llama.cpp tools, their versions, and commit hashes."""

    def __init__(self) -> None:
        self._quantize_bin: Optional[str] = shutil.which("llama-quantize")
        self._convert_py: Optional[str] = shutil.which("convert.py")

    # ---- public API ----

    def is_available(self) -> bool:
        """Return True if either ``llama-quantize`` or ``convert.py`` is found."""
        return self._quantize_bin is not None or self._convert_py is not None

    def get_version(self) -> str:
        """Return a human-readable version string, or ``''`` if unavailable."""
        if self._quantize_bin:
            result = subprocess.run(
                [self._quantize_bin, "--version"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip()

        if self._convert_py:
            result = subprocess.run(
                ["python", self._convert_py, "--version"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip()

        return ""

    def get_commit_hash(self, short: bool = True) -> str:
        """Return the git commit hash of the llama.cpp installation.

        Tries ``git rev-parse HEAD`` in the directory of the detected binary.
        Falls back to ``''`` on failure.
        """
        bin_path = self._quantize_bin or self._convert_py
        if bin_path is None:
            return ""

        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=str(next(p for p in [Path(bin_path).parent] if True)),
            )
            if result.returncode == 0:
                commit = result.stdout.strip()
                return commit[:7] if short else commit
        except Exception:
            pass

        # Last resort: try to read .git/HEAD from a common install location
        for guess in [
            Path.home() / ".local" / "share" / "llama.cpp",
            Path("/usr/local/share/llama.cpp"),
        ]:
            head_file = guess / ".git" / "HEAD"
            if head_file.exists():
                ref = head_file.read_text().strip()
                if ref.startswith("ref: "):
                    ref_path = guess / ".git" / ref[5:]
                    if ref_path.exists():
                        commit = ref_path.read_text().strip()
                        return commit[:7] if short else commit

        return ""

    def convert(
        self,
        model_path: str,
        output_path: str,
        quantization: str = "q4_0",
    ) -> int:
        """Invoke llama.cpp quantize with the given parameters.

        Returns the subprocess exit code.
        """
        if self._quantize_bin:
            cmd = [
                self._quantize_bin,
                model_path,
                output_path,
                quantization,
            ]
        elif self._convert_py:
            cmd = [
                "python",
                self._convert_py,
                "-m",
                model_path,
                "-f",  # placeholder — actual args depend on convert.py version
            ]
            return -1  # convert.py invocation varies too much; delegate to converter module
        else:
            raise RuntimeError("llama.cpp is not available.")

        result = subprocess.run(cmd)
        return result.returncode
