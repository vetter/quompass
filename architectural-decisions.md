# Architectural Decisions Record

**Date**: 2025-12-04
**Status**: Approved

## Summary

All five key architectural decisions for the Quantum-Classical Resource Estimation Tool have been finalized. These decisions establish a flexible, extensible framework that can handle the NISQ→FT transition over the next 5 years.

---

## Decision 1: Algorithm Input Format ✓

**Question**: How should users specify quantum algorithms?

**Decision**: Hybrid approach with phased implementation

### Implementation Plan:
- **Phase 1 (MVP)**: Python API with builder pattern as primary interface
- **Phase 2**: YAML/JSON declarative format for saving/sharing specifications
- **Phase 3 (Future)**: Importers for standard formats (OpenQASM, Quil) if needed

### Example Usage:
```python
# Python API (Phase 1)
algorithm = Algorithm("Shor's Algorithm")
    .set_speedup_class("exponential")
    .add_gates(T=10**9, Clifford=10**8, CNOT=5*10**8)
    .set_depth(10**7)
    .set_width(2048)  # logical qubits

# Save to YAML (Phase 2)
algorithm.save("shors_2048.yaml")

# Load from YAML
algorithm = Algorithm.load("shors_2048.yaml")
```

### Rationale:
- Python API is familiar to target users, enables type checking and composition
- YAML/JSON provides declarative format for persistence and sharing
- Standard format support deferred until proven necessary
- Keeps initial implementation simple while maintaining extensibility

---

## Decision 2: Scope of Algorithms ✓

**Question**: Focus on specific algorithm classes or support broad range?

**Decision**: Unified framework supporting NISQ, Fault-Tolerant, and Early-FT regimes

### Architecture Layers:

**Layer 1: Regime-Agnostic Algorithm Specification**
- Gates, depth, width, classical interactions
- Same abstraction works for all regimes

**Layer 2: Hardware Regime Model**
- **NISQ Mode**:
  - 1:1 logical-to-physical qubit mapping
  - Depth limits based on coherence time
  - Noise modeling and error accumulation
  - Success probability calculations

- **Early-FT Mode** (transition period):
  - Small code distances (d=3-7)
  - Partial error correction
  - Limited depth extension
  - Hybrid characteristics

- **FT Mode**:
  - Full error correction overhead
  - Arbitrary circuit depth
  - Magic state factories
  - Crossover time analysis (Hoefler criteria)

**Layer 3: Regime-Specific Resource Estimation**
- Different calculation engines per regime
- Shared infrastructure, specialized models

**Layer 4: Unified Pareto Front Generation**
- Works across all regimes
- Regime-specific optimization variables

### Phased Implementation:
- **Phase 1 (MVP)**: Algorithm abstraction + FT estimation + basic NISQ support
- **Phase 2**: Enhanced NISQ modeling, early-FT regime, crossover analysis
- **Phase 3**: Regime comparison tools, transition path optimization

### Example Usage:
```python
# Evaluate same algorithm in different regimes
algorithm = VQE_Algorithm(molecule="H2O")

# NISQ evaluation (current hardware)
nisq_resources = estimate(
    algorithm,
    Architecture(regime="NISQ", physical_qubits=100, gate_fidelity=0.999)
)

# Early-FT evaluation (near-term)
early_ft_resources = estimate(
    algorithm,
    Architecture(regime="early-FT", code_distance=5, logical_qubits=50)
)

# Full FT evaluation (future)
ft_resources = estimate(
    algorithm,
    Architecture(regime="FT", code_distance=11, logical_qubits=50)
)

# Compare regimes
compare_regimes(nisq_resources, early_ft_resources, ft_resources)
```

### Rationale:
- Models the realistic 5-year NISQ→FT transition trajectory
- Enables comparative analysis across technology generations
- Provides technology evolution and transition planning capabilities
- More useful than focusing on single regime
- Unified codebase with regime-specific modules

---

## Decision 3: Error Correction Models ✓

**Question**: Which quantum error correction schemes should we support?

**Decision**: Pluggable architecture with Surface Code as initial implementation

### Interface Design:
```python
class ErrorCorrectionScheme(ABC):
    """Abstract base class for QEC schemes"""

    @abstractmethod
    def physical_qubits(self, logical_qubits: int, code_distance: int) -> int:
        """Calculate physical qubit overhead"""
        pass

    @abstractmethod
    def magic_state_overhead(self, T_count: int) -> Dict[str, int]:
        """Calculate magic state factory requirements"""
        pass

    @abstractmethod
    def cycle_time(self, physical_gate_time: float, code_distance: int) -> float:
        """Calculate error correction cycle time"""
        pass

    @abstractmethod
    def ancilla_qubits(self, logical_qubits: int, code_distance: int) -> int:
        """Calculate ancilla qubit requirements"""
        pass
```

