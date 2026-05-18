"""Mock and analytical backends for offline estimation and testing."""

from __future__ import annotations

import math

from quompass.backends.base import LogicalEstimator, PhysicalEstimator
from quompass.core.algorithm import AlgorithmSpec, LogicalCounts
from quompass.core.error_budget import ErrorBudget, ErrorBudgetBreakdown
from quompass.core.hardware import HardwareModel
from quompass.core.qec import QECScheme
from quompass.core.results import (
    LogicalQubitEstimate,
    PhysicalEstimate,
    TFactoryEstimate,
)


class MockLogicalEstimator(LogicalEstimator):
    """Passes through LogicalCounts from AlgorithmSpec without transformation.

    Used for: unit tests, manual entry workflows, template-based estimation.
    """

    @property
    def name(self) -> str:
        return "mock"

    def estimate(self, spec: AlgorithmSpec) -> LogicalCounts:
        return spec.logical_counts

    def is_available(self) -> bool:
        return True


class AnalyticalPhysicalEstimator(PhysicalEstimator):
    """Analytical physical estimation using QECScheme methods directly.

    Does NOT call any external backend. Uses the QECScheme's own
    formulas for code distance, physical qubits, cycle time.
    Provides a simplified T-factory model.

    Used for: unit tests, offline estimation, fallback when no backend available.
    """

    @property
    def name(self) -> str:
        return "analytical"

    def is_available(self) -> bool:
        return True

    def estimate(
        self,
        logical_counts: LogicalCounts,
        hardware: HardwareModel,
        qec: QECScheme,
        error_budget: ErrorBudget,
        algorithm_spec: AlgorithmSpec,
    ) -> PhysicalEstimate:
        budget = error_budget.resolve(has_rotations=logical_counts.has_rotations)
        p = hardware.qubit_params.worst_case_clifford_error
        transversal = qec.transversal_magic_states

        n_logical = logical_counts.num_qubits
        if transversal:
            # Transversal architecture: T and CCZ/Toffoli are native logical
            # gates -- one logical cycle each, no distillation. A CCZ is NOT
            # expanded into 4 T equivalents.
            n_nonclifford = (
                logical_counts.t_count
                + logical_counts.ccz_count
                + logical_counts.rotation_count
            )
        else:
            n_nonclifford = logical_counts.total_t_equivalent

        # Required logical error rate: total logical error budget spread
        # across all logical qubits and all logical cycles
        logical_depth = max(n_nonclifford, 1)
        required_logical_rate = budget.logical / (n_logical * logical_depth)

        # Find minimum code distance
        d = qec.min_code_distance(required_logical_rate, p)

        # Compute physical qubit costs for algorithm
        phys_per_logical = qec.physical_qubits_per_logical(d)
        algo_physical = n_logical * phys_per_logical

        # Logical cycle time
        cycle_time = qec.logical_cycle_time(d, hardware.qubit_params)

        # T factory estimation (simplified model). Transversal codes produce
        # magic states in-place via cultivation -- no dedicated factory.
        if transversal:
            t_factory = None
        else:
            t_factory = self._estimate_t_factories(
                logical_counts, hardware, qec, d, budget
            )

        # Runtime
        runtime = logical_depth * cycle_time

        total_physical = algo_physical + (
            t_factory.total_physical_qubits if t_factory else 0
        )

        # rQOPS = logical qubits * clock frequency
        clock_freq = 1.0 / cycle_time if cycle_time > 0 else 0.0

        logical_error_rate = qec.logical_error_rate(d, p)

        required_t_state_rate = (
            0.0
            if transversal or n_nonclifford == 0
            else budget.distillation / n_nonclifford
        )

        return PhysicalEstimate(
            total_physical_qubits=total_physical,
            runtime_seconds=runtime,
            rqops=n_logical * clock_freq,
            algorithmic_logical_qubits=n_logical,
            physical_qubits_for_algorithm=algo_physical,
            physical_qubits_for_t_factories=(
                t_factory.total_physical_qubits if t_factory else 0
            ),
            logical_qubit=LogicalQubitEstimate(
                code_distance=d,
                physical_qubits=phys_per_logical,
                logical_cycle_time=cycle_time,
                logical_error_rate=logical_error_rate,
            ),
            t_factory=t_factory,
            algorithmic_logical_depth=logical_depth,
            num_t_states=n_nonclifford,
            clock_frequency=clock_freq,
            error_budget=budget,
            required_logical_error_rate=required_logical_rate,
            required_t_state_error_rate=required_t_state_rate,
            algorithm_spec=algorithm_spec,
            hardware_model=hardware,
            qec_scheme_name=qec.name,
            backend_name=self.name,
        )

    def _estimate_t_factories(
        self,
        logical_counts: LogicalCounts,
        hardware: HardwareModel,
        qec: QECScheme,
        code_distance: int,
        budget: ErrorBudgetBreakdown,
    ) -> TFactoryEstimate | None:
        """Simplified T-factory estimation.

        Uses a basic 15-to-1 distillation model. Real backends (Azure QRE)
        perform full multi-level distillation pipeline optimization.
        """
        n_t_states = logical_counts.total_t_equivalent
        if n_t_states == 0:
            return None

        required_output_error = budget.distillation / n_t_states
        p_in = hardware.qubit_params.t_gate_error_rate

        # 15-to-1 distillation: output error ~ 35 * p_in^3
        # Number of rounds needed to reach target output error
        rounds = 1
        p_out = 35.0 * p_in**3
        while p_out > required_output_error and rounds < 5:
            rounds += 1
            p_out = 35.0 * p_out**3

        # Physical qubits per factory: roughly 15^rounds * physical_per_logical
        phys_per_logical = qec.physical_qubits_per_logical(code_distance)
        qubits_per_factory = int(15**rounds * phys_per_logical * 0.5)
        qubits_per_factory = max(qubits_per_factory, phys_per_logical)

        # Factory runtime: distillation takes ~code_distance logical cycles
        cycle_time = qec.logical_cycle_time(code_distance, hardware.qubit_params)
        factory_runtime = code_distance * cycle_time * rounds

        # Number of factories: enough to produce T states within algorithm runtime
        algorithm_runtime = max(n_t_states, 1) * cycle_time
        if factory_runtime > 0:
            t_per_factory = algorithm_runtime / factory_runtime
            num_factories = max(1, math.ceil(n_t_states / max(t_per_factory, 1)))
        else:
            num_factories = 1

        # Cap at reasonable number
        num_factories = min(num_factories, n_t_states)

        return TFactoryEstimate(
            num_factories=num_factories,
            physical_qubits_per_factory=qubits_per_factory,
            total_physical_qubits=num_factories * qubits_per_factory,
            factory_runtime=factory_runtime,
            num_rounds=rounds,
            output_error_rate=p_out,
        )
