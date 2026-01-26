"""Tests for the quantcoder.tools module."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from quantcoder.tools.base import Tool, ToolResult
from quantcoder.tools.file_tools import ReadFileTool, WriteFileTool
from quantcoder.tools.article_tools import SearchArticlesTool, DownloadArticleTool, SummarizeArticleTool
from quantcoder.tools.code_tools import GenerateCodeTool, ValidateCodeTool, BacktestTool


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_success_result(self):
        """Test successful result creation."""
        result = ToolResult(
            success=True,
            data="test data",
            message="Operation successful"
        )
        assert result.success is True
        assert result.data == "test data"
        assert result.message == "Operation successful"

    def test_error_result(self):
        """Test error result creation."""
        result = ToolResult(
            success=False,
            error="Something went wrong"
        )
        assert result.success is False
        assert result.error == "Something went wrong"

    def test_str_success(self):
        """Test string representation for success."""
        result = ToolResult(success=True, message="Done")
        assert str(result) == "Done"

    def test_str_success_with_data(self):
        """Test string representation for success with data."""
        result = ToolResult(success=True, data="my_data")
        assert "my_data" in str(result)

    def test_str_error(self):
        """Test string representation for error."""
        result = ToolResult(success=False, error="Failed")
        assert str(result) == "Failed"

    def test_str_unknown_error(self):
        """Test string representation for unknown error."""
        result = ToolResult(success=False)
        assert str(result) == "Unknown error"


class TestToolBase:
    """Tests for Tool base class."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.tools.enabled_tools = ["*"]
        config.tools.disabled_tools = []
        config.ui.auto_approve = False
        return config

    def test_is_enabled_wildcard(self, mock_config):
        """Test tool enabled with wildcard."""
        class TestTool(Tool):
            @property
            def name(self):
                return "test_tool"

            @property
            def description(self):
                return "Test tool"

            def execute(self, **kwargs):
                return ToolResult(success=True)

        tool = TestTool(mock_config)
        assert tool.is_enabled() is True

    def test_is_enabled_specific(self, mock_config):
        """Test tool enabled by specific name."""
        mock_config.tools.enabled_tools = ["test_tool"]

        class TestTool(Tool):
            @property
            def name(self):
                return "test_tool"

            @property
            def description(self):
                return "Test tool"

            def execute(self, **kwargs):
                return ToolResult(success=True)

        tool = TestTool(mock_config)
        assert tool.is_enabled() is True

    def test_is_disabled(self, mock_config):
        """Test tool disabled."""
        mock_config.tools.disabled_tools = ["test_tool"]

        class TestTool(Tool):
            @property
            def name(self):
                return "test_tool"

            @property
            def description(self):
                return "Test tool"

            def execute(self, **kwargs):
                return ToolResult(success=True)

        tool = TestTool(mock_config)
        assert tool.is_enabled() is False

    def test_is_disabled_wildcard(self, mock_config):
        """Test tool disabled with wildcard."""
        mock_config.tools.disabled_tools = ["*"]

        class TestTool(Tool):
            @property
            def name(self):
                return "test_tool"

            @property
            def description(self):
                return "Test tool"

            def execute(self, **kwargs):
                return ToolResult(success=True)

        tool = TestTool(mock_config)
        assert tool.is_enabled() is False

    def test_require_approval(self, mock_config):
        """Test tool requires approval by default."""
        class TestTool(Tool):
            @property
            def name(self):
                return "test_tool"

            @property
            def description(self):
                return "Test tool"

            def execute(self, **kwargs):
                return ToolResult(success=True)

        tool = TestTool(mock_config)
        assert tool.require_approval() is True

    def test_no_approval_in_auto_mode(self, mock_config):
        """Test tool doesn't require approval in auto mode."""
        mock_config.ui.auto_approve = True

        class TestTool(Tool):
            @property
            def name(self):
                return "test_tool"

            @property
            def description(self):
                return "Test tool"

            def execute(self, **kwargs):
                return ToolResult(success=True)

        tool = TestTool(mock_config)
        assert tool.require_approval() is False

    def test_repr(self, mock_config):
        """Test tool representation."""
        class TestTool(Tool):
            @property
            def name(self):
                return "test_tool"

            @property
            def description(self):
                return "Test tool"

            def execute(self, **kwargs):
                return ToolResult(success=True)

        tool = TestTool(mock_config)
        assert "test_tool" in repr(tool)


