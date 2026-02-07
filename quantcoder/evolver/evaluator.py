"""
QuantConnect Evaluator
======================

Handles backtesting of algorithm variants via QuantConnect API.
Parses results and calculates fitness scores.

Uses the shared QuantConnectMCPClient for correct API auth and endpoints.
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .config import EvolutionConfig


@dataclass
class BacktestResult:
    """Parsed backtest results."""
    backtest_id: str
    status: str  # completed, failed, running
    sharpe_ratio: float
    total_return: float  # as decimal (0.25 = 25%)
    max_drawdown: float  # as decimal (0.15 = 15%)
    win_rate: float  # as decimal
    total_trades: int
    cagr: float
    raw_response: Dict[str, Any]

    def to_metrics_dict(self) -> Dict[str, float]:
        """Convert to metrics dict for fitness calculation."""
        return {
            'sharpe_ratio': self.sharpe_ratio,
            'total_return': self.total_return,
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate,
            'total_trades': self.total_trades,
            'cagr': self.cagr
        }


class QCEvaluator:
    """
    Evaluates algorithm variants by running backtests on QuantConnect.

    Uses QuantConnectMCPClient for correct hash-based auth and POST endpoints.
    """

    def __init__(self, config: EvolutionConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._client = None

    def _get_client(self):
        """Lazy-init the QC API client."""
        if self._client is None:
            from quantcoder.mcp.quantconnect_mcp import QuantConnectMCPClient
            self._client = QuantConnectMCPClient(
                self.config.qc_api_token,
                self.config.qc_user_id
            )
        return self._client

    async def create_project(self, name: str) -> Optional[int]:
        """Create a new project for evolution testing."""
        client = self._get_client()
        result = await client._call_api(
            "/projects/create", method="POST",
            data={"name": name, "language": "Py"}
        )
        if result and result.get("success"):
            project_id = result["projects"][0]["projectId"]
            self.logger.info(f"Created project {name} with ID {project_id}")
            return project_id

        self.logger.error(f"Failed to create project: {result}")
        return None

    async def update_project_code(self, project_id: int, code: str, filename: str = "main.py") -> bool:
        """Update the algorithm code in a project."""
        client = self._get_client()
        result = await client._call_api(
            "/files/update", method="POST",
            data={"projectId": project_id, "name": filename, "content": code}
        )
        if result and result.get("success"):
            self.logger.debug(f"Updated code in project {project_id}")
            return True

        self.logger.error(f"Failed to update code: {result}")
        return False

    async def compile_project(self, project_id: int) -> Optional[str]:
        """Compile project and return compile ID."""
        client = self._get_client()
        result = await client._call_api(
            "/compile/create", method="POST",
            data={"projectId": project_id}
        )
        if not result or not result.get("compileId"):
            self.logger.error(f"Failed to start compilation: {result}")
            return None

        compile_id = result["compileId"]
        state = result.get("state", "InQueue")

        # Wait for compilation
        for _ in range(30):
            if state == "BuildSuccess":
                self.logger.info(f"Project {project_id} compiled successfully")
                return compile_id
            elif state == "BuildError":
                self.logger.error(f"Compilation failed: {result.get('logs', [])}")
                return None

            await asyncio.sleep(2)
            status = await client._call_api(
                "/compile/read", method="POST",
                data={"projectId": project_id, "compileId": compile_id}
            )
            if status:
                state = status.get("state", "Unknown")

        self.logger.error("Compilation timed out")
        return None

    async def run_backtest(self, project_id: int, compile_id: str, name: str) -> Optional[str]:
        """Start a backtest and return backtest ID."""
        client = self._get_client()
        result = await client._call_api(
            "/backtests/create", method="POST",
            data={"projectId": project_id, "compileId": compile_id, "backtestName": name}
        )
        if result and result.get("success"):
            backtest_id = result["backtest"]["backtestId"]
            self.logger.info(f"Started backtest {backtest_id}")
            return backtest_id

        self.logger.error(f"Failed to start backtest: {result}")
        return None

    async def wait_for_backtest(self, project_id: int, backtest_id: str, timeout: int = 300) -> Optional[dict]:
        """Wait for backtest to complete and return results."""
        client = self._get_client()
        waited = 0
        poll_interval = 5

        while waited < timeout:
            result = await client._call_api(
                "/backtests/read", method="POST",
                data={"projectId": project_id, "backtestId": backtest_id}
            )

            if result:
                backtest = result.get("backtest", {})
                completed = backtest.get("completed", False)
                error = backtest.get("error")

                if completed or backtest.get("progress") == 1.0:
                    if error:
                        self.logger.error(f"Backtest {backtest_id} runtime error: {error[:200]}")
                    else:
                        self.logger.info(f"Backtest {backtest_id} completed")
                    return backtest

            await asyncio.sleep(poll_interval)
            waited += poll_interval
            self.logger.debug(f"Waiting for backtest... ({waited}s)")

        self.logger.error(f"Backtest timed out after {timeout}s")
        return None

    def parse_backtest_results(self, backtest_data: dict) -> BacktestResult:
        """Parse raw backtest response into structured result."""
        stats = backtest_data.get("statistics", {})

        def parse_pct(value, default=0.0):
            if isinstance(value, (int, float)):
                return value
            if isinstance(value, str):
                value = value.replace('%', '').replace(',', '')
                try:
                    return float(value) / 100
                except ValueError:
                    return default
            return default

        def parse_float(value, default=0.0):
            if isinstance(value, (int, float)):
                return value
            if isinstance(value, str):
                value = value.replace(',', '').replace('$', '')
                try:
                    return float(value)
                except ValueError:
                    return default
            return default

        return BacktestResult(
            backtest_id=backtest_data.get("backtestId", "unknown"),
            status="completed" if not backtest_data.get("error") else "failed",
            sharpe_ratio=parse_float(stats.get("Sharpe Ratio", 0)),
            total_return=parse_pct(stats.get("Net Profit", "0%")),
            max_drawdown=parse_pct(stats.get("Drawdown", "0%")),
            win_rate=parse_pct(stats.get("Win Rate", "0%")),
            total_trades=int(parse_float(stats.get("Total Orders", 0))),
            cagr=parse_pct(stats.get("Compounding Annual Return", "0%")),
            raw_response=backtest_data
        )

    async def evaluate(self, code: str, variant_id: str) -> Optional[BacktestResult]:
        """
        Full evaluation pipeline for a single variant.

        1. Update project code
        2. Compile
        3. Run backtest
        4. Parse and return results
        """
        project_id = self.config.qc_project_id

        if not project_id:
            self.logger.error("No project ID configured")
            return None

        self.logger.info(f"Evaluating variant {variant_id}")

        # Step 1: Update code
        if not await self.update_project_code(project_id, code):
            return None

        # Step 2: Compile
        compile_id = await self.compile_project(project_id)
        if not compile_id:
            return None

        # Step 3: Run backtest
        backtest_name = f"evolution_{variant_id}"
        backtest_id = await self.run_backtest(project_id, compile_id, backtest_name)
        if not backtest_id:
            return None

        # Step 4: Wait and get results
        backtest_data = await self.wait_for_backtest(project_id, backtest_id)
        if not backtest_data:
            return None

        # Step 5: Parse results
        result = self.parse_backtest_results(backtest_data)
        self.logger.info(
            f"Variant {variant_id}: Sharpe={result.sharpe_ratio:.2f}, "
            f"Return={result.total_return:.1%}, MaxDD={result.max_drawdown:.1%}"
        )

        return result

    async def evaluate_batch(self, variants: list) -> Dict[str, Optional[BacktestResult]]:
        """
        Evaluate multiple variants sequentially.

        Args:
            variants: List of (variant_id, code) tuples

        Returns:
            Dict mapping variant_id to BacktestResult (or None if failed)
        """
        results = {}

        for variant_id, code in variants:
            result = await self.evaluate(code, variant_id)
            results[variant_id] = result

            # Rate limiting
            await asyncio.sleep(2)

        return results
