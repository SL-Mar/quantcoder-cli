"""Configuration management for QuantCoder CLI."""

import os
import stat
import toml
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

# Service name for keyring storage
KEYRING_SERVICE = "quantcoder-cli"


def _get_keyring():
    """Get keyring module if available."""
    try:
        import keyring
        return keyring
    except ImportError:
        return None


@dataclass
class ModelConfig:
    """Configuration for the AI model."""
    provider: str = "anthropic"  # anthropic, mistral, deepseek, openai, ollama
    model: str = "claude-sonnet-4-5-20250929"
    temperature: float = 0.5
    max_tokens: int = 3000

    # Multi-agent specific
    coordinator_provider: str = "anthropic"  # Best for orchestration
    code_provider: str = "mistral"  # Devstral for code generation
    risk_provider: str = "anthropic"  # Sonnet for nuanced risk decisions

    # Local LLM (Ollama) settings
    ollama_base_url: str = "http://localhost:11434/v1"  # Ollama API endpoint
    ollama_model: str = "llama3.2"  # Default Ollama model (codellama, qwen2.5-coder, etc.)


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
                "ollama_base_url": self.model.ollama_base_url,
                "ollama_model": self.model.ollama_model,
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
        """Load API key from keyring, environment, or .env file (in that order)."""
        from dotenv import load_dotenv

        # 1. Try keyring first (most secure)
        keyring = _get_keyring()
        if keyring:
            try:
                api_key = keyring.get_password(KEYRING_SERVICE, "OPENAI_API_KEY")
                if api_key:
                    logger.debug("Loaded API key from system keyring")
                    self.api_key = api_key
                    return api_key
            except Exception as e:
                logger.debug(f"Keyring not available: {e}")

        # 2. Try environment variable
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            logger.debug("Loaded API key from environment variable")
            self.api_key = api_key
            return api_key

        # 3. Try .env file in home directory
        env_path = self.home_dir / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                logger.debug(f"Loaded API key from {env_path}")
                self.api_key = api_key
                return api_key

        raise EnvironmentError(
            "OPENAI_API_KEY not found. Please set it via:\n"
            "  1. System keyring (most secure): quantcoder config set-key\n"
            "  2. Environment variable: export OPENAI_API_KEY=your_key\n"
            f"  3. .env file: {env_path}"
        )

    def load_quantconnect_credentials(self) -> tuple[str, str]:
        """Load QuantConnect API credentials from keyring, environment, or .env file."""
        from dotenv import load_dotenv

        api_key = None
        user_id = None

        # 1. Try keyring first
        keyring = _get_keyring()
        if keyring:
            try:
                api_key = keyring.get_password(KEYRING_SERVICE, "QUANTCONNECT_API_KEY")
                user_id = keyring.get_password(KEYRING_SERVICE, "QUANTCONNECT_USER_ID")
                if api_key and user_id:
                    logger.debug("Loaded QuantConnect credentials from system keyring")
            except Exception as e:
                logger.debug(f"Keyring not available: {e}")

        # 2. Try environment variables
        if not api_key:
            api_key = os.getenv("QUANTCONNECT_API_KEY")
        if not user_id:
            user_id = os.getenv("QUANTCONNECT_USER_ID")

        # 3. Try .env file
        if not api_key or not user_id:
            env_path = self.home_dir / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                if not api_key:
                    api_key = os.getenv("QUANTCONNECT_API_KEY")
                if not user_id:
                    user_id = os.getenv("QUANTCONNECT_USER_ID")

        if not api_key or not user_id:
            raise EnvironmentError(
                "QuantConnect credentials not found. Please set via:\n"
                "  1. System keyring: quantcoder config set-qc-credentials\n"
                "  2. Environment: export QUANTCONNECT_API_KEY=... QUANTCONNECT_USER_ID=...\n"
                f"  3. .env file: {self.home_dir / '.env'}"
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

    def save_api_key(self, api_key: str, provider: str = "openai"):
        """
        Save API key securely using keyring (preferred) or secure file storage.

        Args:
            api_key: The API key to store
            provider: The provider name (openai, anthropic, mistral, etc.)
        """
        key_name = f"{provider.upper()}_API_KEY"

        # 1. Try keyring first (most secure - uses OS credential store)
        keyring = _get_keyring()
        if keyring:
            try:
                keyring.set_password(KEYRING_SERVICE, key_name, api_key)
                logger.info(f"API key saved to system keyring ({key_name})")
                self.api_key = api_key
                return
            except Exception as e:
                logger.warning(f"Could not save to keyring: {e}. Falling back to file storage.")

        # 2. Fallback to .env file with restricted permissions
        env_path = self.home_dir / ".env"
        env_path.parent.mkdir(parents=True, exist_ok=True)

        # Read existing content to preserve other keys
        existing_content = {}
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        k, v = line.split('=', 1)
                        existing_content[k] = v

        # Update with new key
        existing_content[key_name] = api_key

        # Write with restricted permissions (owner read/write only)
        with open(env_path, 'w') as f:
            for k, v in existing_content.items():
                f.write(f"{k}={v}\n")

        # Set file permissions to 600 (owner read/write only)
        try:
            os.chmod(env_path, stat.S_IRUSR | stat.S_IWUSR)
            logger.info(f"API key saved to {env_path} (permissions: 600)")
        except Exception as e:
            logger.warning(f"Could not set file permissions: {e}")
            logger.info(f"API key saved to {env_path}")

        self.api_key = api_key
