"""Design space exploration for quompass."""

from quompass.exploration.explorer import explore
from quompass.exploration.pareto import extract_pareto_front
from quompass.exploration.sensitivity import SensitivityResult, compute_sensitivity
from quompass.exploration.space import (
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
