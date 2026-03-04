"""Backend discovery and registry via entry_points.

Discovers logical and physical estimator backends from:
1. Built-in backends (mock/analytical)
2. Installed plugins via ``importlib.metadata.entry_points``

Priority order for "auto" selection:
- Logical: qualtran > pyliqtr > mock
- Physical: azure > mqt > analytical
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quompass.backends.base import LogicalEstimator, PhysicalEstimator

logger = logging.getLogger(__name__)

# Priority order: first available wins for "auto" selection
_LOGICAL_PRIORITY = ["qualtran", "pyliqtr", "mock"]
_PHYSICAL_PRIORITY = ["azure", "mqt", "analytical"]


def discover_logical_estimators() -> dict[str, LogicalEstimator]:
    """Discover all available logical estimators."""
    from quompass.backends.mock import MockLogicalEstimator

    estimators: dict[str, LogicalEstimator] = {}

    # Built-in
    estimators["mock"] = MockLogicalEstimator()

    # Entry points
    try:
        from importlib.metadata import entry_points

        eps = entry_points(group="quompass.logical_estimators")
        for ep in eps:
            if ep.name not in estimators:
                try:
                    cls = ep.load()
                    instance = cls()
                    estimators[ep.name] = instance
                except Exception as e:
                    logger.debug("Failed to load logical estimator %s: %s", ep.name, e)
    except Exception:
        pass

    return estimators


def discover_physical_estimators() -> dict[str, PhysicalEstimator]:
    """Discover all available physical estimators."""
    from quompass.backends.mock import AnalyticalPhysicalEstimator

    estimators: dict[str, PhysicalEstimator] = {}

    # Built-in
    estimators["analytical"] = AnalyticalPhysicalEstimator()

    # Entry points
    try:
        from importlib.metadata import entry_points

        eps = entry_points(group="quompass.physical_estimators")
        for ep in eps:
            if ep.name not in estimators:
                try:
                    cls = ep.load()
                    instance = cls()
                    estimators[ep.name] = instance
                except Exception as e:
                    logger.debug("Failed to load physical estimator %s: %s", ep.name, e)
    except Exception:
        pass

    return estimators


def select_backends(
    logical_name: str = "auto",
    physical_name: str = "auto",
) -> tuple[LogicalEstimator, PhysicalEstimator]:
    """Select backends by name or auto-detect the best available.

    Parameters
    ----------
    logical_name : str
        Name of the logical estimator, or "auto" for best available.
    physical_name : str
        Name of the physical estimator, or "auto" for best available.

    Returns
    -------
    tuple[LogicalEstimator, PhysicalEstimator]
    """
    logical_backends = discover_logical_estimators()
    physical_backends = discover_physical_estimators()

    # Select logical
    if logical_name == "auto":
        le = _select_by_priority(logical_backends, _LOGICAL_PRIORITY, "logical")
    else:
        le = logical_backends.get(logical_name)
        if le is None:
            available = ", ".join(sorted(logical_backends.keys()))
            raise ValueError(
                f"Unknown logical backend: {logical_name!r}. Available: {available}"
            )

    # Select physical
    if physical_name == "auto":
        pe = _select_by_priority(physical_backends, _PHYSICAL_PRIORITY, "physical")
    else:
        pe = physical_backends.get(physical_name)
        if pe is None:
            available = ", ".join(sorted(physical_backends.keys()))
            raise ValueError(
                f"Unknown physical backend: {physical_name!r}. Available: {available}"
            )

    return le, pe


def _select_by_priority(
    backends: dict,
    priority: list[str],
    kind: str,
) -> LogicalEstimator | PhysicalEstimator:
    """Select the highest-priority available backend."""
    for name in priority:
        backend = backends.get(name)
        if backend is not None and backend.is_available():
            return backend
    # Fallback to any available
    for backend in backends.values():
        if backend.is_available():
            return backend
    raise RuntimeError(f"No available {kind} estimation backends found")
