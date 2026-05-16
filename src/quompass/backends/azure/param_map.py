"""Map quompass types to Azure QRE parameter dictionaries.

Converts HardwareModel, QECScheme, and ErrorBudget into the nested
dict structure expected by ``qsharp.estimate()``.

All qsharp imports are lazy.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quompass.core.error_budget import ErrorBudget
    from quompass.core.hardware import HardwareModel
    from quompass.core.qec import QECScheme


def build_params(
    hardware: HardwareModel,
    qec: QECScheme,
    error_budget: ErrorBudget,
) -> dict:
    """Build Azure QRE EstimatorParams dict.

    Parameters
    ----------
    hardware : HardwareModel
    qec : QECScheme
    error_budget : ErrorBudget

    Returns
    -------
    dict
        Nested dict for ``qsharp.estimate(..., params=...)``.
    """
    params: dict = {}
    params["qubitParams"] = _map_qubit_params(hardware)
    params["qecScheme"] = _map_qec_scheme(qec)
    params["errorBudget"] = _map_error_budget(error_budget)
    return params


def _map_qubit_params(hardware: HardwareModel) -> dict:
    """Map QubitParams to Azure qubitParams dict.

    Azure QRE uses different parameter sets for gate-based vs Majorana qubits.
    Gate-based: oneQubitGateTime/ErrorRate, twoQubitGateTime/ErrorRate, etc.
    Majorana: oneQubitMeasurementTime/ErrorRate, twoQubitJointMeasurement*, tGate*.
    Sending gate-based fields to a Majorana instruction set causes an error.
    """
    from quompass.core.types import InstructionSet

    qp = hardware.qubit_params

    result: dict = {
        "name": qp.name,
        "instructionSet": qp.instruction_set.value,
        "oneQubitMeasurementTime": _seconds_to_azure_time(qp.one_qubit_measurement_time),
        "oneQubitMeasurementErrorRate": qp.one_qubit_measurement_error_rate,
        "tGateTime": _seconds_to_azure_time(qp.t_gate_time),
        "tGateErrorRate": qp.t_gate_error_rate,
    }

    if qp.instruction_set == InstructionSet.GATE_BASED:
        result["oneQubitGateTime"] = _seconds_to_azure_time(qp.one_qubit_gate_time)
        result["twoQubitGateTime"] = _seconds_to_azure_time(qp.two_qubit_gate_time)
        result["oneQubitGateErrorRate"] = qp.one_qubit_gate_error_rate
        result["twoQubitGateErrorRate"] = qp.two_qubit_gate_error_rate

    if qp.idle_error_rate is not None:
        result["idleErrorRate"] = qp.idle_error_rate

    if qp.two_qubit_joint_measurement_time is not None:
        result["twoQubitJointMeasurementTime"] = _seconds_to_azure_time(
            qp.two_qubit_joint_measurement_time
        )
    if qp.two_qubit_joint_measurement_error_rate is not None:
        result["twoQubitJointMeasurementErrorRate"] = (
            qp.two_qubit_joint_measurement_error_rate
        )

    return result


def _map_qec_scheme(qec: QECScheme) -> dict:
    """Map QECScheme to Azure qecScheme dict."""
    from quompass.core.qec import FloquetCode, FormulaQEC, SurfaceCode

    # Azure has named presets for surface_code and floquet_code
    if isinstance(qec, SurfaceCode):
        return {"name": "surface_code"}
    if isinstance(qec, FloquetCode):
        return {"name": "floquet_code"}

    # FormulaQEC or custom -- use Azure's custom QEC scheme format
    result: dict = {
        "name": qec.name,
        "errorCorrectionThreshold": qec.error_correction_threshold,
        "crossingPrefactor": qec.crossing_prefactor,
        "logicalCycleTime": f"(4 * twoQubitGateTime + 2 * oneQubitMeasurementTime) * codeDistance",
        "physicalQubitsPerLogicalQubit": f"2 * codeDistance * codeDistance",
    }

    if isinstance(qec, FormulaQEC):
        # Translate quompass formula variables to Azure formula variables.
        # Use regex word boundaries to avoid corrupting function names
        # like "round" or "ード" when replacing "d" with "codeDistance".
        # Replace longer variable names first to prevent partial matches.
        cycle_formula = qec.cycle_time_formula
        cycle_formula = re.sub(r'\bt_meas\b', 'oneQubitMeasurementTime', cycle_formula)
        cycle_formula = re.sub(r'\bt_2q\b', 'twoQubitGateTime', cycle_formula)
        cycle_formula = re.sub(r'\bt_1q\b', 'oneQubitGateTime', cycle_formula)
        cycle_formula = re.sub(r'\bt_jm\b', 'twoQubitJointMeasurementTime', cycle_formula)
        cycle_formula = re.sub(r'\bd\b', 'codeDistance', cycle_formula)
        result["logicalCycleTime"] = cycle_formula

        qubits_formula = qec.qubits_formula
        qubits_formula = re.sub(r'\bd\b', 'codeDistance', qubits_formula)
        result["physicalQubitsPerLogicalQubit"] = qubits_formula

    return result


def _map_error_budget(error_budget: ErrorBudget) -> float:
    """Map ErrorBudget to Azure errorBudget value.

    Azure QRE accepts a float for the total error budget.
    """
    return error_budget.total


def _seconds_to_azure_time(seconds: float) -> str:
    """Convert seconds to Azure time string.

    Azure QRE accepts time strings like "50 ns", "100 us", "1 ms".

    Examples
    --------
    >>> _seconds_to_azure_time(50e-9)
    '50 ns'
    >>> _seconds_to_azure_time(100e-6)
    '100 us'
    >>> _seconds_to_azure_time(1e-3)
    '1000 us'
    """
    if seconds < 1e-6:
        # Nanoseconds
        ns = seconds * 1e9
        if ns == int(ns):
            return f"{int(ns)} ns"
        return f"{ns:.3g} ns"
    elif seconds < 1e-3:
        # Microseconds
        us = seconds * 1e6
        if us == int(us):
            return f"{int(us)} us"
        return f"{us:.3g} us"
    else:
        # Milliseconds
        ms = seconds * 1e3
        if ms == int(ms):
            return f"{int(ms)} ms"
        return f"{ms:.3g} ms"
