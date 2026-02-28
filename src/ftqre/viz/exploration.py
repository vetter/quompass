"""Visualization for design space exploration results.

Rich console tables (always available) and optional matplotlib plots
(requires matplotlib: pip install ftqre[viz]).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from ftqre.exploration.space import ExplorationResult, ParetoFront
    from ftqre.exploration.sensitivity import SensitivityResult


def print_exploration_table(
    result: ExplorationResult,
    console: Console | None = None,
) -> None:
    """Print a Rich table of all design points."""
    if console is None:
        console = Console()

    table = Table(
        title=f"Design Space Exploration: {result.space.algorithm.name}",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Hardware", style="cyan")
    table.add_column("QEC", style="yellow")
    table.add_column("Error Budget", style="green", justify="right")
    table.add_column("Physical Qubits", justify="right")
    table.add_column("Runtime", justify="right")
    table.add_column("Code Distance", justify="right")
    table.add_column("Space-Time Vol", justify="right")
    table.add_column("Status", justify="center")

    for pt in result.all_points:
        if pt.succeeded:
            est = pt.estimate
            table.add_row(
                pt.hardware_name,
                pt.qec_name,
                f"{pt.error_budget:.1e}",
                f"{est.total_physical_qubits:,}",
                est.runtime_human,
                str(est.logical_qubit.code_distance),
                f"{est.space_time_volume:.2e}",
                "[green]OK[/green]",
            )
        else:
            table.add_row(
                pt.hardware_name,
                pt.qec_name,
                f"{pt.error_budget:.1e}",
                "-", "-", "-", "-",
                "[red]FAIL[/red]",
            )

    console.print(table)
    console.print(
        f"\n{result.num_succeeded}/{len(result.all_points)} points succeeded, "
        f"{result.num_failed} failed."
    )


def print_pareto_table(
    front: ParetoFront,
    console: Console | None = None,
) -> None:
    """Print a Rich table of Pareto-optimal points."""
    if console is None:
        console = Console()

    obj_names = list(front.objectives.keys())
    table = Table(
        title=f"Pareto Front ({len(front)} points)",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("#", style="dim", justify="right")
    table.add_column("Hardware", style="cyan")
    table.add_column("QEC", style="yellow")
    table.add_column("Error Budget", style="green", justify="right")
    for obj_name in obj_names:
        direction = front.objectives[obj_name]
        arrow = "v" if direction == "minimize" else "^"
        table.add_column(f"{obj_name} ({arrow})", justify="right")

    for i, pt in enumerate(front.points, 1):
        row = [
            str(i),
            pt.hardware_name,
            pt.qec_name,
            f"{pt.error_budget:.1e}",
        ]
        for obj_name in obj_names:
            val = pt.metric(obj_name)
            if val > 1e6:
                row.append(f"{val:.2e}")
            else:
                row.append(f"{val:,.0f}")
        table.add_row(*row)

    console.print(table)


def print_sensitivity_table(
    sensitivity: SensitivityResult,
    console: Console | None = None,
) -> None:
    """Print a Rich table of sensitivity analysis results."""
    if console is None:
        console = Console()

    console.print(
        f"\n[bold]Sensitivity Analysis[/bold] "
        f"(metric: {sensitivity.metric}, "
        f"baseline: {sensitivity.baseline_value:,.0f})"
    )

    for dim_name, entries in sensitivity.dimensions.items():
        table = Table(
            title=f"Varying: {dim_name}",
            show_header=True,
            header_style="bold",
        )
        table.add_column(dim_name, style="cyan")
        table.add_column(sensitivity.metric, justify="right")
        table.add_column("% Change", justify="right")

        for entry in entries:
            pct_str = f"{entry.pct_change:+.1f}%"
            if entry.pct_change == 0:
                pct_str = f"[dim]{pct_str}[/dim] (baseline)"
            elif entry.pct_change < 0:
                pct_str = f"[green]{pct_str}[/green]"
            else:
                pct_str = f"[red]{pct_str}[/red]"

            val_str = (
                f"{entry.metric_value:,.0f}"
                if entry.metric_value < 1e9
                else f"{entry.metric_value:.2e}"
            )
            table.add_row(str(entry.param_value), val_str, pct_str)

        console.print(table)


def plot_exploration(
    result: ExplorationResult,
    *,
    x: str = "total_physical_qubits",
    y: str = "runtime_seconds",
    show_pareto: bool = True,
    save_path: str | None = None,
) -> Any:
    """Scatter plot of design points with optional Pareto front overlay."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError(
            "matplotlib is required for plotting. "
            "Install with: pip install ftqre[viz]"
        )

    fig, ax = plt.subplots(figsize=(10, 7))

    succeeded = result.succeeded
    x_vals = [pt.metric(x) for pt in succeeded]
    y_vals = [pt.metric(y) for pt in succeeded]

    # Color by hardware, marker by QEC
    hw_names = sorted(set(pt.hardware_name for pt in succeeded))
    qec_names = sorted(set(pt.qec_name for pt in succeeded))

    colors = plt.cm.tab10.colors
    markers = ["o", "s", "^", "D", "v", "P", "*", "X"]
    hw_color = {name: colors[i % len(colors)] for i, name in enumerate(hw_names)}
    qec_marker = {name: markers[i % len(markers)] for i, name in enumerate(qec_names)}

    for pt, xv, yv in zip(succeeded, x_vals, y_vals):
        ax.scatter(
            xv, yv,
            color=hw_color[pt.hardware_name],
            marker=qec_marker[pt.qec_name],
            s=80, alpha=0.7, edgecolors="black", linewidth=0.5,
        )

    # Legend entries
    from matplotlib.lines import Line2D

    legend_elements = []
    for name, c in hw_color.items():
        legend_elements.append(
            Line2D(
                [0], [0], marker="o", color="w", markerfacecolor=c,
                markersize=8, label=f"HW: {name}",
            )
        )
    for name, m in qec_marker.items():
        legend_elements.append(
            Line2D(
                [0], [0], marker=m, color="w", markerfacecolor="gray",
                markersize=8, label=f"QEC: {name}",
            )
        )

    if show_pareto:
        front = result.pareto_front(
            objectives={x: "minimize", y: "minimize"}
        )
        if len(front) > 1:
            fx = [pt.metric(x) for pt in front]
            fy = [pt.metric(y) for pt in front]
            sorted_pairs = sorted(zip(fx, fy))
            fx_s, fy_s = zip(*sorted_pairs)
            ax.plot(fx_s, fy_s, "r--", linewidth=2, alpha=0.8, label="Pareto front")
            ax.scatter(
                fx_s, fy_s, color="red", s=120, zorder=5,
                edgecolors="darkred", linewidth=1.5,
            )
            legend_elements.append(
                Line2D(
                    [0], [0], color="red", linestyle="--",
                    linewidth=2, label="Pareto front",
                )
            )

    ax.set_xlabel(x.replace("_", " ").title(), fontsize=12)
    ax.set_ylabel(y.replace("_", " ").title(), fontsize=12)
    ax.set_title(
        f"Design Space: {result.space.algorithm.name}",
        fontsize=14,
    )
    ax.legend(handles=legend_elements, loc="best", fontsize=9)
    ax.grid(True, alpha=0.3)

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def plot_sensitivity(
    sensitivity: SensitivityResult,
    *,
    save_path: str | None = None,
) -> Any:
    """Bar chart showing sensitivity of each parameter dimension."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError(
            "matplotlib is required for plotting. "
            "Install with: pip install ftqre[viz]"
        )

    dims = sensitivity.dimensions
    n_dims = len(dims)
    fig, axes = plt.subplots(1, n_dims, figsize=(5 * n_dims, 5))
    if n_dims == 1:
        axes = [axes]

    for ax, (dim_name, entries) in zip(axes, dims.items()):
        labels = [str(e.param_value) for e in entries]
        values = [e.pct_change for e in entries]
        bar_colors = ["green" if v <= 0 else "red" for v in values]
        ax.barh(labels, values, color=bar_colors, alpha=0.7)
        ax.axvline(x=0, color="black", linewidth=0.8)
        ax.set_xlabel("% Change from Baseline")
        ax.set_title(f"Sensitivity: {dim_name}")

    fig.suptitle(
        f"Sensitivity Analysis: {sensitivity.metric}",
        fontsize=14,
    )
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig
