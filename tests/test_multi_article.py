"""Tests for multi-article workflow with consolidated summaries."""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch

from quantcoder.core.summary_store import (
    SummaryStore,
    IndividualSummary,
    ConsolidatedSummary
)


class TestSummaryStore:
    """Tests for SummaryStore."""

    @pytest.fixture
    def store(self, tmp_path):
        """Create a temporary summary store."""
        return SummaryStore(tmp_path)

    @pytest.fixture
    def sample_individual(self):
        """Create a sample individual summary."""
        return IndividualSummary(
            article_id=1,
            title="Momentum Trading Strategies",
            authors="John Doe",
            url="https://example.com/paper1",
            strategy_type="momentum",
            key_concepts=["12-month lookback", "monthly rebalance"],
            indicators=["SMA", "RSI"],
            risk_approach="volatility targeting",
            summary_text="This paper presents a momentum strategy..."
        )

    def test_save_individual_summary(self, store, sample_individual):
        """Test saving an individual summary."""
        summary_id = store.save_individual(sample_individual)

        assert summary_id == 1
        assert store.get_summary_id_for_article(1) == 1

        # Retrieve and verify
        saved = store.get_summary(summary_id)
        assert saved is not None
        assert saved['title'] == "Momentum Trading Strategies"
        assert saved['is_consolidated'] is False

    def test_save_consolidated_summary(self, store, sample_individual):
        """Test saving a consolidated summary."""
        # First save individual summaries
        store.save_individual(sample_individual)

        individual2 = IndividualSummary(
            article_id=2,
            title="Risk Management Techniques",
            authors="Jane Smith",
            url="https://example.com/paper2",
            strategy_type="risk_management",
            key_concepts=["stop loss", "position sizing"],
            indicators=["ATR"],
            risk_approach="fixed fractional",
            summary_text="This paper presents risk management..."
        )
        store.save_individual(individual2)

        # Create consolidated
        consolidated = ConsolidatedSummary(
            summary_id=0,
            source_article_ids=[1, 2],
            references=[
                {"id": 1, "title": "Momentum Trading", "contribution": "signals"},
                {"id": 2, "title": "Risk Management", "contribution": "risk"}
            ],
            merged_strategy_type="hybrid",
            merged_description="Combined momentum and risk management",
            contributions_by_article={1: "momentum signals", 2: "risk management"},
            key_concepts=["momentum", "risk"],
            indicators=["SMA", "ATR"],
            risk_approach="Combined approach"
        )

        consolidated_id = store.save_consolidated(consolidated)

        assert consolidated_id == 3  # After 2 individual summaries
        assert store.is_consolidated(consolidated_id)

        # Retrieve and verify
        saved = store.get_summary(consolidated_id)
        assert saved is not None
        assert saved['source_article_ids'] == [1, 2]
        assert saved['is_consolidated'] is True

    def test_list_summaries(self, store, sample_individual):
        """Test listing all summaries."""
        store.save_individual(sample_individual)

        summaries = store.list_summaries()

        assert len(summaries['individual']) == 1
        assert len(summaries['consolidated']) == 0
        assert summaries['individual'][0]['article_id'] == 1

    def test_get_individual_summaries(self, store, sample_individual):
        """Test getting multiple individual summaries."""
        store.save_individual(sample_individual)

        individual2 = IndividualSummary(
            article_id=2,
            title="Paper 2",
            authors="Author",
            url="",
            strategy_type="other",
            key_concepts=[],
            indicators=[],
            risk_approach="",
            summary_text="Summary 2"
        )
        store.save_individual(individual2)

        summaries = store.get_individual_summaries([1, 2])
        assert len(summaries) == 2


