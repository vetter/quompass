#!/usr/bin/env python3
"""quompass Quick Start Examples

Run this script to see quompass in action:
    python examples/quick_start.py
"""

import quompass
from quompass.templates.shor import shor
from quompass.templates.chemistry import chemistry
from quompass.exploration import ExplorationSpace, explore


def basic_estimation():
    """Example 1: One-shot estimation for Shor's algorithm."""
    print("=" * 60)
    print("Example 1: Basic Estimation (Shor's Algorithm)")
    print("=" * 60)

    spec = shor(n_bits=2048)
    result = quompass.estimate(spec)

    print(f"Algorithm: {result.algorithm_spec.name}")
    print(f"Physical qubits: {result.total_physical_qubits:,}")
    print(f"  Algorithm: {result.physical_qubits_for_algorithm:,}")
    print(f"  T factories: {result.physical_qubits_for_t_factories:,}")
    print(f"Runtime: {result.runtime_human}")
    print(f"Code distance: {result.logical_qubit.code_distance}")
    print(f"Logical error rate: {result.logical_qubit.logical_error_rate:.2e}")
    print()


def compare_hardware():
    """Example 2: Compare hardware targets."""
    print("=" * 60)
    print("Example 2: Comparing Hardware Targets")
    print("=" * 60)

    spec = chemistry(num_orbitals=54, method="double_factorization")

    for hw in ["gate_ns_e3", "gate_ns_e4", "gate_us_e3"]:
        result = quompass.estimate(spec, hardware=hw, qec="surface_code")
        print(
            f"  {hw:12s}: {result.total_physical_qubits:>12,} qubits, "
            f"{result.runtime_human:>10}, distance={result.logical_qubit.code_distance}"
        )
    print()


def design_space_exploration():
    """Example 3: Full design space exploration with Pareto front and sensitivity."""
    print("=" * 60)
    print("Example 3: Design Space Exploration")
    print("=" * 60)

    space = ExplorationSpace(
        algorithm=shor(n_bits=2048),
        hardware=["gate_ns_e3", "gate_ns_e4", "gate_us_e3"],
        qec=["surface_code", "color_code"],
        error_budgets=[0.01, 0.001, 0.0001],
    )

    print(f"Exploring {space.size} combinations...\n")
    result = explore(space)

    # Print full results table
    result.print_table()
    print()

    # Pareto front
    front = result.pareto_front()
    front.print_table()
    print()

    # Best single point
    best = result.best()
    print(f"Best configuration: {best.label()}")
    print(f"  Physical qubits: {best.total_physical_qubits:,.0f}")
    print(f"  Runtime: {best.estimate.runtime_human}")
    print()

    # Sensitivity analysis
    sens = result.sensitivity()
    sens.print_table()
    print(f"\nMost sensitive parameter: {sens.most_sensitive_dimension()}")
    print()


def custom_algorithm():
    """Example 4: Custom algorithm specification."""
    print("=" * 60)
    print("Example 4: Custom Algorithm Spec")
    print("=" * 60)

    from quompass.core.algorithm import AlgorithmSpec, LogicalCounts

    spec = AlgorithmSpec(
        name="My Custom Algorithm",
        logical_counts=LogicalCounts(
            num_qubits=100,
            t_count=1_000_000,
            ccz_count=500_000,
            measurement_count=100,
        ),
    )

    result = quompass.estimate(spec)
    print(f"Algorithm: {result.algorithm_spec.name}")
    print(f"Physical qubits: {result.total_physical_qubits:,}")
    print(f"Runtime: {result.runtime_human}")
    print()


def custom_qec():
    """Example 5: Custom QEC scheme via FormulaQEC."""
    print("=" * 60)
    print("Example 5: Custom QEC Scheme (FormulaQEC)")
    print("=" * 60)

    from quompass import FormulaQEC

    # Define a hypothetical code with linear qubit overhead
    my_code = FormulaQEC(
        name="my_qldpc",
        threshold=0.01,
        prefactor=0.03,
        qubits_formula="12 * d",
        cycle_time_formula="6 * t_2q * d",
    )

    spec = shor(n_bits=2048)

    for qec in ["surface_code", my_code]:
        qec_name = qec if isinstance(qec, str) else qec.name
        result = quompass.estimate(spec, qec=qec)
        print(
            f"  {qec_name:15s}: {result.total_physical_qubits:>12,} qubits, "
            f"distance={result.logical_qubit.code_distance}"
        )
    print()


if __name__ == "__main__":
    basic_estimation()
    compare_hardware()
    custom_algorithm()
    custom_qec()
    design_space_exploration()
