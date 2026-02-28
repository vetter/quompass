"""Resource estimation result types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ftqre.core.algorithm import AlgorithmSpec
    from ftqre.core.error_budget import ErrorBudgetBreakdown
    from ftqre.core.hardware import HardwareModel
    from ftqre.core.qec import QECScheme


@dataclass(frozen=True)
class TFactoryEstimate:
    """T-state factory resource requirements."""

    num_factories: int
    physical_qubits_per_factory: int
    total_physical_qubits: int
    factory_runtime: float  # seconds per round
    num_rounds: int
    output_error_rate: float


@dataclass(frozen=True)
class LogicalQubitEstimate:
    """Properties of a single logical qubit."""

    code_distance: int
    physical_qubits: int
    logical_cycle_time: float  # seconds
    logical_error_rate: float


@dataclass(frozen=True)
class PhysicalEstimate:
    """Complete physical resource estimation result.

    This is the primary output type. It contains the full breakdown
    from logical counts down to physical qubit counts and wall-clock time.
    """

    # Top-level summary
    total_physical_qubits: int
    runtime_seconds: float
    rqops: float

    # Breakdown
    algorithmic_logical_qubits: int
    physical_qubits_for_algorithm: int
    physical_qubits_for_t_factories: int

    # Logical qubit properties
    logical_qubit: LogicalQubitEstimate

    # T factory
    t_factory: Optional[TFactoryEstimate]

    # Depth/counts
    algorithmic_logical_depth: int
    num_t_states: int
    clock_frequency: float  # logical cycles/sec

    # Error
    error_budget: ErrorBudgetBreakdown
    required_logical_error_rate: float
    required_t_state_error_rate: float

    # Provenance
    algorithm_spec: AlgorithmSpec
    hardware_model: HardwareModel
    qec_scheme_name: str
    backend_name: str
    raw_backend_output: Optional[dict[str, Any]] = None

    @property
    def runtime_human(self) -> str:
        """Human-readable runtime string."""
        td = timedelta(seconds=self.runtime_seconds)
        total_secs = int(td.total_seconds())
        if total_secs < 1:
            return f"{self.runtime_seconds * 1e6:.1f} us"
        if total_secs < 60:
            return f"{total_secs}s"
        if total_secs < 3600:
            m, s = divmod(total_secs, 60)
            return f"{m}m {s}s"
        if total_secs < 86400:
            h, remainder = divmod(total_secs, 3600)
            m = remainder // 60
            return f"{h}h {m}m"
        days = total_secs // 86400
        hours = (total_secs % 86400) // 3600
        return f"{days}d {hours}h"

    @property
    def space_time_volume(self) -> float:
        """Qubits * seconds."""
        return self.total_physical_qubits * self.runtime_seconds

    def summary_dict(self) -> dict[str, Any]:
        """Flat dictionary for tabular display."""
        return {
            "algorithm": self.algorithm_spec.name,
            "total_physical_qubits": self.total_physical_qubits,
            "physical_qubits_algorithm": self.physical_qubits_for_algorithm,
            "physical_qubits_t_factories": self.physical_qubits_for_t_factories,
            "runtime": self.runtime_human,
            "runtime_seconds": self.runtime_seconds,
            "rqops": self.rqops,
            "code_distance": self.logical_qubit.code_distance,
            "logical_qubits": self.algorithmic_logical_qubits,
            "num_t_states": self.num_t_states,
            "space_time_volume": self.space_time_volume,
            "error_budget": self.error_budget.total,
            "backend": self.backend_name,
        }
