"""Tests for Pareto front extraction."""

from unittest.mock import MagicMock

from ftqre.exploration.pareto import extract_pareto_front
from ftqre.exploration.space import DesignPoint


def _mock_point(hw, qec, eb, qubits, runtime, rqops=1e6, stv=None):
    """Create a DesignPoint with a mock PhysicalEstimate."""
    est = MagicMock()
    est.total_physical_qubits = qubits
    est.runtime_seconds = runtime
    est.space_time_volume = stv if stv is not None else qubits * runtime
    est.rqops = rqops
    est.logical_qubit.code_distance = 7
    return DesignPoint(
        hardware_name=hw, qec_name=qec, error_budget=eb, estimate=est,
    )


class TestParetoExtraction:
    def test_empty_input(self):
        assert extract_pareto_front([], {"total_physical_qubits": "minimize"}) == []

    def test_single_point(self):
        pt = _mock_point("hw1", "qec1", 0.001, 1000, 100)
        front = extract_pareto_front(
            [pt], {"total_physical_qubits": "minimize", "runtime_seconds": "minimize"}
        )
        assert len(front) == 1
        assert front[0] is pt

    def test_two_objectives_basic(self):
        # A: fewer qubits, longer runtime -> Pareto
        # B: more qubits, shorter runtime -> Pareto
        # C: more qubits AND longer runtime than A -> dominated by A
        a = _mock_point("a", "q", 0.001, 100, 1000)
        b = _mock_point("b", "q", 0.001, 500, 200)
        c = _mock_point("c", "q", 0.001, 600, 1500)
        front = extract_pareto_front(
            [a, b, c],
            {"total_physical_qubits": "minimize", "runtime_seconds": "minimize"},
        )
        assert len(front) == 2
        labels = {pt.hardware_name for pt in front}
        assert labels == {"a", "b"}

    def test_all_on_pareto(self):
        pts = [
            _mock_point("a", "q", 0.001, 100, 1000),
            _mock_point("b", "q", 0.001, 200, 500),
            _mock_point("c", "q", 0.001, 300, 100),
        ]
        front = extract_pareto_front(
            pts, {"total_physical_qubits": "minimize", "runtime_seconds": "minimize"}
        )
        assert len(front) == 3

    def test_all_dominated_by_one(self):
        pts = [
            _mock_point("a", "q", 0.001, 100, 100),
            _mock_point("b", "q", 0.001, 200, 200),
            _mock_point("c", "q", 0.001, 300, 300),
        ]
        front = extract_pareto_front(
            pts, {"total_physical_qubits": "minimize", "runtime_seconds": "minimize"}
        )
        assert len(front) == 1
        assert front[0].hardware_name == "a"

    def test_maximize_objective(self):
        # a has fewer qubits and same rqops -> dominates b
        pts = [
            _mock_point("a", "q", 0.001, 100, 100, rqops=1e6),
            _mock_point("b", "q", 0.001, 200, 100, rqops=1e6),
        ]
        front = extract_pareto_front(
            pts, {"total_physical_qubits": "minimize", "rqops": "maximize"}
        )
        assert len(front) == 1
        assert front[0].hardware_name == "a"

    def test_ties_both_kept(self):
        a = _mock_point("a", "q", 0.001, 100, 100)
        b = _mock_point("b", "q", 0.001, 100, 100)
        front = extract_pareto_front(
            [a, b],
            {"total_physical_qubits": "minimize", "runtime_seconds": "minimize"},
        )
        assert len(front) == 2

    def test_three_objectives(self):
        pts = [
            _mock_point("a", "q", 0.001, 100, 1000, stv=100000),
            _mock_point("b", "q", 0.001, 500, 200, stv=100000),
            _mock_point("c", "q", 0.001, 300, 300, stv=90000),
        ]
        front = extract_pareto_front(
            pts,
            {
                "total_physical_qubits": "minimize",
                "runtime_seconds": "minimize",
                "space_time_volume": "minimize",
            },
        )
        # All three are non-dominated in 3D
        assert len(front) == 3

    def test_sorted_by_first_objective(self):
        pts = [
            _mock_point("c", "q", 0.001, 300, 100),
            _mock_point("a", "q", 0.001, 100, 300),
            _mock_point("b", "q", 0.001, 200, 200),
        ]
        front = extract_pareto_front(
            pts, {"total_physical_qubits": "minimize", "runtime_seconds": "minimize"}
        )
        qubits = [pt.metric("total_physical_qubits") for pt in front]
        assert qubits == sorted(qubits)

    def test_maximize_sort_order(self):
        pts = [
            _mock_point("a", "q", 0.001, 100, 300, rqops=300),
            _mock_point("b", "q", 0.001, 200, 200, rqops=200),
            _mock_point("c", "q", 0.001, 300, 100, rqops=100),
        ]
        front = extract_pareto_front(
            pts, {"rqops": "maximize", "total_physical_qubits": "minimize"}
        )
        # Should be sorted by rqops descending (maximize)
        rqops_vals = [pt.metric("rqops") for pt in front]
        assert rqops_vals == sorted(rqops_vals, reverse=True)
