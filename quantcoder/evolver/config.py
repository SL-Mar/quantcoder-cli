"""
Evolution Configuration
=======================

Configuration dataclasses for the evolution process.
Adapted for QuantCoder v2.0 with multi-provider LLM support.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class StoppingCondition(Enum):
    MAX_GENERATIONS = "max_generations"
    NO_IMPROVEMENT = "no_improvement"
    TARGET_FITNESS = "target_fitness"
    MANUAL = "manual"


@dataclass
class FitnessWeights:
    """Weights for multi-objective fitness calculation."""
    sharpe_ratio: float = 0.4
    max_drawdown: float = 0.3  # penalize high drawdown
    total_return: float = 0.2
    win_rate: float = 0.1


@dataclass
class EvolutionConfig:
    """Configuration for the evolution process."""

    # Population settings
    variants_per_generation: int = 5
    elite_pool_size: int = 3

    # Stopping conditions
    max_generations: int = 3
    convergence_patience: int = 3  # stop if no improvement for N generations
    target_sharpe: Optional[float] = None  # stop if Sharpe exceeds this

    # Mutation settings
    mutation_rate: float = 0.3  # probability of mutation vs crossover
    increase_mutation_on_stagnation: bool = True
    max_mutation_rate: float = 0.7

    # Fitness calculation
    fitness_weights: FitnessWeights = field(default_factory=FitnessWeights)

    # QuantConnect settings
    qc_user_id: Optional[str] = None
    qc_api_token: Optional[str] = None
    qc_project_id: Optional[int] = None
    backtest_start_date: str = "2020-01-01"
    backtest_end_date: str = "2023-12-31"
    initial_cash: int = 100000

    # LLM settings — Ollama local models
    llm_provider: str = "ollama"
    model: str = "qwen2.5-coder:14b"
    temperature_variation: float = 0.7  # higher for more diverse variations
    temperature_refinement: float = 0.3  # lower for precise fixes

    # Persistence
    auto_save: bool = True
    save_all_generations: bool = True  # save every generation or just elite

    def calculate_fitness(self, metrics: dict) -> float:
        """
        Calculate weighted fitness score from backtest metrics.
        Higher is better.
        """
        w = self.fitness_weights

        sharpe = metrics.get('sharpe_ratio', 0)
        drawdown = metrics.get('max_drawdown', 1)  # 0-1, lower is better
        returns = metrics.get('total_return', 0)
        win_rate = metrics.get('win_rate', 0)

        # Normalize and combine (drawdown inverted since lower is better)
        fitness = (
            w.sharpe_ratio * sharpe +
            w.max_drawdown * (1 - drawdown) +  # invert: 0 drawdown = 1.0 score
            w.total_return * returns +
            w.win_rate * win_rate
        )

        return fitness

    @classmethod
    def from_env(cls) -> 'EvolutionConfig':
        """Create config from environment variables."""
        import os
        return cls(
            qc_user_id=os.getenv('QC_USER_ID'),
            qc_api_token=os.getenv('QC_API_TOKEN'),
            qc_project_id=int(os.getenv('QC_PROJECT_ID', 0)) or None,
        )
