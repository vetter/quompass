"""Tests for error paths, edge cases, and security boundaries.

Covers:
- _safe_eval security: disallowed constructs, injection attempts
- FormulaQEC construction validation and error paths
- QECScheme.min_code_distance error conditions
- PhysicalEstimate.runtime_human formatting for various durations
- get_qec_scheme error for unknown names
"""

import pytest

from quompass.core.qec import (
    FormulaQEC,
    SurfaceCode,
    _safe_eval,
    color_code,
    get_qec_scheme,
)
from quompass.core.results import (
    LogicalQubitEstimate,
    PhysicalEstimate,
    TFactoryEstimate,
)
from quompass.core.algorithm import AlgorithmSpec, LogicalCounts
from quompass.core.error_budget import ErrorBudget, ErrorBudgetBreakdown
from quompass.core.hardware import HardwareModel
from quompass.core.types import HardwarePreset


# ---------------------------------------------------------------------------
# _safe_eval security tests
# ---------------------------------------------------------------------------


class TestSafeEval:
    def test_basic_arithmetic(self):
        assert _safe_eval("2 + 3", {}) == 5.0
        assert _safe_eval("2 * d", {"d": 5}) == 10.0

    def test_allowed_functions(self):
        assert _safe_eval("ceil(4.5)", {}) == 5.0
        assert _safe_eval("floor(4.5)", {}) == 4.0
        assert _safe_eval("sqrt(9)", {}) == 3.0
        assert _safe_eval("abs(-3)", {}) == 3.0
        assert _safe_eval("max(1, 2, 3)", {}) == 3.0
        assert _safe_eval("min(1, 2, 3)", {}) == 1.0

    def test_power_operator(self):
        assert _safe_eval("d ** 2", {"d": 3}) == 9.0

    def test_unary_negation(self):
        assert _safe_eval("-d", {"d": 3}) == -3.0

    def test_floor_division(self):
        assert _safe_eval("7 // 2", {}) == 3.0

    def test_modulo(self):
        assert _safe_eval("7 % 3", {}) == 1.0

    def test_nested_expression(self):
        assert _safe_eval("ceil(4.5 * d * d)", {"d": 3}) == 41.0

    def test_unknown_variable_raises(self):
        with pytest.raises(ValueError, match="Unknown variable"):
            _safe_eval("x + 1", {})

    def test_disallowed_function_raises(self):
        with pytest.raises(ValueError, match="Disallowed function"):
            _safe_eval("exec('import os')", {})

    def test_import_attempt_raises(self):
        with pytest.raises(ValueError, match="Disallowed|Unknown"):
            _safe_eval("__import__('os')", {})

    def test_attribute_access_raises(self):
        with pytest.raises(ValueError, match="Only simple function calls|Disallowed"):
            _safe_eval("''.join(['a'])", {})

    def test_string_constant_raises(self):
        with pytest.raises(ValueError, match="Disallowed constant type"):
            _safe_eval("'hello'", {})

    def test_syntax_error_raises(self):
        with pytest.raises(ValueError, match="Invalid formula syntax"):
            _safe_eval("2 +* 3", {})

    def test_list_comprehension_raises(self):
        with pytest.raises(ValueError, match="Disallowed expression node"):
            _safe_eval("[x for x in range(10)]", {})


# ---------------------------------------------------------------------------
# FormulaQEC validation
# ---------------------------------------------------------------------------


class TestFormulaQECValidation:
    def test_invalid_qubits_formula_syntax(self):
        with pytest.raises(ValueError, match="Invalid formula syntax"):
            FormulaQEC(
                name="bad",
                threshold=0.01,
                prefactor=0.1,
                qubits_formula="2 ** ** d",
                cycle_time_formula="10 * t_2q * d",
            )

    def test_invalid_cycle_time_formula_syntax(self):
        with pytest.raises(ValueError, match="Invalid formula syntax"):
            FormulaQEC(
                name="bad",
                threshold=0.01,
                prefactor=0.1,
                qubits_formula="2 * d * d",
                cycle_time_formula="10 ** ** t_2q",
            )

    def test_formula_with_unknown_variable(self):
        with pytest.raises(ValueError, match="Unknown variable"):
            FormulaQEC(
                name="bad",
                threshold=0.01,
                prefactor=0.1,
                qubits_formula="2 * unknown_var",
                cycle_time_formula="10 * t_2q * d",
            )

    def test_to_dict_from_dict_roundtrip(self):
        cc = color_code()
        d = cc.to_dict()
        cc2 = FormulaQEC.from_dict(d)
        assert cc2.name == cc.name
        assert cc2.error_correction_threshold == cc.error_correction_threshold
        assert cc2.qubits_formula == cc.qubits_formula

    def test_distance_coefficient_power(self):
        qec = FormulaQEC(
            name="test",
            threshold=0.01,
            prefactor=0.1,
            qubits_formula="2 * d * d",
            cycle_time_formula="10 * t_2q * d",
            distance_coefficient_power=1.0,
        )
        # With distance_coefficient_power=1, error rate includes d^k factor
        rate = qec.logical_error_rate(5, 0.001)
        assert rate > 0


