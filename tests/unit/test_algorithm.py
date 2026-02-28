"""Tests for core algorithm types."""

from ftqre.core.algorithm import AlgorithmSpec, LogicalCounts


class TestLogicalCounts:
    def test_frozen(self):
        lc = LogicalCounts(num_qubits=10, t_count=100)
        # Should be immutable
        try:
            lc.num_qubits = 20  # type: ignore
            assert False, "Should have raised"
        except AttributeError:
            pass

    def test_total_t_equivalent(self):
        lc = LogicalCounts(
            num_qubits=10, t_count=100, ccz_count=50, rotation_count=30
        )
        # 100 + 4*50 + 30 = 330
        assert lc.total_t_equivalent == 330

    def test_total_t_equivalent_zero(self):
        lc = LogicalCounts(num_qubits=10)
        assert lc.total_t_equivalent == 0

    def test_has_rotations(self):
        lc_with = LogicalCounts(num_qubits=10, rotation_count=5)
        lc_without = LogicalCounts(num_qubits=10)
        assert lc_with.has_rotations
        assert not lc_without.has_rotations

    def test_to_dict(self):
        lc = LogicalCounts(
            num_qubits=10, t_count=100, ccz_count=50, measurement_count=20
        )
        d = lc.to_dict()
        assert d["numQubits"] == 10
        assert d["tCount"] == 100
        assert d["cczCount"] == 50
        assert d["measurementCount"] == 20

    def test_hashable(self):
        lc1 = LogicalCounts(num_qubits=10, t_count=100)
        lc2 = LogicalCounts(num_qubits=10, t_count=100)
        assert hash(lc1) == hash(lc2)
        assert lc1 == lc2
        s = {lc1, lc2}
        assert len(s) == 1


class TestAlgorithmSpec:
    def test_round_trip(self):
        spec = AlgorithmSpec(
            name="Test",
            logical_counts=LogicalCounts(num_qubits=10, t_count=100),
            algorithm_family="test",
            problem_parameters={"n": 42},
            source="manual",
        )
        d = spec.to_dict()
        spec2 = AlgorithmSpec.from_dict(d)
        assert spec2.name == spec.name
        assert spec2.logical_counts.num_qubits == spec.logical_counts.num_qubits
        assert spec2.logical_counts.t_count == spec.logical_counts.t_count
        assert spec2.problem_parameters == spec.problem_parameters

    def test_from_dict_minimal(self):
        d = {"name": "Minimal", "logical_counts": {"num_qubits": 5}}
        spec = AlgorithmSpec.from_dict(d)
        assert spec.name == "Minimal"
        assert spec.logical_counts.num_qubits == 5
        assert spec.logical_counts.t_count == 0
