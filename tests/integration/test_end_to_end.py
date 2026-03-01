"""End-to-end integration tests for the full estimation pipeline."""

import ftqre
from ftqre.core.algorithm import AlgorithmSpec, LogicalCounts
from ftqre.core.qec import color_code
from ftqre.templates.shor import shor
from ftqre.io import load_algorithm, save_estimate, save_yaml


class TestEndToEnd:
    def test_shor_default(self):
        """Full pipeline: template -> logical -> physical."""
        spec = shor(n_bits=64)
        result = ftqre.estimate(spec)
        assert result.total_physical_qubits > 0
        assert result.runtime_seconds > 0
        assert result.logical_qubit.code_distance % 2 == 1

    def test_custom_algorithm(self):
        """Manual algorithm spec through the pipeline."""
        spec = AlgorithmSpec(
            name="Custom QPE",
            logical_counts=LogicalCounts(
                num_qubits=50,
                t_count=10000,
                rotation_count=500,
                rotation_depth=100,
            ),
            algorithm_family="simulation",
        )
        result = ftqre.estimate(spec, hardware="gate_us_e3", qec="surface_code")
        assert result.total_physical_qubits > 0
        assert result.hardware_model.name == "gate_us_e3"

    def test_with_color_code(self):
        """Pipeline with FormulaQEC (color code)."""
        spec = AlgorithmSpec(
            name="Test",
            logical_counts=LogicalCounts(num_qubits=10, t_count=100),
        )
        result = ftqre.estimate(spec, qec=color_code())
        assert result.total_physical_qubits > 0
        assert result.qec_scheme_name == "color_code"

    def test_color_code_by_name(self):
        """Pipeline with color code looked up by name."""
        spec = AlgorithmSpec(
            name="Test",
            logical_counts=LogicalCounts(num_qubits=10, t_count=100),
        )
        result = ftqre.estimate(spec, qec="color_code")
        assert result.qec_scheme_name == "color_code"

    def test_different_hardware_targets(self):
        """Same algorithm on different hardware should give different results."""
        spec = shor(n_bits=64)
        r_sc = ftqre.estimate(spec, hardware="gate_ns_e3")
        r_ion = ftqre.estimate(spec, hardware="gate_us_e3")
        # Trapped ion has slower gates, so runtime should be longer
        assert r_ion.runtime_seconds > r_sc.runtime_seconds

    def test_yaml_round_trip(self, tmp_path):
        """Estimate -> save YAML -> load spec -> re-estimate -> compare."""
        spec = shor(n_bits=64)
        result1 = ftqre.estimate(spec)

        # Save spec as YAML, reload, re-estimate
        spec_path = tmp_path / "spec.yaml"
        save_yaml(spec.to_dict(), spec_path)
        loaded_spec = load_algorithm(spec_path)
        result2 = ftqre.estimate(loaded_spec)

        assert result2.total_physical_qubits == result1.total_physical_qubits
        assert result2.runtime_seconds == result1.runtime_seconds

        # Save result as YAML and verify it loads
        result_path = tmp_path / "result.yaml"
        save_estimate(result1, result_path)
        import yaml

        with open(result_path) as f:
            data = yaml.safe_load(f)
        assert data["summary"]["total_physical_qubits"] == result1.total_physical_qubits
