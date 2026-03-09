"""Bridge between quompass AlgorithmSpec and Qualtran Bloq objects.

Maps algorithm families and sources to known Qualtran Bloq classes
when available, or creates a placeholder Bloq that encodes the
LogicalCounts directly.

All qualtran imports are lazy.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from quompass.core.algorithm import AlgorithmSpec

logger = logging.getLogger(__name__)

# Registry of algorithm family -> builder function
_FAMILY_BUILDERS: dict[str, Any] = {}


def _register_family(family: str):
    """Decorator to register a bloq builder for an algorithm family."""
    def decorator(func):
        _FAMILY_BUILDERS[family] = func
        return func
    return decorator


def spec_to_bloq(spec: AlgorithmSpec) -> Any:
    """Convert an AlgorithmSpec to a Qualtran Bloq.

    If the spec's source starts with "qualtran:", attempts to look up
    the corresponding Qualtran Bloq class. Otherwise, tries to map
    by algorithm family.

    Parameters
    ----------
    spec : AlgorithmSpec
        The algorithm specification.

    Returns
    -------
    bloq
        A ``qualtran.Bloq`` instance.

    Raises
    ------
    ImportError
        If qualtran is not installed.
    ValueError
        If the spec cannot be mapped to a Bloq.
    """
    source = spec.source or ""

    if source.startswith("qualtran:"):
        return _lookup_qualtran_bloq(source, spec.problem_parameters)

    # For template-generated specs, try to map by algorithm family
    builder = _FAMILY_BUILDERS.get(spec.algorithm_family)
    if builder is not None:
        return builder(spec.problem_parameters)

    raise ValueError(
        f"Cannot map AlgorithmSpec '{spec.name}' (family={spec.algorithm_family!r}) "
        f"to a Qualtran Bloq. "
        f"Use QualtranLogicalEstimator.estimate_from_bloq() for direct Bloq input."
    )


def _lookup_qualtran_bloq(source: str, params: dict[str, Any]) -> Any:
    """Look up a Qualtran Bloq by fully-qualified source string."""
    # source format: "qualtran:module.path:ClassName"
    parts = source.split(":", 2)
    if len(parts) != 3:
        raise ValueError(
            f"Invalid qualtran source format: {source!r}. "
            f"Expected 'qualtran:module.path:ClassName'"
        )
    _, module_path, class_name = parts

    import importlib

    try:
        mod = importlib.import_module(module_path)
    except ImportError as e:
        raise ImportError(
            f"Cannot import Qualtran module {module_path!r}: {e}"
        ) from e

    bloq_cls = getattr(mod, class_name, None)
    if bloq_cls is None:
        raise ValueError(
            f"Class {class_name!r} not found in module {module_path!r}"
        )
    return bloq_cls(**params)


# ---------------------------------------------------------------------------
# Algorithm family builders
# ---------------------------------------------------------------------------


@_register_family("cryptanalysis")
def _try_shor_bloq(params: dict[str, Any]) -> Any:
    """Try to construct a Qualtran Shor/RSA factoring Bloq."""
    try:
        from qualtran.bloqs.factoring.mod_exp import ModExp

        n_bits = int(params.get("n_bits", 2048))
        return ModExp(base=2, exp_bitsize=n_bits, mod_bitsize=n_bits)
    except ImportError:
        raise ValueError(
            "Qualtran factoring bloqs not available. "
            "Install qualtran with: pip install 'qualtran>=0.4'"
        )


@_register_family("phase_estimation")
def _try_qpe_bloq(params: dict[str, Any]) -> Any:
    """Try to construct a Qualtran QPE Bloq."""
    try:
        from qualtran.bloqs.phase_estimation import QubitizationQPE

        num_qubits = int(params.get("num_qubits", 10))
        precision_bits = int(params.get("precision_bits", 20))
        return QubitizationQPE(
            num_qubits=num_qubits, precision_bits=precision_bits
        )
    except (ImportError, TypeError):
        # QubitizationQPE may not exist or may have different signature
        logger.debug(
            "Could not construct QPE Bloq from qualtran; "
            "will fall back to template-provided counts"
        )
        raise ValueError("Qualtran QPE bloqs not available or incompatible")


@_register_family("chemistry")
def _try_chemistry_bloq(params: dict[str, Any]) -> Any:
    """Try to construct a Qualtran chemistry Bloq."""
    method = str(params.get("method", "double_factorization"))
    num_orbitals = int(params.get("num_orbitals", 54))

    try:
        if method == "double_factorization":
            from qualtran.bloqs.chemistry.df.double_factorization import (
                DoubleFactorization,
            )
            return DoubleFactorization(num_spin_orb=2 * num_orbitals)
        elif method == "thc":
            from qualtran.bloqs.chemistry.thc.walk_operator import THCWalkOperator
            return THCWalkOperator(num_spin_orb=2 * num_orbitals)
        elif method == "sparse":
            from qualtran.bloqs.chemistry.sparse.walk_operator import (
                SparseWalkOperator,
            )
            return SparseWalkOperator(num_spin_orb=2 * num_orbitals)
    except (ImportError, TypeError):
        pass

    logger.debug(
        "Could not construct chemistry Bloq (method=%s) from qualtran; "
        "will fall back to template-provided counts",
        method,
    )
    raise ValueError(
        f"Qualtran chemistry bloqs not available for method={method!r}"
    )


@_register_family("simulation")
def _try_hamiltonian_sim_bloq(params: dict[str, Any]) -> Any:
    """Try to construct a Qualtran Hamiltonian simulation Bloq."""
    method = str(params.get("method", "trotter"))
    num_qubits = int(params.get("num_qubits", 50))

    try:
        if method == "trotter":
            from qualtran.bloqs.hamiltonian_simulation.product_formula import (
                ProductFormula,
            )
            return ProductFormula(num_qubits=num_qubits)
        elif method in ("qsp", "qubitization"):
            from qualtran.bloqs.hamiltonian_simulation.qubitization_walk_operator import (
                QubitizationWalkOperator,
            )
            return QubitizationWalkOperator(num_qubits=num_qubits)
    except (ImportError, TypeError):
        pass

    logger.debug(
        "Could not construct Hamiltonian simulation Bloq (method=%s) from qualtran; "
        "will fall back to template-provided counts",
        method,
    )
    raise ValueError(
        f"Qualtran Hamiltonian simulation bloqs not available for method={method!r}"
    )


@_register_family("search")
def _try_grover_bloq(params: dict[str, Any]) -> Any:
    """Try to construct a Qualtran Grover/amplitude amplification Bloq."""
    try:
        from qualtran.bloqs.mcmt.and_bloq import And

        # Grover's algorithm doesn't have a single dedicated Bloq in qualtran;
        # the oracle is problem-specific. Use And as a representative primitive.
        search_space_bits = int(params.get("search_space_bits", 20))
        return And(cv=(1,) * search_space_bits)
    except (ImportError, TypeError):
        pass

    logger.debug(
        "Could not construct Grover Bloq from qualtran; "
        "will fall back to template-provided counts"
    )
    raise ValueError("Qualtran Grover/search bloqs not available")
