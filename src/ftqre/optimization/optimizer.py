"""NSGA-II multi-objective optimizer for ftqre."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ftqre.exploration.space import (
    DesignPoint,
    ExplorationResult,
    ExplorationSpace,
    ParetoFront,
)
from ftqre.optimization.space import OptimizationSpace


@dataclass(frozen=True)
class OptimizationConfig:
    """Configuration snapshot for an optimization run."""

    generations: int = 50
    population_size: int = 100
    seed: Optional[int] = None


@dataclass
class OptimizationResult:
    """Result of a multi-objective optimization run.

    Wraps the pymoo result and provides convenience methods
    compatible with the existing ExplorationResult API.
    """

    space: OptimizationSpace
    all_points: list[DesignPoint]
    config: OptimizationConfig
    pymoo_result: Any = None
    n_evaluations: int = 0
    converged: bool = False

    @property
    def succeeded(self) -> list[DesignPoint]:
        """Design points where estimation succeeded."""
        return [p for p in self.all_points if p.succeeded]

    def pareto_front(
        self,
        objectives: dict[str, str] | None = None,
    ) -> ParetoFront:
        """Extract Pareto-optimal points.

        Parameters
        ----------
        objectives : dict, optional
            Override objectives. Defaults to space.objectives.
        """
        from ftqre.exploration.pareto import extract_pareto_front

        if objectives is None:
            objectives = dict(self.space.objectives)
        front_points = extract_pareto_front(self.succeeded, objectives)
        return ParetoFront(front_points, objectives)

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

    def print_table(self, console: Any = None) -> None:
        """Print Rich table of all design points."""
        self.to_exploration_result().print_table(console=console)

    def plot(
        self,
        x: str = "total_physical_qubits",
        y: str = "runtime_seconds",
        show_pareto: bool = True,
        save_path: str | None = None,
    ) -> Any:
        """Scatter plot with optional Pareto front overlay."""
        return self.to_exploration_result().plot(
            x=x, y=y, show_pareto=show_pareto, save_path=save_path
        )

    def to_exploration_result(self) -> ExplorationResult:
        """Convert to ExplorationResult for downstream analysis compatibility.

        Creates a synthetic ExplorationSpace from the optimization space
        so that existing visualization and analysis tools work.
        """
        # Build a synthetic ExplorationSpace
        synthetic_space = ExplorationSpace(
            algorithm=self.space.algorithm,
            hardware=list(self.space.hardware),
            qec=list(self.space.qec),
            error_budgets=[self.space.error_budget_range[0]],
        )
        return ExplorationResult(
            space=synthetic_space,
            points=self.all_points,
        )


def optimize(
    space: OptimizationSpace,
    *,
    generations: int = 50,
    population_size: int = 100,
    seed: int | None = None,
    verbose: bool = False,
    progress_callback: Callable[[int, int], None] | None = None,
) -> OptimizationResult:
    """Run NSGA-II multi-objective optimization.

    Uses pymoo's NSGA-II with mixed-variable operators to explore the
    design space with continuous error budget tuning and categorical
    hardware/QEC selection.

    Parameters
    ----------
    space : OptimizationSpace
        The search space definition.
    generations : int
        Number of NSGA-II generations.
    population_size : int
        Population size per generation.
    seed : int, optional
        Random seed for reproducibility.
    verbose : bool
        Print pymoo progress output.
    progress_callback : callable, optional
        Called with (current_gen, total_gens) after each generation.

    Returns
    -------
    OptimizationResult

    Raises
    ------
    ImportError
        If pymoo is not installed.
    """
    try:
        from pymoo.algorithms.moo.nsga2 import NSGA2
        from pymoo.core.mixed import (
            MixedVariableDuplicateElimination,
            MixedVariableMating,
            MixedVariableSampling,
        )
        from pymoo.optimize import minimize as pymoo_minimize
    except ImportError:
        raise ImportError(
            "pymoo is required for optimization. "
            "Install it with: pip install 'ftqre[optimize]' "
            "or: pip install 'pymoo>=0.6'"
        )

    from ftqre.optimization.problem import FTQREProblem

    config = OptimizationConfig(
        generations=generations,
        population_size=population_size,
        seed=seed,
    )

    # Build the pymoo problem
    ftqre_problem = FTQREProblem(space)
    problem = ftqre_problem.problem

    # Configure NSGA-II with mixed-variable operators
    algorithm = NSGA2(
        pop_size=population_size,
        sampling=MixedVariableSampling(),
        mating=MixedVariableMating(
            eliminate_duplicates=MixedVariableDuplicateElimination(),
        ),
        eliminate_duplicates=MixedVariableDuplicateElimination(),
    )

    # Set up callback (always provide one -- pymoo requires it to be callable)
    from ftqre.optimization.callback import ProgressCallback

    if progress_callback is not None:
        pc = ProgressCallback(generations, progress_callback)
        callback = pc.pymoo_callback
    else:
        pc = ProgressCallback(generations, lambda _g, _t: None)
        callback = pc.pymoo_callback

    # Run optimization
    res = pymoo_minimize(
        problem,
        algorithm,
        ("n_gen", generations),
        seed=seed,
        verbose=verbose,
        callback=callback,
    )

    # Extract design points from the final population
    points = _extract_points(res, space, ftqre_problem)

    return OptimizationResult(
        space=space,
        all_points=points,
        config=config,
        pymoo_result=res,
        n_evaluations=res.algorithm.evaluator.n_eval if res.algorithm else 0,
        converged=res.algorithm.has_next() is False if res.algorithm else False,
    )


def _extract_points(
    res: Any,
    space: OptimizationSpace,
    ftqre_problem: Any,
) -> list[DesignPoint]:
    """Extract DesignPoint list from the pymoo result population."""
    import ftqre as ftqre_mod
    from ftqre.core.error_budget import ErrorBudget
    from ftqre.optimization.problem import FTQREProblem

    points: list[DesignPoint] = []
    pop = res.pop if res.pop is not None else []

    for ind in pop:
        x = ind.X
        if x is None:
            continue

        error_budget_total = float(x["error_budget"])
        s1 = float(x["split1"])
        s2 = float(x["split2"])
        hw_idx = int(x["hw_idx"])
        qec_idx = int(x["qec_idx"])

        r_logical, r_distillation, r_rotation = FTQREProblem.split_budget(s1, s2)
        eb = ErrorBudget(
            total=error_budget_total,
            logical=error_budget_total * r_logical,
            distillation=error_budget_total * r_distillation,
            rotation=error_budget_total * r_rotation,
        )

        hw = space.hardware[hw_idx]
        qec = space.qec[qec_idx]
        hw_name = hw if isinstance(hw, str) else hw.name
        qec_name = qec if isinstance(qec, str) else qec.name

        try:
            result = ftqre_mod.estimate(
                space.algorithm,
                hardware=hw,
                qec=qec,
                error_budget=eb,
            )
            points.append(
                DesignPoint(
                    hardware_name=hw_name,
                    qec_name=qec_name,
                    error_budget=error_budget_total,
                    estimate=result,
                    error_budget_splits=(r_logical, r_distillation, r_rotation),
                )
            )
        except Exception as e:
            points.append(
                DesignPoint(
                    hardware_name=hw_name,
                    qec_name=qec_name,
                    error_budget=error_budget_total,
                    estimate=None,
                    error_message=str(e),
                    error_budget_splits=(r_logical, r_distillation, r_rotation),
                )
            )

    return points
