# Quompass Design Document

**Version:** 0.1.0
**Last updated:** 2026-03-09

---

## 1. Purpose

Quompass is a Python library for estimating the physical resources required to run fault-tolerant quantum algorithms. It provides a portable abstraction layer over multiple estimation backends (Qualtran, Azure QRE, pyLIQTR, MQT) with pluggable QEC schemes, hardware models, and algorithm templates.

The core insight is that **LogicalCounts** (qubit count, T-gate count, CCZ count, rotation count, etc.) form a universal interchange format. Any algorithm source can produce them; any physical estimator can consume them. Quompass owns this interchange layer and orchestrates the pipeline.

---

## 2. Architecture Overview

```
                           ┌──────────────────────────────────┐
                           │         User Entry Points         │
                           │  Python API / CLI / YAML files    │
                           └────────────┬─────────────────────┘
                                        │
                                        ▼
                    ┌───────────────────────────────────────────┐
                    │          quompass.estimate()               │
                    │  Type coercion, backend selection, pipeline│
                    └─────────────┬──────────────┬──────────────┘
                                  │              │
                    ┌─────────────▼──┐    ┌──────▼──────────────┐
                    │    Stage 1:     │    │     Stage 2:         │
                    │  Logical Est.   │    │  Physical Est.       │
                    │  (Qualtran/     │    │  (Azure/MQT/         │
                    │   pyLIQTR/mock) │    │   analytical)        │
                    └───────┬────────┘    └──────┬──────────────┘
                            │                     │
                            ▼                     ▼
                    ┌──────────────┐      ┌────────────────────┐
                    │ LogicalCounts │─────▶│  PhysicalEstimate   │
                    │  (portable)   │      │  (full breakdown)   │
                    └──────────────┘      └────────────────────┘
```

**Two-stage pipeline:**

| Stage | Input | Output | Backends |
|-------|-------|--------|----------|
| Logical estimation | `AlgorithmSpec` | `LogicalCounts` | Qualtran, pyLIQTR, mock (passthrough) |
| Physical estimation | `LogicalCounts` + `HardwareModel` + `QECScheme` + `ErrorBudget` | `PhysicalEstimate` | Azure QRE, MQT, analytical (built-in) |

---

## 3. Module Map

```
src/quompass/
├── __init__.py              # Public API: estimate(), top-level imports
├── _version.py              # Version string
├── core/                    # Domain types (no external deps)
│   ├── types.py             #   Enums: InstructionSet, HardwarePreset
│   ├── algorithm.py         #   LogicalCounts, AlgorithmSpec
│   ├── hardware.py          #   QubitParams, HardwareModel, preset definitions
│   ├── qec.py               #   QECScheme ABC, SurfaceCode, FloquetCode, FormulaQEC
│   ├── error_budget.py      #   ErrorBudget, ErrorBudgetBreakdown
│   └── results.py           #   PhysicalEstimate, LogicalQubitEstimate, TFactoryEstimate
├── backends/                # Estimation backends (lazy imports)
│   ├── base.py              #   LogicalEstimator ABC, PhysicalEstimator ABC
│   ├── mock.py              #   MockLogicalEstimator, AnalyticalPhysicalEstimator
│   ├── registry.py          #   Plugin discovery, auto-selection
│   ├── qualtran/            #   Qualtran logical estimator + bloq bridge
│   ├── azure/               #   Azure QRE physical estimator + param/result mapping
│   ├── pyliqtr/             #   pyLIQTR logical estimator (stub)
│   └── mqt/                 #   MQT physical estimator (stub)
├── templates/               # Parameterized algorithm templates
│   ├── base.py              #   AlgorithmTemplate ABC
│   ├── shor.py              #   Shor's factoring (Gidney-Ekera + textbook)
│   ├── qpe.py               #   Quantum Phase Estimation
│   ├── chemistry.py         #   Quantum chemistry (DF/THC/sparse)
│   ├── hamiltonian_sim.py   #   Hamiltonian simulation (Trotter/QSP/qubitization)
│   ├── grover.py            #   Grover's search
│   └── registry.py          #   Template lookup by name
├── exploration/             # Design space analysis
│   ├── space.py             #   ExplorationSpace, DesignPoint, ExplorationResult, ParetoFront
│   ├── explorer.py          #   Grid search: explore()
│   ├── pareto.py            #   Pareto front extraction
│   └── sensitivity.py       #   One-at-a-time sensitivity analysis
├── optimization/            # Multi-objective optimization (requires pymoo)
│   ├── space.py             #   OptimizationSpace
│   ├── optimizer.py         #   optimize(), OptimizationResult, OptimizationConfig
│   ├── problem.py           #   FTQREProblem (pymoo Problem wrapper)
│   └── callback.py          #   ProgressCallback for pymoo
├── io/                      # YAML/JSON serialization
│   └── __init__.py          #   load_algorithm, load_hardware, load_qec, save_estimate
├── viz/                     # Visualization
│   ├── exploration.py       #   Rich tables, matplotlib scatter plots
│   └── summary.py           #   Single-estimate Rich summary
├── cli/                     # Typer CLI
│   ├── main.py              #   App entry point
│   ├── estimate.py          #   `quompass estimate` command
│   ├── explore.py           #   `quompass explore` command
│   ├── optimize.py          #   `quompass optimize` command
│   └── catalog.py           #   `quompass catalog` command
└── plugins/                 # Plugin namespace (for third-party extensions)
    └── __init__.py
```

