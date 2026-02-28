"""Algorithm templates for common quantum algorithms."""

from ftqre.templates.chemistry import chemistry
from ftqre.templates.grover import grover
from ftqre.templates.hamiltonian_sim import hamiltonian_sim
from ftqre.templates.qpe import qpe
from ftqre.templates.shor import shor

__all__ = ["shor", "qpe", "hamiltonian_sim", "chemistry", "grover"]
