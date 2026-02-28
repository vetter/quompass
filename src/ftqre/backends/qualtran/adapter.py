"""Qualtran adapter for logical resource estimation.

Wraps Qualtran's Bloq cost-analysis framework to produce
ftqre LogicalCounts. All qualtran imports are lazy -- the adapter
gracefully reports unavailability when qualtran is not installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ftqre.backends.base import LogicalEstimator
from ftqre.core.algorithm import AlgorithmSpec, LogicalCounts

if TYPE_CHECKING:
    pass


class QualtranLogicalEstimator(LogicalEstimator):
    """Logical resource estimator backed by Google Qualtran.

    Uses Qualtran's Bloq abstraction and cost analysis framework
    to extract T-count, Toffoli count, qubit count, etc.
    """

    @property
    def name(self) -> str:
        return "qualtran"

    def is_available(self) -> bool:
        try:
            import qualtran  # noqa: F401

            return True
        except ImportError:
            return False

    def estimate(self, spec: AlgorithmSpec) -> LogicalCounts:
        """Estimate logical resources by converting spec to a Bloq.

        For specs that originated from templates or manual entry,
        this attempts to map the algorithm family to a known Qualtran
        Bloq. If mapping fails, falls back to the spec's existing
        LogicalCounts.

        Parameters
        ----------
        spec : AlgorithmSpec
            The algorithm specification.

        Returns
        -------
        LogicalCounts
        """
        from ftqre.backends.qualtran.bloq_bridge import spec_to_bloq
        from ftqre.backends.qualtran.cost_extract import extract_logical_counts

        try:
            bloq = spec_to_bloq(spec)
            return extract_logical_counts(bloq)
        except (ImportError, ValueError):
            # Cannot map to Bloq -- fall back to existing counts
            return spec.logical_counts

    def estimate_from_bloq(self, bloq: Any) -> LogicalCounts:
        """Extract logical counts directly from a Qualtran Bloq.

        Power-user entry point for researchers who already have a Bloq
        object and want to feed it into ftqre's physical estimation pipeline.

        Parameters
        ----------
        bloq
            A ``qualtran.Bloq`` instance.

        Returns
        -------
        LogicalCounts
        """
        from ftqre.backends.qualtran.cost_extract import extract_logical_counts

        return extract_logical_counts(bloq)
