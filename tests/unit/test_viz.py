"""Tests for visualization modules (viz/summary.py and viz/exploration.py).

Uses Rich Console with a StringIO file to capture output without printing.
"""

from io import StringIO

import pytest
from rich.console import Console

from quompass.backends.mock import AnalyticalPhysicalEstimator, MockLogicalEstimator
from quompass.core.algorithm import AlgorithmSpec, LogicalCounts
from quompass.core.error_budget import ErrorBudget
from quompass.core.hardware import HardwareModel
from quompass.core.qec import SurfaceCode
from quompass.core.types import HardwarePreset
from quompass.exploration.space import (
    DesignPoint,
    ExplorationResult,
    ExplorationSpace,
    ParetoFront,
)
from quompass.exploration.sensitivity import SensitivityEntry, SensitivityResult
from quompass.viz.summary import print_estimate_detail, print_estimate_summary
from quompass.viz.exploration import (
    print_exploration_table,
    print_pareto_table,
    print_sensitivity_table,
)


@pytest.fixture
def estimate():
    """Create a real PhysicalEstimate via the analytical backend."""
    spec = AlgorithmSpec(
        name="Test Algorithm",
        logical_counts=LogicalCounts(num_qubits=10, t_count=100, ccz_count=50),
    )
    hw = HardwareModel.from_preset(HardwarePreset.SUPERCONDUCTING_REALISTIC)
    qec = SurfaceCode()
    eb = ErrorBudget(total=0.001)
    le = MockLogicalEstimator()
    pe = AnalyticalPhysicalEstimator()
    lc = le.estimate(spec)
    return pe.estimate(lc, hw, qec, eb, spec)


@pytest.fixture
def estimate_no_tfactory():
    """Estimate for an algorithm with zero T gates."""
    spec = AlgorithmSpec(
        name="No T Gates",
        logical_counts=LogicalCounts(num_qubits=5, measurement_count=10),
    )
    hw = HardwareModel.from_preset(HardwarePreset.SUPERCONDUCTING_OPTIMISTIC)
    qec = SurfaceCode()
    eb = ErrorBudget(total=0.01)
    le = MockLogicalEstimator()
    pe = AnalyticalPhysicalEstimator()
    lc = le.estimate(spec)
    return pe.estimate(lc, hw, qec, eb, spec)


def _capture_console() -> tuple[Console, StringIO]:
    buf = StringIO()
    return Console(file=buf, width=120), buf


# ---------------------------------------------------------------------------
# viz/summary.py tests
# ---------------------------------------------------------------------------


class TestPrintEstimateSummary:
    def test_renders_without_error(self, estimate):
        console, buf = _capture_console()
        print_estimate_summary(estimate, console)
        output = buf.getvalue()
        assert len(output) > 0

    def test_contains_key_metrics(self, estimate):
        console, buf = _capture_console()
        print_estimate_summary(estimate, console)
        output = buf.getvalue()
        assert "Physical Qubits" in output
        assert "Runtime" in output
        assert "Code Distance" in output
        assert "Error Budget" in output
        assert "surface_code" in output
        assert "analytical" in output

    def test_contains_algorithm_name(self, estimate):
        console, buf = _capture_console()
        print_estimate_summary(estimate, console)
        assert "Test Algorithm" in buf.getvalue()

    def test_default_console(self, estimate):
        # Should not raise when no console is passed
        print_estimate_summary(estimate)


class TestPrintEstimateDetail:
    def test_renders_without_error(self, estimate):
        console, buf = _capture_console()
        print_estimate_detail(estimate, console)
        output = buf.getvalue()
        assert len(output) > 0

    def test_includes_logical_qubit_details(self, estimate):
        console, buf = _capture_console()
        print_estimate_detail(estimate, console)
        output = buf.getvalue()
        assert "Logical Qubit Details" in output
        assert "Physical Qubits / Logical" in output

    def test_includes_t_factory_details(self, estimate):
        console, buf = _capture_console()
        print_estimate_detail(estimate, console)
        output = buf.getvalue()
        assert "T Factory Details" in output
        assert "Distillation Rounds" in output

    def test_no_t_factory_section(self, estimate_no_tfactory):
        console, buf = _capture_console()
        print_estimate_detail(estimate_no_tfactory, console)
        output = buf.getvalue()
        assert "T Factory Details" not in output


