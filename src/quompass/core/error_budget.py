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

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "total": self.total,
            "logical": self.logical,
            "distillation": self.distillation,
            "rotation": self.rotation,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ErrorBudgetBreakdown:
        """Construct from a dictionary."""
        return cls(
            total=d["total"],
            logical=d["logical"],
            distillation=d["distillation"],
            rotation=d["rotation"],
        )


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

    def __post_init__(self) -> None:
        if not (0 < self.total < 1):
            raise ValueError(f"total error budget must be in (0, 1), got {self.total}")
        for name in ("logical", "distillation", "rotation"):
            val = getattr(self, name)
            if val is not None and val < 0:
                raise ValueError(f"{name} must be non-negative, got {val}")

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        d: dict = {"total": self.total}
        if self.logical is not None:
            d["logical"] = self.logical
        if self.distillation is not None:
            d["distillation"] = self.distillation
        if self.rotation is not None:
            d["rotation"] = self.rotation
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ErrorBudget:
        """Construct from a dictionary."""
        return cls(
            total=d.get("total", 0.001),
            logical=d.get("logical"),
            distillation=d.get("distillation"),
            rotation=d.get("rotation"),
        )

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
