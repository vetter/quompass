"""Hamiltonian simulation algorithm template.

Resource models for multiple simulation methods:
- Trotter-Suzuki product formulas
- Quantum Signal Processing (QSP/QSVT)
- Qubitization (Linear Combination of Unitaries)

References:
- Lloyd (1996): universal quantum simulation
- Berry et al. (2015): simulating Hamiltonians with near-optimal dependence
- Low & Chuang (2017): optimal Hamiltonian simulation by quantum signal processing
- Childs & Wiebe (2012): Hamiltonian simulation using linear combinations of unitary operations
"""

from __future__ import annotations

import math
from typing import Any

from ftqre.core.algorithm import AlgorithmSpec, LogicalCounts
from ftqre.templates.base import AlgorithmTemplate

_VALID_METHODS = ("trotter", "qsp", "qubitization")


class HamiltonianSimTemplate(AlgorithmTemplate):
    """Hamiltonian simulation template with multiple product formula and
    post-Trotter methods."""

    @property
    def name(self) -> str:
        return "hamiltonian_sim"

    @property
    def family(self) -> str:
        return "simulation"

    @property
    def description(self) -> str:
        return "Hamiltonian simulation (Trotter, QSP, or qubitization)"

    def generate(self, **params: Any) -> AlgorithmSpec:
        num_qubits = int(params.get("num_qubits", 50))
        num_terms = int(params.get("num_terms", 100))
        evolution_time = float(params.get("evolution_time", 1.0))
        precision = float(params.get("precision", 1e-3))
        method = str(params.get("method", "trotter"))

        if method not in _VALID_METHODS:
            raise ValueError(
                f"Unknown method '{method}'. Available: {', '.join(_VALID_METHODS)}"
            )

        if method == "trotter":
            return self._trotter(num_qubits, num_terms, evolution_time, precision)
        elif method == "qsp":
            return self._qsp(num_qubits, num_terms, evolution_time, precision)
        else:
            return self._qubitization(num_qubits, num_terms, evolution_time, precision)

    def _trotter(
        self, n: int, L: int, t: float, eps: float
    ) -> AlgorithmSpec:
        """Second-order Trotter-Suzuki decomposition.

        Gate count ~ O(L^2 * n * t^2 / epsilon) for 2nd order formula.
        Each Trotter step has ~L CNOT+rotation sequences.
        """
        # Number of Trotter steps for 2nd order: r ~ (L*t)^{3/2} / sqrt(eps)
        r = max(1, int(math.ceil((L * t) ** 1.5 / math.sqrt(eps))))
        # Each step: L terms, each requiring ~2n CNOT + rotation gates
        gates_per_step = L * 2 * n
        total_gates = r * gates_per_step

        # T-count: rotations require T gates via synthesis (~ log(1/eps) per rotation)
        rotation_synthesis_t = max(1, int(math.ceil(math.log2(1.0 / eps))))
        t_count = r * L * rotation_synthesis_t
        rotation_count = r * L
        rotation_depth = r * L

        # CCZ from multi-controlled rotations
        ccz_count = r * max(1, n // 4)

        return AlgorithmSpec(
            name=f"Hamiltonian sim (n={n}, Trotter, t={t})",
            logical_counts=LogicalCounts(
                num_qubits=n,
                t_count=t_count,
                ccz_count=ccz_count,
                rotation_count=rotation_count,
                rotation_depth=rotation_depth,
                clifford_count=total_gates,
            ),
            description=(
                f"Trotter-Suzuki 2nd order simulation of {L}-term Hamiltonian "
                f"on {n} qubits for time {t}, precision {eps}."
            ),
            algorithm_family="simulation",
            problem_parameters={
                "num_qubits": n,
                "num_terms": L,
                "evolution_time": t,
                "precision": eps,
                "method": "trotter",
            },
            source="template:hamiltonian_sim",
        )

    def _qsp(
        self, n: int, L: int, t: float, eps: float
    ) -> AlgorithmSpec:
        """Quantum Signal Processing / QSVT.

        Gate count ~ O(L * n * t * polylog(1/epsilon)).
        Near-optimal in all parameters.
        """
        # QSP degree ~ L*t + log(1/eps)
        degree = int(math.ceil(L * t + math.log2(1.0 / eps)))
        # Each QSP step: block-encoding of H (cost ~ L*n) + signal processing rotation
        block_encoding_cost = L * n
        t_count = degree * block_encoding_cost

        # Ancilla qubits for block encoding: O(log(L))
        ancilla = max(1, int(math.ceil(math.log2(L))))
        total_qubits = n + ancilla

        # Rotations from QSP angles
        rotation_count = degree
        rotation_depth = degree

        return AlgorithmSpec(
            name=f"Hamiltonian sim (n={n}, QSP, t={t})",
            logical_counts=LogicalCounts(
                num_qubits=total_qubits,
                t_count=t_count,
                rotation_count=rotation_count,
                rotation_depth=rotation_depth,
            ),
            description=(
                f"QSP/QSVT simulation of {L}-term Hamiltonian on {n} qubits "
                f"for time {t}, precision {eps}."
            ),
            algorithm_family="simulation",
            problem_parameters={
                "num_qubits": n,
                "num_terms": L,
                "evolution_time": t,
                "precision": eps,
                "method": "qsp",
            },
            source="template:hamiltonian_sim",
        )

    def _qubitization(
        self, n: int, L: int, t: float, eps: float
    ) -> AlgorithmSpec:
        """Qubitization (LCU-based).

        Gate count ~ O(L * t / epsilon) with O(n + log(L)) qubits.
        Optimal in t but worse in eps than QSP.
        """
        # Steps ~ L * t / eps
        steps = max(1, int(math.ceil(L * t / eps)))

        # Qubits: system + select register
        select_qubits = max(1, int(math.ceil(math.log2(L))))
        total_qubits = n + select_qubits

        # T-count per step: PREPARE + SELECT circuits, each O(L) multi-controlled ops
        t_per_step = 4 * L  # Toffoli/T decompositions
        t_count = steps * t_per_step
        ccz_count = steps * L

        return AlgorithmSpec(
            name=f"Hamiltonian sim (n={n}, qubitization, t={t})",
            logical_counts=LogicalCounts(
                num_qubits=total_qubits,
                t_count=t_count,
                ccz_count=ccz_count,
            ),
            description=(
                f"Qubitization simulation of {L}-term Hamiltonian on {n} qubits "
                f"for time {t}, precision {eps}."
            ),
            algorithm_family="simulation",
            problem_parameters={
                "num_qubits": n,
                "num_terms": L,
                "evolution_time": t,
                "precision": eps,
                "method": "qubitization",
            },
            source="template:hamiltonian_sim",
        )

    def parameter_schema(self) -> dict[str, Any]:
        return {
            "num_qubits": {
                "type": "int",
                "default": 50,
                "min": 1,
                "description": "Number of system qubits",
            },
            "num_terms": {
                "type": "int",
                "default": 100,
                "min": 1,
                "description": "Number of terms in the Hamiltonian",
            },
            "evolution_time": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "description": "Simulation time",
            },
            "precision": {
                "type": "float",
                "default": 1e-3,
                "min": 0.0,
                "description": "Target precision (epsilon)",
            },
            "method": {
                "type": "str",
                "default": "trotter",
                "choices": list(_VALID_METHODS),
                "description": "Simulation method",
            },
        }


def hamiltonian_sim(
    num_qubits: int = 50,
    num_terms: int = 100,
    evolution_time: float = 1.0,
    precision: float = 1e-3,
    **kwargs: Any,
) -> AlgorithmSpec:
    """Convenience function for Hamiltonian simulation template."""
    return HamiltonianSimTemplate().generate(
        num_qubits=num_qubits,
        num_terms=num_terms,
        evolution_time=evolution_time,
        precision=precision,
        **kwargs,
    )
