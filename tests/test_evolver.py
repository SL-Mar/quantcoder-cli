"""Tests for the quantcoder.evolver module."""

import tempfile
from pathlib import Path

from quantcoder.evolver.config import (
    EvolutionConfig,
    FitnessWeights,
    StoppingCondition,
)
from quantcoder.evolver.persistence import (
    ElitePool,
    EvolutionState,
    Variant,
)


class TestFitnessWeights:
    """Tests for FitnessWeights dataclass."""

    def test_default_weights(self):
        """Test default weight values."""
        weights = FitnessWeights()
        assert weights.sharpe_ratio == 0.4
        assert weights.max_drawdown == 0.3
        assert weights.total_return == 0.2
        assert weights.win_rate == 0.1

    def test_custom_weights(self):
        """Test custom weight values."""
        weights = FitnessWeights(
            sharpe_ratio=0.5, max_drawdown=0.25, total_return=0.15, win_rate=0.1
        )
        assert weights.sharpe_ratio == 0.5
        assert weights.max_drawdown == 0.25


class TestEvolutionConfig:
    """Tests for EvolutionConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = EvolutionConfig()
        assert config.variants_per_generation == 5
        assert config.elite_pool_size == 3
        assert config.max_generations == 10
        assert config.mutation_rate == 0.3

    def test_calculate_fitness_basic(self):
        """Test basic fitness calculation."""
        config = EvolutionConfig()
        metrics = {"sharpe_ratio": 2.0, "max_drawdown": 0.1, "total_return": 0.5, "win_rate": 0.6}

        fitness = config.calculate_fitness(metrics)
        assert fitness > 0

    def test_calculate_fitness_zero_metrics(self):
        """Test fitness calculation with zero metrics."""
        config = EvolutionConfig()
        metrics = {}

        fitness = config.calculate_fitness(metrics)
        # Should handle missing metrics gracefully
        assert fitness >= 0 or fitness < 0  # Just shouldn't error

    def test_calculate_fitness_high_drawdown_penalized(self):
        """Test that high drawdown results in lower fitness."""
        config = EvolutionConfig()

        low_drawdown = config.calculate_fitness(
            {"sharpe_ratio": 1.5, "max_drawdown": 0.1, "total_return": 0.3, "win_rate": 0.5}
        )

        high_drawdown = config.calculate_fitness(
            {"sharpe_ratio": 1.5, "max_drawdown": 0.5, "total_return": 0.3, "win_rate": 0.5}
        )

        assert low_drawdown > high_drawdown

    def test_from_env(self, monkeypatch):
        """Test creating config from environment."""
        monkeypatch.setenv("QC_USER_ID", "test-user")
        monkeypatch.setenv("QC_API_TOKEN", "test-token")
        monkeypatch.setenv("QC_PROJECT_ID", "12345")

        config = EvolutionConfig.from_env()
        assert config.qc_user_id == "test-user"
        assert config.qc_api_token == "test-token"
        assert config.qc_project_id == 12345


class TestStoppingCondition:
    """Tests for StoppingCondition enum."""

    def test_enum_values(self):
        """Test enum values exist."""
        assert StoppingCondition.MAX_GENERATIONS.value == "max_generations"
        assert StoppingCondition.NO_IMPROVEMENT.value == "no_improvement"
        assert StoppingCondition.TARGET_FITNESS.value == "target_fitness"
        assert StoppingCondition.MANUAL.value == "manual"


class TestVariant:
    """Tests for Variant dataclass."""

    def test_create_variant(self):
        """Test creating a variant."""
        variant = Variant(
            id="v001",
            generation=1,
            code="def main(): pass",
            parent_ids=[],
            mutation_description="Initial variant",
        )
        assert variant.id == "v001"
        assert variant.generation == 1
        assert variant.metrics is None
        assert variant.fitness is None
        assert variant.created_at is not None

    def test_variant_with_metrics(self):
        """Test variant with backtest metrics."""
        variant = Variant(
            id="v002",
            generation=2,
            code="code",
            parent_ids=["v001"],
            mutation_description="Mutation of v001",
            metrics={"sharpe_ratio": 1.5, "max_drawdown": 0.1},
            fitness=1.2,
        )
        assert variant.metrics["sharpe_ratio"] == 1.5
        assert variant.fitness == 1.2

    def test_to_dict(self):
        """Test variant serialization."""
        variant = Variant(
            id="v003", generation=1, code="code", parent_ids=[], mutation_description="test"
        )
        data = variant.to_dict()

        assert data["id"] == "v003"
        assert data["code"] == "code"
        assert "created_at" in data

    def test_from_dict(self):
        """Test variant deserialization."""
        data = {
            "id": "v004",
            "generation": 2,
            "code": "new code",
            "parent_ids": ["v001", "v002"],
            "mutation_description": "crossover",
            "metrics": {"sharpe_ratio": 2.0},
            "fitness": 1.8,
            "created_at": "2024-01-01T00:00:00",
        }
        variant = Variant.from_dict(data)

        assert variant.id == "v004"
        assert variant.generation == 2
        assert len(variant.parent_ids) == 2
        assert variant.fitness == 1.8


class TestElitePool:
    """Tests for ElitePool class."""

    def test_init(self):
        """Test pool initialization."""
        pool = ElitePool(max_size=5)
        assert pool.max_size == 5
        assert len(pool.variants) == 0

    def test_update_adds_to_empty_pool(self):
        """Test adding variant to empty pool."""
        pool = ElitePool(max_size=3)
        variant = Variant(
            id="v001",
            generation=1,
            code="code",
            parent_ids=[],
            mutation_description="test",
            fitness=1.0,
        )

        result = pool.update(variant)

        assert result is True
        assert len(pool.variants) == 1

    def test_update_rejects_no_fitness(self):
        """Test that variants without fitness are rejected."""
        pool = ElitePool(max_size=3)
        variant = Variant(
            id="v001",
            generation=1,
            code="code",
            parent_ids=[],
            mutation_description="test",
            fitness=None,
        )

        result = pool.update(variant)

        assert result is False
        assert len(pool.variants) == 0

    def test_update_replaces_worst(self):
        """Test that better variants replace worst in pool."""
        pool = ElitePool(max_size=2)

        # Fill pool
        for i, fitness in enumerate([1.0, 2.0]):
            pool.update(
                Variant(
                    id=f"v{i}",
                    generation=1,
                    code="code",
                    parent_ids=[],
                    mutation_description="test",
                    fitness=fitness,
                )
            )

        # Add better variant
        result = pool.update(
            Variant(
                id="v_better",
                generation=2,
                code="code",
                parent_ids=[],
                mutation_description="test",
                fitness=3.0,
            )
        )

        assert result is True
        assert len(pool.variants) == 2
        # Worst (1.0) should be replaced
        fitnesses = [v.fitness for v in pool.variants]
        assert 1.0 not in fitnesses
        assert 3.0 in fitnesses

    def test_update_rejects_worse_than_pool(self):
        """Test that worse variants don't enter full pool."""
        pool = ElitePool(max_size=2)

        # Fill pool with good variants
        for i in range(2):
            pool.update(
                Variant(
                    id=f"v{i}",
                    generation=1,
                    code="code",
                    parent_ids=[],
                    mutation_description="test",
                    fitness=5.0 + i,
                )
            )

        # Try to add worse variant
        result = pool.update(
            Variant(
                id="v_worse",
                generation=2,
                code="code",
                parent_ids=[],
                mutation_description="test",
                fitness=1.0,
            )
        )

        assert result is False
        assert len(pool.variants) == 2

    def test_get_best(self):
        """Test getting best variant."""
        pool = ElitePool(max_size=3)

        for fitness in [1.0, 3.0, 2.0]:
            pool.update(
                Variant(
                    id=f"v_{fitness}",
                    generation=1,
                    code="code",
                    parent_ids=[],
                    mutation_description="test",
                    fitness=fitness,
                )
            )

        best = pool.get_best()
        assert best is not None
        assert best.fitness == 3.0

    def test_get_best_empty_pool(self):
        """Test getting best from empty pool."""
        pool = ElitePool()
        assert pool.get_best() is None

    def test_get_parents_for_next_gen(self):
        """Test getting parents for breeding."""
        pool = ElitePool(max_size=3)

        for i in range(3):
            pool.update(
                Variant(
                    id=f"v{i}",
                    generation=1,
                    code="code",
                    parent_ids=[],
                    mutation_description="test",
                    fitness=float(i),
                )
            )

        parents = pool.get_parents_for_next_gen()
        assert len(parents) == 3
        # Should be a copy
        parents.append(
            Variant(id="new", generation=0, code="", parent_ids=[], mutation_description="")
        )
        assert len(pool.variants) == 3

    def test_serialization(self):
        """Test pool serialization and deserialization."""
        pool = ElitePool(max_size=2)
        pool.update(
            Variant(
                id="v1",
                generation=1,
                code="code1",
                parent_ids=[],
                mutation_description="test",
                fitness=1.5,
            )
        )

        data = pool.to_dict()
        restored = ElitePool.from_dict(data)

        assert restored.max_size == 2
        assert len(restored.variants) == 1
        assert restored.variants[0].fitness == 1.5


