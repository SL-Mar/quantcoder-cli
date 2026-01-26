"""Base classes for tools."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union
import logging
import os

logger = logging.getLogger(__name__)


class PathSecurityError(Exception):
    """Raised when a path operation would violate security constraints."""
    pass


def validate_path_within_directory(
    file_path: Union[str, Path],
    allowed_directory: Union[str, Path],
    must_exist: bool = False
) -> Path:
    """
    Validate that a file path is within an allowed directory.

    This prevents path traversal attacks where malicious paths like
    '../../../etc/passwd' could escape the intended directory.

    Args:
        file_path: The path to validate
        allowed_directory: The directory the path must be within
        must_exist: If True, the path must exist

    Returns:
        The resolved, validated path

    Raises:
        PathSecurityError: If the path escapes the allowed directory
        FileNotFoundError: If must_exist=True and path doesn't exist
    """
    # Resolve both paths to absolute canonical paths
    resolved_path = Path(file_path).resolve()
    resolved_allowed = Path(allowed_directory).resolve()

    # Check if the resolved path is within the allowed directory
    try:
        resolved_path.relative_to(resolved_allowed)
    except ValueError:
        raise PathSecurityError(
            f"Path '{file_path}' resolves outside allowed directory '{allowed_directory}'. "
            f"Resolved path: {resolved_path}"
        )

    if must_exist and not resolved_path.exists():
        raise FileNotFoundError(f"Path does not exist: {resolved_path}")

    return resolved_path


def get_safe_path(
    base_dir: Union[str, Path],
    *path_parts: str,
    create_parents: bool = False
) -> Path:
    """
    Safely construct a path within a base directory.

    Args:
        base_dir: The base directory (must exist or be created)
        *path_parts: Path components to join (e.g., "subdir", "file.txt")
        create_parents: If True, create parent directories

    Returns:
        A validated path within base_dir

    Raises:
        PathSecurityError: If the resulting path would escape base_dir
    """
    base = Path(base_dir).resolve()

    # Join path parts
    target = base.joinpath(*path_parts)

    # Resolve and validate
    resolved = target.resolve()

    # Ensure it's still within base_dir (handles .. in path_parts)
    try:
        resolved.relative_to(base)
    except ValueError:
        raise PathSecurityError(
            f"Path components {path_parts} would escape base directory '{base_dir}'"
        )

    if create_parents:
        resolved.parent.mkdir(parents=True, exist_ok=True)

    return resolved


@dataclass
class ToolResult:
    """Result from a tool execution."""

    success: bool
    data: Any = None
    error: Optional[str] = None
    message: Optional[str] = None

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
