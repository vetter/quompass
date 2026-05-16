"""Tests for hardware model types."""

import pytest

from quompass.core.hardware import HardwareModel
from quompass.core.types import HardwarePreset, InstructionSet


class TestHardwarePresets:
    @pytest.mark.parametrize("preset", list(HardwarePreset))
    def test_from_preset(self, preset):
        hw = HardwareModel.from_preset(preset)
        assert hw.name == preset.value
        assert hw.qubit_params is not None
        assert hw.description != ""

    def test_from_string(self):
        hw = HardwareModel.from_preset("gate_ns_e3")
        assert hw.name == "gate_ns_e3"

    def test_superconducting_is_gate_based(self):
        hw = HardwareModel.from_preset(HardwarePreset.SUPERCONDUCTING_REALISTIC)
        assert hw.qubit_params.instruction_set == InstructionSet.GATE_BASED

    def test_majorana_is_majorana(self):
        hw = HardwareModel.from_preset(HardwarePreset.MAJORANA_REALISTIC)
        assert hw.qubit_params.instruction_set == InstructionSet.MAJORANA

    def test_majorana_has_joint_measurement(self):
        hw = HardwareModel.from_preset(HardwarePreset.MAJORANA_REALISTIC)
        assert hw.qubit_params.two_qubit_joint_measurement_time is not None
        assert hw.qubit_params.two_qubit_joint_measurement_error_rate is not None

    def test_worst_case_clifford_error(self):
        hw = HardwareModel.from_preset(HardwarePreset.SUPERCONDUCTING_REALISTIC)
        assert hw.qubit_params.worst_case_clifford_error == 1e-3

    def test_invalid_preset(self):
        with pytest.raises(ValueError):
            HardwareModel.from_preset("nonexistent")
