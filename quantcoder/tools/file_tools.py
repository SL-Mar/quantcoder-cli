"""Tools for file operations."""

from pathlib import Path
from typing import Optional, List
from .base import Tool, ToolResult, validate_path_within_directory, PathSecurityError

# Maximum file size to read (10 MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Allowed directories for file operations (relative to cwd or absolute paths within project)
# These can be extended via configuration


class ReadFileTool(Tool):
    """Tool for reading files within allowed directories."""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read contents of a file within allowed directories"

    def _get_allowed_directories(self) -> List[Path]:
        """Get list of allowed directories for reading."""
        cwd = Path.cwd()
        return [
            cwd,
            cwd / self.config.tools.downloads_dir,
            cwd / self.config.tools.generated_code_dir,
            self.config.home_dir,
        ]

    def _is_path_allowed(self, file_path: Path) -> bool:
        """Check if path is within allowed directories."""
        resolved = file_path.resolve()
        for allowed_dir in self._get_allowed_directories():
            try:
                resolved.relative_to(allowed_dir.resolve())
                return True
            except ValueError:
                continue
        return False

    def execute(self, file_path: str, max_lines: Optional[int] = None) -> ToolResult:
        """
        Read a file.

        Args:
            file_path: Path to the file
            max_lines: Maximum number of lines to read

        Returns:
            ToolResult with file contents
        """
        self.logger.info(f"Reading file: {file_path}")

        try:
            path = Path(file_path).resolve()

            # Validate path is within allowed directories
            if not self._is_path_allowed(path):
                self.logger.warning(f"Attempted to read file outside allowed directories: {file_path}")
                return ToolResult(
                    success=False,
                    error="File path is outside allowed directories"
                )

            if not path.exists():
                return ToolResult(
                    success=False,
                    error=f"File not found: {file_path}"
                )

            # Check file size to prevent memory issues
            if path.stat().st_size > MAX_FILE_SIZE:
                return ToolResult(
                    success=False,
                    error=f"File too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)"
                )

            with open(path, 'r', encoding='utf-8') as f:
                if max_lines:
                    lines = [f.readline() for _ in range(max_lines)]
                    content = ''.join(lines)
                else:
                    content = f.read()

            return ToolResult(
                success=True,
                data=content,
                message=f"Read {len(content)} characters from {file_path}"
            )

        except PathSecurityError as e:
            self.logger.error(f"Path security error: {e}")
            return ToolResult(success=False, error="Path security violation")
        except Exception as e:
            self.logger.error(f"Error reading file: {e}")
            return ToolResult(success=False, error=str(e))


class WriteFileTool(Tool):
    """Tool for writing files within allowed directories."""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file within allowed directories"

    def _get_allowed_directories(self) -> List[Path]:
        """Get list of allowed directories for writing."""
        cwd = Path.cwd()
        return [
            cwd / self.config.tools.downloads_dir,
            cwd / self.config.tools.generated_code_dir,
        ]

    def _is_path_allowed(self, file_path: Path) -> bool:
        """Check if path is within allowed directories for writing."""
        resolved = file_path.resolve()
        for allowed_dir in self._get_allowed_directories():
            try:
                # Ensure parent directory exists or will be created within allowed dir
                allowed_resolved = allowed_dir.resolve()
                resolved.relative_to(allowed_resolved)
                return True
            except ValueError:
                continue
        return False

    def execute(self, file_path: str, content: str, append: bool = False) -> ToolResult:
        """
        Write to a file.

        Args:
            file_path: Path to the file
            content: Content to write
            append: Whether to append or overwrite

        Returns:
            ToolResult with write status
        """
        self.logger.info(f"Writing to file: {file_path}")

        try:
            path = Path(file_path)

            # For relative paths, resolve against cwd
            if not path.is_absolute():
                path = Path.cwd() / path

            path = path.resolve()

            # Validate path is within allowed directories
            if not self._is_path_allowed(path):
                self.logger.warning(f"Attempted to write file outside allowed directories: {file_path}")
                return ToolResult(
                    success=False,
                    error="File path is outside allowed directories (downloads/ or generated_code/)"
                )

            # Create parent directories within allowed path
            path.parent.mkdir(parents=True, exist_ok=True)

            mode = 'a' if append else 'w'
            with open(path, mode, encoding='utf-8') as f:
                f.write(content)

            return ToolResult(
                success=True,
                message=f"Wrote {len(content)} characters to {file_path}"
            )

        except PathSecurityError as e:
            self.logger.error(f"Path security error: {e}")
            return ToolResult(success=False, error="Path security violation")
        except Exception as e:
            self.logger.error(f"Error writing file: {e}")
            return ToolResult(success=False, error=str(e))