# ---------------------------------------------------------------------------
# QECScheme.min_code_distance error paths
# ---------------------------------------------------------------------------


class TestMinCodeDistance:
    def test_exceeds_threshold_raises(self):
        sc = SurfaceCode()
        with pytest.raises(ValueError, match="exceeds QEC threshold"):
            sc.min_code_distance(1e-10, physical_error_rate=0.02)

    def test_cannot_achieve_target_raises(self):
        sc = SurfaceCode()
        with pytest.raises(ValueError, match="Cannot achieve target"):
            sc.min_code_distance(1e-100, physical_error_rate=0.009, max_distance=5)

    def test_returns_valid_odd_distance(self):
        sc = SurfaceCode()
        d = sc.min_code_distance(1e-6, physical_error_rate=0.001)
        assert d >= 3
        assert d % 2 == 1


# ---------------------------------------------------------------------------
# get_qec_scheme error path
# ---------------------------------------------------------------------------


class TestGetQecScheme:
    def test_unknown_scheme_raises(self):
        with pytest.raises(ValueError, match="Unknown QEC scheme"):
            get_qec_scheme("nonexistent_code")

    def test_surface_code_lookup(self):
        sc = get_qec_scheme("surface_code")
        assert sc.name == "surface_code"

    def test_color_code_lookup(self):
        cc = get_qec_scheme("color_code")
        assert cc.name == "color_code"


# ---------------------------------------------------------------------------
# PhysicalEstimate.runtime_human formatting
# ---------------------------------------------------------------------------


def _make_estimate(runtime_seconds: float) -> PhysicalEstimate:
    """Create a minimal PhysicalEstimate with a given runtime."""
    spec = AlgorithmSpec(
        name="Test", logical_counts=LogicalCounts(num_qubits=2, t_count=10)
    )
    hw = HardwareModel.from_preset(HardwarePreset.SUPERCONDUCTING_REALISTIC)
    eb = ErrorBudget(total=0.001)
    budget = eb.resolve(has_rotations=False)
    lq = LogicalQubitEstimate(
        code_distance=3, physical_qubits=18, logical_cycle_time=1e-6,
        logical_error_rate=1e-10,
    )
    return PhysicalEstimate(
        total_physical_qubits=100,
        runtime_seconds=runtime_seconds,
        rqops=1000.0,
        algorithmic_logical_qubits=2,
        physical_qubits_for_algorithm=50,
        physical_qubits_for_t_factories=50,
        logical_qubit=lq,
        t_factory=None,
        algorithmic_logical_depth=100,
        num_t_states=10,
        clock_frequency=1e6,
        error_budget=budget,
        required_logical_error_rate=1e-10,
        required_t_state_error_rate=1e-6,
        algorithm_spec=spec,
        hardware_model=hw,
        qec_scheme_name="surface_code",
        backend_name="test",
    )


class TestRuntimeHuman:
    def test_microseconds(self):
        est = _make_estimate(0.000_5)
        assert "us" in est.runtime_human

    def test_seconds(self):
        est = _make_estimate(30)
        assert est.runtime_human == "30s"

    def test_minutes(self):
        est = _make_estimate(125)  # 2m 5s
        assert "2m" in est.runtime_human
        assert "5s" in est.runtime_human

    def test_hours(self):
        est = _make_estimate(7200)  # 2h 0m
        assert "2h" in est.runtime_human

    def test_days(self):
        est = _make_estimate(172800)  # 2d 0h
        assert "2d" in est.runtime_human

    def test_space_time_volume(self):
        est = _make_estimate(10.0)
        assert est.space_time_volume == 100 * 10.0

    def test_summary_dict_keys(self):
        est = _make_estimate(1.0)
        d = est.summary_dict()
        assert "total_physical_qubits" in d
        assert "runtime" in d
        assert "backend" in d

    def test_to_dict_structure(self):
        est = _make_estimate(1.0)
        d = est.to_dict()
        assert "summary" in d
        assert "breakdown" in d
        assert "logical_qubit" in d
        assert "provenance" in d
