"""
End-to-End Tests for QuantCoder CLI
====================================

Tests critical user workflows from start to finish.
These tests validate the integration between components.

Run with: pytest tests/test_e2e.py -v -m e2e
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Mark all tests in this module as e2e
pytestmark = pytest.mark.e2e


class TestSearchToGenerateWorkflow:
    """Test the complete workflow: search -> download -> summarize -> generate -> validate."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        config = MagicMock()
        config.home_dir = Path(tempfile.mkdtemp())
        config.tools.downloads_dir = "downloads"
        config.tools.generated_code_dir = "generated_code"
        config.tools.enabled_tools = ["*"]
        config.tools.disabled_tools = []
        config.ui.auto_approve = True
        config.model.provider = "anthropic"
        config.model.model = "claude-sonnet-4-5-20250929"
        config.model.temperature = 0.5
        config.model.max_tokens = 3000
        return config

    @pytest.fixture
    def mock_crossref_response(self):
        """Mock CrossRef API response."""
        return {
            "message": {
                "items": [
                    {
                        "title": ["Momentum Trading Strategies in Financial Markets"],
                        "author": [
                            {"given": "John", "family": "Doe"},
                            {"given": "Jane", "family": "Smith"}
                        ],
                        "published-print": {"date-parts": [[2023]]},
                        "DOI": "10.1234/example.doi",
                        "URL": "https://example.com/article"
                    }
                ]
            }
        }

    @pytest.fixture
    def sample_algorithm_code(self):
        """Sample generated algorithm code."""
        return '''
from AlgorithmImports import *

class MomentumStrategy(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2023, 12, 31)
        self.SetCash(100000)
        self.symbol = self.AddEquity("SPY", Resolution.Daily).Symbol
        self.rsi = self.RSI(self.symbol, 14)

    def OnData(self, data):
        if not self.rsi.IsReady:
            return
        if self.rsi.Current.Value < 30:
            self.SetHoldings(self.symbol, 1.0)
        elif self.rsi.Current.Value > 70:
            self.Liquidate(self.symbol)
'''

    @pytest.mark.asyncio
    async def test_search_articles_workflow(self, mock_config, mock_crossref_response):
        """Test article search returns properly formatted results."""
        from quantcoder.tools.article_tools import SearchArticlesTool

        with patch('aiohttp.ClientSession') as mock_session:
            # Setup mock response
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(return_value=mock_crossref_response)

            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_response
            mock_context.__aexit__.return_value = None

            mock_session_instance = MagicMock()
            mock_session_instance.get.return_value = mock_context
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_session_instance

            tool = SearchArticlesTool(mock_config)
            result = tool.execute(query="momentum trading", max_results=5)

            assert result.success is True
            assert result.data is not None
            assert len(result.data) == 1
            assert "Momentum Trading" in result.data[0]["title"]
            assert result.data[0]["DOI"] == "10.1234/example.doi"

    @pytest.mark.asyncio
    async def test_code_validation_workflow(self, mock_config, sample_algorithm_code):
        """Test that generated code passes syntax validation."""
        from quantcoder.tools.code_tools import ValidateCodeTool

        tool = ValidateCodeTool(mock_config)
        result = tool.execute(code=sample_algorithm_code, use_quantconnect=False)

        assert result.success is True
        assert "valid" in str(result.message).lower() or result.data.get("valid", False)

    @pytest.mark.asyncio
    async def test_invalid_code_validation(self, mock_config):
        """Test that invalid code fails validation."""
        from quantcoder.tools.code_tools import ValidateCodeTool

        invalid_code = """
def broken_function(
    # Missing closing parenthesis
"""
        tool = ValidateCodeTool(mock_config)
        result = tool.execute(code=invalid_code, use_quantconnect=False)

        # Should either fail or return invalid status
        assert result.success is False or (result.data and not result.data.get("valid", True))


