"""Tests for new algorithm templates (QPE, Hamiltonian sim, chemistry, Grover)."""

import pytest

from quompass.templates.qpe import QPETemplate, qpe
from quompass.templates.hamiltonian_sim import HamiltonianSimTemplate, hamiltonian_sim
from quompass.templates.chemistry import ChemistryTemplate, chemistry
from quompass.templates.grover import GroverTemplate, grover
from quompass.templates.registry import get_template, list_templates


# ---------------------------------------------------------------------------
# QPE
# ---------------------------------------------------------------------------
class TestQPETemplate:
    def test_basic(self):
        spec = qpe(num_qubits=10, precision_bits=20)
        assert spec.name.startswith("QPE")
        assert spec.algorithm_family == "phase_estimation"
        assert spec.logical_counts.num_qubits == 10 + 20 + 1
        assert spec.logical_counts.t_count > 0
        assert spec.source == "template:qpe"

    def test_scaling(self):
        s1 = qpe(num_qubits=10, precision_bits=10)
        s2 = qpe(num_qubits=10, precision_bits=20)
        # More precision bits -> more T gates
        assert s2.logical_counts.t_count > s1.logical_counts.t_count

    def test_qubit_scaling(self):
        s1 = qpe(num_qubits=10, precision_bits=20)
        s2 = qpe(num_qubits=50, precision_bits=20)
        assert s2.logical_counts.num_qubits > s1.logical_counts.num_qubits
        assert s2.logical_counts.t_count > s1.logical_counts.t_count

    def test_parameter_schema(self):
        tmpl = QPETemplate()
        schema = tmpl.parameter_schema()
        assert "num_qubits" in schema
        assert "precision_bits" in schema
        assert schema["num_qubits"]["default"] == 10

    def test_has_rotations(self):
        spec = qpe(num_qubits=10, precision_bits=20)
        # QPE should have rotations from inverse QFT
        assert spec.logical_counts.rotation_count > 0


# ---------------------------------------------------------------------------
# Hamiltonian Simulation
# ---------------------------------------------------------------------------
class TestHamiltonianSimTemplate:
    def test_trotter(self):
        spec = hamiltonian_sim(num_qubits=20, method="trotter")
        assert "Trotter" in spec.name
        assert spec.algorithm_family == "simulation"
        assert spec.logical_counts.num_qubits == 20
        assert spec.logical_counts.t_count > 0
        assert spec.source == "template:hamiltonian_sim"

    def test_qsp(self):
        spec = hamiltonian_sim(num_qubits=20, method="qsp")
        assert "QSP" in spec.name
        # QSP needs ancilla qubits
        assert spec.logical_counts.num_qubits > 20

    def test_qubitization(self):
        spec = hamiltonian_sim(num_qubits=20, method="qubitization")
        assert "qubitization" in spec.name
        assert spec.logical_counts.num_qubits > 20

    def test_invalid_method(self):
        with pytest.raises(ValueError, match="Unknown method"):
            hamiltonian_sim(method="invalid")

    def test_time_scaling(self):
        s1 = hamiltonian_sim(evolution_time=1.0, method="trotter")
        s2 = hamiltonian_sim(evolution_time=10.0, method="trotter")
        # Longer time -> more gates
        assert s2.logical_counts.t_count > s1.logical_counts.t_count

    def test_precision_scaling(self):
        s1 = hamiltonian_sim(precision=1e-2, method="trotter")
        s2 = hamiltonian_sim(precision=1e-6, method="trotter")
        # Tighter precision -> more gates
        assert s2.logical_counts.t_count > s1.logical_counts.t_count

    def test_qsp_is_more_efficient_than_trotter(self):
        """QSP should generally use fewer T-gates than Trotter for the same problem."""
        s_trotter = hamiltonian_sim(
            num_qubits=20, num_terms=100, evolution_time=10.0,
            precision=1e-4, method="trotter"
        )
        s_qsp = hamiltonian_sim(
            num_qubits=20, num_terms=100, evolution_time=10.0,
            precision=1e-4, method="qsp"
        )
        # QSP has better asymptotic scaling in time
        assert s_qsp.logical_counts.total_t_equivalent < s_trotter.logical_counts.total_t_equivalent

    def test_parameter_schema(self):
        tmpl = HamiltonianSimTemplate()
        schema = tmpl.parameter_schema()
        assert "num_qubits" in schema
        assert "method" in schema
        assert "trotter" in schema["method"]["choices"]


