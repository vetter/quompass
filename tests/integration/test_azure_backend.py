"""Integration tests for the Azure QRE backend adapter.

These tests require qsharp to be installed and are skipped otherwise.
"""

import pytest

qsharp = pytest.importorskip("qsharp", reason="qsharp not installed")

from quompass.backends.azure.adapter import AzurePhysicalEstimator
from quompass.core.algorithm import AlgorithmSpec, LogicalCounts
from quompass.core.error_budget import ErrorBudget
from quompass.core.hardware import HardwareModel
from quompass.core.qec import SurfaceCode, color_code
from quompass.core.types import HardwarePreset


@pytest.mark.integration
class TestAzurePhysicalEstimator:
    def test_is_available(self):
        est = AzurePhysicalEstimator()
        assert est.is_available()

    def test_name(self):
        est = AzurePhysicalEstimator()
        assert est.name == "azure"

    def test_basic_estimation(self):
        est = AzurePhysicalEstimator()
        spec = AlgorithmSpec(
            name="Test",
            logical_counts=LogicalCounts(num_qubits=10, t_count=100),
        )
        hw = HardwareModel.from_preset(HardwarePreset.SUPERCONDUCTING_REALISTIC)
        result = est.estimate(
            spec.logical_counts, hw, SurfaceCode(), ErrorBudget(total=0.001), spec
        )
        assert result.total_physical_qubits > 0
        assert result.runtime_seconds > 0
        assert result.backend_name == "azure"
        assert result.raw_backend_output is not None

    def test_with_formula_qec(self):
        """Azure backend should work with FormulaQEC schemes."""
        est = AzurePhysicalEstimator()
        spec = AlgorithmSpec(
            name="Test",
            logical_counts=LogicalCounts(num_qubits=10, t_count=100),
        )
        hw = HardwareModel.from_preset(HardwarePreset.SUPERCONDUCTING_REALISTIC)
        cc = color_code()
        result = est.estimate(
            spec.logical_counts, hw, cc, ErrorBudget(total=0.001), spec
        )
        assert result.total_physical_qubits > 0
        assert result.qec_scheme_name == "color_code"
