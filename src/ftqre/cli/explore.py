"""The 'ftqre explore' CLI command."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

console = Console()


def explore_cmd(
    template: str = typer.Option(
        ..., help="Algorithm template name (e.g. 'shor')"
    ),
    param: list[str] = typer.Option(
        [], help="Template parameters as key=value (repeatable)"
    ),
    hardware: str = typer.Option(
        "gate_ns_e3,gate_us_e3",
        help="Comma-separated hardware preset names",
    ),
    qec: str = typer.Option(
        "surface_code",
        help="Comma-separated QEC scheme names",
    ),
    error_budget: str = typer.Option(
        "0.001",
        help="Comma-separated error budget values",
    ),
    output: str = typer.Option(
        "table",
        help="Output format: table, pareto, json, detail",
    ),
    pareto_x: str = typer.Option(
        "total_physical_qubits",
        help="Pareto front X objective",
    ),
    pareto_y: str = typer.Option(
        "runtime_seconds",
        help="Pareto front Y objective",
    ),
    plot: Optional[str] = typer.Option(
        None,
        help="Save plot to file path (requires matplotlib)",
    ),
    sensitivity: bool = typer.Option(
        False,
        help="Run and display sensitivity analysis",
    ),
) -> None:
    """Explore the design space for a quantum algorithm."""
    from ftqre.cli.estimate import _parse_params
    from ftqre.exploration import ExplorationSpace, explore
    from ftqre.templates.registry import get_template

    # Build algorithm spec from template
    tmpl = get_template(template)
    params = _parse_params(param, tmpl.parameter_schema())
    algorithm = tmpl.generate(**params)

    # Parse comma-separated lists
    hw_list = [h.strip() for h in hardware.split(",")]
    qec_list = [q.strip() for q in qec.split(",")]
    eb_list = [float(e.strip()) for e in error_budget.split(",")]

    space = ExplorationSpace(
        algorithm=algorithm,
        hardware=hw_list,
        qec=qec_list,
        error_budgets=eb_list,
    )

    console.print(
        f"[bold]Exploring {space.size} combinations[/bold] "
        f"for {algorithm.name}..."
    )

    # Run with progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Evaluating...", total=space.size)

        def _on_progress(completed: int, total: int) -> None:
            progress.update(task, completed=completed)

        result = explore(space, progress_callback=_on_progress)

    console.print()

    # Output
    if output == "json":
        import json

        rows = []
        for pt in result.succeeded:
            rows.append(pt.estimate.summary_dict())
        console.print_json(json.dumps(rows, indent=2, default=str))

    elif output == "pareto":
        front = result.pareto_front(
            objectives={pareto_x: "minimize", pareto_y: "minimize"}
        )
        front.print_table(console=console)

    elif output == "detail":
        result.print_table(console=console)
        console.print()
        front = result.pareto_front(
            objectives={pareto_x: "minimize", pareto_y: "minimize"}
        )
        front.print_table(console=console)

    else:  # "table"
        result.print_table(console=console)

    # Optional sensitivity analysis
    if sensitivity:
        console.print()
        sens = result.sensitivity()
        sens.print_table(console=console)

    # Optional plot
    if plot:
        try:
            result.plot(
                x=pareto_x, y=pareto_y,
                show_pareto=True,
                save_path=plot,
            )
            console.print(f"[green]Plot saved to {plot}[/green]")
        except ImportError as e:
            console.print(f"[yellow]Warning:[/yellow] {e}")
