"""Abstract backend interfaces for logical and physical estimation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quompass.core.algorithm import AlgorithmSpec, LogicalCounts
    from quompass.core.error_budget import ErrorBudget
    from quompass.core.hardware import HardwareModel
    from quompass.core.qec import QECScheme
    from quompass.core.results import PhysicalEstimate


class LogicalEstimator(ABC):
    """Produces LogicalCounts from an AlgorithmSpec or algorithm definition.

    Backends: Qualtran (via Bloq call_graph), pyLIQTR, manual entry.
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def estimate(self, spec: AlgorithmSpec) -> LogicalCounts:
        """Extract logical resource counts from the algorithm spec."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend's dependencies are installed."""
        ...


class PhysicalEstimator(ABC):
    """Produces PhysicalEstimate from LogicalCounts + HardwareModel + QECScheme.

    Backends: Azure QRE, built-in analytical, Qualtran surface_code.
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def estimate(
        self,
        logical_counts: LogicalCounts,
        hardware: HardwareModel,
        qec: QECScheme,
        error_budget: ErrorBudget,
        algorithm_spec: AlgorithmSpec,
    ) -> PhysicalEstimate:
        """Produce a physical resource estimate."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend's dependencies are installed."""
        ...

    def supports_qec(self, qec: QECScheme) -> bool:
        """Check if this backend can handle the given QEC scheme."""
        return True
