"""MQT (Munich Quantum Toolkit) adapter for physical resource estimation.

Wraps MQT's resource estimation capabilities to produce quompass
PhysicalEstimate results. All MQT imports are lazy -- the adapter
gracefully reports unavailability when mqt.core is not installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from quompass.backends.base import PhysicalEstimator

if TYPE_CHECKING:
    from quompass.core.algorithm import AlgorithmSpec, LogicalCounts
    from quompass.core.error_budget import ErrorBudget
    from quompass.core.hardware import HardwareModel
    from quompass.core.qec import QECScheme
    from quompass.core.results import PhysicalEstimate


class MQTPhysicalEstimator(PhysicalEstimator):
    """Physical resource estimator backed by MQT.

    Uses MQT's resource estimation tools for physical-level
    cost analysis.

    .. note::
        This is a stub. Install mqt.core and contribute an
        implementation to enable this backend.
    """

    @property
    def name(self) -> str:
        return "mqt"

    def is_available(self) -> bool:
        try:
            import mqt.core  # noqa: F401

            return True
        except ImportError:
            return False

    def estimate(
        self,
        logical_counts: LogicalCounts,
        hardware: HardwareModel,
        qec: QECScheme,
        error_budget: ErrorBudget,
        algorithm_spec: AlgorithmSpec,
    ) -> PhysicalEstimate:
        """Run MQT physical estimation.

        Parameters
        ----------
        logical_counts : LogicalCounts
        hardware : HardwareModel
        qec : QECScheme
        error_budget : ErrorBudget
        algorithm_spec : AlgorithmSpec

        Returns
        -------
        PhysicalEstimate

        Raises
        ------
        NotImplementedError
            Always -- this is a stub awaiting implementation.
        """
        raise NotImplementedError(
            "MQT backend is not yet implemented. "
            "Contributions welcome! See the quompass plugin architecture docs."
        )

    def supports_qec(self, qec: QECScheme) -> bool:
        """MQT supports arbitrary QEC schemes."""
        return True
