"""Tests for the quantcoder.agents module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from quantcoder.agents.base import AgentResult, BaseAgent
from quantcoder.agents.alpha_agent import AlphaAgent
from quantcoder.agents.universe_agent import UniverseAgent
from quantcoder.agents.risk_agent import RiskAgent
from quantcoder.agents.strategy_agent import StrategyAgent


class TestAgentResult:
    """Tests for AgentResult dataclass."""

    def test_success_result(self):
        """Test successful result creation."""
        result = AgentResult(
            success=True,
            data={"key": "value"},
            message="Operation completed",
            code="def main(): pass",
            filename="main.py"
        )
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.message == "Operation completed"
        assert result.code == "def main(): pass"
        assert result.filename == "main.py"

    def test_error_result(self):
        """Test error result creation."""
        result = AgentResult(
            success=False,
            error="Something went wrong"
        )
        assert result.success is False
        assert result.error == "Something went wrong"

    def test_str_success(self):
        """Test string representation for success."""
        result = AgentResult(success=True, message="Done")
        assert str(result) == "Done"

    def test_str_success_with_data(self):
        """Test string representation for success with data."""
        result = AgentResult(success=True, data="test_data")
        assert "test_data" in str(result)

    def test_str_error(self):
        """Test string representation for error."""
        result = AgentResult(success=False, error="Error occurred")
        assert str(result) == "Error occurred"

    def test_str_unknown_error(self):
        """Test string representation for unknown error."""
        result = AgentResult(success=False)
        assert str(result) == "Unknown error"


class TestBaseAgent:
    """Tests for BaseAgent class."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM provider."""
        llm = MagicMock()
        llm.chat = AsyncMock(return_value="Generated response")
        llm.get_model_name.return_value = "test-model"
        return llm

    def test_extract_code_with_python_block(self, mock_llm):
        """Test code extraction from markdown python block."""
        # Create concrete implementation for testing
        class TestAgent(BaseAgent):
            @property
            def agent_name(self):
                return "TestAgent"

            @property
            def agent_description(self):
                return "Test agent"

            async def execute(self, **kwargs):
                return AgentResult(success=True)

        agent = TestAgent(mock_llm)

        response = """Here's the code:
```python
def hello():
    return "Hello"
```
That's it."""

        code = agent._extract_code(response)
        assert code == 'def hello():\n    return "Hello"'

    def test_extract_code_with_generic_block(self, mock_llm):
        """Test code extraction from generic markdown block."""
        class TestAgent(BaseAgent):
            @property
            def agent_name(self):
                return "TestAgent"

            @property
            def agent_description(self):
                return "Test agent"

            async def execute(self, **kwargs):
                return AgentResult(success=True)

        agent = TestAgent(mock_llm)

        response = """```
def hello():
    pass
```"""

        code = agent._extract_code(response)
        assert "def hello():" in code

    def test_extract_code_no_block(self, mock_llm):
        """Test code extraction without markdown block."""
        class TestAgent(BaseAgent):
            @property
            def agent_name(self):
                return "TestAgent"

            @property
            def agent_description(self):
                return "Test agent"

            async def execute(self, **kwargs):
                return AgentResult(success=True)

        agent = TestAgent(mock_llm)

        response = "def hello(): pass"
        code = agent._extract_code(response)
        assert code == "def hello(): pass"

    def test_repr(self, mock_llm):
        """Test agent representation."""
        class TestAgent(BaseAgent):
            @property
            def agent_name(self):
                return "TestAgent"

            @property
            def agent_description(self):
                return "Test agent"

            async def execute(self, **kwargs):
                return AgentResult(success=True)

        agent = TestAgent(mock_llm)
        assert "TestAgent" in repr(agent)
        assert "test-model" in repr(agent)

    @pytest.mark.asyncio
    async def test_generate_with_llm(self, mock_llm):
        """Test LLM generation helper."""
        class TestAgent(BaseAgent):
            @property
            def agent_name(self):
                return "TestAgent"

            @property
            def agent_description(self):
                return "Test agent"

            async def execute(self, **kwargs):
                return AgentResult(success=True)

        agent = TestAgent(mock_llm)

        result = await agent._generate_with_llm(
            system_prompt="You are a helper",
            user_prompt="Hello"
        )

        assert result == "Generated response"
        mock_llm.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_llm_error(self, mock_llm):
        """Test LLM generation error handling."""
        mock_llm.chat = AsyncMock(side_effect=Exception("API Error"))

        class TestAgent(BaseAgent):
            @property
            def agent_name(self):
                return "TestAgent"

            @property
            def agent_description(self):
                return "Test agent"

            async def execute(self, **kwargs):
                return AgentResult(success=True)

        agent = TestAgent(mock_llm)

        with pytest.raises(Exception) as exc_info:
            await agent._generate_with_llm(
                system_prompt="System",
                user_prompt="User"
            )
        assert "API Error" in str(exc_info.value)


