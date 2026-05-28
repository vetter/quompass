"""Tests for FormulaQEC and safe formula evaluation."""

import pytest

from quompass.core.hardware import HardwareModel
from quompass.core.qec import FormulaQEC, _safe_eval, color_code, get_qec_scheme
from quompass.core.types import HardwarePreset


class TestSafeEval:
    def test_arithmetic(self):
        assert _safe_eval("2 + 3", {}) == 5.0
        assert _safe_eval("10 - 4", {}) == 6.0
        assert _safe_eval("3 * 7", {}) == 21.0
        assert _safe_eval("15 / 3", {}) == 5.0
        assert _safe_eval("7 // 2", {}) == 3.0
        assert _safe_eval("7 % 3", {}) == 1.0
        assert _safe_eval("2 ** 3", {}) == 8.0

    def test_variables(self):
        assert _safe_eval("d * d", {"d": 5}) == 25.0
        assert _safe_eval("2 * d", {"d": 3}) == 6.0

    def test_unary_neg(self):
        assert _safe_eval("-d", {"d": 5}) == -5.0

    def test_functions(self):
        assert _safe_eval("round(4.7)", {}) == 5.0
        assert _safe_eval("ceil(4.1)", {}) == 5.0
        assert _safe_eval("floor(4.9)", {}) == 4.0
        assert _safe_eval("sqrt(9)", {}) == 3.0
        assert _safe_eval("max(3, 7)", {}) == 7.0
        assert _safe_eval("min(3, 7)", {}) == 3.0
        assert _safe_eval("abs(-5)", {}) == 5.0

    def test_complex_formula(self):
        # 2 * d^2 -- surface code formula
        assert _safe_eval("2 * d * d", {"d": 5}) == 50.0
        # ceil(4.5 * d^2) -- color code formula
        assert _safe_eval("ceil(4.5 * d * d)", {"d": 3}) == 41.0
        # 4*d^2 + 8*(d-1) -- Floquet formula
        assert _safe_eval("4 * d * d + 8 * (d - 1)", {"d": 3}) == 52.0

    def test_unknown_variable(self):
        with pytest.raises(ValueError, match="Unknown variable"):
            _safe_eval("x + 1", {"d": 5})

    def test_disallowed_function(self):
        with pytest.raises(ValueError, match="Disallowed function"):
            _safe_eval("__import__('os')", {})

    def test_disallowed_attribute(self):
        with pytest.raises(ValueError, match="Disallowed expression node"):
            _safe_eval("d.__class__", {"d": 5})

    def test_invalid_syntax(self):
        with pytest.raises(ValueError, match="Invalid formula syntax"):
            _safe_eval("2 +* 3", {})

    def test_string_constant_rejected(self):
        with pytest.raises(ValueError, match="Disallowed constant type"):
            _safe_eval("'hello'", {})


