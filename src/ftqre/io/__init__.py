"""YAML I/O utilities for ftqre.

Provides convenience functions for loading algorithm specs, hardware models,
and QEC schemes from YAML files, and saving estimation results.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ftqre.core.algorithm import AlgorithmSpec
from ftqre.core.hardware import HardwareModel, QubitParams
from ftqre.core.qec import FormulaQEC
from ftqre.core.results import PhysicalEstimate


def load_algorithm(path: str | Path) -> AlgorithmSpec:
    """Load an AlgorithmSpec from a YAML file.

    Parameters
    ----------
    path : str or Path
        Path to YAML file with algorithm spec data.

    Returns
    -------
    AlgorithmSpec
    """
    with open(path) as f:
        data = yaml.safe_load(f)
    return AlgorithmSpec.from_dict(data)


def load_hardware(path: str | Path) -> HardwareModel:
    """Load a HardwareModel from a YAML file.

    Parameters
    ----------
    path : str or Path
        Path to YAML file with hardware model data.

    Returns
    -------
    HardwareModel
    """
    with open(path) as f:
        data = yaml.safe_load(f)
    return HardwareModel.from_dict(data)


def load_qec(path: str | Path) -> FormulaQEC:
    """Load a FormulaQEC scheme from a YAML file.

    Parameters
    ----------
    path : str or Path
        Path to YAML file with QEC scheme data.

    Returns
    -------
    FormulaQEC
    """
    with open(path) as f:
        data = yaml.safe_load(f)
    return FormulaQEC.from_dict(data)


def save_yaml(data: dict[str, Any], path: str | Path) -> None:
    """Dump any dictionary to a YAML file.

    Parameters
    ----------
    data : dict
        Dictionary to serialize.
    path : str or Path
        Output file path.
    """
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def save_estimate(result: PhysicalEstimate, path: str | Path) -> None:
    """Save a PhysicalEstimate to a YAML file.

    Calls ``result.to_dict()`` and writes the output as YAML.

    Parameters
    ----------
    result : PhysicalEstimate
        Estimation result to save.
    path : str or Path
        Output file path.
    """
    save_yaml(result.to_dict(), path)


def save_exploration(result: Any, path: str | Path) -> None:
    """Save an ExplorationResult to a YAML file.

    Dumps summary dicts for all succeeded design points.

    Parameters
    ----------
    result : ExplorationResult
        Exploration result to save.
    path : str or Path
        Output file path.
    """
    rows = [pt.estimate.summary_dict() for pt in result.succeeded]
    save_yaml({"points": rows}, path)


__all__ = [
    "load_algorithm",
    "load_hardware",
    "load_qec",
    "save_yaml",
    "save_estimate",
    "save_exploration",
]
