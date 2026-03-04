"""Algorithm templates for common quantum algorithms."""

from quompass.templates.chemistry import chemistry
from quompass.templates.grover import grover
from quompass.templates.hamiltonian_sim import hamiltonian_sim
from quompass.templates.qpe import qpe
from quompass.templates.shor import shor

__all__ = ["shor", "qpe", "hamiltonian_sim", "chemistry", "grover"]