### Initial Implementations:
```python
class NoErrorCorrection(ErrorCorrectionScheme):
    """For NISQ regime - no error correction"""
    def physical_qubits(self, logical, distance):
        return logical  # 1:1 mapping

class SurfaceCode(ErrorCorrectionScheme):
    """Surface code implementation (Gidney-Fowler model)"""
    def physical_qubits(self, logical, distance):
        return logical * 2 * distance**2

    def magic_state_overhead(self, T_count):
        # Implement Gidney-Fowler magic state factory model
        ...

# Future additions:
class ColorCode(ErrorCorrectionScheme): ...
class LDPCCode(ErrorCorrectionScheme): ...
```

### Usage:
```python
# Use Surface Code
architecture = Architecture(
    regime="FT",
    error_correction=SurfaceCode(),
    code_distance=7
)

# Easy to swap QEC schemes
architecture = Architecture(
    regime="FT",
    error_correction=ColorCode(),
    code_distance=7
)
```

### Rationale:
- Clean separation of concerns
- Easy to add new QEC schemes without modifying core code
- Surface Code is well-documented and sufficient for MVP
- Matches unified regime approach (NISQ uses NoErrorCorrection)
- Future-proof without over-engineering

---

## Decision 4: Classical Integration Depth ✓

**Question**: How detailed should classical HPC resource modeling be?

**Decision**: Tiered/layered approach - simple by default, detailed when needed

### Tier 1: Simple Estimates (MVP - Default)
```python
classical = ClassicalResources(
    cpu_cores=100,
    gpus=4,
    memory_gb=256,
    role="variational_optimizer"
)
```

**Estimates**:
- Core counts (CPUs, GPUs)
- Memory requirements (order of magnitude)
- Basic categorization (optimizer, preprocessor, controller)

**Use Case**: Initial planning, feasibility studies, high-level architecture

### Tier 2: Detailed Performance Modeling (Advanced - Optional)
```python
classical = ClassicalResources(
    # Compute
    cpu_cores=100,
    cpu_type="Intel Xeon Platinum 8380",
    cpu_frequency_ghz=2.3,
    flops_per_core=50e9,

    # Memory
    memory_gb=256,
    memory_bandwidth_gbs=200,
    memory_latency_ns=100,

    # Accelerators
    gpus=4,
    gpu_type="NVIDIA A100",
    gpu_memory_gb=80,
    gpu_flops=312e12,

    # Interconnect
    network_latency_us=10,
    network_bandwidth_gbs=100,
    quantum_classical_latency_us=5,
    quantum_classical_bandwidth_gbs=1,  # Per Hoefler 2023

    # Workload
    preprocessing_flops=1e15,
    optimization_iterations=1000,
    optimizer_type="L-BFGS-B"
)
```

**Estimates**:
- Detailed performance characteristics
- Bottleneck identification (memory-bound, compute-bound, I/O-bound)
- Communication overhead analysis
- Time-to-solution for classical components

**Use Case**: Detailed system design, procurement planning, bottleneck analysis

### Progressive API:
```python
# Simple mode (auto-estimates)
resources = estimate_classical(algorithm, mode="simple")

# Detailed mode (user provides specs)
resources = estimate_classical(
    algorithm,
    mode="detailed",
    hardware_specs=detailed_specs
)

# Hybrid (some details, auto-fill rest)
resources = estimate_classical(
    algorithm,
    cpu_cores=100,  # Specified
    gpus=4,         # Specified
    # Auto-estimate: memory, bandwidth, etc.
)
```

### Rationale:
- Serves both quick estimates and detailed planning needs
- Gradual learning curve - users can start simple
- Avoids overwhelming users with parameters
- Critical for hybrid algorithms (VQE, QAOA) where classical is significant
- Matches Hoefler 2023 emphasis on quantum-classical I/O bottlenecks

---

## Decision 5: Optimization Approach ✓

**Question**: How should we generate Pareto-optimal architecture configurations?

**Decision**: Hybrid approach - grid search for MVP, evolutionary algorithms for advanced cases

### Phase 1 (MVP): Smart Grid Search

**Implementation**:
```python
pareto_front = optimize(
    algorithm=algorithm,
    objectives=["minimize_physical_qubits", "minimize_time"],
    variables={
        "code_distance": [3, 5, 7, 9, 11],
        "logical_qubits": range(100, 1000, 100)
    },
    constraints={
        "error_rate": "<1e-6",
        "time_to_solution": "<2 weeks"  # Hoefler criterion
    }
)
```

