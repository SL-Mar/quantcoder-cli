"""Tools for file operations."""

from pathlib import Path

from .base import Tool, ToolResult


class ReadFileTool(Tool):
    """Tool for reading files."""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read contents of a file"

    def execute(self, file_path: str, max_lines: int | None = None) -> ToolResult:
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
            path = Path(file_path)

            if not path.exists():
                return ToolResult(success=False, error=f"File not found: {file_path}")

            with open(path, encoding="utf-8") as f:
                if max_lines:
                    lines = [f.readline() for _ in range(max_lines)]
                    content = "".join(lines)
                else:
                    content = f.read()

            return ToolResult(
                success=True,
                data=content,
                message=f"Read {len(content)} characters from {file_path}",
            )

        except Exception as e:
            self.logger.error(f"Error reading file: {e}")
            return ToolResult(success=False, error=str(e))


class WriteFileTool(Tool):
    """Tool for writing files."""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file"

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
            path.parent.mkdir(parents=True, exist_ok=True)

            mode = "a" if append else "w"
            with open(path, mode, encoding="utf-8") as f:
                f.write(content)

            return ToolResult(
                success=True, message=f"Wrote {len(content)} characters to {file_path}"
            )

        except Exception as e:
            self.logger.error(f"Error writing file: {e}")
            return ToolResult(success=False, error=str(e))
