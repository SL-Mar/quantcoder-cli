"""Alpha Agent - Generates trading signal logic."""

from .base import BaseAgent, AgentResult


class AlphaAgent(BaseAgent):
    """
    Specialized agent for alpha signal generation.

    Generates Alpha.py module with:
    - Technical indicators
    - Entry/exit signals
    - Signal strength calculation
    - Insight generation
    """

    @property
    def agent_name(self) -> str:
        return "AlphaAgent"

    @property
    def agent_description(self) -> str:
        return "Generates alpha signal generation logic"

    async def execute(
        self,
        strategy: str,
        indicators: str = "",
        strategy_summary: str = ""
    ) -> AgentResult:
        """
        Generate alpha signal code.

        Args:
            strategy: Strategy description (e.g., "20-day momentum")
            indicators: Specific indicators to use
            strategy_summary: Full strategy summary from paper

        Returns:
            AgentResult with Alpha.py code
        """
        self.logger.info(f"Generating alpha signals for: {strategy}")

        try:
            system_prompt = """You are a QuantConnect expert specializing in alpha models.

Your task is to generate an Alpha.py module that implements trading signals.

Requirements:
- Implement AlphaModel class
- Create Update() method that generates Insight objects
- Use QuantConnect indicators efficiently
- Handle data availability (check IsReady)
- Generate InsightDirection.Up/Down/Flat signals
- Add insight expiration (timedelta)
- Include clear comments

Use QuantConnect's Framework:
- from AlgorithmImports import *
- Return List[Insight]
- Use Insight.Price() for signals

Return ONLY the Python code for Alpha.py, no explanations."""

            user_prompt = f"""Generate alpha signal logic for:

Strategy: {strategy}

{f"Indicators: {indicators}" if indicators else ""}

{f"Strategy Summary: {strategy_summary}" if strategy_summary else ""}

Create a QuantConnect alpha model that:
1. Implements the strategy signals
2. Uses appropriate indicators
3. Generates Insight objects with direction and confidence
4. Handles edge cases (missing data, initialization)
5. Optimizes for performance

Generate complete Alpha.py code."""

            response = await self._generate_with_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3
            )

            code = self._extract_code(response)

            return AgentResult(
                success=True,
                code=code,
                filename="Alpha.py",
                message=f"Generated alpha signals for: {strategy}",
                data={"strategy": strategy}
            )

        except Exception as e:
            self.logger.error(f"Alpha generation error: {e}")
            return AgentResult(
                success=False,
                error=str(e)
            )
