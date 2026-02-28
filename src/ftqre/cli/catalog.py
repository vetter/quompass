"""The 'ftqre catalog' CLI command group."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

catalog_app = typer.Typer(
    help="Browse available templates, hardware presets, and QEC schemes.",
    no_args_is_help=True,
)
console = Console()


@catalog_app.command("templates")
def list_templates(
    name: str = typer.Argument(None, help="Show details for a specific template"),
) -> None:
    """List available algorithm templates."""
    from ftqre.templates.registry import list_templates as _list

    templates = _list()

    if name:
        if name not in templates:
            console.print(f"[red]Unknown template '{name}'[/red]")
            raise typer.Exit(1)
        tmpl = templates[name]
        console.print(f"[bold cyan]{tmpl.name}[/bold cyan] ({tmpl.family})")
        console.print(f"  {tmpl.description}")
        console.print()
        schema = tmpl.parameter_schema()
        if schema:
            table = Table(title="Parameters")
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="yellow")
            table.add_column("Default", style="green")
            table.add_column("Description")
            for pname, pinfo in schema.items():
                default = str(pinfo.get("default", ""))
                choices = pinfo.get("choices")
                desc = pinfo.get("description", "")
                if choices:
                    desc += f" [{', '.join(str(c) for c in choices)}]"
                table.add_row(pname, pinfo.get("type", ""), default, desc)
            console.print(table)
    else:
        table = Table(title="Algorithm Templates")
        table.add_column("Name", style="cyan")
        table.add_column("Family", style="yellow")
        table.add_column("Description")
        for tname, tmpl in sorted(templates.items()):
            table.add_row(tname, tmpl.family, tmpl.description)
        console.print(table)


@catalog_app.command("hardware")
def list_hardware() -> None:
    """List predefined hardware presets."""
    from ftqre.core.hardware import HardwareModel, _PRESET_DESCRIPTIONS
    from ftqre.core.types import HardwarePreset

    table = Table(title="Hardware Presets")
    table.add_column("Preset", style="cyan")
    table.add_column("Name", style="yellow")
    table.add_column("Description")
    for preset in HardwarePreset:
        hw = HardwareModel.from_preset(preset)
        table.add_row(preset.name, preset.value, _PRESET_DESCRIPTIONS[preset])
    console.print(table)


@catalog_app.command("qec")
def list_qec() -> None:
    """List available QEC schemes."""
    from ftqre.core.qec import _BUILTIN_SCHEMES

    table = Table(title="QEC Schemes")
    table.add_column("Name", style="cyan")
    table.add_column("Threshold", style="yellow", justify="right")
    table.add_column("Prefactor", style="green", justify="right")
    for name, cls in sorted(_BUILTIN_SCHEMES.items()):
        scheme = cls()
        table.add_row(
            name,
            f"{scheme.error_correction_threshold:.4f}",
            f"{scheme.crossing_prefactor:.4f}",
        )
    console.print(table)


@catalog_app.command("backends")
def list_backends() -> None:
    """List available estimation backends."""
    from ftqre.backends.mock import AnalyticalPhysicalEstimator, MockLogicalEstimator

    table = Table(title="Estimation Backends")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Available", style="green")

    le = MockLogicalEstimator()
    table.add_row(le.name, "logical", "yes" if le.is_available() else "no")

    pe = AnalyticalPhysicalEstimator()
    table.add_row(pe.name, "physical", "yes" if pe.is_available() else "no")

    console.print(table)
