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
uv run pytest --cov=quompass --cov-report=html

# Lint and type check
uv run ruff check src/ tests/
uv run mypy src/quompass/

# CLI (after install)
quompass estimate --template shor --param n_bits=2048
quompass explore --template shor --param n_bits=2048 --hardware gate_ns_e3,gate_ns_e4 --qec surface_code
quompass optimize --template shor --param n_bits=2048
quompass catalog templates|hardware|qec
```

## Architecture

**Two-stage estimation pipeline:**
```
AlgorithmSpec -> LogicalEstimator -> LogicalCounts -> PhysicalEstimator -> PhysicalEstimate
  (template)      (Qualtran/mock)    (PORTABLE)       (Azure/analytical)    (result)
```

**LogicalCounts** (`core/algorithm.py`) is the portable interchange format — a frozen dataclass with `num_qubits`, `t_count`, `ccz_count`, `rotation_count`, etc. Everything upstream produces it; everything downstream consumes it. `total_t_equivalent` property converts CCZ (×4) and rotations into T-gate equivalents.

**Primary entry point:** `quompass.estimate()` in `__init__.py`. Handles type coercion (strings → enums/models), backend auto-selection via registry, and runs the full pipeline. This is the main API for both library and CLI use.

**Key modules under `src/quompass/`:**

- `core/` — Domain types: `AlgorithmSpec`, `LogicalCounts`, `QECScheme` (ABC), `HardwareModel`, `QubitParams`, `PhysicalEstimate`, `ErrorBudget`. All result types are frozen dataclasses. `HardwarePreset` enum + `HardwareModel.from_preset()` for built-in hardware targets.
- `backends/` — `LogicalEstimator` and `PhysicalEstimator` ABCs in `base.py`. Both require `name`, `estimate()`, and `is_available()`. Mock/analytical backends in `mock.py`. Real backends (qualtran/, azure/, pyliqtr/, mqt/) use lazy imports and adapter pattern.
- `backends/registry.py` — Plugin discovery via `importlib.metadata.entry_points`. Auto-selection priority: logical = qualtran > pyliqtr > mock; physical = azure > mqt > analytical. Four entry-point groups: `quompass.logical_estimators`, `quompass.physical_estimators`, `quompass.qec_schemes`, `quompass.algorithm_templates`.
- `core/qec.py` — `QECScheme` ABC with `logical_error_rate()`, `physical_qubits_per_logical()`, `logical_cycle_time()`, `min_code_distance()`. `FormulaQEC` enables YAML-defined codes via AST-safe formula evaluation (never `eval()`). Built-in: `SurfaceCode`, `FloquetCode`, `color_code()`.
- `templates/` — Algorithm templates (Shor, QPE, chemistry, Hamiltonian sim, Grover). Each has a `generate(**params) -> AlgorithmSpec` method and a convenience function.
- `exploration/` — Design space grid search (`ExplorationSpace` + `explore()`), Pareto front extraction, sensitivity analysis (OFAT).
- `optimization/` — NSGA-II multi-objective optimization via pymoo.
- `cli/` — Typer app with `estimate`, `explore`, `optimize`, `catalog` subcommands.
- `io/` — YAML load/save for algorithm specs, hardware models, QEC schemes, and results.

## Design Conventions

- **QEC is pluggable** — `QECScheme` ABC + `FormulaQEC` for YAML-defined codes. `_safe_eval()` uses AST walking with whitelisted operators and math functions (ceil, sqrt, log, etc.). Formula variables: `d` for distance, `t_1q`/`t_2q`/`t_meas`/`t_jm` for cycle time.
- **Backend isolation** — Heavy dependencies (qualtran, qsharp, pymoo, pyLIQTR, mqt) are lazy-imported. Backends must implement `is_available() -> bool`. Mock backends have zero external deps and are used in all unit tests.
- **Plugin architecture** — Backends, QEC schemes, and templates are discovered via `entry_points` in `pyproject.toml`. New ones can be added by third-party packages without modifying this repo.
- **Frozen dataclasses** — All result/interchange types (`LogicalCounts`, `PhysicalEstimate`, `LogicalQubitEstimate`, `TFactoryEstimate`, `ErrorBudgetBreakdown`) are frozen. `AlgorithmSpec` is mutable (has `problem_parameters` dict).
- **YAML workflows** — CLI accepts `--hardware path.yaml` and `--qec path.yaml` alongside preset names. `io/` module provides `load_algorithm()`, `load_hardware()`, `load_qec()`, `save_estimate()`.
- **Hardware presets** — `HardwarePreset` enum maps to `QubitParams` via `HardwareModel.from_preset()`. Six presets: `gate_ns_e3`, `gate_ns_e4`, `gate_us_e3`, `gate_us_e4`, `maj_ns_e4`, `maj_ns_e6`.

## Testing Patterns

- Unit tests use `MockLogicalEstimator` (passthrough) and `AnalyticalPhysicalEstimator` (formula-based) — no real backends needed.
- Integration tests: `@pytest.mark.integration`, conditionally skip if backends unavailable. Fixtures in `tests/integration/conftest.py`.
- Optimization tests: `@pytest.mark.optimize`, require pymoo.
- All core types have `to_dict()`/`from_dict()` round-trip serialization tested in `test_serialization.py` and `test_io.py`.

## Configuration

- **ruff**: line-length 100, target Python 3.10
- **mypy**: Python 3.10, `warn_return_any = true`
- **pytest**: testpaths = `["tests"]`, custom markers: `integration`, `optimize`
- **Python**: requires >= 3.10, runtime deps: numpy, typer, rich, pyyaml
