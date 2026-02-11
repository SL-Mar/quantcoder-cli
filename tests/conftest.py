"""Pytest fixtures and configuration for quantcoder tests."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.fixture
def mock_ollama_provider():
    """Create a mock OllamaProvider for testing."""
    from quantcoder.llm import OllamaProvider

    provider = MagicMock(spec=OllamaProvider)
    provider.get_model_name.return_value = "qwen2.5-coder:14b"
    provider.get_provider_name.return_value = "ollama"
    provider.chat = AsyncMock(return_value="Test response")
    provider.check_health = AsyncMock(return_value=True)
    provider.list_models = AsyncMock(return_value=["qwen2.5-coder:14b", "mistral"])
    return provider


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
    return '''
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
'''


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
    config.model.provider = "ollama"
    config.model.model = "qwen2.5-coder:14b"
    config.model.temperature = 0.5
    config.model.max_tokens = 1000
    config.model.code_model = "qwen2.5-coder:14b"
    config.model.reasoning_model = "mistral"
    config.model.ollama_base_url = "http://localhost:11434"
    config.model.ollama_timeout = 600
    config.tools.pdf_backend = "pdfplumber"
    config.home_dir = MagicMock()
    return config
