"""
Evolution Engine
================

Main orchestrator for the evolution process.
Coordinates variation generation, evaluation, and elite pool management.

Adapted for QuantCoder v2.0 with async support and multi-provider LLM.
"""

import logging
import os
from typing import Optional, Callable, List
from dataclasses import asdict

from .config import EvolutionConfig
from .persistence import EvolutionState, Variant, ElitePool
from .variation import VariationGenerator
from .evaluator import QCEvaluator


class EvolutionEngine:
    """
    Main evolution engine that orchestrates the AlphaEvolve-inspired
    strategy optimization loop.

    Flow:
    1. Generate initial variations from baseline
    2. Evaluate each variant via QuantConnect backtest
    3. Update elite pool with best performers
    4. Generate next generation from elite pool
    5. Repeat until stopping condition met
    """

    def __init__(
        self,
        config: EvolutionConfig,
        state_dir: str = "data/evolutions"
    ):
        self.config = config
        self.state_dir = state_dir
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize components
        self.variation_generator = VariationGenerator(config)
        self.evaluator = QCEvaluator(config)

        # State
        self.state: Optional[EvolutionState] = None

        # Callbacks for progress reporting
        self.on_generation_complete: Optional[Callable] = None
        self.on_variant_evaluated: Optional[Callable] = None

    def _get_state_path(self, evolution_id: str) -> str:
        """Get path for state file."""
        return os.path.join(self.state_dir, f"{evolution_id}.json")

    def _save_state(self):
        """Save current state to disk."""
        if self.state and self.config.auto_save:
            path = self._get_state_path(self.state.evolution_id)
            self.state.save(path)

    async def evolve(
        self,
        baseline_code: str,
        source_paper: str = "",
        resume_id: Optional[str] = None
    ) -> EvolutionState:
        """
        Main evolution entry point.

        Args:
            baseline_code: The starting algorithm code
            source_paper: Reference to source paper (for logging)
            resume_id: Optional evolution ID to resume

        Returns:
            Final EvolutionState with results
        """
        # Initialize or resume state
        if resume_id:
            self.state = self._resume(resume_id)
            if not self.state:
                raise ValueError(f"Could not resume evolution {resume_id}")
        else:
            self.state = EvolutionState(
                baseline_code=baseline_code,
                source_paper=source_paper,
                config=asdict(self.config)
            )
            # Add baseline as first variant
            baseline_variant = Variant(
                id="baseline",
                generation=0,
                code=baseline_code,
                parent_ids=[],
                mutation_description="Original algorithm from research paper"
            )
            self.state.all_variants["baseline"] = baseline_variant

        self.state.status = "running"
        self._save_state()

        self.logger.info(f"Starting evolution {self.state.evolution_id}")
        self.logger.info(f"Config: {self.config.variants_per_generation} variants/gen, "
                        f"max {self.config.max_generations} generations")

        try:
            # Main evolution loop
            while True:
                generation = self.state.current_generation + 1
                self.logger.info(f"\n{'='*50}")
                self.logger.info(f"GENERATION {generation}")
                self.logger.info(f"{'='*50}")

                # Generate variations
                variants = await self._generate_generation(generation)

                if not variants:
                    self.logger.error("Failed to generate any variants")
                    break

                # Evaluate variants
                await self._evaluate_variants(variants)

                # Record generation
                variant_ids = [v.id for v in variants]
                self.state.record_generation(generation, variant_ids)

                # Save state
                self._save_state()

                # Report progress
                if self.on_generation_complete:
                    self.on_generation_complete(self.state, generation)

                # Check stopping conditions
                should_stop, reason = self.state.should_stop(self.config)
                if should_stop:
                    self.logger.info(f"Stopping evolution: {reason}")
                    self.state.status = "completed"
                    break

                # Adjust mutation rate if stagnating
                if self.config.increase_mutation_on_stagnation:
                    self._adjust_mutation_rate()

            self._save_state()
            self._log_final_results()

            return self.state

        except Exception as e:
            self.logger.error(f"Evolution failed: {e}")
            self.state.status = "failed"
            self._save_state()
            raise

    async def _generate_generation(self, generation: int) -> List[Variant]:
        """Generate variants for a new generation."""

        if generation == 1:
            # First generation: vary from baseline
            raw_variations = await self.variation_generator.generate_initial_variations(
                self.state.baseline_code,
                self.config.variants_per_generation
            )
        else:
            # Subsequent generations: vary from elite pool
            parents = self.state.elite_pool.get_parents_for_next_gen()

            if not parents:
                # Fallback to baseline if elite pool is empty
                self.logger.warning("Elite pool empty, falling back to baseline")
                baseline = self.state.all_variants.get("baseline")
                if baseline:
                    parents = [baseline]
                else:
                    return []

            raw_variations = await self.variation_generator.generate_variations(
                parents,
                self.config.variants_per_generation,
                generation
            )

        # Convert to Variant objects
        variants = []
        for i, (code, description, parent_ids) in enumerate(raw_variations):
            variant_id = f"v{generation}_{i+1}"
            variant = Variant(
                id=variant_id,
                generation=generation,
                code=code,
                parent_ids=parent_ids,
                mutation_description=description
            )
            variants.append(variant)
            self.state.all_variants[variant_id] = variant

        return variants

    async def _evaluate_variants(self, variants: List[Variant]):
        """Evaluate all variants and update their metrics/fitness."""

        for variant in variants:
            self.logger.info(f"Evaluating {variant.id}: {variant.mutation_description}")

            result = await self.evaluator.evaluate(variant.code, variant.id)

            if result:
                variant.metrics = result.to_metrics_dict()
                variant.fitness = self.config.calculate_fitness(variant.metrics)

                self.logger.info(
                    f"  -> Fitness: {variant.fitness:.4f} "
                    f"(Sharpe: {result.sharpe_ratio:.2f}, DD: {result.max_drawdown:.1%})"
                )

                # Update elite pool
                added = self.state.elite_pool.update(variant)
                if added:
                    self.logger.info(f"  -> Added to elite pool!")
            else:
                self.logger.warning(f"  -> Evaluation failed for {variant.id}")
                variant.fitness = -1  # Mark as failed

            # Callback
            if self.on_variant_evaluated:
                self.on_variant_evaluated(variant, result)

    def _adjust_mutation_rate(self):
        """Increase mutation rate if stuck to encourage exploration."""
        if self.state.generations_without_improvement > 0:
            # Increase mutation rate by 10% for each generation without improvement
            old_rate = self.config.mutation_rate
            new_rate = min(
                self.config.max_mutation_rate,
                old_rate + 0.1 * self.state.generations_without_improvement
            )

            if new_rate > old_rate:
                self.config.mutation_rate = new_rate
                self.logger.info(
                    f"Increased mutation rate: {old_rate:.2f} -> {new_rate:.2f} "
                    f"(stagnation: {self.state.generations_without_improvement} gens)"
                )

    def _resume(self, evolution_id: str) -> Optional[EvolutionState]:
        """Resume a previous evolution from saved state."""
        path = self._get_state_path(evolution_id)

        if not os.path.exists(path):
            self.logger.error(f"No saved state found at {path}")
            return None

        try:
            state = EvolutionState.load(path)
            self.logger.info(f"Resumed evolution {evolution_id} at generation {state.current_generation}")
            return state
        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")
            return None

    def _log_final_results(self):
        """Log final evolution results."""
        self.logger.info("\n" + "="*60)
        self.logger.info("EVOLUTION COMPLETE")
        self.logger.info("="*60)
        self.logger.info(self.state.get_summary())

        self.logger.info("\nElite Pool:")
        for i, variant in enumerate(self.state.elite_pool.variants, 1):
            self.logger.info(
                f"  {i}. {variant.id} (Gen {variant.generation}): "
                f"Fitness={variant.fitness:.4f}"
            )
            if variant.metrics:
                self.logger.info(
                    f"     Sharpe={variant.metrics.get('sharpe_ratio', 0):.2f}, "
                    f"Return={variant.metrics.get('total_return', 0):.1%}, "
                    f"MaxDD={variant.metrics.get('max_drawdown', 0):.1%}"
                )

    def get_best_variant(self) -> Optional[Variant]:
        """Get the best variant from the elite pool."""
        if self.state:
            return self.state.elite_pool.get_best()
        return None

    def export_best_code(self, output_path: str) -> bool:
        """Export the best variant's code to a file."""
        best = self.get_best_variant()
        if not best:
            self.logger.error("No best variant available")
            return False

        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(f"# Evolution: {self.state.evolution_id}\n")
                f.write(f"# Variant: {best.id} (Generation {best.generation})\n")
                f.write(f"# Fitness: {best.fitness:.4f}\n")
                if best.metrics:
                    f.write(f"# Sharpe: {best.metrics.get('sharpe_ratio', 0):.2f}\n")
                    f.write(f"# Max Drawdown: {best.metrics.get('max_drawdown', 0):.1%}\n")
                f.write(f"# Description: {best.mutation_description}\n")
                f.write("#\n")
                f.write(best.code)

            self.logger.info(f"Exported best variant to {output_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to export: {e}")
            return False


def create_evolution_engine(
    qc_user_id: str,
    qc_api_token: str,
    qc_project_id: int,
    **kwargs
) -> EvolutionEngine:
    """
    Factory function to create a configured EvolutionEngine.

    Example:
        engine = create_evolution_engine(
            qc_user_id="12345",
            qc_api_token="your_token",
            qc_project_id=67890,
            max_generations=5,
            variants_per_generation=3
        )
        result = await engine.evolve(baseline_code)
    """
    config = EvolutionConfig(
        qc_user_id=qc_user_id,
        qc_api_token=qc_api_token,
        qc_project_id=qc_project_id,
        **kwargs
    )

    return EvolutionEngine(config)
