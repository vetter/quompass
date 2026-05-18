"""Tests for QEC scheme abstractions."""

import pytest

from quompass.core.hardware import HardwareModel
from quompass.core.qec import FloquetCode, SurfaceCode, get_qec_scheme
from quompass.core.types import HardwarePreset


class TestSurfaceCode:
    def test_name(self):
        sc = SurfaceCode()
        assert sc.name == "surface_code"

    def test_threshold(self):
        sc = SurfaceCode()
        assert sc.error_correction_threshold == 0.01

    def test_physical_qubits_per_logical(self):
        sc = SurfaceCode()
        assert sc.physical_qubits_per_logical(3) == 18  # 2 * 9
        assert sc.physical_qubits_per_logical(5) == 50  # 2 * 25
        assert sc.physical_qubits_per_logical(7) == 98  # 2 * 49

    def test_logical_error_rate_decreases_with_distance(self):
        sc = SurfaceCode()
        p = 1e-3
        rates = [sc.logical_error_rate(d, p) for d in range(3, 15, 2)]
        # Each rate should be smaller than the previous
        for i in range(1, len(rates)):
            assert rates[i] < rates[i - 1]

    def test_logical_error_rate_known_value(self):
        sc = SurfaceCode()
        # At d=3, p=1e-3: 0.03 * (0.1)^2 = 0.0003
        rate = sc.logical_error_rate(3, 1e-3)
        assert abs(rate - 0.03 * (0.1) ** 2) < 1e-10

    def test_min_code_distance(self):
        sc = SurfaceCode()
        d = sc.min_code_distance(1e-10, 1e-3)
        assert d % 2 == 1  # Must be odd
        assert d >= 3
        # Verify the distance achieves the target
        assert sc.logical_error_rate(d, 1e-3) <= 1e-10
        # Verify d-2 does NOT achieve the target
        if d > 3:
            assert sc.logical_error_rate(d - 2, 1e-3) > 1e-10

    def test_min_code_distance_above_threshold(self):
        sc = SurfaceCode()
        with pytest.raises(ValueError, match="exceeds QEC threshold"):
            sc.min_code_distance(1e-10, 0.02)

    def test_logical_cycle_time(self):
        sc = SurfaceCode()
        hw = HardwareModel.from_preset(HardwarePreset.SUPERCONDUCTING_REALISTIC)
        qp = hw.qubit_params
        t = sc.logical_cycle_time(3, qp)
        expected = (4 * qp.two_qubit_gate_time + 2 * qp.one_qubit_measurement_time) * 3
        assert abs(t - expected) < 1e-15


class TestFloquetCode:
    def test_name(self):
        fc = FloquetCode()
        assert fc.name == "floquet_code"

    def test_physical_qubits_per_logical(self):
        fc = FloquetCode()
        # d=3: 4*9 + 8*2 = 36 + 16 = 52
        assert fc.physical_qubits_per_logical(3) == 52
        # d=5: 4*25 + 8*4 = 100 + 32 = 132
        assert fc.physical_qubits_per_logical(5) == 132


class TestTransversalMagicStates:
    def test_surface_code_requires_distillation(self):
        assert SurfaceCode().transversal_magic_states is False

    def test_floquet_code_requires_distillation(self):
        assert FloquetCode().transversal_magic_states is False


class TestGetQECScheme:
    def test_surface_code(self):
        scheme = get_qec_scheme("surface_code")
        assert isinstance(scheme, SurfaceCode)

    def test_floquet_code(self):
        scheme = get_qec_scheme("floquet_code")
        assert isinstance(scheme, FloquetCode)

    def test_unknown(self):
        with pytest.raises(ValueError, match="Unknown QEC scheme"):
            get_qec_scheme("nonexistent")