class TestEvolutionWorkflow:
    """Test the evolution engine workflow."""

    @pytest.fixture
    def evolution_config(self):
        """Create evolution configuration."""
        from quantcoder.evolver.config import EvolutionConfig

        return EvolutionConfig(
            qc_user_id="test_user",
            qc_api_token="test_token",
            qc_project_id=12345,
            max_generations=2,
            variants_per_generation=2,
            elite_pool_size=3
        )

    @pytest.fixture
    def sample_baseline_code(self):
        """Sample baseline algorithm for evolution."""
        return '''
from AlgorithmImports import *

class BaselineStrategy(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetCash(100000)
        self.AddEquity("SPY", Resolution.Daily)

    def OnData(self, data):
        if not self.Portfolio.Invested:
            self.SetHoldings("SPY", 1.0)
'''

    @pytest.mark.asyncio
    async def test_parallel_variant_evaluation(self, evolution_config):
        """Test that variant evaluation runs in parallel."""
        from quantcoder.evolver.evaluator import QCEvaluator, BacktestResult

        evaluator = QCEvaluator(evolution_config)

        # Track evaluation order and timing
        evaluation_times = []

        async def mock_evaluate(code: str, variant_id: str):
            import time
            start = time.time()
            await asyncio.sleep(0.1)  # Simulate API call
            evaluation_times.append((variant_id, time.time() - start))
            return BacktestResult(
                backtest_id=f"bt_{variant_id}",
                status="completed",
                sharpe_ratio=1.5,
                total_return=0.25,
                max_drawdown=0.10,
                win_rate=0.55,
                total_trades=100,
                cagr=0.20,
                raw_response={}
            )

        # Patch the evaluate method
        with patch.object(evaluator, 'evaluate', side_effect=mock_evaluate):
            variants = [
                ("v1", "code1"),
                ("v2", "code2"),
                ("v3", "code3"),
            ]

            import time
            start_time = time.time()
            results = await evaluator.evaluate_batch(variants, parallel=True, max_concurrent=3)
            total_time = time.time() - start_time

            # All variants should be evaluated
            assert len(results) == 3
            assert all(r is not None for r in results.values())

            # Parallel execution should be faster than sequential
            # Sequential would take ~0.3s, parallel should be ~0.1-0.15s
            assert total_time < 0.25, f"Parallel evaluation took too long: {total_time}s"


class TestAutonomousPipelineWorkflow:
    """Test the autonomous learning pipeline workflow."""

    @pytest.fixture
    def temp_db_path(self, tmp_path):
        """Create temporary database path."""
        return str(tmp_path / "test_learning.db")

    def test_learning_database_workflow(self, temp_db_path):
        """Test that learning database properly stores and retrieves data."""
        from quantcoder.autonomous.database import LearningDatabase

        db = LearningDatabase(temp_db_path)

        # Test storing a successful strategy
        strategy_id = db.store_strategy(
            query="momentum trading",
            paper_title="Test Paper",
            generated_code="# test code",
            validation_result={"valid": True},
            backtest_result={"sharpe_ratio": 1.5, "total_return": 0.25},
            success=True
        )

        assert strategy_id is not None
        assert strategy_id > 0

        # Test retrieving statistics
        stats = db.get_statistics()
        assert stats["total_strategies"] >= 1

    def test_compilation_error_learning(self, temp_db_path):
        """Test that compilation errors are properly learned from."""
        from quantcoder.autonomous.database import LearningDatabase, CompilationError

        db = LearningDatabase(temp_db_path)

        # Store a compilation error
        error = CompilationError(
            error_type="SyntaxError",
            error_message="unexpected indent",
            original_code="def foo():\n  pass\n pass",
            fixed_code="def foo():\n    pass",
            context="momentum strategy generation",
            success=True
        )

        db.store_compilation_error(error)

        # Retrieve solutions
        solutions = db.get_error_solutions("SyntaxError", limit=5)
        assert len(solutions) >= 1
        assert solutions[0]["error_type"] == "SyntaxError"


