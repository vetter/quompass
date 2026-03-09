"""Unit tests for the Azure backend adapter, param_map, and result_map.

These tests do NOT require qsharp -- they test the mapping logic
and error handling in isolation.
"""

import pytest

from quompass.backends.azure.param_map import (
    _seconds_to_azure_time,
    build_params,
    _map_qec_scheme,
)
from quompass.backends.azure.result_map import parse_result
from quompass.core.algorithm import AlgorithmSpec, LogicalCounts
from quompass.core.error_budget import ErrorBudget
from quompass.core.hardware import HardwareModel
from quompass.core.qec import SurfaceCode, FloquetCode, color_code
from quompass.core.types import HardwarePreset


# ---------------------------------------------------------------------------
# param_map tests
# ---------------------------------------------------------------------------


class TestSecondsToAzureTime:
    def test_nanoseconds(self):
        assert _seconds_to_azure_time(50e-9) == "50 ns"

    def test_microseconds(self):
        assert _seconds_to_azure_time(100e-6) == "100 us"

    def test_milliseconds(self):
        assert _seconds_to_azure_time(1e-3) == "1 ms"

    def test_fractional_ns(self):
        result = _seconds_to_azure_time(50.5e-9)
        assert "ns" in result


class TestBuildParams:
    def test_surface_code(self):
        hw = HardwareModel.from_preset(HardwarePreset.SUPERCONDUCTING_REALISTIC)
        params = build_params(hw, SurfaceCode(), ErrorBudget(total=0.001))
        assert params["qecScheme"] == {"name": "surface_code"}
        assert params["errorBudget"] == 0.001
        assert "qubitParams" in params

    def test_floquet_code(self):
        hw = HardwareModel.from_preset(HardwarePreset.MAJORANA_REALISTIC)
        params = build_params(hw, FloquetCode(), ErrorBudget(total=0.01))
        assert params["qecScheme"] == {"name": "floquet_code"}

    def test_formula_qec(self):
        hw = HardwareModel.from_preset(HardwarePreset.SUPERCONDUCTING_REALISTIC)
        cc = color_code()
        params = build_params(hw, cc, ErrorBudget(total=0.001))
        scheme = params["qecScheme"]
        assert scheme["name"] == "color_code"
        assert "errorCorrectionThreshold" in scheme
        assert "crossingPrefactor" in scheme
        # Verify formula variable translation
        assert "codeDistance" in scheme["physicalQubitsPerLogicalQubit"]
        assert "twoQubitGateTime" in scheme["logicalCycleTime"]
        # Ensure quompass variable names are NOT in the Azure formula
        assert " d " not in f" {scheme['physicalQubitsPerLogicalQubit']} "

    def test_qubit_params_mapping(self):
        hw = HardwareModel.from_preset(HardwarePreset.SUPERCONDUCTING_REALISTIC)
        params = build_params(hw, SurfaceCode(), ErrorBudget())
        qp = params["qubitParams"]
        assert qp["instructionSet"] == "gate_based"
        assert qp["oneQubitGateTime"] == "50 ns"
        assert qp["oneQubitGateErrorRate"] == 1e-3

    def test_majorana_params_mapping(self):
        hw = HardwareModel.from_preset(HardwarePreset.MAJORANA_REALISTIC)
        params = build_params(hw, FloquetCode(), ErrorBudget())
        qp = params["qubitParams"]
        assert qp["instructionSet"] == "majorana"
        assert "twoQubitJointMeasurementTime" in qp
        assert "twoQubitJointMeasurementErrorRate" in qp


class TestMapQecScheme:
    def test_surface_uses_preset(self):
        result = _map_qec_scheme(SurfaceCode())
        assert result == {"name": "surface_code"}

    def test_floquet_uses_preset(self):
        result = _map_qec_scheme(FloquetCode())
        assert result == {"name": "floquet_code"}

    def test_formula_qec_translates_variables(self):
        cc = color_code()
        result = _map_qec_scheme(cc)
        cycle = result["logicalCycleTime"]
        qubits = result["physicalQubitsPerLogicalQubit"]
        # d -> codeDistance
        assert "codeDistance" in qubits
        # t_2q -> twoQubitGateTime
        assert "twoQubitGateTime" in cycle


