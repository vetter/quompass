"""Design space definition and result types for exploration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

from ftqre.core.algorithm import AlgorithmSpec
from ftqre.core.hardware import HardwareModel
from ftqre.core.qec import QECScheme
from ftqre.core.results import PhysicalEstimate


@dataclass(frozen=True)
class DesignPoint:
    """A single point in the design space with its estimation result.

    Captures the input parameters and the output estimate (or error).
    """

    hardware_name: str
    qec_name: str
    error_budget: float
    estimate: Optional[PhysicalEstimate]  # None if estimation failed
    error_message: Optional[str] = None

    @property
    def succeeded(self) -> bool:
        return self.estimate is not None

    @property
    def total_physical_qubits(self) -> float:
        if self.estimate is None:
            return float("inf")
        return float(self.estimate.total_physical_qubits)

    @property
    def runtime_seconds(self) -> float:
        if self.estimate is None:
            return float("inf")
        return self.estimate.runtime_seconds

    @property
    def space_time_volume(self) -> float:
        if self.estimate is None:
            return float("inf")
        return self.estimate.space_time_volume

    def metric(self, name: str) -> float:
        """Get a named metric from the underlying PhysicalEstimate.

        Supports: 'total_physical_qubits', 'runtime_seconds',
        'space_time_volume', 'rqops', 'code_distance'.
        Returns inf if the point failed.
        """
        if self.estimate is None:
            return float("inf")
        _METRICS: dict[str, Any] = {
            "total_physical_qubits": lambda e: float(e.total_physical_qubits),
            "runtime_seconds": lambda e: e.runtime_seconds,
            "space_time_volume": lambda e: e.space_time_volume,
            "rqops": lambda e: e.rqops,
            "code_distance": lambda e: float(e.logical_qubit.code_distance),
        }
        accessor = _METRICS.get(name)
        if accessor is None:
            raise ValueError(
                f"Unknown metric '{name}'. Available: {sorted(_METRICS.keys())}"
            )
        return accessor(self.estimate)

    def label(self) -> str:
        """Short human-readable label for this point."""
        return f"{self.hardware_name}/{self.qec_name}/eb={self.error_budget}"


@dataclass
class ExplorationSpace:
    """Defines the parameter grid to explore.

    The algorithm is fixed; hardware, QEC, and error budgets are swept.
    """

    algorithm: AlgorithmSpec
    hardware: Sequence[str | HardwareModel] = field(
        default_factory=lambda: ["gate_ns_e3"]
    )
    qec: Sequence[str | QECScheme] = field(
        default_factory=lambda: ["surface_code"]
    )
    error_budgets: Sequence[float] = field(
        default_factory=lambda: [0.001]
    )

    @property
    def size(self) -> int:
        """Total number of combinations in the grid."""
        return len(self.hardware) * len(self.qec) * len(self.error_budgets)


class ParetoFront:
    """A set of Pareto-optimal design points."""

    def __init__(
        self,
        points: list[DesignPoint],
        objectives: dict[str, str],
    ) -> None:
        self.points = points
        self.objectives = objectives

    def __len__(self) -> int:
        return len(self.points)

    def __iter__(self):
        return iter(self.points)

    def __getitem__(self, idx):
        return self.points[idx]

    def print_table(self, console=None) -> None:
        """Print Rich table of Pareto-optimal points."""
        from ftqre.viz.exploration import print_pareto_table

        print_pareto_table(self, console=console)

    def to_dicts(self) -> list[dict[str, Any]]:
        """Serialize Pareto front to list of dicts."""
        rows = []
        for pt in self.points:
            row = {
                "hardware": pt.hardware_name,
                "qec": pt.qec_name,
                "error_budget": pt.error_budget,
            }
            for obj_name in self.objectives:
                row[obj_name] = pt.metric(obj_name)
            rows.append(row)
        return rows


class ExplorationResult:
    """Result of a design space exploration.

    Contains all evaluated design points and provides methods for
    Pareto front extraction, sensitivity analysis, and visualization.
    """

    def __init__(
        self,
        space: ExplorationSpace,
        points: list[DesignPoint],
    ) -> None:
        self.space = space
        self.all_points = points

    @property
    def succeeded(self) -> list[DesignPoint]:
        return [p for p in self.all_points if p.succeeded]

    @property
    def failed(self) -> list[DesignPoint]:
        return [p for p in self.all_points if not p.succeeded]

    @property
    def num_succeeded(self) -> int:
        return sum(1 for p in self.all_points if p.succeeded)

    @property
    def num_failed(self) -> int:
        return sum(1 for p in self.all_points if not p.succeeded)

    def pareto_front(
        self,
        objectives: dict[str, str] | None = None,
    ) -> ParetoFront:
        """Extract Pareto-optimal points.

        Parameters
        ----------
        objectives : dict mapping metric_name -> "minimize"|"maximize"
            Default: {"total_physical_qubits": "minimize",
                       "runtime_seconds": "minimize"}
        """
        from ftqre.exploration.pareto import extract_pareto_front

        if objectives is None:
            objectives = {
                "total_physical_qubits": "minimize",
                "runtime_seconds": "minimize",
            }
        front_points = extract_pareto_front(self.succeeded, objectives)
        return ParetoFront(front_points, objectives)

    def sensitivity(
        self,
        baseline: dict[str, Any] | None = None,
        metric: str = "total_physical_qubits",
    ):
        """One-at-a-time sensitivity analysis."""
        from ftqre.exploration.sensitivity import compute_sensitivity

        return compute_sensitivity(self, baseline=baseline, metric=metric)

    def best(
        self,
        metric: str = "total_physical_qubits",
        minimize: bool = True,
    ) -> DesignPoint:
        """Return the best single design point by a given metric."""
        succeeded = self.succeeded
        if not succeeded:
            raise ValueError("No successful design points")
        key = lambda p: p.metric(metric)
        return min(succeeded, key=key) if minimize else max(succeeded, key=key)

    def print_table(self, console=None) -> None:
        """Print Rich table of all design points."""
        from ftqre.viz.exploration import print_exploration_table

        print_exploration_table(self, console=console)

    def plot(
        self,
        x: str = "total_physical_qubits",
        y: str = "runtime_seconds",
        show_pareto: bool = True,
        save_path: str | None = None,
    ) -> Any:
        """Scatter plot with optional Pareto front overlay."""
        from ftqre.viz.exploration import plot_exploration

        return plot_exploration(
            self, x=x, y=y, show_pareto=show_pareto, save_path=save_path
        )
