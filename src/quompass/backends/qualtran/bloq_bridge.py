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
    """Try to construct a Qualtran Shor/RSA factoring Bloq.

    Uses ModExp from qualtran.bloqs.cryptography.rsa (qualtran >= 0.7)
    or qualtran.bloqs.factoring.mod_exp (qualtran < 0.7).
    """
    n_bits = int(params.get("n_bits", 2048))
    # Use a small placeholder modulus (actual value doesn't affect resource counts
    # structurally, but qualtran requires a concrete value)
    mod = (1 << n_bits) - 1  # 2^n - 1 as placeholder

    # Try qualtran >= 0.7 path first
    try:
        from qualtran.bloqs.cryptography.rsa import ModExp

        return ModExp(base=2, mod=mod, exp_bitsize=n_bits, x_bitsize=n_bits)
    except (ImportError, TypeError):
        pass

    # Try legacy qualtran < 0.7 path
    try:
        from qualtran.bloqs.factoring.mod_exp import ModExp as LegacyModExp

        return LegacyModExp(base=2, exp_bitsize=n_bits, mod_bitsize=n_bits)
    except (ImportError, TypeError):
        pass

    raise ValueError(
        "Qualtran factoring/cryptography bloqs not available. "
        "Install qualtran with: pip install 'qualtran>=0.4'"
    )


@_register_family("phase_estimation")
def _try_qpe_bloq(params: dict[str, Any]) -> Any:
    """Try to construct a Qualtran QPE Bloq.

    QPE Bloqs (TextbookQPE, QubitizationQPE) require an inner unitary/walk
    operator that can't be auto-constructed from template parameters alone.
    This builder supports the ``qualtran:`` source prefix for direct Bloq
    references. Otherwise, falls back to template-provided counts.
    """
    raise ValueError(
        "QPE Bloq requires a concrete unitary operator. "
        "Use source='qualtran:module:ClassName' or estimate_from_bloq() "
        "for direct Bloq input."
    )


@_register_family("chemistry")
def _try_chemistry_bloq(params: dict[str, Any]) -> Any:
    """Try to construct a Qualtran chemistry Bloq.

    Chemistry Bloqs (DoubleFactorizationBlockEncoding, SelectTHC, etc.)
    require Hamiltonian coefficient data that can't be auto-constructed
    from template parameters alone.
    """
    method = str(params.get("method", "double_factorization"))
    raise ValueError(
        f"Chemistry Bloq (method={method!r}) requires Hamiltonian data. "
        f"Use source='qualtran:module:ClassName' or estimate_from_bloq() "
        f"for direct Bloq input."
    )


@_register_family("simulation")
def _try_hamiltonian_sim_bloq(params: dict[str, Any]) -> Any:
    """Try to construct a Qualtran Hamiltonian simulation Bloq.

    Hamiltonian simulation Bloqs require a concrete Hamiltonian operator
    that can't be auto-constructed from template parameters alone.
    """
    method = str(params.get("method", "trotter"))
    raise ValueError(
        f"Hamiltonian simulation Bloq (method={method!r}) requires a "
        f"concrete Hamiltonian. Use source='qualtran:module:ClassName' "
        f"or estimate_from_bloq() for direct Bloq input."
    )


@_register_family("search")
def _try_grover_bloq(params: dict[str, Any]) -> Any:
    """Try to construct a Qualtran Grover/amplitude amplification Bloq.

    Grover's algorithm requires a problem-specific oracle Bloq.
    """
    raise ValueError(
        "Grover Bloq requires a problem-specific oracle. "
        "Use source='qualtran:module:ClassName' or estimate_from_bloq() "
        "for direct Bloq input."
    )
