"""Tests for serialization (to_dict / from_dict) of core types."""

from quompass.core.error_budget import ErrorBudget, ErrorBudgetBreakdown
from quompass.core.hardware import HardwareModel, QubitParams
from quompass.core.results import LogicalQubitEstimate, TFactoryEstimate
from quompass.core.types import InstructionSet


class TestQubitParamsSerialization:
    def test_round_trip_gate_based(self):
        params = QubitParams(
            name="test_gate",
            instruction_set=InstructionSet.GATE_BASED,
            one_qubit_gate_time=50e-9,
            two_qubit_gate_time=50e-9,
            one_qubit_measurement_time=100e-9,
            t_gate_time=50e-9,
            one_qubit_gate_error_rate=1e-3,
            two_qubit_gate_error_rate=1e-3,
            one_qubit_measurement_error_rate=1e-3,
            t_gate_error_rate=1e-3,
        )
        d = params.to_dict()
        restored = QubitParams.from_dict(d)
        assert restored == params
        assert d["instruction_set"] == "gate_based"

    def test_round_trip_majorana(self):
        params = QubitParams(
            name="test_maj",
            instruction_set=InstructionSet.MAJORANA,
            one_qubit_gate_time=100e-9,
            two_qubit_gate_time=100e-9,
            one_qubit_measurement_time=100e-9,
            t_gate_time=100e-9,
            one_qubit_gate_error_rate=1e-4,
            two_qubit_gate_error_rate=1e-4,
            one_qubit_measurement_error_rate=1e-4,
            t_gate_error_rate=0.05,
            idle_error_rate=1e-5,
            two_qubit_joint_measurement_time=100e-9,
            two_qubit_joint_measurement_error_rate=1e-4,
        )
        d = params.to_dict()
        restored = QubitParams.from_dict(d)
        assert restored == params
        assert d["instruction_set"] == "majorana"
        assert "idle_error_rate" in d
        assert "two_qubit_joint_measurement_time" in d

    def test_optional_fields_omitted(self):
        params = QubitParams(
            name="minimal",
            instruction_set=InstructionSet.GATE_BASED,
            one_qubit_gate_time=50e-9,
            two_qubit_gate_time=50e-9,
            one_qubit_measurement_time=100e-9,
            t_gate_time=50e-9,
            one_qubit_gate_error_rate=1e-3,
            two_qubit_gate_error_rate=1e-3,
            one_qubit_measurement_error_rate=1e-3,
            t_gate_error_rate=1e-3,
        )
        d = params.to_dict()
        assert "idle_error_rate" not in d
        assert "two_qubit_joint_measurement_time" not in d
        assert "two_qubit_joint_measurement_error_rate" not in d


class TestHardwareModelSerialization:
    def test_round_trip(self):
        hw = HardwareModel.from_preset("gate_ns_e3")
        d = hw.to_dict()
        restored = HardwareModel.from_dict(d)
        assert restored.name == hw.name
        assert restored.qubit_params == hw.qubit_params
        assert restored.description == hw.description

    def test_custom_hardware(self):
        params = QubitParams(
            name="custom",
            instruction_set=InstructionSet.GATE_BASED,
            one_qubit_gate_time=25e-9,
            two_qubit_gate_time=40e-9,
            one_qubit_measurement_time=80e-9,
            t_gate_time=40e-9,
            one_qubit_gate_error_rate=1e-5,
            two_qubit_gate_error_rate=1e-5,
            one_qubit_measurement_error_rate=1e-5,
            t_gate_error_rate=1e-5,
        )
        hw = HardwareModel(name="custom_hw", qubit_params=params, description="test")
        d = hw.to_dict()
        restored = HardwareModel.from_dict(d)
        assert restored == hw


