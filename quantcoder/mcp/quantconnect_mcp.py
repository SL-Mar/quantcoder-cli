"""MCP Client and Server for QuantConnect API integration."""

import asyncio
import base64
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

import aiohttp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

try:
    import pybreaker
    CIRCUIT_BREAKER_AVAILABLE = True
except ImportError:
    CIRCUIT_BREAKER_AVAILABLE = False

logger = logging.getLogger(__name__)

# Configuration constants
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=60, connect=10)
MAX_COMPILE_WAIT_ITERATIONS = 120  # 2 minutes at 1 second intervals
MAX_BACKTEST_WAIT_SECONDS = 600    # 10 minutes max


class QuantConnectAPIError(Exception):
    """Raised when QuantConnect API returns an error."""
    pass


class QuantConnectTimeoutError(Exception):
    """Raised when an operation times out."""
    pass


class QuantConnectMCPClient:
    """
    MCP Client for interacting with QuantConnect.

    Features:
    - Connection pooling (reuses HTTP sessions)
    - Circuit breaker pattern for fault tolerance
    - Exponential backoff on transient failures
    - Bounded polling loops with explicit timeouts

    Provides tools for:
    - Code validation
    - Backtesting
    - Live deployment
    - API documentation lookup
    """

    def __init__(self, api_key: str, user_id: str):
        """
        Initialize QuantConnect MCP client.

        Args:
            api_key: QuantConnect API key
            user_id: QuantConnect user ID
        """
        self.api_key = api_key
        self.user_id = user_id
        self.base_url = "https://www.quantconnect.com/api/v2"
        self.logger = logging.getLogger(self.__class__.__name__)

        # Connection pooling: shared session (created lazily)
        self._session: Optional[aiohttp.ClientSession] = None

        # Circuit breaker for API calls (if available)
        if CIRCUIT_BREAKER_AVAILABLE:
            self._circuit_breaker = pybreaker.CircuitBreaker(
                fail_max=5,           # Open circuit after 5 failures
                reset_timeout=60,     # Try again after 60 seconds
                exclude=[QuantConnectAPIError],  # Don't count API errors as failures
            )
        else:
            self._circuit_breaker = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create a shared aiohttp session for connection pooling."""
        if self._session is None or self._session.closed:
            # Configure connection pool
            connector = aiohttp.TCPConnector(
                limit=10,              # Max 10 concurrent connections
                limit_per_host=5,      # Max 5 per host
                ttl_dns_cache=300,     # Cache DNS for 5 minutes
            )
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=DEFAULT_TIMEOUT,
            )
        return self._session

    async def close(self):
        """Close the HTTP session. Call this when done with the client."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close session."""
        await self.close()

    async def validate_code(
        self,
        code: str,
        files: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Validate code against QuantConnect API.

        Args:
            code: Main algorithm code
            files: Additional files (Universe.py, Alpha.py, etc.)

        Returns:
            Validation result with errors/warnings
        """
        self.logger.info("Validating code with QuantConnect API")

        try:
            # Create or update project
            project_id = await self._create_project()

            # Upload files
            await self._upload_files(project_id, code, files or {})

            # Compile with bounded wait
            compile_result = await self._compile(project_id)

            return {
                "valid": compile_result.get("success", False),
                "errors": compile_result.get("errors", []),
                "warnings": compile_result.get("warnings", []),
                "compile_id": compile_result.get("compileId"),
                "project_id": project_id
            }

        except QuantConnectTimeoutError as e:
            self.logger.error(f"Validation timeout: {e}")
            return {
                "valid": False,
                "errors": [f"Compilation timed out: {e}"],
                "warnings": []
            }
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": []
            }

    async def backtest(
        self,
        code: str,
        start_date: str,
        end_date: str,
        files: Optional[Dict[str, str]] = None,
        name: Optional[str] = None,
        max_wait: int = MAX_BACKTEST_WAIT_SECONDS
    ) -> Dict[str, Any]:
        """
        Run backtest in QuantConnect.

        Args:
            code: Main algorithm code
            start_date: Backtest start date (YYYY-MM-DD)
            end_date: Backtest end date (YYYY-MM-DD)
            files: Additional files
            name: Backtest name
            max_wait: Maximum seconds to wait for backtest completion

        Returns:
            Backtest results with statistics
        """
        self.logger.info(f"Running backtest: {start_date} to {end_date}")

        try:
            # Validate first
            validation = await self.validate_code(code, files)

            if not validation["valid"]:
                return {
                    "success": False,
                    "error": "Code validation failed",
                    "validation_errors": validation["errors"]
                }

            # Create backtest
            backtest_name = name or f"QuantCoder_{datetime.now().isoformat()}"

            backtest_result = await self._call_api(
                "/backtests/create",
                method="POST",
                data={
                    "projectId": validation["project_id"],
                    "compileId": validation["compile_id"],
                    "backtestName": backtest_name
                }
            )

            backtest_id = backtest_result.get("backtestId")

            if not backtest_id:
                return {
                    "success": False,
                    "error": "Failed to create backtest"
                }

            # Poll for completion with bounded wait
            self.logger.info(f"Waiting for backtest {backtest_id} to complete (max {max_wait}s)")

            result = await self._wait_for_backtest(backtest_id, max_wait=max_wait)

            return {
                "success": True,
                "backtest_id": backtest_id,
                "statistics": result.get("result", {}).get("Statistics", {}),
                "runtime_statistics": result.get("result", {}).get("RuntimeStatistics", {}),
                "charts": result.get("result", {}).get("Charts", {}),
                "sharpe": result.get("result", {}).get("Statistics", {}).get("Sharpe Ratio"),
                "total_return": result.get("result", {}).get("Statistics", {}).get("Total Net Profit")
            }

        except QuantConnectTimeoutError as e:
            self.logger.error(f"Backtest timeout: {e}")
            return {
                "success": False,
                "error": f"Backtest timed out: {e}"
            }
        except Exception as e:
            self.logger.error(f"Backtest error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_api_docs(self, topic: str) -> str:
        """
        Get QuantConnect API documentation for a topic.

        Args:
            topic: API topic (e.g., "indicators", "universe selection")

        Returns:
            Documentation text
        """
        # Map topics to documentation endpoints
        topic_map = {
            "indicators": "indicators/supported-indicators",
            "universe": "algorithm-reference/universes",
            "universe selection": "algorithm-reference/universes",
            "risk management": "algorithm-reference/risk-management",
            "portfolio": "algorithm-reference/portfolio-construction",
            "execution": "algorithm-reference/execution-models",
            "alpha": "algorithm-reference/alpha-models",
            "data": "datasets",
            "orders": "algorithm-reference/trading-and-orders",
            "securities": "algorithm-reference/securities-and-portfolio",
            "history": "algorithm-reference/historical-data",
            "scheduling": "algorithm-reference/scheduled-events",
            "charting": "algorithm-reference/charting",
            "logging": "algorithm-reference/logging-and-debug",
        }

        # Find matching topic
        topic_lower = topic.lower()
        doc_path = None
        for key, path in topic_map.items():
            if key in topic_lower:
                doc_path = path
                break

        if not doc_path:
            doc_path = "algorithm-reference"

        doc_url = f"https://www.quantconnect.com/docs/v2/{doc_path}"

        try:
            session = await self._get_session()
            async with session.get(doc_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    # Return URL and basic info
                    return (
                        f"QuantConnect Documentation for '{topic}':\n"
                        f"URL: {doc_url}\n\n"
                        f"Key topics covered:\n"
                        f"- API Reference and usage examples\n"
                        f"- Code samples in Python and C#\n"
                        f"- Best practices and common patterns\n\n"
                        f"Visit the URL above for detailed documentation."
                    )
                else:
                    return f"Documentation for '{topic}': {doc_url}"
        except Exception as e:
            self.logger.warning(f"Failed to fetch docs: {e}")
            return f"Documentation for '{topic}': {doc_url}"

    async def deploy_live(
        self,
        project_id: str,
        compile_id: str,
        node_id: str,
        brokerage: str = "InteractiveBrokers"
    ) -> Dict[str, Any]:
        """
        Deploy algorithm to live trading.

        Args:
            project_id: Project ID
            compile_id: Compile ID
            node_id: Live node ID
            brokerage: Brokerage name

        Returns:
            Deployment result
        """
        self.logger.info(f"Deploying to live trading on {brokerage}")

        try:
            result = await self._call_api(
                "/live/create",
                method="POST",
                data={
                    "projectId": project_id,
                    "compileId": compile_id,
                    "nodeId": node_id,
                    "brokerage": brokerage
                }
            )

            return {
                "success": result.get("success", False),
                "live_id": result.get("liveAlgorithmId"),
                "message": result.get("message", "")
            }

        except Exception as e:
            self.logger.error(f"Deployment error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # Private helper methods

    async def _create_project(self) -> str:
        """Create a new project in QuantConnect."""
        result = await self._call_api(
            "/projects/create",
            method="POST",
            data={
                "name": f"QuantCoder_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "language": "Py"
            }
        )

        return result.get("projects", [{}])[0].get("projectId")

    async def _upload_files(
        self,
        project_id: str,
        main_code: str,
        additional_files: Dict[str, str]
    ):
        """Upload files to project."""
        # Upload Main.py
        await self._call_api(
            "/files/create",
            method="POST",
            data={
                "projectId": project_id,
                "name": "main.py",
                "content": main_code
            }
        )

        # Upload additional files
        for filename, content in additional_files.items():
            await self._call_api(
                "/files/create",
                method="POST",
                data={
                    "projectId": project_id,
                    "name": filename.lower(),
                    "content": content
                }
            )

    async def _compile(
        self,
        project_id: str,
        max_iterations: int = MAX_COMPILE_WAIT_ITERATIONS
    ) -> Dict[str, Any]:
        """
        Compile project with bounded polling.

        Args:
            project_id: Project ID to compile
            max_iterations: Maximum poll iterations (at 1 second intervals)

        Returns:
            Compilation result

        Raises:
            QuantConnectTimeoutError: If compilation doesn't complete in time
        """
        result = await self._call_api(
            "/compile/create",
            method="POST",
            data={"projectId": project_id}
        )

        compile_id = result.get("compileId")

        # Wait for compilation with explicit bound
        for iteration in range(max_iterations):
            status = await self._call_api(
                "/compile/read",
                params={"projectId": project_id, "compileId": compile_id}
            )

            state = status.get("state")

            if state == "BuildSuccess":
                self.logger.info(f"Compilation succeeded after {iteration + 1} iterations")
                return {
                    "success": True,
                    "compileId": compile_id,
                    "errors": [],
                    "warnings": []
                }
            elif state == "BuildError":
                return {
                    "success": False,
                    "compileId": compile_id,
                    "errors": status.get("logs", []),
                    "warnings": []
                }

            await asyncio.sleep(1)

        # Timeout reached
        raise QuantConnectTimeoutError(
            f"Compilation did not complete after {max_iterations} seconds"
        )

    async def _wait_for_backtest(
        self,
        backtest_id: str,
        max_wait: int = MAX_BACKTEST_WAIT_SECONDS,
        poll_interval: int = 2
    ) -> Dict[str, Any]:
        """
        Wait for backtest to complete with bounded polling.

        Args:
            backtest_id: Backtest ID to poll
            max_wait: Maximum seconds to wait
            poll_interval: Seconds between polls

        Returns:
            Backtest result

        Raises:
            QuantConnectTimeoutError: If backtest doesn't complete in time
        """
        max_iterations = max_wait // poll_interval

        for iteration in range(max_iterations):
            result = await self._call_api(
                "/backtests/read",
                params={"backtestId": backtest_id}
            )

            progress = result.get("progress", 0)
            completed = result.get("completed", False)

            if progress == 1.0 or completed:
                self.logger.info(
                    f"Backtest completed after {(iteration + 1) * poll_interval} seconds"
                )
                return result

            # Log progress periodically
            if iteration % 15 == 0:  # Every 30 seconds
                self.logger.info(f"Backtest progress: {progress * 100:.0f}%")

            await asyncio.sleep(poll_interval)

        # Timeout reached
        raise QuantConnectTimeoutError(
            f"Backtest {backtest_id} did not complete in {max_wait} seconds"
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _call_api(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Call QuantConnect API with retry and circuit breaker.

        Uses exponential backoff on transient failures and circuit breaker
        to prevent cascading failures.

        Args:
            endpoint: API endpoint (e.g., "/projects/create")
            method: HTTP method (GET or POST)
            data: JSON body for POST requests
            params: Query parameters for GET requests

        Returns:
            API response as dictionary

        Raises:
            QuantConnectAPIError: If API returns an error
            aiohttp.ClientError: On connection errors (will be retried)
        """
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Basic {self._encode_credentials()}"
        }

        # Use circuit breaker if available
        if self._circuit_breaker:
            return await self._circuit_breaker.call_async(
                self._execute_request, url, method, headers, data, params
            )
        else:
            return await self._execute_request(url, method, headers, data, params)

    async def _execute_request(
        self,
        url: str,
        method: str,
        headers: Dict[str, str],
        data: Optional[Dict],
        params: Optional[Dict]
    ) -> Dict[str, Any]:
        """Execute the actual HTTP request using the shared session."""
        session = await self._get_session()

        if method == "GET":
            async with session.get(url, headers=headers, params=params) as resp:
                response_data = await resp.json()
                if resp.status >= 400:
                    raise QuantConnectAPIError(
                        f"API error {resp.status}: {response_data}"
                    )
                return response_data
        elif method == "POST":
            async with session.post(url, headers=headers, json=data) as resp:
                response_data = await resp.json()
                if resp.status >= 400:
                    raise QuantConnectAPIError(
                        f"API error {resp.status}: {response_data}"
                    )
                return response_data
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

    def _encode_credentials(self) -> str:
        """Encode API credentials for Basic auth."""
        credentials = f"{self.user_id}:{self.api_key}"
        return base64.b64encode(credentials.encode()).decode()


