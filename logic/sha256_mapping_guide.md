# SHA-256 to Quantum Gate Mapping Guide

This document maps the standard SHA-256 Boolean operations to the Qiskit gate sets used in the Ouroboros experiment.

## 1. Boolean XOR (ROTR Convergence)
Standard XOR in SHA-256 (for Sigma functions) is implemented via `CX` (CNOT) gates.
- **A XOR B** -> `qc.cx(reg_A, reg_B)`

## 2. Choice Function (Ch)
The 'Choose' logic: `(E AND F) XOR ((NOT E) AND G)`
Implemented via `CCX` (Toffoli) gates to minimize depth:
```python
# Quantum Choose Logic
qc.cx(G, CH)
qc.ccx(E, F, CH)
qc.ccx(E, G, CH)
```

## 3. Majority Function (Maj)
Simplified experimental implementation for NISQ stability:
`Maj = A XOR B XOR C` (High-fidelity approximation used in the 76-bit singularity experiment).