# ---------------------------------------------------------------------------
# result_map tests
# ---------------------------------------------------------------------------

def _make_azure_result(**overrides) -> dict:
    """Create a minimal valid Azure QRE result dict."""
    base = {
        "physicalCounts": {
            "physicalQubits": 10000,
            "runtime": 1_000_000_000,  # 1 second in ns
            "rqops": 5000.0,
            "breakdown": {
                "algorithmicLogicalQubits": 10,
                "algorithmicPhysicalQubits": 5000,
                "physicalQubitsForTfactories": 5000,
                "logicalDepth": 1000,
                "numTstates": 500,
                "clockFrequency": 100.0,
                "requiredLogicalQubitErrorRate": 1e-10,
                "requiredLogicalTstateErrorRate": 1e-6,
                "numTfactories": 4,
            },
        },
        "logicalQubit": {
            "codeDistance": 17,
            "physicalQubits": 578,
            "logicalCycleTime": 6800,  # ns
            "logicalErrorRate": 1e-12,
        },
        "tfactory": {
            "physicalQubits": 1250,
            "runtime": 46800,  # ns
            "numRounds": 2,
            "logicalErrorRate": 1e-8,
        },
    }
    base.update(overrides)
    return base


def _make_inputs():
    """Create standard test inputs for parse_result."""
    spec = AlgorithmSpec(
        name="Test",
        logical_counts=LogicalCounts(num_qubits=10, t_count=100),
    )
    hw = HardwareModel.from_preset(HardwarePreset.SUPERCONDUCTING_REALISTIC)
    qec = SurfaceCode()
    eb = ErrorBudget(total=0.001)
    return spec.logical_counts, hw, qec, eb, spec


class TestParseResult:
    def test_basic_parsing(self):
        lc, hw, qec, eb, spec = _make_inputs()
        result = parse_result(_make_azure_result(), lc, hw, qec, eb, spec)
        assert result.total_physical_qubits == 10000
        assert result.runtime_seconds == pytest.approx(1.0)
        assert result.rqops == 5000.0
        assert result.backend_name == "azure"
        assert result.logical_qubit.code_distance == 17

    def test_t_factory_parsing(self):
        lc, hw, qec, eb, spec = _make_inputs()
        result = parse_result(_make_azure_result(), lc, hw, qec, eb, spec)
        assert result.t_factory is not None
        assert result.t_factory.num_factories == 4
        assert result.t_factory.num_rounds == 2

    def test_no_t_factory(self):
        lc, hw, qec, eb, spec = _make_inputs()
        azure = _make_azure_result()
        azure["tfactory"] = {}
        result = parse_result(azure, lc, hw, qec, eb, spec)
        assert result.t_factory is None

    def test_raw_backend_output_preserved(self):
        lc, hw, qec, eb, spec = _make_inputs()
        azure = _make_azure_result()
        result = parse_result(azure, lc, hw, qec, eb, spec)
        assert result.raw_backend_output is not None

    def test_missing_physical_counts_raises(self):
        lc, hw, qec, eb, spec = _make_inputs()
        with pytest.raises(ValueError, match="missing 'physicalCounts'"):
            parse_result({}, lc, hw, qec, eb, spec)

    def test_unexpected_type_raises(self):
        lc, hw, qec, eb, spec = _make_inputs()
        with pytest.raises(ValueError, match="Unexpected Azure result type"):
            parse_result("not a dict", lc, hw, qec, eb, spec)

    def test_ns_to_seconds_conversion(self):
        lc, hw, qec, eb, spec = _make_inputs()
        azure = _make_azure_result()
        azure["physicalCounts"]["runtime"] = 5_000_000_000  # 5 seconds
        result = parse_result(azure, lc, hw, qec, eb, spec)
        assert result.runtime_seconds == pytest.approx(5.0)

    def test_logical_cycle_time_conversion(self):
        lc, hw, qec, eb, spec = _make_inputs()
        result = parse_result(_make_azure_result(), lc, hw, qec, eb, spec)
        # 6800 ns -> 6.8e-6 seconds
        assert result.logical_qubit.logical_cycle_time == pytest.approx(6.8e-6)