class QuantConnectMCPServer:
    """
    MCP Server exposing QuantConnect capabilities as MCP tools.

    Can be used by Claude Code or other MCP-compatible clients.
    """

    def __init__(self, api_key: str, user_id: str):
        """Initialize MCP server."""
        self.client = QuantConnectMCPClient(api_key, user_id)
        self.logger = logging.getLogger(self.__class__.__name__)

    async def start(self):
        """
        Start MCP server and register available tools.

        This initializes the server and makes tools available for MCP clients.
        Tools are exposed via the handle_tool_call method.
        """
        self.logger.info("Initializing QuantConnect MCP Server")

        # Define available tools with their schemas
        self.tools = {
            "validate_code": {
                "description": "Validate QuantConnect algorithm code",
                "parameters": {
                    "code": {"type": "string", "description": "Main algorithm code"},
                    "files": {"type": "object", "description": "Additional files (optional)"},
                },
                "required": ["code"],
            },
            "backtest": {
                "description": "Run backtest on QuantConnect",
                "parameters": {
                    "code": {"type": "string", "description": "Main algorithm code"},
                    "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    "files": {"type": "object", "description": "Additional files (optional)"},
                    "name": {"type": "string", "description": "Backtest name (optional)"},
                },
                "required": ["code", "start_date", "end_date"],
            },
            "get_api_docs": {
                "description": "Get QuantConnect API documentation",
                "parameters": {
                    "topic": {"type": "string", "description": "Documentation topic"},
                },
                "required": ["topic"],
            },
            "deploy_live": {
                "description": "Deploy algorithm to live trading",
                "parameters": {
                    "project_id": {"type": "string", "description": "Project ID"},
                    "compile_id": {"type": "string", "description": "Compile ID"},
                    "node_id": {"type": "string", "description": "Live node ID"},
                    "brokerage": {"type": "string", "description": "Brokerage name"},
                },
                "required": ["project_id", "compile_id", "node_id"],
            },
        }

        self._running = True
        self.logger.info(
            f"QuantConnect MCP Server started with {len(self.tools)} tools: "
            f"{', '.join(self.tools.keys())}"
        )

    def get_tools(self) -> dict:
        """Return available tools and their schemas."""
        return self.tools if hasattr(self, 'tools') else {}

    def is_running(self) -> bool:
        """Check if server is running."""
        return getattr(self, '_running', False)

    async def stop(self):
        """Stop the MCP server and clean up resources."""
        self._running = False
        await self.client.close()
        self.logger.info("QuantConnect MCP Server stopped")

    async def handle_tool_call(self, tool_name: str, arguments: Dict) -> Any:
        """Handle MCP tool call."""
        if tool_name == "validate_code":
            return await self.client.validate_code(**arguments)
        elif tool_name == "backtest":
            return await self.client.backtest(**arguments)
        elif tool_name == "get_api_docs":
            return await self.client.get_api_docs(**arguments)
        elif tool_name == "deploy_live":
            return await self.client.deploy_live(**arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
