"""Base classes for tools."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from a tool execution."""

    success: bool
    data: Any = None
    error: str | None = None
    message: str | None = None

    def __str__(self) -> str:
        if self.success:
            return self.message or f"Success: {self.data}"
        else:
            return self.error or "Unknown error"


class Tool(ABC):
    """Base class for all tools."""

    def __init__(self, config: Any):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    def is_enabled(self) -> bool:
        """Check if tool is enabled in configuration."""
        enabled = self.config.tools.enabled_tools
        disabled = self.config.tools.disabled_tools

        # Check if explicitly disabled
        if self.name in disabled or "*" in disabled:
            return False

        # Check if enabled
        if "*" in enabled or self.name in enabled:
            return True

        return False

    def require_approval(self) -> bool:
        """Check if tool requires user approval before execution."""
        # By default, tools don't require approval in auto-approve mode
        return not self.config.ui.auto_approve

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
