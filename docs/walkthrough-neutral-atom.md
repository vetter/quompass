# Walkthrough: Extending quompass for a New Architecture

> **Private case study.** This walkthrough depends on the private example
> YAMLs in `examples/` at the studio root (`shor_2048_gidney2025.yaml`,
> `neutral_atom.yaml`, `lp_qldpc.yaml`) and is not shipped with the public
> quompass distribution. The `transversal_magic_states` capability it
> exercises is in the public source tree under `public/src/quompass/`.

The Chemistry walkthrough used quompass entirely "from the catalog" — built-in templates, hardware presets, and QEC schemes. This walkthrough does the opposite. It follows a real research question that none of the built-ins can answer, and extends quompass across all three of its layers — a new algorithm, a new hardware target, and a new error-correcting code — including the one case where YAML is not enough and the estimator itself must be extended.

The case study reproduces a 2026 result: Cain et al. showed that Shor's algorithm for RSA-2048 can be run on roughly **10,000 neutral atoms**, two to three orders of magnitude below the superconducting surface-code estimates. We rebuild that estimate in quompass from scratch. The finished example ships in the repository as `examples/shor_2048_gidney2025.yaml`, `examples/neutral_atom.yaml`, and `examples/lp_qldpc.yaml`; here we build each file and explain every field.

## The Scenario

