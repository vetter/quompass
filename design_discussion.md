# Quantum-Classical Resource Estimation Tool - Design Discussion

## Project Overview

Create a quantum-classical resource estimation and performance prediction tool in Python that:

1. **Generates resource estimates** for quantum-classical computer architectures:
   - Number of physical qubits
   - Number of logical qubits
   - Error correction resources
   - Ancilla qubits
   - Expected HPC system size (GPUs/CPUs)

2. **Reads algorithm descriptions** in a limited form or pseudo-code format using a DSL or API

3. **Provides Pareto optimization** - convolution of architectural specification with algorithm to generate Pareto front of resource estimates for architecture free variables

---

## Key Design Decisions to Make

### 1. Algorithm Description Language

**Question:** How should users describe their quantum algorithms?

**Options under consideration:**

- **Low-level (gate-based)**
  - Users specify gates, qubits, measurements directly
  - Pros: Maximum flexibility, precise resource counting
  - Cons: Verbose for complex algorithms

- **Mid-level (circuit operations)**
  - Describe common patterns (QFT, Grover iteration, etc.)
  - Pros: Balance of precision and usability
  - Cons: Need to build library of patterns

- **High-level (algorithmic)**
  - Describe algorithm intent ("solve linear system", "optimize function")
  - Pros: Easy for non-experts
  - Cons: Hard to accurately estimate resources

**Initial recommendation:** Python API that allows both gate-level and pattern-level descriptions, similar to Qiskit/Cirq but focused on resource analysis rather than execution.

### 2. Resource Estimation Model

**Questions to answer:**
- Which error correction scheme(s) to support?
  - Surface codes (industry standard)
  - Other codes (e.g., color codes, topological codes)?

- What parameters should be configurable?
  - Physical qubit error rates
  - Gate times
  - T-gate costs
  - Coherence times

- Should we support time-based estimates?
  - Circuit depth → wall-clock time conversions

### 3. Architectural Free Variables

**Question:** What architectural parameters should the Pareto optimization vary?

**Candidate variables:**
- Physical qubit error rate (representing different hardware quality)
- Code distance (error correction strength vs overhead trade-off)
- Number of available physical qubits (hardware scale constraints)
- Classical compute resources (CPUs/GPUs for hybrid algorithms)
- Connectivity/topology constraints (hardware-specific limitations)

### 4. Pareto Front Objectives

**Question:** What trade-offs should we optimize?

**Possible objectives:**
- Minimize total physical qubits
- Minimize runtime (circuit depth × gate time)
- Minimize classical resources (memory, CPU/GPU requirements)
- Minimize estimated cost/power consumption

---

## Next Steps

**Awaiting decisions on:**
1. Priority areas to focus on first
2. Specific use cases in mind (quantum chemistry, optimization, cryptography, etc.)
3. Target users (researchers, hardware developers, algorithm designers)
4. Existing tools/libraries to integrate with or differentiate from

---

## Status

- [x] Initial project specification reviewed
- [x] Key design questions identified
- [ ] Design decisions finalized
- [ ] Implementation plan created
- [ ] Code development started