---

## 4. Key Interfaces and Data Types

### 4.1 LogicalCounts — The Portable Interchange Format

**Location:** `core/algorithm.py`
**Frozen dataclass** — the universal currency between stages.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `num_qubits` | `int` | *required* | Algorithmic logical qubits |
| `t_count` | `int` | 0 | Number of T gates |
| `rotation_count` | `int` | 0 | Number of arbitrary rotations |
| `rotation_depth` | `int` | 0 | Depth of rotation sub-circuit |
| `ccz_count` | `int` | 0 | Number of CCZ/Toffoli gates |
| `measurement_count` | `int` | 0 | Mid-circuit measurements |
| `clifford_count` | `int` | 0 | Clifford gate count |
| `circuit_depth` | `int?` | None | Total circuit depth (optional) |

**Derived properties:**
- `total_t_equivalent` → `t_count + 4 * ccz_count + rotation_count`
- `has_rotations` → `rotation_count > 0`

**Serialization:** `to_dict()` emits camelCase keys (`numQubits`, `tCount`, etc.) for Azure QRE wire-format compatibility.

### 4.2 AlgorithmSpec

**Location:** `core/algorithm.py`
**Mutable dataclass** — wraps LogicalCounts with metadata.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Human-readable name |
| `logical_counts` | `LogicalCounts` | The resource profile |
| `description` | `str` | Algorithm description |
| `algorithm_family` | `str` | Category (e.g., "cryptanalysis", "chemistry") |
| `problem_parameters` | `dict` | Template input parameters (e.g., `{"n_bits": 2048}`) |
| `source` | `str` | Provenance (e.g., "template:shor") |

### 4.3 HardwareModel / QubitParams

**Location:** `core/hardware.py`, `core/types.py`

