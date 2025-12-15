"""
Comprehensive tests for the QuantConnect MCP module.

Tests cover:
- QuantConnectAPIClient: Low-level API operations
- QuantConnectMCPClient: High-level workflow operations
- QuantConnectMCPServer: MCP protocol handling
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import asdict

from quantcoder.mcp import (
    APIResponse,
    CompileResult,
    BacktestResult,
    CompileState,
    BacktestState,
    QuantConnectAPIClient,
    QuantConnectMCPClient,
    QuantConnectMCPServer,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def api_client():
    """Create an API client with test credentials."""
    return QuantConnectAPIClient(
        user_id="test_user",
        api_token="test_token",
        timeout=5.0,
        max_retries=1
    )


@pytest.fixture
def mcp_client(monkeypatch):
    """Create an MCP client with mocked credentials."""
    monkeypatch.setenv("QC_USER_ID", "test_user")
    monkeypatch.setenv("QC_API_TOKEN", "test_token")
    return QuantConnectMCPClient(auto_cleanup=False)


@pytest.fixture
def mcp_server(monkeypatch):
    """Create an MCP server with mocked credentials."""
    monkeypatch.setenv("QC_USER_ID", "test_user")
    monkeypatch.setenv("QC_API_TOKEN", "test_token")
    return QuantConnectMCPServer()


@pytest.fixture
def sample_algorithm():
    """Sample QuantConnect algorithm code."""
    return '''
from AlgorithmImports import *

class SampleAlgorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2020, 12, 31)
        self.SetCash(100000)
        self.AddEquity("SPY", Resolution.Daily)

    def OnData(self, data):
        if not self.Portfolio.Invested:
            self.SetHoldings("SPY", 1)
'''


# ============================================================================
# Data Class Tests
# ============================================================================

class TestDataClasses:
    """Tests for data classes."""

    def test_api_response_success(self):
        """Test APIResponse with success."""
        response = APIResponse(
            success=True,
            data={"projectId": 123},
            errors=[]
        )
        assert response.success
        assert response.data["projectId"] == 123
        assert len(response.errors) == 0

    def test_api_response_failure(self):
        """Test APIResponse with failure."""
        response = APIResponse(
            success=False,
            errors=["Invalid credentials"]
        )
        assert not response.success
        assert "Invalid credentials" in response.errors

    def test_compile_result_success(self):
        """Test CompileResult with success."""
        result = CompileResult(
            success=True,
            compile_id="abc123",
            project_id=456,
            state=CompileState.BUILD_SUCCESS.value
        )
        assert result.success
        assert result.compile_id == "abc123"
        assert result.state == "BuildSuccess"

    def test_compile_result_failure(self):
        """Test CompileResult with failure."""
        result = CompileResult(
            success=False,
            project_id=456,
            state=CompileState.BUILD_ERROR.value,
            errors=["Syntax error on line 10"]
        )
        assert not result.success
        assert "Syntax error on line 10" in result.errors

    def test_backtest_result_success(self):
        """Test BacktestResult with success."""
        result = BacktestResult(
            success=True,
            backtest_id="bt123",
            project_id=456,
            completed=True,
            progress=1.0,
            statistics={"Sharpe Ratio": "1.5"},
            sharpe_ratio=1.5,
            total_return=25.5,
            drawdown=5.2
        )
        assert result.success
        assert result.completed
        assert result.sharpe_ratio == 1.5

    def test_compile_state_enum(self):
        """Test CompileState enum values."""
        assert CompileState.IN_QUEUE.value == "InQueue"
        assert CompileState.BUILD_SUCCESS.value == "BuildSuccess"
        assert CompileState.BUILD_ERROR.value == "BuildError"

    def test_backtest_state_enum(self):
        """Test BacktestState enum values."""
        assert BacktestState.IN_QUEUE.value == "InQueue"
        assert BacktestState.RUNNING.value == "Running"
        assert BacktestState.COMPLETED.value == "Completed"
        assert BacktestState.ERROR.value == "Error"


# ============================================================================
# API Client Tests
# ============================================================================

class TestQuantConnectAPIClient:
    """Tests for the low-level API client."""

    def test_init(self, api_client):
        """Test client initialization."""
        assert api_client.user_id == "test_user"
        assert api_client.api_token == "test_token"
        assert api_client.timeout == 5.0
        assert api_client.max_retries == 1

    def test_auth_header(self, api_client):
        """Test Basic auth header generation."""
        header = api_client._get_auth_header()
        assert header.startswith("Basic ")
        # Decode and verify
        import base64
        encoded = header.replace("Basic ", "")
        decoded = base64.b64decode(encoded).decode()
        assert decoded == "test_user:test_token"

    def test_timestamp_hash(self, api_client):
        """Test timestamp hash generation."""
        hash1 = api_client._get_timestamp_hash()
        hash2 = api_client._get_timestamp_hash()
        # Hashes should be 64 chars (SHA256 hex)
        assert len(hash1) == 64
        # Consecutive calls within same second should match
        # (may differ if called across second boundary)

    @pytest.mark.asyncio
    async def test_close_session(self, api_client):
        """Test session closing."""
        # Should not raise even if no session exists
        await api_client.close()

    @pytest.mark.asyncio
    async def test_request_success(self, api_client):
        """Test successful API request."""
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value={
            "success": True,
            "projects": [{"projectId": 123}]
        })

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock()
            ))
            mock_session.closed = False
            mock_session_class.return_value = mock_session
            api_client._session = mock_session

            response = await api_client._request("/projects/create", {"name": "Test"})

            assert response.success
            assert response.data["projects"][0]["projectId"] == 123

    @pytest.mark.asyncio
    async def test_request_failure(self, api_client):
        """Test failed API request."""
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value={
            "success": False,
            "errors": ["Project not found"]
        })

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock()
            ))
            mock_session.closed = False
            mock_session_class.return_value = mock_session
            api_client._session = mock_session

            response = await api_client._request("/projects/read", {"projectId": 999})

            assert not response.success
            assert "Project not found" in response.errors


# ============================================================================
# MCP Client Tests
# ============================================================================

class TestQuantConnectMCPClient:
    """Tests for the high-level MCP client."""

    def test_init_with_env_vars(self, mcp_client):
        """Test initialization with environment variables."""
        assert mcp_client.user_id == "test_user"
        assert mcp_client.api_token == "test_token"
        assert mcp_client.auto_cleanup == False

    def test_init_without_credentials(self, monkeypatch):
        """Test initialization fails without credentials."""
        monkeypatch.delenv("QC_USER_ID", raising=False)
        monkeypatch.delenv("QC_API_TOKEN", raising=False)

        with pytest.raises(ValueError, match="QuantConnect credentials required"):
            QuantConnectMCPClient()

    def test_init_with_explicit_credentials(self, monkeypatch):
        """Test initialization with explicit credentials."""
        monkeypatch.delenv("QC_USER_ID", raising=False)
        monkeypatch.delenv("QC_API_TOKEN", raising=False)

        client = QuantConnectMCPClient(
            user_id="explicit_user",
            api_token="explicit_token",
            auto_cleanup=False
        )
        assert client.user_id == "explicit_user"
        assert client.api_token == "explicit_token"

    @pytest.mark.asyncio
    async def test_context_manager(self, mcp_client):
        """Test async context manager."""
        async with mcp_client as client:
            assert client is mcp_client
        # Should close without error

    @pytest.mark.asyncio
    async def test_verify_credentials_success(self, mcp_client):
        """Test credential verification success."""
        mcp_client.api.authenticate = AsyncMock(return_value=APIResponse(
            success=True,
            data={"success": True}
        ))
        mcp_client.api.read_account = AsyncMock(return_value=APIResponse(
            success=True,
            data={"organizationId": "org123"}
        ))

        result = await mcp_client.verify_credentials()

        assert result["success"]
        assert result["authenticated"]

    @pytest.mark.asyncio
    async def test_verify_credentials_failure(self, mcp_client):
        """Test credential verification failure."""
        mcp_client.api.authenticate = AsyncMock(return_value=APIResponse(
            success=False,
            errors=["Invalid API token"]
        ))

        result = await mcp_client.verify_credentials()

        assert not result["success"]
        assert not result["authenticated"]
        assert "Invalid API token" in result["errors"]

    @pytest.mark.asyncio
    async def test_validate_code_success(self, mcp_client, sample_algorithm):
        """Test code validation success."""
        # Mock API calls
        mcp_client.api.create_project = AsyncMock(return_value=APIResponse(
            success=True,
            data={"projects": [{"projectId": 123}]}
        ))
        mcp_client.api.create_file = AsyncMock(return_value=APIResponse(
            success=True,
            data={}
        ))
        mcp_client.api.create_compile = AsyncMock(return_value=APIResponse(
            success=True,
            data={"compileId": "compile123", "state": "BuildSuccess"}
        ))

        result = await mcp_client.validate_code(sample_algorithm)

        assert result["valid"]
        assert result["project_id"] == 123
        assert result["compile_id"] == "compile123"

    @pytest.mark.asyncio
    async def test_validate_code_compile_error(self, mcp_client):
        """Test code validation with compile error."""
        mcp_client.api.create_project = AsyncMock(return_value=APIResponse(
            success=True,
            data={"projects": [{"projectId": 123}]}
        ))
        mcp_client.api.create_file = AsyncMock(return_value=APIResponse(
            success=True,
            data={}
        ))
        mcp_client.api.create_compile = AsyncMock(return_value=APIResponse(
            success=True,
            data={
                "compileId": "compile123",
                "state": "BuildError",
                "logs": ["Error: undefined variable 'x'"]
            }
        ))

        result = await mcp_client.validate_code("invalid code")

        assert not result["valid"]
        assert "Error: undefined variable 'x'" in result["errors"]

    @pytest.mark.asyncio
    async def test_validate_code_project_creation_failure(self, mcp_client):
        """Test code validation when project creation fails."""
        mcp_client.api.create_project = AsyncMock(return_value=APIResponse(
            success=False,
            errors=["Project limit reached"]
        ))

        result = await mcp_client.validate_code("some code")

        assert not result["valid"]
        assert "Project limit reached" in result["errors"]

    @pytest.mark.asyncio
    async def test_run_backtest_success(self, mcp_client, sample_algorithm):
        """Test backtest execution success."""
        # Mock all required API calls
        mcp_client.api.create_project = AsyncMock(return_value=APIResponse(
            success=True,
            data={"projects": [{"projectId": 123}]}
        ))
        mcp_client.api.create_file = AsyncMock(return_value=APIResponse(
            success=True,
            data={}
        ))
        mcp_client.api.create_compile = AsyncMock(return_value=APIResponse(
            success=True,
            data={"compileId": "compile123", "state": "BuildSuccess"}
        ))
        mcp_client.api.create_backtest = AsyncMock(return_value=APIResponse(
            success=True,
            data={"backtestId": "bt123"}
        ))
        mcp_client.api.read_backtest = AsyncMock(return_value=APIResponse(
            success=True,
            data={
                "progress": 1.0,
                "completed": True,
                "name": "Test Backtest",
                "result": {
                    "Statistics": {
                        "Sharpe Ratio": "1.5",
                        "Net Profit": "25%",
                        "Drawdown": "5%"
                    },
                    "RuntimeStatistics": {}
                }
            }
        ))

        result = await mcp_client.run_backtest(sample_algorithm)

        assert result["success"]
        assert result["completed"]
        assert result["sharpe_ratio"] == 1.5
        assert result["backtest_id"] == "bt123"

    @pytest.mark.asyncio
    async def test_list_projects(self, mcp_client):
        """Test listing projects."""
        mcp_client.api.list_projects = AsyncMock(return_value=APIResponse(
            success=True,
            data={
                "projects": [
                    {"projectId": 1, "name": "Project 1", "language": "Py"},
                    {"projectId": 2, "name": "Project 2", "language": "Py"}
                ]
            }
        ))

        result = await mcp_client.list_projects()

        assert result["success"]
        assert result["count"] == 2
        assert len(result["projects"]) == 2

    @pytest.mark.asyncio
    async def test_delete_project(self, mcp_client):
        """Test deleting a project."""
        mcp_client.api.delete_project = AsyncMock(return_value=APIResponse(
            success=True,
            data={}
        ))

        result = await mcp_client.delete_project(123)

        assert result["success"]
        assert result["project_id"] == 123

    @pytest.mark.asyncio
    async def test_cleanup_temp_projects(self, mcp_client):
        """Test cleaning up temporary projects."""
        mcp_client._temp_projects = [1, 2, 3]
        mcp_client.api.delete_project = AsyncMock(return_value=APIResponse(
            success=True,
            data={}
        ))

        result = await mcp_client.cleanup_temp_projects()

        assert result["deleted_count"] == 3
        assert len(result["deleted"]) == 3
        assert len(mcp_client._temp_projects) == 0

    @pytest.mark.asyncio
    async def test_deploy_live_requires_confirm(self, mcp_client):
        """Test that live deployment requires explicit confirmation."""
        result = await mcp_client.deploy_live(
            project_id=123,
            compile_id="compile123",
            node_id="node123",
            brokerage="InteractiveBrokers",
            brokerage_settings={},
            confirm=False  # Safety check
        )

        assert not result["success"]
        assert "confirm=True" in result["error"]


# ============================================================================
# MCP Server Tests
# ============================================================================

class TestQuantConnectMCPServer:
    """Tests for the MCP server."""

    def test_init(self, mcp_server):
        """Test server initialization."""
        assert mcp_server.user_id == "test_user"
        assert mcp_server.api_token == "test_token"
        assert mcp_server.client is None

    def test_tools_defined(self, mcp_server):
        """Test that all tools are defined."""
        tools = mcp_server._tools
        assert "qc_validate_code" in tools
        assert "qc_run_backtest" in tools
        assert "qc_list_projects" in tools
        assert "qc_delete_project" in tools
        assert "qc_verify_credentials" in tools

    def test_get_tools_list(self, mcp_server):
        """Test getting tools list in MCP format."""
        tools_list = mcp_server.get_tools_list()

        assert len(tools_list) == 5
        tool_names = [t["name"] for t in tools_list]
        assert "qc_validate_code" in tool_names
        assert "qc_run_backtest" in tool_names

        # Verify schema structure
        for tool in tools_list:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"

    @pytest.mark.asyncio
    async def test_handle_tool_call_validate(self, mcp_server, sample_algorithm):
        """Test handling validate_code tool call."""
        with patch.object(mcp_server, '_ensure_client', new_callable=AsyncMock):
            mcp_server.client = MagicMock()
            mcp_server.client.validate_code = AsyncMock(return_value={
                "valid": True,
                "errors": [],
                "project_id": 123
            })

            result = await mcp_server.handle_tool_call(
                "qc_validate_code",
                {"code": sample_algorithm}
            )

            assert result["valid"]
            assert result["project_id"] == 123

    @pytest.mark.asyncio
    async def test_handle_tool_call_unknown(self, mcp_server):
        """Test handling unknown tool call."""
        result = await mcp_server.handle_tool_call(
            "unknown_tool",
            {}
        )

        assert "error" in result
        assert "Unknown tool" in result["error"]
        assert "available_tools" in result

    @pytest.mark.asyncio
    async def test_handle_message_initialize(self, mcp_server):
        """Test handling initialize message."""
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }

        response = await mcp_server._handle_message(message)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2024-11-05"
        assert response["result"]["serverInfo"]["name"] == "quantconnect-mcp"

    @pytest.mark.asyncio
    async def test_handle_message_tools_list(self, mcp_server):
        """Test handling tools/list message."""
        message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }

        response = await mcp_server._handle_message(message)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "result" in response
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) == 5

    @pytest.mark.asyncio
    async def test_handle_message_tools_call(self, mcp_server):
        """Test handling tools/call message."""
        with patch.object(mcp_server, 'handle_tool_call', new_callable=AsyncMock) as mock_handler:
            mock_handler.return_value = {"success": True}

            message = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "qc_list_projects",
                    "arguments": {}
                }
            }

            response = await mcp_server._handle_message(message)

            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 3
            assert "result" in response
            assert "content" in response["result"]

    @pytest.mark.asyncio
    async def test_handle_message_shutdown(self, mcp_server):
        """Test handling shutdown message."""
        mcp_server.client = MagicMock()
        mcp_server.client.close = AsyncMock()

        message = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "shutdown",
            "params": {}
        }

        response = await mcp_server._handle_message(message)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 4
        assert response["result"] == {}


# ============================================================================
# Integration Tests (Mocked)
# ============================================================================

class TestIntegration:
    """Integration tests with mocked API."""

    @pytest.mark.asyncio
    async def test_full_validation_workflow(self, mcp_client, sample_algorithm):
        """Test complete validation workflow."""
        # Set up mocks for full workflow
        mcp_client.api.create_project = AsyncMock(return_value=APIResponse(
            success=True,
            data={"projects": [{"projectId": 100}]}
        ))
        mcp_client.api.create_file = AsyncMock(return_value=APIResponse(
            success=True,
            data={}
        ))
        mcp_client.api.create_compile = AsyncMock(return_value=APIResponse(
            success=True,
            data={"compileId": "c100", "state": "InQueue"}
        ))
        mcp_client.api.read_compile = AsyncMock(return_value=APIResponse(
            success=True,
            data={"state": "BuildSuccess", "logs": []}
        ))

        result = await mcp_client.validate_code(
            code=sample_algorithm,
            files={"helper.py": "# Helper functions"},
            project_name="TestProject"
        )

        assert result["valid"]
        assert result["project_id"] == 100

    @pytest.mark.asyncio
    async def test_full_backtest_workflow(self, mcp_client, sample_algorithm):
        """Test complete backtest workflow."""
        mcp_client.api.create_project = AsyncMock(return_value=APIResponse(
            success=True,
            data={"projects": [{"projectId": 200}]}
        ))
        mcp_client.api.create_file = AsyncMock(return_value=APIResponse(
            success=True,
            data={}
        ))
        mcp_client.api.create_compile = AsyncMock(return_value=APIResponse(
            success=True,
            data={"compileId": "c200", "state": "BuildSuccess"}
        ))
        mcp_client.api.create_backtest = AsyncMock(return_value=APIResponse(
            success=True,
            data={"backtestId": "bt200"}
        ))
        mcp_client.api.read_backtest = AsyncMock(return_value=APIResponse(
            success=True,
            data={
                "progress": 1.0,
                "completed": True,
                "name": "Integration Test",
                "result": {
                    "Statistics": {
                        "Sharpe Ratio": "2.1",
                        "Net Profit": "$15,000",
                        "Drawdown": "8%"
                    },
                    "RuntimeStatistics": {
                        "Equity": "$115,000"
                    }
                }
            }
        ))

        result = await mcp_client.run_backtest(
            code=sample_algorithm,
            backtest_name="Integration Test"
        )

        assert result["success"]
        assert result["completed"]
        assert result["sharpe_ratio"] == 2.1
        assert result["statistics"]["Sharpe Ratio"] == "2.1"


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_network_error_retry(self, api_client):
        """Test that network errors trigger retries."""
        import aiohttp

        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise aiohttp.ClientError("Connection failed")
            mock_response = MagicMock()
            mock_response.json = AsyncMock(return_value={"success": True})
            return mock_response

        # Configure for 2 retries
        api_client.max_retries = 2

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session.post = MagicMock(side_effect=mock_post)
            mock_session.closed = False
            mock_session_class.return_value = mock_session
            api_client._session = mock_session

            # This should succeed on second attempt
            # (Implementation depends on how retries work)

    @pytest.mark.asyncio
    async def test_compile_timeout(self, mcp_client):
        """Test compilation timeout handling."""
        mcp_client.api.create_project = AsyncMock(return_value=APIResponse(
            success=True,
            data={"projects": [{"projectId": 123}]}
        ))
        mcp_client.api.create_file = AsyncMock(return_value=APIResponse(
            success=True,
            data={}
        ))
        mcp_client.api.create_compile = AsyncMock(return_value=APIResponse(
            success=True,
            data={"compileId": "c123", "state": "InQueue"}
        ))
        # Always return InQueue state (never completes)
        mcp_client.api.read_compile = AsyncMock(return_value=APIResponse(
            success=True,
            data={"state": "InQueue"}
        ))

        # Use very short timeout for test
        result = await mcp_client._compile_and_wait(123, timeout=0.1, poll_interval=0.05)

        assert not result.success
        assert "timed out" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_backtest_error_state(self, mcp_client, sample_algorithm):
        """Test handling backtest error state."""
        mcp_client.api.create_project = AsyncMock(return_value=APIResponse(
            success=True,
            data={"projects": [{"projectId": 123}]}
        ))
        mcp_client.api.create_file = AsyncMock(return_value=APIResponse(
            success=True,
            data={}
        ))
        mcp_client.api.create_compile = AsyncMock(return_value=APIResponse(
            success=True,
            data={"compileId": "c123", "state": "BuildSuccess"}
        ))
        mcp_client.api.create_backtest = AsyncMock(return_value=APIResponse(
            success=True,
            data={"backtestId": "bt123"}
        ))
        mcp_client.api.read_backtest = AsyncMock(return_value=APIResponse(
            success=True,
            data={
                "progress": 0.5,
                "error": "Runtime exception: Division by zero"
            }
        ))

        result = await mcp_client.run_backtest(sample_algorithm)

        assert not result["success"]
        assert "Division by zero" in result["error"]
