"""
Fully Operational MCP Client and Server for QuantConnect API Integration.

This module provides:
- QuantConnectAPIClient: Direct API client for QuantConnect REST API v2
- QuantConnectMCPClient: High-level client with workflow methods
- QuantConnectMCPServer: MCP-compliant server with stdio transport

Author: QuantCoder
License: MIT
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes and Enums
# ============================================================================

class CompileState(Enum):
    """QuantConnect compile states."""
    IN_QUEUE = "InQueue"
    BUILD_SUCCESS = "BuildSuccess"
    BUILD_ERROR = "BuildError"


class BacktestState(Enum):
    """QuantConnect backtest states."""
    IN_QUEUE = "InQueue"
    RUNNING = "Running"
    COMPLETED = "Completed"
    ERROR = "Error"


@dataclass
class APIResponse:
    """Standardized API response."""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    raw_response: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompileResult:
    """Result of a compilation."""
    success: bool
    compile_id: str = ""
    project_id: int = 0
    state: str = ""
    errors: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)


@dataclass
class BacktestResult:
    """Result of a backtest."""
    success: bool
    backtest_id: str = ""
    name: str = ""
    project_id: int = 0
    completed: bool = False
    progress: float = 0.0
    statistics: Dict[str, Any] = field(default_factory=dict)
    runtime_statistics: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    sharpe_ratio: Optional[float] = None
    total_return: Optional[float] = None
    drawdown: Optional[float] = None


@dataclass
class ProjectInfo:
    """QuantConnect project information."""
    project_id: int
    name: str
    created: datetime
    modified: datetime
    language: str = "Py"


@dataclass
class MCPTool:
    """MCP Tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[..., Awaitable[Any]]


# ============================================================================
# QuantConnect API Client (Low-Level)
# ============================================================================