`QubitParams` captures all physical qubit characteristics needed by any backend:

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `name` | `str` | | Identifier |
| `instruction_set` | `InstructionSet` | | `GATE_BASED` or `MAJORANA` |
| `one_qubit_gate_time` | `float` | seconds | 1Q gate duration |
| `two_qubit_gate_time` | `float` | seconds | 2Q gate duration |
| `one_qubit_measurement_time` | `float` | seconds | Measurement duration |
| `t_gate_time` | `float` | seconds | T gate duration |
| `one_qubit_gate_error_rate` | `float` | dimensionless | 1Q gate error probability |
| `two_qubit_gate_error_rate` | `float` | dimensionless | 2Q gate error probability |
| `one_qubit_measurement_error_rate` | `float` | dimensionless | Measurement error probability |
| `t_gate_error_rate` | `float` | dimensionless | T gate error probability |
| `idle_error_rate` | `float?` | dimensionless | Idle qubit dephasing rate |
| `two_qubit_joint_measurement_time` | `float?` | seconds | Majorana-specific |
| `two_qubit_joint_measurement_error_rate` | `float?` | dimensionless | Majorana-specific |

**Derived:** `worst_case_clifford_error` → `max(measurement, 1q_gate, 2q_gate [, joint_meas])` error rates.

`HardwareModel` wraps `QubitParams` with a name and description, and provides `from_preset(name)` for the six built-in targets:

| Preset Name | Enum | Modality | Gate Time | Clifford Error |
|-------------|------|----------|-----------|----------------|
| `gate_ns_e3` | `SUPERCONDUCTING_REALISTIC` | Superconducting | 50 ns | 10^-3 |
| `gate_ns_e4` | `SUPERCONDUCTING_OPTIMISTIC` | Superconducting | 50 ns | 10^-4 |
| `gate_us_e3` | `TRAPPED_ION_REALISTIC` | Trapped ion | 100 us | 10^-3 |
| `gate_us_e4` | `TRAPPED_ION_OPTIMISTIC` | Trapped ion | 100 us | 10^-4 |
| `maj_ns_e4` | `MAJORANA_REALISTIC` | Majorana | 100 ns | 10^-4 |
| `maj_ns_e6` | `MAJORANA_OPTIMISTIC` | Majorana | 100 ns | 10^-6 |

### 4.4 QECScheme — Pluggable Error Correction

**Location:** `core/qec.py`

Abstract base class. Every QEC scheme must implement:

| Method | Signature | Description |
|--------|-----------|-------------|
| `name` | `-> str` | Scheme identifier |
| `error_correction_threshold` | `-> float` | Physical error rate threshold p* |
| `crossing_prefactor` | `-> float` | Prefactor *a* in logical error formula |
| `logical_error_rate` | `(code_distance, physical_error_rate) -> float` | Compute P_L |
| `physical_qubits_per_logical` | `(code_distance) -> int` | Physical qubits for one logical qubit |
| `logical_cycle_time` | `(code_distance, qubit_params) -> float` | Time (seconds) for one logical cycle |

**Provided:** `min_code_distance(target_error_rate, physical_error_rate)` — linear search over odd distances 3..51.

**Built-in implementations:**

| Class | Qubits/Logical | Threshold | Cycle Time |
|-------|----------------|-----------|------------|
| `SurfaceCode` | 2d^2 | 1% | (4 * t_2q + 2 * t_meas) * d |
| `FloquetCode` | 4d^2 + 8(d-1) | 1% | 3 * t_meas * d |
| `color_code()` | ceil(4.5 * d^2) | 0.77% | 10 * t_2q * d |

**FormulaQEC** enables user-defined codes via YAML without writing Python. Formulas are evaluated with AST-safe parsing (no `eval()`). Variables: `d` (distance), `t_1q`, `t_2q`, `t_meas`, `t_jm` (gate times). The optional `transversal_magic_states` flag marks codes that apply T/CCZ transversally (high-rate qLDPC), suppressing the distillation-factory model.

```yaml
# Example custom QEC definition
name: my_qldpc_code
threshold: 0.005
prefactor: 0.2
qubits_formula: "ceil(3 * d * d)"
cycle_time_formula: "8 * t_2q * d"
```

### 4.5 ErrorBudget

**Location:** `core/error_budget.py`

The total error budget epsilon is split across three components:

