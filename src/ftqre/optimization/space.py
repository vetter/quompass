"""Optimization space definition for multi-objective optimization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from ftqre.core.algorithm import AlgorithmSpec
from ftqre.core.hardware import HardwareModel
from ftqre.core.qec import QECScheme

_DEFAULT_OBJECTIVES: dict[str, str] = {
    "total_physical_qubits": "minimize",
    "runtime_seconds": "minimize",
}


@dataclass
class OptimizationSpace:
    """Defines the optimization search space.

    Unlike ExplorationSpace (which sweeps a discrete grid), this defines
    continuous ranges and categorical choices for NSGA-II optimization.

    Parameters
    ----------
    algorithm : AlgorithmSpec
        The algorithm to optimize for.
    hardware : Sequence[str | HardwareModel]
        Hardware targets (categorical choices).
    qec : Sequence[str | QECScheme]
        QEC schemes (categorical choices).
    error_budget_range : tuple[float, float]
        Continuous range for total error budget.
    objectives : dict[str, str]
        Mapping of metric name to "minimize" or "maximize".
    """

    algorithm: AlgorithmSpec
    hardware: Sequence[str | HardwareModel] = field(
        default_factory=lambda: ["gate_ns_e3"]
    )
    qec: Sequence[str | QECScheme] = field(
        default_factory=lambda: ["surface_code"]
    )
    error_budget_range: tuple[float, float] = (1e-4, 0.1)
    objectives: dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_OBJECTIVES))

    def __post_init__(self) -> None:
        """Validate the optimization space."""
        lo, hi = self.error_budget_range
        if lo >= hi:
            raise ValueError(
                f"error_budget_range lower bound ({lo}) must be less than "
                f"upper bound ({hi})"
            )
        if lo <= 0:
            raise ValueError(
                f"error_budget_range lower bound ({lo}) must be positive"
            )
        if not self.hardware:
            raise ValueError("hardware list must not be empty")
        if not self.qec:
            raise ValueError("qec list must not be empty")
        for direction in self.objectives.values():
            if direction not in ("minimize", "maximize"):
                raise ValueError(
                    f"Objective direction must be 'minimize' or 'maximize', "
                    f"got '{direction}'"
                )
