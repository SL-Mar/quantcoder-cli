"""Configuration management for QuantCoder CLI."""

import os
import toml
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for the AI model."""
    provider: str = "anthropic"  # anthropic, mistral, deepseek, openai
    model: str = "claude-sonnet-4-5-20250929"
    temperature: float = 0.5
    max_tokens: int = 3000

    # Multi-agent specific
    coordinator_provider: str = "anthropic"  # Best for orchestration
    code_provider: str = "mistral"  # Devstral for code generation
    risk_provider: str = "anthropic"  # Sonnet for nuanced risk decisions


@dataclass
class UIConfig:
    """Configuration for the user interface."""
    theme: str = "monokai"
    auto_approve: bool = False
    show_token_usage: bool = True
    editor: str = "zed"  # Editor for --open-in-editor flag (zed, code, vim, etc.)


@dataclass
class ToolsConfig:
    """Configuration for tools."""
    enabled_tools: list[str] = field(default_factory=lambda: ["*"])
    disabled_tools: list[str] = field(default_factory=list)
    downloads_dir: str = "downloads"
    generated_code_dir: str = "generated_code"


@dataclass
class MultiAgentConfig:
    """Configuration for multi-agent system."""
    enabled: bool = True
    parallel_execution: bool = True
    max_parallel_agents: int = 5
    validation_enabled: bool = True
    auto_backtest: bool = False
    max_refinement_attempts: int = 3


@dataclass
class Config:
    """Main configuration class for QuantCoder."""

    model: ModelConfig = field(default_factory=ModelConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    tools: ToolsConfig = field(default_factory=ToolsConfig)
    multi_agent: MultiAgentConfig = field(default_factory=MultiAgentConfig)
    api_key: Optional[str] = None
    quantconnect_api_key: Optional[str] = None
    quantconnect_user_id: Optional[str] = None
    home_dir: Path = field(default_factory=lambda: Path.home() / ".quantcoder")

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """Load configuration from file or create default."""
        if config_path is None:
            config_path = Path.home() / ".quantcoder" / "config.toml"

        if config_path.exists():
            logger.info(f"Loading configuration from {config_path}")
            try:
                data = toml.load(config_path)
                return cls.from_dict(data)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                return cls()
        else:
            logger.info("No configuration found, creating default")
            config = cls()
            config.save(config_path)
            return config

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create configuration from dictionary."""
        config = cls()

        if "model" in data:
            config.model = ModelConfig(**data["model"])
        if "ui" in data:
            config.ui = UIConfig(**data["ui"])
        if "tools" in data:
            config.tools = ToolsConfig(**data["tools"])

        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "model": {
                "provider": self.model.provider,
                "model": self.model.model,
                "temperature": self.model.temperature,
                "max_tokens": self.model.max_tokens,
            },
            "ui": {
                "theme": self.ui.theme,
                "auto_approve": self.ui.auto_approve,
                "show_token_usage": self.ui.show_token_usage,
                "editor": self.ui.editor,
            },
            "tools": {
                "enabled_tools": self.tools.enabled_tools,
                "disabled_tools": self.tools.disabled_tools,
                "downloads_dir": self.tools.downloads_dir,
                "generated_code_dir": self.tools.generated_code_dir,
            }
        }

    def save(self, config_path: Optional[Path] = None):
        """Save configuration to file."""
        if config_path is None:
            config_path = self.home_dir / "config.toml"

        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w') as f:
            toml.dump(self.to_dict(), f)

        logger.info(f"Configuration saved to {config_path}")

    def load_api_key(self) -> str:
        """Load API key from environment or .env file."""
        from dotenv import load_dotenv

        # Try to load from .env in home directory
        env_path = self.home_dir / ".env"
        if env_path.exists():
            load_dotenv(env_path)

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY not found. Please set it in your environment "
                f"or create {env_path} with OPENAI_API_KEY=your_key"
            )

        self.api_key = api_key
        return api_key

    def load_quantconnect_credentials(self) -> tuple[str, str]:
        """Load QuantConnect API credentials from environment."""
        from dotenv import load_dotenv

        env_path = self.home_dir / ".env"
        if env_path.exists():
            load_dotenv(env_path)

        api_key = os.getenv("QUANTCONNECT_API_KEY")
        user_id = os.getenv("QUANTCONNECT_USER_ID")

        if not api_key or not user_id:
            raise EnvironmentError(
                "QuantConnect credentials not found. Please set QUANTCONNECT_API_KEY "
                f"and QUANTCONNECT_USER_ID in your environment or {env_path}"
            )

        self.quantconnect_api_key = api_key
        self.quantconnect_user_id = user_id
        return api_key, user_id

    def has_quantconnect_credentials(self) -> bool:
        """Check if QuantConnect credentials are available."""
        from dotenv import load_dotenv

        env_path = self.home_dir / ".env"
        if env_path.exists():
            load_dotenv(env_path)

        api_key = os.getenv("QUANTCONNECT_API_KEY")
        user_id = os.getenv("QUANTCONNECT_USER_ID")
        return bool(api_key and user_id)

    def save_api_key(self, api_key: str):
        """Save API key to .env file."""
        env_path = self.home_dir / ".env"
        env_path.parent.mkdir(parents=True, exist_ok=True)

        with open(env_path, 'w') as f:
            f.write(f"OPENAI_API_KEY={api_key}\n")

        logger.info(f"API key saved to {env_path}")
        self.api_key = api_key
