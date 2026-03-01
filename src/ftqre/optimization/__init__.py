"""Multi-objective optimization for ftqre design space exploration."""

from ftqre.optimization.optimizer import OptimizationConfig, OptimizationResult, optimize
from ftqre.optimization.space import OptimizationSpace

__all__ = [
    "OptimizationSpace",
    "OptimizationResult",
    "OptimizationConfig",
    "optimize",
]
