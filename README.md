# ftqre -- Portable Fault-Tolerant Quantum Resource Estimation

A Python library for estimating the physical resources required to run fault-tolerant quantum algorithms. Provides a portable abstraction layer over estimation backends (Qualtran, Azure QRE) with pluggable QEC schemes, hardware models, and algorithm templates.

## Installation

```bash
pip install ftqre
```

Optional extras:

```bash
pip install ftqre[viz]       # matplotlib plotting
pip install ftqre[qualtran]  # Qualtran logical estimation backend
pip install ftqre[azure]     # Azure QRE physical estimation backend
pip install ftqre[all]       # everything
pip install ftqre[dev]       # development tools (pytest, ruff, mypy)
```

## Quick Start (Python)

### One-shot estimation

```python
import ftqre
from ftqre.templates.shor import shor

# Estimate resources for factoring a 2048-bit integer
spec = shor(n_bits=2048)
result = ftqre.estimate(spec)

print(f"Physical qubits: {result.total_physical_qubits:,}")
print(f"Runtime: {result.runtime_human}")
print(f"Code distance: {result.logical_qubit.code_distance}")
```

### Compare hardware targets and QEC schemes

```python
import ftqre
from ftqre.templates.chemistry import chemistry

spec = chemistry(num_orbitals=54, method="double_factorization")

# Try different hardware + QEC combinations
for hw in ["gate_ns_e3", "gate_ns_e4"]:
    result = ftqre.estimate(spec, hardware=hw, qec="surface_code")
    print(f"{hw}: {result.total_physical_qubits:,} qubits, {result.runtime_human}")
```

### Design space exploration

```python
from ftqre.templates.shor import shor
from ftqre.exploration import ExplorationSpace, explore

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
import ftqre
from ftqre.core.algorithm import AlgorithmSpec, LogicalCounts

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
result = ftqre.estimate(spec)
print(f"Physical qubits: {result.total_physical_qubits:,}")
```

## Quick Start (CLI)

```bash
# Estimate resources for Shor's algorithm
ftqre estimate --template shor --param n_bits=2048

# Explore the design space
ftqre explore --template shor --param n_bits=2048 \
    --hardware gate_ns_e3,gate_ns_e4,gate_us_e3 \
    --qec surface_code,color_code \
    --error-budget 0.01,0.001 \
    --sensitivity

# List available templates, hardware, QEC schemes
ftqre catalog templates
ftqre catalog hardware
ftqre catalog qec
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
