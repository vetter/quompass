"""Tests for quompass.io YAML load/save utilities."""

import yaml
import pytest
from pathlib import Path

import quompass
from quompass.core.algorithm import AlgorithmSpec, LogicalCounts
from quompass.core.hardware import HardwareModel, QubitParams
from quompass.core.qec import FormulaQEC
from quompass.core.types import InstructionSet
from quompass.io import (
    load_algorithm,
    load_hardware,
    load_qec,
    save_estimate,
    save_yaml,
)


class TestLoadAlgorithm:
    def test_load_from_file(self, tmp_path):
        spec = AlgorithmSpec(
            name="Test Algo",
            logical_counts=LogicalCounts(num_qubits=20, t_count=500),
            algorithm_family="test",
            problem_parameters={"size": 20},
        )
        path = tmp_path / "algo.yaml"
        with open(path, "w") as f:
            yaml.dump(spec.to_dict(), f)

        loaded = load_algorithm(path)
        assert loaded.name == spec.name
        assert loaded.logical_counts.num_qubits == 20
        assert loaded.logical_counts.t_count == 500
        assert loaded.algorithm_family == "test"

    def test_round_trip(self, tmp_path):
        spec = AlgorithmSpec(
            name="Round Trip",
            logical_counts=LogicalCounts(
                num_qubits=100,
                t_count=1000,
                rotation_count=50,
                rotation_depth=10,
                ccz_count=200,
                measurement_count=100,
                clifford_count=5000,
            ),
            description="A test algorithm",
            algorithm_family="simulation",
            problem_parameters={"n": 100, "method": "qsp"},
            source="test",
        )
        path = tmp_path / "spec.yaml"
        save_yaml(spec.to_dict(), path)
        loaded = load_algorithm(path)

        assert loaded.name == spec.name
        assert loaded.logical_counts.num_qubits == spec.logical_counts.num_qubits
        assert loaded.logical_counts.t_count == spec.logical_counts.t_count
        assert loaded.logical_counts.rotation_count == spec.logical_counts.rotation_count
        assert loaded.logical_counts.ccz_count == spec.logical_counts.ccz_count
        assert loaded.description == spec.description
        assert loaded.algorithm_family == spec.algorithm_family
        assert loaded.source == spec.source


class TestLoadHardware:
    def test_load_from_file(self, tmp_path):
        hw = HardwareModel.from_preset("gate_ns_e3")
        path = tmp_path / "hw.yaml"
        save_yaml(hw.to_dict(), path)
        loaded = load_hardware(path)
        assert loaded.name == hw.name
        assert loaded.qubit_params.one_qubit_gate_time == hw.qubit_params.one_qubit_gate_time
        assert loaded.qubit_params.instruction_set == InstructionSet.GATE_BASED

    def test_round_trip_custom(self, tmp_path):
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
        hw = HardwareModel(name="custom", qubit_params=params, description="test")
        path = tmp_path / "hw.yaml"
        save_yaml(hw.to_dict(), path)
        loaded = load_hardware(path)
        assert loaded.qubit_params == params


class TestLoadQEC:
    def test_load_from_file(self, tmp_path):
        qec = FormulaQEC(
            name="test_qldpc",
            threshold=0.01,
            prefactor=0.03,
            qubits_formula="12 * d",
            cycle_time_formula="6 * t_2q * d",
        )
        path = tmp_path / "qec.yaml"
        save_yaml(qec.to_dict(), path)
        loaded = load_qec(path)
        assert loaded.name == "test_qldpc"
        assert loaded.error_correction_threshold == 0.01
        assert loaded.crossing_prefactor == 0.03
        assert loaded.qubits_formula == "12 * d"
        assert loaded.cycle_time_formula == "6 * t_2q * d"

    def test_round_trip_with_distance_power(self, tmp_path):
        qec = FormulaQEC(
            name="power_code",
            threshold=0.005,
            prefactor=0.1,
            qubits_formula="ceil(4.5 * d * d)",
            cycle_time_formula="10 * t_2q * d",
            distance_coefficient_power=1.0,
        )
        path = tmp_path / "qec.yaml"
        save_yaml(qec.to_dict(), path)
        loaded = load_qec(path)
        assert loaded.distance_coefficient_power == 1.0


class TestSaveEstimate:
    def test_save_and_reload(self, tmp_path):
        from quompass.templates.shor import shor

        spec = shor(n_bits=64)
        result = quompass.estimate(spec)

        path = tmp_path / "result.yaml"
        save_estimate(result, path)

        with open(path) as f:
            data = yaml.safe_load(f)

        assert data["summary"]["total_physical_qubits"] == result.total_physical_qubits
        assert data["summary"]["runtime_seconds"] == result.runtime_seconds
        assert "provenance" in data
        assert "logical_qubit" in data


class TestSaveYaml:
    def test_save_and_load(self, tmp_path):
        data = {"key": "value", "number": 42, "nested": {"a": 1}}
        path = tmp_path / "test.yaml"
        save_yaml(data, path)

        with open(path) as f:
            loaded = yaml.safe_load(f)
        assert loaded == data