| Component | Description |
|-----------|-------------|
| `logical` | Errors in logical qubit operations |
| `distillation` | Errors in T-state distillation |
| `rotation` | Errors in rotation gate synthesis |

`ErrorBudget.resolve(has_rotations)` produces a frozen `ErrorBudgetBreakdown`:
- If splits are explicitly set: use them directly
- If algorithm has rotations: uniform 1/3 split
- If no rotations: 1/2 split across logical and distillation

### 4.6 PhysicalEstimate — The Output

**Location:** `core/results.py`
**Frozen dataclass** — complete result breakdown.

| Field | Type | Description |
|-------|------|-------------|
| `total_physical_qubits` | `int` | Total physical qubits (algorithm + T factories) |
| `runtime_seconds` | `float` | Wall-clock execution time |
| `rqops` | `float` | Reliable quantum operations per second |
| `algorithmic_logical_qubits` | `int` | Logical qubits for the algorithm |
| `physical_qubits_for_algorithm` | `int` | Physical qubits for algorithmic logical qubits |
| `physical_qubits_for_t_factories` | `int` | Physical qubits for T-state factories |
| `logical_qubit` | `LogicalQubitEstimate` | Code distance, qubits/logical, cycle time, error rate |
| `t_factory` | `TFactoryEstimate?` | Factory count, qubits, runtime, rounds, output error |
| `algorithmic_logical_depth` | `int` | Total logical cycles |
| `num_t_states` | `int` | Total T-equivalent states consumed |
| `clock_frequency` | `float` | Logical cycles per second |
| `error_budget` | `ErrorBudgetBreakdown` | How the error budget was split |
| `required_logical_error_rate` | `float` | Target logical error rate per qubit per cycle |
| `required_t_state_error_rate` | `float` | Target T-state output error rate |
| `algorithm_spec` | `AlgorithmSpec` | Input algorithm (for provenance) |
| `hardware_model` | `HardwareModel` | Input hardware target (for provenance) |
| `qec_scheme_name` | `str` | QEC scheme used |
| `backend_name` | `str` | Which backend produced this estimate |

**Derived properties:**
- `runtime_human` → e.g., "3h 42m", "156d 8h"
- `space_time_volume` → `total_physical_qubits * runtime_seconds`

### 4.7 Backend ABCs

**Location:** `backends/base.py`

```
LogicalEstimator (ABC)
├── name: str
├── estimate(AlgorithmSpec) -> LogicalCounts
└── is_available() -> bool

PhysicalEstimator (ABC)
├── name: str
├── estimate(LogicalCounts, HardwareModel, QECScheme, ErrorBudget, AlgorithmSpec) -> PhysicalEstimate
├── is_available() -> bool
└── supports_qec(QECScheme) -> bool   [default: True]
```

### 4.8 AlgorithmTemplate ABC

**Location:** `templates/base.py`

```
AlgorithmTemplate (ABC)
├── name: str
├── family: str
├── description: str
├── generate(**params) -> AlgorithmSpec
└── parameter_schema() -> dict[str, {type, default, description, ...}]
```

Built-in templates:

| Template | Family | Key Parameters |
|----------|--------|----------------|
| `shor` | cryptanalysis | `n_bits` (int, default 2048), `construction` ("gidney_ekera" or "textbook") |
| `qpe` | simulation | `num_qubits` (int), `precision_bits` (int) |
| `chemistry` | chemistry | `num_orbitals` (int), `method` ("double_factorization"/"thc"/"sparse") |
| `hamiltonian_sim` | simulation | `num_qubits` (int), `evolution_time` (float), `method` ("trotter"/"qsp"/"qubitization") |
| `grover` | search | `search_space_bits` (int), `num_solutions` (int, default 1) |

---

## 5. Backend Discovery and Selection

**Location:** `backends/registry.py`

Backends are discovered via two mechanisms:
1. **Built-in:** `MockLogicalEstimator` and `AnalyticalPhysicalEstimator` are always available
2. **Entry points:** Installed plugins register via `pyproject.toml` entry points

