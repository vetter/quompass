"""Grover's search algorithm template.

Resource model based on:
- Grover (1996): original algorithm
- Boyer et al. (1998): tight bounds on quantum searching
- Brassard et al. (2002): quantum amplitude amplification

The template computes logical resource counts as a function of:
- search_space_bits: log2 of the search space size
- num_solutions: expected number of solutions
- num_oracle_t_gates: T-gate cost of one oracle call
"""

from __future__ import annotations

import math
from typing import Any

from quompass.core.algorithm import AlgorithmSpec, LogicalCounts
from quompass.templates.base import AlgorithmTemplate


class GroverTemplate(AlgorithmTemplate):
    """Grover's search / amplitude amplification template."""

    @property
    def name(self) -> str:
        return "grover"

    @property
    def family(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "Grover's search / amplitude amplification"

    def generate(self, **params: Any) -> AlgorithmSpec:
        search_space_bits = int(params.get("search_space_bits", 20))
        num_solutions = int(params.get("num_solutions", 1))
        num_oracle_t_gates = int(params.get("num_oracle_t_gates", 0))

        N = 2**search_space_bits
        M = max(1, num_solutions)

        # Number of Grover iterations: pi/4 * sqrt(N/M)
        num_iterations = max(1, int(math.ceil(math.pi / 4 * math.sqrt(N / M))))

        # Qubits: search register + ancilla for oracle + 1 for phase flip
        # Oracle ancilla ~ search_space_bits (conservative)
        total_qubits = 2 * search_space_bits + 1

        # Oracle T-gate cost: user-provided or estimated
        if num_oracle_t_gates <= 0:
            # Default: generic oracle with O(n) Toffoli gates
            oracle_t = 8 * search_space_bits
        else:
            oracle_t = num_oracle_t_gates

        # Diffusion operator: multi-controlled Z gate
        # Decomposes into O(n) Toffoli gates = O(4n) T gates
        diffusion_t = 4 * search_space_bits

        # Total T-count: iterations * (oracle + diffusion)
        t_count = num_iterations * (oracle_t + diffusion_t)

        # CCZ from multi-controlled operations
        ccz_per_iteration = search_space_bits  # diffusion operator
        ccz_count = num_iterations * ccz_per_iteration

        # Measurements: read out search register
        measurement_count = search_space_bits

        return AlgorithmSpec(
            name=f"Grover (n={search_space_bits}, M={M})",
            logical_counts=LogicalCounts(
                num_qubits=total_qubits,
                t_count=t_count,
                ccz_count=ccz_count,
                measurement_count=measurement_count,
            ),
            description=(
                f"Grover search over {search_space_bits}-bit space "
                f"({N:,} elements) with {M} solution(s), "
                f"requiring {num_iterations:,} iterations."
            ),
            algorithm_family="search",
            problem_parameters={
                "search_space_bits": search_space_bits,
                "num_solutions": num_solutions,
                "num_oracle_t_gates": num_oracle_t_gates,
                "num_iterations": num_iterations,
            },
            source="template:grover",
        )

    def parameter_schema(self) -> dict[str, Any]:
        return {
            "search_space_bits": {
                "type": "int",
                "default": 20,
                "min": 1,
                "description": "Number of bits in the search space (N = 2^bits)",
            },
            "num_solutions": {
                "type": "int",
                "default": 1,
                "min": 1,
                "description": "Expected number of solutions in the search space",
            },
            "num_oracle_t_gates": {
                "type": "int",
                "default": 0,
                "min": 0,
                "description": "T-gate cost of one oracle call (0 = auto-estimate)",
            },
        }


def grover(search_space_bits: int = 20, **kwargs: Any) -> AlgorithmSpec:
    """Convenience function for Grover's algorithm template."""
    return GroverTemplate().generate(search_space_bits=search_space_bits, **kwargs)
