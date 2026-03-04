"""Tests for the optimization module."""

import pytest

pymoo = pytest.importorskip("pymoo", reason="pymoo not installed")

from quompass.core.algorithm import AlgorithmSpec, LogicalCounts
from quompass.optimization.problem import FTQREProblem
from quompass.optimization.space import OptimizationSpace


@pytest.fixture
def shor_64_spec():
    """Small Shor spec for fast optimization tests."""
    from quompass.templates.shor import shor
    return shor(n_bits=64)


@pytest.fixture
def basic_space(shor_64_spec):
    return OptimizationSpace(
        algorithm=shor_64_spec,
        hardware=["gate_ns_e3", "gate_ns_e4"],
        qec=["surface_code"],
    )


class TestOptimizationSpace:
    def test_construction(self, shor_64_spec):
        space = OptimizationSpace(
            algorithm=shor_64_spec,
            hardware=["gate_ns_e3"],
            qec=["surface_code"],
        )
        assert space.error_budget_range == (1e-4, 0.1)
        assert "total_physical_qubits" in space.objectives
        assert "runtime_seconds" in space.objectives

    def test_custom_objectives(self, shor_64_spec):
        space = OptimizationSpace(
            algorithm=shor_64_spec,
            hardware=["gate_ns_e3"],
            qec=["surface_code"],
            objectives={"space_time_volume": "minimize"},
        )
        assert "space_time_volume" in space.objectives
        assert len(space.objectives) == 1

    def test_range_validation_inverted(self, shor_64_spec):
        with pytest.raises(ValueError, match="lower bound.*must be less than"):
            OptimizationSpace(
                algorithm=shor_64_spec,
                hardware=["gate_ns_e3"],
                qec=["surface_code"],
                error_budget_range=(0.1, 0.001),
            )

    def test_range_validation_zero(self, shor_64_spec):
        with pytest.raises(ValueError, match="must be positive"):
            OptimizationSpace(
                algorithm=shor_64_spec,
                hardware=["gate_ns_e3"],
                qec=["surface_code"],
                error_budget_range=(0.0, 0.1),
            )

    def test_empty_hardware_raises(self, shor_64_spec):
        with pytest.raises(ValueError, match="hardware list must not be empty"):
            OptimizationSpace(
                algorithm=shor_64_spec,
                hardware=[],
                qec=["surface_code"],
            )

    def test_empty_qec_raises(self, shor_64_spec):
        with pytest.raises(ValueError, match="qec list must not be empty"):
            OptimizationSpace(
                algorithm=shor_64_spec,
                hardware=["gate_ns_e3"],
                qec=[],
            )

    def test_invalid_direction_raises(self, shor_64_spec):
        with pytest.raises(ValueError, match="must be 'minimize' or 'maximize'"):
            OptimizationSpace(
                algorithm=shor_64_spec,
                hardware=["gate_ns_e3"],
                qec=["surface_code"],
                objectives={"total_physical_qubits": "min"},
            )


class TestFTQREProblem:
    def test_variable_count(self, basic_space):
        problem = FTQREProblem(basic_space)
        assert problem.n_var == 5

    def test_objective_count(self, basic_space):
        problem = FTQREProblem(basic_space)
        assert problem.n_obj == 2

    def test_single_objective(self, shor_64_spec):
        space = OptimizationSpace(
            algorithm=shor_64_spec,
            hardware=["gate_ns_e3"],
            qec=["surface_code"],
            objectives={"total_physical_qubits": "minimize"},
        )
        problem = FTQREProblem(space)
        assert problem.n_obj == 1

    def test_split_normalization(self):
        r_log, r_dist, r_rot = FTQREProblem.split_budget(1.0, 1.0)
        # 1/(1+1+1), 1/(1+1+1), 1/(1+1+1)
        assert abs(r_log - 1 / 3) < 1e-10
        assert abs(r_dist - 1 / 3) < 1e-10
        assert abs(r_rot - 1 / 3) < 1e-10
        assert abs(r_log + r_dist + r_rot - 1.0) < 1e-10

    def test_split_normalization_edge(self):
        r_log, r_dist, r_rot = FTQREProblem.split_budget(0.0, 0.0)
        # 0/(0+0+1), 0/(0+0+1), 1/(0+0+1)
        assert r_log == 0.0
        assert r_dist == 0.0
        assert r_rot == 1.0

    def test_split_normalization_sums_to_one(self):
        import random
        rng = random.Random(42)
        for _ in range(100):
            s1 = rng.random()
            s2 = rng.random()
            r1, r2, r3 = FTQREProblem.split_budget(s1, s2)
            assert abs(r1 + r2 + r3 - 1.0) < 1e-10
            assert r1 >= 0 and r2 >= 0 and r3 >= 0


class TestOptimize:
    def test_basic_run(self, basic_space):
        from quompass.optimization import optimize

        result = optimize(
            basic_space,
            generations=5,
            population_size=10,
            seed=42,
        )
        assert len(result.all_points) > 0

    def test_produces_design_points(self, basic_space):
        from quompass.exploration.space import DesignPoint
        from quompass.optimization import optimize

        result = optimize(
            basic_space,
            generations=5,
            population_size=10,
            seed=42,
        )
        for pt in result.all_points:
            assert isinstance(pt, DesignPoint)

    def test_pareto_front_works(self, basic_space):
        from quompass.optimization import optimize

        result = optimize(
            basic_space,
            generations=5,
            population_size=10,
            seed=42,
        )
        front = result.pareto_front()
        assert len(front) >= 1

    def test_progress_callback_fires(self, basic_space):
        from quompass.optimization import optimize

        calls = []

        def on_progress(gen, total):
            calls.append((gen, total))

        result = optimize(
            basic_space,
            generations=5,
            population_size=10,
            seed=42,
            progress_callback=on_progress,
        )
        assert len(calls) > 0
        # Last call should be for the final generation
        assert calls[-1][1] == 5

    def test_reproducible_with_seed(self, basic_space):
        from quompass.optimization import optimize

        r1 = optimize(basic_space, generations=3, population_size=10, seed=123)
        r2 = optimize(basic_space, generations=3, population_size=10, seed=123)

        # Same seed should produce same number of points
        assert len(r1.all_points) == len(r2.all_points)

        # Compare metrics of succeeded points
        if r1.succeeded and r2.succeeded:
            q1 = sorted(p.total_physical_qubits for p in r1.succeeded)
            q2 = sorted(p.total_physical_qubits for p in r2.succeeded)
            assert q1 == q2


class TestOptimizationResult:
    def test_succeeded_filter(self, basic_space):
        from quompass.optimization import optimize

        result = optimize(
            basic_space,
            generations=5,
            population_size=10,
            seed=42,
        )
        succeeded = result.succeeded
        for pt in succeeded:
            assert pt.succeeded

    def test_best_point(self, basic_space):
        from quompass.optimization import optimize

        result = optimize(
            basic_space,
            generations=5,
            population_size=10,
            seed=42,
        )
        if result.succeeded:
            best = result.best(metric="total_physical_qubits")
            assert best.succeeded
            # best should be <= all others
            for pt in result.succeeded:
                assert best.total_physical_qubits <= pt.total_physical_qubits

    def test_to_exploration_result(self, basic_space):
        from quompass.exploration.space import ExplorationResult
        from quompass.optimization import optimize

        result = optimize(
            basic_space,
            generations=5,
            population_size=10,
            seed=42,
        )
        er = result.to_exploration_result()
        assert isinstance(er, ExplorationResult)
        assert len(er.all_points) == len(result.all_points)
