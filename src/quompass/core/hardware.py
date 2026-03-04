"""Hardware model types for physical qubit targets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from quompass.core.types import HardwarePreset, InstructionSet


@dataclass
class QubitParams:
    """Physical qubit parameters for a hardware target.

    Sufficient to drive any physical estimation backend.
    Units: times in seconds (float), error rates dimensionless.
    """

    name: str
    instruction_set: InstructionSet
    one_qubit_gate_time: float
    two_qubit_gate_time: float
    one_qubit_measurement_time: float
    t_gate_time: float
    one_qubit_gate_error_rate: float
    two_qubit_gate_error_rate: float
    one_qubit_measurement_error_rate: float
    t_gate_error_rate: float
    idle_error_rate: Optional[float] = None
    # Majorana-specific
    two_qubit_joint_measurement_time: Optional[float] = None
    two_qubit_joint_measurement_error_rate: Optional[float] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        d = {
            "name": self.name,
            "instruction_set": self.instruction_set.value,
            "one_qubit_gate_time": self.one_qubit_gate_time,
            "two_qubit_gate_time": self.two_qubit_gate_time,
            "one_qubit_measurement_time": self.one_qubit_measurement_time,
            "t_gate_time": self.t_gate_time,
            "one_qubit_gate_error_rate": self.one_qubit_gate_error_rate,
            "two_qubit_gate_error_rate": self.two_qubit_gate_error_rate,
            "one_qubit_measurement_error_rate": self.one_qubit_measurement_error_rate,
            "t_gate_error_rate": self.t_gate_error_rate,
        }
        if self.idle_error_rate is not None:
            d["idle_error_rate"] = self.idle_error_rate
        if self.two_qubit_joint_measurement_time is not None:
            d["two_qubit_joint_measurement_time"] = self.two_qubit_joint_measurement_time
        if self.two_qubit_joint_measurement_error_rate is not None:
            d["two_qubit_joint_measurement_error_rate"] = self.two_qubit_joint_measurement_error_rate
        return d

    @classmethod
    def from_dict(cls, d: dict) -> QubitParams:
        """Construct from a dictionary (e.g. loaded from YAML)."""
        return cls(
            name=d["name"],
            instruction_set=InstructionSet(d["instruction_set"]),
            one_qubit_gate_time=d["one_qubit_gate_time"],
            two_qubit_gate_time=d["two_qubit_gate_time"],
            one_qubit_measurement_time=d["one_qubit_measurement_time"],
            t_gate_time=d["t_gate_time"],
            one_qubit_gate_error_rate=d["one_qubit_gate_error_rate"],
            two_qubit_gate_error_rate=d["two_qubit_gate_error_rate"],
            one_qubit_measurement_error_rate=d["one_qubit_measurement_error_rate"],
            t_gate_error_rate=d["t_gate_error_rate"],
            idle_error_rate=d.get("idle_error_rate"),
            two_qubit_joint_measurement_time=d.get("two_qubit_joint_measurement_time"),
            two_qubit_joint_measurement_error_rate=d.get("two_qubit_joint_measurement_error_rate"),
        )

    @property
    def worst_case_clifford_error(self) -> float:
        """p = max(measurement, 1q gate, 2q gate) per Azure QRE convention."""
        rates = [
            self.one_qubit_measurement_error_rate,
            self.one_qubit_gate_error_rate,
            self.two_qubit_gate_error_rate,
        ]
        if self.two_qubit_joint_measurement_error_rate is not None:
            rates.append(self.two_qubit_joint_measurement_error_rate)
        return max(rates)


@dataclass
class HardwareModel:
    """Complete hardware target specification."""

    name: str
    qubit_params: QubitParams
    description: str = ""

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "qubit_params": self.qubit_params.to_dict(),
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, d: dict) -> HardwareModel:
        """Construct from a dictionary (e.g. loaded from YAML)."""
        return cls(
            name=d["name"],
            qubit_params=QubitParams.from_dict(d["qubit_params"]),
            description=d.get("description", ""),
        )

    @classmethod
    def from_preset(cls, preset: HardwarePreset | str) -> HardwareModel:
        """Construct from a predefined hardware model."""
        if isinstance(preset, str):
            preset = HardwarePreset(preset)
        params = _PRESET_PARAMS[preset]
        return cls(
            name=params.name,
            qubit_params=params,
            description=_PRESET_DESCRIPTIONS[preset],
        )


# ---------------------------------------------------------------------------
# Predefined qubit parameter sets (from Azure QRE documentation)
# ---------------------------------------------------------------------------

_PRESET_PARAMS: dict[HardwarePreset, QubitParams] = {
    HardwarePreset.SUPERCONDUCTING_REALISTIC: QubitParams(
        name="gate_ns_e3",
        instruction_set=InstructionSet.GATE_BASED,
        one_qubit_gate_time=50e-9,
        two_qubit_gate_time=50e-9,
        one_qubit_measurement_time=100e-9,
        t_gate_time=50e-9,
        one_qubit_gate_error_rate=1e-3,
        two_qubit_gate_error_rate=1e-3,
        one_qubit_measurement_error_rate=1e-3,
        t_gate_error_rate=1e-3,
    ),
    HardwarePreset.SUPERCONDUCTING_OPTIMISTIC: QubitParams(
        name="gate_ns_e4",
        instruction_set=InstructionSet.GATE_BASED,
        one_qubit_gate_time=50e-9,
        two_qubit_gate_time=50e-9,
        one_qubit_measurement_time=100e-9,
        t_gate_time=50e-9,
        one_qubit_gate_error_rate=1e-4,
        two_qubit_gate_error_rate=1e-4,
        one_qubit_measurement_error_rate=1e-4,
        t_gate_error_rate=1e-4,
    ),
    HardwarePreset.TRAPPED_ION_REALISTIC: QubitParams(
        name="gate_us_e3",
        instruction_set=InstructionSet.GATE_BASED,
        one_qubit_gate_time=100e-6,
        two_qubit_gate_time=100e-6,
        one_qubit_measurement_time=100e-6,
        t_gate_time=100e-6,
        one_qubit_gate_error_rate=1e-3,
        two_qubit_gate_error_rate=1e-3,
        one_qubit_measurement_error_rate=1e-3,
        t_gate_error_rate=1e-6,
    ),
    HardwarePreset.TRAPPED_ION_OPTIMISTIC: QubitParams(
        name="gate_us_e4",
        instruction_set=InstructionSet.GATE_BASED,
        one_qubit_gate_time=100e-6,
        two_qubit_gate_time=100e-6,
        one_qubit_measurement_time=100e-6,
        t_gate_time=100e-6,
        one_qubit_gate_error_rate=1e-4,
        two_qubit_gate_error_rate=1e-4,
        one_qubit_measurement_error_rate=1e-4,
        t_gate_error_rate=1e-6,
    ),
    HardwarePreset.MAJORANA_REALISTIC: QubitParams(
        name="maj_ns_e4",
        instruction_set=InstructionSet.MAJORANA,
        one_qubit_gate_time=100e-9,
        two_qubit_gate_time=100e-9,
        one_qubit_measurement_time=100e-9,
        t_gate_time=100e-9,
        one_qubit_gate_error_rate=1e-4,
        two_qubit_gate_error_rate=1e-4,
        one_qubit_measurement_error_rate=1e-4,
        t_gate_error_rate=0.05,
        two_qubit_joint_measurement_time=100e-9,
        two_qubit_joint_measurement_error_rate=1e-4,
    ),
    HardwarePreset.MAJORANA_OPTIMISTIC: QubitParams(
        name="maj_ns_e6",
        instruction_set=InstructionSet.MAJORANA,
        one_qubit_gate_time=100e-9,
        two_qubit_gate_time=100e-9,
        one_qubit_measurement_time=100e-9,
        t_gate_time=100e-9,
        one_qubit_gate_error_rate=1e-6,
        two_qubit_gate_error_rate=1e-6,
        one_qubit_measurement_error_rate=1e-6,
        t_gate_error_rate=0.01,
        two_qubit_joint_measurement_time=100e-9,
        two_qubit_joint_measurement_error_rate=1e-6,
    ),
}

_PRESET_DESCRIPTIONS: dict[HardwarePreset, str] = {
    HardwarePreset.SUPERCONDUCTING_REALISTIC: "Superconducting, gate-based, ns timescale, 1e-3 error rate",
    HardwarePreset.SUPERCONDUCTING_OPTIMISTIC: "Superconducting, gate-based, ns timescale, 1e-4 error rate",
    HardwarePreset.TRAPPED_ION_REALISTIC: "Trapped ion, gate-based, us timescale, 1e-3 Clifford / 1e-6 T error",
    HardwarePreset.TRAPPED_ION_OPTIMISTIC: "Trapped ion, gate-based, us timescale, 1e-4 Clifford / 1e-6 T error",
    HardwarePreset.MAJORANA_REALISTIC: "Majorana/topological, 1e-4 Clifford, 5% T gate error",
    HardwarePreset.MAJORANA_OPTIMISTIC: "Majorana/topological, 1e-6 Clifford, 1% T gate error",
}
