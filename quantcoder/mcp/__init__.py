"""
QuantConnect MCP Integration Module.

This module provides MCP (Model Context Protocol) integration for QuantConnect,
enabling Claude Code and other MCP-compatible clients to interact with
QuantConnect's API for code validation, backtesting, and deployment.

Components:
- QuantConnectAPIClient: Low-level async API client
- QuantConnectMCPClient: High-level workflow client
- QuantConnectMCPServer: MCP-compliant server with stdio transport

Usage:
    # As a library
    from quantcoder.mcp import QuantConnectMCPClient

    async with QuantConnectMCPClient() as client:
        result = await client.validate_code(code)

    # As an MCP server
    python -m quantcoder.mcp.quantconnect_mcp --stdio

Environment Variables:
    QC_USER_ID: QuantConnect user ID
    QC_API_TOKEN: QuantConnect API token
"""

from .quantconnect_mcp import (
    # Data classes
    APIResponse,
    CompileResult,
    BacktestResult,
    ProjectInfo,
    CompileState,
    BacktestState,
    # Clients
    QuantConnectAPIClient,
    QuantConnectMCPClient,
    # Server
    QuantConnectMCPServer,
    MCPTool,
)

__all__ = [
    # Data classes
    "APIResponse",
    "CompileResult",
    "BacktestResult",
    "ProjectInfo",
    "CompileState",
    "BacktestState",
    # Clients
    "QuantConnectAPIClient",
    "QuantConnectMCPClient",
    # Server
    "QuantConnectMCPServer",
    "MCPTool",
]

__version__ = "1.0.0"
