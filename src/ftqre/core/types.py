"""Core enumerations and type aliases for ftqre."""

from __future__ import annotations

from enum import Enum


class InstructionSet(str, Enum):
    """Physical qubit instruction set type."""

    GATE_BASED = "gate_based"
    MAJORANA = "majorana"


class HardwarePreset(str, Enum):
    """Predefined hardware targets (mirrors Azure QRE presets)."""

    SUPERCONDUCTING_OPTIMISTIC = "gate_ns_e4"
    SUPERCONDUCTING_REALISTIC = "gate_ns_e3"
    TRAPPED_ION_OPTIMISTIC = "gate_us_e4"
    TRAPPED_ION_REALISTIC = "gate_us_e3"
    MAJORANA_OPTIMISTIC = "maj_ns_e6"
    MAJORANA_REALISTIC = "maj_ns_e4"
