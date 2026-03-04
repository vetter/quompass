"""pymoo Problem definition for quompass multi-objective optimization."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from quompass.optimization.space import OptimizationSpace

logger = logging.getLogger(__name__)


class FTQREProblem:
    """pymoo ElementwiseProblem for quompass resource estimation.

    Decision variables:
    - error_budget (Real): total error budget within configured range
    - split1 (Real [0,1]): budget split parameter 1
    - split2 (Real [0,1]): budget split parameter 2
    - hw_idx (Integer): index into hardware list
    - qec_idx (Integer): index into QEC list

    Split normalization: s1/(s1+s2+1), s2/(s1+s2+1), 1/(s1+s2+1)
    maps 2 unconstrained vars to 3 non-negative ratios summing to 1.
    """

    def __init__(self, space: OptimizationSpace) -> None:
        from pymoo.core.problem import ElementwiseProblem
        from pymoo.core.variable import Integer, Real

        self._space = space
        self._objective_names = list(space.objectives.keys())
        self._objective_directions = [
            1 if d == "minimize" else -1
            for d in space.objectives.values()
        ]

        n_hw = len(space.hardware)
        n_qec = len(space.qec)

        variables = {
            "error_budget": Real(
                bounds=(space.error_budget_range[0], space.error_budget_range[1])
            ),
            "split1": Real(bounds=(0.0, 1.0)),
            "split2": Real(bounds=(0.0, 1.0)),
            "hw_idx": Integer(bounds=(0, max(n_hw - 1, 0))),
            "qec_idx": Integer(bounds=(0, max(n_qec - 1, 0))),
        }

        self._n_obj = len(self._objective_names)

        # Capture self for use in the inner class
        outer = self

        class _Problem(ElementwiseProblem):
            def _evaluate(self_inner, x, out, *args, **kwargs):
                outer._evaluate(x, out, *args, **kwargs)

        self._problem = _Problem(
            vars=variables,
            n_obj=self._n_obj,
        )

    @property
    def problem(self) -> Any:
        """Return the pymoo Problem instance."""
        return self._problem

    @property
    def n_var(self) -> int:
        """Number of decision variables."""
        return 5

    @property
    def n_obj(self) -> int:
        """Number of objectives."""
        return self._n_obj

    @staticmethod
    def split_budget(s1: float, s2: float) -> tuple[float, float, float]:
        """Normalize split variables to 3 ratios summing to 1.

        Parameters
        ----------
        s1, s2 : float
            Unconstrained split parameters in [0, 1].

        Returns
        -------
        tuple[float, float, float]
            (r_logical, r_distillation, r_rotation) ratios.
        """
        denom = s1 + s2 + 1.0
        return (s1 / denom, s2 / denom, 1.0 / denom)

    def _evaluate(self, x: dict, out: dict, *args: Any, **kwargs: Any) -> None:
        """Evaluate a single candidate solution."""
        import quompass as quompass_mod
        from quompass.core.error_budget import ErrorBudget

        error_budget_total = float(x["error_budget"])
        s1 = float(x["split1"])
        s2 = float(x["split2"])
        hw_idx = int(x["hw_idx"])
        qec_idx = int(x["qec_idx"])

        # Compute budget splits
        r_logical, r_distillation, r_rotation = self.split_budget(s1, s2)
        eb = ErrorBudget(
            total=error_budget_total,
            logical=error_budget_total * r_logical,
            distillation=error_budget_total * r_distillation,
            rotation=error_budget_total * r_rotation,
        )

        hw = self._space.hardware[hw_idx]
        qec = self._space.qec[qec_idx]

        try:
            result = quompass_mod.estimate(
                self._space.algorithm,
                hardware=hw,
                qec=qec,
                error_budget=eb,
            )

            obj_values = []
            for name, direction in zip(
                self._objective_names, self._objective_directions
            ):
                from quompass.exploration.space import DesignPoint

                # Use DesignPoint.metric for consistent access
                hw_name = hw if isinstance(hw, str) else hw.name
                qec_name = qec if isinstance(qec, str) else qec.name
                pt = DesignPoint(
                    hardware_name=hw_name,
                    qec_name=qec_name,
                    error_budget=error_budget_total,
                    estimate=result,
                    error_budget_splits=(r_logical, r_distillation, r_rotation),
                )
                val = pt.metric(name)
                obj_values.append(val * direction)

            out["F"] = np.array(obj_values)

        except Exception as e:
            logger.debug("Evaluation failed: %s", e)
            out["F"] = np.full(self._n_obj, 1e30)
