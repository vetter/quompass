# Quompass -- Portable Fault-Tolerant Quantum Resource Estimation

A Python library for estimating the physical resources required to run fault-tolerant quantum algorithms. Provides a portable abstraction layer over estimation backends (Qualtran, Azure QRE) with pluggable QEC schemes, hardware models, and algorithm templates.

## Installation

With [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv add quompass
```

With pip:

```bash
pip install quompass
```

Optional extras:

```bash
# uv
uv add "quompass[viz]"       # matplotlib plotting
uv add "quompass[qualtran]"  # Qualtran logical estimation backend
uv add "quompass[azure]"     # Azure QRE physical estimation backend
uv add "quompass[all]"       # everything
uv add --dev "quompass[dev]" # development tools (pytest, ruff, mypy)

# pip
pip install quompass[viz]
pip install quompass[qualtran]
pip install quompass[azure]
pip install quompass[all]
pip install quompass[dev]
```

### From source

```bash
# uv
git clone https://github.com/<org>/quompass && cd quompass
uv sync --extra dev          # install with dev extras
uv sync --all-extras         # install everything
uv run pytest tests/unit -v  # run unit tests
uv run quompass --help       # run the CLI

# pip
git clone https://github.com/<org>/quompass && cd quompass
pip install -e ".[dev]"
pytest tests/unit -v
quompass --help
```

## Quick Start (Python)

### One-shot estimation

```python
import quompass
from quompass.templates.shor import shor

# Estimate resources for factoring a 2048-bit integer
spec = shor(n_bits=2048)
result = quompass.estimate(spec)

print(f"Physical qubits: {result.total_physical_qubits:,}")
print(f"Runtime: {result.runtime_human}")
print(f"Code distance: {result.logical_qubit.code_distance}")
```

### Compare hardware targets and QEC schemes

```python
import quompass
from quompass.templates.chemistry import chemistry

spec = chemistry(num_orbitals=54, method="double_factorization")

# Try different hardware + QEC combinations
for hw in ["gate_ns_e3", "gate_ns_e4"]:
    result = quompass.estimate(spec, hardware=hw, qec="surface_code")
    print(f"{hw}: {result.total_physical_qubits:,} qubits, {result.runtime_human}")
```

### Design space exploration

```python
from quompass.templates.shor import shor
from quompass.exploration import ExplorationSpace, explore

result = explore(ExplorationSpace(
    algorithm=shor(n_bits=2048),
    hardware=["gate_ns_e3", "gate_ns_e4", "gate_us_e3"],
    qec=["surface_code", "color_code"],
    error_budgets=[0.01, 0.001, 0.0001],
))

result.print_table()                    # Full results table
result.pareto_front().print_table()     # Pareto-optimal points
result.sensitivity().print_table()      # Which parameter matters most?
```

### Custom algorithm specification

```python
import quompass
from quompass.core.algorithm import AlgorithmSpec, LogicalCounts

# Define your own algorithm from known logical resource counts
spec = AlgorithmSpec(
    name="My Algorithm",
    logical_counts=LogicalCounts(
        num_qubits=100,
        t_count=1_000_000,
        ccz_count=500_000,
        measurement_count=100,
    ),
)
result = quompass.estimate(spec)
print(f"Physical qubits: {result.total_physical_qubits:,}")
```

## Quick Start (CLI)

```bash
# Estimate resources for Shor's algorithm
quompass estimate --template shor --param n_bits=2048

# Explore the design space
quompass explore --template shor --param n_bits=2048 \
    --hardware gate_ns_e3,gate_ns_e4,gate_us_e3 \
    --qec surface_code,color_code \
    --error-budget 0.01,0.001 \
    --sensitivity

# Optimize design space with NSGA-II
quompass optimize --template shor --param n_bits=2048 \
    --hardware gate_ns_e3,gate_ns_e4 --qec surface_code \
    --generations 50 --output pareto

# List available templates, hardware, QEC schemes, backends
quompass catalog templates
quompass catalog hardware
quompass catalog qec
quompass catalog backends
```

## Available Templates

| Template | Description | Key Parameters |
|----------|-------------|----------------|
| `shor` | Integer factoring (Gidney-Ekera) | `n_bits` (default: 2048) |
| `qpe` | Quantum Phase Estimation | `num_qubits`, `precision_bits` |
| `hamiltonian_sim` | Hamiltonian simulation | `num_qubits`, `evolution_time`, `method` (trotter/qsp/qubitization) |
| `chemistry` | Quantum chemistry | `num_orbitals`, `method` (double_factorization/thc/sparse) |
| `grover` | Grover's search | `search_space_bits`, `num_solutions` |

## Available Hardware Presets

| Preset | Description |
|--------|-------------|
| `gate_ns_e3` | Superconducting, ns gates, 10^-3 error rate |
| `gate_ns_e4` | Superconducting, ns gates, 10^-4 error rate |
| `gate_us_e3` | Trapped ion, us gates, 10^-3 Clifford error |
| `gate_us_e4` | Trapped ion, us gates, 10^-4 Clifford error |
| `maj_ns_e4` | Majorana topological, 10^-4 Clifford error |
| `maj_ns_e6` | Majorana topological, 10^-6 Clifford error |

## Available QEC Schemes

| Scheme | Description |
|--------|-------------|
| `surface_code` | Rotated surface code (threshold ~1%, 2d^2 qubits) |
| `floquet_code` | Floquet/Hastings-Haah code (for Majorana hardware) |
| `color_code` | 6.6.6 color code (threshold ~0.77%, 4.5d^2 qubits) |

Custom QEC schemes can be defined with `FormulaQEC` -- see the [User Guide](docs/user-guide.md).

## Architecture

```
AlgorithmSpec ──> LogicalEstimator ──> LogicalCounts ──> PhysicalEstimator ──> PhysicalEstimate
  (template)       (Qualtran/mock)     (portable)        (Azure/analytical)    (result)
```

LogicalCounts is the portable interchange format. You can bring your own from any source (Qualtran Bloqs, published papers, hand calculations) and estimate physical resources across different hardware and QEC combinations.

## Documentation

- [User Guide](docs/user-guide.md) -- detailed API reference, exploration guide, custom QEC, plugin architecture

## License

BSD-3-Clause