class TestMultiArticleWorkflow:
    """Tests for the multi-article workflow integration."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create a mock config."""
        config = Mock()
        config.home_dir = tmp_path
        config.tools.downloads_dir = str(tmp_path / "downloads")
        config.tools.generated_code_dir = str(tmp_path / "generated")

        # Create directories
        (tmp_path / "downloads").mkdir()
        (tmp_path / "generated").mkdir()

        return config

    def test_workflow_single_article(self, mock_config, tmp_path):
        """Test workflow with single article."""
        # Create articles.json
        articles = [{"title": "Test Paper", "authors": "Author", "URL": "http://test.com"}]
        with open(tmp_path / "articles.json", 'w') as f:
            json.dump(articles, f)

        store = SummaryStore(tmp_path)

        # Simulate creating individual summary
        individual = IndividualSummary(
            article_id=1,
            title="Test Paper",
            authors="Author",
            url="http://test.com",
            strategy_type="momentum",
            key_concepts=["test"],
            indicators=["SMA"],
            risk_approach="basic",
            summary_text="Test summary"
        )
        summary_id = store.save_individual(individual)

        # Verify we can retrieve it
        summary = store.get_summary(summary_id)
        assert summary is not None
        assert summary['article_id'] == 1

    def test_workflow_multiple_articles_creates_consolidated(self, mock_config, tmp_path):
        """Test that multiple articles create a consolidated summary."""
        store = SummaryStore(tmp_path)

        # Create two individual summaries
        for i in [1, 2]:
            individual = IndividualSummary(
                article_id=i,
                title=f"Paper {i}",
                authors="Author",
                url=f"http://test{i}.com",
                strategy_type="momentum" if i == 1 else "risk_management",
                key_concepts=[f"concept{i}"],
                indicators=["SMA"] if i == 1 else ["ATR"],
                risk_approach="basic",
                summary_text=f"Summary for paper {i}"
            )
            store.save_individual(individual)

        # Create consolidated
        consolidated = ConsolidatedSummary(
            summary_id=0,
            source_article_ids=[1, 2],
            references=[
                {"id": 1, "title": "Paper 1", "contribution": "momentum"},
                {"id": 2, "title": "Paper 2", "contribution": "risk"}
            ],
            merged_strategy_type="hybrid",
            merged_description="Combined strategy",
            contributions_by_article={1: "signals", 2: "risk"},
            key_concepts=["concept1", "concept2"],
            indicators=["SMA", "ATR"],
            risk_approach="combined"
        )
        consolidated_id = store.save_consolidated(consolidated)

        # Verify
        assert consolidated_id == 3
        summaries = store.list_summaries()
        assert len(summaries['individual']) == 2
        assert len(summaries['consolidated']) == 1
        assert summaries['consolidated'][0]['source_article_ids'] == [1, 2]


class TestIndividualSummary:
    """Tests for IndividualSummary dataclass."""

    def test_to_dict(self):
        """Test conversion to dict."""
        summary = IndividualSummary(
            article_id=1,
            title="Test",
            authors="Author",
            url="http://test.com",
            strategy_type="momentum",
            key_concepts=["a", "b"],
            indicators=["SMA"],
            risk_approach="basic",
            summary_text="Summary"
        )

        d = summary.to_dict()
        assert d['article_id'] == 1
        assert d['title'] == "Test"
        assert d['key_concepts'] == ["a", "b"]

    def test_from_dict(self):
        """Test creation from dict."""
        data = {
            "article_id": 1,
            "title": "Test",
            "authors": "Author",
            "url": "http://test.com",
            "strategy_type": "momentum",
            "key_concepts": ["a"],
            "indicators": ["SMA"],
            "risk_approach": "basic",
            "summary_text": "Summary",
            "created_at": "2024-01-01T00:00:00"
        }

        summary = IndividualSummary.from_dict(data)
        assert summary.article_id == 1
        assert summary.title == "Test"


class TestConsolidatedSummary:
    """Tests for ConsolidatedSummary dataclass."""

    def test_to_dict(self):
        """Test conversion to dict."""
        summary = ConsolidatedSummary(
            summary_id=5,
            source_article_ids=[1, 2, 3],
            references=[{"id": 1, "title": "P1", "contribution": "c1"}],
            merged_strategy_type="hybrid",
            merged_description="Combined",
            contributions_by_article={1: "signals"},
            key_concepts=["a"],
            indicators=["SMA"],
            risk_approach="combined"
        )

        d = summary.to_dict()
        assert d['summary_id'] == 5
        assert d['source_article_ids'] == [1, 2, 3]
        assert d['is_consolidated'] is True
