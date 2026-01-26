"""
Performance Tests for QuantCoder CLI
====================================

Tests to measure and validate performance characteristics.
These tests establish baselines and catch performance regressions.

Run with: pytest tests/test_performance.py -v -m performance
"""

import pytest
import asyncio
import time
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import dataclass
from typing import List, Callable

# Mark all tests in this module as performance tests
pytestmark = pytest.mark.performance


@dataclass
class PerformanceResult:
    """Result from a performance measurement."""
    name: str
    iterations: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float

    def __str__(self) -> str:
        return (
            f"{self.name}: avg={self.avg_time*1000:.2f}ms, "
            f"min={self.min_time*1000:.2f}ms, max={self.max_time*1000:.2f}ms "
            f"({self.iterations} iterations)"
        )


def measure_performance(func: Callable, iterations: int = 10, warmup: int = 2) -> PerformanceResult:
    """Measure performance of a synchronous function."""
    # Warmup
    for _ in range(warmup):
        func()

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    return PerformanceResult(
        name=func.__name__,
        iterations=iterations,
        total_time=sum(times),
        avg_time=sum(times) / len(times),
        min_time=min(times),
        max_time=max(times)
    )


async def measure_async_performance(
    func: Callable,
    iterations: int = 10,
    warmup: int = 2
) -> PerformanceResult:
    """Measure performance of an async function."""
    # Warmup
    for _ in range(warmup):
        await func()

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        await func()
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    return PerformanceResult(
        name=func.__name__,
        iterations=iterations,
        total_time=sum(times),
        avg_time=sum(times) / len(times),
        min_time=min(times),
        max_time=max(times)
    )


class TestAsyncNetworkPerformance:
    """Test async network operation performance."""

    @pytest.mark.asyncio
    async def test_parallel_requests_faster_than_sequential(self):
        """Verify that parallel requests are faster than sequential."""
        import aiohttp

        async def mock_request():
            await asyncio.sleep(0.05)  # Simulate 50ms network latency
            return {"data": "result"}

        # Sequential execution
        start = time.perf_counter()
        for _ in range(5):
            await mock_request()
        sequential_time = time.perf_counter() - start

        # Parallel execution
        start = time.perf_counter()
        await asyncio.gather(*[mock_request() for _ in range(5)])
        parallel_time = time.perf_counter() - start

        # Parallel should be significantly faster (at least 3x)
        speedup = sequential_time / parallel_time
        assert speedup >= 3.0, f"Parallel speedup ({speedup:.1f}x) should be >= 3x"

    @pytest.mark.asyncio
    async def test_semaphore_rate_limiting(self):
        """Test that semaphore properly limits concurrency."""
        max_concurrent = 2
        semaphore = asyncio.Semaphore(max_concurrent)
        concurrent_count = 0
        max_observed_concurrent = 0

        async def limited_task():
            nonlocal concurrent_count, max_observed_concurrent
            async with semaphore:
                concurrent_count += 1
                max_observed_concurrent = max(max_observed_concurrent, concurrent_count)
                await asyncio.sleep(0.05)
                concurrent_count -= 1

        # Run 10 tasks with max 2 concurrent
        await asyncio.gather(*[limited_task() for _ in range(10)])

        assert max_observed_concurrent <= max_concurrent, (
            f"Concurrent count ({max_observed_concurrent}) exceeded limit ({max_concurrent})"
        )


class TestEvolutionPerformance:
    """Test evolution engine performance characteristics."""

    @pytest.fixture
    def mock_evaluator(self):
        """Create a mock evaluator for testing."""
        from quantcoder.evolver.evaluator import QCEvaluator, BacktestResult
        from quantcoder.evolver.config import EvolutionConfig

        config = EvolutionConfig(
            qc_user_id="test",
            qc_api_token="test",
            qc_project_id=1
        )
        evaluator = QCEvaluator(config)

        async def fast_evaluate(code: str, variant_id: str):
            await asyncio.sleep(0.01)  # 10ms simulated evaluation
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

        evaluator.evaluate = fast_evaluate
        return evaluator

    @pytest.mark.asyncio
    async def test_batch_evaluation_scales_with_parallelism(self, mock_evaluator):
        """Test that batch evaluation scales with parallel execution."""
        variants = [(f"v{i}", f"code_{i}") for i in range(10)]

        # Sequential evaluation
        start = time.perf_counter()
        await mock_evaluator.evaluate_batch(variants, parallel=False)
        sequential_time = time.perf_counter() - start

        # Parallel evaluation (3 concurrent)
        start = time.perf_counter()
        await mock_evaluator.evaluate_batch(variants, parallel=True, max_concurrent=3)
        parallel_time = time.perf_counter() - start

        # Parallel should be at least 2x faster
        speedup = sequential_time / parallel_time
        assert speedup >= 2.0, f"Parallel speedup ({speedup:.1f}x) should be >= 2x"

    @pytest.mark.asyncio
    async def test_evaluation_throughput(self, mock_evaluator):
        """Measure evaluation throughput (variants/second)."""
        variants = [(f"v{i}", f"code_{i}") for i in range(20)]

        start = time.perf_counter()
        results = await mock_evaluator.evaluate_batch(variants, parallel=True, max_concurrent=5)
        elapsed = time.perf_counter() - start

        throughput = len(results) / elapsed
        # Should achieve at least 10 variants/second with parallel evaluation
        assert throughput >= 10, f"Throughput ({throughput:.1f}/s) should be >= 10/s"