Three papers define the problem (full citations in [References](#references)):

- **The logical circuit.** Gidney (2025) gives a windowed-arithmetic circuit that factors a 2048-bit RSA integer with ~1,399 logical qubits and ~6.5 × 10⁹ Toffoli gates.
- **The reference estimate.** Cain et al. (2026) re-cost that circuit on a reconfigurable neutral-atom processor using high-rate lifted-product (LP) qLDPC codes, and report a "space-efficient" architecture of **11,033 atoms**.
- **The contrast.** The same circuit on a surface code with superconducting hardware needs ~16 million physical qubits — quompass shows this directly.

The gap between 16 million and 11 thousand is not hardware speed. It is two structural choices that the surface-code defaults bake in:

1. **The code.** A surface code spends `2 * d^2` physical qubits per logical qubit. A high-rate qLDPC code amortizes a near-constant overhead across many logical qubits.
2. **The magic states.** Surface-code architectures distill T/CCZ states in dedicated 15-to-1 factories — for this circuit, the factories alone are ~13M qubits. Neutral-atom LP-code architectures apply T and CCZ *transversally*, with magic-state cultivation, and need no factory at all.

quompass models (1) with a `FormulaQEC` scheme — no code change. Modeling (2) requires teaching the estimator a concept it does not yet have. We hit that wall deliberately in Step 3.

## Step 1: Capture the Logical Algorithm

quompass has a Shor template, but it implements the Gidney–Ekerå (2019) construction, not the newer Gidney (2025) circuit. Writing a new `AlgorithmTemplate` class is the right move for a *parameterized family* of circuits; for a single published circuit the lighter path is a YAML `AlgorithmSpec` — enter the logical counts directly.

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

The `logical_counts` block maps field-for-field onto the `LogicalCounts` dataclass — the portable interchange format. Two modeling decisions are worth calling out:

- **Toffolis go in `ccz_count`, not `t_count`.** A Toffoli and a CCZ are equivalent up to Clifford corrections and cost the same in magic states. quompass's `total_t_equivalent` property expands each CCZ into 4 T gates — a convention that matters in Step 3.
- **`rotation_count: 0`.** Gidney's circuit replaces the textbook QFT with windowed arithmetic, so there are no arbitrary-angle rotations to synthesize; the cost is entirely in Toffolis.

Load it and confirm:

```python
from quompass.io import load_algorithm

spec = load_algorithm("examples/shor_2048_gidney2025.yaml")
print(spec.logical_counts.num_qubits)                  # 1399
print(f"{spec.logical_counts.total_t_equivalent:,}")   # 26,000,000,000
```

## Step 2: Model the Neutral-Atom Hardware

A hardware target is a `HardwareModel` wrapping a `QubitParams` record. None of the six built-in presets is a neutral-atom processor, so we write one as YAML. The numbers come from the device assumptions in Cain et al.: a physical entangling-gate error rate of p = 0.1%, and a stabilizer-measurement cycle of about 1 ms.

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

## Step 3: Run It and Hit the Factory Wall

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

## Step 4: Extend the Estimator

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

## Step 5: Define the qLDPC Code Scheme

With the estimator extended, the LP qLDPC code can be written as a `FormulaQEC` YAML. This is where the modeling judgment lives, so each field gets a justification.

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

## Step 6: Run the Full Estimate

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

## Step 7: Test the Extension

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

## A Note on Honest Calibration

This example reproduces a published result, and it is worth being explicit about which numbers are *derived* and which are *fitted* — a distinction every resource-estimation model should make visible.

**Pinned to the literature:** the 1,399 logical qubits and 6.5 × 10⁹ Toffolis (Gidney 2025; Cain et al. Fig. 3a); the physical error rate p = 0.1%; the ~1 ms stabilizer round; the LP memory-code parameters ≈ [[5278, 1480, ≤24]].

**Fitted by the modeler:** the QEC `threshold` (0.008) and `prefactor` (2 × 10⁻⁵), chosen so the distance search lands near d ≈ 25, consistent with the paper's d ≤ 24; and `qubits_formula = 7.886`, which is the paper's reported 11,033 ÷ 1,399 — an *effective* overhead, not a derivation of the LP code's geometry from first principles.

The analytical backend also rounds physical-qubits-per-logical to an integer, so the total is `1399 * 8 = 11,192` rather than 11,033 — a 1.5% artifact of that rounding. None of this is hidden: it is all in the comments of `examples/lp_qldpc.yaml`. For a higher-fidelity estimate, the LP code's overhead and threshold would be computed by a dedicated logical/physical backend — the role the Qualtran and Azure adapters play for surface codes — and a `FormulaQEC` calibrated to a paper is the fast, transparent first cut.

## References

1. C. Gidney, *How to factor 2048 bit RSA integers with less than a million noisy qubits* (2025). arXiv:2505.15917. DOI: [10.48550/arXiv.2505.15917](https://doi.org/10.48550/arXiv.2505.15917). — the logical circuit used by this example.
2. M. Cain, Q. Xu, R. King, et al., *Shor's algorithm is possible with as few as 10,000 reconfigurable atomic qubits* (2026). arXiv:2603.28627. DOI: [10.48550/arXiv.2603.28627](https://doi.org/10.48550/arXiv.2603.28627). — the reference physical estimate.
3. C. Gidney and M. Ekerå, *How to factor 2048 bit RSA integers in 8 hours using 20 million noisy qubits*, Quantum **5**, 433 (2021). DOI: [10.22331/q-2021-04-15-433](https://doi.org/10.22331/q-2021-04-15-433). — the earlier construction behind quompass's built-in Shor template.
4. A. G. Fowler, M. Mariantoni, J. M. Martinis, and A. N. Cleland, *Surface codes: Towards practical large-scale quantum computation*, Phys. Rev. A **86**, 032324 (2012). DOI: [10.1103/PhysRevA.86.032324](https://doi.org/10.1103/PhysRevA.86.032324). — the surface-code model behind quompass's `SurfaceCode`.
5. S. Bravyi and J. Haah, *Magic-state distillation with low overhead*, Phys. Rev. A **86**, 052329 (2012). DOI: [10.1103/PhysRevA.86.052329](https://doi.org/10.1103/PhysRevA.86.052329). — the distillation model the transversal path replaces.
6. P. Panteleev and G. Kalachev, *Quantum LDPC codes with almost linear minimum distance*, IEEE Trans. Inf. Theory **68**, 213 (2022). DOI: [10.1109/TIT.2021.3119384](https://doi.org/10.1109/TIT.2021.3119384). — introduces the lifted-product (LP) construction.
7. D. Bluvstein, S. J. Evered, A. A. Geim, et al., *Logical quantum processor based on reconfigurable atom arrays*, Nature **626**, 58 (2024). DOI: [10.1038/s41586-023-06927-3](https://doi.org/10.1038/s41586-023-06927-3). — transversal logical operations on neutral-atom hardware.