class TestReadFileTool:
    """Tests for ReadFileTool class."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.tools.enabled_tools = ["*"]
        config.tools.disabled_tools = []
        return config

    def test_name_and_description(self, mock_config):
        """Test tool name and description."""
        tool = ReadFileTool(mock_config)
        assert tool.name == "read_file"
        assert "read" in tool.description.lower()

    def test_read_existing_file(self, mock_config):
        """Test reading an existing file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Hello, World!")
            f.flush()

            tool = ReadFileTool(mock_config)
            result = tool.execute(file_path=f.name)

            assert result.success is True
            assert result.data == "Hello, World!"

            Path(f.name).unlink()

    def test_read_with_max_lines(self, mock_config):
        """Test reading with line limit."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Line 1\nLine 2\nLine 3\n")
            f.flush()

            tool = ReadFileTool(mock_config)
            result = tool.execute(file_path=f.name, max_lines=2)

            assert result.success is True
            assert "Line 1" in result.data
            assert "Line 2" in result.data

            Path(f.name).unlink()

    def test_read_nonexistent_file(self, mock_config):
        """Test reading a nonexistent file."""
        tool = ReadFileTool(mock_config)
        result = tool.execute(file_path="/nonexistent/path/file.txt")

        assert result.success is False
        assert "not found" in result.error.lower()


class TestWriteFileTool:
    """Tests for WriteFileTool class."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.tools.enabled_tools = ["*"]
        config.tools.disabled_tools = []
        return config

    def test_name_and_description(self, mock_config):
        """Test tool name and description."""
        tool = WriteFileTool(mock_config)
        assert tool.name == "write_file"
        assert "write" in tool.description.lower()

    def test_write_new_file(self, mock_config):
        """Test writing to a new file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"

            tool = WriteFileTool(mock_config)
            result = tool.execute(file_path=str(file_path), content="Hello!")

            assert result.success is True
            assert file_path.exists()
            assert file_path.read_text() == "Hello!"

    def test_write_creates_directories(self, mock_config):
        """Test that writing creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "nested" / "dir" / "test.txt"

            tool = WriteFileTool(mock_config)
            result = tool.execute(file_path=str(file_path), content="Content")

            assert result.success is True
            assert file_path.exists()

    def test_write_append_mode(self, mock_config):
        """Test appending to a file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Original")
            f.flush()

            tool = WriteFileTool(mock_config)
            result = tool.execute(
                file_path=f.name,
                content=" Appended",
                append=True
            )

            assert result.success is True
            content = Path(f.name).read_text()
            assert content == "Original Appended"

            Path(f.name).unlink()

    def test_write_overwrite_mode(self, mock_config):
        """Test overwriting a file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Original content")
            f.flush()

            tool = WriteFileTool(mock_config)
            result = tool.execute(
                file_path=f.name,
                content="New content",
                append=False
            )

            assert result.success is True
            content = Path(f.name).read_text()
            assert content == "New content"

            Path(f.name).unlink()


