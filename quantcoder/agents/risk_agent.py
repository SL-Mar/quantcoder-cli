"""Risk Agent - Generates risk management logic."""

from .base import AgentResult, BaseAgent


class RiskAgent(BaseAgent):
    """
    Specialized agent for risk management.

    Generates Risk.py module with:
    - Position sizing logic
    - Stop loss/take profit
    - Portfolio constraints
    - Volatility-based sizing
    """

    @property
    def agent_name(self) -> str:
        return "RiskAgent"

    @property
    def agent_description(self) -> str:
        return "Generates risk management and position sizing logic"

    async def execute(
        self, risk_parameters: str, alpha_info: str = "", strategy_context: str = ""
    ) -> AgentResult:
        """
        Generate risk management code.

        Args:
            risk_parameters: Risk params (e.g., "2% per trade, max 10 positions")
            alpha_info: Information about alpha signals
            strategy_context: Overall strategy context

        Returns:
            AgentResult with Risk.py code
        """
        self.logger.info(f"Generating risk management for: {risk_parameters}")

        try:
            system_prompt = """You are a QuantConnect expert specializing in risk management.

Your task is to generate a Risk.py module that implements risk controls.

Requirements:
- Implement RiskManagementModel class
- Create ManageRisk() method that adjusts PortfolioTarget objects
- Implement position sizing (volatility-based, equal weight, or custom)
- Add stop loss and take profit logic
- Enforce portfolio constraints (max leverage, max position size)
- Handle risk on both long and short positions
- Include clear comments

Use QuantConnect's Framework:
- from AlgorithmImports import *
- Return List[PortfolioTarget]
- Use RiskManagementModel base class

Return ONLY the Python code for Risk.py, no explanations."""

            user_prompt = f"""Generate risk management logic for:

Risk Parameters: {risk_parameters}

{f"Alpha Information: {alpha_info}" if alpha_info else ""}

{f"Strategy Context: {strategy_context}" if strategy_context else ""}

Create a QuantConnect risk management model that:
1. Implements position sizing based on parameters
2. Adds stop loss and take profit logic
3. Enforces portfolio constraints
4. Handles volatility-based sizing if appropriate
5. Manages both long and short positions

Generate complete Risk.py code."""

            response = await self._generate_with_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,  # Very deterministic for risk
            )

            code = self._extract_code(response)

            return AgentResult(
                success=True,
                code=code,
                filename="Risk.py",
                message=f"Generated risk management for: {risk_parameters}",
                data={"risk_parameters": risk_parameters},
            )

        except Exception as e:
            self.logger.error(f"Risk generation error: {e}")
            return AgentResult(success=False, error=str(e))
