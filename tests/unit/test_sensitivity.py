"""Tests for sensitivity analysis."""

import pytest

from ftqre.exploration import ExplorationSpace, explore
from ftqre.exploration.sensitivity import compute_sensitivity, _pct_change
from ftqre.templates.shor import shor


class TestSensitivity:
    def test_basic_sensitivity(self):
        space = ExplorationSpace(
            algorithm=shor(n_bits=64),
            hardware=["gate_ns_e3", "gate_ns_e4"],
            qec=["surface_code"],
            error_budgets=[0.001],
        )
        result = explore(space)
        sens = compute_sensitivity(result, metric="total_physical_qubits")

        assert sens.metric == "total_physical_qubits"
        assert sens.baseline_value > 0
        assert "hardware" in sens.dimensions
        assert "qec" in sens.dimensions
        assert "error_budget" in sens.dimensions

    def test_baseline_at_zero_pct(self):
        space = ExplorationSpace(
            algorithm=shor(n_bits=64),
            hardware=["gate_ns_e3", "gate_ns_e4"],
            qec=["surface_code"],
            error_budgets=[0.001],
        )
        result = explore(space)
        sens = compute_sensitivity(
            result,
            baseline={
                "hardware": "gate_ns_e3",
                "qec": "surface_code",
                "error_budget": 0.001,
            },
        )
        hw_entries = sens.dimensions["hardware"]
        baseline_entry = [e for e in hw_entries if e.param_value == "gate_ns_e3"]
        assert len(baseline_entry) == 1
        assert baseline_entry[0].pct_change == 0.0

    def test_custom_baseline(self):
        space = ExplorationSpace(
            algorithm=shor(n_bits=64),
            hardware=["gate_ns_e3", "gate_ns_e4"],
            qec=["surface_code"],
            error_budgets=[0.01, 0.001],
        )
        result = explore(space)
        sens = compute_sensitivity(
            result,
            baseline={
                "hardware": "gate_ns_e4",
                "qec": "surface_code",
                "error_budget": 0.01,
            },
        )
        assert sens.baseline_params["hardware"] == "gate_ns_e4"

    def test_missing_baseline_raises(self):
        space = ExplorationSpace(
            algorithm=shor(n_bits=64),
            hardware=["gate_ns_e3"],
            qec=["surface_code"],
            error_budgets=[0.001],
        )
        result = explore(space)
        with pytest.raises(ValueError, match="Baseline point not found"):
            compute_sensitivity(
                result,
                baseline={
                    "hardware": "nonexistent",
                    "qec": "surface_code",
                    "error_budget": 0.001,
                },
            )

    def test_most_sensitive_dimension(self):
        space = ExplorationSpace(
            algorithm=shor(n_bits=64),
            hardware=["gate_ns_e3", "gate_ns_e4"],
            qec=["surface_code"],
            error_budgets=[0.01, 0.001, 0.0001],
        )
        result = explore(space)
        sens = result.sensitivity()
        dim = sens.most_sensitive_dimension()
        assert dim in ("hardware", "qec", "error_budget")


class TestPctChange:
    def test_no_change(self):
        assert _pct_change(100, 100) == 0.0

    def test_increase(self):
        assert _pct_change(100, 150) == 50.0

    def test_decrease(self):
        assert _pct_change(100, 50) == -50.0

    def test_zero_baseline(self):
        assert _pct_change(0, 0) == 0.0
        assert _pct_change(0, 100) == float("inf")
