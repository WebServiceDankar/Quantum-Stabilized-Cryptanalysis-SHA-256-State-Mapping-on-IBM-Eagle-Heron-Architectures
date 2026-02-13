#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PHASE 2e: REFINED TACTICAL GROVER — Proper Phase Oracle
              Hardware: IBM Torino (133 Qubits - Heron r2)
===============================================================================

FIX: The previous oracle used CZ between adjacent search qubits, which
does NOT properly mark the target state. A correct Grover oracle must:

  1. Apply X to qubits where target bit = '0'
  2. Apply multi-controlled Z (marks |target⟩ with phase -1)
  3. Apply X again (undo step 1)

This ensures ONLY the target state gets a phase flip.

For 10 qubits, we decompose MCZ into a CZ ladder using ancillas.
===============================================================================
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import numpy as np
import json
import os

from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2, SamplerOptions

def _apply_mcz(qc, search_qubits, ancilla_start):
    """Multi-controlled Z via V-chain Toffoli decomposition."""
    n = len(search_qubits)
    if n == 2:
        qc.cz(search_qubits[0], search_qubits[1])
        return
    if n == 3:
        qc.h(search_qubits[2])
        qc.ccx(search_qubits[0], search_qubits[1], search_qubits[2])
        qc.h(search_qubits[2])
        return
    
    # V-chain for n >= 4
    anc = list(range(ancilla_start, ancilla_start + n - 2))
    
    # Forward: build AND-chain
    qc.ccx(search_qubits[0], search_qubits[1], anc[0])
    for i in range(2, n - 1):
        qc.ccx(search_qubits[i], anc[i - 2], anc[i - 1])
    
    # Phase flip on last search qubit controlled by last ancilla
    qc.cz(anc[n - 3], search_qubits[n - 1])
    
    # Reverse: uncompute AND-chain
    for i in range(n - 2, 1, -1):
        qc.ccx(search_qubits[i], anc[i - 2], anc[i - 1])
    qc.ccx(search_qubits[0], search_qubits[1], anc[0])

def build_oracle(qc, search_qubits, target_bits, ancilla_start):
    """
    Proper Grover oracle: phase-flips ONLY the target state.
    """
    # Step 1: X on qubits where target = '0'
    for i, bit in enumerate(target_bits):
        if bit == '0':
            qc.x(search_qubits[i])
    
    # Step 2: Multi-controlled Z
    _apply_mcz(qc, search_qubits, ancilla_start)
    
    # Step 3: Undo X
    for i, bit in enumerate(target_bits):
        if bit == '0':
            qc.x(search_qubits[i])

def build_diffuser(qc, search_qubits, ancilla_start):
    """Grover diffuser: reflection about the mean."""
    qc.h(search_qubits)
    qc.x(search_qubits)
    _apply_mcz(qc, search_qubits, ancilla_start)
    qc.x(search_qubits)
    qc.h(search_qubits)

