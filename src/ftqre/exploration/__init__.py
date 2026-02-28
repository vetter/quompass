"""Design space exploration for ftqre."""

from ftqre.exploration.explorer import explore
from ftqre.exploration.pareto import extract_pareto_front
from ftqre.exploration.sensitivity import SensitivityResult, compute_sensitivity
from ftqre.exploration.space import (
    DesignPoint,
    ExplorationResult,
    ExplorationSpace,
    ParetoFront,
)

__all__ = [
    "ExplorationSpace",
    "DesignPoint",
    "ExplorationResult",
    "ParetoFront",
    "explore",
    "extract_pareto_front",
    "compute_sensitivity",
    "SensitivityResult",
]