class TestSearchArticlesTool:
    """Tests for SearchArticlesTool class."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.tools.enabled_tools = ["*"]
        config.tools.disabled_tools = []
        return config

    def test_name_and_description(self, mock_config):
        """Test tool name and description."""
        tool = SearchArticlesTool(mock_config)
        assert tool.name == "search_articles"
        assert "search" in tool.description.lower()

    @patch('requests.get')
    def test_search_success(self, mock_get, mock_config):
        """Test successful article search."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'message': {
                'items': [
                    {
                        'DOI': '10.1234/test',
                        'title': ['Test Article'],
                        'author': [{'given': 'John', 'family': 'Doe'}],
                        'published': {'date-parts': [[2023, 1, 15]]},
                        'abstract': 'Test abstract'
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        tool = SearchArticlesTool(mock_config)
        result = tool.execute(query="momentum trading")

        assert result.success is True
        assert result.data is not None

    @patch('requests.get')
    def test_search_no_results(self, mock_get, mock_config):
        """Test search with no results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'message': {'items': []}}
        mock_get.return_value = mock_response

        tool = SearchArticlesTool(mock_config)
        result = tool.execute(query="nonexistent query xyz")

        assert result.success is True
        assert result.data == []

    @patch('requests.get')
    def test_search_api_error(self, mock_get, mock_config):
        """Test search with API error."""
        mock_get.side_effect = Exception("Network error")

        tool = SearchArticlesTool(mock_config)
        result = tool.execute(query="test")

        assert result.success is False
        assert "error" in result.error.lower() or "Network" in result.error


class TestGenerateCodeTool:
    """Tests for GenerateCodeTool class."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration with API key."""
        config = MagicMock()
        config.tools.enabled_tools = ["*"]
        config.tools.disabled_tools = []
        config.tools.downloads_dir = "downloads"
        config.tools.generated_code_dir = "generated_code"
        config.api_key = "test-key"
        config.load_api_key.return_value = "test-key"
        return config

    def test_name_and_description(self, mock_config):
        """Test tool name and description."""
        tool = GenerateCodeTool(mock_config)
        assert tool.name == "generate_code"
        assert "generate" in tool.description.lower()


class TestValidateCodeTool:
    """Tests for ValidateCodeTool class."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.tools.enabled_tools = ["*"]
        config.tools.disabled_tools = []
        config.has_quantconnect_credentials.return_value = False
        return config

    def test_name_and_description(self, mock_config):
        """Test tool name and description."""
        tool = ValidateCodeTool(mock_config)
        assert tool.name == "validate_code"
        assert "validate" in tool.description.lower()

    def test_validate_valid_code(self, mock_config):
        """Test validating syntactically correct code."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write("def hello():\n    return 'Hello'\n")
            f.flush()

            tool = ValidateCodeTool(mock_config)
            result = tool.execute(file_path=f.name, local_only=True)

            assert result.success is True
            Path(f.name).unlink()

    def test_validate_invalid_code(self, mock_config):
        """Test validating syntactically incorrect code."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write("def hello(\n    # missing closing paren")
            f.flush()

            tool = ValidateCodeTool(mock_config)
            result = tool.execute(file_path=f.name, local_only=True)

            assert result.success is False
            Path(f.name).unlink()

    def test_validate_nonexistent_file(self, mock_config):
        """Test validating nonexistent file."""
        tool = ValidateCodeTool(mock_config)
        result = tool.execute(file_path="/nonexistent/file.py", local_only=True)

        assert result.success is False


class TestBacktestTool:
    """Tests for BacktestTool class."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.tools.enabled_tools = ["*"]
        config.tools.disabled_tools = []
        config.has_quantconnect_credentials.return_value = False
        return config

    def test_name_and_description(self, mock_config):
        """Test tool name and description."""
        tool = BacktestTool(mock_config)
        assert tool.name == "backtest"
        assert "backtest" in tool.description.lower()

    def test_backtest_without_credentials(self, mock_config):
        """Test backtest fails without QC credentials."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write("def main(): pass")
            f.flush()

            tool = BacktestTool(mock_config)
            result = tool.execute(
                file_path=f.name,
                start_date="2020-01-01",
                end_date="2020-12-31"
            )

            # Should fail or indicate missing credentials
            assert result.success is False or "credential" in str(result).lower()

            Path(f.name).unlink()