class TestEvolutionState:
    """Tests for EvolutionState class."""

    def test_init(self):
        """Test state initialization."""
        state = EvolutionState(baseline_code="def main(): pass", source_paper="arxiv:1234")

        assert state.evolution_id is not None
        assert state.baseline_code == "def main(): pass"
        assert state.status == "initialized"
        assert state.current_generation == 0

    def test_add_variant(self):
        """Test adding variant to state."""
        state = EvolutionState()
        variant = Variant(
            id="v001",
            generation=1,
            code="code",
            parent_ids=[],
            mutation_description="test",
            fitness=1.0,
        )

        state.add_variant(variant)

        assert "v001" in state.all_variants
        assert len(state.elite_pool.variants) == 1

    def test_record_generation(self):
        """Test recording generation completion."""
        state = EvolutionState()

        # Add variants
        for i in range(3):
            state.add_variant(
                Variant(
                    id=f"v{i}",
                    generation=1,
                    code="code",
                    parent_ids=[],
                    mutation_description="test",
                    fitness=float(i),
                )
            )

        state.record_generation(1, ["v0", "v1", "v2"])

        assert len(state.generation_history) == 1
        assert state.generation_history[0].best_fitness == 2.0
        assert state.current_generation == 1

    def test_generations_without_improvement(self):
        """Test tracking stagnation."""
        state = EvolutionState()

        # First generation
        state.add_variant(
            Variant(
                id="v1",
                generation=1,
                code="code",
                parent_ids=[],
                mutation_description="test",
                fitness=2.0,
            )
        )
        state.record_generation(1, ["v1"])

        # Second generation - same fitness (no improvement)
        state.add_variant(
            Variant(
                id="v2",
                generation=2,
                code="code",
                parent_ids=[],
                mutation_description="test",
                fitness=2.0,
            )
        )
        state.record_generation(2, ["v2"])

        assert state.generations_without_improvement == 1

    def test_should_stop_max_generations(self):
        """Test stopping at max generations."""
        config = EvolutionConfig(max_generations=5)
        state = EvolutionState()
        state.current_generation = 5

        should_stop, reason = state.should_stop(config)

        assert should_stop is True
        assert "max generations" in reason.lower()

    def test_should_stop_no_improvement(self):
        """Test stopping after no improvement."""
        config = EvolutionConfig(convergence_patience=3)
        state = EvolutionState()
        state.generations_without_improvement = 3

        should_stop, reason = state.should_stop(config)

        assert should_stop is True
        assert "no improvement" in reason.lower()

    def test_should_stop_target_reached(self):
        """Test stopping when target Sharpe is reached."""
        config = EvolutionConfig(target_sharpe=2.0)
        state = EvolutionState()

        state.add_variant(
            Variant(
                id="v1",
                generation=1,
                code="code",
                parent_ids=[],
                mutation_description="test",
                metrics={"sharpe_ratio": 2.5},
                fitness=2.5,
            )
        )

        should_stop, reason = state.should_stop(config)

        assert should_stop is True
        assert "sharpe" in reason.lower()

    def test_should_continue(self):
        """Test that evolution continues when no stopping condition met."""
        config = EvolutionConfig(max_generations=10, convergence_patience=5)
        state = EvolutionState()
        state.current_generation = 3
        state.generations_without_improvement = 2

        should_stop, reason = state.should_stop(config)

        assert should_stop is False
        assert reason == ""

    def test_save_and_load(self):
        """Test state persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"

            # Create and save state
            state = EvolutionState(baseline_code="def main(): pass", source_paper="test paper")
            state.add_variant(
                Variant(
                    id="v1",
                    generation=1,
                    code="variant code",
                    parent_ids=[],
                    mutation_description="initial",
                    fitness=1.5,
                )
            )
            state.record_generation(1, ["v1"])
            state.status = "running"

            state.save(str(path))

            # Verify file exists
            assert path.exists()

            # Load and verify
            loaded = EvolutionState.load(str(path))

            assert loaded.evolution_id == state.evolution_id
            assert loaded.baseline_code == "def main(): pass"
            assert loaded.status == "running"
            assert loaded.current_generation == 1
            assert "v1" in loaded.all_variants
            assert len(loaded.elite_pool.variants) == 1

    def test_get_summary(self):
        """Test getting human-readable summary."""
        state = EvolutionState(evolution_id="test123")
        state.status = "running"
        state.current_generation = 5

        state.add_variant(
            Variant(
                id="best",
                generation=5,
                code="code",
                parent_ids=[],
                mutation_description="test",
                fitness=2.5,
            )
        )

        summary = state.get_summary()

        assert "test123" in summary
        assert "running" in summary
        assert "2.5" in summary
