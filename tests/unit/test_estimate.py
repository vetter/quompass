"""Tests for the top-level estimate() API."""

import quompass
from quompass.templates.shor import shor


class TestEstimate:
    def test_basic_estimate(self):
        spec = shor(n_bits=64)
        result = quompass.estimate(spec)
        assert isinstance(result, quompass.PhysicalEstimate)
        assert result.total_physical_qubits > 0
        assert result.runtime_seconds > 0

    def test_with_hardware_string(self):
        spec = shor(n_bits=64)
        result = quompass.estimate(spec, hardware="gate_ns_e3")
        assert result.hardware_model.name == "gate_ns_e3"

    def test_with_hardware_preset(self):
        spec = shor(n_bits=64)
        result = quompass.estimate(
            spec, hardware=quompass.HardwarePreset.TRAPPED_ION_REALISTIC
        )
        assert result.hardware_model.name == "gate_us_e3"

    def test_with_qec_string(self):
        spec = shor(n_bits=64)
        result = quompass.estimate(spec, qec="surface_code")
        assert result.qec_scheme_name == "surface_code"

    def test_with_qec_instance(self):
        spec = shor(n_bits=64)
        result = quompass.estimate(spec, qec=quompass.SurfaceCode())
        assert result.qec_scheme_name == "surface_code"

    def test_with_float_budget(self):
        spec = shor(n_bits=64)
        result = quompass.estimate(spec, error_budget=0.01)
        assert result.error_budget.total == 0.01

    def test_runtime_human_readable(self):
        spec = shor(n_bits=64)
        result = quompass.estimate(spec)
        assert isinstance(result.runtime_human, str)
        assert len(result.runtime_human) > 0

    def test_space_time_volume(self):
        spec = shor(n_bits=64)
        result = quompass.estimate(spec)
        expected = result.total_physical_qubits * result.runtime_seconds
        assert abs(result.space_time_volume - expected) < 1e-10

    def test_summary_dict(self):
        spec = shor(n_bits=64)
        result = quompass.estimate(spec)
        d = result.summary_dict()
        assert "total_physical_qubits" in d
        assert "runtime" in d
        assert "code_distance" in d
