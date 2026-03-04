# Quompass User Guide

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Python API](#python-api)
  - [quompass.estimate()](#quompassestimate)
  - [Algorithm Templates](#algorithm-templates)
  - [Result Objects](#result-objects)
- [Design Space Exploration](#design-space-exploration)
  - [ExplorationSpace](#explorationspace)
  - [Pareto Front](#pareto-front)
  - [Sensitivity Analysis](#sensitivity-analysis)
  - [Plotting](#plotting)
- [Multi-Objective Optimization](#multi-objective-optimization)
  - [When to Use Optimize vs Explore](#when-to-use-optimize-vs-explore)
  - [OptimizationSpace](#optimizationspace)
  - [Running Optimization](#running-optimization)
  - [Interpreting Results](#interpreting-results)
- [Custom QEC Schemes](#custom-qec-schemes)
- [YAML Workflows](#yaml-workflows)
  - [Algorithm Spec YAML](#algorithm-spec-yaml)
  - [Custom Hardware YAML](#custom-hardware-yaml)
  - [Custom QEC YAML](#custom-qec-yaml)
  - [Exporting Results](#exporting-results)
- [CLI Reference](#cli-reference)
  - [quompass estimate](#quompass-estimate)
  - [quompass explore](#quompass-explore)
  - [quompass catalog](#quompass-catalog)
- [Plugin Architecture](#plugin-architecture)
- [Hardware Presets Reference](#hardware-presets-reference)

---

## Architecture Overview

quompass uses a two-stage pipeline that separates logical resource estimation from physical resource estimation:

```
                        Logical Stage                Physical Stage
                    ┌─────────────────┐          ┌──────────────────┐
AlgorithmSpec ────> │ LogicalEstimator │ ───────> │ PhysicalEstimator │ ────> PhysicalEstimate
  (template or      │  (Qualtran/mock) │          │  (Azure/analytical)│
   custom spec)     └─────────────────┘          └──────────────────┘
                           │                              │
                      LogicalCounts                  PhysicalEstimate
                      (portable)                     (final result)
```

**LogicalCounts** is the portable interchange format -- a frozen dataclass containing:

| Field | Type | Description |
|-------|------|-------------|
| `num_qubits` | int | Number of logical qubits |
| `t_count` | int | Number of T gates |
| `ccz_count` | int | Number of CCZ/Toffoli gates |
| `rotation_count` | int | Number of arbitrary rotations |
| `rotation_depth` | int | Depth of rotation sub-circuits |
| `measurement_count` | int | Number of measurements |
| `clifford_count` | int | Number of Clifford gates |

You can bring your own `LogicalCounts` from any source: Qualtran Bloqs, published papers, or hand calculations.

---

## Python API

### quompass.estimate()

The primary entry point. Handles type coercion, backend selection, and the full pipeline.

```python
quompass.estimate(
    algorithm: AlgorithmSpec,
    hardware: HardwareModel | HardwarePreset | str = "gate_ns_e3",
    qec: QECScheme | str = "surface_code",
    error_budget: ErrorBudget | float = 0.001,
    logical_backend: str = "auto",
    physical_backend: str = "auto",
) -> PhysicalEstimate
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `algorithm` | AlgorithmSpec | required | The algorithm to estimate |
| `hardware` | str or HardwareModel | `"gate_ns_e3"` | Hardware target (preset name or instance) |
| `qec` | str or QECScheme | `"surface_code"` | QEC scheme (name or instance) |
| `error_budget` | float or ErrorBudget | `0.001` | Total error budget (float creates uniform split) |
| `logical_backend` | str | `"auto"` | Logical estimator (`"auto"`, `"mock"`, `"qualtran"`) |
| `physical_backend` | str | `"auto"` | Physical estimator (`"auto"`, `"analytical"`, `"azure"`) |

**Example:**

```python
import quompass
from quompass.templates.shor import shor

result = quompass.estimate(
    shor(n_bits=2048),
    hardware="gate_ns_e4",
    qec="surface_code",
    error_budget=0.001,
)
```

### Algorithm Templates

Each template is a convenience function that returns an `AlgorithmSpec` with computed logical resource counts.

#### shor -- Integer Factoring

```python
from quompass.templates.shor import shor

spec = shor(n_bits=2048, construction="gidney_ekera")
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `n_bits` | int | 2048 | Bits in the integer to factor |
| `construction` | str | `"gidney_ekera"` | `"gidney_ekera"` or `"textbook"` |

Resource model: Gidney & Ekera (2021) -- ~2n qubits, ~0.3n^3 Toffoli gates.

#### qpe -- Quantum Phase Estimation

```python
from quompass.templates.qpe import qpe

spec = qpe(num_qubits=50, precision_bits=20)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `num_qubits` | int | 10 | System qubits (unitary size) |
| `precision_bits` | int | 20 | Phase register precision bits |
| `num_rotations` | int | 0 | Additional rotations beyond inverse QFT |

Resource model: standard QPE with ~2^precision controlled-U operations.

#### hamiltonian_sim -- Hamiltonian Simulation

```python
from quompass.templates.hamiltonian_sim import hamiltonian_sim

spec = hamiltonian_sim(num_qubits=50, evolution_time=10.0, method="qsp")
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `num_qubits` | int | 50 | System qubits |
| `num_terms` | int | 100 | Hamiltonian terms |
| `evolution_time` | float | 1.0 | Simulation time |
| `precision` | float | 1e-3 | Target precision |
| `method` | str | `"trotter"` | `"trotter"`, `"qsp"`, or `"qubitization"` |

Methods and their scaling:
- **trotter**: 2nd-order Trotter-Suzuki, O(L^1.5 * t^1.5 / sqrt(eps)) steps
- **qsp**: Quantum Signal Processing, O(L*t + log(1/eps)) -- near-optimal
- **qubitization**: LCU-based, O(L*t/eps) steps

#### chemistry -- Quantum Chemistry

```python
from quompass.templates.chemistry import chemistry

spec = chemistry(num_orbitals=108, method="double_factorization")
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `num_orbitals` | int | 54 | Spatial orbitals |
| `num_electrons` | int | 0 | Electrons (0 = auto-fill to num_orbitals) |
| `method` | str | `"double_factorization"` | `"double_factorization"`, `"thc"`, or `"sparse"` |

Resource models from published estimates:
- **double_factorization**: Lee et al. (2021) -- O(N^3) Toffoli gates
- **thc**: Tensor hypercontraction -- better constants for large systems
- **sparse**: Berry et al. (2019) -- leverages Hamiltonian sparsity

#### grover -- Grover's Search

```python
from quompass.templates.grover import grover

spec = grover(search_space_bits=30, num_solutions=1)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `search_space_bits` | int | 20 | log2 of search space size |
| `num_solutions` | int | 1 | Expected number of solutions |
| `num_oracle_t_gates` | int | 0 | Oracle T-gate cost (0 = auto-estimate) |

Resource model: pi/4 * sqrt(N/M) Grover iterations.

### Result Objects

#### PhysicalEstimate

The primary output of `quompass.estimate()`. Frozen dataclass with:

```python
result = quompass.estimate(spec)

# Top-level summary
result.total_physical_qubits       # int: total physical qubits needed
result.runtime_seconds             # float: wall-clock time in seconds
result.runtime_human               # str: human-readable ("3h 42m")
result.rqops                       # float: reliable quantum operations/sec
result.space_time_volume           # float: qubits * seconds

# Breakdown
result.algorithmic_logical_qubits  # int: logical qubits for the algorithm
result.physical_qubits_for_algorithm    # int: physical qubits for algorithm
result.physical_qubits_for_t_factories  # int: physical qubits for T factories
result.num_t_states                # int: total T states consumed

# Logical qubit details
result.logical_qubit.code_distance       # int
result.logical_qubit.physical_qubits     # int: physical qubits per logical
result.logical_qubit.logical_cycle_time  # float: seconds
result.logical_qubit.logical_error_rate  # float

# T factory details (None if no T gates)
result.t_factory.num_factories               # int
result.t_factory.physical_qubits_per_factory # int
result.t_factory.factory_runtime             # float: seconds
result.t_factory.output_error_rate           # float

# Error budget
result.error_budget.total        # float
result.error_budget.logical      # float
result.error_budget.distillation # float
result.error_budget.rotation     # float

# Provenance
result.algorithm_spec      # AlgorithmSpec
result.hardware_model      # HardwareModel
result.qec_scheme_name     # str
result.backend_name        # str

# Serialization
result.summary_dict()      # dict for tabular display
```

#### Visualization

```python
from quompass.viz.summary import print_estimate_summary, print_estimate_detail

print_estimate_summary(result)  # Compact Rich table
print_estimate_detail(result)   # Full breakdown with logical qubit + T factory details
```

---

## Design Space Exploration

Sweep across hardware, QEC, and error budget combinations to find optimal configurations.

### ExplorationSpace

Define the grid of parameters to explore:

```python
from quompass.templates.shor import shor
from quompass.exploration import ExplorationSpace, explore

space = ExplorationSpace(
    algorithm=shor(n_bits=2048),
    hardware=["gate_ns_e3", "gate_ns_e4", "gate_us_e3"],
    qec=["surface_code", "color_code"],
    error_budgets=[0.01, 0.001, 0.0001],
)
print(f"Grid size: {space.size}")  # 3 * 2 * 3 = 18 combinations

result = explore(space)
result.print_table()
```

The `explore()` function evaluates every combination, catching errors gracefully. Failed combinations (e.g., error rate above QEC threshold) are recorded but don't crash the run.

### ExplorationResult

The result object provides several analysis methods:

```python
# All points
result.all_points         # list[DesignPoint]
result.succeeded          # list[DesignPoint] (estimation succeeded)
result.failed             # list[DesignPoint] (estimation failed)
result.num_succeeded      # int
result.num_failed         # int

# Best single point
best = result.best(metric="total_physical_qubits", minimize=True)
print(f"Best: {best.label()} -> {best.total_physical_qubits:,.0f} qubits")

# Pareto front (see below)
front = result.pareto_front()

# Sensitivity analysis (see below)
sens = result.sensitivity()
```

### Pareto Front

The Pareto front identifies configurations where no other configuration is better in all objectives simultaneously. Useful for understanding the tradeoff between physical qubits and runtime.

```python
front = result.pareto_front(
    objectives={
        "total_physical_qubits": "minimize",
        "runtime_seconds": "minimize",
    }
)

front.print_table()

# Access individual points
for pt in front:
    print(f"{pt.label()}: {pt.total_physical_qubits:,.0f} qubits, {pt.runtime_seconds:.1f}s")

# Serialize to dicts (for export to pandas, CSV, etc.)
rows = front.to_dicts()
```

### Sensitivity Analysis

One-at-a-time (OAT) sensitivity analysis shows which parameter dimension has the largest impact on a metric:

```python
sens = result.sensitivity(metric="total_physical_qubits")

sens.print_table()
print(f"Most sensitive: {sens.most_sensitive_dimension()}")

# Access raw data
for dim_name, entries in sens.dimensions.items():
    print(f"\n{dim_name}:")
    for entry in entries:
        print(f"  {entry.param_value}: {entry.metric_value:,.0f} ({entry.pct_change:+.1f}%)")
```

You can also specify a custom baseline:

```python
sens = result.sensitivity(
    baseline={"hardware": "gate_ns_e4", "qec": "surface_code", "error_budget": 0.001},
    metric="runtime_seconds",
)
```

### Plotting

Requires matplotlib (`pip install quompass[viz]`):

```python
# Scatter plot with Pareto front overlay
result.plot(
    x="total_physical_qubits",
    y="runtime_seconds",
    show_pareto=True,
    save_path="exploration.png",
)

# Sensitivity bar chart
sens = result.sensitivity()
sens.plot(save_path="sensitivity.png")
```

---

## Multi-Objective Optimization

Use NSGA-II genetic algorithm optimization for continuous design space exploration, powered by [pymoo](https://pymoo.org/).

### When to Use Optimize vs Explore

| Feature | `quompass explore` (Grid) | `quompass optimize` (NSGA-II) |
|---------|----------------------|---------------------------|
| Error budget | Discrete values | Continuous range |
| Budget splits | Default (uniform) | Optimized (logical/distillation/rotation) |
| Coverage | Exhaustive | Heuristic (evolutionary) |
| Speed | Fast for small grids | Better for large spaces |
| Use case | Quick comparison | Fine-tuning, large sweeps |

Use **explore** when you want exhaustive comparison of a few discrete configurations. Use **optimize** when you want to find the best error budget within a continuous range, or when the space is too large for grid search.

### OptimizationSpace

Define the search space with continuous ranges and categorical choices:

```python
from quompass.templates.shor import shor
from quompass.optimization import OptimizationSpace, optimize

space = OptimizationSpace(
    algorithm=shor(n_bits=2048),
    hardware=["gate_ns_e3", "gate_ns_e4", "gate_us_e3"],
    qec=["surface_code", "color_code"],
    error_budget_range=(1e-4, 0.1),   # continuous range
    objectives={
        "total_physical_qubits": "minimize",
        "runtime_seconds": "minimize",
    },
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `algorithm` | AlgorithmSpec | required | Algorithm to optimize |
| `hardware` | list[str] | `["gate_ns_e3"]` | Hardware choices (categorical) |
| `qec` | list[str] | `["surface_code"]` | QEC choices (categorical) |
| `error_budget_range` | tuple[float, float] | `(1e-4, 0.1)` | Continuous error budget range |
| `objectives` | dict[str, str] | qubits + runtime | Metrics to optimize |

### Running Optimization

```python
result = optimize(
    space,
    generations=50,        # NSGA-II generations
    population_size=100,   # individuals per generation
    seed=42,               # reproducibility
)
```

The optimizer explores:
- **Error budget total** continuously within the specified range
- **Error budget splits** (logical/distillation/rotation ratios) as continuous variables
- **Hardware** and **QEC** as categorical choices

### Interpreting Results

`OptimizationResult` provides the same API as `ExplorationResult`:

```python
# Pareto front
front = result.pareto_front()
front.print_table()

# Best single point
best = result.best(metric="total_physical_qubits")

# All successful points
for pt in result.succeeded:
    print(f"{pt.label()}: {pt.total_physical_qubits:,.0f} qubits")

# Convert to ExplorationResult for existing viz tools
er = result.to_exploration_result()
er.plot(save_path="optimization.png")
```

**Requires:** `pip install 'quompass[optimize]'` (installs pymoo).

---

## Custom QEC Schemes

Use `FormulaQEC` to define QEC schemes via formula strings, without writing Python classes:

```python
from quompass import FormulaQEC

# Define a hypothetical qLDPC code
my_code = FormulaQEC(
    name="my_qldpc",
    threshold=0.01,
    prefactor=0.03,
    qubits_formula="12 * d",           # Linear in code distance
    cycle_time_formula="6 * t_2q * d",  # Depends on 2-qubit gate time
)

# Use it in estimation
import quompass
from quompass.templates.shor import shor

result = quompass.estimate(shor(n_bits=2048), qec=my_code)
```

### Formula Variables

Formulas can use these variables:

| Variable | Description |
|----------|-------------|
| `d` | Code distance |
| `t_1q` | One-qubit gate time (seconds) |
| `t_2q` | Two-qubit gate time (seconds) |
| `t_meas` | Measurement time (seconds) |
| `t_jm` | Joint measurement time (Majorana hardware, seconds) |

Supported functions: `sqrt`, `log`, `log2`, `ceil`, `floor`, `round`, `abs`, `max`, `min`, `exp`, `sin`, `cos`.

### FormulaQEC Parameters

```python
FormulaQEC(
    name: str,              # Scheme name
    threshold: float,       # Error threshold (e.g., 0.01)
    prefactor: float,       # Error rate prefactor (e.g., 0.03)
    qubits_formula: str,    # Physical qubits per logical qubit (function of d)
    cycle_time_formula: str, # Logical cycle time (function of d, t_1q, t_2q, etc.)
    distance_coefficient_power: float = 0.0,  # Power of d in error rate formula
)
```

The logical error rate is computed as: `prefactor * d^power * (p/threshold)^((d+1)/2)`, where `p` is the worst-case physical error rate.

### Built-in FormulaQEC: Color Code

```python
from quompass import color_code

cc = color_code()  # 6.6.6 color code with threshold 0.0077, ~4.5*d^2 qubits
```

---

## YAML Workflows

quompass supports YAML files for algorithm specs, hardware models, QEC schemes, and result export. This enables reproducible workflows, version-controlled configurations, and easy sharing.

### Algorithm Spec YAML

Define an algorithm spec in YAML and pass it to `quompass estimate --spec`:

```yaml
# shor_2048.yaml
name: "Shor's factoring (n=2048, Gidney-Ekera)"
description: "Factor a 2048-bit integer"
algorithm_family: cryptanalysis
source: template:shor

problem_parameters:
  n_bits: 2048
  construction: gidney_ekera

logical_counts:
  num_qubits: 4141
  t_count: 12
  rotation_count: 12
  rotation_depth: 12
  ccz_count: 2576980377
  measurement_count: 4096
  clifford_count: 0
```

```bash
quompass estimate --spec shor_2048.yaml
```

**Python API:**

```python
from quompass.io import load_algorithm, save_yaml

# Load
spec = load_algorithm("shor_2048.yaml")

# Save
save_yaml(spec.to_dict(), "output_spec.yaml")
```

### Custom Hardware YAML

Define custom qubit parameters in YAML and pass via `--hardware`:

```yaml
# custom_hardware.yaml
name: next_gen_sc
description: "Next-gen superconducting"

qubit_params:
  name: next_gen_sc
  instruction_set: gate_based     # or "majorana"
  one_qubit_gate_time: 25.0e-9
  two_qubit_gate_time: 40.0e-9
  one_qubit_measurement_time: 80.0e-9
  t_gate_time: 40.0e-9
  one_qubit_gate_error_rate: 1.0e-5
  two_qubit_gate_error_rate: 1.0e-5
  one_qubit_measurement_error_rate: 1.0e-5
  t_gate_error_rate: 1.0e-5
```

```bash
quompass estimate --template shor --param n_bits=2048 --hardware custom_hardware.yaml
```

**Python API:**

```python
from quompass.io import load_hardware

hw = load_hardware("custom_hardware.yaml")
result = quompass.estimate(spec, hardware=hw)
```

### Custom QEC YAML

Define a FormulaQEC scheme in YAML and pass via `--qec`:

```yaml
# custom_qec.yaml
name: example_qldpc
threshold: 0.01
prefactor: 0.03
qubits_formula: "12 * d"
cycle_time_formula: "6 * t_2q * d"
distance_coefficient_power: 0.0
```

```bash
quompass estimate --template shor --param n_bits=2048 --qec custom_qec.yaml
```

**Python API:**

```python
from quompass.io import load_qec

qec = load_qec("custom_qec.yaml")
result = quompass.estimate(spec, qec=qec)
```

### Exporting Results

Export estimation results as YAML using `--output yaml` or the Python API:

```bash
# CLI: export as YAML
quompass estimate --template shor --param n_bits=2048 --output yaml > result.yaml

# Exploration results
quompass explore --template shor --param n_bits=512 --hardware gate_ns_e3,gate_ns_e4 --output yaml
```

**Python API:**

```python
from quompass.io import save_estimate, save_yaml

result = quompass.estimate(spec)

# Full nested result
save_estimate(result, "result.yaml")

# Or save the summary dict
save_yaml(result.summary_dict(), "summary.yaml")
```

The exported YAML includes nested sections for summary, breakdown, logical qubit, T factory, error budget, error rates, and provenance (algorithm spec, hardware model, QEC scheme).

---

## CLI Reference

### quompass estimate

Estimate physical resources for a quantum algorithm.

```
quompass estimate [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--template` | | Algorithm template name |
| `--spec` | | Path to YAML algorithm spec file |
| `--param KEY=VALUE` | | Template parameters (repeatable) |
| `--hardware` | `gate_ns_e3` | Hardware preset name or YAML file path (`.yaml`/`.yml`) |
| `--qec` | `surface_code` | QEC scheme name or YAML file path (`.yaml`/`.yml`) |
| `--error-budget` | `0.001` | Total error budget |
| `--output` | `table` | Output format: `table`, `json`, `yaml`, `detail` |

**Examples:**

```bash
# Shor's algorithm with optimistic hardware
quompass estimate --template shor --param n_bits=2048 --hardware gate_ns_e4

# Chemistry with color code QEC
quompass estimate --template chemistry --param num_orbitals=108 \
    --param method=double_factorization --qec color_code

# Detailed output
quompass estimate --template qpe --param num_qubits=50 --output detail

# YAML output
quompass estimate --template shor --param n_bits=2048 --output yaml

# Custom hardware and QEC from YAML files
quompass estimate --template shor --param n_bits=2048 \
    --hardware examples/custom_hardware.yaml \
    --qec examples/custom_qec.yaml

# Load algorithm spec from YAML
quompass estimate --spec examples/shor_2048.yaml --output yaml
```

### quompass explore

Explore the design space across hardware, QEC, and error budget combinations.

```
quompass explore [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--template` | (required) | Algorithm template name |
| `--param KEY=VALUE` | | Template parameters (repeatable) |
| `--hardware` | `gate_ns_e3,gate_us_e3` | Comma-separated hardware presets |
| `--qec` | `surface_code` | Comma-separated QEC schemes |
| `--error-budget` | `0.001` | Comma-separated error budgets |
| `--output` | `table` | `table`, `pareto`, `json`, `yaml`, `detail` |
| `--pareto-x` | `total_physical_qubits` | Pareto X-axis metric |
| `--pareto-y` | `runtime_seconds` | Pareto Y-axis metric |
| `--plot` | | Save plot to file path |
| `--sensitivity` | false | Include sensitivity analysis |

**Examples:**

```bash
# Full sweep with sensitivity analysis
quompass explore --template shor --param n_bits=2048 \
    --hardware gate_ns_e3,gate_ns_e4,gate_us_e3 \
    --qec surface_code,color_code \
    --error-budget 0.01,0.001,0.0001 \
    --sensitivity

# Pareto front output
quompass explore --template chemistry --param num_orbitals=54 \
    --hardware gate_ns_e3,gate_ns_e4 \
    --error-budget 0.01,0.001 \
    --output pareto

# Save exploration plot
quompass explore --template grover --param search_space_bits=30 \
    --hardware gate_ns_e3,gate_ns_e4 \
    --error-budget 0.01,0.001,0.0001 \
    --plot exploration.png
```

### quompass optimize

Run NSGA-II multi-objective optimization across the design space.

```
quompass optimize [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--template` | (required) | Algorithm template name |
| `--param KEY=VALUE` | | Template parameters (repeatable) |
| `--hardware` | `gate_ns_e3,gate_ns_e4` | Comma-separated hardware presets |
| `--qec` | `surface_code` | Comma-separated QEC schemes |
| `--error-budget-min` | `0.0001` | Min error budget (continuous range) |
| `--error-budget-max` | `0.1` | Max error budget (continuous range) |
| `--objective` | qubits + runtime | Objectives as `metric:direction` (repeatable) |
| `--generations` | `50` | NSGA-II generations |
| `--population-size` | `100` | Population size per generation |
| `--seed` | | Random seed for reproducibility |
| `--output` | `table` | `table`, `pareto`, `json`, `yaml` |
| `--plot` | | Save plot to file path |

**Examples:**

```bash
# Basic optimization
quompass optimize --template shor --param n_bits=2048 \
    --hardware gate_ns_e3,gate_ns_e4 --qec surface_code \
    --generations 50 --population-size 100

# Quick test run
quompass optimize --template shor --param n_bits=64 \
    --hardware gate_ns_e3,gate_ns_e4 --qec surface_code \
    --generations 5 --population-size 10

# Pareto front output with reproducibility
quompass optimize --template shor --param n_bits=2048 \
    --hardware gate_ns_e3,gate_ns_e4 --qec surface_code,color_code \
    --output pareto --seed 42

# Custom objectives
quompass optimize --template chemistry --param num_orbitals=54 \
    --objective space_time_volume:minimize \
    --generations 30
```

### quompass catalog

List available templates, hardware presets, QEC schemes, and backends.

```bash
quompass catalog templates              # List all algorithm templates
quompass catalog templates shor         # Show details for a specific template
quompass catalog hardware               # List hardware presets
quompass catalog qec                    # List QEC schemes
quompass catalog backends               # List estimation backends and availability
```

---

## Plugin Architecture

quompass uses Python `entry_points` for plugin discovery. Third-party packages can register new templates, backends, and QEC schemes.

### Adding a Custom Template

Create a class extending `AlgorithmTemplate` and register it in your package's `pyproject.toml`:

```python
# my_package/templates.py
from quompass.templates.base import AlgorithmTemplate
from quompass.core.algorithm import AlgorithmSpec, LogicalCounts

class MyTemplate(AlgorithmTemplate):
    @property
    def name(self) -> str:
        return "my_algorithm"

    @property
    def family(self) -> str:
        return "custom"

    @property
    def description(self) -> str:
        return "My custom algorithm"

    def generate(self, **params) -> AlgorithmSpec:
        n = int(params.get("size", 100))
        return AlgorithmSpec(
            name=f"My Algorithm (n={n})",
            logical_counts=LogicalCounts(num_qubits=n, t_count=n * 1000),
            source="template:my_algorithm",
        )

    def parameter_schema(self) -> dict:
        return {
            "size": {"type": "int", "default": 100, "description": "Problem size"},
        }
```

```toml
# pyproject.toml
[project.entry-points."quompass.algorithm_templates"]
my_algorithm = "my_package.templates:MyTemplate"
```

After installing your package, `quompass catalog templates` will list `my_algorithm`.

### Adding a Custom Backend

Extend `LogicalEstimator` or `PhysicalEstimator`:

```toml
[project.entry-points."quompass.logical_estimators"]
my_backend = "my_package.backend:MyLogicalEstimator"

[project.entry-points."quompass.physical_estimators"]
my_physical = "my_package.backend:MyPhysicalEstimator"
```

### Registered Backend Stubs

quompass includes stub adapters for backends that are not yet fully implemented but are registered for future use:

| Backend | Type | Entry Point | Status |
|---------|------|-------------|--------|
| **pyLIQTR** | Logical estimator | `quompass.logical_estimators` | Stub (install pyLIQTR to enable) |
| **MQT** | Physical estimator | `quompass.physical_estimators` | Stub (install mqt.core to enable) |

These stubs appear in `quompass catalog backends` as "(unavailable)". When the underlying package is installed, they will be discovered automatically. Community contributions to implement the adapter logic are welcome.

### Adding a Custom QEC Scheme

Register a `FormulaQEC` factory or a `QECScheme` subclass:

```toml
[project.entry-points."quompass.qec_schemes"]
my_code = "my_package.qec:MyQECScheme"
```

---

## Hardware Presets Reference

Detailed parameters for all built-in hardware presets:

### gate_ns_e3 (Superconducting Realistic)

| Parameter | Value |
|-----------|-------|
| Gate times (1q/2q) | 50 ns |
| Measurement time | 100 ns |
| Clifford error rate | 10^-3 |
| T gate error rate | 10^-3 |

### gate_ns_e4 (Superconducting Optimistic)

| Parameter | Value |
|-----------|-------|
| Gate times (1q/2q) | 50 ns |
| Measurement time | 100 ns |
| Clifford error rate | 10^-4 |
| T gate error rate | 10^-4 |

### gate_us_e3 (Trapped Ion Realistic)

| Parameter | Value |
|-----------|-------|
| Gate times (1q/2q) | 100 us |
| Measurement time | 100 us |
| Clifford error rate | 10^-3 |
| T gate error rate | 10^-6 |

### gate_us_e4 (Trapped Ion Optimistic)

| Parameter | Value |
|-----------|-------|
| Gate times (1q/2q) | 100 us |
| Measurement time | 100 us |
| Clifford error rate | 10^-4 |
| T gate error rate | 10^-6 |

### maj_ns_e4 (Majorana Realistic)

| Parameter | Value |
|-----------|-------|
| Gate times (1q/2q) | 100 ns |
| Measurement time | 100 ns |
| Joint measurement time | 100 ns |
| Clifford error rate | 10^-4 |
| T gate error rate | 5% |

### maj_ns_e6 (Majorana Optimistic)

| Parameter | Value |
|-----------|-------|
| Gate times (1q/2q) | 100 ns |
| Measurement time | 100 ns |
| Joint measurement time | 100 ns |
| Clifford error rate | 10^-6 |
| T gate error rate | 1% |
