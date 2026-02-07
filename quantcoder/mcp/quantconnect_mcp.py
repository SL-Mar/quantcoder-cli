"""MCP Client and Server for QuantConnect API integration."""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class QuantConnectMCPClient:
    """
    MCP Client for interacting with QuantConnect.

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

            # Compile
            compile_result = await self._compile(project_id)

            return {
                "valid": compile_result.get("success", False),
                "errors": compile_result.get("errors", []),
                "warnings": compile_result.get("warnings", []),
                "compile_id": compile_result.get("compileId"),
                "project_id": project_id
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
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run backtest in QuantConnect.

        Args:
            code: Main algorithm code
            start_date: Backtest start date (YYYY-MM-DD)
            end_date: Backtest end date (YYYY-MM-DD)
            files: Additional files
            name: Backtest name

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

            # backtestId is nested inside "backtest" object
            backtest_obj = backtest_result.get("backtest", {})
            backtest_id = backtest_obj.get("backtestId")

            if not backtest_id:
                return {
                    "success": False,
                    "error": f"Failed to create backtest: {backtest_result.get('errors', backtest_result.get('messages', 'unknown'))}"
                }

            # Poll for completion
            self.logger.info(f"Waiting for backtest {backtest_id} to complete")

            result = await self._wait_for_backtest(backtest_id, validation["project_id"])

            # Results may be nested under "backtest" or at top level
            bt = result.get("backtest", result)
            runtime_error = bt.get("error")
            stats = bt.get("statistics", {})
            runtime_stats = bt.get("runtimeStatistics", {})

            if runtime_error:
                return {
                    "success": False,
                    "error": "Runtime error during backtest",
                    "runtime_error": runtime_error,
                    "stacktrace": bt.get("stacktrace", ""),
                    "backtest_id": backtest_id,
                    "project_id": validation["project_id"],
                    "project_url": f"https://www.quantconnect.com/terminal/{validation['project_id']}#open",
                }

            return {
                "success": True,
                "backtest_id": backtest_id,
                "project_id": validation["project_id"],
                "project_url": f"https://www.quantconnect.com/terminal/{validation['project_id']}#open",
                "statistics": stats,
                "runtime_statistics": runtime_stats,
                "sharpe": stats.get("Sharpe Ratio"),
                "total_return": stats.get("Net Profit")
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
        import aiohttp

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
            async with aiohttp.ClientSession() as session:
                async with session.get(doc_url, timeout=10) as resp:
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
        project_name = f"QuantCoder_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.logger.info(f"Creating project: {project_name}")

        result = await self._call_api(
            "/projects/create",
            method="POST",
            data={
                "name": project_name,
                "language": "Py"
            }
        )

        project_id = result.get("projects", [{}])[0].get("projectId")
        if not project_id:
            raise RuntimeError(f"Failed to create project: {result}")

        self.logger.info(f"Created project {project_id}: {project_name}")
        return project_id

    async def _upload_files(
        self,
        project_id: str,
        main_code: str,
        additional_files: Dict[str, str]
    ):
        """Upload files to project with validation."""
        # Update main.py (QC auto-creates it with boilerplate on project creation)
        self.logger.info(f"Uploading main.py to project {project_id} ({len(main_code)} chars)")
        result = await self._call_api(
            "/files/update",
            method="POST",
            data={
                "projectId": project_id,
                "name": "main.py",
                "content": main_code
            }
        )

        if not result.get("success"):
            raise RuntimeError(
                f"Failed to upload main.py to project {project_id}: {result}"
            )

        # Verify the upload by reading back
        verify = await self._call_api(
            "/files/read",
            method="POST",
            data={"projectId": project_id, "name": "main.py"}
        )
        verify_files = verify.get("files", [])
        if not verify_files:
            raise RuntimeError(
                f"main.py not found after upload to project {project_id}"
            )
        uploaded_lines = len(verify_files[0].get("content", "").splitlines())
        expected_lines = len(main_code.splitlines())
        self.logger.info(
            f"Upload verified: main.py has {uploaded_lines} lines "
            f"(expected {expected_lines})"
        )

        # Upload additional files
        for filename, content in additional_files.items():
            self.logger.info(f"Creating {filename} in project {project_id}")
            result = await self._call_api(
                "/files/create",
                method="POST",
                data={
                    "projectId": project_id,
                    "name": filename.lower(),
                    "content": content
                }
            )
            if not result.get("success"):
                self.logger.warning(
                    f"Failed to create {filename}: {result}"
                )

    async def _compile(self, project_id: str) -> Dict[str, Any]:
        """Compile project."""
        result = await self._call_api(
            "/compile/create",
            method="POST",
            data={"projectId": project_id}
        )

        compile_id = result.get("compileId")

        if not compile_id:
            return {
                "success": False,
                "compileId": None,
                "errors": [f"Compile create failed: {result}"],
                "warnings": []
            }

        # Wait for compilation (compile/read is POST, not GET)
        for _ in range(60):
            status = await self._call_api(
                "/compile/read",
                method="POST",
                data={"projectId": project_id, "compileId": compile_id}
            )

            if status.get("state") == "BuildSuccess":
                return {
                    "success": True,
                    "compileId": compile_id,
                    "errors": [],
                    "warnings": []
                }
            elif status.get("state") == "BuildError":
                return {
                    "success": False,
                    "compileId": compile_id,
                    "errors": status.get("logs", []),
                    "warnings": []
                }

            await asyncio.sleep(1)

        return {
            "success": False,
            "compileId": compile_id,
            "errors": ["Compilation timed out after 60 seconds"],
            "warnings": []
        }

    async def _wait_for_backtest(self, backtest_id: str, project_id: str, max_wait: int = 300) -> Dict[str, Any]:
        """Wait for backtest to complete, tolerating transient API failures."""
        consecutive_errors = 0
        max_consecutive_errors = 5

        for i in range(max_wait // 2):
            try:
                result = await self._call_api(
                    "/backtests/read",
                    method="POST",
                    data={"projectId": project_id, "backtestId": backtest_id}
                )
                consecutive_errors = 0  # reset on success

                bt = result.get("backtest", result)
                if bt.get("progress") == 1.0 or bt.get("completed"):
                    return result

                progress = bt.get("progress", 0)
                if i % 15 == 0:
                    self.logger.info(f"Backtest progress: {progress * 100:.0f}%")

            except (ConnectionError, Exception) as e:
                consecutive_errors += 1
                self.logger.warning(f"Poll attempt {i} failed ({consecutive_errors}/{max_consecutive_errors}): {e}")
                if consecutive_errors >= max_consecutive_errors:
                    raise TimeoutError(
                        f"Backtest polling failed {max_consecutive_errors} times consecutively: {e}"
                    )

            await asyncio.sleep(2)

        raise TimeoutError(f"Backtest {backtest_id} did not complete in {max_wait} seconds")

    async def _call_api(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        retries: int = 3,
        timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """Call QuantConnect API with hash-based authentication, timeout, and retry."""
        import aiohttp

        url = f"{self.base_url}{endpoint}"
        timeout = aiohttp.ClientTimeout(total=timeout_seconds, connect=10)

        for attempt in range(retries):
            try:
                headers = self._build_auth_headers()
                headers["Content-Type"] = "application/json"

                async with aiohttp.ClientSession(timeout=timeout) as session:
                    if method == "GET":
                        async with session.get(url, headers=headers, params=params) as resp:
                            return await resp.json(content_type=None)
                    elif method == "POST":
                        async with session.post(url, headers=headers, json=data) as resp:
                            return await resp.json(content_type=None)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                self.logger.warning(f"API call {endpoint} attempt {attempt + 1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise ConnectionError(f"Connection timeout to host {url}") from e

    def _build_auth_headers(self) -> Dict[str, str]:
        """Build QC API auth headers with hash-based authentication."""
        import base64
        import hashlib
        import time

        timestamp = str(int(time.time()))
        api_hash = hashlib.sha256(f"{self.api_key}:{timestamp}".encode()).hexdigest()
        credentials = base64.b64encode(f"{self.user_id}:{api_hash}".encode()).decode()
        return {
            "Timestamp": timestamp,
            "Authorization": f"Basic {credentials}",
        }


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
        """Stop the MCP server."""
        self._running = False
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
