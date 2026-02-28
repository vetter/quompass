"""Bridge between ftqre AlgorithmSpec and Qualtran Bloq objects.

Maps algorithm families and sources to known Qualtran Bloq classes
when available, or creates a placeholder Bloq that encodes the
LogicalCounts directly.

All qualtran imports are lazy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ftqre.core.algorithm import AlgorithmSpec


def spec_to_bloq(spec: AlgorithmSpec) -> Any:
    """Convert an AlgorithmSpec to a Qualtran Bloq.

    If the spec's source starts with "qualtran:", attempts to look up
    the corresponding Qualtran Bloq class. Otherwise, returns a
    placeholder that can still be used for cost extraction.

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
    if spec.algorithm_family == "cryptanalysis":
        return _try_shor_bloq(spec.problem_parameters)

    raise ValueError(
        f"Cannot map AlgorithmSpec '{spec.name}' to a Qualtran Bloq. "
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

    mod = importlib.import_module(module_path)
    bloq_cls = getattr(mod, class_name)
    return bloq_cls(**params)


def _try_shor_bloq(params: dict[str, Any]) -> Any:
    """Try to construct a Qualtran Shor/RSA factoring Bloq."""
    try:
        from qualtran.bloqs.factoring.mod_exp import ModExp

        n_bits = params.get("n_bits", 2048)
        return ModExp(base=2, exp_bitsize=n_bits, mod_bitsize=n_bits)
    except ImportError:
        raise ValueError(
            "Qualtran factoring bloqs not available. "
            "Install qualtran with: pip install 'qualtran>=0.4'"
        )
