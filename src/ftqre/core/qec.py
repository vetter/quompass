"""Quantum Error Correction scheme abstractions.

This is the critical differentiator of ftqre. The design must support
surface code, Floquet code, color code, qLDPC, and unknown future codes
through a single abstract interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

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


# Registry of built-in QEC schemes
_BUILTIN_SCHEMES: dict[str, type[QECScheme]] = {
    "surface_code": SurfaceCode,
    "floquet_code": FloquetCode,
}


def get_qec_scheme(name: str) -> QECScheme:
    """Look up a QEC scheme by name."""
    cls = _BUILTIN_SCHEMES.get(name)
    if cls is None:
        available = ", ".join(sorted(_BUILTIN_SCHEMES.keys()))
        raise ValueError(f"Unknown QEC scheme '{name}'. Available: {available}")
    return cls()
