"""
Persistence Layer for Evolution State
=====================================

Handles saving/loading of:
- Elite pool (best algorithms across all generations)
- Evolution state (for resuming interrupted evolutions)
- Generation history (for analysis and debugging)
"""

import json
import os
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime
import uuid


@dataclass
class Variant:
    """A single algorithm variant."""
    id: str
    generation: int
    code: str
    parent_ids: List[str]  # empty for baseline, 1 for mutation, 2 for crossover
    mutation_description: str  # what was changed
    metrics: Optional[Dict[str, float]] = None  # backtest results
    fitness: Optional[float] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'Variant':
        return cls(**data)


@dataclass
class GenerationRecord:
    """Record of a single generation."""
    generation_num: int
    variants: List[str]  # variant IDs
    best_fitness: float
    best_variant_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ElitePool:
    """
    Manages the elite pool - the best N algorithms ever seen.
    Ensures we never lose good solutions due to poor generations.
    """

    def __init__(self, max_size: int = 3):
        self.max_size = max_size
        self.variants: List[Variant] = []
        self.logger = logging.getLogger(f"quantcoder.{self.__class__.__name__}")

    def update(self, candidate: Variant) -> bool:
        """
        Try to add a candidate to the elite pool.
        Returns True if the candidate made it into the pool.
        """
        if candidate.fitness is None:
            self.logger.warning(f"Cannot add variant {candidate.id} to elite pool: no fitness score")
            return False

        # Check if it beats any existing elite
        if len(self.variants) < self.max_size:
            self.variants.append(candidate)
            self._sort_pool()
            self.logger.info(f"Added {candidate.id} to elite pool (pool not full)")
            return True

        # Pool is full - check if candidate beats the worst
        worst_elite = self.variants[-1]
        if candidate.fitness > worst_elite.fitness:
            self.variants[-1] = candidate
            self._sort_pool()
            self.logger.info(
                f"Replaced {worst_elite.id} (fitness={worst_elite.fitness:.4f}) "
                f"with {candidate.id} (fitness={candidate.fitness:.4f}) in elite pool"
            )
            return True

        return False

    def _sort_pool(self):
        """Sort pool by fitness (descending)."""
        self.variants.sort(key=lambda v: v.fitness or 0, reverse=True)

    def get_best(self) -> Optional[Variant]:
        """Get the best variant in the pool."""
        return self.variants[0] if self.variants else None

    def get_parents_for_next_gen(self) -> List[Variant]:
        """
        Get variants to use as parents for the next generation.
        Returns all elite variants for crossover/mutation.
        """
        return self.variants.copy()

    def to_dict(self) -> dict:
        return {
            'max_size': self.max_size,
            'variants': [v.to_dict() for v in self.variants]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ElitePool':
        pool = cls(max_size=data['max_size'])
        pool.variants = [Variant.from_dict(v) for v in data['variants']]
        return pool


class EvolutionState:
    """
    Complete state of an evolution run.
    Persisted to disk for resuming and analysis.
    """

    def __init__(
        self,
        evolution_id: Optional[str] = None,
        baseline_code: str = "",
        source_paper: str = "",
        config: Optional[dict] = None
    ):
        self.evolution_id = evolution_id or str(uuid.uuid4())[:8]
        self.baseline_code = baseline_code
        self.source_paper = source_paper
        self.config = config or {}

        self.elite_pool = ElitePool(max_size=config.get('elite_pool_size', 3) if config else 3)
        self.all_variants: Dict[str, Variant] = {}  # id -> Variant
        self.generation_history: List[GenerationRecord] = []

        self.current_generation = 0
        self.generations_without_improvement = 0
        self.status = "initialized"  # initialized, running, converged, completed, failed

        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

        self.logger = logging.getLogger(f"quantcoder.{self.__class__.__name__}")

    def add_variant(self, variant: Variant):
        """Add a variant to the history."""
        self.all_variants[variant.id] = variant
        self.elite_pool.update(variant)
        self.updated_at = datetime.now().isoformat()

    def record_generation(self, generation_num: int, variant_ids: List[str]):
        """Record completion of a generation."""
        variants_in_gen = [self.all_variants[vid] for vid in variant_ids if vid in self.all_variants]

        if not variants_in_gen:
            self.logger.warning(f"No variants found for generation {generation_num}")
            return

        best_variant = max(variants_in_gen, key=lambda v: v.fitness or 0)

        record = GenerationRecord(
            generation_num=generation_num,
            variants=variant_ids,
            best_fitness=best_variant.fitness or 0,
            best_variant_id=best_variant.id
        )
        self.generation_history.append(record)

        # Check for improvement
        if len(self.generation_history) >= 2:
            prev_best = self.generation_history[-2].best_fitness
            if best_variant.fitness <= prev_best:
                self.generations_without_improvement += 1
                self.logger.info(
                    f"Generation {generation_num}: No improvement "
                    f"({self.generations_without_improvement} consecutive)"
                )
            else:
                self.generations_without_improvement = 0
                self.logger.info(
                    f"Generation {generation_num}: Improved! "
                    f"Fitness {prev_best:.4f} -> {best_variant.fitness:.4f}"
                )

        self.current_generation = generation_num
        self.updated_at = datetime.now().isoformat()

    def should_stop(self, config) -> tuple:
        """
        Check if evolution should stop.
        Returns (should_stop, reason).
        """
        # Max generations reached
        if self.current_generation >= config.max_generations:
            return True, f"Reached max generations ({config.max_generations})"

        # No improvement for N generations
        if self.generations_without_improvement >= config.convergence_patience:
            return True, f"No improvement for {config.convergence_patience} generations"

        # Target fitness reached
        if config.target_sharpe and self.elite_pool.get_best():
            best = self.elite_pool.get_best()
            if best.metrics and best.metrics.get('sharpe_ratio', 0) >= config.target_sharpe:
                return True, f"Target Sharpe ratio ({config.target_sharpe}) achieved"

        return False, ""

    def save(self, path: str):
        """Save state to disk."""
        data = {
            'evolution_id': self.evolution_id,
            'baseline_code': self.baseline_code,
            'source_paper': self.source_paper,
            'config': self.config,
            'elite_pool': self.elite_pool.to_dict(),
            'all_variants': {k: v.to_dict() for k, v in self.all_variants.items()},
            'generation_history': [asdict(g) for g in self.generation_history],
            'current_generation': self.current_generation,
            'generations_without_improvement': self.generations_without_improvement,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

        self.logger.info(f"Evolution state saved to {path}")

    @classmethod
    def load(cls, path: str) -> 'EvolutionState':
        """Load state from disk."""
        with open(path, 'r') as f:
            data = json.load(f)

        state = cls(
            evolution_id=data['evolution_id'],
            baseline_code=data['baseline_code'],
            source_paper=data['source_paper'],
            config=data['config']
        )

        state.elite_pool = ElitePool.from_dict(data['elite_pool'])
        state.all_variants = {k: Variant.from_dict(v) for k, v in data['all_variants'].items()}
        state.generation_history = [GenerationRecord(**g) for g in data['generation_history']]
        state.current_generation = data['current_generation']
        state.generations_without_improvement = data['generations_without_improvement']
        state.status = data['status']
        state.created_at = data['created_at']
        state.updated_at = data['updated_at']

        return state

    def get_summary(self) -> str:
        """Get a human-readable summary of the evolution state."""
        best = self.elite_pool.get_best()
        return f"""
Evolution: {self.evolution_id}
Status: {self.status}
Generation: {self.current_generation}
Total Variants: {len(self.all_variants)}
Elite Pool Size: {len(self.elite_pool.variants)}
Best Fitness: {best.fitness:.4f if best and best.fitness else 'N/A'}
Best Variant: {best.id if best else 'N/A'}
Stagnation: {self.generations_without_improvement} generations
"""