```toml
[project.entry-points."quompass.logical_estimators"]
qualtran = "quompass.backends.qualtran.adapter:QualtranLogicalEstimator"

[project.entry-points."quompass.physical_estimators"]
azure = "quompass.backends.azure.adapter:AzurePhysicalEstimator"
```

**Auto-selection priority** (first available wins):
- Logical: qualtran > pyliqtr > mock
- Physical: azure > mqt > analytical

Each backend's `is_available()` checks whether its dependencies are importable. Failed loads are logged at DEBUG level and skipped.

**Four entry-point groups:**
- `quompass.logical_estimators`
- `quompass.physical_estimators`
- `quompass.qec_schemes`
- `quompass.algorithm_templates`

---

## 6. Physical Estimation Logic (Analytical Backend)

The built-in `AnalyticalPhysicalEstimator` implements the core estimation math, used when no external backend is available:

1. **Resolve error budget** → split epsilon across logical, distillation, rotation
2. **Get physical error rate** → `p = worst_case_clifford_error` from `QubitParams`
3. **Compute required logical error rate** → `epsilon_logical / (n_qubits * logical_depth)`
4. **Find minimum code distance** → `QECScheme.min_code_distance(target, p)`
5. **Compute physical qubit cost** → `n_qubits * qec.physical_qubits_per_logical(d)`
6. **Estimate T factories** → simplified 15-to-1 distillation model:
   - Output error per round: `35 * p_in^3`
   - Cascade up to 5 rounds until target error met
   - Factory count sized to T-state production rate
   - Skipped entirely when `qec.transversal_magic_states` is `True`: magic
     states are produced in-place (cultivation), so a CCZ counts as one
     logical cycle rather than four T equivalents and there is no factory
7. **Compute runtime** → `logical_depth * logical_cycle_time(d)`
8. **Assemble PhysicalEstimate** with full breakdown

---

## 7. Exploration and Optimization

### 7.1 Grid Exploration

**Location:** `exploration/`

`ExplorationSpace` defines a grid over:
- Hardware targets (list of preset names or `HardwareModel` instances)
- QEC schemes (list of names or `QECScheme` instances)
- Error budgets (list of floats)

`explore(space)` evaluates all combinations, producing `ExplorationResult` with:
- All `DesignPoint` objects (successful and failed)
- `pareto_front()` → Pareto-optimal points (default: minimize qubits + runtime)
- `sensitivity()` → one-at-a-time parameter sensitivity
- `best(metric)` → single best point
- `print_table()` / `plot()` → Rich tables and matplotlib visualization

### 7.2 NSGA-II Optimization

**Location:** `optimization/`
**Requires:** `pymoo >= 0.6`

`OptimizationSpace` adds continuous variables to the grid:
- Error budget total (continuous range)
- Error budget split ratios (continuous, 2 variables → 3-way split)
- Hardware and QEC as categorical indices

`optimize(space)` runs pymoo's NSGA-II with mixed-variable operators:
- Population size, generation count, random seed configurable
- Objectives: any combination of metrics (minimize/maximize)
- Returns `OptimizationResult` with Pareto front and all evaluated points
- Converts to `ExplorationResult` for visualization compatibility

---

## 8. CLI

**Location:** `cli/`
**Framework:** Typer + Rich

| Command | Description |
|---------|-------------|
| `quompass estimate` | Single-point resource estimation |
| `quompass explore` | Grid search over hardware/QEC/error budget |
| `quompass optimize` | NSGA-II multi-objective optimization |
| `quompass catalog` | List available templates, hardware, QEC, backends |

All commands accept:
- `--template <name>` + `--param key=value` (repeatable) — or `--spec path.yaml`
- `--hardware <preset_or_path>` — preset name or YAML file
- `--qec <name_or_path>` — scheme name or YAML file
- `--error-budget <float>`
- `--output <format>` — table, json, yaml

