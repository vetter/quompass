"""Error budget configuration and breakdown."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ErrorBudgetBreakdown:
    """How the total error budget is distributed across components."""

    total: float
    logical: float
    distillation: float
    rotation: float


@dataclass
class ErrorBudget:
    """Configurable error budget with default uniform distribution.

    The total error budget epsilon is split across three components:
    - logical: errors in logical qubit operations
    - distillation: errors in T state distillation
    - rotation: errors in rotation gate synthesis

    Default split is uniform (epsilon/3 each), or epsilon/2 for logical
    and distillation when no rotations are present.
    """

    total: float = 0.001
    logical: Optional[float] = None
    distillation: Optional[float] = None
    rotation: Optional[float] = None

    def resolve(self, has_rotations: bool = True) -> ErrorBudgetBreakdown:
        """Compute the actual split, defaulting to uniform."""
        if self.logical is not None:
            return ErrorBudgetBreakdown(
                total=self.total,
                logical=self.logical,
                distillation=self.distillation or 0.0,
                rotation=self.rotation or 0.0,
            )
        if has_rotations:
            third = self.total / 3
            return ErrorBudgetBreakdown(self.total, third, third, third)
        else:
            half = self.total / 2
            return ErrorBudgetBreakdown(self.total, half, half, 0.0)
