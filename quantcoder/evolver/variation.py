"""
LLM Variation Generator
=======================

The core LLM layer that generates strategy variations.
Implements mutation (single parent) and crossover (two parents) operations.

Adapted for QuantCoder v2.0 with async support and multi-provider LLM.
"""

import logging
import re
import random
from typing import List, Optional, Tuple

from .persistence import Variant
from .config import EvolutionConfig
from ..llm import LLMFactory, LLMProvider


class VariationGenerator:
    """
    Generates algorithm variations using LLM.
    Replaces traditional parameter optimization with structural exploration.
    """

    def __init__(self, config: EvolutionConfig, llm: Optional[LLMProvider] = None):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        # Use provided LLM or create one from config
        if llm:
            self.llm = llm
        else:
            # Get API key from environment
            import os
            api_key = os.getenv('OPENAI_API_KEY', '')
            self.llm = LLMFactory.create(
                config.llm_provider,
                api_key,
                config.model
            )

        # Variation strategies for mutation
        self.mutation_strategies = [
            "indicator_change",      # Swap SMA->EMA, add RSI, change MACD params
            "risk_management",       # Modify stop-loss, position sizing, leverage
            "entry_exit_logic",      # Change entry/exit conditions
            "universe_selection",    # Modify stock filtering criteria
            "timeframe_change",      # Change rebalance frequency
            "add_filter",            # Add volatility filter, trend filter, etc.
            "parameter_tune",        # Adjust numeric parameters
        ]

    async def generate_variations(
        self,
        parents: List[Variant],
        num_variations: int,
        generation: int
    ) -> List[Tuple[str, str, List[str]]]:
        """
        Generate N variations from parent algorithms.

        Returns list of tuples: (code, mutation_description, parent_ids)
        """
        if not parents:
            self.logger.error("No parents provided for variation generation")
            return []

        variations = []

        for i in range(num_variations):
            # Decide: mutation (1 parent) or crossover (2 parents)
            if len(parents) >= 2 and random.random() > self.config.mutation_rate:
                # Crossover
                parent1, parent2 = random.sample(parents, 2)
                code, description = await self._crossover(parent1, parent2)
                parent_ids = [parent1.id, parent2.id]
            else:
                # Mutation
                parent = random.choice(parents)
                strategy = random.choice(self.mutation_strategies)
                code, description = await self._mutate(parent, strategy)
                parent_ids = [parent.id]

            if code:
                variations.append((code, description, parent_ids))
                self.logger.info(f"Generated variation {i+1}/{num_variations}: {description}")
            else:
                self.logger.warning(f"Failed to generate variation {i+1}/{num_variations}")

        return variations

    async def _mutate(self, parent: Variant, strategy: str) -> Tuple[Optional[str], str]:
        """
        Generate a mutation of a single parent using specified strategy.
        """
        prompt = self._build_mutation_prompt(parent.code, strategy)

        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a QuantConnect algorithm expert. Generate variations of "
                        "trading strategies by modifying specific aspects while keeping "
                        "the core strategy concept intact. Always output valid Python code."
                    )
                },
                {"role": "user", "content": prompt}
            ]

            response = await self.llm.chat(
                messages=messages,
                temperature=self.config.temperature_variation,
                max_tokens=2000
            )

            code = self._extract_code(response)
            description = f"Mutation ({strategy}): {self._extract_description(response)}"

            return code, description

        except Exception as e:
            self.logger.error(f"LLM error during mutation: {e}")
            return None, f"Failed: {e}"

    async def _crossover(self, parent1: Variant, parent2: Variant) -> Tuple[Optional[str], str]:
        """
        Generate a crossover combining features of two parents.
        """
        prompt = self._build_crossover_prompt(parent1, parent2)

        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a QuantConnect algorithm expert. Combine the best features "
                        "of two trading strategies into a single coherent algorithm. "
                        "Always output valid Python code."
                    )
                },
                {"role": "user", "content": prompt}
            ]

            response = await self.llm.chat(
                messages=messages,
                temperature=self.config.temperature_variation,
                max_tokens=2000
            )

            code = self._extract_code(response)
            description = f"Crossover ({parent1.id} x {parent2.id}): {self._extract_description(response)}"

            return code, description

        except Exception as e:
            self.logger.error(f"LLM error during crossover: {e}")
            return None, f"Failed: {e}"

    def _build_mutation_prompt(self, code: str, strategy: str) -> str:
        """Build the prompt for mutation."""

        strategy_instructions = {
            "indicator_change": """
                Modify the technical indicators used:
                - Swap SMA for EMA or vice versa
                - Add or remove indicators (RSI, MACD, Bollinger Bands)
                - Change indicator periods/parameters
                - Add indicator confirmation requirements
            """,
            "risk_management": """
                Modify the risk management approach:
                - Change stop-loss type (fixed % -> trailing, ATR-based)
                - Adjust position sizing (fixed -> volatility-scaled)
                - Add or modify take-profit levels
                - Change maximum position limits
            """,
            "entry_exit_logic": """
                Modify entry and exit conditions:
                - Add or remove entry conditions
                - Change from market to limit orders
                - Add partial position exits
                - Modify signal confirmation requirements
            """,
            "universe_selection": """
                Modify stock/asset selection:
                - Change liquidity filters
                - Add momentum or value screens
                - Modify sector constraints
                - Change the number of holdings
            """,
            "timeframe_change": """
                Modify timing aspects:
                - Change rebalance frequency (daily -> weekly)
                - Add trading hour restrictions
                - Modify lookback periods
                - Add market regime filters
            """,
            "add_filter": """
                Add a new filter or condition:
                - Volatility filter (only trade in low/high vol)
                - Trend filter (only trade with trend)
                - Volume filter
                - Correlation filter
            """,
            "parameter_tune": """
                Adjust numeric parameters:
                - Change moving average periods
                - Adjust threshold values
                - Modify allocation percentages
                - Tune indicator parameters
            """
        }

        instruction = strategy_instructions.get(strategy, strategy_instructions["parameter_tune"])

        return f"""
Here is a QuantConnect trading algorithm:

```python
{code}
```

Generate a VARIATION of this algorithm by applying the following mutation strategy:

{instruction}

Requirements:
1. Keep the core strategy concept intact
2. Make meaningful changes (not just cosmetic)
3. Output complete, valid QuantConnect Python code
4. Briefly explain what you changed (1-2 sentences)

Output format:
CHANGES: [Brief description of what was changed]

```python
[Complete modified algorithm code]
```
"""

    def _build_crossover_prompt(self, parent1: Variant, parent2: Variant) -> str:
        """Build the prompt for crossover."""

        # Include performance context if available
        p1_context = ""
        p2_context = ""

        if parent1.metrics:
            p1_context = f"\nPerformance: Sharpe={parent1.metrics.get('sharpe_ratio', 'N/A')}, MaxDD={parent1.metrics.get('max_drawdown', 'N/A')}"
        if parent2.metrics:
            p2_context = f"\nPerformance: Sharpe={parent2.metrics.get('sharpe_ratio', 'N/A')}, MaxDD={parent2.metrics.get('max_drawdown', 'N/A')}"

        return f"""
Here are two QuantConnect trading algorithms that performed well:

ALGORITHM A ({parent1.id}):
{parent1.mutation_description}{p1_context}

```python
{parent1.code}
```

ALGORITHM B ({parent2.id}):
{parent2.mutation_description}{p2_context}

```python
{parent2.code}
```

Generate a NEW algorithm that COMBINES the best features of both:
- Take the strongest elements from each (indicators, risk management, logic)
- Create a coherent, unified strategy
- The result should be better than either parent alone

Requirements:
1. Output complete, valid QuantConnect Python code
2. Explain which features you took from each parent
3. Ensure the combination makes strategic sense

Output format:
CHANGES: [What was combined from each parent]

```python
[Complete combined algorithm code]
```
"""

    def _extract_code(self, content: str) -> Optional[str]:
        """Extract Python code from LLM response."""
        # Try to find code block
        code_match = re.search(r'```python(.*?)```', content, re.DOTALL | re.IGNORECASE)
        if code_match:
            return code_match.group(1).strip()

        # Try generic code block
        code_match = re.search(r'```(.*?)```', content, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        return None

    def _extract_description(self, content: str) -> str:
        """Extract the change description from LLM response."""
        # Look for CHANGES: line
        match = re.search(r'CHANGES?:\s*(.+?)(?:\n|```)', content, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Fallback: first line
        first_line = content.split('\n')[0]
        return first_line[:100] if first_line else "Variation generated"

    async def generate_initial_variations(
        self,
        baseline_code: str,
        num_variations: int
    ) -> List[Tuple[str, str, List[str]]]:
        """
        Generate initial variations from baseline (generation 0 -> 1).
        Uses diverse mutation strategies to explore the space.
        """
        self.logger.info(f"Generating {num_variations} initial variations from baseline")

        # Create a pseudo-variant for the baseline
        baseline_variant = Variant(
            id="baseline",
            generation=0,
            code=baseline_code,
            parent_ids=[],
            mutation_description="Original algorithm from research paper"
        )

        variations = []

        # Use different strategies for initial diversity
        strategies_to_use = self.mutation_strategies.copy()
        random.shuffle(strategies_to_use)

        for i in range(num_variations):
            strategy = strategies_to_use[i % len(strategies_to_use)]
            code, description = await self._mutate(baseline_variant, strategy)

            if code:
                variations.append((code, description, ["baseline"]))
                self.logger.info(f"Initial variation {i+1}: {description}")

        return variations
