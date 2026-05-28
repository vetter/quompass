"""Private tests for the Gidney-2025 / Cain-et-al. neutral-atom example.

Depends on the private example YAMLs in the studio-root ``examples/``
directory, which are not shipped with the public quompass distribution.
Run from the studio root with ``quompass`` installed from ``public/``.
"""

from pathlib import Path

import quompass
from quompass.io import load_algorithm, load_hardware, load_qec

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


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