def fire_refined_tactical(pepita_hex):
    # =========================================================================
    # CONNECTION
    # =========================================================================
    API_KEY = "nMvJnquaNusDZYB77_bBM-LO5-XPrJBjVRq2hytFub2n"
    
    try:
        service = QiskitRuntimeService(token=API_KEY)
        backend = service.backend("ibm_torino")
        print(f"[REFINED TACTICAL GROVER] Proper Phase Oracle")
        print(f"    Backend: {backend.name} ({backend.num_qubits} qubits)")
    except Exception as e:
        print(f"[ERROR] Connection: {e}")
        return None

    # =========================================================================
    # TARGET
    # =========================================================================
    pepita_int = int(pepita_hex.replace("0x", ""), 16)
    full_bits = bin(pepita_int)[2:].zfill(155)
    
    num_search = 10  # Search qubits
    target_sector = full_bits[0:num_search]
    
    # Ancillas start right after search qubits
    ancilla_start = num_search  # qubits 10-17 are ancillas (8 needed for 10-qubit MCZ)
    num_ancillas = num_search - 2  # 8 ancillas for V-chain decomposition
    total_qubits = 133
    
    search_qubits = list(range(num_search))
    
    # Optimal Grover iterations for N=1024: floor(pi/4 * sqrt(1024)) = 25
    # We use 8 iterations (safe for hardware depth with proper oracle)
    reps = 8
    
    print(f"\n[TARGET]")
    print(f"    Sector: '{target_sector}' ({num_search} bits)")
    print(f"    Space: {2**num_search} states")
    print(f"    Ancillas: {num_ancillas} (V-chain MCZ)")
    print(f"    Grover iterations: {reps}")
    print(f"    Expected rotation: {np.sin((2*reps+1) * np.arcsin(1/np.sqrt(2**num_search)))**2 * 100:.1f}%")
    
    # =========================================================================
    # BUILD CIRCUIT
    # =========================================================================
    qc = QuantumCircuit(total_qubits)
    
    # Superposition on search register only
    qc.h(search_qubits)
    
    # Grover iterations with PROPER oracle
    print(f"\n[BUILDING] {reps} Grover iterations with proper phase oracle...")
    for r in range(reps):
        build_oracle(qc, search_qubits, target_sector, ancilla_start)
        build_diffuser(qc, search_qubits, ancilla_start)
    
    qc.measure_all()
    
    gate_ops = qc.count_ops()
    print(f"    Raw gates: {dict(gate_ops)}")
    print(f"    Total gates: {sum(gate_ops.values())}")

    # =========================================================================
    # DEFENSE & FIRE
    # =========================================================================
    options = SamplerOptions()
    options.dynamical_decoupling.enable = True
    options.dynamical_decoupling.sequence_type = "XY4"
    options.default_shots = 8192
    
    print(f"\n[TRANSPILING] optimization_level=3...")
    qc_t = transpile(qc, backend, optimization_level=3)
    print(f"    Transpiled depth: {qc_t.depth()}")
    
    print(f"\n[FIRING] REFINED TACTICAL GROVER — 8192 shots + DD Shield...")
    sampler = SamplerV2(mode=backend, options=options)
    job = sampler.run([qc_t])
    
    job_id = job.job_id()
    print(f"[OK] Job ID: {job_id}")
    print(f"[WAITING] Awaiting quantum result...")

    # =========================================================================
    # RESULTS
    # =========================================================================
    try:
        result = job.result()
        pub_result = result[0].data.meas.get_counts()
        total_shots = sum(pub_result.values())
        
        # Aggregate by sector (first 10 bits)
        sector_counts = {}
        for state_raw, count in pub_result.items():
            state = state_raw[::-1]
            sector = state[0:num_search]
            sector_counts[sector] = sector_counts.get(sector, 0) + count
        
        sorted_sectors = sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)
        
        winner_sector = sorted_sectors[0][0]
        winner_count = sorted_sectors[0][1]
        winner_pct = (winner_count / total_shots) * 100
        
        print("\n" + "=" * 70)
        print(f"REFINED TACTICAL GROVER REPORT — {backend.name.upper()}")
        print("=" * 70)
        
        print(f"\n[WINNING SECTOR]")
        print(f"  Bits: {winner_sector}")
        print(f"  HEX: 0x{int(winner_sector, 2):03x}")
        print(f"  Frequency: {winner_count}/{total_shots} ({winner_pct:.2f}%)")
        print(f"  Target match: {'YES!' if winner_sector == target_sector else 'No'}")
        
        print(f"\n[TOP 10 SECTORS]")
        uniform_pct = 100.0 / (2**num_search)
        for i, (sector, count) in enumerate(sorted_sectors[:10]):
            pct = (count / total_shots) * 100
            amp = pct / uniform_pct
            bar = "#" * int(pct)
            marker = ""
            if i == 0: marker += " <-- WINNER"
            if sector == target_sector: marker += " (TARGET)"
            print(f"  #{i+1:2d}: {sector} (0x{int(sector,2):03x}) | "
                  f"{count:5d}/{total_shots} ({pct:5.2f}%) [{amp:.1f}x] {bar}{marker}")
        
        amplification = winner_pct / uniform_pct
        print(f"\n[SIGNAL]")
        print(f"  Uniform baseline: {uniform_pct:.3f}%")
        print(f"  Winner: {winner_pct:.2f}%")
        print(f"  Amplification: {amplification:.1f}x")
        
        if winner_pct > 20:
            print(f"  [12:00] PERFECT LOCK!")
        elif winner_pct > 10:
            print(f"  [11:55] STRONG SIGNAL!")
        elif winner_pct > 3:
            print(f"  [11:45] GOOD SIGNAL!")
        elif winner_pct > 1:
            print(f"  [11:30] WEAK but REAL signal")
        else:
            print(f"  [11:00] Dispersed")

        print("=" * 70)
        
        # Save
        top_sectors = []
        for sector, count in sorted_sectors[:5]:
            s_int = int(sector, 2)
            range_start = s_int << (32 - num_search)
            range_end = range_start + (2**(32 - num_search)) - 1
            top_sectors.append({
                "sector_bits": sector,
                "sector_int": s_int,
                "sector_hex": f"{s_int:03x}",
                "count": count,
                "pct": round((count/total_shots)*100, 4),
                "nonce_range_start": range_start,
                "nonce_range_end": range_end
            })

        report = {
            "backend": backend.name,
            "mode": "REFINED TACTICAL GROVER (Proper Phase Oracle + V-chain MCZ)",
            "job_id": job_id,
            "pepita_input": pepita_hex,
            "target_sector": target_sector,
            "search_qubits": num_search,
            "grover_iterations": reps,
            "total_shots": total_shots,
            "winner_sector": winner_sector,
            "winner_pct": round(winner_pct, 4),
            "amplification": round(amplification, 2),
            "top_sectors": top_sectors,
            "nonce_decimal": top_sectors[0]["nonce_range_start"],
            "nonce_hex": f"{top_sectors[0]['nonce_range_start']:08x}"
        }
        
        os.makedirs("results", exist_ok=True)
        with open("results/tactical_refined_result.json", "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n[SAVED] results/tactical_refined_result.json")
        
        with open("results/sniper_result.json", "w") as f:
            json.dump(report, f, indent=2)
        print(f"[SAVED] results/sniper_result.json")
        
        return winner_sector
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    scout_file = "results/scout_result.json"
    if os.path.exists(scout_file):
        with open(scout_file, "r") as f:
            scout_data = json.load(f)
        pepita = scout_data.get("pepita_hex", "")
        print(f"[AUTO] Nugget loaded: {pepita[:24]}...")
    else:
        pepita = "0x5098501644a202409021822100690d580142480"
        print(f"[MANUAL] Using MAINNET nugget")
    
    fire_refined_tactical(pepita)
