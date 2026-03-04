"""CLI entry point for quompass."""

from __future__ import annotations

import typer

from quompass.cli.catalog import catalog_app
from quompass.cli.estimate import estimate_cmd
from quompass.cli.explore import explore_cmd
from quompass.cli.optimize import optimize_cmd

app = typer.Typer(
    name="quompass",
    help="Portable Fault-Tolerant Quantum Resource Estimation",
    no_args_is_help=True,
    add_completion=False,
)

app.command("estimate")(estimate_cmd)
app.command("explore")(explore_cmd)
app.command("optimize")(optimize_cmd)
app.add_typer(catalog_app, name="catalog")


if __name__ == "__main__":
    app()
