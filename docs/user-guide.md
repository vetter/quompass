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
- [Walkthrough: Extending quompass for a New Architecture](#walkthrough-extending-quompass-for-a-new-architecture)
  - [The Scenario](#the-scenario)
  - [Step 1: Capture the Logical Algorithm](#step-1-capture-the-logical-algorithm)
  - [Step 2: Model the Neutral-Atom Hardware](#step-2-model-the-neutral-atom-hardware)
  - [Step 3: Run It and Hit the Factory Wall](#step-3-run-it-and-hit-the-factory-wall)
  - [Step 4: Extend the Estimator](#step-4-extend-the-estimator)
  - [Step 5: Define the qLDPC Code Scheme](#step-5-define-the-qldpc-code-scheme)
  - [Step 6: Run the Full Estimate](#step-6-run-the-full-estimate)
  - [Step 7: Test the Extension](#step-7-test-the-extension)
  - [A Note on Honest Calibration](#a-note-on-honest-calibration)
  - [References](#references)
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

## Walkthrough: Extending quompass for a New Architecture

The Chemistry walkthrough used quompass entirely "from the catalog" — built-in templates, hardware presets, and QEC schemes. This walkthrough does the opposite. It follows a real research question that none of the built-ins can answer, and extends quompass across all three of its layers — a new algorithm, a new hardware target, and a new error-correcting code — including the one case where YAML is not enough and the estimator itself must be extended.

The case study reproduces a 2026 result: Cain et al. showed that Shor's algorithm for RSA-2048 can be run on roughly **10,000 neutral atoms**, two to three orders of magnitude below the superconducting surface-code estimates. We rebuild that estimate in quompass from scratch. The finished example ships in the repository as `examples/shor_2048_gidney2025.yaml`, `examples/neutral_atom.yaml`, and `examples/lp_qldpc.yaml`; here we build each file and explain every field.

### The Scenario

Three papers define the problem (full citations in [References](#references)):

- **The logical circuit.** Gidney (2025) gives a windowed-arithmetic circuit that factors a 2048-bit RSA integer with ~1,399 logical qubits and ~6.5 × 10⁹ Toffoli gates.
- **The reference estimate.** Cain et al. (2026) re-cost that circuit on a reconfigurable neutral-atom processor using high-rate lifted-product (LP) qLDPC codes, and report a "space-efficient" architecture of **11,033 atoms**.
- **The contrast.** The same circuit on a surface code with superconducting hardware needs ~16 million physical qubits — quompass shows this directly.

The gap between 16 million and 11 thousand is not hardware speed. It is two structural choices that the surface-code defaults bake in:

1. **The code.** A surface code spends `2 * d^2` physical qubits per logical qubit. A high-rate qLDPC code amortizes a near-constant overhead across many logical qubits.
2. **The magic states.** Surface-code architectures distill T/CCZ states in dedicated 15-to-1 factories — for this circuit, the factories alone are ~13M qubits. Neutral-atom LP-code architectures apply T and CCZ *transversally*, with magic-state cultivation, and need no factory at all.

quompass models (1) with a `FormulaQEC` scheme — no code change. Modeling (2) requires teaching the estimator a concept it does not yet have. We hit that wall deliberately in Step 3.

### Step 1: Capture the Logical Algorithm

quompass has a Shor template, but it implements the Gidney–Ekerå (2019) construction, not the newer Gidney (2025) circuit. Writing a new `AlgorithmTemplate` class (see [Adding a Custom Template](#adding-a-custom-template)) is the right move for a *parameterized family* of circuits; for a single published circuit the lighter path is a YAML `AlgorithmSpec` — enter the logical counts directly.

```yaml
# examples/shor_2048_gidney2025.yaml
name: "Shor's factoring (RSA-2048, Gidney 2025 circuit)"
description: >
  Factor a 2048-bit RSA integer using the logical circuit of Gidney 2025.
algorithm_family: cryptanalysis
source: "literature:gidney-2025 (arXiv:2505.15917)"

problem_parameters:
  n_bits: 2048

logical_counts:
  num_qubits: 1399       # logical qubits (Cain et al. Fig. 3a)
  ccz_count: 6500000000  # 6.5e9 Toffoli gates
  t_count: 0
  rotation_count: 0      # windowed/approximate QFT folded into the Toffoli cost
  measurement_count: 0
  clifford_count: 0
```

The `logical_counts` block maps field-for-field onto the `LogicalCounts` dataclass — the portable interchange format from the [Architecture Overview](#architecture-overview). Two modeling decisions are worth calling out:

- **Toffolis go in `ccz_count`, not `t_count`.** A Toffoli and a CCZ are equivalent up to Clifford corrections and cost the same in magic states. quompass's `total_t_equivalent` property expands each CCZ into 4 T gates — a convention that matters in Step 3.
- **`rotation_count: 0`.** Gidney's circuit replaces the textbook QFT with windowed arithmetic, so there are no arbitrary-angle rotations to synthesize; the cost is entirely in Toffolis.

Load it and confirm:

```python
from quompass.io import load_algorithm

spec = load_algorithm("examples/shor_2048_gidney2025.yaml")
print(spec.logical_counts.num_qubits)                  # 1399
print(f"{spec.logical_counts.total_t_equivalent:,}")   # 26,000,000,000
```

### Step 2: Model the Neutral-Atom Hardware

A hardware target is a `HardwareModel` wrapping a `QubitParams` record. None of the six built-in presets is a neutral-atom processor, so we write one as YAML (the [Custom Hardware YAML](#custom-hardware-yaml) path). The numbers come from the device assumptions in Cain et al.: a physical entangling-gate error rate of p = 0.1%, and a stabilizer-measurement cycle of about 1 ms.

```yaml
# examples/neutral_atom.yaml
name: neutral_atom_rydberg
description: >
  Reconfigurable neutral-atom (Rydberg) processor, p = 0.1% two-qubit
  gate error, ~1 ms stabilizer round (Cain et al. 2026).

qubit_params:
  name: neutral_atom_rydberg
  instruction_set: gate_based
  one_qubit_gate_time: 1.0e-6           # local Raman single-qubit gate, ~1 us
  two_qubit_gate_time: 0.5e-6           # Rydberg CZ entangling gate, ~0.5 us
  one_qubit_measurement_time: 1.0e-3    # effective stabilizer round, ~1 ms
  t_gate_time: 0.5e-6                   # unused under transversal magic states
  one_qubit_gate_error_rate: 1.0e-4
  two_qubit_gate_error_rate: 1.0e-3     # p = 0.1% -- the paper's working point
  one_qubit_measurement_error_rate: 1.0e-3
  t_gate_error_rate: 1.0e-3             # unused under transversal magic states
```

Two fields deserve comment. `one_qubit_measurement_time` is set to 1 ms — slow for a single readout, but here it stands for the *effective stabilizer-extraction round* of a neutral-atom device, which is dominated by atom rearrangement and fluorescence imaging, not by a single projective measurement. `QubitParams` has no separate "rearrangement time" field, so we fold that cost into the measurement time and let the QEC scheme's cycle-time formula consume it (Step 5). And `t_gate_time` / `t_gate_error_rate` are required by the dataclass but become irrelevant once the distillation factory is switched off; we set them to sensible values and move on.

The analytical estimator collapses these rates to a single physical error rate via `QubitParams.worst_case_clifford_error` — the maximum of the measurement, 1-qubit, and 2-qubit error rates — which here is 1.0 × 10⁻³, exactly the paper's p = 0.1%.

### Step 3: Run It and Hit the Factory Wall

We have a circuit and a hardware model. We still need a QEC scheme. The closest built-in is the surface code; run with it and read the result critically.

```python
import quompass
from quompass.io import load_algorithm, load_hardware

spec = load_algorithm("examples/shor_2048_gidney2025.yaml")
hw = load_hardware("examples/neutral_atom.yaml")

result = quompass.estimate(spec, hardware=hw, qec="surface_code")
print(f"Total:      {result.total_physical_qubits:,}")
print(f"  Algorithm:{result.physical_qubits_for_algorithm:>12,}")
print(f"  Factories:{result.physical_qubits_for_t_factories:>12,}")
```

```
Total:      16,094,828
  Algorithm:   2,688,878
  Factories:  13,405,950
```

Two problems, matching the two structural choices from The Scenario:

- **The algorithm qubits** (2.7M) come from `1399 * 2 * d^2` at the code distance d = 31 the search selected. The surface code's quadratic per-logical overhead is wrong for a high-rate qLDPC code — but this is fixable with `FormulaQEC`, no code change needed.
- **The T factories** (13.4M) dominate, and they are an artifact. The analytical estimator builds a 15-to-1 distillation factory whenever the circuit has any non-Clifford cost. The neutral-atom architecture has *no* factory: it applies CCZ transversally. There is no `FormulaQEC` field, no hardware field, and no `estimate()` argument that turns the factory off.

This is the wall. A YAML scheme can describe a code's geometry and error suppression, but "this code applies T/CCZ transversally" is a *capability* — a fact the estimator must branch on. Extending quompass here means extending the estimator itself.

### Step 4: Extend the Estimator

The change has three parts: declare the capability on the QEC abstraction, let `FormulaQEC` carry it, and make the analytical estimator act on it. The guiding constraint is **backward compatibility** — every existing scheme and test must behave exactly as before.

**4a. Declare the capability on the `QECScheme` ABC.**

`QECScheme` (in `core/qec.py`) is the abstract base every code implements. We add `transversal_magic_states` as a *concrete* property with a `False` default — deliberately not an `@abstractmethod`. A concrete default means `SurfaceCode`, `FloquetCode`, and every third-party `QECScheme` subclass keep working untouched; only a code that genuinely supports transversal logic overrides it.

```python
# core/qec.py -- a concrete property on the QECScheme ABC
@property
def transversal_magic_states(self) -> bool:
    """Whether non-Clifford gates are applied transversally on this code.

    When False (the default), T and CCZ/Toffoli gates require magic-state
    distillation factories. When True, they are native transversal logical
    operations: no factory, and a CCZ is one logical cycle rather than four
    T-gate equivalents. Models high-rate qLDPC architectures with magic-state
    cultivation, such as the lifted-product codes of Cain et al.
    """
    return False
```

**4b. Let `FormulaQEC` carry the flag.**

`FormulaQEC` is the YAML-backed scheme. It needs a constructor argument, a property override, and round-trip serialization so the flag survives `to_dict()` / `from_dict()` — and therefore YAML.

```python
# core/qec.py -- FormulaQEC
def __init__(self, name, threshold, prefactor, qubits_formula,
             cycle_time_formula, distance_coefficient_power=0.0,
             transversal_magic_states=False):           # new argument
    ...
    self._transversal_magic_states = transversal_magic_states

@property
def transversal_magic_states(self) -> bool:             # overrides the ABC default
    return self._transversal_magic_states
```

`to_dict()` gains `"transversal_magic_states": self._transversal_magic_states`; `from_dict()` reads it with `d.get("transversal_magic_states", False)`. The `.get` default keeps every QEC YAML written before this change loadable.

**4c. Branch the analytical estimator.**

The real behavior change is in `AnalyticalPhysicalEstimator.estimate()` (in `backends/mock.py`). It reads the new flag and changes two things: how non-Clifford depth is counted, and whether a factory is built.

```python
# backends/mock.py -- inside AnalyticalPhysicalEstimator.estimate()
transversal = qec.transversal_magic_states

if transversal:
    # Native transversal T/CCZ: each non-Clifford gate is one logical
    # cycle, and a CCZ is NOT expanded into 4 T equivalents.
    n_nonclifford = (logical_counts.t_count
                     + logical_counts.ccz_count
                     + logical_counts.rotation_count)
else:
    n_nonclifford = logical_counts.total_t_equivalent   # CCZ x4 -- unchanged

# ... distance search, qubit cost, cycle time ...

if transversal:
    t_factory = None                                    # no distillation factory
else:
    t_factory = self._estimate_t_factories(logical_counts, hardware, qec, d, budget)
```

The non-transversal branch is the original code path verbatim, so `total_t_equivalent` (which counts each CCZ as 4 T) and the 15-to-1 factory model are untouched for every existing scheme. The `PhysicalEstimate` result type already allowed `t_factory` to be `None` — it happens for Clifford-only circuits — so the rest of the pipeline and the result tables needed no change.

That is the entire feature: one concrete property, one serialized field, one branch in the estimator. Running `pytest tests/unit` after the change, the full pre-existing suite still passes — the definition of a backward-compatible extension.

### Step 5: Define the qLDPC Code Scheme

With the estimator extended, the LP qLDPC code can be written as a `FormulaQEC` YAML (see also [Transversal Magic States](#transversal-magic-states) under Custom QEC Schemes). This is where the modeling judgment lives, so each field gets a justification.

```yaml
# examples/lp_qldpc.yaml
name: lp_qldpc
threshold: 0.008          # circuit-level QEC threshold for the LP code family
prefactor: 2.0e-5         # crossing prefactor; tuned so the distance search
                          # selects d ~ 25, consistent with lp243'7 (d <= 24)
distance_coefficient_power: 0.0

qubits_formula: "7.886"          # effective atoms per algorithmic logical qubit
cycle_time_formula: "3 * t_meas" # ~3 stabilizer rounds per logical cycle

transversal_magic_states: true   # the capability added in Step 4
```

**`qubits_formula` is constant in `d`.** A surface code's formula is `2 * d * d`; this one is a bare number. That is the defining feature of a high-rate qLDPC code: its physical-qubit overhead per logical qubit does *not* grow with distance — raising the distance enlarges a code block that already holds many logical qubits, so the ratio of physical to logical qubits stays roughly fixed. The value 7.886 is the effective overhead of the paper's space-efficient RSA-2048 architecture: 11,033 atoms ÷ 1,399 algorithmic logical qubits. It amortizes the lp243′7 memory code (parameters ≈ [[5278, 1480, ≤24]], a physical/logical ratio of 3.57) plus the computational blocks and cultivation ancillas.

**`cycle_time_formula` is also distance-independent.** A surface code does d rounds of stabilizer measurement per logical cycle, hence the `* d` in its formula. The LP-code architecture uses *algorithmic fault tolerance* — a small, constant number of rounds per logical operation. With the hardware's 1 ms round (`t_meas`), `3 * t_meas` gives a 3 ms logical cycle.

**`threshold` and `prefactor`** set the error-suppression curve `prefactor * (p / threshold)^((d+1)/2)`. They are tuned, not first-principles — see [A Note on Honest Calibration](#a-note-on-honest-calibration).

**`transversal_magic_states: true`** is the field that did not exist before Step 4. `FormulaQEC.from_dict()` reads it; the estimator branches on it.

### Step 6: Run the Full Estimate

All three pieces compose through the standard `estimate()` entry point:

```python
import quompass
from quompass.io import load_algorithm, load_hardware, load_qec

spec = load_algorithm("examples/shor_2048_gidney2025.yaml")
hw   = load_hardware("examples/neutral_atom.yaml")
qec  = load_qec("examples/lp_qldpc.yaml")

result = quompass.estimate(spec, hardware=hw, qec=qec)
print(f"Total physical qubits: {result.total_physical_qubits:,}")
print(f"  T factories:         {result.physical_qubits_for_t_factories:,}")
print(f"Runtime:               {result.runtime_human}")
print(f"Code distance:         {result.logical_qubit.code_distance}")
```

```
Total physical qubits: 11,192
  T factories:         0
Runtime:               225d 16h
Code distance:         25
```

Or equivalently from the CLI:

```bash
quompass estimate --spec examples/shor_2048_gidney2025.yaml \
    --hardware examples/neutral_atom.yaml \
    --qec examples/lp_qldpc.yaml
```

11,192 physical qubits, no factory, ~226 days — against 16 million for the surface code in Step 3, a roughly 1,400× reduction, and within 1.5% of the paper's 11,033-atom space-efficient figure. The runtime lands inside the paper's quoted 100–300-day band for RSA-2048. The published result is reproduced by composing one YAML algorithm spec, one YAML hardware model, one YAML QEC scheme, and one capability flag.

### Step 7: Test the Extension

An extension is not finished until it is pinned by tests. Three layers need coverage; all of them use the mock/analytical backends, so they need no external dependencies.

The capability default, on the ABC:

```python
def test_surface_code_requires_distillation():
    assert SurfaceCode().transversal_magic_states is False
```

The `FormulaQEC` round-trip — proving the flag survives serialization, and therefore YAML:

```python
def test_transversal_magic_states_roundtrip():
    fqec = FormulaQEC(name="lp", threshold=0.008, prefactor=2.0e-5,
                      qubits_formula="7.886", cycle_time_formula="3 * t_meas",
                      transversal_magic_states=True)
    assert FormulaQEC.from_dict(fqec.to_dict()).transversal_magic_states is True
```

The estimator behavior — that a transversal scheme builds no factory and counts a CCZ as one cycle, not four. Here `_qldpc(transversal)` is a one-line test helper that returns a `FormulaQEC` with the flag set:

```python
def test_ccz_counts_as_one_cycle_not_four(superconducting_hw):
    pe = AnalyticalPhysicalEstimator()
    spec = AlgorithmSpec(name="CCZ depth",
        logical_counts=LogicalCounts(num_qubits=10, t_count=100, ccz_count=50))
    transversal = pe.estimate(spec.logical_counts, superconducting_hw,
                              _qldpc(True), ErrorBudget(total=0.001), spec)
    distilled   = pe.estimate(spec.logical_counts, superconducting_hw,
                              _qldpc(False), ErrorBudget(total=0.001), spec)
    assert transversal.algorithmic_logical_depth == 150   # 100 + 50
    assert distilled.algorithmic_logical_depth   == 300   # 100 + 4*50
```

Finally, an end-to-end test loads the three example files and pins the headline number, so the example cannot silently drift:

```python
def test_lp_qldpc_reaches_about_11k_qubits():
    result = quompass.estimate(
        load_algorithm(EXAMPLES / "shor_2048_gidney2025.yaml"),
        hardware=load_hardware(EXAMPLES / "neutral_atom.yaml"),
        qec=load_qec(EXAMPLES / "lp_qldpc.yaml"))
    assert result.t_factory is None
    assert 10_000 <= result.total_physical_qubits <= 13_000
```

### A Note on Honest Calibration

This example reproduces a published result, and it is worth being explicit about which numbers are *derived* and which are *fitted* — a distinction every resource-estimation model should make visible.

**Pinned to the literature:** the 1,399 logical qubits and 6.5 × 10⁹ Toffolis (Gidney 2025; Cain et al. Fig. 3a); the physical error rate p = 0.1%; the ~1 ms stabilizer round; the LP memory-code parameters ≈ [[5278, 1480, ≤24]].

**Fitted by the modeler:** the QEC `threshold` (0.008) and `prefactor` (2 × 10⁻⁵), chosen so the distance search lands near d ≈ 25, consistent with the paper's d ≤ 24; and `qubits_formula = 7.886`, which is the paper's reported 11,033 ÷ 1,399 — an *effective* overhead, not a derivation of the LP code's geometry from first principles.

The analytical backend also rounds physical-qubits-per-logical to an integer, so the total is `1399 * 8 = 11,192` rather than 11,033 — a 1.5% artifact of that rounding. None of this is hidden: it is all in the comments of `examples/lp_qldpc.yaml`. For a higher-fidelity estimate, the LP code's overhead and threshold would be computed by a dedicated logical/physical backend — the role the Qualtran and Azure adapters play for surface codes — and a `FormulaQEC` calibrated to a paper is the fast, transparent first cut.

### References

1. C. Gidney, *How to factor 2048 bit RSA integers with less than a million noisy qubits* (2025). arXiv:2505.15917. DOI: [10.48550/arXiv.2505.15917](https://doi.org/10.48550/arXiv.2505.15917). — the logical circuit used by this example.
2. M. Cain, Q. Xu, R. King, et al., *Shor's algorithm is possible with as few as 10,000 reconfigurable atomic qubits* (2026). arXiv:2603.28627. DOI: [10.48550/arXiv.2603.28627](https://doi.org/10.48550/arXiv.2603.28627). — the reference physical estimate.
3. C. Gidney and M. Ekerå, *How to factor 2048 bit RSA integers in 8 hours using 20 million noisy qubits*, Quantum **5**, 433 (2021). DOI: [10.22331/q-2021-04-15-433](https://doi.org/10.22331/q-2021-04-15-433). — the earlier construction behind quompass's built-in Shor template.
4. A. G. Fowler, M. Mariantoni, J. M. Martinis, and A. N. Cleland, *Surface codes: Towards practical large-scale quantum computation*, Phys. Rev. A **86**, 032324 (2012). DOI: [10.1103/PhysRevA.86.032324](https://doi.org/10.1103/PhysRevA.86.032324). — the surface-code model behind quompass's `SurfaceCode`.
5. S. Bravyi and J. Haah, *Magic-state distillation with low overhead*, Phys. Rev. A **86**, 052329 (2012). DOI: [10.1103/PhysRevA.86.052329](https://doi.org/10.1103/PhysRevA.86.052329). — the distillation model the transversal path replaces.
6. P. Panteleev and G. Kalachev, *Quantum LDPC codes with almost linear minimum distance*, IEEE Trans. Inf. Theory **68**, 213 (2022). DOI: [10.1109/TIT.2021.3119384](https://doi.org/10.1109/TIT.2021.3119384). — introduces the lifted-product (LP) construction.
7. D. Bluvstein, S. J. Evered, A. A. Geim, et al., *Logical quantum processor based on reconfigurable atom arrays*, Nature **626**, 58 (2024). DOI: [10.1038/s41586-023-06927-3](https://doi.org/10.1038/s41586-023-06927-3). — transversal logical operations on neutral-atom hardware.

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
