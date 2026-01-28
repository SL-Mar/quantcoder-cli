"""Tests for the scheduler module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from pathlib import Path

from quantcoder.scheduler.notion_client import NotionClient, StrategyArticle
from quantcoder.scheduler.article_generator import ArticleGenerator, StrategyReport
from quantcoder.scheduler.runner import ScheduledRunner, ScheduleConfig, ScheduleInterval


class TestNotionClient:
    """Tests for NotionClient."""

    def test_is_configured_without_credentials(self):
        """Test is_configured returns False without credentials."""
        client = NotionClient(api_key=None, database_id=None)
        assert not client.is_configured()

    def test_is_configured_with_credentials(self):
        """Test is_configured returns True with credentials."""
        client = NotionClient(api_key="test_key", database_id="test_db")
        assert client.is_configured()

    @patch('requests.get')
    def test_test_connection_success(self, mock_get):
        """Test successful connection test."""
        mock_get.return_value.status_code = 200
        client = NotionClient(api_key="test_key", database_id="test_db")
        assert client.test_connection()

    @patch('requests.get')
    def test_test_connection_failure(self, mock_get):
        """Test failed connection test."""
        mock_get.return_value.status_code = 401
        client = NotionClient(api_key="invalid_key", database_id="test_db")
        assert not client.test_connection()


class TestStrategyArticle:
    """Tests for StrategyArticle."""

    def test_to_notion_blocks(self):
        """Test conversion to Notion blocks."""
        article = StrategyArticle(
            title="Test Strategy",
            paper_title="Test Paper",
            paper_url="https://example.com/paper",
            paper_authors=["Author 1", "Author 2"],
            strategy_summary="This is a test strategy.",
            strategy_type="momentum",
            backtest_results={
                "sharpe_ratio": 1.5,
                "total_return": 0.25,
                "max_drawdown": -0.10,
            },
            tags=["momentum", "high sharpe"],
        )

        blocks = article.to_notion_blocks()

        assert len(blocks) > 0
        # Check for callout block with paper info
        assert any(b.get("type") == "callout" for b in blocks)
        # Check for heading blocks
        assert any(b.get("type") == "heading_2" for b in blocks)


class TestArticleGenerator:
    """Tests for ArticleGenerator."""

    @pytest.fixture
    def sample_report(self):
        """Create a sample strategy report."""
        return StrategyReport(
            strategy_name="MomentumStrategy_20240101",
            paper_title="A Study of Momentum Trading",
            paper_url="https://arxiv.org/abs/1234.5678",
            paper_authors=["John Doe", "Jane Smith"],
            paper_abstract="This paper studies momentum trading strategies...",
            strategy_type="momentum",
            strategy_summary="",
            code_files={
                "Main.py": "class MomentumAlgorithm(QCAlgorithm):\n    pass",
                "Alpha.py": "class MomentumAlpha:\n    pass",
            },
            backtest_results={
                "sharpe_ratio": 1.2,
                "total_return": 0.35,
                "max_drawdown": -0.15,
            },
        )

    def test_generate_title(self, sample_report):
        """Test title generation."""
        generator = ArticleGenerator()
        title = generator.generate_title(sample_report)

        assert "Momentum" in title
        assert sample_report.strategy_name in title

    def test_generate_template_summary(self, sample_report):
        """Test template-based summary generation."""
        generator = ArticleGenerator()
        summary = generator._generate_template_summary(sample_report)

        assert len(summary) > 0
        assert "momentum" in summary.lower()
        assert "1.2" in summary or "Sharpe" in summary

    def test_generate_notion_article(self, sample_report):
        """Test Notion article generation."""
        generator = ArticleGenerator()
        article = generator.generate_notion_article(sample_report)

        assert isinstance(article, StrategyArticle)
        assert article.paper_title == sample_report.paper_title
        assert article.strategy_type == "momentum"
        assert len(article.tags) > 0

    def test_generate_markdown(self, sample_report):
        """Test markdown generation."""
        generator = ArticleGenerator()
        markdown = generator.generate_markdown(sample_report)

        assert "# " in markdown
        assert sample_report.paper_title in markdown
        assert "```python" in markdown
        assert "Sharpe Ratio" in markdown


class TestScheduleConfig:
    """Tests for ScheduleConfig."""

    def test_daily_trigger(self):
        """Test daily schedule trigger creation."""
        config = ScheduleConfig(
            interval=ScheduleInterval.DAILY,
            hour=6,
            minute=0,
        )
        trigger = config.to_trigger()
        assert trigger is not None

    def test_weekly_trigger(self):
        """Test weekly schedule trigger creation."""
        config = ScheduleConfig(
            interval=ScheduleInterval.WEEKLY,
            hour=9,
            day_of_week="mon",
        )
        trigger = config.to_trigger()
        assert trigger is not None

    def test_hourly_trigger(self):
        """Test hourly schedule trigger creation."""
        config = ScheduleConfig(interval=ScheduleInterval.HOURLY)
        trigger = config.to_trigger()
        assert trigger is not None


class TestScheduledRunner:
    """Tests for ScheduledRunner."""

    @pytest.fixture
    def mock_pipeline(self):
        """Create a mock pipeline function."""
        async def pipeline():
            return {"strategies_generated": 2, "strategies_published": 1}
        return pipeline

    def test_runner_initialization(self, mock_pipeline, tmp_path):
        """Test runner initialization."""
        runner = ScheduledRunner(
            pipeline_func=mock_pipeline,
            state_file=tmp_path / "test_state.json"
        )
        assert runner.stats.total_runs == 0
        assert not runner.running

    def test_get_status(self, mock_pipeline, tmp_path):
        """Test status retrieval."""
        runner = ScheduledRunner(
            pipeline_func=mock_pipeline,
            state_file=tmp_path / "test_state.json"
        )
        status = runner.get_status()

        assert "running" in status
        assert "stats" in status
        assert status["running"] is False

    @pytest.mark.asyncio
    async def test_run_once(self, mock_pipeline, tmp_path):
        """Test single run execution."""
        runner = ScheduledRunner(
            pipeline_func=mock_pipeline,
            state_file=tmp_path / "test_state.json"
        )
        await runner.run_once()

        assert runner.stats.total_runs == 1
        assert runner.stats.successful_runs == 1
        assert runner.stats.strategies_generated == 2
        assert runner.stats.strategies_published == 1

    @pytest.mark.asyncio
    async def test_run_with_error(self, tmp_path):
        """Test run with pipeline error."""
        async def failing_pipeline():
            raise ValueError("Test error")

        # Use a separate state file to avoid test pollution
        runner = ScheduledRunner(
            pipeline_func=failing_pipeline,
            state_file=tmp_path / "test_state.json"
        )
        await runner.run_once()

        assert runner.stats.total_runs == 1
        assert runner.stats.failed_runs == 1
        assert runner.stats.successful_runs == 0
        assert len(runner.stats.errors) == 1


class TestPipelineConfig:
    """Tests for PipelineConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        from quantcoder.scheduler.automated_pipeline import PipelineConfig

        config = PipelineConfig()

        assert len(config.search_queries) > 0
        assert config.min_sharpe_ratio == 0.5
        assert config.max_strategies_per_run == 3
        assert config.publish_to_notion is True