class QuantConnectAPIClient:
    """
    Low-level async client for QuantConnect REST API v2.

    Handles authentication, request signing, and raw API calls.
    All QuantConnect API endpoints use POST with form-encoded or JSON data.
    """

    BASE_URL = "https://www.quantconnect.com/api/v2"

    def __init__(
        self,
        user_id: str,
        api_token: str,
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        """
        Initialize the API client.

        Args:
            user_id: QuantConnect user ID (found in account settings)
            api_token: QuantConnect API token (found in account settings)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.user_id = user_id
        self.api_token = api_token
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def _get_auth_header(self) -> str:
        """Generate Basic auth header from credentials."""
        credentials = f"{self.user_id}:{self.api_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def _get_timestamp_hash(self) -> str:
        """Generate timestamp hash for request signing."""
        timestamp = str(int(time.time()))
        hash_string = f"{self.api_token}:{timestamp}"
        return hashlib.sha256(hash_string.encode()).hexdigest()

    async def _get_session(self):
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        method: str = "POST"
    ) -> APIResponse:
        """
        Make an API request with retries.

        Args:
            endpoint: API endpoint (e.g., "/projects/create")
            data: Request data (sent as form data for POST)
            method: HTTP method

        Returns:
            APIResponse with success status and data
        """
        import aiohttp

        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": self._get_auth_header(),
            "Timestamp": str(int(time.time()))
        }

        last_error = None
        for attempt in range(self.max_retries):
            try:
                session = await self._get_session()

                if method == "POST":
                    async with session.post(url, headers=headers, data=data) as resp:
                        response_data = await resp.json()
                else:
                    async with session.get(url, headers=headers, params=data) as resp:
                        response_data = await resp.json()

                # Check for API-level success
                success = response_data.get("success", False)
                errors = []

                if not success:
                    errors = response_data.get("errors", [])
                    if not errors and "messages" in response_data:
                        errors = response_data["messages"]

                return APIResponse(
                    success=success,
                    data=response_data,
                    errors=errors,
                    raw_response=response_data
                )

            except aiohttp.ClientError as e:
                last_error = str(e)
                self.logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

            except Exception as e:
                last_error = str(e)
                self.logger.error(f"Unexpected error: {e}")
                break

        return APIResponse(
            success=False,
            errors=[f"Request failed after {self.max_retries} attempts: {last_error}"]
        )

    # -------------------------------------------------------------------------
    # Project Management
    # -------------------------------------------------------------------------

    async def create_project(self, name: str, language: str = "Py") -> APIResponse:
        """Create a new project."""
        return await self._request("/projects/create", {
            "name": name,
            "language": language
        })

    async def read_project(self, project_id: int) -> APIResponse:
        """Read project details."""
        return await self._request("/projects/read", {"projectId": project_id})

    async def list_projects(self) -> APIResponse:
        """List all projects."""
        return await self._request("/projects/read")

    async def delete_project(self, project_id: int) -> APIResponse:
        """Delete a project."""
        return await self._request("/projects/delete", {"projectId": project_id})

    async def update_project(
        self,
        project_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> APIResponse:
        """Update project details."""
        data = {"projectId": project_id}
        if name:
            data["name"] = name
        if description:
            data["description"] = description
        return await self._request("/projects/update", data)

    # -------------------------------------------------------------------------
    # File Management
    # -------------------------------------------------------------------------

    async def create_file(
        self,
        project_id: int,
        name: str,
        content: str
    ) -> APIResponse:
        """Create or update a file in a project."""
        return await self._request("/files/create", {
            "projectId": project_id,
            "name": name,
            "content": content
        })

    async def read_file(self, project_id: int, name: str) -> APIResponse:
        """Read a file from a project."""
        return await self._request("/files/read", {
            "projectId": project_id,
            "name": name
        })

    async def delete_file(self, project_id: int, name: str) -> APIResponse:
        """Delete a file from a project."""
        return await self._request("/files/delete", {
            "projectId": project_id,
            "name": name
        })

    # -------------------------------------------------------------------------
    # Compilation
    # -------------------------------------------------------------------------

    async def create_compile(self, project_id: int) -> APIResponse:
        """Start compilation of a project."""
        return await self._request("/compile/create", {"projectId": project_id})

    async def read_compile(self, project_id: int, compile_id: str) -> APIResponse:
        """Read compilation status."""
        return await self._request("/compile/read", {
            "projectId": project_id,
            "compileId": compile_id
        })

    # -------------------------------------------------------------------------
    # Backtesting
    # -------------------------------------------------------------------------

    async def create_backtest(
        self,
        project_id: int,
        compile_id: str,
        backtest_name: str
    ) -> APIResponse:
        """Create and start a backtest."""
        return await self._request("/backtests/create", {
            "projectId": project_id,
            "compileId": compile_id,
            "backtestName": backtest_name
        })

    async def read_backtest(
        self,
        project_id: int,
        backtest_id: str
    ) -> APIResponse:
        """Read backtest status and results."""
        return await self._request("/backtests/read", {
            "projectId": project_id,
            "backtestId": backtest_id
        })

    async def delete_backtest(
        self,
        project_id: int,
        backtest_id: str
    ) -> APIResponse:
        """Delete a backtest."""
        return await self._request("/backtests/delete", {
            "projectId": project_id,
            "backtestId": backtest_id
        })

    async def list_backtests(self, project_id: int) -> APIResponse:
        """List all backtests for a project."""
        return await self._request("/backtests/read", {"projectId": project_id})

    # -------------------------------------------------------------------------
    # Live Trading
    # -------------------------------------------------------------------------

    async def create_live(
        self,
        project_id: int,
        compile_id: str,
        node_id: str,
        brokerage_settings: Dict[str, Any]
    ) -> APIResponse:
        """Deploy algorithm for live trading."""
        data = {
            "projectId": project_id,
            "compileId": compile_id,
            "nodeId": node_id,
            **brokerage_settings
        }
        return await self._request("/live/create", data)

    async def read_live(self, project_id: int) -> APIResponse:
        """Read live algorithm status."""
        return await self._request("/live/read", {"projectId": project_id})

    async def stop_live(self, project_id: int) -> APIResponse:
        """Stop a live algorithm."""
        return await self._request("/live/stop", {"projectId": project_id})

    async def liquidate_live(self, project_id: int) -> APIResponse:
        """Liquidate and stop a live algorithm."""
        return await self._request("/live/liquidate", {"projectId": project_id})

    # -------------------------------------------------------------------------
    # Account & Authentication
    # -------------------------------------------------------------------------

    async def authenticate(self) -> APIResponse:
        """Test authentication credentials."""
        return await self._request("/authenticate")

    async def read_account(self) -> APIResponse:
        """Read account information."""
        return await self._request("/account/read")


# ============================================================================
# QuantConnect MCP Client (High-Level)
# ============================================================================

class QuantConnectMCPClient:
    """
    High-level client providing workflow-oriented methods for QuantConnect.

    This client wraps the low-level API client and provides methods that
    handle complete workflows like validate → compile → backtest.
    """

    def __init__(
        self,
        user_id: Optional[str] = None,
        api_token: Optional[str] = None,
        auto_cleanup: bool = True,
        project_prefix: str = "QuantCoder"
    ):
        """
        Initialize the MCP client.

        Args:
            user_id: QuantConnect user ID (or set QC_USER_ID env var)
            api_token: QuantConnect API token (or set QC_API_TOKEN env var)
            auto_cleanup: Automatically delete temporary projects
            project_prefix: Prefix for auto-created project names
        """
        self.user_id = user_id or os.getenv("QC_USER_ID")
        self.api_token = api_token or os.getenv("QC_API_TOKEN")

        if not self.user_id or not self.api_token:
            raise ValueError(
                "QuantConnect credentials required. Set QC_USER_ID and QC_API_TOKEN "
                "environment variables or pass user_id and api_token parameters."
            )

        self.api = QuantConnectAPIClient(self.user_id, self.api_token)
        self.auto_cleanup = auto_cleanup
        self.project_prefix = project_prefix
        self._temp_projects: List[int] = []
        self.logger = logging.getLogger(self.__class__.__name__)

    async def close(self):
        """Clean up resources."""
        if self.auto_cleanup:
            await self.cleanup_temp_projects()
        await self.api.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # -------------------------------------------------------------------------
    # Authentication & Health
    # -------------------------------------------------------------------------

    async def verify_credentials(self) -> Dict[str, Any]:
        """
        Verify that API credentials are valid.

        Returns:
            Dict with success status and account info
        """
        response = await self.api.authenticate()

        if response.success:
            account = await self.api.read_account()
            return {
                "success": True,
                "authenticated": True,
                "account": account.data if account.success else {}
            }

        return {
            "success": False,
            "authenticated": False,
            "errors": response.errors
        }

    # -------------------------------------------------------------------------
    # Code Validation
    # -------------------------------------------------------------------------

    async def validate_code(
        self,
        code: str,
        files: Optional[Dict[str, str]] = None,
        project_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate algorithm code by compiling it on QuantConnect.

        Args:
            code: Main algorithm code (main.py content)
            files: Additional files {filename: content}
            project_name: Optional project name (auto-generated if not provided)

        Returns:
            Dict with validation results including any compile errors
        """
        self.logger.info("Starting code validation")

        try:
            # Create project
            name = project_name or f"{self.project_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            project_response = await self.api.create_project(name)

            if not project_response.success:
                return {
                    "valid": False,
                    "errors": project_response.errors or ["Failed to create project"],
                    "project_id": None,
                    "compile_id": None
                }

            project_id = project_response.data.get("projects", [{}])[0].get("projectId")
            if not project_id:
                return {
                    "valid": False,
                    "errors": ["No project ID returned"],
                    "project_id": None,
                    "compile_id": None
                }

            self._temp_projects.append(project_id)
            self.logger.info(f"Created project {project_id}")

            # Upload main.py
            main_response = await self.api.create_file(project_id, "main.py", code)
            if not main_response.success:
                return {
                    "valid": False,
                    "errors": main_response.errors or ["Failed to upload main.py"],
                    "project_id": project_id,
                    "compile_id": None
                }

            # Upload additional files
            if files:
                for filename, content in files.items():
                    file_response = await self.api.create_file(project_id, filename, content)
                    if not file_response.success:
                        self.logger.warning(f"Failed to upload {filename}: {file_response.errors}")

            # Compile
            compile_result = await self._compile_and_wait(project_id)

            return {
                "valid": compile_result.success,
                "errors": compile_result.errors,
                "logs": compile_result.logs,
                "project_id": project_id,
                "compile_id": compile_result.compile_id,
                "state": compile_result.state
            }

        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return {
                "valid": False,
                "errors": [str(e)],
                "project_id": None,
                "compile_id": None
            }

    async def _compile_and_wait(
        self,
        project_id: int,
        timeout: int = 120,
        poll_interval: float = 2.0
    ) -> CompileResult:
        """Compile a project and wait for completion."""
        # Start compilation
        compile_response = await self.api.create_compile(project_id)

        if not compile_response.success:
            return CompileResult(
                success=False,
                project_id=project_id,
                errors=compile_response.errors or ["Failed to start compilation"]
            )

        compile_id = compile_response.data.get("compileId", "")
        state = compile_response.data.get("state", "")

        # If already complete
        if state == CompileState.BUILD_SUCCESS.value:
            return CompileResult(
                success=True,
                compile_id=compile_id,
                project_id=project_id,
                state=state
            )
        elif state == CompileState.BUILD_ERROR.value:
            return CompileResult(
                success=False,
                compile_id=compile_id,
                project_id=project_id,
                state=state,
                errors=compile_response.data.get("logs", [])
            )

        # Poll for completion
        start_time = time.time()
        while time.time() - start_time < timeout:
            await asyncio.sleep(poll_interval)

            status_response = await self.api.read_compile(project_id, compile_id)
            if not status_response.success:
                continue

            state = status_response.data.get("state", "")

            if state == CompileState.BUILD_SUCCESS.value:
                return CompileResult(
                    success=True,
                    compile_id=compile_id,
                    project_id=project_id,
                    state=state,
                    logs=status_response.data.get("logs", [])
                )
            elif state == CompileState.BUILD_ERROR.value:
                return CompileResult(
                    success=False,
                    compile_id=compile_id,
                    project_id=project_id,
                    state=state,
                    errors=status_response.data.get("logs", []),
                    logs=status_response.data.get("logs", [])
                )

        return CompileResult(
            success=False,
            compile_id=compile_id,
            project_id=project_id,
            state="Timeout",
            errors=[f"Compilation timed out after {timeout} seconds"]
        )

    # -------------------------------------------------------------------------
    # Backtesting
    # -------------------------------------------------------------------------

    async def run_backtest(
        self,
        code: str,
        files: Optional[Dict[str, str]] = None,
        backtest_name: Optional[str] = None,
        project_name: Optional[str] = None,
        timeout: int = 600
    ) -> Dict[str, Any]:
        """
        Run a full backtest workflow: create project → upload → compile → backtest.

        Args:
            code: Main algorithm code
            files: Additional files {filename: content}
            backtest_name: Name for the backtest
            project_name: Name for the project
            timeout: Maximum time to wait for backtest completion

        Returns:
            Dict with backtest results and statistics
        """
        self.logger.info("Starting backtest workflow")

        # First validate/compile
        validation = await self.validate_code(code, files, project_name)

        if not validation["valid"]:
            return {
                "success": False,
                "phase": "compilation",
                "errors": validation["errors"],
                "statistics": {}
            }

        project_id = validation["project_id"]
        compile_id = validation["compile_id"]

        # Create backtest
        bt_name = backtest_name or f"Backtest_{datetime.now().strftime('%H%M%S')}"
        bt_response = await self.api.create_backtest(project_id, compile_id, bt_name)

        if not bt_response.success:
            return {
                "success": False,
                "phase": "backtest_create",
                "errors": bt_response.errors or ["Failed to create backtest"],
                "project_id": project_id,
                "statistics": {}
            }

        backtest_id = bt_response.data.get("backtestId", "")
        self.logger.info(f"Created backtest {backtest_id}")

        # Wait for completion
        result = await self._wait_for_backtest(project_id, backtest_id, timeout)

        return {
            "success": result.success,
            "phase": "completed" if result.success else "backtest_run",
            "backtest_id": result.backtest_id,
            "project_id": project_id,
            "name": result.name,
            "completed": result.completed,
            "progress": result.progress,
            "statistics": result.statistics,
            "runtime_statistics": result.runtime_statistics,
            "sharpe_ratio": result.sharpe_ratio,
            "total_return": result.total_return,
            "drawdown": result.drawdown,
            "error": result.error,
            "errors": [result.error] if result.error else []
        }

    async def _wait_for_backtest(
        self,
        project_id: int,
        backtest_id: str,
        timeout: int = 600,
        poll_interval: float = 5.0
    ) -> BacktestResult:
        """Wait for a backtest to complete."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            response = await self.api.read_backtest(project_id, backtest_id)

            if not response.success:
                await asyncio.sleep(poll_interval)
                continue

            data = response.data
            progress = data.get("progress", 0)
            completed = data.get("completed", False) or progress >= 1.0

            if completed:
                result_data = data.get("result", {})
                statistics = result_data.get("Statistics", {})
                runtime_stats = result_data.get("RuntimeStatistics", {})

                # Extract key metrics
                sharpe = None
                total_return = None
                drawdown = None

                if statistics:
                    sharpe_str = statistics.get("Sharpe Ratio", "")
                    if sharpe_str:
                        try:
                            sharpe = float(sharpe_str)
                        except (ValueError, TypeError):
                            pass

                    return_str = statistics.get("Net Profit", statistics.get("Total Net Profit", ""))
                    if return_str:
                        try:
                            total_return = float(return_str.replace("%", "").replace("$", "").replace(",", ""))
                        except (ValueError, TypeError):
                            pass

                    dd_str = statistics.get("Drawdown", "")
                    if dd_str:
                        try:
                            drawdown = float(dd_str.replace("%", ""))
                        except (ValueError, TypeError):
                            pass

                return BacktestResult(
                    success=True,
                    backtest_id=backtest_id,
                    name=data.get("name", ""),
                    project_id=project_id,
                    completed=True,
                    progress=1.0,
                    statistics=statistics,
                    runtime_statistics=runtime_stats,
                    sharpe_ratio=sharpe,
                    total_return=total_return,
                    drawdown=drawdown
                )

            # Check for error state
            if data.get("error"):
                return BacktestResult(
                    success=False,
                    backtest_id=backtest_id,
                    project_id=project_id,
                    progress=progress,
                    error=data.get("error", "Unknown error")
                )

            self.logger.debug(f"Backtest progress: {progress * 100:.1f}%")
            await asyncio.sleep(poll_interval)

        return BacktestResult(
            success=False,
            backtest_id=backtest_id,
            project_id=project_id,
            error=f"Backtest timed out after {timeout} seconds"
        )

    # -------------------------------------------------------------------------
    # Project Management
    # -------------------------------------------------------------------------

    async def list_projects(self) -> Dict[str, Any]:
        """List all projects in the account."""
        response = await self.api.list_projects()

        if not response.success:
            return {"success": False, "projects": [], "errors": response.errors}

        projects = []
        for p in response.data.get("projects", []):
            projects.append({
                "project_id": p.get("projectId"),
                "name": p.get("name"),
                "created": p.get("created"),
                "modified": p.get("modified"),
                "language": p.get("language", "Py")
            })

        return {"success": True, "projects": projects, "count": len(projects)}

    async def delete_project(self, project_id: int) -> Dict[str, Any]:
        """Delete a project."""
        response = await self.api.delete_project(project_id)
        return {
            "success": response.success,
            "project_id": project_id,
            "errors": response.errors
        }

    async def cleanup_temp_projects(self) -> Dict[str, Any]:
        """Delete all temporary projects created by this client."""
        deleted = []
        failed = []

        for project_id in self._temp_projects:
            result = await self.delete_project(project_id)
            if result["success"]:
                deleted.append(project_id)
            else:
                failed.append(project_id)

        self._temp_projects = failed  # Keep failed ones for retry

        return {
            "deleted": deleted,
            "failed": failed,
            "deleted_count": len(deleted)
        }

    # -------------------------------------------------------------------------
    # Live Trading (with safety warnings)
    # -------------------------------------------------------------------------

    async def deploy_live(
        self,
        project_id: int,
        compile_id: str,
        node_id: str,
        brokerage: str,
        brokerage_settings: Dict[str, Any],
        confirm: bool = False
    ) -> Dict[str, Any]:
        """
        Deploy algorithm for live trading.

        WARNING: This deploys real money trading. Use with extreme caution.

        Args:
            project_id: Project ID
            compile_id: Compile ID from successful compilation
            node_id: Live trading node ID
            brokerage: Brokerage name
            brokerage_settings: Brokerage-specific configuration
            confirm: Must be True to actually deploy

        Returns:
            Deployment result
        """
        if not confirm:
            return {
                "success": False,
                "error": "Live deployment requires confirm=True. This is a safety measure.",
                "warning": "Live trading involves real money. Ensure thorough testing first."
            }

        self.logger.warning(f"Deploying live algorithm for project {project_id}")

        settings = {
            "brokerage": brokerage,
            **brokerage_settings
        }

        response = await self.api.create_live(project_id, compile_id, node_id, settings)

        return {
            "success": response.success,
            "live_algorithm_id": response.data.get("liveAlgorithmId"),
            "deployed": response.data.get("deployed"),
            "errors": response.errors
        }


# ============================================================================
# MCP Server Implementation
# ============================================================================

class QuantConnectMCPServer:
    """
    MCP-compliant server exposing QuantConnect capabilities.

    Implements the Model Context Protocol (MCP) specification for tool use.
    Uses stdio transport for communication with MCP clients like Claude Code.
    """

    def __init__(
        self,
        user_id: Optional[str] = None,
        api_token: Optional[str] = None
    ):
        """
        Initialize the MCP server.

        Args:
            user_id: QuantConnect user ID (or set QC_USER_ID env var)
            api_token: QuantConnect API token (or set QC_API_TOKEN env var)
        """
        self.user_id = user_id or os.getenv("QC_USER_ID")
        self.api_token = api_token or os.getenv("QC_API_TOKEN")
        self.client: Optional[QuantConnectMCPClient] = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self._tools = self._define_tools()

    def _define_tools(self) -> Dict[str, MCPTool]:
        """Define available MCP tools."""
        return {
            "qc_validate_code": MCPTool(
                name="qc_validate_code",
                description="Validate QuantConnect algorithm code by compiling it on QuantConnect servers. Returns compilation errors if any.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The main algorithm code (main.py content)"
                        },
                        "files": {
                            "type": "object",
                            "description": "Additional files as {filename: content} dict",
                            "additionalProperties": {"type": "string"}
                        }
                    },
                    "required": ["code"]
                },
                handler=self._handle_validate_code
            ),
            "qc_run_backtest": MCPTool(
                name="qc_run_backtest",
                description="Run a full backtest on QuantConnect. Creates project, uploads code, compiles, and runs backtest. Returns performance statistics.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The main algorithm code"
                        },
                        "files": {
                            "type": "object",
                            "description": "Additional files as {filename: content}",
                            "additionalProperties": {"type": "string"}
                        },
                        "backtest_name": {
                            "type": "string",
                            "description": "Name for the backtest (optional)"
                        }
                    },
                    "required": ["code"]
                },
                handler=self._handle_run_backtest
            ),
            "qc_list_projects": MCPTool(
                name="qc_list_projects",
                description="List all QuantConnect projects in the account.",
                input_schema={
                    "type": "object",
                    "properties": {}
                },
                handler=self._handle_list_projects
            ),
            "qc_delete_project": MCPTool(
                name="qc_delete_project",
                description="Delete a QuantConnect project by ID.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "integer",
                            "description": "The project ID to delete"
                        }
                    },
                    "required": ["project_id"]
                },
                handler=self._handle_delete_project
            ),
            "qc_verify_credentials": MCPTool(
                name="qc_verify_credentials",
                description="Verify that QuantConnect API credentials are valid.",
                input_schema={
                    "type": "object",
                    "properties": {}
                },
                handler=self._handle_verify_credentials
            )
        }

    async def _ensure_client(self):
        """Ensure the QuantConnect client is initialized."""
        if self.client is None:
            self.client = QuantConnectMCPClient(self.user_id, self.api_token)

    async def _handle_validate_code(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle validate_code tool call."""
        await self._ensure_client()
        return await self.client.validate_code(
            code=arguments["code"],
            files=arguments.get("files")
        )

    async def _handle_run_backtest(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle run_backtest tool call."""
        await self._ensure_client()
        return await self.client.run_backtest(
            code=arguments["code"],
            files=arguments.get("files"),
            backtest_name=arguments.get("backtest_name")
        )

    async def _handle_list_projects(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list_projects tool call."""
        await self._ensure_client()
        return await self.client.list_projects()

    async def _handle_delete_project(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle delete_project tool call."""
        await self._ensure_client()
        return await self.client.delete_project(arguments["project_id"])

    async def _handle_verify_credentials(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle verify_credentials tool call."""
        await self._ensure_client()
        return await self.client.verify_credentials()

    def get_tools_list(self) -> List[Dict[str, Any]]:
        """Get list of available tools in MCP format."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            }
            for tool in self._tools.values()
        ]

    async def handle_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle an MCP tool call.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool result as dict
        """
        if tool_name not in self._tools:
            return {
                "error": f"Unknown tool: {tool_name}",
                "available_tools": list(self._tools.keys())
            }

        tool = self._tools[tool_name]

        try:
            result = await tool.handler(arguments)
            return result
        except Exception as e:
            self.logger.error(f"Tool {tool_name} failed: {e}")
            return {
                "error": str(e),
                "tool": tool_name
            }

    async def run_stdio(self):
        """
        Run the MCP server using stdio transport.

        This is the main entry point for running as an MCP server.
        Reads JSON-RPC messages from stdin, processes them, and writes responses to stdout.
        """
        self.logger.info("Starting QuantConnect MCP Server (stdio)")

        # Send server info
        server_info = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "quantconnect-mcp",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        }

        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        writer = asyncio.StreamWriter(writer_transport, writer_protocol, reader, asyncio.get_event_loop())

        try:
            while True:
                line = await reader.readline()
                if not line:
                    break

                try:
                    message = json.loads(line.decode())
                    response = await self._handle_message(message)

                    if response:
                        writer.write((json.dumps(response) + "\n").encode())
                        await writer.drain()

                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON: {e}")

        except asyncio.CancelledError:
            pass
        finally:
            if self.client:
                await self.client.close()

    async def _handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle an incoming JSON-RPC message."""
        method = message.get("method", "")
        msg_id = message.get("id")
        params = message.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "quantconnect-mcp",
                        "version": "1.0.0"
                    },
                    "capabilities": {
                        "tools": {}
                    }
                }
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": self.get_tools_list()
                }
            }

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})

            result = await self.handle_tool_call(tool_name, arguments)

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }

        elif method == "shutdown":
            if self.client:
                await self.client.close()
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {}
            }

        return None


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    """CLI entry point for running the MCP server."""
    import argparse

    parser = argparse.ArgumentParser(description="QuantConnect MCP Server")
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="Run in stdio mode for MCP communication"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run a test to verify credentials"
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("quantconnect_mcp.log")]
    )

    if args.test:
        async def test():
            async with QuantConnectMCPClient() as client:
                result = await client.verify_credentials()
                print(json.dumps(result, indent=2))

        asyncio.run(test())

    elif args.stdio:
        server = QuantConnectMCPServer()
        asyncio.run(server.run_stdio())

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