---

## 9. I/O and Serialization

**Location:** `io/__init__.py`

| Function | Description |
|----------|-------------|
| `load_algorithm(path)` | Load `AlgorithmSpec` from YAML |
| `load_hardware(path)` | Load `HardwareModel` from YAML |
| `load_qec(path)` | Load `FormulaQEC` from YAML |
| `save_estimate(result, path)` | Save `PhysicalEstimate` to YAML |

All core types support `to_dict()` / `from_dict()` round-trip serialization.

---

## 10. Dependency Graph

```
Core (zero external deps beyond stdlib):
  core/types.py, core/algorithm.py, core/hardware.py,
  core/qec.py, core/error_budget.py, core/results.py

Runtime (always installed):
  numpy >= 1.24
  typer >= 0.9
  rich >= 13.0
  pyyaml >= 6.0

Optional backends (lazy-imported):
  qualtran >= 0.4       → QualtranLogicalEstimator
  qsharp >= 1.0         → AzurePhysicalEstimator
  pyLIQTR >= 0.3        → PyLIQTRLogicalEstimator (stub)
  mqt.core >= 2.0       → MQTPhysicalEstimator (stub)

Optional features:
  pymoo >= 0.6          → NSGA-II optimization
  matplotlib >= 3.7     → scatter plots
  plotly >= 5.15        → interactive plots

Development:
  pytest >= 7.0, pytest-cov >= 4.0, mypy >= 1.0, ruff >= 0.1
```

All optional dependencies are lazy-imported. The core library and analytical backend work with only the four runtime dependencies.

---

## 11. Extension Points

### Adding a new backend

1. Implement `LogicalEstimator` or `PhysicalEstimator` ABC
2. Implement `is_available()` to check for dependencies
3. Register via entry point in your package's `pyproject.toml`:
   ```toml
   [project.entry-points."quompass.physical_estimators"]
   my_backend = "my_package.adapter:MyPhysicalEstimator"
   ```

### Adding a new QEC scheme

Option A — Python class: subclass `QECScheme`, register via entry point.
Option B — YAML formula: create a YAML file with FormulaQEC fields, load with `--qec path.yaml`.

### Adding a new algorithm template

1. Subclass `AlgorithmTemplate`
2. Implement `generate(**params) -> AlgorithmSpec` and `parameter_schema()`
3. Register via `quompass.algorithm_templates` entry point

### Providing LogicalCounts directly

Skip templates entirely — construct `AlgorithmSpec` with `LogicalCounts` from any source (published papers, hand calculations, external tools):

```python
spec = AlgorithmSpec(
    name="My Algorithm",
    logical_counts=LogicalCounts(num_qubits=100, t_count=1_000_000),
)
result = quompass.estimate(spec)
```

---

## 12. Current Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Core types | Complete | All frozen dataclasses, serialization tested |
| Mock/analytical backends | Complete | Zero-dependency, used in all unit tests |
| Qualtran backend | Partial | Bloq bridge only handles Shor; falls back for others |
| Azure backend | Incomplete | Adapter file is truncated; estimate() not implemented |
| pyLIQTR backend | Stub | Raises NotImplementedError |
| MQT backend | Stub | Raises NotImplementedError |
| Algorithm templates (5) | Complete | Shor, QPE, Chemistry, Hamiltonian Sim, Grover |
| QEC schemes (3) | Complete | Surface code, Floquet code, Color code + FormulaQEC |
| Hardware presets (6) | Complete | SC, Trapped Ion, Majorana (realistic + optimistic) |
| Exploration | Complete | Grid search, Pareto, sensitivity |
| Optimization | Complete | NSGA-II via pymoo |
| CLI | Complete | estimate, explore, optimize, catalog |
| I/O | Complete | YAML load/save |
| Visualization | Complete | Rich tables + matplotlib |
