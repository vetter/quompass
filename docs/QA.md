# Open Questions — Portable QRE

## Architecture & Scope

### Q1: What is the primary user persona?
The prompt mentions "applications and algorithms researchers." Are these people who:
- (a) Write quantum algorithms from scratch (need full expressiveness)?
- (b) Parameterize known algorithm templates (e.g., "estimate resources for Shor's with $n = 2048$ bits")?
- (c) Both?

(c)

This determines whether the API surface is a full algorithm-construction DSL or a parameterized catalog of known algorithms.

### Q2: Which quantum algorithm families must be supported at launch?
Candidates from the literature and backend capabilities:
- Hamiltonian simulation (Trotter, QSP/QSVT, qubitization)
- Quantum Phase Estimation (QPE)
- Quantum chemistry (double factorization, THC, sparse)
- Cryptanalysis (Shor's factoring / discrete log)
- Grover / amplitude estimation
- Variational (VQE, QAOA) — but the prompt says FTQC only, so is this excluded?

yes, we will only focus on FTQC, so variational is out

### Q3: Depth of classical co-processing estimation?
The December 2025 plan had a "Classical Resource Estimator" module (CPU/GPU counts, memory, bandwidth). Does the new portable-QRE effort still need classical HPC resource estimation, or is the scope now purely quantum?

good question. ideally, we will want to couple the quantum system to a classical gpu/cpu system. we already know how to model classical systems, so it is a lower priority; hwoever, we will want to couple them at some future time. 

### Q4: Distributed / networked quantum computing — in scope for MVP?
Filippov's distributed QRE paper is listed in the resource manifest. Is multi-node quantum estimation a launch requirement, or a future extension?

let's not worry about distributed quantum computing now

### Q5: Dynamic magic state distillation pipelines — in scope for MVP?
Wang & Murali's dynamic pipeline work is listed. Is this an optimization the portable layer should expose, or is it sufficient to let the backend (Azure QRE) handle distillation internally?

do not expose it now.

---

## Backend Integration

### Q6: Are all four backends required, or can we start with a subset?
My recommendation is to start with **Qualtran + Azure QRE** (logical → physical pipeline) and add pyLIQTR and MQT incrementally. Does this align with the center's priorities?

start with a subset.

### Q7: Azure QRE licensing and access model?
Azure QRE runs locally via `pip install qdk`. Is the team comfortable with the Microsoft dependency, or do we need a fully open-source fallback for the physical estimation layer?

we can use MSFT for now, but we must keep an eye on some fallback positions on our design decisions.

### Q8: Qualtran stability tolerance?
Qualtran is beta/experimental with no backward-compatibility guarantees. Is the team willing to pin versions and absorb API changes, or do we need an isolation layer that insulates users from Qualtran's API churn?

we need an isolation layer.

---

## Error Correction & Hardware Models

### Q9: Which QEC codes must be parameterizable at launch?
Options:
- Surface code (supported by Azure QRE and Qualtran natively)
- Floquet code (Azure QRE only, Majorana qubits)
- Color code (MQT QECC has decoders, but no resource estimator)
- qLDPC codes (no mature backend support yet)
- Custom / user-defined codes (Azure QRE supports custom QEC scheme parameters)


The prompt says "flexible error correction." Does that mean supporting all of the above, or supporting the surface code with a clean extension point for future codes?

yes, i would argue this will be one of the more important aspects of our design, so we will need to be prepared to use all of these as well as codes we don't know yet.

### Q10: Which hardware modalities must be supported at launch?
Azure QRE provides 6 predefined qubit models:
- Superconducting (gate-based, ns timescale, $10^{-3}$ or $10^{-4}$ error rates)
- Trapped ion (gate-based, μs timescale, $10^{-3}$ or $10^{-4}$ error rates)
- Majorana / topological ($10^{-4}$ or $10^{-6}$ error rates)

The prompt also mentions photonic and neutral atom. Neither has a predefined model in any backend. Custom models would need to be constructed. Are photonic and neutral atom required at launch, or can they be added via the custom qubit model interface?


they can be added later.


---

## Output & Optimization

### Q11: What output metrics matter most?
Candidates:
- Physical qubit count
- Wall-clock runtime
- T-gate / magic state count
- Code distance
- Number of T factories
- rQOPS (reliable quantum operations per second)
- Space-time volume (qubits × time)
- Error budget breakdown

Should the portable layer expose all of these, or present a curated summary with drill-down capability?

yes, we need a portability layer with the ability to drill down

### Q12: Pareto front generation — still a requirement?
The December 2025 plan emphasized multi-objective optimization (minimize qubits vs. time vs. cost). Azure QRE supports frontier estimation natively (`estimateType: "frontier"`). Should the portable layer wrap this, extend it, or implement its own?

let's implement our own design space exploration.

### Q13: MQT error budget optimization — priority level?
The Wille/Forster work shows that optimizing the error budget distribution (instead of uniform 1/3 split) can reduce physical costs. This requires iterative calls to Azure QRE. Is this an important differentiator, or a nice-to-have?

nice-to-have 

---

## Engineering & Deployment

### Q14: Packaging and distribution model?
Options:
- (a) Single pip-installable Python package with optional backend dependencies
- (b) Container image (Docker) with all backends pre-installed
- (c) Both

let's go with (a)

### Q15: CI/CD and testing strategy?
Backend tools have heavy dependencies (Rust for Azure QRE, C++ for MQT). How should we handle CI? Options:
- Mock backends for unit tests, real backends for integration tests
- Docker-based CI with all backends installed

the first one

### Q16: Jupyter / notebook-first or CLI-first?
The December plan proposed a CLI. Azure QRE and Qualtran are heavily notebook-oriented. What is the primary interface for the center's researchers?

i would say cli but not exclude notebook access.

### Q17: Visualization requirements?
Azure QRE has built-in Jupyter widgets for space-time diagrams. Qualtran has bloq graph visualization. Should the portable layer:
- (a) Pass through backend visualizations?
- (b) Provide its own unified visualization?
- (c) Export data for external tools (matplotlib, plotly)?

let's do b and c

---

## Governance & Collaboration

### Q18: Open source or internal?
Will this tool be open-sourced? This affects dependency choices, licensing, and documentation standards.

it will almost certainly need to be open source to gain wide adoption.

### Q19: Multi-team contribution model?
Will other DOE centers contribute backends or algorithms? If so, we need plugin architecture from day one.

perhaps, so yes, we need some modularity and flexibility

### Q20: Relationship to existing QIR / QAT standards?
The prompt mentions QIR (Quantum Intermediate Representation). Should the portable layer emit QIR as an intermediate step, or bypass it in favor of direct API calls to backends?

good question. we are still evaluating this design. use your best judgement.

