"""Tests for the analytical (mock) physical estimator."""

from quompass.backends.mock import AnalyticalPhysicalEstimator, MockLogicalEstimator
from quompass.core.algorithm import AlgorithmSpec, LogicalCounts
from quompass.core.error_budget import ErrorBudget
from quompass.core.hardware import HardwareModel
from quompass.core.qec import SurfaceCode
from quompass.core.types import HardwarePreset


class TestMockLogicalEstimator:
    def test_passthrough(self, small_algorithm_spec):
        le = MockLogicalEstimator()
        result = le.estimate(small_algorithm_spec)
        assert result is small_algorithm_spec.logical_counts

    def test_is_available(self):
        le = MockLogicalEstimator()
        assert le.is_available()


class TestAnalyticalPhysicalEstimator:
    def test_produces_result(self, small_algorithm_spec, superconducting_hw):
        pe = AnalyticalPhysicalEstimator()
        result = pe.estimate(
            small_algorithm_spec.logical_counts,
            superconducting_hw,
            SurfaceCode(),
            ErrorBudget(total=0.001),
            small_algorithm_spec,
        )
        assert result.total_physical_qubits > 0
        assert result.runtime_seconds > 0
        assert result.rqops > 0
        assert result.backend_name == "analytical"

    def test_physical_qubits_include_algorithm_and_factories(
        self, small_algorithm_spec, superconducting_hw
    ):
        pe = AnalyticalPhysicalEstimator()
        result = pe.estimate(
            small_algorithm_spec.logical_counts,
            superconducting_hw,
            SurfaceCode(),
            ErrorBudget(total=0.001),
            small_algorithm_spec,
        )
        assert (
            result.total_physical_qubits
            == result.physical_qubits_for_algorithm
            + result.physical_qubits_for_t_factories
        )

    def test_code_distance_is_odd(self, small_algorithm_spec, superconducting_hw):
        pe = AnalyticalPhysicalEstimator()
        result = pe.estimate(
            small_algorithm_spec.logical_counts,
            superconducting_hw,
            SurfaceCode(),
            ErrorBudget(total=0.001),
            small_algorithm_spec,
        )
        assert result.logical_qubit.code_distance % 2 == 1

    def test_tighter_budget_increases_distance(self, superconducting_hw):
        pe = AnalyticalPhysicalEstimator()
        spec = AlgorithmSpec(
            name="Test",
            logical_counts=LogicalCounts(num_qubits=10, t_count=1000),
        )
        r1 = pe.estimate(
            spec.logical_counts,
            superconducting_hw,
            SurfaceCode(),
            ErrorBudget(total=0.01),
            spec,
        )
        r2 = pe.estimate(
            spec.logical_counts,
            superconducting_hw,
            SurfaceCode(),
            ErrorBudget(total=0.0001),
            spec,
        )
        assert r2.logical_qubit.code_distance >= r1.logical_qubit.code_distance

    def test_no_t_gates_no_factory(self, superconducting_hw):
        pe = AnalyticalPhysicalEstimator()
        spec = AlgorithmSpec(
            name="Clifford only",
            logical_counts=LogicalCounts(num_qubits=10, clifford_count=100),
        )
        result = pe.estimate(
            spec.logical_counts,
            superconducting_hw,
            SurfaceCode(),
            ErrorBudget(total=0.001),
            spec,
        )
        assert result.t_factory is None
        assert result.physical_qubits_for_t_factories == 0

    def test_is_available(self):
        pe = AnalyticalPhysicalEstimator()
        assert pe.is_available()