class TestFormulaQEC:
    def test_basic_construction(self):
        fqec = FormulaQEC(
            name="test_code",
            threshold=0.01,
            prefactor=0.03,
            qubits_formula="2 * d * d",
            cycle_time_formula="(4 * t_2q + 2 * t_meas) * d",
        )
        assert fqec.name == "test_code"
        assert fqec.error_correction_threshold == 0.01
        assert fqec.crossing_prefactor == 0.03

    def test_matches_surface_code(self):
        """FormulaQEC with surface code parameters should match SurfaceCode."""
        from quompass.core.qec import SurfaceCode

        sc = SurfaceCode()
        fqec = FormulaQEC(
            name="surface_formula",
            threshold=0.01,
            prefactor=0.03,
            qubits_formula="2 * d * d",
            cycle_time_formula="(4 * t_2q + 2 * t_meas) * d",
        )

        hw = HardwareModel.from_preset(HardwarePreset.SUPERCONDUCTING_REALISTIC)
        for d in range(3, 15, 2):
            assert fqec.physical_qubits_per_logical(d) == sc.physical_qubits_per_logical(d)
            assert abs(
                fqec.logical_error_rate(d, 1e-3) - sc.logical_error_rate(d, 1e-3)
            ) < 1e-15
            assert abs(
                fqec.logical_cycle_time(d, hw.qubit_params)
                - sc.logical_cycle_time(d, hw.qubit_params)
            ) < 1e-20

    def test_physical_qubits(self):
        fqec = FormulaQEC(
            name="test",
            threshold=0.01,
            prefactor=0.03,
            qubits_formula="ceil(4.5 * d * d)",
            cycle_time_formula="10 * t_2q * d",
        )
        assert fqec.physical_qubits_per_logical(3) == 41  # ceil(4.5 * 9) = 41
        assert fqec.physical_qubits_per_logical(5) == 113  # ceil(4.5 * 25) = 113

    def test_logical_error_rate(self):
        fqec = FormulaQEC(
            name="test",
            threshold=0.01,
            prefactor=0.03,
            qubits_formula="2 * d * d",
            cycle_time_formula="t_2q * d",
        )
        # Standard model: a * (p/p*)^((d+1)/2)
        rate = fqec.logical_error_rate(3, 1e-3)
        assert abs(rate - 0.03 * (0.1) ** 2) < 1e-15

    def test_logical_error_rate_with_distance_power(self):
        fqec = FormulaQEC(
            name="test",
            threshold=0.01,
            prefactor=0.03,
            qubits_formula="2 * d * d",
            cycle_time_formula="t_2q * d",
            distance_coefficient_power=1.0,
        )
        # a * d^k * (p/p*)^((d+1)/2)
        rate = fqec.logical_error_rate(5, 1e-3)
        expected = 0.03 * (5 ** 1.0) * (0.1 ** 3)
        assert abs(rate - expected) < 1e-15

    def test_cycle_time(self):
        fqec = FormulaQEC(
            name="test",
            threshold=0.01,
            prefactor=0.03,
            qubits_formula="2 * d * d",
            cycle_time_formula="10 * t_2q * d",
        )
        hw = HardwareModel.from_preset(HardwarePreset.SUPERCONDUCTING_REALISTIC)
        t = fqec.logical_cycle_time(5, hw.qubit_params)
        expected = 10 * hw.qubit_params.two_qubit_gate_time * 5
        assert abs(t - expected) < 1e-20

    def test_min_code_distance(self):
        fqec = FormulaQEC(
            name="test",
            threshold=0.01,
            prefactor=0.03,
            qubits_formula="2 * d * d",
            cycle_time_formula="t_2q * d",
        )
        d = fqec.min_code_distance(1e-10, 1e-3)
        assert d % 2 == 1
        assert d >= 3
        assert fqec.logical_error_rate(d, 1e-3) <= 1e-10

    def test_above_threshold_raises(self):
        fqec = FormulaQEC(
            name="test",
            threshold=0.01,
            prefactor=0.03,
            qubits_formula="2 * d * d",
            cycle_time_formula="t_2q * d",
        )
        with pytest.raises(ValueError, match="exceeds QEC threshold"):
            fqec.min_code_distance(1e-10, 0.02)

    def test_invalid_qubits_formula(self):
        with pytest.raises(ValueError, match="Invalid formula syntax"):
            FormulaQEC(
                name="bad",
                threshold=0.01,
                prefactor=0.03,
                qubits_formula="2 +* d",
                cycle_time_formula="t_2q * d",
            )

    def test_to_dict_from_dict_roundtrip(self):
        fqec = FormulaQEC(
            name="test_code",
            threshold=0.008,
            prefactor=0.05,
            qubits_formula="ceil(4.5 * d * d)",
            cycle_time_formula="10 * t_2q * d",
            distance_coefficient_power=0.5,
        )
        d = fqec.to_dict()
        restored = FormulaQEC.from_dict(d)
        assert restored.name == fqec.name
        assert restored.error_correction_threshold == fqec.error_correction_threshold
        assert restored.crossing_prefactor == fqec.crossing_prefactor
        assert restored.qubits_formula == fqec.qubits_formula
        assert restored.cycle_time_formula == fqec.cycle_time_formula
        assert restored.distance_coefficient_power == fqec.distance_coefficient_power

    def test_transversal_magic_states_default_false(self):
        fqec = FormulaQEC(
            name="test",
            threshold=0.01,
            prefactor=0.03,
            qubits_formula="2 * d * d",
            cycle_time_formula="t_2q * d",
        )
        assert fqec.transversal_magic_states is False

    def test_transversal_magic_states_explicit(self):
        fqec = FormulaQEC(
            name="lp_code",
            threshold=0.008,
            prefactor=2.0e-5,
            qubits_formula="7.886",
            cycle_time_formula="3 * t_meas",
            transversal_magic_states=True,
        )
        assert fqec.transversal_magic_states is True

    def test_transversal_magic_states_roundtrip(self):
        fqec = FormulaQEC(
            name="lp_code",
            threshold=0.008,
            prefactor=2.0e-5,
            qubits_formula="7.886",
            cycle_time_formula="3 * t_meas",
            transversal_magic_states=True,
        )
        restored = FormulaQEC.from_dict(fqec.to_dict())
        assert restored.transversal_magic_states is True

    def test_cycle_time_with_joint_measurement(self):
        """FormulaQEC can use t_jm for Majorana-style codes."""
        fqec = FormulaQEC(
            name="majorana_formula",
            threshold=0.01,
            prefactor=0.07,
            qubits_formula="4 * d * d + 8 * (d - 1)",
            cycle_time_formula="3 * t_jm * d",
        )
        hw = HardwareModel.from_preset(HardwarePreset.MAJORANA_REALISTIC)
        t = fqec.logical_cycle_time(5, hw.qubit_params)
        expected = 3 * hw.qubit_params.two_qubit_joint_measurement_time * 5
        assert abs(t - expected) < 1e-20


class TestColorCode:
    def test_builtin_color_code(self):
        cc = color_code()
        assert cc.name == "color_code"
        assert cc.error_correction_threshold == 0.0077
        assert cc.crossing_prefactor == 0.1

    def test_color_code_qubits(self):
        cc = color_code()
        assert cc.physical_qubits_per_logical(3) == 41  # ceil(4.5 * 9)
        assert cc.physical_qubits_per_logical(5) == 113  # ceil(4.5 * 25)

    def test_color_code_error_rate_decreases(self):
        cc = color_code()
        rates = [cc.logical_error_rate(d, 1e-3) for d in range(3, 13, 2)]
        for i in range(1, len(rates)):
            assert rates[i] < rates[i - 1]

    def test_color_code_in_registry(self):
        cc = get_qec_scheme("color_code")
        assert cc.name == "color_code"
        assert isinstance(cc, FormulaQEC)

    def test_color_code_with_estimator(self):
        """Full pipeline with color code."""
        import quompass
        from quompass.core.algorithm import AlgorithmSpec, LogicalCounts

        spec = AlgorithmSpec(
            name="Test",
            logical_counts=LogicalCounts(num_qubits=10, t_count=100),
        )
        result = quompass.estimate(spec, qec=color_code())
        assert result.total_physical_qubits > 0
        assert result.runtime_seconds > 0
