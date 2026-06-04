import os
import tempfile
from pathlib import Path

from gghf.config import Config


class TestConfigDefaults:
    def test_default_config_dir(self):
        config = Config()
        assert config.config_dir == Path.home() / ".config" / "gghf"

    def test_default_storage_root(self):
        config = Config()
        assert config.storage_root == Path("/storage")

    def test_default_hf_root(self):
        config = Config()
        assert config.hf_root == Path.home() / ".local" / "share" / "hf-cache"

    def test_default_gguf_root(self):
        config = Config()
        assert config.gguf_root == Path.home() / ".local" / "share" / "gguf"

    def test_default_hf_token_is_empty(self):
        config = Config()
        assert config.hf_token == ""

    def test_default_logs_dir(self):
        config = Config()
        assert config.logs_dir == config.config_dir / "logs"


class TestConfigFromToml:
    def test_load_from_config_file(self):
        toml_content = """
storage_root = "/custom/storage"
hf_root = "/custom/hf"
gguf_root = "/custom/gguf"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            f.flush()
            config = Config(config_path=Path(f.name))
            assert config.storage_root == Path("/custom/storage")
            assert config.hf_root == Path("/custom/hf")
            assert config.gguf_root == Path("/custom/gguf")
        Path(f.name).unlink()

    def test_load_hf_token_from_config_file(self):
        toml_content = 'hf_token = "hf_test_token_123"\n'
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            f.flush()
            config = Config(config_path=Path(f.name))
            assert config.hf_token == "hf_test_token_123"
        Path(f.name).unlink()


class TestConfigSaveAndReload:
    def test_save_to_toml_and_reload(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("")
            f.flush()
            config = Config(config_path=Path(f.name))
            config.storage_root = Path("/new/storage")
            config.hf_token = "secret_token"
            config.save()

            # Reload
            reloaded = Config(config_path=Path(f.name))
            assert reloaded.storage_root == Path("/new/storage")
            assert reloaded.hf_token == "secret_token"
        Path(f.name).unlink()

    def test_save_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "sub" / "config.toml"
            config = Config(config_path=config_path)
            config.storage_root = Path("/tmp/test")
            config.save()
            assert config_path.exists()


class TestConfigEnvOverride:
    def test_hf_token_from_env(self):
        os.environ["GGHF_HF_TOKEN"] = "env_token_456"
        try:
            config = Config()
            assert config.hf_token == "env_token_456"
        finally:
            del os.environ["GGHF_HF_TOKEN"]

    def test_env_token_overrides_config_file(self):
        toml_content = 'hf_token = "file_token"\n'
        os.environ["GGHF_HF_TOKEN"] = "env_token_456"
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
                f.write(toml_content)
                f.flush()
                config = Config(config_path=Path(f.name))
                assert config.hf_token == "env_token_456"
            Path(f.name).unlink()
        finally:
            del os.environ["GGHF_HF_TOKEN"]
