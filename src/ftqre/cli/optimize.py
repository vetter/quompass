"""The 'ftqre optimize' CLI command."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

console = Console()


def optimize_cmd(
    template: Optional[str] = typer.Option(
        None, help="Algorithm template name (e.g. 'shor')"
    ),
    spec: Optional[str] = typer.Option(
        None, help="Path to algorithm spec YAML file"
    ),
    param: list[str] = typer.Option(
        [], help="Template parameters as key=value (repeatable)"
    ),
    hardware: str = typer.Option(
        "gate_ns_e3,gate_ns_e4",
        help="Comma-separated hardware preset names",
    ),
    qec: str = typer.Option(
        "surface_code",
        help="Comma-separated QEC scheme names",
    ),
    error_budget_min: float = typer.Option(
        0.0001,
        help="Minimum error budget (continuous range lower bound)",
    ),
    error_budget_max: float = typer.Option(
        0.1,
        help="Maximum error budget (continuous range upper bound)",
    ),
    objective: list[str] = typer.Option(
        [],
        help="Objectives as 'metric:direction' (repeatable, e.g. 'total_physical_qubits:minimize')",
    ),
    generations: int = typer.Option(
        50, help="Number of NSGA-II generations"
    ),
    population_size: int = typer.Option(
        100, help="Population size per generation"
    ),
    seed: Optional[int] = typer.Option(
        None, help="Random seed for reproducibility"
    ),
    output: str = typer.Option(
        "table",
        help="Output format: table, pareto, json, yaml",
    ),
    plot: Optional[str] = typer.Option(
        None,
        help="Save plot to file path (requires matplotlib)",
    ),
) -> None:
    """Run NSGA-II multi-objective optimization across the design space."""
    import ftqre as ftqre_mod
    from ftqre.cli.estimate import _parse_params
    from ftqre.optimization import OptimizationSpace, optimize
    from ftqre.templates.registry import get_template

    # Build algorithm spec from template or YAML
    if template:
        tmpl = get_template(template)
        params = _parse_params(param, tmpl.parameter_schema())
        algorithm = tmpl.generate(**params)
    elif spec:
        import yaml

        with open(spec) as f:
            data = yaml.safe_load(f)
        algorithm = ftqre_mod.AlgorithmSpec.from_dict(data)
    else:
        console.print(
            "[red]Error:[/red] Provide either --template or --spec", style="bold"
        )
        raise typer.Exit(1)

    # Parse comma-separated lists
    hw_list = [h.strip() for h in hardware.split(",")]
    qec_list = [q.strip() for q in qec.split(",")]

    # Parse objectives
    objectives: dict[str, str] = {}
    if objective:
        for obj_str in objective:
            if ":" not in obj_str:
                console.print(
                    f"[red]Error:[/red] Invalid objective '{obj_str}'. "
                    "Use 'metric:direction' format (e.g. 'total_physical_qubits:minimize').",
                    style="bold",
                )
                raise typer.Exit(1)
            metric_name, direction = obj_str.rsplit(":", 1)
            objectives[metric_name] = direction

    space = OptimizationSpace(
        algorithm=algorithm,
        hardware=hw_list,
        qec=qec_list,
        error_budget_range=(error_budget_min, error_budget_max),
        **({"objectives": objectives} if objectives else {}),
    )

    console.print(
        f"[bold]Optimizing[/bold] {algorithm.name} "
        f"({generations} generations, pop={population_size})..."
    )

    # Run with progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Optimizing...", total=generations)

        def _on_progress(gen: int, total: int) -> None:
            progress.update(task, completed=gen)

        try:
            result = optimize(
                space,
                generations=generations,
                population_size=population_size,
                seed=seed,
                progress_callback=_on_progress,
            )
        except ImportError as e:
            console.print(f"[red]Error:[/red] {e}", style="bold")
            raise typer.Exit(1)

    console.print()
    n_succeeded = len(result.succeeded)
    console.print(
        f"[green]Done![/green] {n_succeeded} successful evaluations "
        f"from {result.n_evaluations} total."
    )
    console.print()

    # Output
    if output == "json":
        import json

        rows = []
        for pt in result.succeeded:
            rows.append(pt.estimate.summary_dict())
        console.print_json(json.dumps(rows, indent=2, default=str))

    elif output == "yaml":
        import yaml

        rows = [pt.estimate.summary_dict() for pt in result.succeeded]
        console.print(yaml.dump(rows, default_flow_style=False, sort_keys=False))

    elif output == "pareto":
        front = result.pareto_front()
        front.print_table(console=console)

    else:  # "table"
        result.print_table(console=console)

    # Optional plot
    if plot:
        try:
            result.plot(show_pareto=True, save_path=plot)
            console.print(f"[green]Plot saved to {plot}[/green]")
        except ImportError as e:
            console.print(f"[yellow]Warning:[/yellow] {e}")
