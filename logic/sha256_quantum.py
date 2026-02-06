
"""
Quantum SHA-256 Gate Library
Copyright (c) 2026 Daniel Palma

Implements reversible Boolean logic for SHA-256 primitives using
Toffoli (CCX) and CNOT (CX) gates.
"""

from qiskit import QuantumCircuit

class SHA256QuantumGates:
    def __init__(self, qc, word_size=16):
        self.qc = qc
        self.w = word_size

    def xor_register(self, src_idx, dest_idx):
        """Quantum XOR: |a>|b> -> |a>|a ^ b>"""
        for i in range(self.w):
            self.qc.cx(src_idx + i, dest_idx + i)

    def rotr(self, reg_idx, n):
        """
        Right Rotation simulation.
        Note: In quantum circuits, rotation is just wire-swapping (logic relabeling),
        so this returns the re-indexed map without adding gate depth.
        """
        return [(reg_idx + (i + n) % self.w) for i in range(self.w)]

    def ch_function(self, e_reg, f_reg, g_reg, target_reg):
        """
        Quantum implementation of Ch(E,F,G) = (E & F) ^ (~E & G)
        Optimized cost: Requires Toffoli gates.
        """
        for i in range(self.w):
            # 1. G to Target
            self.qc.cx(g_reg + i, target_reg + i) 
            # 2. Logic: If E then flip if F!=G
            self.qc.ccx(e_reg + i, f_reg + i, target_reg + i)
            self.qc.ccx(e_reg + i, g_reg + i, target_reg + i)

    def maj_function(self, a_reg, b_reg, c_reg, target_reg):
        """
        Quantum implementation of Maj(A,B,C) = (A&B) ^ (A&C) ^ (B&C)
        """
        for i in range(self.w):
            self.qc.ccx(a_reg + i, b_reg + i, target_reg + i)
            self.qc.ccx(a_reg + i, c_reg + i, target_reg + i)
            self.qc.ccx(b_reg + i, c_reg + i, target_reg + i)
