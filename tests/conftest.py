"""Pytest fixtures and configuration for quantcoder tests."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client for testing."""
    client = MagicMock()

    # Mock chat completions response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test response"

    client.chat.completions.create.return_value = mock_response

    return client


@pytest.fixture
def sample_extracted_data():
    """Sample extracted data for testing."""
    return {
        "trading_signal": [
            "Buy when RSI crosses above 30",
            "Sell when RSI crosses below 70",
        ],
        "risk_management": [
            "Use 2% position sizing",
            "Set stop loss at 10% below entry",
        ],
    }


@pytest.fixture
def sample_pdf_text():
    """Sample text that would be extracted from a PDF."""
    return """
    Trading Strategy Overview

    This strategy uses a momentum-based approach with RSI indicators.
    Buy signals are generated when RSI crosses above 30 from oversold territory.
    Sell signals occur when RSI drops below 70 from overbought levels.

    Risk Management

    Position sizing is limited to 2% of portfolio per trade.
    Stop loss is set at 10% below entry price to limit downside risk.
    Maximum drawdown tolerance is 20%.
    """


@pytest.fixture
def sample_python_code():
    """Sample valid Python code for testing."""
    return """
from AlgorithmImports import *

class MomentumStrategy(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2023, 12, 31)
        self.SetCash(100000)
        self.symbol = self.AddEquity("SPY", Resolution.Daily).Symbol
        self.rsi = self.RSI(self.symbol, 14)

    def OnData(self, data):
        if not self.rsi.IsReady:
            return
        if self.rsi.Current.Value < 30:
            self.SetHoldings(self.symbol, 1.0)
        elif self.rsi.Current.Value > 70:
            self.Liquidate(self.symbol)
"""


@pytest.fixture
def invalid_python_code():
    """Sample invalid Python code for testing."""
    return """
def broken_function(
    # Missing closing parenthesis and body
"""


@pytest.fixture
def mock_config():
    """Mock configuration object for testing."""
    config = MagicMock()
    config.api_key = "sk-test-key-12345"
    config.load_api_key.return_value = "sk-test-key-12345"
    config.model.model = "gpt-4o"
    config.model.temperature = 0.5
    config.model.max_tokens = 1000
    return config


@pytest.fixture
def env_with_api_key(monkeypatch):
    """Set up environment with mock API key."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-12345")
    return "sk-test-key-12345"


@pytest.fixture
def env_without_api_key(monkeypatch):
    """Set up environment without API key."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