class TestDatabasePerformance:
    """Test database operation performance."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary database for testing."""
        from quantcoder.autonomous.database import LearningDatabase
        db_path = str(tmp_path / "perf_test.db")
        return LearningDatabase(db_path)

    def test_bulk_insert_performance(self, temp_db):
        """Test bulk insert performance."""
        def insert_batch():
            for i in range(100):
                temp_db.store_strategy(
                    query=f"test query {i}",
                    paper_title=f"Paper {i}",
                    generated_code=f"# code {i}",
                    validation_result={"valid": True},
                    backtest_result={"sharpe_ratio": 1.0 + i * 0.01},
                    success=True
                )

        result = measure_performance(insert_batch, iterations=5, warmup=1)

        # Should insert 100 records in under 500ms on average
        assert result.avg_time < 0.5, f"Bulk insert too slow: {result}"

    def test_query_performance(self, temp_db):
        """Test query performance after bulk inserts."""
        # First, populate the database
        for i in range(500):
            temp_db.store_strategy(
                query=f"momentum trading {i % 10}",
                paper_title=f"Paper {i}",
                generated_code=f"# code {i}",
                validation_result={"valid": i % 3 != 0},
                backtest_result={"sharpe_ratio": 1.0 + i * 0.01},
                success=i % 2 == 0
            )

        def query_stats():
            return temp_db.get_statistics()

        result = measure_performance(query_stats, iterations=20, warmup=3)

        # Statistics query should complete in under 50ms
        assert result.avg_time < 0.05, f"Query too slow: {result}"


class TestCodeValidationPerformance:
    """Test code validation performance."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create mock configuration."""
        config = MagicMock()
        config.home_dir = tmp_path
        config.tools.downloads_dir = "downloads"
        config.tools.generated_code_dir = "generated_code"
        config.tools.enabled_tools = ["*"]
        config.tools.disabled_tools = []
        config.ui.auto_approve = True
        return config

    def test_syntax_validation_performance(self, mock_config):
        """Test that syntax validation is fast."""
        from quantcoder.tools.code_tools import ValidateCodeTool

        valid_code = '''
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

        tool = ValidateCodeTool(mock_config)

        def validate():
            return tool.execute(code=valid_code, use_quantconnect=False)

        result = measure_performance(validate, iterations=50, warmup=5)

        # Syntax validation should be very fast (< 10ms)
        assert result.avg_time < 0.01, f"Validation too slow: {result}"


class TestPathSecurityPerformance:
    """Test path security validation performance."""

    def test_path_validation_performance(self, tmp_path):
        """Test that path validation is fast."""
        from quantcoder.tools.base import get_safe_path, validate_path_within_directory

        base_dir = tmp_path / "test_dir"
        base_dir.mkdir()

        def validate_paths():
            # Test various path validations
            for i in range(100):
                get_safe_path(base_dir, f"subdir_{i % 10}", f"file_{i}.txt")

        result = measure_performance(validate_paths, iterations=20, warmup=2)

        # 100 path validations should complete in under 50ms
        assert result.avg_time < 0.05, f"Path validation too slow: {result}"


class TestMemoryUsage:
    """Test memory usage characteristics."""

    def test_large_code_processing_memory(self):
        """Test memory usage when processing large code files."""
        import sys

        # Generate a large code string (100KB)
        large_code = "# " + "x" * 100_000

        initial_size = sys.getsizeof(large_code)

        # Process the code multiple times
        processed_codes = []
        for _ in range(10):
            processed_codes.append(large_code.strip())

        # Memory should not grow excessively
        total_size = sum(sys.getsizeof(c) for c in processed_codes)

        # Due to string interning, should not be 10x the initial size
        # Allow for some overhead but not linear growth
        assert total_size < initial_size * 5, "Memory usage grew excessively"


class TestConfigLoadPerformance:
    """Test configuration loading performance."""

    def test_config_load_performance(self, tmp_path, monkeypatch):
        """Test that configuration loads quickly."""
        from quantcoder.config import Config

        # Set up test environment
        monkeypatch.setenv("HOME", str(tmp_path))

        def load_config():
            return Config(home_dir=tmp_path / ".quantcoder")

        result = measure_performance(load_config, iterations=20, warmup=3)

        # Config should load in under 50ms
        assert result.avg_time < 0.05, f"Config load too slow: {result}"


class TestConcurrencyLimits:
    """Test behavior under high concurrency."""

    @pytest.mark.asyncio
    async def test_high_concurrency_stability(self):
        """Test system stability under high concurrency."""
        semaphore = asyncio.Semaphore(10)
        completed = 0
        errors = 0

        async def task():
            nonlocal completed, errors
            try:
                async with semaphore:
                    await asyncio.sleep(0.01)
                    completed += 1
            except Exception:
                errors += 1

        # Run 1000 concurrent tasks
        await asyncio.gather(*[task() for _ in range(1000)])

        assert completed == 1000, f"Only {completed}/1000 tasks completed"
        assert errors == 0, f"{errors} errors occurred"

    @pytest.mark.asyncio
    async def test_timeout_handling_performance(self):
        """Test that timeout handling doesn't block."""
        async def slow_task():
            await asyncio.sleep(10)  # Would take 10s without timeout

        start = time.perf_counter()
        try:
            await asyncio.wait_for(slow_task(), timeout=0.1)
        except asyncio.TimeoutError:
            pass
        elapsed = time.perf_counter() - start

        # Should timeout quickly, not wait the full 10s
        assert elapsed < 0.2, f"Timeout took too long: {elapsed}s"
