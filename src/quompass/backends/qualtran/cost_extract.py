"""Extract logical resource counts from Qualtran Bloqs.

Uses Qualtran's cost analysis framework (call_graph, get_cost_value)
to extract T-count, qubit count, rotation count, etc.

All qualtran imports are lazy -- this module can be imported even if
qualtran is not installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quompass.core.algorithm import LogicalCounts

if TYPE_CHECKING:
    pass  # qualtran types referenced in docstrings only


def extract_logical_counts(bloq: Any) -> LogicalCounts:
    """Extract LogicalCounts from a Qualtran Bloq.

    Tries the modern ``get_cost_value`` API first (qualtran >= 0.5),
    then falls back to ``call_graph`` analysis.

    Parameters
    ----------
    bloq
        A ``qualtran.Bloq`` instance.

    Returns
    -------
    LogicalCounts
    """
    try:
        return _extract_via_cost_api(bloq)
    except Exception:
        return _extract_via_call_graph(bloq)


def _extract_via_cost_api(bloq: Any) -> LogicalCounts:
    """Extract counts using Qualtran's get_cost_value (modern API)."""
    from qualtran.resource_counting import get_cost_value, QECGatesCost, QubitCount

    gate_costs = get_cost_value(bloq, QECGatesCost())
    num_qubits = get_cost_value(bloq, QubitCount())

    # QECGatesCost returns a dict-like with t, toffoli, rotation, measurement keys
    t_count = int(gate_costs.get("t", 0))
    ccz_count = int(gate_costs.get("toffoli", 0))
    rotation_count = int(gate_costs.get("rotation", 0))
    measurement_count = int(gate_costs.get("measurement", 0))

    return LogicalCounts(
        num_qubits=int(num_qubits),
        t_count=t_count,
        ccz_count=ccz_count,
        rotation_count=rotation_count,
        measurement_count=measurement_count,
    )


def _extract_via_call_graph(bloq: Any) -> LogicalCounts:
    """Extract counts via call_graph analysis (legacy API)."""
    from qualtran.bloqs.basic_gates import TGate, Toffoli
    from qualtran.resource_counting import get_bloq_callee_counts

    callee_counts = get_bloq_callee_counts(bloq)

    t_count = 0
    ccz_count = 0
    for callee, count in callee_counts:
        callee_name = type(callee).__name__
        if isinstance(callee, TGate) or callee_name == "TGate":
            t_count += count
        elif isinstance(callee, Toffoli) or callee_name in ("Toffoli", "CCZ"):
            ccz_count += count

    # Estimate qubits from bloq signature
    num_qubits = _count_qubits_from_signature(bloq)

    return LogicalCounts(
        num_qubits=num_qubits,
        t_count=t_count,
        ccz_count=ccz_count,
    )


def _count_qubits_from_signature(bloq: Any) -> int:
    """Count total qubit count from a Bloq's signature."""
    total = 0
    try:
        for reg in bloq.signature:
            size = 1
            for dim in reg.shape:
                size *= dim
            total += reg.bitsize * size
    except Exception:
        total = 1  # Fallback: at least 1 qubit
    return total
