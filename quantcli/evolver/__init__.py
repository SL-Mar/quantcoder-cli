"""
Evolution Layer for QuantCoder CLI
===================================

AlphaEvolve-inspired strategy optimization that explores the strategy space
using LLM-generated variations instead of traditional parameter grid search.

Components:
- EvolutionEngine: Main orchestrator for the evolution loop
- VariationGenerator: LLM-based strategy variation creator
- QCEvaluator: QuantConnect backtest integration
- ElitePool: Persistence layer for best-performing strategies
"""

from .engine import EvolutionEngine
from .variation import VariationGenerator
from .evaluator import QCEvaluator
from .persistence import ElitePool, EvolutionState
from .config import EvolutionConfig

__all__ = [
    'EvolutionEngine',
    'VariationGenerator',
    'QCEvaluator',
    'ElitePool',
    'EvolutionState',
    'EvolutionConfig'
]
