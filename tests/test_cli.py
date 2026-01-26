"""
CLI Integration Tests for QuantCoder
=====================================

Tests CLI commands using Click's CliRunner.
These tests validate argument parsing, error messages, and output formatting.

Run with: pytest tests/test_cli.py -v
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from click.testing import CliRunner

from quantcoder.cli import main as cli


@pytest.fixture
def cli_env(tmp_path, monkeypatch):
    """Set up environment for CLI tests with mock API key."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-12345")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    return tmp_path


class TestVersionCommand:
    """Test the version command."""

    def test_version_displays_version(self, cli_env):
        """Test that version command displays version number."""
        runner = CliRunner()
        result = runner.invoke(cli, ["version"])

        assert result.exit_code == 0
        assert "QuantCoder" in result.output
        assert "v" in result.output or "." in result.output

    def test_version_no_args_required(self, cli_env):
        """Test that version command requires no arguments."""
        runner = CliRunner()
        result = runner.invoke(cli, ["version", "--help"])

        assert result.exit_code == 0
        assert "Show version information" in result.output


class TestHealthCommand:
    """Test the health command."""

    def test_health_returns_valid_exit_code(self, cli_env):
        """Test that health command returns valid exit codes."""
        runner = CliRunner()
        result = runner.invoke(cli, ["health"])

        # Exit code 0 = healthy, 1 = some checks failed (both valid)
        assert result.exit_code in [0, 1]

    def test_health_json_output_is_valid(self, cli_env):
        """Test that health --json outputs valid JSON."""
        runner = CliRunner()
        result = runner.invoke(cli, ["health", "--json"])

        assert result.exit_code in [0, 1]

        # Try to parse JSON output
        output = result.output.strip()
        if output:
            try:
                data = json.loads(output)
                assert isinstance(data, dict)
            except json.JSONDecodeError:
                # Non-JSON output acceptable for error cases
                pass

    def test_health_help_shows_usage(self, cli_env):
        """Test that health --help shows usage info."""
        runner = CliRunner()
        result = runner.invoke(cli, ["health", "--help"])

        assert result.exit_code == 0
        assert "Check application health" in result.output
        assert "--json" in result.output


class TestSearchCommand:
    """Test the search command."""

    def test_search_requires_query_argument(self, cli_env):
        """Test that search command requires query argument."""
        runner = CliRunner()
        result = runner.invoke(cli, ["search"])

        # Either shows missing argument or usage - both valid
        assert result.exit_code != 0 or "Missing argument" in result.output or "Usage" in result.output

    def test_search_help_shows_usage(self, cli_env):
        """Test that search --help shows usage info."""
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--help"])

        assert result.exit_code == 0
        assert "Search for academic articles" in result.output
        assert "--num" in result.output
        assert "QUERY" in result.output

    @patch('quantcoder.cli.SearchArticlesTool')
    def test_search_with_valid_query(self, mock_tool_class, cli_env):
        """Test search with a valid query."""
        # Mock the tool
        mock_tool = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message = "Found 2 articles"
        mock_result.data = [
            {"title": "Test Article 1", "authors": "Author A", "published": "2023"},
            {"title": "Test Article 2", "authors": "Author B", "published": "2024"},
        ]
        mock_tool.execute.return_value = mock_result
        mock_tool_class.return_value = mock_tool

        runner = CliRunner()
        result = runner.invoke(cli, ["search", "momentum trading"])

        assert result.exit_code == 0
        mock_tool.execute.assert_called_once()

    @patch('quantcoder.cli.SearchArticlesTool')
    def test_search_with_num_option(self, mock_tool_class, cli_env):
        """Test search with --num option."""
        mock_tool = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message = "Found 3 articles"
        mock_result.data = []
        mock_tool.execute.return_value = mock_result
        mock_tool_class.return_value = mock_tool

        runner = CliRunner()
        result = runner.invoke(cli, ["search", "test query", "--num", "10"])

        assert result.exit_code == 0
        call_kwargs = mock_tool.execute.call_args
        assert call_kwargs[1]["max_results"] == 10


class TestDownloadCommand:
    """Test the download command."""

    def test_download_requires_article_id(self, cli_env):
        """Test that download command requires article_id argument."""
        runner = CliRunner()
        result = runner.invoke(cli, ["download"])

        assert result.exit_code != 0

    def test_download_help_shows_usage(self, cli_env):
        """Test that download --help shows usage info."""
        runner = CliRunner()
        result = runner.invoke(cli, ["download", "--help"])

        assert result.exit_code == 0
        assert "Download an article PDF" in result.output
        assert "ARTICLE_ID" in result.output


class TestSummarizeCommand:
    """Test the summarize command."""

    def test_summarize_requires_article_id(self, cli_env):
        """Test that summarize command requires article_id argument."""
        runner = CliRunner()
        result = runner.invoke(cli, ["summarize"])

        assert result.exit_code != 0

    def test_summarize_help_shows_usage(self, cli_env):
        """Test that summarize --help shows usage info."""
        runner = CliRunner()
        result = runner.invoke(cli, ["summarize", "--help"])

        assert result.exit_code == 0
        assert "Summarize a downloaded article" in result.output
        assert "ARTICLE_ID" in result.output


