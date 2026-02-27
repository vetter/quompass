
# quantum classical resource estimation and performance prediction


- create a quantum classical resource estimation and performance prediction tool, preferrably in python, that does the following
    - generates resource estimates for quantum classical computer architecture including numbers of physical qubits, number of logical qubits, error correction resources, ancilla qubits, expected size of required HPC system in terms of GPU/CPUs
    - reads a description of an algorithm in a limited form or pseudo code format. we can use a domain specific language or API that helps us build
    - design a convolution of the architectural specification with the algorithm to provide a parato front of resource estimates for an architecture free variables
    - review the scientific documents in the docs directory to get a better understanding of the algorithms and architectures that we want to model
        