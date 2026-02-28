"""Tests for backend registry and discovery."""

from ftqre.backends.registry import (
    discover_logical_estimators,
    discover_physical_estimators,
    select_backends,
)


class TestDiscovery:
    def test_discover_logical_has_mock(self):
        estimators = discover_logical_estimators()
        assert "mock" in estimators
        assert estimators["mock"].is_available()

    def test_discover_physical_has_analytical(self):
        estimators = discover_physical_estimators()
        assert "analytical" in estimators
        assert estimators["analytical"].is_available()


class TestSelectBackends:
    def test_auto_selects_available(self):
        le, pe = select_backends("auto", "auto")
        assert le.is_available()
        assert pe.is_available()

    def test_explicit_mock(self):
        le, pe = select_backends("mock", "analytical")
        assert le.name == "mock"
        assert pe.name == "analytical"

    def test_unknown_logical_raises(self):
        import pytest

        with pytest.raises(ValueError, match="Unknown logical backend"):
            select_backends("nonexistent", "auto")

    def test_unknown_physical_raises(self):
        import pytest

        with pytest.raises(ValueError, match="Unknown physical backend"):
            select_backends("auto", "nonexistent")
