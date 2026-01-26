"""Tests for the quantcoder.autonomous module."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from quantcoder.autonomous.database import (
    CompilationError,
    GeneratedStrategy,
    LearningDatabase,
    PerformancePattern,
)


class TestCompilationError:
    """Tests for CompilationError dataclass."""

    def test_create_with_defaults(self):
        """Test creating error with default values."""
        error = CompilationError(
            error_type="SyntaxError", error_message="Invalid syntax", code_snippet="def func(:"
        )
        assert error.error_type == "SyntaxError"
        assert error.fix_applied is None
        assert error.success is False
        assert error.timestamp is not None

    def test_create_with_fix(self):
        """Test creating error with fix applied."""
        error = CompilationError(
            error_type="NameError",
            error_message="Name 'foo' is not defined",
            code_snippet="print(foo)",
            fix_applied="foo = 'bar'",
            success=True,
        )
        assert error.fix_applied == "foo = 'bar'"
        assert error.success is True


class TestPerformancePattern:
    """Tests for PerformancePattern dataclass."""

    def test_create_pattern(self):
        """Test creating performance pattern."""
        pattern = PerformancePattern(
            strategy_type="momentum",
            sharpe_ratio=1.5,
            max_drawdown=-0.15,
            common_issues="Overfitting to recent data",
            success_patterns="Using longer lookback periods",
        )
        assert pattern.sharpe_ratio == 1.5
        assert pattern.max_drawdown == -0.15
        assert pattern.timestamp is not None


class TestGeneratedStrategy:
    """Tests for GeneratedStrategy dataclass."""

    def test_create_strategy(self):
        """Test creating generated strategy."""
        strategy = GeneratedStrategy(
            name="MomentumStrategy",
            category="Momentum",
            paper_source="arxiv:1234.5678",
            paper_title="Momentum Trading",
            code_files={"main.py": "class Strategy: pass"},
        )
        assert strategy.name == "MomentumStrategy"
        assert strategy.success is False
        assert strategy.sharpe_ratio is None

    def test_create_successful_strategy(self):
        """Test creating successful strategy with metrics."""
        strategy = GeneratedStrategy(
            name="ValueStrategy",
            category="Value",
            paper_source="doi:10.1234/test",
            paper_title="Value Investing",
            code_files={"main.py": "code"},
            sharpe_ratio=2.1,
            max_drawdown=-0.10,
            total_return=0.25,
            success=True,
        )
        assert strategy.sharpe_ratio == 2.1
        assert strategy.success is True


class TestLearningDatabase:
    """Tests for LearningDatabase class."""

    @pytest.fixture
    def db(self):
        """Create temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            database = LearningDatabase(db_path)
            yield database
            database.close()

    def test_init_creates_tables(self, db):
        """Test that database tables are created."""
        cursor = db.conn.cursor()

        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        assert "compilation_errors" in tables
        assert "performance_patterns" in tables
        assert "generated_strategies" in tables
        assert "successful_fixes" in tables

    def test_add_compilation_error(self, db):
        """Test adding compilation error."""
        error = CompilationError(
            error_type="SyntaxError", error_message="Invalid syntax", code_snippet="def func(:"
        )
        error_id = db.add_compilation_error(error)

        assert error_id is not None
        assert error_id > 0

    def test_get_similar_errors(self, db):
        """Test getting similar errors."""
        # Add some errors
        for i in range(3):
            error = CompilationError(
                error_type="SyntaxError",
                error_message=f"Error {i}",
                code_snippet=f"code {i}",
                fix_applied=f"fix {i}",
                success=True,
            )
            db.add_compilation_error(error)

        # Also add a different error type
        error = CompilationError(
            error_type="NameError",
            error_message="Different error",
            code_snippet="code",
            success=True,
        )
        db.add_compilation_error(error)

        similar = db.get_similar_errors("SyntaxError")
        assert len(similar) == 3
        assert all(e["error_type"] == "SyntaxError" for e in similar)

    def test_get_common_error_types(self, db):
        """Test getting common error types."""
        # Add errors of different types
        for _ in range(5):
            db.add_compilation_error(
                CompilationError(error_type="SyntaxError", error_message="msg", code_snippet="code")
            )
        for _ in range(3):
            db.add_compilation_error(
                CompilationError(error_type="NameError", error_message="msg", code_snippet="code")
            )

        common = db.get_common_error_types()
        assert len(common) >= 2
        assert common[0]["error_type"] == "SyntaxError"
        assert common[0]["count"] == 5

    def test_add_performance_pattern(self, db):
        """Test adding performance pattern."""
        pattern = PerformancePattern(
            strategy_type="momentum",
            sharpe_ratio=1.5,
            max_drawdown=-0.15,
            common_issues="issue1",
            success_patterns="pattern1",
        )
        pattern_id = db.add_performance_pattern(pattern)

        assert pattern_id is not None
        assert pattern_id > 0

    def test_get_performance_stats(self, db):
        """Test getting performance statistics."""
        # Add patterns
        for sharpe in [1.0, 1.5, 2.0]:
            db.add_performance_pattern(
                PerformancePattern(
                    strategy_type="momentum",
                    sharpe_ratio=sharpe,
                    max_drawdown=-0.10,
                    common_issues="",
                    success_patterns="",
                )
            )

        stats = db.get_performance_stats("momentum")
        assert stats["count"] == 3
        assert stats["avg_sharpe"] == 1.5
        assert stats["max_sharpe"] == 2.0
        assert stats["min_sharpe"] == 1.0

    def test_add_strategy(self, db):
        """Test adding generated strategy."""
        strategy = GeneratedStrategy(
            name="TestStrategy",
            category="Momentum",
            paper_source="arxiv:1234",
            paper_title="Test Paper",
            code_files={"main.py": "class Strategy: pass"},
        )
        strategy_id = db.add_strategy(strategy)

        assert strategy_id is not None
        assert strategy_id > 0

    def test_get_strategies_by_category(self, db):
        """Test getting strategies by category."""
        # Add strategies
        for i in range(3):
            db.add_strategy(
                GeneratedStrategy(
                    name=f"MomentumStrategy{i}",
                    category="Momentum",
                    paper_source="source",
                    paper_title="title",
                    code_files={"main.py": "code"},
                    sharpe_ratio=1.0 + i * 0.5,
                )
            )

        db.add_strategy(
            GeneratedStrategy(
                name="ValueStrategy",
                category="Value",
                paper_source="source",
                paper_title="title",
                code_files={"main.py": "code"},
            )
        )

        momentum_strategies = db.get_strategies_by_category("Momentum")
        assert len(momentum_strategies) == 3
        # Should be sorted by sharpe ratio descending
        assert momentum_strategies[0]["sharpe_ratio"] == 2.0

    def test_get_top_strategies(self, db):
        """Test getting top performing strategies."""
        for sharpe in [1.0, 2.5, 1.5]:
            db.add_strategy(
                GeneratedStrategy(
                    name="Strategy",
                    category="Test",
                    paper_source="source",
                    paper_title="title",
                    code_files={"main.py": "code"},
                    sharpe_ratio=sharpe,
                    success=True,
                )
            )

        top = db.get_top_strategies(limit=2)
        assert len(top) == 2
        assert top[0]["sharpe_ratio"] == 2.5
        assert top[1]["sharpe_ratio"] == 1.5

    def test_get_library_stats(self, db):
        """Test getting library statistics."""
        # Add strategies
        db.add_strategy(
            GeneratedStrategy(
                name="S1",
                category="Momentum",
                paper_source="",
                paper_title="",
                code_files={},
                sharpe_ratio=1.5,
                success=True,
            )
        )
        db.add_strategy(
            GeneratedStrategy(
                name="S2",
                category="Value",
                paper_source="",
                paper_title="",
                code_files={},
                sharpe_ratio=2.0,
                success=True,
            )
        )
        db.add_strategy(
            GeneratedStrategy(
                name="S3",
                category="Momentum",
                paper_source="",
                paper_title="",
                code_files={},
                success=False,
            )
        )

        stats = db.get_library_stats()
        assert stats["total_strategies"] == 3
        assert stats["successful"] == 2
        assert "categories" in stats

    def test_add_successful_fix(self, db):
        """Test adding successful fix."""
        db.add_successful_fix(
            error_pattern="undefined variable", solution_pattern="define variable before use"
        )

        fix = db.get_fix_for_error("undefined variable")
        assert fix is not None
        assert fix["solution_pattern"] == "define variable before use"
        assert fix["confidence"] == 0.5

    def test_add_successful_fix_updates_confidence(self, db):
        """Test that repeated fixes increase confidence."""
        for _ in range(3):
            db.add_successful_fix(
                error_pattern="missing import", solution_pattern="add import statement"
            )

        fix = db.get_fix_for_error("missing import")
        assert fix["confidence"] > 0.5
        assert fix["times_applied"] == 3

    def test_get_all_successful_fixes(self, db):
        """Test getting all successful fixes."""
        db.add_successful_fix("error1", "fix1")
        # Add multiple times to increase confidence
        for _ in range(5):
            db.add_successful_fix("error2", "fix2")

        fixes = db.get_all_successful_fixes(min_confidence=0.5)
        assert len(fixes) == 2

        # Higher confidence should come first
        high_confidence = db.get_all_successful_fixes(min_confidence=0.8)
        assert len(high_confidence) == 1
        assert high_confidence[0]["error_pattern"] == "error2"

    def test_context_manager(self):
        """Test database can be used as context manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            with LearningDatabase(db_path) as db:
                db.add_compilation_error(
                    CompilationError(error_type="Test", error_message="msg", code_snippet="code")
                )

            # Database should be closed after context manager
            # Reopening should work
            with LearningDatabase(db_path) as db2:
                common = db2.get_common_error_types()
                assert len(common) == 1

    def test_default_path(self):
        """Test database uses default path."""
        with patch.object(Path, "home", return_value=Path(tempfile.gettempdir())):
            db = LearningDatabase()
            assert "quantcoder" in str(db.db_path)
            assert "learnings.db" in str(db.db_path)
            db.close()
