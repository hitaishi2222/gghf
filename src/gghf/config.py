import os
from pathlib import Path
from typing import Optional

import tomli
import tomli_w


def mask_token(token: Optional[str]) -> Optional[str]:
    """Mask a token for safe display.

    Short tokens (≤ 8 chars) are shown as ``***``.
    Longer tokens show the first 5 characters, ``***``, and the last 4.

    >>> mask_token("hf_sk_abc123def456ghi789")
    'hf_s***789'
    >>> mask_token("")
    ''
    >>> mask_token(None)
    """
    if token is None or token == "":
        return token
    if len(token) <= 8:
        return "***"
    return token[:5] + "***" + token[-4:]


class Config:
    """Manage gghf configuration stored as TOML.

    Defaults are read from a config file at ``config_path`` (default
    ``~/.config/gghf/config.toml``).  Environment variables prefixed
    with ``GGHF_`` override values loaded from disk.
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        if config_path is None:
            config_path = Path.home() / ".config" / "gghf" / "config.toml"
        self.config_path: Path = config_path

        # Load file first
        data = self._load()

        # Apply env overrides — coerce path-like strings to Path
        self._storage_root: Optional[Path] = Path(data["storage_root"]) if data.get("storage_root") else None
        self._hf_root: Optional[Path] = Path(data["hf_root"]) if data.get("hf_root") else None
        self._gguf_root: Optional[Path] = Path(data["gguf_root"]) if data.get("gguf_root") else None
        self._hf_token: Optional[str] = data.get("hf_token")
        self._env_hf_token: Optional[str] = data.get("hf_token") or os.environ.get("GGHF_HF_TOKEN")

        # Re-apply env overrides if present
        env_hf_token = os.environ.get("GGHF_HF_TOKEN")
        if env_hf_token:
            self._hf_token = env_hf_token

    @property
    def storage_root(self) -> Path:
        """Root directory for HF repos and GGUF artifacts."""
        if self._storage_root:
            return self._storage_root
        return Path("/storage")

    @storage_root.setter
    def storage_root(self, value: Path) -> None:
        self._storage_root = value

    @property
    def hf_root(self) -> Path:
        """Root directory for cached Hugging Face repositories."""
        if self._hf_root:
            return self._hf_root
        return Path.home() / ".local" / "share" / "hf-cache"

    @hf_root.setter
    def hf_root(self, value: Path) -> None:
        self._hf_root = value

    @property
    def gguf_root(self) -> Path:
        """Root directory for generated GGUF files."""
        if self._gguf_root:
            return self._gguf_root
        return Path.home() / ".local" / "share" / "gguf"

    @gguf_root.setter
    def gguf_root(self, value: Path) -> None:
        self._gguf_root = value

    @property
    def hf_token(self) -> str:
        """Hugging Face access token."""
        return self._hf_token or ""

    @hf_token.setter
    def hf_token(self, value: str) -> None:
        self._hf_token = value

    @property
    def config_dir(self) -> Path:
        """Directory for gghf configuration files."""
        return Path.home() / ".config" / "gghf"

    @property
    def logs_dir(self) -> Path:
        """Directory for log files."""
        return self.config_dir / "logs"

    def save(self) -> None:
        """Persist current configuration to TOML file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data: dict = {}
        if self._storage_root is not None:
            data["storage_root"] = str(self._storage_root)
        if self._hf_root is not None:
            data["hf_root"] = str(self._hf_root)
        if self._gguf_root is not None:
            data["gguf_root"] = str(self._gguf_root)
        if self._hf_token is not None:
            data["hf_token"] = self._hf_token
        self.config_path.write_text(tomli_w.dumps(data))

    # ---- private helpers ----

    def _load(self) -> dict:
        """Load TOML config from disk."""
        if self.config_path.exists():
            with open(self.config_path, "rb") as f:
                return tomli.load(f)
        return {}
