"""Tests for input validation on core types."""

import pytest

from quompass.core.algorithm import LogicalCounts
from quompass.core.error_budget import ErrorBudget
from quompass.core.hardware import QubitParams
from quompass.core.qec import SurfaceCode, FloquetCode, FormulaQEC, color_code
from quompass.core.types import InstructionSet


# ---------------------------------------------------------------------------
# LogicalCounts validation
# ---------------------------------------------------------------------------


class TestLogicalCountsValidation:
    def test_valid_minimal(self):
        lc = LogicalCounts(num_qubits=1)
        assert lc.num_qubits == 1

    def test_valid_full(self):
        lc = LogicalCounts(
            num_qubits=100, t_count=500, rotation_count=10,
            rotation_depth=5, ccz_count=200, measurement_count=50,
            clifford_count=1000, circuit_depth=300,
        )
        assert lc.total_t_equivalent == 500 + 4 * 200 + 10

    def test_num_qubits_zero(self):
        with pytest.raises(ValueError, match="num_qubits must be >= 1"):
            LogicalCounts(num_qubits=0)

    def test_num_qubits_negative(self):
        with pytest.raises(ValueError, match="num_qubits must be >= 1"):
            LogicalCounts(num_qubits=-5)

    @pytest.mark.parametrize("field", [
        "t_count", "rotation_count", "rotation_depth",
        "ccz_count", "measurement_count", "clifford_count",
    ])
    def test_negative_count_fields(self, field):
        with pytest.raises(ValueError, match=f"{field} must be non-negative"):
            LogicalCounts(num_qubits=10, **{field: -1})

    def test_negative_circuit_depth(self):
        with pytest.raises(ValueError, match="circuit_depth must be non-negative"):
            LogicalCounts(num_qubits=10, circuit_depth=-1)

    def test_zero_counts_allowed(self):
        lc = LogicalCounts(num_qubits=1, t_count=0, ccz_count=0)
        assert lc.t_count == 0

    def test_none_circuit_depth_allowed(self):
        lc = LogicalCounts(num_qubits=1)
        assert lc.circuit_depth is None


# ---------------------------------------------------------------------------
# QubitParams validation
# ---------------------------------------------------------------------------


def _valid_qubit_params(**overrides) -> QubitParams:
    """Helper to create valid QubitParams with selective overrides."""
    defaults = dict(
        name="test",
        instruction_set=InstructionSet.GATE_BASED,
        one_qubit_gate_time=50e-9,
        two_qubit_gate_time=50e-9,
        one_qubit_measurement_time=100e-9,
        t_gate_time=50e-9,
        one_qubit_gate_error_rate=1e-3,
        two_qubit_gate_error_rate=1e-3,
        one_qubit_measurement_error_rate=1e-3,
        t_gate_error_rate=1e-3,
    )
    defaults.update(overrides)
    return QubitParams(**defaults)


class TestQubitParamsValidation:
    def test_valid(self):
        qp = _valid_qubit_params()
        assert qp.one_qubit_gate_time == 50e-9

    @pytest.mark.parametrize("field", [
        "one_qubit_gate_time", "two_qubit_gate_time",
        "one_qubit_measurement_time", "t_gate_time",
    ])
    def test_zero_gate_time(self, field):
        with pytest.raises(ValueError, match=f"{field} must be positive"):
            _valid_qubit_params(**{field: 0.0})

    @pytest.mark.parametrize("field", [
        "one_qubit_gate_time", "two_qubit_gate_time",
        "one_qubit_measurement_time", "t_gate_time",
    ])
    def test_negative_gate_time(self, field):
        with pytest.raises(ValueError, match=f"{field} must be positive"):
            _valid_qubit_params(**{field: -1e-9})

    @pytest.mark.parametrize("field", [
        "one_qubit_gate_error_rate", "two_qubit_gate_error_rate",
        "one_qubit_measurement_error_rate", "t_gate_error_rate",
    ])
    def test_error_rate_zero(self, field):
        with pytest.raises(ValueError, match=f"{field} must be in"):
            _valid_qubit_params(**{field: 0.0})

    @pytest.mark.parametrize("field", [
        "one_qubit_gate_error_rate", "two_qubit_gate_error_rate",
        "one_qubit_measurement_error_rate", "t_gate_error_rate",
    ])
    def test_error_rate_one(self, field):
        with pytest.raises(ValueError, match=f"{field} must be in"):
            _valid_qubit_params(**{field: 1.0})

    @pytest.mark.parametrize("field", [
        "one_qubit_gate_error_rate", "two_qubit_gate_error_rate",
        "one_qubit_measurement_error_rate", "t_gate_error_rate",
    ])
    def test_error_rate_above_one(self, field):
        with pytest.raises(ValueError, match=f"{field} must be in"):
            _valid_qubit_params(**{field: 1.5})

    def test_idle_error_rate_invalid(self):
        with pytest.raises(ValueError, match="idle_error_rate must be in"):
            _valid_qubit_params(idle_error_rate=0.0)

    def test_idle_error_rate_valid(self):
        qp = _valid_qubit_params(idle_error_rate=0.001)
        assert qp.idle_error_rate == 0.001

    def test_majorana_both_set(self):
        qp = _valid_qubit_params(
            two_qubit_joint_measurement_time=100e-9,
            two_qubit_joint_measurement_error_rate=1e-4,
        )
        assert qp.two_qubit_joint_measurement_time == 100e-9

    def test_majorana_only_time_set(self):
        with pytest.raises(ValueError, match="must both be set or both be None"):
            _valid_qubit_params(two_qubit_joint_measurement_time=100e-9)

    def test_majorana_only_error_set(self):
        with pytest.raises(ValueError, match="must both be set or both be None"):
            _valid_qubit_params(two_qubit_joint_measurement_error_rate=1e-4)

    def test_majorana_invalid_time(self):
        with pytest.raises(ValueError, match="two_qubit_joint_measurement_time must be positive"):
            _valid_qubit_params(
                two_qubit_joint_measurement_time=-1e-9,
                two_qubit_joint_measurement_error_rate=1e-4,
            )

    def test_majorana_invalid_error(self):
        with pytest.raises(ValueError, match="two_qubit_joint_measurement_error_rate must be in"):
            _valid_qubit_params(
                two_qubit_joint_measurement_time=100e-9,
                two_qubit_joint_measurement_error_rate=0.0,
            )


