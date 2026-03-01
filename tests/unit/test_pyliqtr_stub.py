"""Tests for pyLIQTR backend stub."""

import pytest

from ftqre.backends.pyliqtr.adapter import PyLIQTRLogicalEstimator
from ftqre.backends.registry import discover_logical_estimators, select_backends


class TestPyLIQTRStub:
    def test_name(self):
        est = PyLIQTRLogicalEstimator()
        assert est.name == "pyliqtr"

    def test_is_available_returns_false(self):
        """pyLIQTR is not installed in the test environment."""
        est = PyLIQTRLogicalEstimator()
        assert est.is_available() is False

    def test_estimate_raises_not_implemented(self, small_algorithm_spec):
        est = PyLIQTRLogicalEstimator()
        with pytest.raises(NotImplementedError, match="pyLIQTR backend is not yet implemented"):
            est.estimate(small_algorithm_spec)

    def test_discovered_by_registry(self):
        estimators = discover_logical_estimators()
        assert "pyliqtr" in estimators
        assert estimators["pyliqtr"].name == "pyliqtr"

    def test_auto_selection_skips_unavailable(self):
        """Auto selection should not pick pyliqtr since it's unavailable."""
        le, _ = select_backends("auto", "auto")
        assert le.name != "pyliqtr"