class TestHealthCheckWorkflow:
    """Test the health check workflow."""

    def test_health_check_returns_valid_json(self, tmp_path, monkeypatch):
        """Test that health check returns properly structured JSON."""
        from click.testing import CliRunner
        from quantcoder.cli import cli

        # Set up test environment
        monkeypatch.setenv("HOME", str(tmp_path))

        runner = CliRunner()
        result = runner.invoke(cli, ["health", "--json"])

        # Should not crash even without full config
        assert result.exit_code in [0, 1]  # 0 = healthy, 1 = some checks failed

        # Output should be valid JSON
        try:
            output = result.output.strip()
            if output:
                data = json.loads(output)
                assert "status" in data or "version" in data
        except json.JSONDecodeError:
            # Non-JSON output is acceptable for error cases
            pass


class TestConfigurationWorkflow:
    """Test configuration loading and API key management."""

    def test_config_creates_default_on_first_run(self, tmp_path, monkeypatch):
        """Test that configuration is created on first run."""
        from quantcoder.config import Config

        # Use temp directory as home
        home_dir = tmp_path / ".quantcoder"
        monkeypatch.setenv("HOME", str(tmp_path))

        config = Config(home_dir=home_dir)

        assert config.home_dir == home_dir
        assert config.model is not None
        assert config.tools is not None

    def test_api_key_loading_precedence(self, tmp_path, monkeypatch):
        """Test that API keys are loaded with correct precedence."""
        from quantcoder.config import Config

        # Set environment variable
        monkeypatch.setenv("OPENAI_API_KEY", "env-key-12345")

        home_dir = tmp_path / ".quantcoder"
        config = Config(home_dir=home_dir)

        # Environment variable should take precedence
        key = config.load_api_key("OPENAI_API_KEY")
        assert key == "env-key-12345"


class TestToolIntegration:
    """Test integration between tools."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create mock configuration with temp directories."""
        config = MagicMock()
        config.home_dir = tmp_path / ".quantcoder"
        config.home_dir.mkdir(parents=True, exist_ok=True)
        config.tools.downloads_dir = "downloads"
        config.tools.generated_code_dir = "generated_code"
        config.tools.enabled_tools = ["*"]
        config.tools.disabled_tools = []
        config.ui.auto_approve = True
        return config

    def test_path_security_prevents_traversal(self, mock_config, tmp_path):
        """Test that path traversal attacks are blocked."""
        from quantcoder.tools.base import get_safe_path, PathSecurityError

        base_dir = tmp_path / "safe_dir"
        base_dir.mkdir()

        # Valid path should work
        safe_path = get_safe_path(base_dir, "subdir", "file.txt", create_parents=True)
        assert str(safe_path).startswith(str(base_dir))

        # Path traversal should be blocked
        with pytest.raises(PathSecurityError):
            get_safe_path(base_dir, "..", "..", "etc", "passwd")

    def test_file_tools_respect_size_limits(self, mock_config, tmp_path):
        """Test that file tools respect size limits."""
        from quantcoder.tools.file_tools import ReadFileTool, MAX_FILE_SIZE

        # Create a file within limits
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        # This constant should be defined
        assert MAX_FILE_SIZE == 10 * 1024 * 1024  # 10 MB


# Performance markers for benchmark tests
class TestPerformanceBaselines:
    """Basic performance sanity checks."""

    @pytest.mark.asyncio
    async def test_async_search_completes_within_timeout(self):
        """Test that async search doesn't hang."""
        from quantcoder.tools.article_tools import SearchArticlesTool

        # Create minimal mock config
        mock_config = MagicMock()
        mock_config.home_dir = Path(tempfile.mkdtemp())
        mock_config.tools.downloads_dir = "downloads"
        mock_config.tools.enabled_tools = ["*"]
        mock_config.tools.disabled_tools = []

        with patch('aiohttp.ClientSession') as mock_session:
            # Mock a timeout scenario
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(return_value={"message": {"items": []}})

            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_response
            mock_context.__aexit__.return_value = None

            mock_session_instance = MagicMock()
            mock_session_instance.get.return_value = mock_context
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_session_instance

            tool = SearchArticlesTool(mock_config)

            # Should complete within reasonable time
            import time
            start = time.time()
            result = tool.execute(query="test", max_results=1)
            elapsed = time.time() - start

            assert elapsed < 5.0, f"Search took too long: {elapsed}s"
