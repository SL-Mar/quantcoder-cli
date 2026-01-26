"""Tests for the quantcoder.mcp module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from quantcoder.mcp.quantconnect_mcp import (
    QuantConnectMCPClient,
    QuantConnectMCPServer,
)


class TestQuantConnectMCPClient:
    """Tests for QuantConnectMCPClient class."""

    @pytest.fixture
    def client(self):
        """Create MCP client for testing."""
        return QuantConnectMCPClient(
            api_key="test-api-key",
            user_id="test-user-id"
        )

    def test_init(self, client):
        """Test client initialization."""
        assert client.api_key == "test-api-key"
        assert client.user_id == "test-user-id"
        assert client.base_url == "https://www.quantconnect.com/api/v2"

    def test_encode_credentials(self, client):
        """Test credential encoding."""
        encoded = client._encode_credentials()
        import base64
        decoded = base64.b64decode(encoded).decode()
        assert decoded == "test-user-id:test-api-key"

    @pytest.mark.asyncio
    async def test_validate_code_success(self, client):
        """Test successful code validation."""
        with patch.object(client, '_create_project', new_callable=AsyncMock) as mock_create:
            with patch.object(client, '_upload_files', new_callable=AsyncMock) as mock_upload:
                with patch.object(client, '_compile', new_callable=AsyncMock) as mock_compile:
                    mock_create.return_value = "project-123"
                    mock_compile.return_value = {
                        "success": True,
                        "compileId": "compile-456",
                        "errors": [],
                        "warnings": []
                    }

                    result = await client.validate_code("def main(): pass")

                    assert result["valid"] is True
                    assert result["project_id"] == "project-123"
                    mock_create.assert_called_once()
                    mock_upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_code_with_files(self, client):
        """Test code validation with additional files."""
        with patch.object(client, '_create_project', new_callable=AsyncMock) as mock_create:
            with patch.object(client, '_upload_files', new_callable=AsyncMock) as mock_upload:
                with patch.object(client, '_compile', new_callable=AsyncMock) as mock_compile:
                    mock_create.return_value = "project-123"
                    mock_compile.return_value = {"success": True}

                    result = await client.validate_code(
                        code="def main(): pass",
                        files={"Alpha.py": "class Alpha: pass"}
                    )

                    mock_upload.assert_called_with(
                        "project-123",
                        "def main(): pass",
                        {"Alpha.py": "class Alpha: pass"}
                    )

    @pytest.mark.asyncio
    async def test_validate_code_error(self, client):
        """Test code validation with error."""
        with patch.object(client, '_create_project', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("API Error")

            result = await client.validate_code("def main(): pass")

            assert result["valid"] is False
            assert "API Error" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_backtest_validation_fails(self, client):
        """Test backtest when validation fails."""
        with patch.object(client, 'validate_code', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = {
                "valid": False,
                "errors": ["Syntax error"]
            }

            result = await client.backtest(
                code="invalid code",
                start_date="2020-01-01",
                end_date="2020-12-31"
            )

            assert result["success"] is False
            assert "validation failed" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_backtest_success(self, client):
        """Test successful backtest."""
        with patch.object(client, 'validate_code', new_callable=AsyncMock) as mock_validate:
            with patch.object(client, '_call_api', new_callable=AsyncMock) as mock_api:
                with patch.object(client, '_wait_for_backtest', new_callable=AsyncMock) as mock_wait:
                    mock_validate.return_value = {
                        "valid": True,
                        "project_id": "proj-123",
                        "compile_id": "compile-456"
                    }
                    mock_api.return_value = {"backtestId": "backtest-789"}
                    mock_wait.return_value = {
                        "result": {
                            "Statistics": {"Sharpe Ratio": "1.5"},
                            "RuntimeStatistics": {},
                            "Charts": {}
                        }
                    }

                    result = await client.backtest(
                        code="def main(): pass",
                        start_date="2020-01-01",
                        end_date="2020-12-31"
                    )

                    assert result["success"] is True
                    assert result["backtest_id"] == "backtest-789"

    @pytest.mark.asyncio
    async def test_get_api_docs_with_topic(self, client):
        """Test getting API docs for known topic."""
        with patch('aiohttp.ClientSession') as mock_session_cls:
            # Create proper async context manager mocks
            mock_response = MagicMock()
            mock_response.status = 200

            # Mock for session.get() context manager
            mock_get_cm = AsyncMock()
            mock_get_cm.__aenter__.return_value = mock_response

            # Mock for ClientSession context manager
            mock_session = AsyncMock()
            mock_session.get.return_value = mock_get_cm
            mock_session_cls.return_value.__aenter__.return_value = mock_session

            result = await client.get_api_docs("indicators")

            assert "indicators" in result.lower() or "quantconnect" in result.lower()

    @pytest.mark.asyncio
    async def test_get_api_docs_unknown_topic(self, client):
        """Test getting API docs for unknown topic."""
        with patch('aiohttp.ClientSession') as mock_session_cls:
            # Create proper async context manager mocks
            mock_response = MagicMock()
            mock_response.status = 200

            # Mock for session.get() context manager
            mock_get_cm = AsyncMock()
            mock_get_cm.__aenter__.return_value = mock_response

            # Mock for ClientSession context manager
            mock_session = AsyncMock()
            mock_session.get.return_value = mock_get_cm
            mock_session_cls.return_value.__aenter__.return_value = mock_session

            result = await client.get_api_docs("unknown topic xyz")

            assert "quantconnect" in result.lower()

    @pytest.mark.asyncio
    async def test_deploy_live(self, client):
        """Test live deployment."""
        with patch.object(client, '_call_api', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = {
                "success": True,
                "liveAlgorithmId": "live-123"
            }

            result = await client.deploy_live(
                project_id="proj-123",
                compile_id="compile-456",
                node_id="node-789"
            )

            assert result["success"] is True
            assert result["live_id"] == "live-123"

    @pytest.mark.asyncio
    async def test_deploy_live_error(self, client):
        """Test live deployment error."""
        with patch.object(client, '_call_api', new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = Exception("Deployment failed")

            result = await client.deploy_live(
                project_id="proj-123",
                compile_id="compile-456",
                node_id="node-789"
            )

            assert result["success"] is False
            assert "Deployment failed" in result["error"]


class TestQuantConnectMCPServer:
    """Tests for QuantConnectMCPServer class."""

    @pytest.fixture
    def server(self):
        """Create MCP server for testing."""
        return QuantConnectMCPServer(
            api_key="test-api-key",
            user_id="test-user-id"
        )

    def test_init(self, server):
        """Test server initialization."""
        assert server.client is not None
        assert isinstance(server.client, QuantConnectMCPClient)

    @pytest.mark.asyncio
    async def test_start(self, server):
        """Test server start."""
        await server.start()

        assert server.is_running() is True
        assert len(server.get_tools()) == 4
        assert "validate_code" in server.get_tools()
        assert "backtest" in server.get_tools()
        assert "get_api_docs" in server.get_tools()
        assert "deploy_live" in server.get_tools()

    @pytest.mark.asyncio
    async def test_stop(self, server):
        """Test server stop."""
        await server.start()
        assert server.is_running() is True

        await server.stop()
        assert server.is_running() is False

    @pytest.mark.asyncio
    async def test_get_tools_before_start(self, server):
        """Test getting tools before server starts."""
        tools = server.get_tools()
        assert tools == {}

    @pytest.mark.asyncio
    async def test_handle_tool_call_validate(self, server):
        """Test handling validate_code tool call."""
        with patch.object(
            server.client,
            'validate_code',
            new_callable=AsyncMock
        ) as mock_validate:
            mock_validate.return_value = {"valid": True}

            result = await server.handle_tool_call(
                "validate_code",
                {"code": "def main(): pass"}
            )

            assert result == {"valid": True}
            mock_validate.assert_called_with(code="def main(): pass")

    @pytest.mark.asyncio
    async def test_handle_tool_call_backtest(self, server):
        """Test handling backtest tool call."""
        with patch.object(
            server.client,
            'backtest',
            new_callable=AsyncMock
        ) as mock_backtest:
            mock_backtest.return_value = {"success": True}

            result = await server.handle_tool_call(
                "backtest",
                {
                    "code": "def main(): pass",
                    "start_date": "2020-01-01",
                    "end_date": "2020-12-31"
                }
            )

            assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_handle_tool_call_docs(self, server):
        """Test handling get_api_docs tool call."""
        with patch.object(
            server.client,
            'get_api_docs',
            new_callable=AsyncMock
        ) as mock_docs:
            mock_docs.return_value = "Documentation text"

            result = await server.handle_tool_call(
                "get_api_docs",
                {"topic": "indicators"}
            )

            assert result == "Documentation text"

    @pytest.mark.asyncio
    async def test_handle_tool_call_deploy(self, server):
        """Test handling deploy_live tool call."""
        with patch.object(
            server.client,
            'deploy_live',
            new_callable=AsyncMock
        ) as mock_deploy:
            mock_deploy.return_value = {"success": True}

            result = await server.handle_tool_call(
                "deploy_live",
                {
                    "project_id": "123",
                    "compile_id": "456",
                    "node_id": "789"
                }
            )

            assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_handle_tool_call_unknown(self, server):
        """Test handling unknown tool call."""
        with pytest.raises(ValueError) as exc_info:
            await server.handle_tool_call("unknown_tool", {})
        assert "Unknown tool" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_tool_schemas(self, server):
        """Test tool schemas are properly defined."""
        await server.start()
        tools = server.get_tools()

        # Check validate_code schema
        validate_schema = tools["validate_code"]
        assert "code" in validate_schema["parameters"]
        assert "code" in validate_schema["required"]

        # Check backtest schema
        backtest_schema = tools["backtest"]
        assert "start_date" in backtest_schema["parameters"]
        assert "end_date" in backtest_schema["parameters"]

        # Check deploy_live schema
        deploy_schema = tools["deploy_live"]
        assert "project_id" in deploy_schema["required"]
        assert "compile_id" in deploy_schema["required"]
