"""Azure Quantum Resource Estimation backend adapter.

Wraps ``qsharp.estimator.LogicalCounts.estimate()`` to produce quompass
PhysicalEstimate results. All qsharp imports are lazy -- the adapter
gracefully reports unavailability when qsharp is not installed.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from quompass.backends.base import PhysicalEstimator

if TYPE_CHECKING:
    from quompass.core.algorithm import AlgorithmSpec, LogicalCounts
    from quompass.core.error_budget import ErrorBudget
    from quompass.core.hardware import HardwareModel
    from quompass.core.qec import QECScheme
    from quompass.core.results import PhysicalEstimate

logger = logging.getLogger(__name__)


class AzurePhysicalEstimator(PhysicalEstimator):
    """Physical resource estimator backed by Azure Quantum Resource Estimation.

    Uses ``qsharp.estimator.LogicalCounts`` with the ``estimate()`` method
    (no Q# program needed) plus custom qubit/QEC/error-budget parameters.

    Install with: ``pip install qsharp>=1.0`` or ``pip install quompass[azure]``
    """

    @property
    def name(self) -> str:
        return "azure"

    def is_available(self) -> bool:
        try:
            from qsharp.estimator import LogicalCounts as _  # noqa: F401

            return True
        except (ImportError, ModuleNotFoundError):
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

        Uses the ``qsharp.estimator.LogicalCounts`` class which accepts
        a dict of logical resource counts and runs physical estimation
        locally via the Rust-based QDK engine.

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
        RuntimeError
            If the Azure QRE estimation call fails.
        """
        try:
            from qsharp.estimator import LogicalCounts as AzureLogicalCounts
        except ImportError as e:
            raise ImportError(
                "qsharp package is required for the Azure backend. "
                "Install with: pip install 'quompass[azure]' "
                "or: pip install 'qsharp>=1.0'"
            ) from e

        from quompass.backends.azure.param_map import build_params
        from quompass.backends.azure.result_map import parse_result

        # Build Azure-format parameter dict
        params = build_params(hardware, qec, error_budget)

        # Convert quompass LogicalCounts to Azure-format dict (camelCase keys)
        azure_logical_counts = AzureLogicalCounts(logical_counts.to_dict())

        # Call Azure QRE
        try:
            azure_result = azure_logical_counts.estimate(params=params)
        except Exception as e:
            raise RuntimeError(
                f"Azure QRE estimation failed for algorithm "
                f"'{algorithm_spec.name}' with hardware "
                f"'{hardware.name}' and QEC '{qec.name}': {e}"
            ) from e

        # Validate that we got a usable result
        if azure_result is None:
            raise RuntimeError(
                "Azure QRE returned None. This may indicate an incompatible "
                "combination of hardware parameters and QEC scheme."
            )

        # Parse result into quompass types
        return parse_result(
            azure_result,
            logical_counts,
            hardware,
            qec,
            error_budget,
            algorithm_spec,
        )
