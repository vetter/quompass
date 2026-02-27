# Portable Resource Estimation for FTQC

I am part of a DOE national quantum center. we need a portability layer over the existing quantum resource estimation tools. i have attached a list of these tools below. We need the system to be portable for algorithms writers so that we can use these other tools as a backend when we are investigating different quantum architecture modalities (e.g., superconducting, ion trap, photonic). It will need to have parameterizable features like error correction methods and architectural parameters. we are focused on fault tolerant quantum computing, not NISQ. we understand that the tool may have dependencies on IRs like QIR; however, portabiilty is a high priority, so we must offer functionality at a high level and then map it down to lower existing framework as necessary.

## goals

- propose an api that is built on other quantum resource estimation tools, which our tool will use as a backend.
- our applications and algorithms researchers much have an abstraction at high enough level that they can write the algorithms once, and map them to different quantum modalities and parameters.
- ideally, these tools could leverage quantum compilers and other existing software in order to improve the accuracy and efficiency of its predicitions.

## background 

### **1. Key Context & Assumptions**

* We are operating in the context of current state-of-the-art (2024–2026) research, including **qLDPC codes**, **distributed quantum architectures**, and **dynamic magic state distillation pipelines**.
* We assume a need for **end-to-end toolchains** that bridge logical "bloqs" (Qualtran) with physical estimators (Azure QRE).

### **2. Decisions Made & Reasoning**

* **Framework Hierarchy:** We identified **Qualtran** as the preferred tool for high-level, hierarchical algorithm modeling and **Azure Quantum QRE** for physical-layer mapping and space-time volume analysis.
* **Niche Specialization:** **pyLIQTR** was selected for Quantum Signal Processing (QSP) tasks, and the **TUM (Wille et al.)** framework was identified for error-budget optimization.

### **3. Open Questions & Next Steps**

* **Code Implementation:** we think that the implementation should be based on python but are open to other implementations.
* **Hardware Modality:** Do we need to specialize estimates for a specific hardware platform (e.g., neutral atoms, superconducting qubits, or trapped ions? we need to be able to write algorithms portably and specialize when the architecture is fixed.
* **Specific Codes:** Is the focus shifting specifically toward **qLDPC** (Quantum Low-Density Parity-Check) resource reduction? no. we need to have flexible error correction.

### **5. Resource Manifest**

| Resource Name | Description | DOI / URL |
| --- | --- | --- |
| **Azure Quantum QRE** | Physical-layer estimator for QEC and T-factories. | [10.48550/arxiv.2311.05801](https://www.google.com/search?q=https://doi.org/10.48550/arxiv.2311.05801) |
| **Qualtran (Google)** | Hierarchical "bloq" library for algorithm decomposition. | [10.48550/arXiv.2409.04643](https://www.google.com/search?q=https://doi.org/10.48550/arXiv.2409.04643) |
| **pyLIQTR (MIT LL)** | Specialist library for QSP and QSVT resource analysis. | [10.48550/arxiv.2409.05777](https://www.google.com/search?q=https://doi.org/10.48550/arxiv.2409.05777) |
| **Wille et al. Framework** | ML-based error budget optimization for FTQC. | [10.48550/arxiv.2402.12434](https://doi.org/10.48550/arxiv.2402.12434) |
| **Distributed QRE (Filippov)** | Architecture for networked quantum resource estimation. | [10.48550/arxiv.2508.19160](https://www.google.com/search?q=https://doi.org/10.48550/arxiv.2508.19160) |
| **Dynamic Pipelines (Wang)** | Multi-level magic state distillation optimization. | [10.48550/arxiv.2509.24402](https://www.google.com/search?q=https://doi.org/10.48550/arxiv.2509.24402) |


### **6. Critical Continuity Info**

Maintain an **authentic, adaptive, and witty** persona. Balance high-level empathy for the complexity of quantum engineering with the directness of a peer. Ensure all complex math/science is rendered in LaTeX: $E = mc^2$ style.

### Biblio

TY  - JOUR
AU  - Buchs, G.
AU  - Others
PY  - 2025
TI  - The Role of Quantum Computing in Advancing Scientific High-Performance Computing
JO  - arXiv
UR  - https://doi.org/10.48550/arxiv.2508.11765
DO  - 10.48550/arxiv.2508.11765
ER  - 

TY  - JOUR
AU  - Filippov, D.
AU  - Others
PY  - 2025
TI  - Architecting Distributed Quantum Computers: Design Insights from Resource Estimation
JO  - arXiv
UR  - https://doi.org/10.48550/arxiv.2508.19160
DO  - 10.48550/arxiv.2508.19160
ER  - 

TY  - JOUR
AU  - Forster, T.
AU  - Others
PY  - 2025
TI  - Improving Hardware Requirements for Fault-Tolerant Quantum Computing by Optimizing Error Budget Distributions
JO  - arXiv
UR  - https://doi.org/10.48550/arxiv.2509.02683
DO  - 10.48550/arxiv.2509.02683
ER  - 

TY  - JOUR
AU  - Memon, Q. A.
AU  - Others
PY  - 2024
TI  - Quantum Computing: Navigating the Future of Computation, Challenges, and Technological Breakthroughs
JO  - Quantum Reports
VL  - 6
IS  - 4
SP  - 627
EP  - 663
UR  - https://doi.org/10.3390/quantum6040039
DO  - 10.3390/quantum6040039
ER  - 

TY  - JOUR
AU  - Quetschlich, N.
AU  - Others
PY  - 2024
TI  - Utilizing Resource Estimation for the Development of Quantum Computing Applications
JO  - arXiv
UR  - https://doi.org/10.48550/arxiv.2402.12434
DO  - 10.48550/arxiv.2402.12434
ER  - 

TY  - JOUR
AU  - Sharma, A.
AU  - Obenland, K.
PY  - 2024
TI  - Quantum Resources for Pure Thermal Shadows
JO  - IEEE Computer Society
UR  - https://doi.org/10.48550/arxiv.2409.05777
DO  - 10.48550/arxiv.2409.05777
ER  - 

TY  - JOUR
AU  - van Dam, W.
AU  - Others
PY  - 2023
TI  - Using Azure Quantum Resource Estimator for Assessing Performance of Fault Tolerant Quantum Computation
JO  - arXiv
UR  - https://doi.org/10.48550/arxiv.2311.05801
DO  - 10.48550/arxiv.2311.05801
ER  - 

TY  - JOUR
AU  - Wang, J.
AU  - Murali, P.
PY  - 2025
TI  - Orchestrating multi-level magic state distillation: a dynamic pipeline architecture
JO  - arXiv
UR  - https://doi.org/10.48550/arxiv.2509.24402
DO  - 10.48550/arxiv.2509.24402
ER  -