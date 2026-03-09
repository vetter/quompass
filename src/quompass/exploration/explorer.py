"""Grid search explorer for design space evaluation."""

from __future__ import annotations

import logging
from typing import Callable, Optional

import quompass
from quompass.core.algorithm import AlgorithmSpec
from quompass.exploration.space import DesignPoint, ExplorationResult, ExplorationSpace

logger = logging.getLogger(__name__)


def explore(
    space: ExplorationSpace,
    *,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> ExplorationResult:
    """Evaluate all combinations in the exploration space.

    Parameters
    ----------
    space : ExplorationSpace
        The parameter grid to explore.
    progress_callback : callable, optional
        Called with (completed_count, total_count) after each evaluation.

    Returns
    -------
    ExplorationResult
        Contains all design points (succeeded and failed).
    """
    points: list[DesignPoint] = []
    total = space.size
    completed = 0

    for hw_spec in space.hardware:
        hw_name = hw_spec if isinstance(hw_spec, str) else hw_spec.name
        for qec_spec in space.qec:
            qec_name = qec_spec if isinstance(qec_spec, str) else qec_spec.name
            for eb in space.error_budgets:
                point = _evaluate_single(
                    space.algorithm, hw_spec, qec_spec, eb, hw_name, qec_name
                )
                points.append(point)
                completed += 1
                if progress_callback is not None:
                    progress_callback(completed, total)

    return ExplorationResult(space=space, points=points)


def _evaluate_single(
    algorithm: AlgorithmSpec,
    hardware,
    qec,
    error_budget: float,
    hw_name: str,
    qec_name: str,
) -> DesignPoint:
    """Evaluate a single combination, catching errors gracefully."""
    try:
        result = quompass.estimate(
            algorithm,
            hardware=hardware,
            qec=qec,
            error_budget=error_budget,
        )
        return DesignPoint(
            hardware_name=hw_name,
            qec_name=qec_name,
            error_budget=error_budget,
            estimate=result,
        )
    except BaseException as e:
        logger.debug(
            "Estimation failed for hw=%s qec=%s eb=%s: %s",
            hw_name, qec_name, error_budget, e,
        )
        return DesignPoint(
            hardware_name=hw_name,
            qec_name=qec_name,
            error_budget=error_budget,
            estimate=None,
            error_message=str(e),
        )
