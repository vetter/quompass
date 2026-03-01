# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

```bash
# Setup (uv — preferred)
uv sync --extra dev --extra optimize    # install dev + optimize extras
uv sync --all-extras                     # install everything

# Fallback (pip)
pip install -e ".[dev,optimize]"

# Run all unit tests (no external backends required)
uv run pytest tests/unit -v

# Run a single test file or test
uv run pytest tests/unit/test_qec.py -v
uv run pytest tests/unit/test_estimate.py::test_estimate_basic -v

# Run integration tests (require qualtran/azure installed)
uv run pytest tests/integration -v

# Run optimization tests (require pymoo)
uv run pytest -m optimize -v

# Run with coverage
uv run pytest --cov=ftqre --cov-report=html

# Lint and type check
uv run ruff check src/ tests/
uv run mypy src/ftqre/
```

## Architecture

**Two-stage estimation pipeline:**
```
AlgorithmSpec -> LogicalEstimator -> LogicalCounts -> PhysicalEstimator -> PhysicalEstimate
  (template)      (Qualtran/mock)    (PORTABLE)       (Azure/analytical)    (result)
```

**LogicalCounts** (`core/algorithm.py`) is the portable interchange format — a frozen dataclass with `num_qubits`, `t_count`, `ccz_count`, `rotation_count`, etc. Everything upstream produces it; everything downstream consumes it.

**Key modules under `src/ftqre/`:**

- `core/` — Domain types: `AlgorithmSpec`, `LogicalCounts`, `QECScheme` (ABC), `HardwareModel`, `PhysicalEstimate`, `ErrorBudget`. All result types are frozen dataclasses.
- `backends/` — `LogicalEstimator` and `PhysicalEstimator` ABCs in `base.py`. Mock/analytical backends in `mock.py`. Real backends (qualtran/, azure/) use lazy imports and adapter pattern.
- `backends/registry.py` — Plugin discovery via `importlib.metadata.entry_points`. Four groups: `ftqre.logical_estimators`, `ftqre.physical_estimators`, `ftqre.qec_schemes`, `ftqre.algorithm_templates`.
- `templates/` — Algorithm templates (Shor, QPE, chemistry, Hamiltonian sim, Grover). Each has a `generate(**params) -> AlgorithmSpec` method and a convenience function.
- `exploration/` — Design space grid search (`ExplorationSpace` + `explore()`), Pareto front extraction, sensitivity analysis (OFAT).
- `optimization/` — NSGA-II multi-objective optimization via pymoo.
- `cli/` — Typer app with `estimate`, `explore`, `optimize`, `catalog` subcommands.
- `io/` — YAML load/save for algorithm specs, hardware models, QEC schemes, and results.

**Entry point:** `ftqre.estimate()` in `__init__.py` is the primary API. It handles type coercion (strings → enums/models), backend auto-selection, and runs the full pipeline.

## Design Conventions

- **QEC is pluggable** — `QECScheme` ABC + `FormulaQEC` for YAML-defined codes (AST-based safe formula eval, no `eval()`). Surface code, Floquet, and color code are built in.
- **Backend isolation** — Heavy dependencies (qualtran, qsharp, pymoo) are lazy-imported. Backends must implement `is_available() -> bool`. Mock backends have zero external deps and are used in all unit tests.
- **Plugin architecture** — Backends, QEC schemes, and templates are discovered via `entry_points` in `pyproject.toml`. New ones can be added by third-party packages.
- **YAML workflows** — CLI accepts `--hardware path.yaml` and `--qec path.yaml` alongside preset names. See `examples/` for YAML format.
- **Hardware presets** — `HardwarePreset` enum in `core/types.py` maps to `QubitParams` via `HardwareModel.from_preset()`. Presets: `gate_ns_e3`, `gate_ns_e4`, `gate_us_e3`, `gate_us_e4`, `maj_ns_e4`, `maj_ns_e6`.

## Testing Patterns

- Unit tests use `MockLogicalEstimator` and `AnalyticalPhysicalEstimator` — no real backends needed.
- Integration tests are marked with `@pytest.mark.integration` and conditionally skip if backends are unavailable.
- Optimization tests are marked with `@pytest.mark.optimize` and require pymoo.
- `tests/integration/conftest.py` has shared fixtures.

## Configuration

- **ruff**: line-length 100, target Python 3.10
- **mypy**: Python 3.10, `warn_return_any = true`
- **pytest**: testpaths = `["tests"]`

## Project Status

Phases 1-4 complete (core types, backends, exploration, YAML/docs). Phase 5 (NSGA-II optimization, pyLIQTR/MQT real integration) is in progress — `optimization/` module and pyLIQTR/MQT stubs exist but real backend adapters are not yet wired up.
