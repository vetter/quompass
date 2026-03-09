"""Map Azure QRE results to quompass PhysicalEstimate.

Parses the nested dict returned by ``qsharp.estimate()`` and constructs
a PhysicalEstimate with all the proper breakdown fields.

All qsharp imports are lazy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quompass.core.results import (
    LogicalQubitEstimate,
    PhysicalEstimate,
    TFactoryEstimate,
)

if TYPE_CHECKING:
    from quompass.core.algorithm import AlgorithmSpec, LogicalCounts
    from quompass.core.error_budget import ErrorBudget, ErrorBudgetBreakdown
    from quompass.core.hardware import HardwareModel
    from quompass.core.qec import QECScheme


def parse_result(
    azure_result: dict[str, Any] | Any,
    logical_counts: LogicalCounts,
    hardware: HardwareModel,
    qec: QECScheme,
    error_budget: ErrorBudget,
    algorithm_spec: AlgorithmSpec,
) -> PhysicalEstimate:
    """Parse Azure QRE output into a PhysicalEstimate.

    Parameters
    ----------
    azure_result
        The result returned by ``LogicalCounts.estimate()`` or
        ``qsharp.estimate()``.  May be an ``EstimatorResult`` object
        or a plain dict.
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
    ValueError
        If critical fields are missing from the Azure result.
    """
    # EstimatorResult objects support dict-style access; convert if needed
    if isinstance(azure_result, dict):
        result_data = azure_result
    elif hasattr(azure_result, "keys") and callable(azure_result.keys):
        # EstimatorResult or other dict-like object
        try:
            result_data = dict(azure_result)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"Failed to convert Azure result to dict: {e}. "
                f"Result type: {type(azure_result).__name__}"
            ) from e
    else:
        raise ValueError(
            f"Unexpected Azure result type: {type(azure_result).__name__}. "
            f"Expected dict or EstimatorResult."
        )

    if "physicalCounts" not in result_data:
        raise ValueError(
            "Azure QRE result missing 'physicalCounts' field. "
            f"Result keys: {list(result_data.keys())}"
        )

    phys = result_data["physicalCounts"]
    breakdown = phys.get("breakdown", {})
    lq = result_data.get("logicalQubit", {})
    tf = result_data.get("tfactory", {})

    # Physical counts
    total_physical_qubits = int(phys.get("physicalQubits", 0))
    runtime_ns = float(phys.get("runtime", 0))
    runtime_seconds = runtime_ns * 1e-9
    rqops = float(phys.get("rqops", 0))

    # Breakdown
    algo_logical_qubits = int(breakdown.get("algorithmicLogicalQubits", logical_counts.num_qubits))
    algo_physical_qubits = int(breakdown.get("algorithmicPhysicalQubits", 0))
    factory_physical_qubits = int(breakdown.get("physicalQubitsForTfactories", 0))
    logical_depth = int(breakdown.get("logicalDepth", logical_counts.total_t_equivalent))
    num_t_states = int(breakdown.get("numTstates", logical_counts.total_t_equivalent))
    clock_freq = float(breakdown.get("clockFrequency", 0))

    # Logical qubit
    code_distance = int(lq.get("codeDistance", 0))
    lq_physical = int(lq.get("physicalQubits", 0))
    lq_cycle_time_ns = float(lq.get("logicalCycleTime", 0))
    lq_error_rate = float(lq.get("logicalErrorRate", 0))

    logical_qubit = LogicalQubitEstimate(
        code_distance=code_distance,
        physical_qubits=lq_physical,
        logical_cycle_time=lq_cycle_time_ns * 1e-9,
        logical_error_rate=lq_error_rate,
    )

    # T factory
    t_factory = None
    if tf:
        num_factories = int(breakdown.get("numTfactories", 0))
        tf_physical_per = int(tf.get("physicalQubits", 0))
        tf_runtime_ns = float(tf.get("runtime", 0))
        tf_num_rounds = int(tf.get("numRounds", 1))
        tf_output_error = float(tf.get("logicalErrorRate", 0))

        if num_factories > 0:
            t_factory = TFactoryEstimate(
                num_factories=num_factories,
                physical_qubits_per_factory=tf_physical_per,
                total_physical_qubits=num_factories * tf_physical_per,
                factory_runtime=tf_runtime_ns * 1e-9,
                num_rounds=tf_num_rounds,
                output_error_rate=tf_output_error,
            )

    # Error budget
    budget_breakdown = error_budget.resolve(
        has_rotations=logical_counts.has_rotations
    )

    required_logical_rate = float(
        breakdown.get("requiredLogicalQubitErrorRate") or 0
    )
    required_t_state_rate = float(
        breakdown.get("requiredLogicalTstateErrorRate") or 0
    )

    return PhysicalEstimate(
        total_physical_qubits=total_physical_qubits,
        runtime_seconds=runtime_seconds,
        rqops=rqops,
        algorithmic_logical_qubits=algo_logical_qubits,
        physical_qubits_for_algorithm=algo_physical_qubits,
        physical_qubits_for_t_factories=factory_physical_qubits,
        logical_qubit=logical_qubit,
        t_factory=t_factory,
        algorithmic_logical_depth=logical_depth,
        num_t_states=num_t_states,
        clock_frequency=clock_freq,
        error_budget=budget_breakdown,
        required_logical_error_rate=required_logical_rate,
        required_t_state_error_rate=required_t_state_rate,
        algorithm_spec=algorithm_spec,
        hardware_model=hardware,
        qec_scheme_name=qec.name,
        backend_name="azure",
        raw_backend_output=azure_result,
    )
