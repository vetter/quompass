"""Template discovery and listing."""

from __future__ import annotations

from quompass.templates.base import AlgorithmTemplate
from quompass.templates.chemistry import ChemistryTemplate
from quompass.templates.grover import GroverTemplate
from quompass.templates.hamiltonian_sim import HamiltonianSimTemplate
from quompass.templates.qpe import QPETemplate
from quompass.templates.shor import ShorTemplate

# Built-in templates
_BUILTIN_TEMPLATES: dict[str, type[AlgorithmTemplate]] = {
    "shor": ShorTemplate,
    "qpe": QPETemplate,
    "hamiltonian_sim": HamiltonianSimTemplate,
    "chemistry": ChemistryTemplate,
    "grover": GroverTemplate,
}


def list_templates() -> dict[str, AlgorithmTemplate]:
    """Return all available algorithm templates."""
    templates: dict[str, AlgorithmTemplate] = {}
    for name, cls in _BUILTIN_TEMPLATES.items():
        templates[name] = cls()

    # Also discover plugins via entry_points
    try:
        from importlib.metadata import entry_points

        eps = entry_points(group="quompass.algorithm_templates")
        for ep in eps:
            if ep.name not in templates:
                try:
                    cls = ep.load()
                    templates[ep.name] = cls()
                except Exception:
                    pass
    except Exception:
        pass

    return templates


def get_template(name: str) -> AlgorithmTemplate:
    """Get a specific template by name."""
    templates = list_templates()
    if name not in templates:
        available = ", ".join(sorted(templates.keys()))
        raise ValueError(f"Unknown template '{name}'. Available: {available}")
    return templates[name]
