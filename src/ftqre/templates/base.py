"""Base class for parameterized algorithm templates."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ftqre.core.algorithm import AlgorithmSpec


class AlgorithmTemplate(ABC):
    """Base class for parameterized algorithm templates.

    Templates provide pre-computed or formulaic logical resource counts
    for well-known algorithms. Users parameterize them with problem-specific
    values (e.g., number of bits for Shor's, number of orbitals for chemistry).
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def family(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    def generate(self, **params: Any) -> AlgorithmSpec:
        """Generate an AlgorithmSpec from problem parameters."""
        ...

    @abstractmethod
    def parameter_schema(self) -> dict[str, Any]:
        """Return a description of accepted parameters.

        Each key is a parameter name, and the value is a dict with:
        - type: str (e.g., "int", "float", "str")
        - default: the default value
        - description: human-readable description
        - choices: (optional) list of valid values
        - min/max: (optional) bounds
        """
        ...
