"""Quantum chemistry algorithm template.

Resource models for quantum chemistry simulation methods:
- Double factorization (DF) -- Lee et al. (2021)
- Tensor hypercontraction (THC) -- Lee et al. (2021)
- Sparse Hamiltonian -- Berry et al. (2019)

These are based on published resource estimates for the
electronic structure problem in second quantization.

References:
- Lee et al. (2021): "Even more efficient quantum computations of chemistry
  through tensor hypercontraction" PRX Quantum 2, 030305
- Berry et al. (2019): "Qubitization of arbitrary basis quantum chemistry
  leveraging sparsity and low rank factorization" Quantum 3, 208
- Reiher et al. (2017): "Elucidating reaction mechanisms on quantum computers"
  PNAS 114(29), 7555-7560
"""

from __future__ import annotations

import math
from typing import Any

from ftqre.core.algorithm import AlgorithmSpec, LogicalCounts
from ftqre.templates.base import AlgorithmTemplate

_VALID_METHODS = ("double_factorization", "thc", "sparse")


class ChemistryTemplate(AlgorithmTemplate):
    """Quantum chemistry simulation template."""

    @property
    def name(self) -> str:
        return "chemistry"

    @property
    def family(self) -> str:
        return "chemistry"

    @property
    def description(self) -> str:
        return "Quantum chemistry (double factorization, THC, or sparse)"

    def generate(self, **params: Any) -> AlgorithmSpec:
        num_orbitals = int(params.get("num_orbitals", 54))
        num_electrons = int(params.get("num_electrons", 0))
        method = str(params.get("method", "double_factorization"))

        if method not in _VALID_METHODS:
            raise ValueError(
                f"Unknown method '{method}'. Available: {', '.join(_VALID_METHODS)}"
            )

        # Default electrons to roughly half-filled
        if num_electrons <= 0:
            num_electrons = num_orbitals

        if method == "double_factorization":
            return self._double_factorization(num_orbitals, num_electrons)
        elif method == "thc":
            return self._thc(num_orbitals, num_electrons)
        else:
            return self._sparse(num_orbitals, num_electrons)

    def _double_factorization(self, N: int, eta: int) -> AlgorithmSpec:
        """Double factorization (DF) resource model.

        From Lee et al. (2021):
        - Qubits: N (spatial orbitals) + O(log N) ancilla
        - Toffoli count: O(N^3) with good constant factors
        - The DF rank L ~ N, giving O(L * N^2) = O(N^3) Toffoli
        """
        # Qubits: 2N spin-orbitals (Jordan-Wigner) + log(N) ancilla
        ancilla = max(1, int(math.ceil(math.log2(N))))
        total_qubits = 2 * N + ancilla

        # DF rank L ~ N/2 (typical for molecular systems)
        L = max(1, N // 2)
        # Toffoli per step ~ L * N, number of steps ~ N
        ccz_count = int(0.5 * L * N * N)
        t_count = 4 * N  # small overhead from rotations

        # Rotations for QROM and basis rotations
        rotation_count = L * N
        rotation_depth = L

        return AlgorithmSpec(
            name=f"Chemistry DF (N={N}, eta={eta})",
            logical_counts=LogicalCounts(
                num_qubits=total_qubits,
                t_count=t_count,
                ccz_count=ccz_count,
                rotation_count=rotation_count,
                rotation_depth=rotation_depth,
                measurement_count=total_qubits,
            ),
            description=(
                f"Double factorization chemistry with {N} orbitals, "
                f"{eta} electrons."
            ),
            algorithm_family="chemistry",
            problem_parameters={
                "num_orbitals": N,
                "num_electrons": eta,
                "method": "double_factorization",
            },
            source="template:chemistry",
        )

    def _thc(self, N: int, eta: int) -> AlgorithmSpec:
        """Tensor hypercontraction (THC) resource model.

        From Lee et al. (2021):
        - THC rank M ~ 5N-10N (we use 7N)
        - Toffoli count: O(M * N) = O(N^2) per step, O(N) steps
        - Better constant factors than DF for large systems
        """
        M = 7 * N  # THC rank
        ancilla = max(1, int(math.ceil(math.log2(M))))
        total_qubits = 2 * N + ancilla

        # Toffoli per step ~ M + N, number of QPE steps ~ M
        ccz_count = int(0.3 * M * (M + N))
        t_count = 4 * N

        rotation_count = M + N
        rotation_depth = M

        return AlgorithmSpec(
            name=f"Chemistry THC (N={N}, eta={eta})",
            logical_counts=LogicalCounts(
                num_qubits=total_qubits,
                t_count=t_count,
                ccz_count=ccz_count,
                rotation_count=rotation_count,
                rotation_depth=rotation_depth,
                measurement_count=total_qubits,
            ),
            description=(
                f"Tensor hypercontraction chemistry with {N} orbitals, "
                f"{eta} electrons."
            ),
            algorithm_family="chemistry",
            problem_parameters={
                "num_orbitals": N,
                "num_electrons": eta,
                "method": "thc",
            },
            source="template:chemistry",
        )

    def _sparse(self, N: int, eta: int) -> AlgorithmSpec:
        """Sparse Hamiltonian resource model.

        From Berry et al. (2019):
        - Leverages sparsity in the Hamiltonian
        - Toffoli count depends on number of non-zero entries d
        - d ~ O(N^2) for typical molecular Hamiltonians
        """
        d = N * N  # approximate sparsity
        ancilla = max(1, int(math.ceil(math.log2(d))))
        total_qubits = 2 * N + ancilla

        # Qubitization steps ~ d * sqrt(d)
        steps = int(math.ceil(d * math.sqrt(d) / N))
        ccz_count = steps * N
        t_count = 8 * N

        return AlgorithmSpec(
            name=f"Chemistry Sparse (N={N}, eta={eta})",
            logical_counts=LogicalCounts(
                num_qubits=total_qubits,
                t_count=t_count,
                ccz_count=ccz_count,
                measurement_count=total_qubits,
            ),
            description=(
                f"Sparse qubitization chemistry with {N} orbitals, "
                f"{eta} electrons."
            ),
            algorithm_family="chemistry",
            problem_parameters={
                "num_orbitals": N,
                "num_electrons": eta,
                "method": "sparse",
            },
            source="template:chemistry",
        )

    def parameter_schema(self) -> dict[str, Any]:
        return {
            "num_orbitals": {
                "type": "int",
                "default": 54,
                "min": 2,
                "description": "Number of spatial orbitals",
            },
            "num_electrons": {
                "type": "int",
                "default": 0,
                "min": 0,
                "description": "Number of electrons (0 = auto, defaults to num_orbitals)",
            },
            "method": {
                "type": "str",
                "default": "double_factorization",
                "choices": list(_VALID_METHODS),
                "description": "Chemistry simulation method",
            },
        }


def chemistry(
    num_orbitals: int = 54, num_electrons: int = 0, **kwargs: Any
) -> AlgorithmSpec:
    """Convenience function for chemistry template."""
    return ChemistryTemplate().generate(
        num_orbitals=num_orbitals, num_electrons=num_electrons, **kwargs
    )
