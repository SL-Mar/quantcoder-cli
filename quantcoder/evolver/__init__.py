"""
Evolution Layer for QuantCoder
==============================

AlphaEvolve-inspired strategy optimization that explores the strategy space
using LLM-generated variations instead of traditional parameter grid search.

Adapted for QuantCoder v2.0 with async support and multi-provider LLM.

Components:
- EvolutionEngine: Main orchestrator for the evolution loop
- VariationGenerator: LLM-based strategy variation creator
- QCEvaluator: QuantConnect backtest integration
- ElitePool: Persistence layer for best-performing strategies
"""

from .config import EvolutionConfig, FitnessWeights
from .engine import EvolutionEngine
from .evaluator import QCEvaluator
from .persistence import ElitePool, EvolutionState, Variant
from .variation import VariationGenerator

__all__ = [
    "EvolutionEngine",
    "VariationGenerator",
    "QCEvaluator",
    "ElitePool",
    "EvolutionState",
    "Variant",
    "EvolutionConfig",
    "FitnessWeights",
]
