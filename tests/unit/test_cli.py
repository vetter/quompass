"""CLI smoke tests using typer.testing.CliRunner."""

import pytest
from typer.testing import CliRunner

from quompass.cli.main import app

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


class TestEstimateOutputFormats:
    def test_json_output(self):
        result = runner.invoke(
            app,
            ["estimate", "--template", "shor", "--param", "n_bits=64", "--output", "json"],
        )
        assert result.exit_code == 0
        assert "total_physical_qubits" in result.stdout

    def test_yaml_output(self):
        result = runner.invoke(
            app,
            ["estimate", "--template", "shor", "--param", "n_bits=64", "--output", "yaml"],
        )
        assert result.exit_code == 0
        assert "total_physical_qubits" in result.stdout

    def test_detail_output(self):
        result = runner.invoke(
            app,
            ["estimate", "--template", "shor", "--param", "n_bits=64", "--output", "detail"],
        )
        assert result.exit_code == 0
        assert "Logical Qubit" in result.stdout

    def test_different_hardware_preset(self):
        result = runner.invoke(
            app,
            ["estimate", "--template", "shor", "--param", "n_bits=64", "--hardware", "gate_us_e3"],
        )
        assert result.exit_code == 0

    def test_different_qec_scheme(self):
        result = runner.invoke(
            app,
            ["estimate", "--template", "shor", "--param", "n_bits=64", "--qec", "floquet_code"],
        )
        assert result.exit_code == 0


class TestEstimateErrorPaths:
    def test_invalid_template_name(self):
        result = runner.invoke(
            app, ["estimate", "--template", "nonexistent", "--param", "n_bits=64"]
        )
        assert result.exit_code != 0

    def test_bad_param_format(self):
        result = runner.invoke(
            app, ["estimate", "--template", "shor", "--param", "bad_param_no_equals"]
        )
        assert result.exit_code != 0


class TestExploreOptions:
    def test_explore_multiple_hardware(self):
        result = runner.invoke(
            app,
            [
                "explore",
                "--template", "shor",
                "--param", "n_bits=64",
                "--hardware", "gate_ns_e3,gate_ns_e4",
            ],
        )
        assert result.exit_code == 0

    def test_explore_with_qec(self):
        result = runner.invoke(
            app,
            [
                "explore",
                "--template", "shor",
                "--param", "n_bits=64",
                "--hardware", "gate_ns_e3",
                "--qec", "surface_code",
            ],
        )
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
