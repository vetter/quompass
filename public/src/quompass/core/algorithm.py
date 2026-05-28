"""Algorithm specification types -- the portable interchange format for quompass."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class LogicalCounts:
    """Backend-agnostic logical resource profile of a quantum algorithm.

    This is the portable 'currency' that flows between the logical estimation
    layer and the physical estimation layer. Every backend must be able to
    produce or consume this structure.

    Field names are chosen to mirror Azure QRE's LogicalCounts input format
    to minimize mapping friction, but the type is our own -- no backend imports.
    """

    num_qubits: int
    t_count: int = 0
    rotation_count: int = 0
    rotation_depth: int = 0
    ccz_count: int = 0
    measurement_count: int = 0
    clifford_count: int = 0
    circuit_depth: Optional[int] = None

    def __post_init__(self) -> None:
        if self.num_qubits < 1:
            raise ValueError(f"num_qubits must be >= 1, got {self.num_qubits}")
        for name in (
            "t_count", "rotation_count", "rotation_depth",
            "ccz_count", "measurement_count", "clifford_count",
        ):
            val = getattr(self, name)
            if val < 0:
                raise ValueError(f"{name} must be non-negative, got {val}")
        if self.circuit_depth is not None and self.circuit_depth < 0:
            raise ValueError(
                f"circuit_depth must be non-negative, got {self.circuit_depth}"
            )

    @property
    def total_t_equivalent(self) -> int:
        """Total T-equivalent non-Clifford cost.

        Each CCZ decomposes into 4 T gates. Rotations are counted at 1:1
        as a conservative estimate (actual cost depends on synthesis precision).
        """
        return self.t_count + 4 * self.ccz_count + self.rotation_count

    @property
    def has_rotations(self) -> bool:
        return self.rotation_count > 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary (Azure QRE compatible keys)."""
        return {
            "numQubits": self.num_qubits,
            "tCount": self.t_count,
            "rotationCount": self.rotation_count,
            "rotationDepth": self.rotation_depth,
            "cczCount": self.ccz_count,
            "measurementCount": self.measurement_count,
        }


@dataclass
class AlgorithmSpec:
    """Full specification of a quantum algorithm for resource estimation.

    Combines the logical counts with metadata for reporting and
    template identification.
    """

    name: str
    logical_counts: LogicalCounts
    description: str = ""
    algorithm_family: str = ""
    problem_parameters: dict[str, Any] = field(default_factory=dict)
    source: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AlgorithmSpec:
        """Construct from a dictionary (e.g., loaded from YAML)."""
        lc_data = d.get("logical_counts", {})
        logical_counts = LogicalCounts(
            num_qubits=lc_data["num_qubits"],
            t_count=lc_data.get("t_count", 0),
            rotation_count=lc_data.get("rotation_count", 0),
            rotation_depth=lc_data.get("rotation_depth", 0),
            ccz_count=lc_data.get("ccz_count", 0),
            measurement_count=lc_data.get("measurement_count", 0),
            clifford_count=lc_data.get("clifford_count", 0),
            circuit_depth=lc_data.get("circuit_depth"),
        )
        return cls(
            name=d["name"],
            logical_counts=logical_counts,
            description=d.get("description", ""),
            algorithm_family=d.get("algorithm_family", ""),
            problem_parameters=d.get("problem_parameters", {}),
            source=d.get("source", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize for persistence."""
        return {
            "name": self.name,
            "logical_counts": {
                "num_qubits": self.logical_counts.num_qubits,
                "t_count": self.logical_counts.t_count,
                "rotation_count": self.logical_counts.rotation_count,
                "rotation_depth": self.logical_counts.rotation_depth,
                "ccz_count": self.logical_counts.ccz_count,
                "measurement_count": self.logical_counts.measurement_count,
                "clifford_count": self.logical_counts.clifford_count,
                "circuit_depth": self.logical_counts.circuit_depth,
            },
            "description": self.description,
            "algorithm_family": self.algorithm_family,
            "problem_parameters": self.problem_parameters,
            "source": self.source,
        }
