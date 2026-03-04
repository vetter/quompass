"""Tests for MQT backend stub."""

import pytest

from quompass.backends.mqt.adapter import MQTPhysicalEstimator
from quompass.backends.registry import discover_physical_estimators, select_backends
from quompass.core.qec import SurfaceCode


class TestMQTStub:
    def test_name(self):
        est = MQTPhysicalEstimator()
        assert est.name == "mqt"

    def test_is_available_returns_false(self):
        """mqt.core is not installed in the test environment."""
        est = MQTPhysicalEstimator()
        assert est.is_available() is False

    def test_estimate_raises_not_implemented(
        self, small_algorithm_spec, superconducting_hw, surface_code, default_error_budget
    ):
        est = MQTPhysicalEstimator()
        from quompass.core.algorithm import LogicalCounts

        lc = small_algorithm_spec.logical_counts
        with pytest.raises(NotImplementedError, match="MQT backend is not yet implemented"):
            est.estimate(lc, superconducting_hw, surface_code, default_error_budget, small_algorithm_spec)

    def test_supports_qec_returns_true(self):
        est = MQTPhysicalEstimator()
        qec = SurfaceCode()
        assert est.supports_qec(qec) is True

    def test_discovered_by_registry(self):
        estimators = discover_physical_estimators()
        assert "mqt" in estimators
        assert estimators["mqt"].name == "mqt"

    def test_auto_selection_skips_unavailable(self):
        """Auto selection should not pick mqt since it's unavailable."""
        _, pe = select_backends("auto", "auto")
        assert pe.name != "mqt"
