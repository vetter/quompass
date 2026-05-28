"""Shor's integer factoring algorithm template.

Resource model based on:
- Gidney & Ekera (2021): "How to factor 2048 bit RSA integers in 8 hours"
  using 20 million noisy qubits. arXiv:1905.09749
- Azure QRE known estimates for RSA factoring

The template computes logical resource counts as a function of the
number of bits n in the integer to be factored.
"""

from __future__ import annotations

import math
from typing import Any

from quompass.core.algorithm import AlgorithmSpec, LogicalCounts
from quompass.templates.base import AlgorithmTemplate


class ShorTemplate(AlgorithmTemplate):
    """Shor's algorithm for integer factoring."""

    @property
    def name(self) -> str:
        return "shor"

    @property
    def family(self) -> str:
        return "cryptanalysis"

    @property
    def description(self) -> str:
        return "Shor's algorithm for integer factoring (Gidney-Ekera construction)"

    def generate(self, **params: Any) -> AlgorithmSpec:
        n_bits = int(params.get("n_bits", 2048))
        construction = str(params.get("construction", "gidney_ekera"))

        if construction == "gidney_ekera":
            return self._gidney_ekera(n_bits)
        elif construction == "textbook":
            return self._textbook(n_bits)
        else:
            raise ValueError(
                f"Unknown construction '{construction}'. "
                f"Available: gidney_ekera, textbook"
            )

    def _gidney_ekera(self, n_bits: int) -> AlgorithmSpec:
        """Gidney-Ekera optimized construction.

        From Gidney & Ekera (2021), the dominant cost is modular
        exponentiation using Toffoli gates. Key scalings:
        - Logical qubits: ~2n + O(sqrt(n))
        - CCZ/Toffoli count: ~0.3 * n^3
        - T count: small constant (most non-Clifford cost is in CCZ)
        - Measurement count: ~2n (for modular exponentiation readout)
        """
        num_qubits = 2 * n_bits + int(math.ceil(math.sqrt(n_bits)))
        ccz_count = int(0.3 * n_bits**3)
        t_count = 12
        rotation_count = 12
        rotation_depth = 12
        measurement_count = 2 * n_bits

        return AlgorithmSpec(
            name=f"Shor's factoring (n={n_bits}, Gidney-Ekera)",
            logical_counts=LogicalCounts(
                num_qubits=num_qubits,
                t_count=t_count,
                rotation_count=rotation_count,
                rotation_depth=rotation_depth,
                ccz_count=ccz_count,
                measurement_count=measurement_count,
            ),
            description=(
                f"Factor a {n_bits}-bit integer using the Gidney-Ekera "
                f"construction with windowed arithmetic."
            ),
            algorithm_family="cryptanalysis",
            problem_parameters={"n_bits": n_bits, "construction": "gidney_ekera"},
            source="template:shor",
        )

    def _textbook(self, n_bits: int) -> AlgorithmSpec:
        """Textbook Shor's construction (less efficient, for comparison).

        Uses standard modular exponentiation with O(n^3) Toffoli gates
        and 2n+3 logical qubits.
        """
        num_qubits = 2 * n_bits + 3
        ccz_count = int(2.0 * n_bits**3)
        t_count = 0
        measurement_count = n_bits

        return AlgorithmSpec(
            name=f"Shor's factoring (n={n_bits}, textbook)",
            logical_counts=LogicalCounts(
                num_qubits=num_qubits,
                ccz_count=ccz_count,
                t_count=t_count,
                measurement_count=measurement_count,
            ),
            description=(
                f"Factor a {n_bits}-bit integer using the textbook "
                f"Shor construction."
            ),
            algorithm_family="cryptanalysis",
            problem_parameters={"n_bits": n_bits, "construction": "textbook"},
            source="template:shor",
        )

    def parameter_schema(self) -> dict[str, Any]:
        return {
            "n_bits": {
                "type": "int",
                "default": 2048,
                "min": 4,
                "description": "Number of bits in the integer to factor",
            },
            "construction": {
                "type": "str",
                "default": "gidney_ekera",
                "choices": ["gidney_ekera", "textbook"],
                "description": "Which algorithmic construction to use",
            },
        }


def shor(n_bits: int = 2048, **kwargs: Any) -> AlgorithmSpec:
    """Convenience function for Shor's algorithm template."""
    return ShorTemplate().generate(n_bits=n_bits, **kwargs)
