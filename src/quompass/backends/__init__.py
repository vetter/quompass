"""Estimation backends and plugin registry."""

from quompass.backends.base import LogicalEstimator, PhysicalEstimator
from quompass.backends.registry import (
    discover_logical_estimators,
    discover_physical_estimators,
    select_backends,
)

__all__ = [
    "LogicalEstimator",
    "PhysicalEstimator",
    "discover_logical_estimators",
    "discover_physical_estimators",
    "select_backends",
]
