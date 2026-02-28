"""Tests for the grid search explorer."""

from ftqre.exploration import ExplorationSpace, explore
from ftqre.templates.shor import shor


class TestExplore:
    def test_single_combination(self):
        space = ExplorationSpace(
            algorithm=shor(n_bits=64),
            hardware=["gate_ns_e3"],
            qec=["surface_code"],
            error_budgets=[0.001],
        )
        result = explore(space)
        assert len(result.all_points) == 1
        assert result.num_succeeded == 1
        assert result.num_failed == 0
        pt = result.all_points[0]
        assert pt.succeeded
        assert pt.total_physical_qubits > 0

    def test_multiple_hardware(self):
        space = ExplorationSpace(
            algorithm=shor(n_bits=64),
            hardware=["gate_ns_e3", "gate_us_e3"],
            qec=["surface_code"],
            error_budgets=[0.001],
        )
        result = explore(space)
        assert len(result.all_points) == 2
        hw_names = {pt.hardware_name for pt in result.all_points}
        assert hw_names == {"gate_ns_e3", "gate_us_e3"}

    def test_multiple_qec(self):
        space = ExplorationSpace(
            algorithm=shor(n_bits=64),
            hardware=["gate_ns_e3"],
            qec=["surface_code", "color_code"],
            error_budgets=[0.001],
        )
        result = explore(space)
        assert len(result.all_points) == 2

    def test_full_grid(self):
        space = ExplorationSpace(
            algorithm=shor(n_bits=64),
            hardware=["gate_ns_e3", "gate_us_e3"],
            qec=["surface_code", "color_code"],
            error_budgets=[0.01, 0.001],
        )
        assert space.size == 8
        result = explore(space)
        assert len(result.all_points) == 8

    def test_graceful_failure(self):
        """Floquet code with gate-based hardware may fail; should not crash."""
        space = ExplorationSpace(
            algorithm=shor(n_bits=64),
            hardware=["gate_ns_e3"],
            qec=["surface_code", "floquet_code"],
            error_budgets=[0.001],
        )
        result = explore(space)
        assert len(result.all_points) == 2
        # At least surface code should succeed
        assert result.num_succeeded >= 1

    def test_progress_callback(self):
        calls = []
        space = ExplorationSpace(
            algorithm=shor(n_bits=64),
            hardware=["gate_ns_e3"],
            qec=["surface_code"],
            error_budgets=[0.01, 0.001],
        )
        explore(space, progress_callback=lambda c, t: calls.append((c, t)))
        assert len(calls) == 2
        assert calls[-1] == (2, 2)

    def test_best_point(self):
        space = ExplorationSpace(
            algorithm=shor(n_bits=64),
            hardware=["gate_ns_e3", "gate_ns_e4"],
            qec=["surface_code"],
            error_budgets=[0.001],
        )
        result = explore(space)
        best = result.best(metric="total_physical_qubits", minimize=True)
        assert best.succeeded
        # Optimistic hardware (e4) should need fewer qubits
        assert best.hardware_name == "gate_ns_e4"


class TestExplorationSpace:
    def test_size_calculation(self):
        space = ExplorationSpace(
            algorithm=shor(n_bits=64),
            hardware=["a", "b", "c"],
            qec=["x", "y"],
            error_budgets=[0.01, 0.001, 0.0001],
        )
        assert space.size == 18

    def test_defaults(self):
        space = ExplorationSpace(algorithm=shor(n_bits=64))
        assert space.size == 1
