"""Tests for the quantcoder.config module."""

import pytest
import tempfile
from pathlib import Path

from quantcoder.config import (
    Config,
    ModelConfig,
    UIConfig,
    ToolsConfig,
    MultiAgentConfig,
)


class TestModelConfig:
    """Tests for ModelConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values (Ollama-only)."""
        config = ModelConfig()
        assert config.provider == "ollama"
        assert config.model == "qwen2.5-coder:32b"
        assert config.temperature == 0.5
        assert config.max_tokens == 3000

    def test_code_and_reasoning_models(self):
        """Test code and reasoning model defaults."""
        config = ModelConfig()
        assert config.code_model == "qwen2.5-coder:32b"
        assert config.reasoning_model == "mistral"

    def test_ollama_settings(self):
        """Test Ollama-specific settings."""
        config = ModelConfig()
        assert config.ollama_base_url == "http://localhost:11434"
        assert config.ollama_timeout == 600

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ModelConfig(
            model="mistral",
            temperature=0.7,
            max_tokens=4000,
            code_model="codellama:13b",
            reasoning_model="mistral:7b",
        )
        assert config.model == "mistral"
        assert config.temperature == 0.7
        assert config.max_tokens == 4000
        assert config.code_model == "codellama:13b"
        assert config.reasoning_model == "mistral:7b"


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
        assert data["model"]["provider"] == "ollama"
        assert data["model"]["code_model"] == "qwen2.5-coder:32b"
        assert data["model"]["reasoning_model"] == "mistral"
        assert data["ui"]["theme"] == "monokai"

    def test_from_dict(self):
        """Test configuration deserialization from dict."""
        data = {
            "model": {
                "provider": "ollama",
                "model": "mistral",
                "temperature": 0.8,
                "max_tokens": 2000,
                "code_model": "codellama:13b",
                "reasoning_model": "mistral:7b",
                "ollama_base_url": "http://localhost:11434",
                "ollama_timeout": 300,
            },
            "ui": {
                "theme": "dark",
                "auto_approve": True,
                "show_token_usage": False,
                "editor": "vim",
            },
        }
        config = Config.from_dict(data)

        assert config.model.provider == "ollama"
        assert config.model.model == "mistral"
        assert config.model.code_model == "codellama:13b"
        assert config.ui.theme == "dark"
        assert config.ui.auto_approve is True

    def test_from_dict_strips_v1_suffix(self):
        """Test that /v1 suffix is stripped from ollama_base_url."""
        data = {
            "model": {
                "ollama_base_url": "http://localhost:11434/v1",
            },
        }
        config = Config.from_dict(data)
        assert config.model.ollama_base_url == "http://localhost:11434"

    def test_from_dict_strips_unknown_fields(self):
        """Test that old/unknown model fields are ignored."""
        data = {
            "model": {
                "provider": "ollama",
                "coordinator_provider": "anthropic",  # old field
                "summary_provider": "ollama",  # old field
                "ollama_model": "llama3.2",  # old field
            },
        }
        config = Config.from_dict(data)
        assert config.model.provider == "ollama"

    def test_save_and_load(self):
        """Test saving and loading configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"

            config = Config()
            config.model.code_model = "codellama:13b"
            config.ui.theme = "light"
            config.save(config_path)

            assert config_path.exists()

            loaded_config = Config.load(config_path)
            assert loaded_config.model.code_model == "codellama:13b"
            assert loaded_config.ui.theme == "light"

    def test_load_nonexistent_creates_default(self):
        """Test that loading nonexistent config creates default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nonexistent" / "config.toml"

            config = Config.load(config_path)
            assert config.model.provider == "ollama"

    def test_load_api_key_noop(self):
        """Test load_api_key is a no-op for Ollama."""
        config = Config()
        result = config.load_api_key()
        assert result == ""

    def test_save_api_key_noop(self):
        """Test save_api_key is a no-op for Ollama."""
        config = Config()
        config.save_api_key("anything")  # Should not raise

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
