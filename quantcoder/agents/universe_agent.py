"""Universe Agent - Generates stock selection logic."""

from .base import AgentResult, BaseAgent


class UniverseAgent(BaseAgent):
    """
    Specialized agent for universe selection logic.

    Generates Universe.py module for QuantConnect with:
    - Stock screening criteria
    - Coarse/fine universe selection
    - Dynamic universe updates
    """

    @property
    def agent_name(self) -> str:
        return "UniverseAgent"

    @property
    def agent_description(self) -> str:
        return "Generates universe selection logic for stock screening"

    async def execute(self, criteria: str, strategy_context: str = "") -> AgentResult:
        """
        Generate universe selection code.

        Args:
            criteria: Universe criteria (e.g., "S&P 500", "Top 100 by volume")
            strategy_context: Additional strategy context

        Returns:
            AgentResult with Universe.py code
        """
        self.logger.info(f"Generating universe selection for: {criteria}")

        try:
            system_prompt = """You are a QuantConnect expert specializing in universe selection.

Your task is to generate a Universe.py module that implements stock screening logic.

Requirements:
- Implement CustomUniverseSelectionModel class
- Use SelectCoarse for initial filtering (liquidity, dollar volume)
- Use SelectFine for detailed filtering (market cap, sector, fundamentals)
- Ensure efficient performance (limit universe size appropriately)
- Add clear comments explaining logic

Return ONLY the Python code for Universe.py, no explanations."""

            user_prompt = f"""Generate universe selection logic for:

Criteria: {criteria}

{f"Strategy Context: {strategy_context}" if strategy_context else ""}

Create a QuantConnect universe selection model that:
1. Filters stocks based on the criteria
2. Maintains reasonable universe size (100-500 stocks)
3. Updates universe periodically
4. Handles edge cases (delisted stocks, low liquidity)

Generate complete Universe.py code."""

            response = await self._generate_with_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,  # Lower for more deterministic code
            )

            code = self._extract_code(response)

            return AgentResult(
                success=True,
                code=code,
                filename="Universe.py",
                message=f"Generated universe selection for: {criteria}",
                data={"criteria": criteria},
            )

        except Exception as e:
            self.logger.error(f"Universe generation error: {e}")
            return AgentResult(success=False, error=str(e))
