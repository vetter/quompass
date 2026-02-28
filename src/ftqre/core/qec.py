"""Quantum Error Correction scheme abstractions.

This is the critical differentiator of ftqre. The design must support
surface code, Floquet code, color code, qLDPC, and unknown future codes
through a single abstract interface.
"""

from __future__ import annotations

import ast
import math
import operator
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ftqre.core.hardware import QubitParams


class QECScheme(ABC):
    """Abstract base for quantum error correction schemes.

    Each concrete scheme must provide formulas for:
    1. Logical error rate as a function of code distance and physical error rate
    2. Physical qubits per logical qubit as a function of code distance
    3. Logical cycle time as a function of code distance and physical gate times

    The resource estimator uses these to find the minimum code distance
    that achieves a target logical error rate.
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def error_correction_threshold(self) -> float:
        """Physical error rate threshold p* below which QEC works."""
        ...

    @property
    @abstractmethod
    def crossing_prefactor(self) -> float:
        """Crossing prefactor 'a' in the logical error rate formula."""
        ...

    @abstractmethod
    def logical_error_rate(self, code_distance: int, physical_error_rate: float) -> float:
        """Compute logical error rate for given code distance and physical error rate.

        Standard model: P = a * d^k * (p/p*)^((d+1)/2)
        where a = crossing_prefactor, p* = error_correction_threshold,
        k = distance_coefficient_power (default 0).
        """
        ...

    @abstractmethod
    def physical_qubits_per_logical(self, code_distance: int) -> int:
        """Number of physical qubits to encode one logical qubit."""
        ...

    @abstractmethod
    def logical_cycle_time(self, code_distance: int, qubit_params: QubitParams) -> float:
        """Time (seconds) for one logical cycle at the given code distance."""
        ...

    def min_code_distance(
        self,
        target_error_rate: float,
        physical_error_rate: float,
        max_distance: int = 51,
    ) -> int:
        """Find minimum odd code distance achieving target logical error rate.

        This default implementation does a linear search over odd distances.
        Subclasses may override with analytical solutions.
        """
        if physical_error_rate >= self.error_correction_threshold:
            raise ValueError(
                f"Physical error rate {physical_error_rate:.2e} exceeds "
                f"QEC threshold {self.error_correction_threshold:.2e} for {self.name}"
            )
        for d in range(3, max_distance + 1, 2):
            if self.logical_error_rate(d, physical_error_rate) <= target_error_rate:
                return d
        raise ValueError(
            f"Cannot achieve target error rate {target_error_rate:.2e} "
            f"with code distance up to {max_distance}"
        )


class SurfaceCode(QECScheme):
    """Rotated planar surface code (Gidney-Fowler model).

    Physical qubits per logical qubit: 2 * d^2
    Logical cycle time: (4 * t_2q + 2 * t_meas) * d
    Threshold: 1%
    Crossing prefactor: 0.03
    """

    @property
    def name(self) -> str:
        return "surface_code"

    @property
    def error_correction_threshold(self) -> float:
        return 0.01

    @property
    def crossing_prefactor(self) -> float:
        return 0.03

    def logical_error_rate(self, code_distance: int, physical_error_rate: float) -> float:
        a = self.crossing_prefactor
        p_star = self.error_correction_threshold
        return a * (physical_error_rate / p_star) ** ((code_distance + 1) / 2)

    def physical_qubits_per_logical(self, code_distance: int) -> int:
        return 2 * code_distance * code_distance

    def logical_cycle_time(self, code_distance: int, qubit_params: QubitParams) -> float:
        return (
            4 * qubit_params.two_qubit_gate_time
            + 2 * qubit_params.one_qubit_measurement_time
        ) * code_distance


class FloquetCode(QECScheme):
    """Floquet code (Majorana qubits).

    Physical qubits per logical qubit: 4*d^2 + 8*(d-1)
    Logical cycle time: 3 * t_meas * d
    Threshold: 1%
    Crossing prefactor: 0.07
    """

    @property
    def name(self) -> str:
        return "floquet_code"

    @property
    def error_correction_threshold(self) -> float:
        return 0.01

    @property
    def crossing_prefactor(self) -> float:
        return 0.07

    def logical_error_rate(self, code_distance: int, physical_error_rate: float) -> float:
        a = self.crossing_prefactor
        p_star = self.error_correction_threshold
        return a * (physical_error_rate / p_star) ** ((code_distance + 1) / 2)

    def physical_qubits_per_logical(self, code_distance: int) -> int:
        return 4 * code_distance * code_distance + 8 * (code_distance - 1)

    def logical_cycle_time(self, code_distance: int, qubit_params: QubitParams) -> float:
        return 3 * qubit_params.one_qubit_measurement_time * code_distance


# ---------------------------------------------------------------------------
# Safe formula evaluation
# ---------------------------------------------------------------------------

# Allowed operators in formula expressions
_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

# Allowed function names in formulas
_SAFE_FUNCS: dict[str, Any] = {
    "round": round,
    "ceil": math.ceil,
    "floor": math.floor,
    "sqrt": math.sqrt,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "max": max,
    "min": min,
    "abs": abs,
}


def _safe_eval(expr: str, variables: dict[str, float]) -> float:
    """Evaluate a formula string safely using AST walking.

    Only arithmetic operators and whitelisted math functions are allowed.
    No access to builtins, imports, attribute lookups, or arbitrary callables.

    Parameters
    ----------
    expr : str
        Formula string, e.g. ``"2 * d * d"`` or ``"ceil(4.5 * d * d)"``.
    variables : dict
        Variable names and their float values (e.g. ``{"d": 5}``).

    Returns
    -------
    float
        Result of evaluating the formula.

    Raises
    ------
    ValueError
        If the expression contains disallowed constructs.
    """
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Invalid formula syntax: {expr!r}") from e

    def _eval_node(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise ValueError(f"Disallowed constant type: {type(node.value).__name__}")
        if isinstance(node, ast.Name):
            if node.id in variables:
                return variables[node.id]
            raise ValueError(f"Unknown variable: {node.id!r}")
        if isinstance(node, ast.BinOp):
            op_func = _SAFE_OPS.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Disallowed operator: {type(node.op).__name__}")
            return op_func(_eval_node(node.left), _eval_node(node.right))
        if isinstance(node, ast.UnaryOp):
            op_func = _SAFE_OPS.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Disallowed unary operator: {type(node.op).__name__}")
            return op_func(_eval_node(node.operand))
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Only simple function calls allowed (no methods/attributes)")
            func = _SAFE_FUNCS.get(node.func.id)
            if func is None:
                raise ValueError(f"Disallowed function: {node.func.id!r}")
            args = [_eval_node(a) for a in node.args]
            return float(func(*args))
        raise ValueError(f"Disallowed expression node: {type(node).__name__}")

    return _eval_node(tree)


# ---------------------------------------------------------------------------
# FormulaQEC -- user-defined QEC codes via formula strings
# ---------------------------------------------------------------------------


class FormulaQEC(QECScheme):
    """User-defined QEC scheme via formula strings.

    Enables researchers to plug in new codes (color code, qLDPC, gross code)
    without writing Python. Formulas use AST-safe evaluation -- no ``eval()``.

    Formula variables for ``qubits_formula``:
        - ``d``: code distance

    Formula variables for ``cycle_time_formula``:
        - ``d``: code distance
        - ``t_1q``: one-qubit gate time (seconds)
        - ``t_2q``: two-qubit gate time (seconds)
        - ``t_meas``: measurement time (seconds)
        - ``t_jm``: two-qubit joint measurement time (seconds, 0 if not applicable)

    Examples
    --------
    >>> color = FormulaQEC(
    ...     name="color_code_6.6.6",
    ...     threshold=0.0077,
    ...     prefactor=0.1,
    ...     qubits_formula="ceil(4.5 * d * d)",
    ...     cycle_time_formula="10 * t_2q * d",
    ... )
    """

    def __init__(
        self,
        name: str,
        threshold: float,
        prefactor: float,
        qubits_formula: str,
        cycle_time_formula: str,
        distance_coefficient_power: float = 0.0,
    ) -> None:
        self._name = name
        self._threshold = threshold
        self._prefactor = prefactor
        self._qubits_formula = qubits_formula
        self._cycle_time_formula = cycle_time_formula
        self._distance_coefficient_power = distance_coefficient_power
        # Validate formulas at construction time (catch syntax errors early)
        _safe_eval(qubits_formula, {"d": 3})
        _safe_eval(cycle_time_formula, {"d": 3, "t_1q": 1, "t_2q": 1, "t_meas": 1, "t_jm": 0})

    @property
    def name(self) -> str:
        return self._name

    @property
    def error_correction_threshold(self) -> float:
        return self._threshold

    @property
    def crossing_prefactor(self) -> float:
        return self._prefactor

    @property
    def qubits_formula(self) -> str:
        return self._qubits_formula

    @property
    def cycle_time_formula(self) -> str:
        return self._cycle_time_formula

    @property
    def distance_coefficient_power(self) -> float:
        return self._distance_coefficient_power

    def logical_error_rate(self, code_distance: int, physical_error_rate: float) -> float:
        a = self._prefactor
        p_star = self._threshold
        k = self._distance_coefficient_power
        ratio = physical_error_rate / p_star
        return a * (code_distance ** k) * (ratio ** ((code_distance + 1) / 2))

    def physical_qubits_per_logical(self, code_distance: int) -> int:
        result = _safe_eval(self._qubits_formula, {"d": float(code_distance)})
        return int(math.ceil(result))

    def logical_cycle_time(self, code_distance: int, qubit_params: QubitParams) -> float:
        t_jm = qubit_params.two_qubit_joint_measurement_time or 0.0
        variables = {
            "d": float(code_distance),
            "t_1q": qubit_params.one_qubit_gate_time,
            "t_2q": qubit_params.two_qubit_gate_time,
            "t_meas": qubit_params.one_qubit_measurement_time,
            "t_jm": t_jm,
        }
        return _safe_eval(self._cycle_time_formula, variables)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary (e.g. for YAML persistence)."""
        return {
            "name": self._name,
            "threshold": self._threshold,
            "prefactor": self._prefactor,
            "qubits_formula": self._qubits_formula,
            "cycle_time_formula": self._cycle_time_formula,
            "distance_coefficient_power": self._distance_coefficient_power,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> FormulaQEC:
        """Construct from a dictionary (e.g. loaded from YAML)."""
        return cls(
            name=d["name"],
            threshold=d["threshold"],
            prefactor=d["prefactor"],
            qubits_formula=d["qubits_formula"],
            cycle_time_formula=d["cycle_time_formula"],
            distance_coefficient_power=d.get("distance_coefficient_power", 0.0),
        )


def color_code() -> FormulaQEC:
    """Built-in color code (6.6.6 triangular lattice) as a FormulaQEC instance.

    Based on Bombin & Martin-Delgado (2006), Landahl et al. (2011).
    Threshold ~0.77%, physical qubits ~4.5*d^2, cycle time ~10 two-qubit gate
    rounds per distance.
    """
    return FormulaQEC(
        name="color_code",
        threshold=0.0077,
        prefactor=0.1,
        qubits_formula="ceil(4.5 * d * d)",
        cycle_time_formula="10 * t_2q * d",
    )


# Registry of built-in QEC schemes
_BUILTIN_SCHEMES: dict[str, type[QECScheme] | QECScheme] = {
    "surface_code": SurfaceCode,
    "floquet_code": FloquetCode,
    "color_code": color_code(),
}


def get_qec_scheme(name: str) -> QECScheme:
    """Look up a QEC scheme by name.

    Accepts both class-based schemes (SurfaceCode, FloquetCode) and
    instance-based schemes (FormulaQEC instances like color_code).
    Also accepts a QECScheme instance directly (returned as-is).
    """
    entry = _BUILTIN_SCHEMES.get(name)
    if entry is None:
        available = ", ".join(sorted(_BUILTIN_SCHEMES.keys()))
        raise ValueError(f"Unknown QEC scheme '{name}'. Available: {available}")
    if isinstance(entry, QECScheme):
        return entry
    return entry()
