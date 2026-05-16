"""Core domain types for Quompass resource estimation."""

from quompass.core.algorithm import AlgorithmSpec, LogicalCounts
from quompass.core.error_budget import ErrorBudget, ErrorBudgetBreakdown
from quompass.core.hardware import HardwareModel, QubitParams
from quompass.core.qec import (
    FloquetCode,
    FormulaQEC,
    QECScheme,
    SurfaceCode,
    color_code,
    get_qec_scheme,
)
from quompass.core.results import (
    LogicalQubitEstimate,
    PhysicalEstimate,
    TFactoryEstimate,
)
from quompass.core.types import HardwarePreset, InstructionSet

__all__ = [
    "AlgorithmSpec",
    "LogicalCounts",
    "ErrorBudget",
    "ErrorBudgetBreakdown",
    "HardwareModel",
    "HardwarePreset",
    "InstructionSet",
    "QubitParams",
    "QECScheme",
    "SurfaceCode",
    "FloquetCode",
    "FormulaQEC",
    "color_code",
    "get_qec_scheme",
    "LogicalQubitEstimate",
    "PhysicalEstimate",
    "TFactoryEstimate",
]
