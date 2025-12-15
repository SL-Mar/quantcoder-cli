"""Strategy Agent - Generates main algorithm file."""

from typing import Dict
from .base import BaseAgent, AgentResult


class StrategyAgent(BaseAgent):
    """
    Specialized agent for main algorithm integration.

    Generates Main.py that:
    - Integrates Universe, Alpha, Risk models
    - Sets up algorithm parameters
    - Implements Initialize() and OnData()
    - Adds logging and monitoring
    """

    @property
    def agent_name(self) -> str:
        return "StrategyAgent"

    @property
    def agent_description(self) -> str:
        return "Generates main algorithm file integrating all components"

    async def execute(
        self,
        strategy_name: str,
        components: Dict[str, str],
        parameters: Dict[str, any] = None
    ) -> AgentResult:
        """
        Generate main algorithm code.

        Args:
            strategy_name: Name of the strategy
            components: Dict with component info (universe, alpha, risk)
            parameters: Algorithm parameters (dates, cash, etc.)

        Returns:
            AgentResult with Main.py code
        """
        self.logger.info(f"Generating main algorithm: {strategy_name}")

        try:
            params = parameters or {}
            start_date = params.get("start_date", "2020, 1, 1")
            end_date = params.get("end_date", "2023, 12, 31")
            cash = params.get("cash", 100000)

            system_prompt = """You are a QuantConnect expert specializing in algorithm integration.

Your task is to generate a Main.py file that integrates all strategy components.

Requirements:
- Import all required modules (Universe, Alpha, Risk)
- Implement QCAlgorithm class
- Create Initialize() method with:
  - Start/end dates
  - Initial cash
  - Universe selection model
  - Alpha model
  - Risk management model
  - Portfolio construction model
  - Execution model
- Add OnData() method if custom logic needed
- Add logging and monitoring
- Include clear comments

Use QuantConnect's Framework:
- from AlgorithmImports import *
- from Universe import CustomUniverseSelectionModel
- from Alpha import AlphaModel
- from Risk import RiskManagementModel

Return ONLY the Python code for Main.py, no explanations."""

            user_prompt = f"""Generate main algorithm file for:

Strategy Name: {strategy_name}

Components:
{self._format_components(components)}

Parameters:
- Start Date: {start_date}
- End Date: {end_date}
- Initial Cash: ${cash:,}

Create a complete QuantConnect algorithm that:
1. Imports and wires up all components
2. Sets algorithm parameters
3. Implements Initialize() method
4. Adds appropriate logging
5. Uses Framework architecture (SetAlpha, SetRiskManagement, etc.)

Generate complete Main.py code."""

            response = await self._generate_with_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3
            )

            code = self._extract_code(response)

            return AgentResult(
                success=True,
                code=code,
                filename="Main.py",
                message=f"Generated main algorithm: {strategy_name}",
                data={
                    "strategy_name": strategy_name,
                    "components": components
                }
            )

        except Exception as e:
            self.logger.error(f"Strategy generation error: {e}")
            return AgentResult(
                success=False,
                error=str(e)
            )

    def _format_components(self, components: Dict[str, str]) -> str:
        """Format components for prompt."""
        lines = []
        for comp_type, comp_info in components.items():
            lines.append(f"- {comp_type.title()}: {comp_info}")
        return "\n".join(lines)
