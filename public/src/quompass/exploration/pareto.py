"""Pareto front extraction for multi-objective optimization."""

from __future__ import annotations

from quompass.exploration.space import DesignPoint


def extract_pareto_front(
    points: list[DesignPoint],
    objectives: dict[str, str],
) -> list[DesignPoint]:
    """Extract non-dominated (Pareto-optimal) points.

    Uses the naive O(n^2) dominance-check algorithm, which is adequate
    for the grid sizes we expect (tens to low hundreds of points).

    Parameters
    ----------
    points : list[DesignPoint]
        Only succeeded points should be passed in.
    objectives : dict
        Mapping of metric_name -> "minimize" | "maximize".

    Returns
    -------
    list[DesignPoint]
        The Pareto-optimal subset, sorted by the first objective.
    """
    if not points:
        return []

    obj_names = list(objectives.keys())
    obj_dirs = list(objectives.values())

    def _values(pt: DesignPoint) -> list[float]:
        """Extract objective values, sign-flipped for 'maximize'."""
        vals = []
        for name, direction in zip(obj_names, obj_dirs):
            v = pt.metric(name)
            if direction == "maximize":
                vals.append(-v)
            else:
                vals.append(v)
        return vals

    def _dominates(a_vals: list[float], b_vals: list[float]) -> bool:
        """Does A dominate B? (All values in 'minimize' direction.)"""
        at_least_as_good = all(av <= bv for av, bv in zip(a_vals, b_vals))
        strictly_better = any(av < bv for av, bv in zip(a_vals, b_vals))
        return at_least_as_good and strictly_better

    # Pre-compute objective values, filter out infinities
    point_vals = [(pt, _values(pt)) for pt in points]
    point_vals = [
        (pt, vals)
        for pt, vals in point_vals
        if all(v != float("inf") and v != float("-inf") for v in vals)
    ]

    # O(n^2) non-dominated sort
    pareto: list[DesignPoint] = []
    for i, (pt_i, vals_i) in enumerate(point_vals):
        dominated = False
        for j, (pt_j, vals_j) in enumerate(point_vals):
            if i != j and _dominates(vals_j, vals_i):
                dominated = True
                break
        if not dominated:
            pareto.append(pt_i)

    # Sort by first objective
    sort_key = obj_names[0]
    sort_reverse = objectives[sort_key] == "maximize"
    pareto.sort(key=lambda p: p.metric(sort_key), reverse=sort_reverse)

    return pareto
