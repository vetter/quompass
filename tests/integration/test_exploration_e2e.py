"""End-to-end integration tests for the exploration module."""

from ftqre.exploration import ExplorationSpace, explore
from ftqre.templates.shor import shor


class TestExplorationE2E:
    def test_full_exploration_workflow(self):
        """Complete workflow: space -> explore -> pareto -> sensitivity."""
        space = ExplorationSpace(
            algorithm=shor(n_bits=64),
            hardware=["gate_ns_e3", "gate_ns_e4", "gate_us_e3"],
            qec=["surface_code", "color_code"],
            error_budgets=[0.01, 0.001, 0.0001],
        )
        result = explore(space)

        # Should have attempted all 18 combinations
        assert len(result.all_points) == 18
        assert result.num_succeeded > 0

        # Pareto front
        front = result.pareto_front()
        assert len(front) > 0
        assert len(front) <= result.num_succeeded

        # Sensitivity
        sens = result.sensitivity()
        assert sens.baseline_value > 0

        # Best point
        best = result.best()
        assert best.succeeded

    def test_pareto_front_is_non_dominated(self):
        """Verify that no Pareto front point is dominated by any other."""
        space = ExplorationSpace(
            algorithm=shor(n_bits=64),
            hardware=["gate_ns_e3", "gate_ns_e4", "gate_us_e3"],
            qec=["surface_code", "color_code"],
            error_budgets=[0.01, 0.001],
        )
        result = explore(space)
        front = result.pareto_front()

        for i, pt_i in enumerate(front):
            for j, pt_j in enumerate(front):
                if i != j:
                    q_i = pt_i.total_physical_qubits
                    r_i = pt_i.runtime_seconds
                    q_j = pt_j.total_physical_qubits
                    r_j = pt_j.runtime_seconds
                    # pt_j should NOT dominate pt_i
                    assert not (
                        q_j <= q_i and r_j <= r_i and (q_j < q_i or r_j < r_i)
                    )

    def test_rich_table_output(self):
        """Verify table output does not crash."""
        from rich.console import Console

        console = Console(file=open("/dev/null", "w"))

        space = ExplorationSpace(
            algorithm=shor(n_bits=64),
            hardware=["gate_ns_e3"],
            qec=["surface_code"],
            error_budgets=[0.001],
        )
        result = explore(space)
        result.print_table(console=console)

        front = result.pareto_front()
        front.print_table(console=console)

    def test_exploration_result_methods(self):
        """Test ExplorationResult convenience methods."""
        space = ExplorationSpace(
            algorithm=shor(n_bits=64),
            hardware=["gate_ns_e3", "gate_ns_e4"],
            qec=["surface_code"],
            error_budgets=[0.001],
        )
        result = explore(space)

        assert len(result.succeeded) == result.num_succeeded
        assert len(result.failed) == result.num_failed
        assert result.num_succeeded + result.num_failed == len(result.all_points)

    def test_design_point_accessors(self):
        """Test DesignPoint metric and label accessors."""
        space = ExplorationSpace(
            algorithm=shor(n_bits=64),
            hardware=["gate_ns_e3"],
            qec=["surface_code"],
            error_budgets=[0.001],
        )
        result = explore(space)
        pt = result.all_points[0]

        assert pt.succeeded
        assert pt.label() == "gate_ns_e3/surface_code/eb=0.001"
        assert pt.metric("total_physical_qubits") > 0
        assert pt.metric("runtime_seconds") > 0
        assert pt.metric("space_time_volume") > 0
        assert pt.metric("code_distance") > 0


class TestExploreCLI:
    def test_explore_basic(self):
        from typer.testing import CliRunner
        from ftqre.cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, [
            "explore",
            "--template", "shor",
            "--param", "n_bits=64",
            "--hardware", "gate_ns_e3",
            "--qec", "surface_code",
            "--error-budget", "0.001",
        ])
        assert result.exit_code == 0

    def test_explore_pareto_output(self):
        from typer.testing import CliRunner
        from ftqre.cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, [
            "explore",
            "--template", "shor",
            "--param", "n_bits=64",
            "--hardware", "gate_ns_e3,gate_ns_e4",
            "--qec", "surface_code",
            "--error-budget", "0.01,0.001",
            "--output", "pareto",
        ])
        assert result.exit_code == 0

    def test_explore_with_sensitivity(self):
        from typer.testing import CliRunner
        from ftqre.cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, [
            "explore",
            "--template", "shor",
            "--param", "n_bits=64",
            "--hardware", "gate_ns_e3,gate_ns_e4",
            "--qec", "surface_code",
            "--error-budget", "0.01,0.001",
            "--sensitivity",
        ])
        assert result.exit_code == 0
