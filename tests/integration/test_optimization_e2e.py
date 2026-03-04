"""End-to-end integration tests for multi-objective optimization."""

import pytest

pymoo = pytest.importorskip("pymoo", reason="pymoo not installed")

from quompass.optimization import OptimizationSpace, optimize
from quompass.templates.shor import shor


@pytest.fixture
def shor_64_spec():
    return shor(n_bits=64)


class TestOptimizationE2E:
    def test_full_workflow(self, shor_64_spec):
        """space -> optimize -> pareto -> table"""
        space = OptimizationSpace(
            algorithm=shor_64_spec,
            hardware=["gate_ns_e3", "gate_ns_e4"],
            qec=["surface_code"],
        )
        result = optimize(
            space,
            generations=5,
            population_size=10,
            seed=42,
        )
        assert len(result.succeeded) > 0

        front = result.pareto_front()
        assert len(front) >= 1

        # Should not raise
        from io import StringIO
        from rich.console import Console

        buf = StringIO()
        c = Console(file=buf, force_terminal=False)
        result.print_table(console=c)
        output = buf.getvalue()
        assert len(output) > 0

    def test_multi_qec(self, shor_64_spec):
        """Optimization across multiple QEC schemes."""
        space = OptimizationSpace(
            algorithm=shor_64_spec,
            hardware=["gate_ns_e3"],
            qec=["surface_code", "color_code"],
        )
        result = optimize(
            space,
            generations=5,
            population_size=10,
            seed=42,
        )
        assert len(result.succeeded) > 0

    def test_to_exploration_result_viz_compat(self, shor_64_spec):
        """OptimizationResult.to_exploration_result() works with existing viz."""
        space = OptimizationSpace(
            algorithm=shor_64_spec,
            hardware=["gate_ns_e3", "gate_ns_e4"],
            qec=["surface_code"],
        )
        result = optimize(
            space,
            generations=5,
            population_size=10,
            seed=42,
        )
        er = result.to_exploration_result()

        # Should support pareto_front, best, succeeded
        if er.succeeded:
            front = er.pareto_front()
            assert len(front) >= 1
            best = er.best()
            assert best.succeeded
