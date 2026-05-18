"""Tests for the top-level estimate() API."""

from pathlib import Path

import quompass
from quompass.io import load_algorithm, load_hardware, load_qec
from quompass.templates.shor import shor

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


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


class TestNeutralAtomExample:
    """The Gidney-2025 / Cain-et-al. neutral-atom example must stay runnable."""

    def test_lp_qldpc_reaches_about_11k_qubits(self):
        spec = load_algorithm(EXAMPLES / "shor_2048_gidney2025.yaml")
        hw = load_hardware(EXAMPLES / "neutral_atom.yaml")
        qec = load_qec(EXAMPLES / "lp_qldpc.yaml")
        result = quompass.estimate(spec, hardware=hw, qec=qec)
        # Transversal magic states: no distillation factory.
        assert result.t_factory is None
        assert result.physical_qubits_for_t_factories == 0
        # Cain et al. space-efficient RSA-2048 architecture is 11,033 atoms.
        assert 10_000 <= result.total_physical_qubits <= 13_000
        # CCZ counted natively (6.5e9), not as 4x T-equivalents.
        assert result.num_t_states == 6_500_000_000

    def test_surface_code_contrast_is_far_larger(self):
        """The same logical circuit on a surface code needs ~1000x more qubits."""
        spec = load_algorithm(EXAMPLES / "shor_2048_gidney2025.yaml")
        lp = quompass.estimate(
            spec,
            hardware=load_hardware(EXAMPLES / "neutral_atom.yaml"),
            qec=load_qec(EXAMPLES / "lp_qldpc.yaml"),
        )
        sc = quompass.estimate(spec)  # default surface code + superconducting
        assert sc.total_physical_qubits > 100 * lp.total_physical_qubits