class TestErrorBudgetBreakdownSerialization:
    def test_round_trip(self):
        eb = ErrorBudgetBreakdown(total=0.001, logical=0.0004, distillation=0.0003, rotation=0.0003)
        d = eb.to_dict()
        restored = ErrorBudgetBreakdown.from_dict(d)
        assert restored == eb

    def test_dict_keys(self):
        eb = ErrorBudgetBreakdown(total=0.01, logical=0.005, distillation=0.003, rotation=0.002)
        d = eb.to_dict()
        assert set(d.keys()) == {"total", "logical", "distillation", "rotation"}


class TestErrorBudgetSerialization:
    def test_round_trip_defaults(self):
        eb = ErrorBudget(total=0.001)
        d = eb.to_dict()
        restored = ErrorBudget.from_dict(d)
        assert restored.total == eb.total
        assert restored.logical is None

    def test_round_trip_custom_split(self):
        eb = ErrorBudget(total=0.01, logical=0.005, distillation=0.003, rotation=0.002)
        d = eb.to_dict()
        restored = ErrorBudget.from_dict(d)
        assert restored.total == eb.total
        assert restored.logical == eb.logical
        assert restored.distillation == eb.distillation
        assert restored.rotation == eb.rotation

    def test_optional_fields_omitted(self):
        eb = ErrorBudget(total=0.001)
        d = eb.to_dict()
        assert "logical" not in d
        assert "distillation" not in d
        assert "rotation" not in d


class TestLogicalQubitEstimateSerialization:
    def test_to_dict(self):
        lq = LogicalQubitEstimate(
            code_distance=15,
            physical_qubits=450,
            logical_cycle_time=1.5e-5,
            logical_error_rate=1e-12,
        )
        d = lq.to_dict()
        assert d["code_distance"] == 15
        assert d["physical_qubits"] == 450
        assert d["logical_cycle_time"] == 1.5e-5
        assert d["logical_error_rate"] == 1e-12


class TestTFactoryEstimateSerialization:
    def test_to_dict(self):
        tf = TFactoryEstimate(
            num_factories=4,
            physical_qubits_per_factory=3200,
            total_physical_qubits=12800,
            factory_runtime=5e-4,
            num_rounds=15,
            output_error_rate=1e-8,
        )
        d = tf.to_dict()
        assert d["num_factories"] == 4
        assert d["physical_qubits_per_factory"] == 3200
        assert d["total_physical_qubits"] == 12800
        assert d["factory_runtime"] == 5e-4
        assert d["num_rounds"] == 15
        assert d["output_error_rate"] == 1e-8


class TestPhysicalEstimateSerialization:
    def test_to_dict_structure(self):
        """PhysicalEstimate.to_dict() returns expected nested structure."""
        import quompass
        from quompass.templates.shor import shor

        spec = shor(n_bits=64)
        result = quompass.estimate(spec)
        d = result.to_dict()

        # Top-level keys
        assert "summary" in d
        assert "breakdown" in d
        assert "logical_qubit" in d
        assert "t_factory" in d
        assert "error_budget" in d
        assert "error_rates" in d
        assert "provenance" in d

        # Summary fields
        assert d["summary"]["total_physical_qubits"] == result.total_physical_qubits
        assert d["summary"]["runtime_seconds"] == result.runtime_seconds
        assert d["summary"]["rqops"] == result.rqops

        # Provenance
        assert d["provenance"]["qec_scheme"] == result.qec_scheme_name
        assert d["provenance"]["backend"] == result.backend_name
        assert d["provenance"]["algorithm"]["name"] == result.algorithm_spec.name

    def test_to_dict_no_t_factory(self):
        """PhysicalEstimate with no T factory serializes t_factory as None."""
        from quompass.core.algorithm import AlgorithmSpec, LogicalCounts
        import quompass

        spec = AlgorithmSpec(
            name="No T gates",
            logical_counts=LogicalCounts(num_qubits=10, t_count=0, measurement_count=10),
        )
        result = quompass.estimate(spec)
        d = result.to_dict()
        assert d["t_factory"] is None
