"""Learning database for storing errors, fixes, and performance patterns."""

import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import json


@dataclass
class CompilationError:
    """Represents a compilation error and its solution."""
    error_type: str
    error_message: str
    code_snippet: str
    fix_applied: Optional[str] = None
    success: bool = False
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class PerformancePattern:
    """Represents a performance pattern observation."""
    strategy_type: str
    sharpe_ratio: float
    max_drawdown: float
    common_issues: str
    success_patterns: str
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class GeneratedStrategy:
    """Represents a generated strategy with metadata."""
    name: str
    category: str
    paper_source: str
    paper_title: str
    code_files: Dict[str, str]  # filename -> content
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    total_return: Optional[float] = None
    compilation_errors: int = 0
    refinement_attempts: int = 0
    success: bool = False
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class LearningDatabase:
    """SQLite database for storing learnings from autonomous mode."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database connection."""
        if db_path is None:
            db_path = Path.home() / ".quantcoder" / "learnings.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()

        # Compilation errors table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compilation_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                code_snippet TEXT,
                fix_applied TEXT,
                success BOOLEAN DEFAULT 0,
                timestamp TEXT NOT NULL
            )
        """)

        # Performance patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_type TEXT NOT NULL,
                sharpe_ratio REAL NOT NULL,
                max_drawdown REAL,
                common_issues TEXT,
                success_patterns TEXT,
                timestamp TEXT NOT NULL
            )
        """)

        # Generated strategies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generated_strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                paper_source TEXT,
                paper_title TEXT,
                code_files TEXT NOT NULL,  -- JSON serialized
                sharpe_ratio REAL,
                max_drawdown REAL,
                total_return REAL,
                compilation_errors INTEGER DEFAULT 0,
                refinement_attempts INTEGER DEFAULT 0,
                success BOOLEAN DEFAULT 0,
                timestamp TEXT NOT NULL
            )
        """)

        # Successful fixes table (for quick lookup)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS successful_fixes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_pattern TEXT NOT NULL,
                solution_pattern TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                times_applied INTEGER DEFAULT 1,
                success_count INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL,
                UNIQUE(error_pattern, solution_pattern)
            )
        """)

        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_error_type
            ON compilation_errors(error_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_strategy_category
            ON generated_strategies(category)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_success_fixes_pattern
            ON successful_fixes(error_pattern)
        """)

        self.conn.commit()

    # Compilation Errors
    def add_compilation_error(self, error: CompilationError):
        """Store a compilation error."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO compilation_errors
            (error_type, error_message, code_snippet, fix_applied, success, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            error.error_type,
            error.error_message,
            error.code_snippet,
            error.fix_applied,
            error.success,
            error.timestamp
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_similar_errors(self, error_type: str, limit: int = 10) -> List[Dict]:
        """Get similar errors that were successfully fixed."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM compilation_errors
            WHERE error_type = ? AND success = 1
            ORDER BY timestamp DESC
            LIMIT ?
        """, (error_type, limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_common_error_types(self, limit: int = 10) -> List[Dict]:
        """Get most common error types."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT error_type, COUNT(*) as count,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as fixed_count
            FROM compilation_errors
            GROUP BY error_type
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    # Performance Patterns
    def add_performance_pattern(self, pattern: PerformancePattern):
        """Store a performance pattern."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO performance_patterns
            (strategy_type, sharpe_ratio, max_drawdown, common_issues,
             success_patterns, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            pattern.strategy_type,
            pattern.sharpe_ratio,
            pattern.max_drawdown,
            pattern.common_issues,
            pattern.success_patterns,
            pattern.timestamp
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_performance_stats(self, strategy_type: str) -> Dict:
        """Get performance statistics for a strategy type."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                AVG(sharpe_ratio) as avg_sharpe,
                MAX(sharpe_ratio) as max_sharpe,
                MIN(sharpe_ratio) as min_sharpe,
                AVG(max_drawdown) as avg_drawdown,
                COUNT(*) as count
            FROM performance_patterns
            WHERE strategy_type = ?
        """, (strategy_type,))
        result = cursor.fetchone()
        return dict(result) if result else {}

    # Generated Strategies
    def add_strategy(self, strategy: GeneratedStrategy):
        """Store a generated strategy."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO generated_strategies
            (name, category, paper_source, paper_title, code_files,
             sharpe_ratio, max_drawdown, total_return, compilation_errors,
             refinement_attempts, success, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            strategy.name,
            strategy.category,
            strategy.paper_source,
            strategy.paper_title,
            json.dumps(strategy.code_files),
            strategy.sharpe_ratio,
            strategy.max_drawdown,
            strategy.total_return,
            strategy.compilation_errors,
            strategy.refinement_attempts,
            strategy.success,
            strategy.timestamp
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_strategies_by_category(self, category: str) -> List[Dict]:
        """Get all strategies in a category."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM generated_strategies
            WHERE category = ?
            ORDER BY sharpe_ratio DESC
        """, (category,))
        strategies = []
        for row in cursor.fetchall():
            strategy = dict(row)
            strategy['code_files'] = json.loads(strategy['code_files'])
            strategies.append(strategy)
        return strategies

    def get_top_strategies(self, limit: int = 10) -> List[Dict]:
        """Get top performing strategies."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM generated_strategies
            WHERE success = 1 AND sharpe_ratio IS NOT NULL
            ORDER BY sharpe_ratio DESC
            LIMIT ?
        """, (limit,))
        strategies = []
        for row in cursor.fetchall():
            strategy = dict(row)
            strategy['code_files'] = json.loads(strategy['code_files'])
            strategies.append(strategy)
        return strategies

    def get_library_stats(self) -> Dict:
        """Get overall library statistics."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) as total_strategies,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                AVG(sharpe_ratio) as avg_sharpe,
                AVG(compilation_errors) as avg_errors,
                AVG(refinement_attempts) as avg_refinements
            FROM generated_strategies
        """)
        result = cursor.fetchone()

        # Get category breakdown
        cursor.execute("""
            SELECT category, COUNT(*) as count,
                   AVG(sharpe_ratio) as avg_sharpe
            FROM generated_strategies
            WHERE success = 1
            GROUP BY category
            ORDER BY count DESC
        """)
        categories = [dict(row) for row in cursor.fetchall()]

        stats = dict(result) if result else {}
        stats['categories'] = categories
        return stats

    # Successful Fixes
    def add_successful_fix(self, error_pattern: str, solution_pattern: str):
        """Add or update a successful fix pattern."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO successful_fixes
            (error_pattern, solution_pattern, confidence, times_applied,
             success_count, timestamp)
            VALUES (?, ?, 0.5, 1, 1, ?)
            ON CONFLICT(error_pattern, solution_pattern) DO UPDATE SET
                times_applied = times_applied + 1,
                success_count = success_count + 1,
                confidence = MIN(0.99, confidence + 0.1)
        """, (error_pattern, solution_pattern, datetime.now().isoformat()))
        self.conn.commit()

    def get_fix_for_error(self, error_pattern: str) -> Optional[Dict]:
        """Get the best fix for an error pattern."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM successful_fixes
            WHERE error_pattern = ?
            ORDER BY confidence DESC, success_count DESC
            LIMIT 1
        """, (error_pattern,))
        result = cursor.fetchone()
        return dict(result) if result else None

    def get_all_successful_fixes(self, min_confidence: float = 0.5) -> List[Dict]:
        """Get all successful fixes above confidence threshold."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM successful_fixes
            WHERE confidence >= ?
            ORDER BY confidence DESC, success_count DESC
        """, (min_confidence,))
        return [dict(row) for row in cursor.fetchall()]

    # Utility
    def close(self):
        """Close database connection."""
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