# ---------------------------------------------------------------------------
# ErrorBudget validation
# ---------------------------------------------------------------------------


class TestErrorBudgetValidation:
    def test_valid_default(self):
        eb = ErrorBudget()
        assert eb.total == 0.001

    def test_valid_custom(self):
        eb = ErrorBudget(total=0.01, logical=0.003, distillation=0.004, rotation=0.003)
        assert eb.total == 0.01

    def test_total_zero(self):
        with pytest.raises(ValueError, match="total error budget must be in"):
            ErrorBudget(total=0.0)

    def test_total_one(self):
        with pytest.raises(ValueError, match="total error budget must be in"):
            ErrorBudget(total=1.0)

    def test_total_negative(self):
        with pytest.raises(ValueError, match="total error budget must be in"):
            ErrorBudget(total=-0.01)

    def test_total_above_one(self):
        with pytest.raises(ValueError, match="total error budget must be in"):
            ErrorBudget(total=1.5)

    def test_negative_logical(self):
        with pytest.raises(ValueError, match="logical must be non-negative"):
            ErrorBudget(total=0.01, logical=-0.001)

    def test_negative_distillation(self):
        with pytest.raises(ValueError, match="distillation must be non-negative"):
            ErrorBudget(total=0.01, distillation=-0.001)

    def test_negative_rotation(self):
        with pytest.raises(ValueError, match="rotation must be non-negative"):
            ErrorBudget(total=0.01, rotation=-0.001)


# ---------------------------------------------------------------------------
# QEC code distance validation
# ---------------------------------------------------------------------------


class TestQECCodeDistanceValidation:
    @pytest.fixture
    def surface(self):
        return SurfaceCode()

    @pytest.fixture
    def floquet(self):
        return FloquetCode()

    @pytest.fixture
    def formula_qec(self):
        return color_code()

    @pytest.mark.parametrize("bad_d", [0, 1, 2, 4, -1])
    def test_surface_code_logical_error_rate(self, surface, bad_d):
        with pytest.raises(ValueError, match="code_distance must be an odd integer >= 3"):
            surface.logical_error_rate(bad_d, 1e-3)

    @pytest.mark.parametrize("bad_d", [0, 1, 2, 4, -1])
    def test_surface_code_physical_qubits(self, surface, bad_d):
        with pytest.raises(ValueError, match="code_distance must be an odd integer >= 3"):
            surface.physical_qubits_per_logical(bad_d)

    @pytest.mark.parametrize("bad_d", [0, 1, 2, 4, -1])
    def test_floquet_code_logical_error_rate(self, floquet, bad_d):
        with pytest.raises(ValueError, match="code_distance must be an odd integer >= 3"):
            floquet.logical_error_rate(bad_d, 1e-3)

    @pytest.mark.parametrize("bad_d", [0, 2, 4])
    def test_formula_qec_logical_error_rate(self, formula_qec, bad_d):
        with pytest.raises(ValueError, match="code_distance must be an odd integer >= 3"):
            formula_qec.logical_error_rate(bad_d, 1e-3)

    @pytest.mark.parametrize("bad_d", [0, 2, 4])
    def test_formula_qec_physical_qubits(self, formula_qec, bad_d):
        with pytest.raises(ValueError, match="code_distance must be an odd integer >= 3"):
            formula_qec.physical_qubits_per_logical(bad_d)

    def test_valid_distances_work(self, surface, floquet, formula_qec):
        for d in (3, 5, 7, 9, 11):
            assert surface.logical_error_rate(d, 1e-3) > 0
            assert surface.physical_qubits_per_logical(d) > 0
            assert floquet.logical_error_rate(d, 1e-3) > 0
            assert floquet.physical_qubits_per_logical(d) > 0
            assert formula_qec.logical_error_rate(d, 1e-3) > 0
            assert formula_qec.physical_qubits_per_logical(d) > 0