# ---------------------------------------------------------------------------
# viz/exploration.py table tests
# ---------------------------------------------------------------------------


@pytest.fixture
def exploration_result():
    """Create an ExplorationResult with a mix of succeeded and failed points."""
    spec = AlgorithmSpec(
        name="Explore Test",
        logical_counts=LogicalCounts(num_qubits=10, t_count=100, ccz_count=50),
    )
    hw = HardwareModel.from_preset(HardwarePreset.SUPERCONDUCTING_REALISTIC)
    qec = SurfaceCode()
    eb = ErrorBudget(total=0.001)
    le = MockLogicalEstimator()
    pe = AnalyticalPhysicalEstimator()
    lc = le.estimate(spec)
    est = pe.estimate(lc, hw, qec, eb, spec)

    points = [
        DesignPoint(
            hardware_name="gate_ns_e3",
            qec_name="surface_code",
            error_budget=0.001,
            estimate=est,
        ),
        DesignPoint(
            hardware_name="gate_ns_e4",
            qec_name="surface_code",
            error_budget=0.001,
            estimate=None,
            error_message="Physical error rate exceeds threshold",
        ),
    ]
    space = ExplorationSpace(
        algorithm=spec,
        hardware=["gate_ns_e3", "gate_ns_e4"],
        qec=["surface_code"],
        error_budgets=[0.001],
    )
    return ExplorationResult(space=space, points=points)


class TestPrintExplorationTable:
    def test_renders_without_error(self, exploration_result):
        console, buf = _capture_console()
        print_exploration_table(exploration_result, console)
        output = buf.getvalue()
        assert len(output) > 0

    def test_shows_succeeded_and_failed(self, exploration_result):
        console, buf = _capture_console()
        print_exploration_table(exploration_result, console)
        output = buf.getvalue()
        assert "OK" in output
        assert "FAIL" in output

    def test_shows_count_summary(self, exploration_result):
        console, buf = _capture_console()
        print_exploration_table(exploration_result, console)
        output = buf.getvalue()
        assert "1/2 points succeeded" in output

    def test_shows_hardware_names(self, exploration_result):
        console, buf = _capture_console()
        print_exploration_table(exploration_result, console)
        output = buf.getvalue()
        assert "gate_ns_e3" in output
        assert "gate_ns_e4" in output


class TestPrintParetoTable:
    def test_renders_without_error(self, exploration_result):
        front = exploration_result.pareto_front()
        console, buf = _capture_console()
        print_pareto_table(front, console)
        output = buf.getvalue()
        assert "Pareto Front" in output

    def test_shows_direction_arrows(self, exploration_result):
        front = exploration_result.pareto_front()
        console, buf = _capture_console()
        print_pareto_table(front, console)
        output = buf.getvalue()
        # minimize objectives should show "v"
        assert "(v)" in output


class TestPrintSensitivityTable:
    def test_renders_without_error(self):
        sensitivity = SensitivityResult(
            metric="total_physical_qubits",
            baseline_value=10000.0,
            baseline_params={"hardware": "gate_ns_e3", "qec": "surface_code", "error_budget": 0.001},
            dimensions={
                "hardware": [
                    SensitivityEntry("gate_ns_e3", 10000.0, 0.0),
                    SensitivityEntry("gate_ns_e4", 5000.0, -50.0),
                ],
                "error_budget": [
                    SensitivityEntry(0.001, 10000.0, 0.0),
                    SensitivityEntry(0.01, 8000.0, -20.0),
                ],
            },
        )
        console, buf = _capture_console()
        print_sensitivity_table(sensitivity, console)
        output = buf.getvalue()
        assert "Sensitivity Analysis" in output
        assert "hardware" in output
        assert "baseline" in output.lower()

    def test_color_coding(self):
        sensitivity = SensitivityResult(
            metric="total_physical_qubits",
            baseline_value=10000.0,
            baseline_params={},
            dimensions={
                "test": [
                    SensitivityEntry("a", 10000.0, 0.0),
                    SensitivityEntry("b", 8000.0, -20.0),
                    SensitivityEntry("c", 12000.0, 20.0),
                ],
            },
        )
        console, buf = _capture_console()
        print_sensitivity_table(sensitivity, console)
        output = buf.getvalue()
        # Negative change = good = green, positive = bad = red in raw markup
        assert "-20.0%" in output
        assert "+20.0%" in output
