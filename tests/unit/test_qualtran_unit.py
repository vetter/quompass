"""Unit tests for the Qualtran backend (adapter, bloq_bridge, cost_extract).

These tests do NOT require qualtran installed -- they mock the qualtran
imports to test the mapping logic and error handling in isolation.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from quompass.core.algorithm import AlgorithmSpec, LogicalCounts


# ---------------------------------------------------------------------------
# bloq_bridge tests
# ---------------------------------------------------------------------------


class TestSpecToBloq:
    def test_qualtran_source_format_valid(self):
        """Test fully-qualified qualtran: source parsing."""
        from quompass.backends.qualtran.bloq_bridge import _lookup_qualtran_bloq

        mock_cls = MagicMock(return_value="mock_bloq")
        mock_mod = MagicMock()
        mock_mod.MyBloq = mock_cls

        with patch("importlib.import_module", return_value=mock_mod):
            result = _lookup_qualtran_bloq("qualtran:my.module:MyBloq", {"n": 10})

        mock_cls.assert_called_once_with(n=10)
        assert result == "mock_bloq"

    def test_qualtran_source_format_invalid(self):
        from quompass.backends.qualtran.bloq_bridge import _lookup_qualtran_bloq

        with pytest.raises(ValueError, match="Invalid qualtran source format"):
            _lookup_qualtran_bloq("qualtran:just_one_part", {})

    def test_qualtran_source_module_not_found(self):
        from quompass.backends.qualtran.bloq_bridge import _lookup_qualtran_bloq

        with patch("importlib.import_module", side_effect=ImportError("no module")):
            with pytest.raises(ImportError, match="Cannot import Qualtran module"):
                _lookup_qualtran_bloq("qualtran:bad.module:Cls", {})

    def test_qualtran_source_class_not_found(self):
        from quompass.backends.qualtran.bloq_bridge import _lookup_qualtran_bloq

        mock_mod = MagicMock(spec=[])  # empty module
        with patch("importlib.import_module", return_value=mock_mod):
            with pytest.raises(ValueError, match="not found in module"):
                _lookup_qualtran_bloq("qualtran:my.module:Missing", {})

    def test_spec_to_bloq_unknown_family_raises(self):
        from quompass.backends.qualtran.bloq_bridge import spec_to_bloq

        spec = AlgorithmSpec(
            name="Unknown",
            logical_counts=LogicalCounts(num_qubits=5, t_count=10),
            algorithm_family="quantum_ml",
        )
        with pytest.raises(ValueError, match="Cannot map"):
            spec_to_bloq(spec)

    def test_spec_to_bloq_with_qualtran_source(self):
        from quompass.backends.qualtran.bloq_bridge import spec_to_bloq

        mock_cls = MagicMock(return_value="my_bloq")
        mock_mod = MagicMock()
        mock_mod.TestBloq = mock_cls

        spec = AlgorithmSpec(
            name="Test",
            logical_counts=LogicalCounts(num_qubits=5),
            source="qualtran:test.module:TestBloq",
            problem_parameters={"x": 42},
        )
        with patch("importlib.import_module", return_value=mock_mod):
            result = spec_to_bloq(spec)

        assert result == "my_bloq"
        mock_cls.assert_called_once_with(x=42)

    def test_family_builder_registry(self):
        """All template algorithm families are registered."""
        from quompass.backends.qualtran.bloq_bridge import _FAMILY_BUILDERS

        assert "cryptanalysis" in _FAMILY_BUILDERS
        assert "phase_estimation" in _FAMILY_BUILDERS
        assert "chemistry" in _FAMILY_BUILDERS
        assert "simulation" in _FAMILY_BUILDERS
        assert "search" in _FAMILY_BUILDERS


class TestFamilyBuilders:
    def test_shor_builder_constructs_bloq(self):
        """Shor builder should construct a Bloq if qualtran is installed,
        or raise ValueError/ImportError if not."""
        from quompass.backends.qualtran.bloq_bridge import _FAMILY_BUILDERS

        builder = _FAMILY_BUILDERS["cryptanalysis"]
        try:
            bloq = builder({"n_bits": 16})
            # If qualtran is installed, should get a Bloq back
            assert bloq is not None
        except (ImportError, ValueError):
            # Expected when qualtran is not installed
            pass

    def test_qpe_builder_raises(self):
        """QPE builder always raises (needs concrete unitary)."""
        from quompass.backends.qualtran.bloq_bridge import _FAMILY_BUILDERS

        builder = _FAMILY_BUILDERS["phase_estimation"]
        with pytest.raises(ValueError, match="concrete unitary"):
            builder({"num_qubits": 10, "precision_bits": 20})

    def test_chemistry_builder_raises(self):
        """Chemistry builder always raises (needs Hamiltonian data)."""
        from quompass.backends.qualtran.bloq_bridge import _FAMILY_BUILDERS

        builder = _FAMILY_BUILDERS["chemistry"]
        with pytest.raises(ValueError, match="Hamiltonian data"):
            builder({"method": "double_factorization", "num_orbitals": 54})

    def test_simulation_builder_raises(self):
        """Hamiltonian sim builder always raises (needs concrete Hamiltonian)."""
        from quompass.backends.qualtran.bloq_bridge import _FAMILY_BUILDERS

        builder = _FAMILY_BUILDERS["simulation"]
        with pytest.raises(ValueError, match="concrete Hamiltonian"):
            builder({"method": "trotter", "num_qubits": 50})

    def test_search_builder_raises(self):
        """Search builder always raises (needs problem-specific oracle)."""
        from quompass.backends.qualtran.bloq_bridge import _FAMILY_BUILDERS

        builder = _FAMILY_BUILDERS["search"]
        with pytest.raises(ValueError, match="problem-specific oracle"):
            builder({"search_space_bits": 20})


# ---------------------------------------------------------------------------
# cost_extract tests
# ---------------------------------------------------------------------------


class TestExtractLogicalCounts:
    def test_modern_api_success(self):
        """Test extraction via modern get_cost_value API."""
        import sys

        mock_bloq = MagicMock()

        # GateCounts is a dataclass with attributes and total_t_and_ccz_count()
        mock_gate_costs = MagicMock()
        mock_gate_costs.total_t_and_ccz_count.return_value = {"n_t": 100, "n_ccz": 50}
        mock_gate_costs.rotation = 10
        mock_gate_costs.measurement = 200

        mock_qubit_count = 42

        mock_rc = MagicMock()
        mock_rc.get_cost_value = MagicMock(side_effect=[mock_gate_costs, mock_qubit_count])
        mock_rc.QECGatesCost = MagicMock()
        mock_rc.QubitCount = MagicMock()

        with patch.dict(sys.modules, {"qualtran.resource_counting": mock_rc}):
            from quompass.backends.qualtran.cost_extract import _extract_via_cost_api

            result = _extract_via_cost_api(mock_bloq)

        assert result.num_qubits == 42
        assert result.t_count == 100
        assert result.ccz_count == 50
        assert result.rotation_count == 10
        assert result.measurement_count == 200

    def test_legacy_api_success(self):
        """Test extraction via legacy call_graph API."""
        import sys

        mock_tgate = type("TGate", (), {})()
        mock_toffoli = type("Toffoli", (), {})()
        mock_rz = type("Rz", (), {})()

        callee_counts = [
            (mock_tgate, 80),
            (mock_toffoli, 20),
            (mock_rz, 5),
        ]

        # Mock the bloq signature for qubit counting
        mock_reg = SimpleNamespace(bitsize=4, shape=(2,))
        mock_bloq = MagicMock()
        mock_bloq.signature = [mock_reg]

        mock_bg = MagicMock()
        mock_bg.TGate = type(mock_tgate)
        mock_bg.Toffoli = type(mock_toffoli)

        mock_rc = MagicMock()
        mock_rc.get_bloq_callee_counts = MagicMock(return_value=callee_counts)

        with patch.dict(sys.modules, {
            "qualtran.bloqs.basic_gates": mock_bg,
            "qualtran.resource_counting": mock_rc,
        }):
            from quompass.backends.qualtran.cost_extract import _extract_via_call_graph

            result = _extract_via_call_graph(mock_bloq)

        assert result.t_count == 80
        assert result.ccz_count == 20
        assert result.rotation_count == 5
        assert result.num_qubits == 8  # 4 bitsize * 2 shape

    def test_extract_falls_back_to_legacy(self):
        """extract_logical_counts falls back to call_graph when modern API fails."""
        import sys

        mock_bloq = MagicMock()
        mock_bloq.signature = []

        # Modern API raises
        mock_rc_modern = MagicMock()
        mock_rc_modern.get_cost_value = MagicMock(side_effect=AttributeError("no cost api"))
        mock_rc_modern.QECGatesCost = MagicMock()
        mock_rc_modern.QubitCount = MagicMock()
        mock_rc_modern.get_bloq_callee_counts = MagicMock(return_value=[])

        mock_bg = MagicMock()
        mock_bg.TGate = type("TGate", (), {})
        mock_bg.Toffoli = type("Toffoli", (), {})

        with patch.dict(sys.modules, {
            "qualtran.resource_counting": mock_rc_modern,
            "qualtran.bloqs.basic_gates": mock_bg,
        }):
            from quompass.backends.qualtran.cost_extract import extract_logical_counts

            result = extract_logical_counts(mock_bloq)

        # Should get fallback result with at least 1 qubit
        assert result.num_qubits >= 1


class TestCountQubitsFromSignature:
    def test_simple_register(self):
        from quompass.backends.qualtran.cost_extract import _count_qubits_from_signature

        reg = SimpleNamespace(bitsize=8, shape=())
        bloq = SimpleNamespace(signature=[reg])
        assert _count_qubits_from_signature(bloq) == 8

    def test_multi_dim_register(self):
        from quompass.backends.qualtran.cost_extract import _count_qubits_from_signature

        reg = SimpleNamespace(bitsize=4, shape=(3, 2))
        bloq = SimpleNamespace(signature=[reg])
        assert _count_qubits_from_signature(bloq) == 24  # 4 * 3 * 2

    def test_multiple_registers(self):
        from quompass.backends.qualtran.cost_extract import _count_qubits_from_signature

        reg1 = SimpleNamespace(bitsize=4, shape=())
        reg2 = SimpleNamespace(bitsize=2, shape=(3,))
        bloq = SimpleNamespace(signature=[reg1, reg2])
        assert _count_qubits_from_signature(bloq) == 10  # 4 + 2*3

    def test_broken_signature_returns_1(self):
        from quompass.backends.qualtran.cost_extract import _count_qubits_from_signature

        bloq = SimpleNamespace()  # no signature attribute
        assert _count_qubits_from_signature(bloq) == 1

    def test_empty_signature_returns_1(self):
        from quompass.backends.qualtran.cost_extract import _count_qubits_from_signature

        bloq = SimpleNamespace(signature=[])
        assert _count_qubits_from_signature(bloq) == 1


# ---------------------------------------------------------------------------
# adapter tests
# ---------------------------------------------------------------------------


class TestQualtranAdapter:
    def test_name(self):
        from quompass.backends.qualtran.adapter import QualtranLogicalEstimator

        est = QualtranLogicalEstimator()
        assert est.name == "qualtran"

    def test_is_available_without_qualtran(self):
        from quompass.backends.qualtran.adapter import QualtranLogicalEstimator

        est = QualtranLogicalEstimator()
        # Without qualtran installed, should return False
        # (may return True in CI if qualtran is installed)
        result = est.is_available()
        assert isinstance(result, bool)

    def test_estimate_falls_back_for_unmapped_family(self):
        from quompass.backends.qualtran.adapter import QualtranLogicalEstimator

        est = QualtranLogicalEstimator()
        spec = AlgorithmSpec(
            name="Unmappable",
            logical_counts=LogicalCounts(num_qubits=42, t_count=100),
            algorithm_family="quantum_ml",
        )
        counts = est.estimate(spec)
        # Should fall back to spec's counts
        assert counts.num_qubits == 42
        assert counts.t_count == 100

    def test_estimate_shor_uses_qualtran_or_fallback(self):
        """Shor estimate uses Qualtran Bloq if available, else falls back."""
        from quompass.backends.qualtran.adapter import QualtranLogicalEstimator

        est = QualtranLogicalEstimator()
        spec = AlgorithmSpec(
            name="Shor 16-bit",
            logical_counts=LogicalCounts(num_qubits=32, t_count=1000),
            algorithm_family="cryptanalysis",
            problem_parameters={"n_bits": 16},
        )
        counts = est.estimate(spec)
        if est.is_available():
            # With qualtran, should get Bloq-derived counts (different from spec)
            assert counts.num_qubits >= 1
            assert counts.total_t_equivalent > 0
        else:
            # Without qualtran, should fall back to spec counts
            assert counts.num_qubits == 32
            assert counts.t_count == 1000

    def test_estimate_from_bloq_delegates(self):
        """estimate_from_bloq calls extract_logical_counts."""
        from quompass.backends.qualtran.adapter import QualtranLogicalEstimator

        est = QualtranLogicalEstimator()
        mock_counts = LogicalCounts(num_qubits=10, t_count=50)

        with patch(
            "quompass.backends.qualtran.cost_extract.extract_logical_counts",
            return_value=mock_counts,
        ):
            result = est.estimate_from_bloq(MagicMock())

        assert result.num_qubits == 10
        assert result.t_count == 50
