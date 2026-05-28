"""Integration tests for the Qualtran backend adapter.

These tests require qualtran to be installed and are skipped otherwise.
"""

import pytest

qualtran = pytest.importorskip("qualtran", reason="qualtran not installed")

from quompass.backends.qualtran.adapter import QualtranLogicalEstimator
from quompass.core.algorithm import AlgorithmSpec, LogicalCounts


@pytest.mark.integration
class TestQualtranLogicalEstimator:
    def test_is_available(self):
        est = QualtranLogicalEstimator()
        assert est.is_available()

    def test_name(self):
        est = QualtranLogicalEstimator()
        assert est.name == "qualtran"

    def test_estimate_from_bloq(self):
        """Test direct Bloq estimation with a simple known Bloq."""
        from qualtran.bloqs.basic_gates import TGate

        est = QualtranLogicalEstimator()
        bloq = TGate()
        counts = est.estimate_from_bloq(bloq)
        assert isinstance(counts, LogicalCounts)
        assert counts.num_qubits >= 1

    def test_fallback_to_spec_counts(self):
        """When spec can't be mapped to Bloq, falls back to existing counts."""
        est = QualtranLogicalEstimator()
        spec = AlgorithmSpec(
            name="Unmappable",
            logical_counts=LogicalCounts(num_qubits=42, t_count=100),
            algorithm_family="unknown",
        )
        counts = est.estimate(spec)
        assert counts.num_qubits == 42
        assert counts.t_count == 100

    def test_shor_bloq_mapping(self):
        """Shor cryptanalysis family maps to ModExp Bloq and extracts real counts."""
        est = QualtranLogicalEstimator()
        spec = AlgorithmSpec(
            name="Shor 16-bit",
            logical_counts=LogicalCounts(num_qubits=32, t_count=1000),
            algorithm_family="cryptanalysis",
            problem_parameters={"n_bits": 16},
        )
        counts = est.estimate(spec)
        # Should get Bloq-derived counts, NOT the template fallback
        assert counts.num_qubits != 32  # Qualtran computes different qubit count
        assert counts.total_t_equivalent > 0
        assert counts.ccz_count > 0  # ModExp uses CCZ/Toffoli gates
        assert counts.measurement_count > 0

    def test_shor_bloq_cost_extraction(self):
        """Verify ModExp Bloq produces reasonable resource counts."""
        from quompass.backends.qualtran.bloq_bridge import _FAMILY_BUILDERS
        from quompass.backends.qualtran.cost_extract import extract_logical_counts

        bloq = _FAMILY_BUILDERS["cryptanalysis"]({"n_bits": 8})
        counts = extract_logical_counts(bloq)
        # Small factoring should have modest but nonzero counts
        assert counts.num_qubits >= 8
        assert counts.total_t_equivalent > 0

    def test_direct_bloq_source(self):
        """Test qualtran: source prefix for direct Bloq import."""
        from quompass.backends.qualtran.bloq_bridge import spec_to_bloq

        spec = AlgorithmSpec(
            name="Direct TGate",
            logical_counts=LogicalCounts(num_qubits=1),
            source="qualtran:qualtran.bloqs.basic_gates:TGate",
        )
        bloq = spec_to_bloq(spec)
        assert type(bloq).__name__ == "TGate"
