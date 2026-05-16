"""Quompass -- Portable Fault-Tolerant Quantum Resource Estimation."""

from quompass._version import __version__
from quompass.core.algorithm import AlgorithmSpec, LogicalCounts
from quompass.core.error_budget import ErrorBudget
from quompass.core.hardware import HardwareModel, HardwarePreset, QubitParams
from quompass.core.qec import (
    FloquetCode,
    FormulaQEC,
    QECScheme,
    SurfaceCode,
    color_code,
    get_qec_scheme,
)
from quompass.core.results import PhysicalEstimate

__all__ = [
    "__version__",
    "AlgorithmSpec",
    "LogicalCounts",
    "ErrorBudget",
    "HardwareModel",
    "HardwarePreset",
    "QubitParams",
    "QECScheme",
    "SurfaceCode",
    "FloquetCode",
    "FormulaQEC",
    "color_code",
    "PhysicalEstimate",
    "estimate",
]


def estimate(
    algorithm: AlgorithmSpec,
    hardware: HardwareModel | HardwarePreset | str = HardwarePreset.SUPERCONDUCTING_REALISTIC,
    qec: QECScheme | str = "surface_code",
    error_budget: ErrorBudget | float = 0.001,
    logical_backend: str = "auto",
    physical_backend: str = "auto",
) -> PhysicalEstimate:
    """One-shot resource estimation.

    The primary entry point. Handles type coercion, backend selection,
    and the full logical->physical pipeline.

    Parameters
    ----------
    algorithm : AlgorithmSpec
        The algorithm to estimate resources for.
    hardware : HardwareModel | HardwarePreset | str
        Hardware target. Can be a preset name string, HardwarePreset enum,
        or a fully specified HardwareModel.
    qec : QECScheme | str
        QEC scheme. Can be a name string or a QECScheme instance.
    error_budget : ErrorBudget | float
        Total error budget. If a float, creates an ErrorBudget with
        uniform distribution.
    logical_backend : str
        Logical estimation backend name, or "auto" for best available.
    physical_backend : str
        Physical estimation backend name, or "auto" for best available.

    Returns
    -------
    PhysicalEstimate
        Complete physical resource estimation result.

    Examples
    --------
    >>> import quompass
    >>> from quompass.templates.shor import shor
    >>> spec = shor(n_bits=2048)
    >>> result = quompass.estimate(spec)
    >>> print(result.total_physical_qubits)
    >>> print(result.runtime_human)
    """
    # 1. Resolve hardware
    if isinstance(hardware, str):
        hardware = HardwareModel.from_preset(hardware)
    elif isinstance(hardware, HardwarePreset):
        hardware = HardwareModel.from_preset(hardware)

    # 2. Resolve QEC
    if isinstance(qec, str):
        qec = get_qec_scheme(qec)

    # 3. Resolve error budget
    if isinstance(error_budget, (int, float)):
        error_budget = ErrorBudget(total=float(error_budget))

    # 4. Select backends
    le, pe = _select_backends(logical_backend, physical_backend)

    # 5. Run pipeline
    logical_counts = le.estimate(algorithm)
    return pe.estimate(logical_counts, hardware, qec, error_budget, algorithm)


def _select_backends(
    logical_name: str, physical_name: str
) -> tuple:
    """Select the best available backends using the registry."""
    from quompass.backends.registry import select_backends

    return select_backends(logical_name, physical_name)
