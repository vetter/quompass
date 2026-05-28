# Optimization Algorithm Templates for Quompass

## Compatibility Assessment

Quompass estimates resources for **fault-tolerant gate-based** quantum computing. The pipeline produces `LogicalCounts` (T-gates, CCZ gates, rotations, qubits) and maps them through QEC to physical qubits and runtime. Any new template must produce `LogicalCounts` to flow through the existing pipeline.

## What Does NOT Fit

### Quantum Annealing (D-Wave-style)
Fundamentally different computational model — no gates, no T-counts, no QEC. It doesn't produce `LogicalCounts` and can't flow through the Quompass pipeline. Adding it would require a parallel estimation framework, which would be scope creep and architecturally inconsistent.

### NISQ-era QAOA
Variational, shallow-circuit, doesn't use error correction. The resource story is about shot counts and classical optimizer iterations, not T-factories.

## What DOES Fit

### 1. QUBO via Grover Adaptive Search (GAS) — RECOMMENDED

This is the cleanest fit. Dürr-Høyer / Gilliam et al. (2021) showed how to solve QUBO problems on a fault-tolerant machine:

- Encode an n-variable QUBO as a quantum oracle that evaluates the objective function `x^T Q x` and compares against a threshold
- Use Grover search to find bitstrings with lower cost, iteratively tightening the threshold
- The oracle requires arithmetic circuits (additions, multiplications) that decompose cleanly into T-gates

**Resource model:**
- **Qubits**: `n` (problem variables) + `O(n log n)` ancillas for arithmetic evaluation of `x^T Q x`
- **Oracle T-cost**: dominated by the number of nonzero entries in the Q matrix — each quadratic term needs a controlled addition, costing `O(precision)` Toffolis. For a QUBO with `m` nonzero terms and `b`-bit precision: `~8 * m * b` T-gates per oracle call
- **Iterations**: `O(sqrt(2^n))` Grover iterations, each calling the oracle twice (evaluate + uncompute)
- **Total T-count**: `iterations * 2 * oracle_T`

**Proposed parameters**: `num_variables`, `num_quadratic_terms` (or `density`), `precision_bits`

**Why it fits well:**
- Maps directly to `LogicalCounts`
- Resource formulas are well-established in the literature (Gilliam et al. 2021, Campbell et al. 2019)
- Naturally extends the existing Grover template with a concrete, problem-aware oracle cost model
- Users can parameterize with problem size and density, making it easy to estimate real workloads
- MIP problems can be reformulated as QUBOs via penalty terms, so this covers that class too

**Key references:**
- Gilliam et al. (2021) — Grover Adaptive Search for QUBO
- Campbell et al. (2019) — concrete T-gate costs for arithmetic oracles
- Dürr & Høyer (1996) — quantum minimum finding algorithm

### 2. Quantum Walk Optimization (Montanaro 2018 / backtracking) — FUTURE CANDIDATE

For mixed-integer and constraint satisfaction problems, quantum walk-based backtracking provides a proven FT-compatible speedup:

- Montanaro (2018) gives a quantum speedup for branch-and-bound on tree-structured search spaces
- The algorithm uses quantum walks on the search tree, with an oracle that prunes branches
- Provides up to quadratic speedup over classical branch-and-bound

**Resource model:**
- **Qubits**: `O(depth * log(branching_factor))` + oracle ancillas
- **T-cost**: depends on the constraint-checking oracle, similar structure to Grover
- **Advantage**: more natural fit for constrained optimization (MIP) than raw Grover, because it exploits problem structure

**Proposed parameters**: `num_variables`, `num_constraints`, `branching_factor`, `tree_depth`

**Status:** More speculative — the literature has fewer concrete gate-count breakdowns compared to GAS for QUBO. Hold for a future phase.

## Recommendation

**Implement one template now: `qubo` (QUBO via Grover Adaptive Search)**

- Cleanest mapping to existing architecture
- Well-established resource formulas
- Covers QUBO directly and MIP via reformulation
- Extends the existing Grover template pattern

**Defer:** Quantum walk / branch-and-bound (less mature resource models)

**Exclude:** Quantum annealing and NISQ QAOA (different computational paradigms)
