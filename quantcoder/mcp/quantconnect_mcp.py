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

            backtest_id = backtest_result.get("backtestId")

            if not backtest_id:
                return {
                    "success": False,
                    "error": "Failed to create backtest"
                }

            # Poll for completion
            self.logger.info(f"Waiting for backtest {backtest_id} to complete")

            result = await self._wait_for_backtest(backtest_id)

            return {
                "success": True,
                "backtest_id": backtest_id,
                "statistics": result.get("result", {}).get("Statistics", {}),
                "runtime_statistics": result.get("result", {}).get("RuntimeStatistics", {}),
                "charts": result.get("result", {}).get("Charts", {}),
                "sharpe": result.get("result", {}).get("Statistics", {}).get("Sharpe Ratio"),
                "total_return": result.get("result", {}).get("Statistics", {}).get("Total Net Profit")
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
        # This would integrate with QC docs or use web scraping
        # For now, return placeholder
        return f"Documentation for {topic}: See https://www.quantconnect.com/docs/"

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
            f"/files/create",
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
                f"/files/create",
                method="POST",
                data={
                    "projectId": project_id,
                    "name": filename.lower(),
                    "content": content
                }
            )

    async def _compile(self, project_id: str) -> Dict[str, Any]:
        """Compile project."""
        result = await self._call_api(
            f"/compile/create",
            method="POST",
            data={"projectId": project_id}
        )

        compile_id = result.get("compileId")

        # Wait for compilation
        while True:
            status = await self._call_api(f"/compile/read", params={"projectId": project_id, "compileId": compile_id})

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

    async def _wait_for_backtest(self, backtest_id: str, max_wait: int = 300) -> Dict[str, Any]:
        """Wait for backtest to complete."""
        for _ in range(max_wait):
            result = await self._call_api(f"/backtests/read", params={"backtestId": backtest_id})

            if result.get("progress") == 1.0 or result.get("completed"):
                return result

            await asyncio.sleep(2)

        raise TimeoutError(f"Backtest {backtest_id} did not complete in {max_wait} seconds")

    async def _call_api(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Call QuantConnect API."""
        import aiohttp

        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Basic {self._encode_credentials()}"
        }

        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, headers=headers, params=params) as resp:
                    return await resp.json()
            elif method == "POST":
                async with session.post(url, headers=headers, json=data) as resp:
                    return await resp.json()

    def _encode_credentials(self) -> str:
        """Encode API credentials."""
        import base64
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
        """Start MCP server."""
        # This would use the MCP SDK to expose tools
        # For now, this is a placeholder
        self.logger.info("QuantConnect MCP Server started")

        # Register tools with MCP framework
        # Each method becomes an MCP tool
        pass

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
