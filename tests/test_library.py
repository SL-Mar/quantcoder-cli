"""Tests for the quantcoder.library module."""

import pytest
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from quantcoder.library.coverage import CategoryProgress, CoverageTracker
from quantcoder.library.taxonomy import (
    StrategyCategory,
    STRATEGY_TAXONOMY,
    get_total_strategies_needed,
    get_categories_by_priority,
    get_all_queries,
)


class TestStrategyCategory:
    """Tests for StrategyCategory dataclass."""

    def test_create_category(self):
        """Test creating a strategy category."""
        category = StrategyCategory(
            name="test_category",
            queries=["query1", "query2"],
            min_strategies=5,
            priority="high",
            description="Test description"
        )

        assert category.name == "test_category"
        assert len(category.queries) == 2
        assert category.min_strategies == 5
        assert category.priority == "high"


class TestStrategyTaxonomy:
    """Tests for strategy taxonomy configuration."""

    def test_taxonomy_not_empty(self):
        """Test that taxonomy has categories defined."""
        assert len(STRATEGY_TAXONOMY) > 0

    def test_taxonomy_categories_valid(self):
        """Test that all taxonomy categories have required fields."""
        for name, category in STRATEGY_TAXONOMY.items():
            assert category.name == name
            assert len(category.queries) > 0
            assert category.min_strategies > 0
            assert category.priority in ["high", "medium", "low"]
            assert len(category.description) > 0

    def test_high_priority_categories_exist(self):
        """Test that high priority categories exist."""
        high_priority = get_categories_by_priority("high")
        assert len(high_priority) > 0

    def test_get_total_strategies_needed(self):
        """Test calculating total strategies needed."""
        total = get_total_strategies_needed()
        assert total > 0

        # Should equal sum of min_strategies
        expected = sum(cat.min_strategies for cat in STRATEGY_TAXONOMY.values())
        assert total == expected

    def test_get_categories_by_priority(self):
        """Test filtering categories by priority."""
        high = get_categories_by_priority("high")
        medium = get_categories_by_priority("medium")
        low = get_categories_by_priority("low")

        # All returned categories should have matching priority
        for name, cat in high.items():
            assert cat.priority == "high"
        for name, cat in medium.items():
            assert cat.priority == "medium"
        for name, cat in low.items():
            assert cat.priority == "low"

    def test_get_all_queries(self):
        """Test getting all search queries."""
        queries = get_all_queries()
        assert len(queries) > 0

        # Should contain queries from multiple categories
        total_queries = sum(len(cat.queries) for cat in STRATEGY_TAXONOMY.values())
        assert len(queries) == total_queries


class TestCategoryProgress:
    """Tests for CategoryProgress dataclass."""

    def test_create_progress(self):
        """Test creating category progress."""
        progress = CategoryProgress(
            category="momentum",
            target=10
        )

        assert progress.category == "momentum"
        assert progress.target == 10
        assert progress.completed == 0
        assert progress.failed == 0
        assert progress.avg_sharpe == 0.0

    def test_progress_pct(self):
        """Test progress percentage calculation."""
        progress = CategoryProgress(category="test", target=10, completed=5)
        assert progress.progress_pct == 50.0

    def test_progress_pct_zero_target(self):
        """Test progress percentage with zero target."""
        progress = CategoryProgress(category="test", target=0)
        assert progress.progress_pct == 0

    def test_is_complete(self):
        """Test completion check."""
        progress = CategoryProgress(category="test", target=5)
        assert progress.is_complete is False

        progress.completed = 5
        assert progress.is_complete is True

        progress.completed = 6  # Over target
        assert progress.is_complete is True

    def test_elapsed_hours(self):
        """Test elapsed time calculation."""
        progress = CategoryProgress(category="test", target=5)

        # Elapsed time should be very small
        assert progress.elapsed_hours >= 0
        assert progress.elapsed_hours < 0.01  # Less than ~36 seconds


