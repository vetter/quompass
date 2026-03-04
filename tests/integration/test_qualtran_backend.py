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
