"""
QuantConnect Evaluator
======================

Handles backtesting of algorithm variants via QuantConnect API.
Parses results and calculates fitness scores.

Adapted for QuantCoder v2.0 with async support.
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass

import requests

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

    Uses QuantConnect's REST API:
    - Create/update project with algorithm code
    - Compile project
    - Run backtest
    - Fetch and parse results
    """

    API_BASE = "https://www.quantconnect.com/api/v2"

    def __init__(self, config: EvolutionConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        # Validate credentials
        if not config.qc_user_id or not config.qc_api_token:
            self.logger.warning(
                "QuantConnect credentials not configured. "
                "Set qc_user_id and qc_api_token in config."
            )

    def _get_auth(self) -> tuple:
        """Get auth tuple for requests."""
        return (self.config.qc_user_id, self.config.qc_api_token)

    async def _api_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None
    ) -> Optional[dict]:
        """Make authenticated API request to QuantConnect."""
        url = f"{self.API_BASE}/{endpoint}"

        try:
            # Run sync request in thread pool to not block
            loop = asyncio.get_event_loop()

            if method == "GET":
                response = await loop.run_in_executor(
                    None,
                    lambda: requests.get(url, auth=self._get_auth(), timeout=30)
                )
            elif method == "POST":
                response = await loop.run_in_executor(
                    None,
                    lambda: requests.post(url, auth=self._get_auth(), json=data, timeout=30)
                )
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            return None

    async def create_project(self, name: str) -> Optional[int]:
        """Create a new project for evolution testing."""
        data = {
            "name": name,
            "language": "Py"
        }

        result = await self._api_request("POST", "projects/create", data)
        if result and result.get("success"):
            project_id = result["projects"][0]["projectId"]
            self.logger.info(f"Created project {name} with ID {project_id}")
            return project_id

        self.logger.error(f"Failed to create project: {result}")
        return None

    async def update_project_code(self, project_id: int, code: str, filename: str = "main.py") -> bool:
        """Update the algorithm code in a project."""
        data = {
            "projectId": project_id,
            "name": filename,
            "content": code
        }

        result = await self._api_request("POST", "files/update", data)
        if result and result.get("success"):
            self.logger.debug(f"Updated code in project {project_id}")
            return True

        self.logger.error(f"Failed to update code: {result}")
        return False

    async def compile_project(self, project_id: int) -> Optional[str]:
        """Compile project and return compile ID."""
        data = {"projectId": project_id}

        result = await self._api_request("POST", "compile/create", data)
        if result and result.get("success"):
            compile_id = result["compileId"]
            state = result["state"]

            # Wait for compilation to complete
            max_wait = 60
            waited = 0
            while state == "InQueue" and waited < max_wait:
                await asyncio.sleep(2)
                waited += 2
                status = await self._api_request("GET", f"compile/read?projectId={project_id}&compileId={compile_id}")
                if status:
                    state = status.get("state", "Unknown")

            if state == "BuildSuccess":
                self.logger.info(f"Project {project_id} compiled successfully")
                return compile_id
            else:
                self.logger.error(f"Compilation failed with state: {state}")
                return None

        self.logger.error(f"Failed to start compilation: {result}")
        return None

    async def run_backtest(self, project_id: int, compile_id: str, name: str) -> Optional[str]:
        """Start a backtest and return backtest ID."""
        data = {
            "projectId": project_id,
            "compileId": compile_id,
            "backtestName": name
        }

        result = await self._api_request("POST", "backtests/create", data)
        if result and result.get("success"):
            backtest_id = result["backtest"]["backtestId"]
            self.logger.info(f"Started backtest {backtest_id}")
            return backtest_id

        self.logger.error(f"Failed to start backtest: {result}")
        return None

    async def wait_for_backtest(self, project_id: int, backtest_id: str, timeout: int = 300) -> Optional[dict]:
        """Wait for backtest to complete and return results."""
        waited = 0
        poll_interval = 5

        while waited < timeout:
            result = await self._api_request(
                "GET",
                f"backtests/read?projectId={project_id}&backtestId={backtest_id}"
            )

            if result and result.get("success"):
                backtest = result.get("backtest", {})
                completed = backtest.get("completed", False)

                if completed:
                    self.logger.info(f"Backtest {backtest_id} completed")
                    return backtest

            await asyncio.sleep(poll_interval)
            waited += poll_interval
            self.logger.debug(f"Waiting for backtest... ({waited}s)")

        self.logger.error(f"Backtest timed out after {timeout}s")
        return None

    def parse_backtest_results(self, backtest_data: dict) -> BacktestResult:
        """Parse raw backtest response into structured result."""

        # Extract statistics
        stats = backtest_data.get("statistics", {})

        # Parse values with fallbacks
        def parse_pct(value, default=0.0):
            """Parse percentage string like '25.5%' to 0.255"""
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
            """Parse numeric value."""
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
            status="completed" if backtest_data.get("completed") else "failed",
            sharpe_ratio=parse_float(stats.get("Sharpe Ratio", 0)),
            total_return=parse_pct(stats.get("Total Net Profit", "0%")),
            max_drawdown=parse_pct(stats.get("Drawdown", "0%")),
            win_rate=parse_pct(stats.get("Win Rate", "0%")),
            total_trades=int(parse_float(stats.get("Total Trades", 0))),
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

            # Rate limiting - be nice to QC API
            await asyncio.sleep(2)

        return results
