"""CLI smoke tests using typer.testing.CliRunner."""

import pytest
from typer.testing import CliRunner

from ftqre.cli.main import app

runner = CliRunner()


class TestEstimateCLI:
    def test_estimate_with_template(self):
        result = runner.invoke(app, ["estimate", "--template", "shor", "--param", "n_bits=64"])
        assert result.exit_code == 0

    def test_estimate_no_args_fails(self):
        result = runner.invoke(app, ["estimate"])
        assert result.exit_code != 0


class TestExploreCLI:
    def test_explore_with_template(self):
        result = runner.invoke(
            app,
            [
                "explore",
                "--template", "shor",
                "--param", "n_bits=64",
                "--hardware", "gate_ns_e3",
            ],
        )
        assert result.exit_code == 0


class TestCatalogCLI:
    def test_catalog_templates(self):
        result = runner.invoke(app, ["catalog", "templates"])
        assert result.exit_code == 0
        assert "shor" in result.stdout

    def test_catalog_hardware(self):
        result = runner.invoke(app, ["catalog", "hardware"])
        assert result.exit_code == 0

    def test_catalog_qec(self):
        result = runner.invoke(app, ["catalog", "qec"])
        assert result.exit_code == 0

    def test_catalog_backends(self):
        result = runner.invoke(app, ["catalog", "backends"])
        assert result.exit_code == 0


class TestOptimizeCLI:
    @pytest.mark.optimize
    def test_optimize_with_template(self):
        result = runner.invoke(
            app,
            [
                "optimize",
                "--template", "shor",
                "--param", "n_bits=64",
                "--hardware", "gate_ns_e3",
                "--generations", "2",
                "--population-size", "10",
            ],
        )
        assert result.exit_code == 0
