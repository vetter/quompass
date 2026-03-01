"""The 'ftqre estimate' CLI command."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

console = Console()


def estimate_cmd(
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
        "gate_ns_e3", help="Hardware preset name or YAML file path (.yaml/.yml)"
    ),
    qec: str = typer.Option(
        "surface_code", help="QEC scheme name or YAML file path (.yaml/.yml)"
    ),
    error_budget: float = typer.Option(0.001, help="Total error budget"),
    output: str = typer.Option(
        "table", help="Output format: table, json, yaml, detail"
    ),
) -> None:
    """Estimate physical resources for a quantum algorithm."""
    import ftqre
    from ftqre.templates.registry import get_template
    from ftqre.viz.summary import print_estimate_detail, print_estimate_summary

    # Build algorithm spec
    if template:
        tmpl = get_template(template)
        params = _parse_params(param, tmpl.parameter_schema())
        algorithm = tmpl.generate(**params)
    elif spec:
        import yaml

        with open(spec) as f:
            data = yaml.safe_load(f)
        algorithm = ftqre.AlgorithmSpec.from_dict(data)
    else:
        console.print(
            "[red]Error:[/red] Provide either --template or --spec", style="bold"
        )
        raise typer.Exit(1)

    # Resolve hardware: YAML file or preset name
    hw_arg: ftqre.HardwareModel | str = hardware
    if hardware.endswith((".yaml", ".yml")):
        from ftqre.io import load_hardware

        hw_arg = load_hardware(hardware)

    # Resolve QEC: YAML file or scheme name
    qec_arg: ftqre.QECScheme | str = qec
    if qec.endswith((".yaml", ".yml")):
        from ftqre.io import load_qec

        qec_arg = load_qec(qec)

    # Run estimation
    try:
        result = ftqre.estimate(
            algorithm,
            hardware=hw_arg,
            qec=qec_arg,
            error_budget=error_budget,
        )
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}", style="bold")
        raise typer.Exit(1)

    # Output
    if output == "json":
        import json

        console.print_json(json.dumps(result.summary_dict(), indent=2, default=str))
    elif output == "yaml":
        import yaml

        console.print(yaml.dump(result.to_dict(), default_flow_style=False, sort_keys=False))
    elif output == "detail":
        print_estimate_detail(result, console)
    else:
        print_estimate_summary(result, console)


def _parse_params(
    raw_params: list[str], schema: dict
) -> dict:
    """Parse key=value parameter strings using the template schema for typing."""
    params: dict = {}
    for item in raw_params:
        if "=" not in item:
            console.print(
                f"[red]Error:[/red] Invalid parameter '{item}'. Use key=value format.",
                style="bold",
            )
            raise typer.Exit(1)
        key, value = item.split("=", 1)
        if key in schema:
            param_type = schema[key].get("type", "str")
            if param_type == "int":
                params[key] = int(value)
            elif param_type == "float":
                params[key] = float(value)
            else:
                params[key] = value
        else:
            params[key] = value
    return params