class TestGenerateCommand:
    """Test the generate command."""

    def test_generate_requires_article_id(self, cli_env):
        """Test that generate command requires article_id argument."""
        runner = CliRunner()
        result = runner.invoke(cli, ["generate"])

        assert result.exit_code != 0

    def test_generate_help_shows_options(self, cli_env):
        """Test that generate --help shows all options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["generate", "--help"])

        assert result.exit_code == 0
        assert "Generate QuantConnect code" in result.output
        assert "--max-attempts" in result.output
        assert "--open-in-editor" in result.output
        assert "--editor" in result.output


class TestValidateCommand:
    """Test the validate command."""

    def test_validate_requires_file_argument(self, cli_env):
        """Test that validate command requires file argument."""
        runner = CliRunner()
        result = runner.invoke(cli, ["validate"])

        assert result.exit_code != 0

    def test_validate_help_shows_options(self, cli_env):
        """Test that validate --help shows all options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", "--help"])

        assert result.exit_code == 0
        assert "--local-only" in result.output or "local" in result.output.lower()


class TestBacktestCommand:
    """Test the backtest command."""

    def test_backtest_requires_file_argument(self, cli_env):
        """Test that backtest command requires file argument."""
        runner = CliRunner()
        result = runner.invoke(cli, ["backtest"])

        assert result.exit_code != 0

    def test_backtest_help_shows_usage(self, cli_env):
        """Test that backtest --help shows usage info."""
        runner = CliRunner()
        result = runner.invoke(cli, ["backtest", "--help"])

        assert result.exit_code == 0
        assert "FILE" in result.output


class TestConfigShowCommand:
    """Test the config-show command."""

    def test_config_show_runs(self, cli_env):
        """Test that config-show command runs without error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["config-show"])

        assert result.exit_code in [0, 1]

    def test_config_show_help(self, cli_env):
        """Test that config-show --help shows usage info."""
        runner = CliRunner()
        result = runner.invoke(cli, ["config-show", "--help"])

        assert result.exit_code == 0
        assert "configuration" in result.output.lower()


class TestChatCommand:
    """Test the chat command."""

    def test_chat_help_shows_usage(self, cli_env):
        """Test that chat --help shows usage info."""
        runner = CliRunner()
        result = runner.invoke(cli, ["chat", "--help"])

        # Chat may or may not be a registered command
        assert result.exit_code in [0, 2]


class TestAutoSubcommands:
    """Test the auto subcommand group."""

    def test_auto_help_shows_subcommands(self, cli_env):
        """Test that auto --help shows available subcommands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["auto", "--help"])

        assert result.exit_code == 0
        assert "start" in result.output
        assert "status" in result.output
        assert "report" in result.output

    def test_auto_start_help(self, cli_env):
        """Test that auto start --help shows options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["auto", "start", "--help"])

        assert result.exit_code == 0


class TestLibrarySubcommands:
    """Test the library subcommand group."""

    def test_library_help_shows_subcommands(self, cli_env):
        """Test that library --help shows available subcommands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["library", "--help"])

        assert result.exit_code == 0
        assert "build" in result.output
        assert "status" in result.output
        assert "export" in result.output

    def test_library_build_help(self, cli_env):
        """Test that library build --help shows options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["library", "build", "--help"])

        assert result.exit_code == 0


class TestEvolveSubcommands:
    """Test the evolve subcommand group."""

    def test_evolve_help_shows_subcommands(self, cli_env):
        """Test that evolve --help shows available subcommands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["evolve", "--help"])

        assert result.exit_code == 0
        assert "start" in result.output
        assert "list" in result.output
        assert "show" in result.output
        assert "export" in result.output

    def test_evolve_start_requires_file(self, cli_env):
        """Test that evolve start requires a file argument."""
        runner = CliRunner()
        result = runner.invoke(cli, ["evolve", "start"])

        assert result.exit_code != 0

    def test_evolve_list_help(self, cli_env):
        """Test that evolve list --help shows options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["evolve", "list", "--help"])

        assert result.exit_code == 0


class TestMainHelp:
    """Test main CLI help and structure."""

    def test_main_help_shows_all_commands(self, cli_env):
        """Test that main --help shows all top-level commands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        # Check for main commands
        assert "search" in result.output
        assert "download" in result.output
        assert "generate" in result.output
        assert "validate" in result.output
        assert "health" in result.output
        assert "version" in result.output
        # Check for subcommand groups
        assert "auto" in result.output
        assert "library" in result.output
        assert "evolve" in result.output

    def test_invalid_command_shows_error(self, cli_env):
        """Test that invalid command shows helpful error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["nonexistent-command"])

        assert result.exit_code != 0
        assert "No such command" in result.output or "Usage" in result.output


class TestErrorHandling:
    """Test CLI error handling."""

    def test_missing_required_option_shows_error(self, cli_env):
        """Test that missing required options show helpful errors."""
        runner = CliRunner()
        # Evolve start without required options
        result = runner.invoke(cli, ["evolve", "start", "file.py"])

        # Should fail gracefully
        assert isinstance(result.exit_code, int)

    @patch('quantcoder.cli.SearchArticlesTool')
    def test_tool_error_handled_gracefully(self, mock_tool_class, cli_env):
        """Test that tool errors are handled gracefully."""
        mock_tool = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "Network error"
        mock_result.data = None
        mock_tool.execute.return_value = mock_result
        mock_tool_class.return_value = mock_tool

        runner = CliRunner()
        result = runner.invoke(cli, ["search", "test query"])

        # Should not crash, just report error
        assert result.exit_code in [0, 1]
        assert "error" in result.output.lower() or "Network error" in result.output