class TestAlphaAgent:
    """Tests for AlphaAgent class."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM provider."""
        llm = MagicMock()
        llm.chat = AsyncMock(return_value="""```python
from AlgorithmImports import *

class MomentumAlpha(AlphaModel):
    def Update(self, algorithm, data):
        return []
```""")
        llm.get_model_name.return_value = "test-model"
        return llm

    def test_agent_properties(self, mock_llm):
        """Test agent name and description."""
        agent = AlphaAgent(mock_llm)
        assert agent.agent_name == "AlphaAgent"
        assert "alpha" in agent.agent_description.lower()

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_llm):
        """Test successful alpha generation."""
        agent = AlphaAgent(mock_llm)

        result = await agent.execute(
            strategy="20-day momentum",
            indicators="SMA, RSI"
        )

        assert result.success is True
        assert result.filename == "Alpha.py"
        assert result.code is not None
        assert "AlphaModel" in result.code

    @pytest.mark.asyncio
    async def test_execute_with_summary(self, mock_llm):
        """Test alpha generation with strategy summary."""
        agent = AlphaAgent(mock_llm)

        result = await agent.execute(
            strategy="momentum",
            strategy_summary="Buy on RSI below 30, sell above 70"
        )

        assert result.success is True
        mock_llm.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_error(self, mock_llm):
        """Test alpha generation error handling."""
        mock_llm.chat = AsyncMock(side_effect=Exception("Generation failed"))

        agent = AlphaAgent(mock_llm)
        result = await agent.execute(strategy="test")

        assert result.success is False
        assert "Generation failed" in result.error


class TestUniverseAgent:
    """Tests for UniverseAgent class."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM provider."""
        llm = MagicMock()
        llm.chat = AsyncMock(return_value="""```python
from AlgorithmImports import *

class CustomUniverse(UniverseSelectionModel):
    def SelectCoarse(self, algorithm, coarse):
        return [x.Symbol for x in coarse]
```""")
        llm.get_model_name.return_value = "test-model"
        return llm

    def test_agent_properties(self, mock_llm):
        """Test agent name and description."""
        agent = UniverseAgent(mock_llm)
        assert agent.agent_name == "UniverseAgent"
        assert "universe" in agent.agent_description.lower()

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_llm):
        """Test successful universe generation."""
        agent = UniverseAgent(mock_llm)

        result = await agent.execute(
            criteria="S&P 500 stocks"
        )

        assert result.success is True
        assert result.filename == "Universe.py"
        assert result.code is not None

    @pytest.mark.asyncio
    async def test_execute_with_context(self, mock_llm):
        """Test universe generation with context."""
        agent = UniverseAgent(mock_llm)

        result = await agent.execute(
            criteria="Top 100 by volume",
            strategy_context="Momentum trading"
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_error(self, mock_llm):
        """Test universe generation error handling."""
        mock_llm.chat = AsyncMock(side_effect=Exception("API timeout"))

        agent = UniverseAgent(mock_llm)
        result = await agent.execute(criteria="test")

        assert result.success is False
        assert "API timeout" in result.error


class TestRiskAgent:
    """Tests for RiskAgent class."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM provider."""
        llm = MagicMock()
        llm.chat = AsyncMock(return_value="""```python
from AlgorithmImports import *

class CustomRiskManagement(RiskManagementModel):
    def ManageRisk(self, algorithm, targets):
        return targets
```""")
        llm.get_model_name.return_value = "test-model"
        return llm

    def test_agent_properties(self, mock_llm):
        """Test agent name and description."""
        agent = RiskAgent(mock_llm)
        assert agent.agent_name == "RiskAgent"
        assert "risk" in agent.agent_description.lower()

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_llm):
        """Test successful risk management generation."""
        agent = RiskAgent(mock_llm)

        result = await agent.execute(
            risk_parameters="Max drawdown 10%"
        )

        assert result.success is True
        assert result.filename == "Risk.py"

    @pytest.mark.asyncio
    async def test_execute_error(self, mock_llm):
        """Test risk generation error handling."""
        mock_llm.chat = AsyncMock(side_effect=Exception("Error"))

        agent = RiskAgent(mock_llm)
        result = await agent.execute(risk_parameters="test")

        assert result.success is False


class TestStrategyAgent:
    """Tests for StrategyAgent class."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM provider."""
        llm = MagicMock()
        llm.chat = AsyncMock(return_value="""```python
from AlgorithmImports import *

class MomentumStrategy(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetCash(100000)
```""")
        llm.get_model_name.return_value = "test-model"
        return llm

    def test_agent_properties(self, mock_llm):
        """Test agent name and description."""
        agent = StrategyAgent(mock_llm)
        assert agent.agent_name == "StrategyAgent"
        assert "algorithm" in agent.agent_description.lower()

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_llm):
        """Test successful strategy generation."""
        agent = StrategyAgent(mock_llm)

        result = await agent.execute(
            strategy_name="Momentum Strategy",
            components={
                "universe": "class Universe: pass",
                "alpha": "class Alpha: pass",
            }
        )

        assert result.success is True
        assert result.filename == "Main.py"

    @pytest.mark.asyncio
    async def test_execute_error(self, mock_llm):
        """Test strategy generation error handling."""
        mock_llm.chat = AsyncMock(side_effect=Exception("Error"))

        agent = StrategyAgent(mock_llm)
        result = await agent.execute(strategy_name="test", components={})

        assert result.success is False
