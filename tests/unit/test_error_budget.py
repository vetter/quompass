"""Tests for error budget distribution."""

from quompass.core.error_budget import ErrorBudget


class TestErrorBudget:
    def test_uniform_with_rotations(self):
        eb = ErrorBudget(total=0.003)
        breakdown = eb.resolve(has_rotations=True)
        assert breakdown.total == 0.003
        assert abs(breakdown.logical - 0.001) < 1e-10
        assert abs(breakdown.distillation - 0.001) < 1e-10
        assert abs(breakdown.rotation - 0.001) < 1e-10

    def test_uniform_without_rotations(self):
        eb = ErrorBudget(total=0.002)
        breakdown = eb.resolve(has_rotations=False)
        assert breakdown.total == 0.002
        assert abs(breakdown.logical - 0.001) < 1e-10
        assert abs(breakdown.distillation - 0.001) < 1e-10
        assert breakdown.rotation == 0.0

    def test_custom_split(self):
        eb = ErrorBudget(total=0.01, logical=0.005, distillation=0.003, rotation=0.002)
        breakdown = eb.resolve()
        assert breakdown.logical == 0.005
        assert breakdown.distillation == 0.003
        assert breakdown.rotation == 0.002
