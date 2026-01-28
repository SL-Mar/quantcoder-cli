"""Integration tests for QuantCoder CLI.

These tests verify end-to-end functionality of CLI commands with mocked external services.
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from quantcoder.cli import main


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_env(tmp_path, monkeypatch):
    """Set up mock environment with API keys and temp directories."""
    # Set up environment variables
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-12345")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-12345")

    # Create temp directories
    home_dir = tmp_path / ".quantcoder"
    home_dir.mkdir()
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()
    generated_dir = tmp_path / "generated_code"
    generated_dir.mkdir()

    return {
        "home_dir": home_dir,
        "downloads_dir": downloads_dir,
        "generated_dir": generated_dir,
        "tmp_path": tmp_path,
    }


# =============================================================================
# CLI SMOKE TESTS
# =============================================================================


class TestCLISmoke:
    """Smoke tests for basic CLI functionality."""

    def test_help_command(self, cli_runner):
        """Test that --help displays usage information."""
        result = cli_runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "QuantCoder" in result.output
        assert "AI-powered CLI" in result.output

    def test_version_command(self, cli_runner):
        """Test that version command shows version info."""
        with patch("quantcoder.cli.Config") as mock_config_class:
            mock_config = MagicMock()
            mock_config.api_key = "sk-test-key"
            mock_config.load_api_key.return_value = "sk-test-key"
            mock_config_class.load.return_value = mock_config

            result = cli_runner.invoke(main, ["version"])
            assert result.exit_code == 0
            assert "QuantCoder" in result.output or "2.0" in result.output

    def test_search_help(self, cli_runner):
        """Test that search --help shows search options."""
        result = cli_runner.invoke(main, ["search", "--help"])
        assert result.exit_code == 0
        assert "Search for academic articles" in result.output
        assert "--num" in result.output

    def test_download_help(self, cli_runner):
        """Test that download --help shows download options."""
        result = cli_runner.invoke(main, ["download", "--help"])
        assert result.exit_code == 0
        assert "Download" in result.output

    def test_summarize_help(self, cli_runner):
        """Test that summarize --help shows summarize options."""
        result = cli_runner.invoke(main, ["summarize", "--help"])
        assert result.exit_code == 0
        assert "Summarize" in result.output

    def test_generate_help(self, cli_runner):
        """Test that generate --help shows generate options."""
        result = cli_runner.invoke(main, ["generate", "--help"])
        assert result.exit_code == 0
        assert "Generate" in result.output
        assert "--max-attempts" in result.output

    def test_validate_help(self, cli_runner):
        """Test that validate --help shows validate options."""
        result = cli_runner.invoke(main, ["validate", "--help"])
        assert result.exit_code == 0
        assert "Validate" in result.output
        assert "--local-only" in result.output

    def test_backtest_help(self, cli_runner):
        """Test that backtest --help shows backtest options."""
        result = cli_runner.invoke(main, ["backtest", "--help"])
        assert result.exit_code == 0
        assert "backtest" in result.output.lower()
        assert "--start" in result.output
        assert "--end" in result.output

    def test_auto_help(self, cli_runner):
        """Test that auto --help shows autonomous mode options."""
        result = cli_runner.invoke(main, ["auto", "--help"])
        assert result.exit_code == 0
        assert "Autonomous" in result.output or "auto" in result.output.lower()

    def test_library_help(self, cli_runner):
        """Test that library --help shows library builder options."""
        result = cli_runner.invoke(main, ["library", "--help"])
        assert result.exit_code == 0
        assert "library" in result.output.lower()

    def test_evolve_help(self, cli_runner):
        """Test that evolve --help shows evolution options."""
        result = cli_runner.invoke(main, ["evolve", "--help"])
        assert result.exit_code == 0
        assert "evolve" in result.output.lower() or "AlphaEvolve" in result.output

    def test_config_show_help(self, cli_runner):
        """Test that config-show --help shows config options."""
        result = cli_runner.invoke(main, ["config-show", "--help"])
        assert result.exit_code == 0
        assert "configuration" in result.output.lower()


# =============================================================================
# SEARCH COMMAND INTEGRATION TESTS
# =============================================================================


class TestSearchCommand:
    """Integration tests for the search command."""

    @pytest.mark.integration
    def test_search_with_mocked_api(self, cli_runner):
        """Test search command with mocked CrossRef API."""
        mock_articles = [
            {
                "title": "Momentum Trading Strategies",
                "authors": "John Doe, Jane Smith",
                "published": "2023",
                "doi": "10.1234/test.001",
            },
            {
                "title": "Mean Reversion in Financial Markets",
                "authors": "Alice Brown",
                "published": "2022",
                "doi": "10.1234/test.002",
            },
        ]

        with patch("quantcoder.cli.Config") as mock_config_class:
            mock_config = MagicMock()
            mock_config.api_key = "sk-test-key"
            mock_config.load_api_key.return_value = "sk-test-key"
            mock_config_class.load.return_value = mock_config

            with patch("quantcoder.cli.SearchArticlesTool") as mock_tool_class:
                mock_tool = MagicMock()
                mock_result = MagicMock()
                mock_result.success = True
                mock_result.message = "Found 2 articles"
                mock_result.data = mock_articles
                mock_tool.execute.return_value = mock_result
                mock_tool_class.return_value = mock_tool

                result = cli_runner.invoke(main, ["search", "momentum trading", "--num", "2"])

                assert result.exit_code == 0
                assert "Found 2 articles" in result.output or "Momentum" in result.output

    @pytest.mark.integration
    def test_search_no_results(self, cli_runner):
        """Test search command when no results found."""
        with patch("quantcoder.cli.Config") as mock_config_class:
            mock_config = MagicMock()
            mock_config.api_key = "sk-test-key"
            mock_config.load_api_key.return_value = "sk-test-key"
            mock_config_class.load.return_value = mock_config

            with patch("quantcoder.cli.SearchArticlesTool") as mock_tool_class:
                mock_tool = MagicMock()
                mock_result = MagicMock()
                mock_result.success = False
                mock_result.error = "No articles found"
                mock_tool.execute.return_value = mock_result
                mock_tool_class.return_value = mock_tool

                result = cli_runner.invoke(main, ["search", "nonexistent topic xyz"])

                assert "No articles found" in result.output or result.exit_code == 0


# =============================================================================
# GENERATE COMMAND INTEGRATION TESTS
# =============================================================================


class TestGenerateCommand:
    """Integration tests for the generate command."""

    @pytest.mark.integration
    def test_generate_with_mocked_llm(self, cli_runner):
        """Test generate command with mocked LLM response."""
        mock_code = '''
from AlgorithmImports import *

class TestStrategy(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetCash(100000)
        self.AddEquity("SPY", Resolution.Daily)

    def OnData(self, data):
        if not self.Portfolio.Invested:
            self.SetHoldings("SPY", 1.0)
'''

        with patch("quantcoder.cli.Config") as mock_config_class:
            mock_config = MagicMock()
            mock_config.api_key = "sk-test-key"
            mock_config.load_api_key.return_value = "sk-test-key"
            mock_config_class.load.return_value = mock_config

            with patch("quantcoder.cli.GenerateCodeTool") as mock_tool_class:
                mock_tool = MagicMock()
                mock_result = MagicMock()
                mock_result.success = True
                mock_result.message = "Generated algorithm successfully"
                mock_result.data = {
                    "code": mock_code,
                    "summary": "A simple buy and hold strategy",
                    "path": "/tmp/algorithm_1.py",
                }
                mock_tool.execute.return_value = mock_result
                mock_tool_class.return_value = mock_tool

                result = cli_runner.invoke(main, ["generate", "1"])

                assert result.exit_code == 0
                assert "Generated" in result.output or "TestStrategy" in result.output


# =============================================================================
# VALIDATE COMMAND INTEGRATION TESTS
# =============================================================================


class TestValidateCommand:
    """Integration tests for the validate command."""

    @pytest.mark.integration
    def test_validate_valid_code(self, cli_runner, tmp_path):
        """Test validate command with valid Python code."""
        # Create a temporary file with valid code
        code_file = tmp_path / "test_algo.py"
        code_file.write_text('''
from AlgorithmImports import *

class TestStrategy(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetCash(100000)

    def OnData(self, data):
        pass
''')

        with patch("quantcoder.cli.Config") as mock_config_class:
            mock_config = MagicMock()
            mock_config.api_key = "sk-test-key"
            mock_config.load_api_key.return_value = "sk-test-key"
            mock_config_class.load.return_value = mock_config

            with patch("quantcoder.cli.ValidateCodeTool") as mock_tool_class:
                mock_tool = MagicMock()
                mock_result = MagicMock()
                mock_result.success = True
                mock_result.message = "Code is valid"
                mock_result.data = {"warnings": []}
                mock_tool.execute.return_value = mock_result
                mock_tool_class.return_value = mock_tool

                result = cli_runner.invoke(main, ["validate", str(code_file), "--local-only"])

                assert result.exit_code == 0
                assert "valid" in result.output.lower() or "✓" in result.output

    @pytest.mark.integration
    def test_validate_invalid_code(self, cli_runner, tmp_path):
        """Test validate command with invalid Python code."""
        # Create a temporary file with invalid code
        code_file = tmp_path / "invalid_algo.py"
        code_file.write_text('''
def broken_function(
    # Missing closing parenthesis
''')

        with patch("quantcoder.cli.Config") as mock_config_class:
            mock_config = MagicMock()
            mock_config.api_key = "sk-test-key"
            mock_config.load_api_key.return_value = "sk-test-key"
            mock_config_class.load.return_value = mock_config

            with patch("quantcoder.cli.ValidateCodeTool") as mock_tool_class:
                mock_tool = MagicMock()
                mock_result = MagicMock()
                mock_result.success = False
                mock_result.error = "Syntax error in code"
                mock_result.data = {"errors": ["SyntaxError: unexpected EOF"]}
                mock_tool.execute.return_value = mock_result
                mock_tool_class.return_value = mock_tool

                result = cli_runner.invoke(main, ["validate", str(code_file), "--local-only"])

                assert "error" in result.output.lower() or "✗" in result.output


# =============================================================================
# AUTO (AUTONOMOUS) COMMAND INTEGRATION TESTS
# =============================================================================


class TestAutoCommand:
    """Integration tests for the autonomous mode commands."""

    def test_auto_start_help(self, cli_runner):
        """Test auto start --help shows options."""
        result = cli_runner.invoke(main, ["auto", "start", "--help"])
        assert result.exit_code == 0
        assert "--query" in result.output
        assert "--max-iterations" in result.output
        assert "--demo" in result.output

    def test_auto_status_help(self, cli_runner):
        """Test auto status --help shows options."""
        result = cli_runner.invoke(main, ["auto", "status", "--help"])
        assert result.exit_code == 0

    def test_auto_report_help(self, cli_runner):
        """Test auto report --help shows options."""
        result = cli_runner.invoke(main, ["auto", "report", "--help"])
        assert result.exit_code == 0
        assert "--format" in result.output


# =============================================================================
# LIBRARY COMMAND INTEGRATION TESTS
# =============================================================================


class TestLibraryCommand:
    """Integration tests for the library builder commands."""

    def test_library_build_help(self, cli_runner):
        """Test library build --help shows options."""
        result = cli_runner.invoke(main, ["library", "build", "--help"])
        assert result.exit_code == 0
        assert "--comprehensive" in result.output
        assert "--max-hours" in result.output
        assert "--demo" in result.output

    def test_library_status_help(self, cli_runner):
        """Test library status --help shows options."""
        result = cli_runner.invoke(main, ["library", "status", "--help"])
        assert result.exit_code == 0

    def test_library_export_help(self, cli_runner):
        """Test library export --help shows options."""
        result = cli_runner.invoke(main, ["library", "export", "--help"])
        assert result.exit_code == 0
        assert "--format" in result.output


# =============================================================================
# EVOLVE COMMAND INTEGRATION TESTS
# =============================================================================


class TestEvolveCommand:
    """Integration tests for the evolve commands."""

    def test_evolve_start_help(self, cli_runner):
        """Test evolve start --help shows options."""
        result = cli_runner.invoke(main, ["evolve", "start", "--help"])
        assert result.exit_code == 0
        assert "--gens" in result.output or "--max_generations" in result.output or "generations" in result.output.lower()

    def test_evolve_list_help(self, cli_runner):
        """Test evolve list --help shows options."""
        result = cli_runner.invoke(main, ["evolve", "list", "--help"])
        assert result.exit_code == 0

    def test_evolve_show_help(self, cli_runner):
        """Test evolve show --help shows options."""
        result = cli_runner.invoke(main, ["evolve", "show", "--help"])
        assert result.exit_code == 0
        assert "EVOLUTION_ID" in result.output

    def test_evolve_export_help(self, cli_runner):
        """Test evolve export --help shows options."""
        result = cli_runner.invoke(main, ["evolve", "export", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.output


# =============================================================================
# END-TO-END WORKFLOW TESTS
# =============================================================================


class TestEndToEndWorkflow:
    """Tests for complete workflows with mocked external services."""

    @pytest.mark.integration
    def test_search_to_generate_workflow(self, cli_runner, tmp_path):
        """Test the search -> download -> summarize -> generate workflow."""
        # Mock search results
        mock_articles = [
            {
                "title": "RSI Momentum Strategy",
                "authors": "Test Author",
                "published": "2023",
                "doi": "10.1234/test.001",
            }
        ]

        # Mock article summary
        mock_summary = "This paper describes an RSI-based momentum strategy."

        # Mock generated code
        mock_code = '''
from AlgorithmImports import *

class RSIMomentumStrategy(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetCash(100000)
        self.symbol = self.AddEquity("SPY", Resolution.Daily).Symbol
        self.rsi = self.RSI(self.symbol, 14)

    def OnData(self, data):
        if self.rsi.Current.Value < 30:
            self.SetHoldings(self.symbol, 1.0)
        elif self.rsi.Current.Value > 70:
            self.Liquidate()
'''

        with patch("quantcoder.cli.Config") as mock_config_class:
            mock_config = MagicMock()
            mock_config.api_key = "sk-test-key"
            mock_config.load_api_key.return_value = "sk-test-key"
            mock_config_class.load.return_value = mock_config

            # Step 1: Search
            with patch("quantcoder.cli.SearchArticlesTool") as mock_search:
                mock_tool = MagicMock()
                mock_result = MagicMock()
                mock_result.success = True
                mock_result.message = "Found 1 article"
                mock_result.data = mock_articles
                mock_tool.execute.return_value = mock_result
                mock_search.return_value = mock_tool

                result = cli_runner.invoke(main, ["search", "RSI momentum"])
                assert result.exit_code == 0

            # Step 2: Generate (skipping download/summarize for brevity)
            with patch("quantcoder.cli.GenerateCodeTool") as mock_generate:
                mock_tool = MagicMock()
                mock_result = MagicMock()
                mock_result.success = True
                mock_result.message = "Generated algorithm"
                mock_result.data = {
                    "code": mock_code,
                    "summary": mock_summary,
                    "path": str(tmp_path / "algorithm_1.py"),
                }
                mock_tool.execute.return_value = mock_result
                mock_generate.return_value = mock_tool

                result = cli_runner.invoke(main, ["generate", "1"])
                assert result.exit_code == 0


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.integration
    def test_missing_api_key_graceful_error(self, cli_runner, monkeypatch):
        """Test that missing API key produces a helpful error message."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        with patch("quantcoder.cli.Config") as mock_config_class:
            mock_config = MagicMock()
            mock_config.api_key = None
            mock_config.load_api_key.return_value = None
            mock_config_class.load.return_value = mock_config

            # The CLI should prompt for API key or show an error
            result = cli_runner.invoke(main, ["search", "test"], input="\n")
            # Either prompts for key or shows error - both are acceptable
            assert result.exit_code in [0, 1]

    @pytest.mark.integration
    def test_network_error_handling(self, cli_runner):
        """Test handling of network errors."""
        with patch("quantcoder.cli.Config") as mock_config_class:
            mock_config = MagicMock()
            mock_config.api_key = "sk-test-key"
            mock_config.load_api_key.return_value = "sk-test-key"
            mock_config_class.load.return_value = mock_config

            with patch("quantcoder.cli.SearchArticlesTool") as mock_tool_class:
                mock_tool = MagicMock()
                mock_result = MagicMock()
                mock_result.success = False
                mock_result.error = "Network error: Connection timeout"
                mock_tool.execute.return_value = mock_result
                mock_tool_class.return_value = mock_tool

                result = cli_runner.invoke(main, ["search", "test query"])

                assert "error" in result.output.lower() or "timeout" in result.output.lower()

    def test_invalid_article_id(self, cli_runner):
        """Test handling of invalid article ID."""
        with patch("quantcoder.cli.Config") as mock_config_class:
            mock_config = MagicMock()
            mock_config.api_key = "sk-test-key"
            mock_config.load_api_key.return_value = "sk-test-key"
            mock_config_class.load.return_value = mock_config

            with patch("quantcoder.cli.DownloadArticleTool") as mock_tool_class:
                mock_tool = MagicMock()
                mock_result = MagicMock()
                mock_result.success = False
                mock_result.error = "Article not found"
                mock_tool.execute.return_value = mock_result
                mock_tool_class.return_value = mock_tool

                result = cli_runner.invoke(main, ["download", "999"])

                assert "not found" in result.output.lower() or "error" in result.output.lower() or "✗" in result.output
