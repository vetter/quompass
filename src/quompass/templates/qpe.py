"""Quantum Phase Estimation (QPE) algorithm template.

Resource model based on standard QPE circuit structure:
- Uses O(precision) controlled-U operations
- Each controlled-U contributes to T-count via gate synthesis
- Total logical qubits = system qubits + precision qubits + ancilla

References:
- Kitaev (1995): original QPE
- Nielsen & Chuang (2000): textbook QPE circuit
- Babbush et al. (2018): QPE with improved error bounds
"""

from __future__ import annotations

import math
from typing import Any

from quompass.core.algorithm import AlgorithmSpec, LogicalCounts
from quompass.templates.base import AlgorithmTemplate


class QPETemplate(AlgorithmTemplate):
    """Quantum Phase Estimation template."""

    @property
    def name(self) -> str:
        return "qpe"

    @property
    def family(self) -> str:
        return "phase_estimation"

    @property
    def description(self) -> str:
        return "Quantum Phase Estimation for eigenvalue extraction"

    def generate(self, **params: Any) -> AlgorithmSpec:
        num_qubits = int(params.get("num_qubits", 10))
        precision_bits = int(params.get("precision_bits", 20))
        num_rotations = int(params.get("num_rotations", 0))

        # Logical qubits: system + precision register + 1 ancilla
        total_qubits = num_qubits + precision_bits + 1

        # T-count: controlled-U operations at each precision level
        # Each controlled-U for an n-qubit system requires O(n) T gates
        # for a generic unitary. QPE applies 2^k copies of U for k-th bit.
        # Total T-count ~ sum_{k=0}^{precision-1} 2^k * O(n) ~ 2^precision * n
        # We use a more conservative estimate with T gates per controlled-U
        t_per_controlled_u = 4 * num_qubits  # approximate for structured unitaries
        total_t = sum(
            t_per_controlled_u * (2**k)
            for k in range(min(precision_bits, 30))  # cap to avoid overflow
        )
        # For very large precision, use closed-form
        if precision_bits > 30:
            total_t = t_per_controlled_u * (2**precision_bits - 1)

        # CCZ from Toffoli decompositions in controlled multi-qubit gates
        ccz_count = int(0.5 * num_qubits * precision_bits)

        # Rotations for phase kickback inverse QFT
        rotation_count = precision_bits * (precision_bits - 1) // 2 + num_rotations
        rotation_depth = precision_bits + num_rotations

        # Measurements: read out precision register
        measurement_count = precision_bits

        return AlgorithmSpec(
            name=f"QPE (n={num_qubits}, precision={precision_bits})",
            logical_counts=LogicalCounts(
                num_qubits=total_qubits,
                t_count=total_t,
                ccz_count=ccz_count,
                rotation_count=rotation_count,
                rotation_depth=rotation_depth,
                measurement_count=measurement_count,
            ),
            description=(
                f"Quantum Phase Estimation with {num_qubits} system qubits "
                f"and {precision_bits} bits of precision."
            ),
            algorithm_family="phase_estimation",
            problem_parameters={
                "num_qubits": num_qubits,
                "precision_bits": precision_bits,
                "num_rotations": num_rotations,
            },
            source="template:qpe",
        )

    def parameter_schema(self) -> dict[str, Any]:
        return {
            "num_qubits": {
                "type": "int",
                "default": 10,
                "min": 1,
                "description": "Number of system qubits (size of the unitary)",
            },
            "precision_bits": {
                "type": "int",
                "default": 20,
                "min": 1,
                "description": "Number of precision bits in the phase register",
            },
            "num_rotations": {
                "type": "int",
                "default": 0,
                "min": 0,
                "description": "Additional rotation gates (beyond inverse QFT)",
            },
        }


def qpe(num_qubits: int = 10, precision_bits: int = 20, **kwargs: Any) -> AlgorithmSpec:
    """Convenience function for QPE template."""
    return QPETemplate().generate(
        num_qubits=num_qubits, precision_bits=precision_bits, **kwargs
    )