class TestCoverageTracker:
    """Tests for CoverageTracker class."""

    def test_init(self):
        """Test tracker initialization."""
        tracker = CoverageTracker()

        # Should have categories from taxonomy
        assert len(tracker.categories) == len(STRATEGY_TAXONOMY)

        # Each category should be initialized
        for name in STRATEGY_TAXONOMY.keys():
            assert name in tracker.categories
            assert tracker.categories[name].completed == 0

    def test_update_success(self):
        """Test updating progress with success."""
        tracker = CoverageTracker()
        category = list(STRATEGY_TAXONOMY.keys())[0]

        tracker.update(category, success=True, sharpe=1.5)

        assert tracker.categories[category].completed == 1
        assert tracker.categories[category].avg_sharpe == 1.5
        assert tracker.categories[category].best_sharpe == 1.5

    def test_update_failure(self):
        """Test updating progress with failure."""
        tracker = CoverageTracker()
        category = list(STRATEGY_TAXONOMY.keys())[0]

        tracker.update(category, success=False)

        assert tracker.categories[category].completed == 0
        assert tracker.categories[category].failed == 1

    def test_update_sharpe_averaging(self):
        """Test that Sharpe ratio is properly averaged."""
        tracker = CoverageTracker()
        category = list(STRATEGY_TAXONOMY.keys())[0]

        tracker.update(category, success=True, sharpe=1.0)
        tracker.update(category, success=True, sharpe=2.0)
        tracker.update(category, success=True, sharpe=3.0)

        assert tracker.categories[category].avg_sharpe == pytest.approx(2.0)
        assert tracker.categories[category].best_sharpe == 3.0

    def test_update_unknown_category(self):
        """Test updating unknown category does nothing."""
        tracker = CoverageTracker()

        # Should not raise error
        tracker.update("nonexistent_category", success=True)

    def test_get_progress_pct(self):
        """Test overall progress calculation."""
        tracker = CoverageTracker()

        # Initially 0%
        assert tracker.get_progress_pct() == 0

        # Update some categories
        categories = list(STRATEGY_TAXONOMY.keys())[:2]
        for cat in categories:
            for _ in range(tracker.categories[cat].target):
                tracker.update(cat, success=True, sharpe=1.0)

        # Should have some progress
        assert tracker.get_progress_pct() > 0

    def test_get_completed_categories(self):
        """Test counting completed categories."""
        tracker = CoverageTracker()

        assert tracker.get_completed_categories() == 0

        # Complete one category
        cat = list(STRATEGY_TAXONOMY.keys())[0]
        for _ in range(tracker.categories[cat].target):
            tracker.update(cat, success=True)

        assert tracker.get_completed_categories() == 1

    def test_get_total_strategies(self):
        """Test total strategies count."""
        tracker = CoverageTracker()

        assert tracker.get_total_strategies() == 0

        # Add some strategies
        tracker.update("momentum", success=True)
        tracker.update("momentum", success=True)
        tracker.update("mean_reversion", success=True)

        assert tracker.get_total_strategies() == 3

    def test_get_elapsed_hours(self):
        """Test elapsed time tracking."""
        tracker = CoverageTracker()

        elapsed = tracker.get_elapsed_hours()
        assert elapsed >= 0
        assert elapsed < 0.01  # Very small time

    def test_estimate_time_remaining(self):
        """Test time remaining estimation."""
        tracker = CoverageTracker()

        # No progress, no estimate
        assert tracker.estimate_time_remaining() == 0.0

    def test_get_progress_bar(self):
        """Test progress bar generation."""
        tracker = CoverageTracker()
        category = list(STRATEGY_TAXONOMY.keys())[0]

        bar = tracker.get_progress_bar(category)
        assert "░" in bar or "█" in bar
        assert "%" in bar

    def test_get_progress_bar_unknown_category(self):
        """Test progress bar for unknown category."""
        tracker = CoverageTracker()
        bar = tracker.get_progress_bar("nonexistent")
        assert bar == ""

    def test_get_progress_bar_complete(self):
        """Test progress bar shows completion mark."""
        tracker = CoverageTracker()
        category = list(STRATEGY_TAXONOMY.keys())[0]

        # Complete the category
        for _ in range(tracker.categories[category].target):
            tracker.update(category, success=True)

        bar = tracker.get_progress_bar(category)
        assert "✓" in bar

    def test_get_status_report(self):
        """Test getting status report."""
        tracker = CoverageTracker()

        # Add some progress
        tracker.update("momentum", success=True, sharpe=1.5)
        tracker.update("momentum", success=True, sharpe=2.0)

        report = tracker.get_status_report()

        assert "total_strategies" in report
        assert report["total_strategies"] == 2
        assert "progress_pct" in report
        assert "categories" in report
        assert "momentum" in report["categories"]
        assert report["categories"]["momentum"]["completed"] == 2

    def test_save_checkpoint(self):
        """Test saving checkpoint."""
        tracker = CoverageTracker()
        tracker.update("momentum", success=True, sharpe=1.5)

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            tracker.save_checkpoint(f.name)

            # Read and verify
            with open(f.name, 'r') as rf:
                data = json.load(rf)

            assert data["total_strategies"] == 1
            assert "categories" in data

            Path(f.name).unlink()

    def test_load_checkpoint(self):
        """Test loading checkpoint."""
        tracker = CoverageTracker()
        tracker.update("momentum", success=True, sharpe=1.5)
        tracker.update("momentum", success=True, sharpe=2.5)

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            tracker.save_checkpoint(f.name)

            # Load into new tracker
            loaded = CoverageTracker.load_checkpoint(f.name)

            assert loaded.categories["momentum"].completed == 2
            assert loaded.categories["momentum"].avg_sharpe == pytest.approx(2.0)
            assert loaded.categories["momentum"].best_sharpe == 2.5

            Path(f.name).unlink()

    def test_display_progress(self):
        """Test that display_progress doesn't error."""
        tracker = CoverageTracker()
        tracker.update("momentum", success=True, sharpe=1.0)

        # Should not raise an error (captures console output)
        with patch('quantcoder.library.coverage.console.print'):
            tracker.display_progress()
