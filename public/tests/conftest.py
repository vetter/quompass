"""Shared test fixtures."""

import pytest

from quompass.core.algorithm import AlgorithmSpec, LogicalCounts
from quompass.core.error_budget import ErrorBudget
from quompass.core.hardware import HardwareModel
from quompass.core.qec import SurfaceCode
from quompass.core.types import HardwarePreset


@pytest.fixture
def shor_2048_spec():
    """Known logical counts for Shor's 2048-bit factoring (Gidney-Ekera)."""
    return AlgorithmSpec(
        name="Shor 2048",
        logical_counts=LogicalCounts(
            num_qubits=4142,
            t_count=12,
            rotation_count=12,
            rotation_depth=12,
            ccz_count=2_576_980_377,
            measurement_count=4096,
        ),
        algorithm_family="cryptanalysis",
        problem_parameters={"n_bits": 2048},
        source="template:shor",
    )


@pytest.fixture
def small_algorithm_spec():
    """A small algorithm for fast unit tests."""
    return AlgorithmSpec(
        name="Small test algorithm",
        logical_counts=LogicalCounts(
            num_qubits=10,
            t_count=100,
            ccz_count=50,
            measurement_count=20,
        ),
        algorithm_family="test",
    )


@pytest.fixture
def superconducting_hw():
    return HardwareModel.from_preset(HardwarePreset.SUPERCONDUCTING_REALISTIC)


@pytest.fixture
def trapped_ion_hw():
    return HardwareModel.from_preset(HardwarePreset.TRAPPED_ION_REALISTIC)


@pytest.fixture
def surface_code():
    return SurfaceCode()


@pytest.fixture
def default_error_budget():
    return ErrorBudget(total=0.001)