**Characteristics**:
- Discrete parameter grid
- Exhaustive search within grid
- Smart bounds to limit search space
- Coarse granularity (2-3 variables, ~50-200 evaluations)

**Use Cases**:
- 2-3 optimization variables
- Discrete parameter choices
- Guaranteed completeness within grid
- Educational/exploratory use

### Phase 2 (Advanced): Evolutionary Optimization

**Implementation**:
```python
pareto_front = optimize(
    algorithm=algorithm,
    objectives=[
        "minimize_physical_qubits",
        "minimize_time",
        "minimize_error_rate",
        "minimize_cost"
    ],
    method="evolutionary",  # NSGA-II or similar
    variables={
        "code_distance": (3, 15),           # Continuous range
        "logical_qubits": (50, 2000),
        "factory_units": (1, 20),
        "classical_cores": (10, 1000),
        "memory_gb": (64, 2048)
    },
    constraints={
        "error_rate": "<1e-6",
        "budget_usd": "<100M"
    },
    algorithm_config={
        "population_size": 100,
        "generations": 50,
        "crossover_prob": 0.9,
        "mutation_prob": 0.1
    }
)
```

**Characteristics**:
- Continuous or discrete variables
- Many variables (5-10+)
- Multiple objectives (3-4+)
- Stochastic search
- Good approximation of Pareto front

**Use Cases**:
- Complex multi-objective optimization
- Many free parameters
- Fine-grained parameter tuning
- Production system design

### Phase 3 (Special Cases): Analytical Solutions

**Implementation**:
```python
# For specific cases with known analytical solutions
pareto_front = optimize(
    algorithm=algorithm,
    method="analytical",
    objectives=["minimize_physical_qubits", "minimize_time"]
)
# Derives Pareto front mathematically when possible
```

**Use Cases**:
- Simple 2-objective problems with monotonic trade-offs
- Educational purposes (showing exact solutions)
- Fast prototyping

### Unified API:
```python
# Framework automatically selects appropriate method
pareto_front = optimize(
    algorithm=algorithm,
    objectives=[...],
    variables={...},
    method="auto"  # Chooses based on problem characteristics
)

# Or user specifies
pareto_front = optimize(..., method="grid")      # Grid search
pareto_front = optimize(..., method="nsga2")     # NSGA-II
pareto_front = optimize(..., method="analytical") # Analytical
```

### Rationale:
- Appropriate tool for each scenario
- Start simple (grid search easy to implement and understand)
- Grid search sufficient for common cases (2-3 variables)
- Add sophistication as needed (evolutionary for complex cases)
- Pragmatic approach balances simplicity and capability

---

## Implementation Priority

Based on these decisions, the implementation order is:

### MVP (Phase 1):
1. ✓ Algorithm: Python API with builder pattern
2. ✓ Regimes: FT mode + basic NISQ mode
3. ✓ QEC: Surface Code + NoErrorCorrection
4. ✓ Classical: Tier 1 (simple estimates)
5. ✓ Optimization: Grid search

### Phase 2 (Enhanced):
1. Algorithm: YAML/JSON format support
2. Regimes: Enhanced NISQ modeling, Early-FT regime
3. QEC: Additional schemes (Color Code, LDPC)
4. Classical: Tier 2 (detailed performance modeling)
5. Optimization: Evolutionary algorithms (NSGA-II)

### Phase 3 (Advanced):
1. Algorithm: Standard format importers (OpenQASM, Quil)
2. Regimes: Regime comparison tools, transition planning
3. QEC: Cutting-edge schemes as they emerge
4. Classical: Bottleneck analysis, advanced profiling
5. Optimization: Analytical solutions, hybrid methods

---

## Design Principles

These decisions reflect consistent design principles:

1. **Start Simple, Add Complexity**: MVP focuses on essential features, advanced capabilities added incrementally
2. **Extensibility**: Pluggable architecture allows adding new components without rewriting core
3. **Progressive Disclosure**: Simple interface by default, detailed options available when needed
4. **Future-Proof**: Designs accommodate expected technology evolution (NISQ→FT transition)
5. **Pragmatic**: Choose appropriate tool for each scenario rather than one-size-fits-all
6. **Scientifically Grounded**: Based on peer-reviewed research (Hoefler 2023, Gidney-Fowler, etc.)

---

## Next Steps

1. Begin Phase 1 (MVP) implementation
2. Extract models from scientific papers (docs/ directory)
3. Implement core architecture components
4. Validate against published benchmarks
5. Iterate based on testing and feedback
