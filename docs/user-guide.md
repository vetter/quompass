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
- [Walkthrough: Chemistry Resource Estimation](#walkthrough-chemistry-resource-estimation)
  - [Step 1: Define the Problem](#step-1-define-the-problem)
  - [Step 2: Run a Single Estimate](#step-2-run-a-single-estimate)
  - [Step 3: Compare Methods](#step-3-compare-methods)
  - [Step 4: Explore the Design Space](#step-4-explore-the-design-space)
  - [Step 5: Analyze Sensitivity](#step-5-analyze-sensitivity)
  - [Step 6: Create a Custom QEC Scheme](#step-6-create-a-custom-qec-scheme)
  - [Step 7: Export and Reproduce](#step-7-export-and-reproduce)
- [CLI Reference](#cli-reference)
  - [quompass estimate](#quompass-estimate)
  - [quompass explore](#quompass-explore)
  - [quompass optimize](#quompass-optimize)
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
    transversal_magic_states: bool = False,   # Native transversal T/CCZ (no factory)
)
```

The logical error rate is computed as: `prefactor * d^power * (p/threshold)^((d+1)/2)`, where `p` is the worst-case physical error rate.

### Built-in FormulaQEC: Color Code

```python
from quompass import color_code

cc = color_code()  # 6.6.6 color code with threshold 0.0077, ~4.5*d^2 qubits
```

### Transversal Magic States

By default a QEC scheme requires magic-state distillation: every T and CCZ/Toffoli
gate is supplied by a 15-to-1 distillation factory, and a CCZ counts as four T-gate
equivalents. For surface-code estimates of large algorithms these factories dominate
the physical qubit count.

High-rate qLDPC architectures instead apply T and CCZ gates as **native transversal
logical operations** with magic-state cultivation — no dedicated distillation factory.
Set `transversal_magic_states=True` to model this. When enabled, the analytical
estimator:

- reports **no T factory** (`t_factory is None`, zero factory qubits); and
- counts each CCZ/Toffoli as **one logical cycle** rather than four T equivalents.

```python
lp_qldpc = FormulaQEC(
    name="lp_qldpc",
    threshold=0.008,
    prefactor=2.0e-5,
    qubits_formula="7.886",        # high-rate code: ~constant per-logical overhead
    cycle_time_formula="3 * t_meas",
    transversal_magic_states=True,
)
```

This is the mechanism behind the neutral-atom example
(`examples/shor_2048_gidney2025.yaml` with `examples/lp_qldpc.yaml`): it reproduces
the ~11,000-qubit RSA-2048 architecture of Cain et al. 2026 (arXiv:2603.28627),
versus ~16 million qubits for the same logical circuit on a surface code.

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

## Walkthrough: Chemistry Resource Estimation

This walkthrough guides you through a complete resource estimation workflow for quantum chemistry — one of the most promising near-term applications of fault-tolerant quantum computers. We will estimate the resources needed to simulate the electronic structure of a molecule, compare simulation methods and hardware targets, explore the design space, and analyze what matters most.

The scenario: you are planning a quantum chemistry experiment to simulate a molecule with 54 spatial orbitals (roughly the size of the FeMo-co active space in nitrogenase, a benchmark for quantum advantage in chemistry). You want to answer:

1. How many physical qubits and how much time will it take?
2. Which simulation method is most efficient?
3. Which hardware target is most practical?
4. How sensitive are the results to the error budget?

### Step 1: Define the Problem

Start by creating an `AlgorithmSpec` using the chemistry template. The template computes logical resource counts based on published models from Lee et al. (2021) and Berry et al. (2019).

```python
import quompass
from quompass.templates.chemistry import chemistry

# FeMo-co active space: 54 spatial orbitals, 54 electrons
spec = chemistry(num_orbitals=54, num_electrons=54, method="double_factorization")

# Inspect the logical resource counts
lc = spec.logical_counts
print(f"Algorithm: {spec.name}")
print(f"Logical qubits: {lc.num_qubits}")
print(f"CCZ/Toffoli gates: {lc.ccz_count:,}")
print(f"T-equivalent gates: {lc.total_t_equivalent:,}")
```

The `LogicalCounts` object is the portable interchange format — it captures everything the physical estimation stage needs, independent of which backend produced it.

### Step 2: Run a Single Estimate

Run a physical resource estimate using the default hardware and QEC settings:

```python
result = quompass.estimate(spec)

# Print a compact summary table
from quompass.viz.summary import print_estimate_summary
print_estimate_summary(result)
```

This produces a Rich table showing physical qubits, runtime, code distance, error budget, and other key metrics. For a more detailed breakdown including logical qubit properties and T factory details:

```python
from quompass.viz.summary import print_estimate_detail
print_estimate_detail(result)
```

You can also access any field programmatically:

```python
print(f"Physical qubits: {result.total_physical_qubits:,}")
print(f"  Algorithm:    {result.physical_qubits_for_algorithm:,}")
print(f"  T factories:  {result.physical_qubits_for_t_factories:,}")
print(f"Runtime: {result.runtime_human}")
print(f"Code distance: {result.logical_qubit.code_distance}")
print(f"Logical error rate: {result.logical_qubit.logical_error_rate:.2e}")
```

Or from the CLI:

```bash
quompass estimate --template chemistry --param num_orbitals=54 --param num_electrons=54
quompass estimate --template chemistry --param num_orbitals=54 --output detail
```

### Step 3: Compare Methods

Quantum chemistry has three main simulation approaches with different resource trade-offs. Let's compare them:

```python
methods = ["double_factorization", "thc", "sparse"]

for method in methods:
    spec = chemistry(num_orbitals=54, num_electrons=54, method=method)
    result = quompass.estimate(spec, hardware="gate_ns_e4")

    print(f"\n{method}:")
    print(f"  Qubits: {result.total_physical_qubits:>12,}")
    print(f"  Runtime: {result.runtime_human:>10}")
    print(f"  T states: {result.num_t_states:>12,}")
    print(f"  Code distance: {result.logical_qubit.code_distance}")
```

You'll see that double factorization and THC typically produce significantly different physical qubit counts, even for the same molecule, because the underlying gate counts differ substantially. This is exactly the kind of comparison that makes quompass useful — the same physical estimation pipeline applied consistently across different algorithmic approaches.

### Step 4: Explore the Design Space

Now let's systematically explore how the results change across hardware targets, QEC schemes, and error budgets:

```python
from quompass.exploration import ExplorationSpace, explore

space = ExplorationSpace(
    algorithm=chemistry(num_orbitals=54, method="double_factorization"),
    hardware=["gate_ns_e3", "gate_ns_e4", "gate_us_e3"],
    qec=["surface_code", "color_code"],
    error_budgets=[0.01, 0.001, 0.0001],
)

print(f"Evaluating {space.size} combinations...")
result = explore(space)

# Print results table
from quompass.viz.exploration import print_exploration_table
print_exploration_table(result)

print(f"\n{result.num_succeeded}/{space.size} succeeded")
```

Some combinations will fail (e.g., if the physical error rate exceeds the QEC threshold). These are recorded as failed points — they don't crash the run.

Extract the Pareto front to see which configurations offer the best trade-offs between physical qubits and runtime:

```python
front = result.pareto_front()

from quompass.viz.exploration import print_pareto_table
print_pareto_table(front)
```

The Pareto front shows configurations where no other configuration is simultaneously better in both qubits and runtime. This helps you understand the fundamental trade-off: faster hardware may need more qubits, and vice versa.

From the CLI:

```bash
quompass explore --template chemistry --param num_orbitals=54 \
    --hardware gate_ns_e3,gate_ns_e4,gate_us_e3 \
    --qec surface_code,color_code \
    --error-budget 0.01,0.001,0.0001

# With Pareto front output
quompass explore --template chemistry --param num_orbitals=54 \
    --hardware gate_ns_e3,gate_ns_e4 \
    --error-budget 0.01,0.001,0.0001 \
    --output pareto
```

### Step 5: Analyze Sensitivity

Which parameter has the biggest impact on physical qubit count? Sensitivity analysis tells you where to focus your engineering effort:

```python
sens = result.sensitivity(metric="total_physical_qubits")

from quompass.viz.exploration import print_sensitivity_table
print_sensitivity_table(sens)

print(f"\nMost sensitive dimension: {sens.most_sensitive_dimension()}")
```

This performs a one-at-a-time (OAT) analysis: for each dimension (hardware, QEC, error budget), it varies that dimension while holding the others at a baseline, and reports the percentage change in the target metric.

Typical findings for chemistry:
- **Hardware quality** (error rate) usually has the largest impact, because lower error rates mean smaller code distances and fewer physical qubits per logical qubit.
- **Error budget** has a moderate impact — tighter budgets require higher code distances.
- **QEC scheme** matters, but the difference between surface code and color code is typically smaller than the hardware effect.

You can also analyze sensitivity for runtime:

```python
sens_time = result.sensitivity(metric="runtime_seconds")
print_sensitivity_table(sens_time)
```

### Step 6: Create a Custom QEC Scheme

Suppose you're researching a new qLDPC code that promises linear qubit overhead instead of quadratic. You can define it using `FormulaQEC` and immediately compare it against surface code:

```python
from quompass import FormulaQEC

# Hypothetical qLDPC code with linear qubit scaling
my_qldpc = FormulaQEC(
    name="my_qldpc",
    threshold=0.01,         # Same threshold as surface code
    prefactor=0.03,         # Same prefactor
    qubits_formula="12 * d",           # Linear in d (vs 2*d^2 for surface code)
    cycle_time_formula="6 * t_2q * d", # Faster cycles
)

# Compare against surface code
spec = chemistry(num_orbitals=54, method="double_factorization")

for qec_name, qec_obj in [("surface_code", "surface_code"), ("my_qldpc", my_qldpc)]:
    r = quompass.estimate(spec, hardware="gate_ns_e4", qec=qec_obj)
    print(f"{qec_name}: {r.total_physical_qubits:,} qubits, {r.runtime_human}")
```

The linear qubit scaling of the hypothetical qLDPC code should produce dramatically fewer physical qubits. This kind of what-if analysis is central to QEC research — you can quickly assess the practical impact of theoretical improvements.

You can also define the QEC scheme in YAML for reproducibility:

```yaml
# my_qldpc.yaml
name: my_qldpc
threshold: 0.01
prefactor: 0.03
qubits_formula: "12 * d"
cycle_time_formula: "6 * t_2q * d"
```

```bash
quompass estimate --template chemistry --param num_orbitals=54 \
    --hardware gate_ns_e4 --qec my_qldpc.yaml
```

### Step 7: Export and Reproduce

Save your results for later analysis or sharing:

```python
from quompass.io import save_estimate, save_yaml

# Save full result as YAML
spec = chemistry(num_orbitals=54, method="double_factorization")
result = quompass.estimate(spec, hardware="gate_ns_e4")
save_estimate(result, "chemistry_df_54orb.yaml")

# Save the algorithm spec for reproducibility
save_yaml(spec.to_dict(), "chemistry_spec.yaml")
```

The saved YAML contains everything needed to understand and reproduce the estimate: algorithm parameters, hardware model, QEC scheme, error budget, and all computed results.

You can also export from the CLI:

```bash
# YAML output to file
quompass estimate --template chemistry --param num_orbitals=54 \
    --hardware gate_ns_e4 --output yaml > chemistry_result.yaml

# JSON output (flat summary, good for scripts)
quompass estimate --template chemistry --param num_orbitals=54 \
    --hardware gate_ns_e4 --output json
```

### Putting It All Together

Here is a complete script that runs the full workflow:

```python
"""Chemistry resource estimation workflow.

Estimates physical resources for simulating a 54-orbital molecule
using different methods, hardware targets, and QEC schemes.
"""

import quompass
from quompass.templates.chemistry import chemistry
from quompass.exploration import ExplorationSpace, explore
from quompass.viz.summary import print_estimate_summary
from quompass.viz.exploration import (
    print_exploration_table,
    print_pareto_table,
    print_sensitivity_table,
)

# --- 1. Single estimate ---
spec = chemistry(num_orbitals=54, num_electrons=54, method="double_factorization")
result = quompass.estimate(spec, hardware="gate_ns_e4")
print("=== Single Estimate ===")
print_estimate_summary(result)

# --- 2. Method comparison ---
print("\n=== Method Comparison (gate_ns_e4) ===")
for method in ["double_factorization", "thc", "sparse"]:
    s = chemistry(num_orbitals=54, method=method)
    r = quompass.estimate(s, hardware="gate_ns_e4")
    print(f"  {method:25s}  {r.total_physical_qubits:>10,} qubits  {r.runtime_human:>10}")

# --- 3. Design space exploration ---
print("\n=== Design Space Exploration ===")
space = ExplorationSpace(
    algorithm=spec,
    hardware=["gate_ns_e3", "gate_ns_e4", "gate_us_e3"],
    qec=["surface_code"],
    error_budgets=[0.01, 0.001, 0.0001],
)
er = explore(space)
print_exploration_table(er)

# --- 4. Pareto front ---
print("\n=== Pareto Front ===")
front = er.pareto_front()
print_pareto_table(front)

# --- 5. Sensitivity analysis ---
print("\n=== Sensitivity Analysis ===")
sens = er.sensitivity(metric="total_physical_qubits")
print_sensitivity_table(sens)
print(f"Most sensitive: {sens.most_sensitive_dimension()}")
```

This script demonstrates the full power of quompass: from a single estimate to systematic exploration to actionable insights about where to invest engineering effort.

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
