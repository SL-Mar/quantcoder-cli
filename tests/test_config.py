"""Tests for the quantcoder.config module."""

import tempfile
from pathlib import Path

import pytest

from quantcoder.config import (
    Config,
    ModelConfig,
    MultiAgentConfig,
    ToolsConfig,
    UIConfig,
)


class TestModelConfig:
    """Tests for ModelConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ModelConfig()
        assert config.provider == "anthropic"
        assert config.model == "claude-sonnet-4-5-20250929"
        assert config.temperature == 0.5
        assert config.max_tokens == 3000

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ModelConfig(
            provider="openai",
            model="gpt-4",
            temperature=0.7,
            max_tokens=4000,
        )
        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.temperature == 0.7
        assert config.max_tokens == 4000

    def test_ollama_settings(self):
        """Test Ollama-specific settings."""
        config = ModelConfig()
        assert config.ollama_base_url == "http://localhost:11434/v1"
        assert config.ollama_model == "llama3.2"


class TestUIConfig:
    """Tests for UIConfig dataclass."""

    def test_default_values(self):
        """Test default UI configuration."""
        config = UIConfig()
        assert config.theme == "monokai"
        assert config.auto_approve is False
        assert config.show_token_usage is True
        assert config.editor == "zed"

    def test_custom_values(self):
        """Test custom UI configuration."""
        config = UIConfig(theme="dark", auto_approve=True, editor="code")
        assert config.theme == "dark"
        assert config.auto_approve is True
        assert config.editor == "code"


class TestToolsConfig:
    """Tests for ToolsConfig dataclass."""

    def test_default_values(self):
        """Test default tools configuration."""
        config = ToolsConfig()
        assert config.enabled_tools == ["*"]
        assert config.disabled_tools == []
        assert config.downloads_dir == "downloads"
        assert config.generated_code_dir == "generated_code"

    def test_custom_tools(self):
        """Test custom tools configuration."""
        config = ToolsConfig(
            enabled_tools=["search", "download"],
            disabled_tools=["backtest"],
        )
        assert "search" in config.enabled_tools
        assert "backtest" in config.disabled_tools


class TestMultiAgentConfig:
    """Tests for MultiAgentConfig dataclass."""

    def test_default_values(self):
        """Test default multi-agent configuration."""
        config = MultiAgentConfig()
        assert config.enabled is True
        assert config.parallel_execution is True
        assert config.max_parallel_agents == 5
        assert config.validation_enabled is True
        assert config.auto_backtest is False

    def test_disabled_config(self):
        """Test disabled multi-agent configuration."""
        config = MultiAgentConfig(enabled=False, parallel_execution=False)
        assert config.enabled is False
        assert config.parallel_execution is False


class TestConfig:
    """Tests for main Config class."""

    def test_default_config(self):
        """Test default configuration creation."""
        config = Config()
        assert isinstance(config.model, ModelConfig)
        assert isinstance(config.ui, UIConfig)
        assert isinstance(config.tools, ToolsConfig)
        assert isinstance(config.multi_agent, MultiAgentConfig)
        assert config.api_key is None

    def test_to_dict(self):
        """Test configuration serialization to dict."""
        config = Config()
        data = config.to_dict()

        assert "model" in data
        assert "ui" in data
        assert "tools" in data
        assert data["model"]["provider"] == "anthropic"
        assert data["ui"]["theme"] == "monokai"

    def test_from_dict(self):
        """Test configuration deserialization from dict."""
        data = {
            "model": {
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.8,
                "max_tokens": 2000,
            },
            "ui": {
                "theme": "dark",
                "auto_approve": True,
                "show_token_usage": False,
                "editor": "vim",
            },
        }
        config = Config.from_dict(data)

        assert config.model.provider == "openai"
        assert config.model.model == "gpt-4"
        assert config.ui.theme == "dark"
        assert config.ui.auto_approve is True

    def test_save_and_load(self):
        """Test saving and loading configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"

            # Create and save config
            config = Config()
            config.model.provider = "mistral"
            config.ui.theme = "light"
            config.save(config_path)

            # Verify file exists
            assert config_path.exists()

            # Load and verify
            loaded_config = Config.load(config_path)
            assert loaded_config.model.provider == "mistral"
            assert loaded_config.ui.theme == "light"

    def test_load_nonexistent_creates_default(self):
        """Test that loading nonexistent config creates default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nonexistent" / "config.toml"

            # Should create default config
            config = Config.load(config_path)
            assert config.model.provider == "anthropic"

    def test_load_api_key_from_env(self, monkeypatch):
        """Test loading API key from environment."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            config.home_dir = Path(tmpdir)

            api_key = config.load_api_key()
            assert api_key == "test-api-key"
            assert config.api_key == "test-api-key"

    def test_load_api_key_raises_without_key(self, monkeypatch):
        """Test that missing API key raises error."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            config.home_dir = Path(tmpdir)

            with pytest.raises(EnvironmentError):
                config.load_api_key()

    def test_save_api_key(self):
        """Test saving API key to .env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            config.home_dir = Path(tmpdir)

            config.save_api_key("my-secret-key")

            env_path = Path(tmpdir) / ".env"
            assert env_path.exists()
            assert "my-secret-key" in env_path.read_text()

    def test_has_quantconnect_credentials(self, monkeypatch):
        """Test checking for QuantConnect credentials."""
        monkeypatch.setenv("QUANTCONNECT_API_KEY", "qc-key")
        monkeypatch.setenv("QUANTCONNECT_USER_ID", "qc-user")

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            config.home_dir = Path(tmpdir)

            assert config.has_quantconnect_credentials() is True

    def test_has_quantconnect_credentials_missing(self, monkeypatch):
        """Test missing QuantConnect credentials."""
        monkeypatch.delenv("QUANTCONNECT_API_KEY", raising=False)
        monkeypatch.delenv("QUANTCONNECT_USER_ID", raising=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            config.home_dir = Path(tmpdir)

            assert config.has_quantconnect_credentials() is False

    def test_load_quantconnect_credentials(self, monkeypatch):
        """Test loading QuantConnect credentials."""
        monkeypatch.setenv("QUANTCONNECT_API_KEY", "qc-api-key")
        monkeypatch.setenv("QUANTCONNECT_USER_ID", "qc-user-id")

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            config.home_dir = Path(tmpdir)

            api_key, user_id = config.load_quantconnect_credentials()
            assert api_key == "qc-api-key"
            assert user_id == "qc-user-id"

    def test_load_quantconnect_credentials_raises_without_creds(self, monkeypatch):
        """Test that missing QC credentials raises error."""
        monkeypatch.delenv("QUANTCONNECT_API_KEY", raising=False)
        monkeypatch.delenv("QUANTCONNECT_USER_ID", raising=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config()
            config.home_dir = Path(tmpdir)

            with pytest.raises(EnvironmentError):
                config.load_quantconnect_credentials()
