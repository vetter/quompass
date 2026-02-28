"""Tests for algorithm templates."""

from ftqre.templates.shor import ShorTemplate, shor
from ftqre.templates.registry import get_template, list_templates


class TestShorTemplate:
    def test_gidney_ekera(self):
        spec = shor(n_bits=2048)
        assert spec.name.startswith("Shor")
        assert spec.algorithm_family == "cryptanalysis"
        assert spec.logical_counts.num_qubits > 0
        assert spec.logical_counts.ccz_count > 0
        assert spec.source == "template:shor"

    def test_textbook(self):
        spec = shor(n_bits=64, construction="textbook")
        assert "textbook" in spec.name
        assert spec.logical_counts.num_qubits == 2 * 64 + 3

    def test_scaling(self):
        s1 = shor(n_bits=512)
        s2 = shor(n_bits=1024)
        # More bits should require more qubits and more gates
        assert s2.logical_counts.num_qubits > s1.logical_counts.num_qubits
        assert s2.logical_counts.ccz_count > s1.logical_counts.ccz_count

    def test_parameter_schema(self):
        tmpl = ShorTemplate()
        schema = tmpl.parameter_schema()
        assert "n_bits" in schema
        assert schema["n_bits"]["type"] == "int"
        assert schema["n_bits"]["default"] == 2048

    def test_invalid_construction(self):
        import pytest

        with pytest.raises(ValueError, match="Unknown construction"):
            shor(construction="invalid")


class TestRegistry:
    def test_list_templates(self):
        templates = list_templates()
        assert "shor" in templates

    def test_get_template(self):
        tmpl = get_template("shor")
        assert tmpl.name == "shor"

    def test_get_unknown_template(self):
        import pytest

        with pytest.raises(ValueError, match="Unknown template"):
            get_template("nonexistent")
