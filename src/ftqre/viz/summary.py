"""Rich console summary tables for resource estimates."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from ftqre.core.results import PhysicalEstimate


def print_estimate_summary(
    estimate: PhysicalEstimate, console: Console | None = None
) -> None:
    """Print a compact summary table to the terminal."""
    if console is None:
        console = Console()

    table = Table(
        title=f"Resource Estimate: {estimate.algorithm_spec.name}",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Metric", style="cyan", min_width=28)
    table.add_column("Value", style="green", justify="right")

    table.add_row("Physical Qubits (total)", f"{estimate.total_physical_qubits:,}")
    table.add_row("  Algorithm", f"{estimate.physical_qubits_for_algorithm:,}")
    table.add_row("  T Factories", f"{estimate.physical_qubits_for_t_factories:,}")
    table.add_row("Runtime", estimate.runtime_human)
    table.add_row("rQOPS", f"{estimate.rqops:,.0f}")
    table.add_row("Code Distance", str(estimate.logical_qubit.code_distance))
    table.add_row("Logical Qubits", str(estimate.algorithmic_logical_qubits))
    table.add_row("T States", f"{estimate.num_t_states:,}")
    table.add_row(
        "Space-Time Volume", f"{estimate.space_time_volume:.2e} qubit-seconds"
    )
    table.add_row("Error Budget", f"{estimate.error_budget.total:.1e}")
    table.add_row(
        "  Logical / Distill / Rotation",
        f"{estimate.error_budget.logical:.1e} / "
        f"{estimate.error_budget.distillation:.1e} / "
        f"{estimate.error_budget.rotation:.1e}",
    )
    table.add_row("QEC Scheme", estimate.qec_scheme_name)
    table.add_row("Hardware", estimate.hardware_model.name)
    table.add_row("Backend", estimate.backend_name)

    console.print(table)


def print_estimate_detail(
    estimate: PhysicalEstimate, console: Console | None = None
) -> None:
    """Print the full detailed breakdown."""
    if console is None:
        console = Console()

    print_estimate_summary(estimate, console)

    # Logical qubit details
    lq = estimate.logical_qubit
    console.print()
    detail = Table(title="Logical Qubit Details", show_header=True)
    detail.add_column("Property", style="cyan")
    detail.add_column("Value", style="green", justify="right")
    detail.add_row("Code Distance", str(lq.code_distance))
    detail.add_row("Physical Qubits / Logical", f"{lq.physical_qubits:,}")
    detail.add_row("Logical Cycle Time", f"{lq.logical_cycle_time:.2e} s")
    detail.add_row("Logical Error Rate", f"{lq.logical_error_rate:.2e}")
    console.print(detail)

    # T factory details
    if estimate.t_factory:
        tf = estimate.t_factory
        console.print()
        tf_table = Table(title="T Factory Details", show_header=True)
        tf_table.add_column("Property", style="cyan")
        tf_table.add_column("Value", style="green", justify="right")
        tf_table.add_row("Number of Factories", str(tf.num_factories))
        tf_table.add_row("Qubits / Factory", f"{tf.physical_qubits_per_factory:,}")
        tf_table.add_row("Total Factory Qubits", f"{tf.total_physical_qubits:,}")
        tf_table.add_row("Factory Runtime", f"{tf.factory_runtime:.2e} s")
        tf_table.add_row("Distillation Rounds", str(tf.num_rounds))
        tf_table.add_row("Output Error Rate", f"{tf.output_error_rate:.2e}")
        console.print(tf_table)
