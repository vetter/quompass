"""pyLIQTR adapter for logical resource estimation.

Wraps pyLIQTR's circuit generation and resource counting to produce
quompass LogicalCounts. All pyLIQTR imports are lazy -- the adapter
gracefully reports unavailability when pyLIQTR is not installed.
"""

from __future__ import annotations

from quompass.backends.base import LogicalEstimator
from quompass.core.algorithm import AlgorithmSpec, LogicalCounts


class PyLIQTRLogicalEstimator(LogicalEstimator):
    """Logical resource estimator backed by pyLIQTR.

    Uses pyLIQTR's circuit generation and resource counting
    framework to extract T-count, qubit count, etc.

    .. note::
        This is a stub. Install pyLIQTR and contribute an
        implementation to enable this backend.
    """

    @property
    def name(self) -> str:
        return "pyliqtr"

    def is_available(self) -> bool:
        try:
            import pyLIQTR  # noqa: F401

            return True
        except ImportError:
            return False

    def estimate(self, spec: AlgorithmSpec) -> LogicalCounts:
        """Estimate logical resources using pyLIQTR.

        Parameters
        ----------
        spec : AlgorithmSpec
            The algorithm specification.

        Returns
        -------
        LogicalCounts

        Raises
        ------
        NotImplementedError
            Always -- this is a stub awaiting implementation.
        """
        raise NotImplementedError(
            "pyLIQTR backend is not yet implemented. "
            "Contributions welcome! See the quompass plugin architecture docs."
        )
