"""One-at-a-time (OAT) sensitivity analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from ftqre.exploration.space import DesignPoint, ExplorationResult


@dataclass(frozen=True)
class SensitivityEntry:
    """One data point in a sensitivity sweep."""

    param_value: Any
    metric_value: float
    pct_change: float


@dataclass
class SensitivityResult:
    """Result of OAT sensitivity analysis."""

    metric: str
    baseline_value: float
    baseline_params: dict[str, Any]
    dimensions: dict[str, list[SensitivityEntry]]

    def most_sensitive_dimension(self) -> str:
        """Return the dimension with the largest max absolute pct_change."""
        max_sens: dict[str, float] = {}
        for dim_name, entries in self.dimensions.items():
            if entries:
                max_sens[dim_name] = max(abs(e.pct_change) for e in entries)
            else:
                max_sens[dim_name] = 0.0
        return max(max_sens, key=max_sens.get)  # type: ignore[arg-type]

    def print_table(self, console=None) -> None:
        from ftqre.viz.exploration import print_sensitivity_table

        print_sensitivity_table(self, console=console)

    def plot(self, save_path: str | None = None) -> Any:
        from ftqre.viz.exploration import plot_sensitivity

        return plot_sensitivity(self, save_path=save_path)


def compute_sensitivity(
    result: ExplorationResult,
    *,
    baseline: Optional[dict[str, Any]] = None,
    metric: str = "total_physical_qubits",
) -> SensitivityResult:
    """Compute OAT sensitivity from an ExplorationResult.

    For each dimension (hardware, qec, error_budget), vary that dimension
    while holding the other two at baseline values.
    """
    space = result.space

    if baseline is None:
        hw0 = space.hardware[0]
        qec0 = space.qec[0]
        eb0 = space.error_budgets[0]
        baseline = {
            "hardware": hw0 if isinstance(hw0, str) else hw0.name,
            "qec": qec0 if isinstance(qec0, str) else qec0.name,
            "error_budget": eb0,
        }

    baseline_point = _find_point(
        result.succeeded,
        baseline["hardware"],
        baseline["qec"],
        baseline["error_budget"],
    )
    if baseline_point is None:
        raise ValueError(
            f"Baseline point not found in results: {baseline}. "
            f"It may have failed estimation."
        )

    baseline_val = baseline_point.metric(metric)
    dimensions: dict[str, list[SensitivityEntry]] = {}

    # Sweep hardware
    hw_entries = []
    for hw_spec in space.hardware:
        hw_name = hw_spec if isinstance(hw_spec, str) else hw_spec.name
        pt = _find_point(
            result.succeeded, hw_name, baseline["qec"], baseline["error_budget"]
        )
        if pt is not None:
            val = pt.metric(metric)
            pct = _pct_change(baseline_val, val)
            hw_entries.append(SensitivityEntry(hw_name, val, pct))
    dimensions["hardware"] = hw_entries

    # Sweep QEC
    qec_entries = []
    for qec_spec in space.qec:
        qec_name = qec_spec if isinstance(qec_spec, str) else qec_spec.name
        pt = _find_point(
            result.succeeded, baseline["hardware"], qec_name, baseline["error_budget"]
        )
        if pt is not None:
            val = pt.metric(metric)
            pct = _pct_change(baseline_val, val)
            qec_entries.append(SensitivityEntry(qec_name, val, pct))
    dimensions["qec"] = qec_entries

    # Sweep error_budget
    eb_entries = []
    for eb in space.error_budgets:
        pt = _find_point(
            result.succeeded, baseline["hardware"], baseline["qec"], eb
        )
        if pt is not None:
            val = pt.metric(metric)
            pct = _pct_change(baseline_val, val)
            eb_entries.append(SensitivityEntry(eb, val, pct))
    dimensions["error_budget"] = eb_entries

    return SensitivityResult(
        metric=metric,
        baseline_value=baseline_val,
        baseline_params=baseline,
        dimensions=dimensions,
    )


def _find_point(
    points: list[DesignPoint],
    hw_name: str,
    qec_name: str,
    error_budget: float,
) -> Optional[DesignPoint]:
    """Find a specific design point by its parameter values."""
    for pt in points:
        if (
            pt.hardware_name == hw_name
            and pt.qec_name == qec_name
            and abs(pt.error_budget - error_budget) < 1e-15
        ):
            return pt
    return None


def _pct_change(baseline: float, value: float) -> float:
    """Percentage change from baseline."""
    if baseline == 0:
        return 0.0 if value == 0 else float("inf")
    return ((value - baseline) / abs(baseline)) * 100.0