# ---------------------------------------------------------------------------
# Chemistry
# ---------------------------------------------------------------------------
class TestChemistryTemplate:
    def test_double_factorization(self):
        spec = chemistry(num_orbitals=54, method="double_factorization")
        assert "DF" in spec.name
        assert spec.algorithm_family == "chemistry"
        assert spec.logical_counts.num_qubits > 0
        assert spec.logical_counts.ccz_count > 0
        assert spec.source == "template:chemistry"

    def test_thc(self):
        spec = chemistry(num_orbitals=54, method="thc")
        assert "THC" in spec.name
        assert spec.logical_counts.ccz_count > 0

    def test_sparse(self):
        spec = chemistry(num_orbitals=54, method="sparse")
        assert "Sparse" in spec.name
        assert spec.logical_counts.ccz_count > 0

    def test_invalid_method(self):
        with pytest.raises(ValueError, match="Unknown method"):
            chemistry(method="invalid")

    def test_orbital_scaling(self):
        s1 = chemistry(num_orbitals=20, method="double_factorization")
        s2 = chemistry(num_orbitals=100, method="double_factorization")
        # More orbitals -> more resources
        assert s2.logical_counts.num_qubits > s1.logical_counts.num_qubits
        assert s2.logical_counts.ccz_count > s1.logical_counts.ccz_count

    def test_default_electrons(self):
        """With num_electrons=0, should auto-fill."""
        spec = chemistry(num_orbitals=54, num_electrons=0)
        assert spec.problem_parameters["num_electrons"] == 54

    def test_parameter_schema(self):
        tmpl = ChemistryTemplate()
        schema = tmpl.parameter_schema()
        assert "num_orbitals" in schema
        assert "method" in schema
        assert "double_factorization" in schema["method"]["choices"]

    def test_femo_benchmark(self):
        """FeMoCo-scale problem (108 orbitals) should produce reasonable numbers."""
        spec = chemistry(num_orbitals=108, method="double_factorization")
        # Should need > 200 qubits (2*108 + ancilla)
        assert spec.logical_counts.num_qubits >= 216
        # Should need substantial Toffoli count
        assert spec.logical_counts.ccz_count > 100_000


# ---------------------------------------------------------------------------
# Grover
# ---------------------------------------------------------------------------
class TestGroverTemplate:
    def test_basic(self):
        spec = grover(search_space_bits=20)
        assert spec.name.startswith("Grover")
        assert spec.algorithm_family == "search"
        assert spec.logical_counts.num_qubits > 0
        assert spec.logical_counts.t_count > 0
        assert spec.source == "template:grover"

    def test_scaling(self):
        s1 = grover(search_space_bits=10)
        s2 = grover(search_space_bits=20)
        # Grover scales as sqrt(N) iterations, so 20 bits needs ~32x more
        assert s2.logical_counts.t_count > s1.logical_counts.t_count

    def test_multiple_solutions(self):
        s1 = grover(search_space_bits=20, num_solutions=1)
        s2 = grover(search_space_bits=20, num_solutions=100)
        # More solutions -> fewer iterations -> fewer T gates
        assert s2.logical_counts.t_count < s1.logical_counts.t_count

    def test_custom_oracle(self):
        spec = grover(search_space_bits=20, num_oracle_t_gates=1000)
        assert spec.logical_counts.t_count > 0
        assert spec.problem_parameters["num_oracle_t_gates"] == 1000

    def test_iterations_stored(self):
        spec = grover(search_space_bits=20)
        assert spec.problem_parameters["num_iterations"] > 0

    def test_parameter_schema(self):
        tmpl = GroverTemplate()
        schema = tmpl.parameter_schema()
        assert "search_space_bits" in schema
        assert "num_solutions" in schema
        assert schema["search_space_bits"]["default"] == 20


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
class TestNewTemplateRegistry:
    def test_all_templates_listed(self):
        templates = list_templates()
        assert "shor" in templates
        assert "qpe" in templates
        assert "hamiltonian_sim" in templates
        assert "chemistry" in templates
        assert "grover" in templates

    def test_get_each_template(self):
        for name in ["shor", "qpe", "hamiltonian_sim", "chemistry", "grover"]:
            tmpl = get_template(name)
            assert tmpl.name == name
