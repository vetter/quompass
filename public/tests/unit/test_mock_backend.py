"""Tests for the analytical (mock) physical estimator."""

from quompass.backends.mock import AnalyticalPhysicalEstimator, MockLogicalEstimator
from quompass.core.algorithm import AlgorithmSpec, LogicalCounts
from quompass.core.error_budget import ErrorBudget
from quompass.core.qec import FormulaQEC, SurfaceCode


def _qldpc(transversal: bool) -> FormulaQEC:
    """A FormulaQEC usable with the gate_ns_e3 preset (p = 1e-3 < threshold)."""
    return FormulaQEC(
        name="qldpc_test",
        threshold=0.01,
        prefactor=0.03,
        qubits_formula="2 * d * d",
        cycle_time_formula="t_2q * d",
        transversal_magic_states=transversal,
    )


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


class TestTransversalMagicStates:
    """Estimation with a QEC scheme that applies T/CCZ transversally."""

    def test_no_t_factory(self, superconducting_hw):
        pe = AnalyticalPhysicalEstimator()
        spec = AlgorithmSpec(
            name="Transversal",
            logical_counts=LogicalCounts(num_qubits=10, t_count=100, ccz_count=50),
        )
        result = pe.estimate(
            spec.logical_counts,
            superconducting_hw,
            _qldpc(transversal=True),
            ErrorBudget(total=0.001),
            spec,
        )
        assert result.t_factory is None
        assert result.physical_qubits_for_t_factories == 0
        assert result.total_physical_qubits == result.physical_qubits_for_algorithm

    def test_ccz_counts_as_one_cycle_not_four(self, superconducting_hw):
        """Transversal CCZ is one logical cycle; otherwise it is 4 T equivalents."""
        pe = AnalyticalPhysicalEstimator()
        spec = AlgorithmSpec(
            name="CCZ depth",
            logical_counts=LogicalCounts(num_qubits=10, t_count=100, ccz_count=50),
        )
        transversal = pe.estimate(
            spec.logical_counts, superconducting_hw, _qldpc(True),
            ErrorBudget(total=0.001), spec,
        )
        distilled = pe.estimate(
            spec.logical_counts, superconducting_hw, _qldpc(False),
            ErrorBudget(total=0.001), spec,
        )
        # transversal: 100 + 50; distilled: 100 + 4*50
        assert transversal.algorithmic_logical_depth == 150
        assert transversal.num_t_states == 150
        assert distilled.algorithmic_logical_depth == 300
        assert distilled.num_t_states == 300

    def test_non_transversal_formula_qec_still_builds_factory(self, superconducting_hw):
        pe = AnalyticalPhysicalEstimator()
        spec = AlgorithmSpec(
            name="Distilled",
            logical_counts=LogicalCounts(num_qubits=10, t_count=100),
        )
        result = pe.estimate(
            spec.logical_counts,
            superconducting_hw,
            _qldpc(transversal=False),
            ErrorBudget(total=0.001),
            spec,
        )
        assert result.t_factory is not None
        assert result.physical_qubits_for_t_factories > 0
