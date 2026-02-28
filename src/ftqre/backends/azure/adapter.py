"""Azure Quantum Resource Estimation backend adapter.

Wraps ``qsharp.estimate()`` to produce ftqre PhysicalEstimate results.
All qsharp imports are lazy -- the adapter gracefully reports
unavailability when qsharp is not installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ftqre.backends.base import PhysicalEstimator

if TYPE_CHECKING:
    from ftqre.core.algorithm import AlgorithmSpec, LogicalCounts
    from ftqre.core.error_budget import ErrorBudget
    from ftqre.core.hardware import HardwareModel
    from ftqre.core.qec import QECScheme
    from ftqre.core.results import PhysicalEstimate


class AzurePhysicalEstimator(PhysicalEstimator):
    """Physical resource estimator backed by Azure Quantum Resource Estimation.

    Uses ``qsharp.estimate()`` with ``LogicalCounts`` input mode
    (no Q# program needed) plus custom ``EstimatorParams``.
    """

    @property
    def name(self) -> str:
        return "azure"

    def is_available(self) -> bool:
        try:
            import qsharp  # noqa: F401

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
        """Run Azure QRE physical estimation.

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
        """
        import qsharp

        from ftqre.backends.azure.param_map import build_params
        from ftqre.backends.azure.result_map import parse_result

        # Build Azure-format inputs
        params = build_params(hardware, qec, error_budget)

        # Azure QRE accepts LogicalCounts as a dict
        azure_logical_counts = logical_counts.to_dict()

        # Call Azure QRE
        azure_result = qsharp.estimate(
            f"LogicalCounts({azure_logical_counts})",
            params=params,
        )

        # Parse result into ftqre types
        return parse_result(
            azure_result,
            logical_counts,
            hardware,
            qec,
            error_budget,
            algorithm_spec,
        )
