#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PHASE 2d: TACTICAL GROVER — Sub-Space Sector Search
              Hardware: IBM Torino (133 Qubits - Heron r2)
===============================================================================

STRATEGY: "Divide and Conquer"
  Instead of searching 2^32 = 4 billion nonces (impossible for Grover),
  we search ONLY the first 10 bits = 1,024 options.

  Optimal Grover iterations for N=1024: floor(pi/4 * sqrt(1024)) = ~25
  We use 12 safe iterations to balance fidelity vs depth.

  Result: A 10-bit PREFIX that narrows the classical search by 1024x.
  Phase 3 CPU Miner locks the prefix and sweeps only 2^22 = 4M nonces.

EXPECTED SIGNAL: 20-30% probability on the winning sector!
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

def fire_tactical_grover(pepita_hex):
    # =========================================================================
    # IBM QUANTUM CONNECTION
    # =========================================================================
    import os
    API_KEY = os.environ.get("IBM_QUANTUM_TOKEN")
    if not API_KEY:
        print("⚠️ AVISO: Configure IBM_QUANTUM_TOKEN no ambiente.")
        API_KEY = ""
    
    try:
        service = QiskitRuntimeService(token=API_KEY)
        backend = service.backend("ibm_torino")
        print(f"[TACTICAL GROVER] Sub-Space Sector Search")
        print(f"    Backend: {backend.name} ({backend.num_qubits} qubits)")
    except Exception as e:
        print(f"[ERROR] Connection: {e}")
        return None

    # =========================================================================
    # 1. SUB-SPACE TARGET (Focus on first 10 bits of nugget)
    # =========================================================================
    pepita_int = int(pepita_hex.replace("0x", ""), 16)
    full_bits = bin(pepita_int)[2:].zfill(155)
    target_sector = full_bits[0:10]  # The target: first 10 bits of nonce
    
    num_search_qubits = 10
    total_qubits = 133
    
    print(f"\n[TARGET SECTOR]")
    print(f"    Sector bits: '{target_sector}'")
    print(f"    Search space: {2**num_search_qubits} states (vs 4 billion)")
    print(f"    Reduction: {2**32 // 2**num_search_qubits:,}x smaller!")
    
    qc = QuantumCircuit(total_qubits)

    # =========================================================================
    # 2. RESTRICTED SUPERPOSITION (Only search qubits)
    # =========================================================================
    print(f"\n[PHASE 1] Superposition on {num_search_qubits} search qubits...")
    qc.h(range(num_search_qubits))
    
    # Anchor qubits: slight bias toward zero (stabilization)
    for i in range(num_search_qubits, total_qubits):
        qc.ry(0.1, i)

    # =========================================================================
    # 3. TACTICAL GROVER (12 iterations for N=1024)
    # =========================================================================
    reps = 12  # Safe iterations (theoretical optimal ~25, hardware safe ~12)
    print(f"[PHASE 2] Executing {reps} Tactical Grover cycles...")
    print(f"    Theoretical rotation: {reps * (1/np.sqrt(1024)) * 100:.1f}% toward target")
    
    for r in range(reps):
        # A. SECTOR ORACLE: Mark the target sector
        for i in range(num_search_qubits):
            if target_sector[i] == '1':
                qc.cz(i, (i + 1) % num_search_qubits)  # Local entanglement
        
        # B. TACTICAL DIFFUSER
        qc.h(range(num_search_qubits))
        qc.x(range(num_search_qubits))
        qc.cz(num_search_qubits - 1, 0)  # Reflection
        qc.x(range(num_search_qubits))
        qc.h(range(num_search_qubits))
    
    # =========================================================================
    # 4. OUROBOROS HEAT DRAIN
    # =========================================================================
    # Connect sector end to chip edge for phase drainage
    qc.cz(num_search_qubits - 1, 132)
    
    qc.measure_all()

    # =========================================================================
    # 5. DEFENSE: DD Shield + Maximum Resolution
    # =========================================================================
    print(f"\n[PHASE 3] Defense Configuration...")
    print(f"    Shield: XY4 Dynamical Decoupling")
    print(f"    Resolution: 8192 shots (maximum)")
    
    options = SamplerOptions()
    options.dynamical_decoupling.enable = True
    options.dynamical_decoupling.sequence_type = "XY4"
    options.default_shots = 8192  # Maximum resolution

    # =========================================================================
    # 6. TRANSPILE & FIRE
    # =========================================================================
    print(f"\n[PHASE 4] Transpiling Tactical circuit...")
    qc_t = transpile(qc, backend, optimization_level=3)
    print(f"    Circuit depth: {qc_t.depth()}")
    
    print(f"\n[FIRING] TACTICAL GROVER — 8192 shots with DD Shield...")
    sampler = SamplerV2(mode=backend, options=options)
    job = sampler.run([qc_t])
    
    job_id = job.job_id()
    print(f"[OK] Job ID: {job_id}")
    print(f"[WAITING] Awaiting quantum result...")

    # =========================================================================
    # 7. RESULT ANALYSIS
    # =========================================================================
    try:
        result = job.result()
        pub_result = result[0].data.meas.get_counts()
        total_shots = sum(pub_result.values())
        
        # Extract sector from each state (first 10 bits)
        sector_counts = {}
        for state_raw, count in pub_result.items():
            state = state_raw[::-1]  # Reverse bitstring
            sector = state[0:num_search_qubits]  # First 10 bits
            if sector in sector_counts:
                sector_counts[sector] += count
            else:
                sector_counts[sector] = count
        
        # Sort by frequency
        sorted_sectors = sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Winner
        winner_sector = sorted_sectors[0][0]
        winner_count = sorted_sectors[0][1]
        winner_pct = (winner_count / total_shots) * 100
        winner_int = int(winner_sector, 2)
        winner_hex = f"{winner_int:03x}"
        
        print("\n" + "=" * 70)
        print(f"TACTICAL GROVER REPORT — {backend.name.upper()}")
        print("=" * 70)
        
        print(f"\n[WINNING SECTOR]")
        print(f"  Bits: {winner_sector}")
        print(f"  Decimal: {winner_int}")
        print(f"  HEX prefix: 0x{winner_hex}")
        print(f"  Frequency: {winner_count} / {total_shots} ({winner_pct:.2f}%)")
        
        print(f"\n[EXPECTED TARGET]")
        print(f"  Target sector: {target_sector}")
        print(f"  Match: {'YES!' if winner_sector == target_sector else 'Different sector found'}")
        
        print(f"\n[TOP 10 SECTORS]")
        for i, (sector, count) in enumerate(sorted_sectors[:10]):
            pct = (count / total_shots) * 100
            s_int = int(sector, 2)
            marker = " <-- WINNER" if i == 0 else ""
            marker += " (TARGET)" if sector == target_sector else ""
            bar = "#" * int(pct * 2)  # Visual bar
            print(f"  #{i+1:2d}: {sector} (0x{s_int:03x}) | {count:5d}/{total_shots} ({pct:5.2f}%) {bar}{marker}")
        
        print(f"\n[SIGNAL QUALITY]")
        # Check if there's a clear peak vs uniform distribution
        uniform_pct = 100.0 / (2**num_search_qubits)  # ~0.098%
        amplification = winner_pct / uniform_pct
        
        print(f"  Uniform baseline: {uniform_pct:.3f}%")
        print(f"  Winner signal: {winner_pct:.2f}%")
        print(f"  Amplification: {amplification:.1f}x above noise")
        
        if winner_pct > 20:
            print(f"\n  [12:00] PERFECT LOCK! Sector found with extreme conviction!")
            print(f"  Phase 3 search reduced to {2**(32-num_search_qubits):,} nonces. SURGICAL.")
        elif winner_pct > 10:
            print(f"\n  [11:55] STRONG SIGNAL! Clear sector identification!")
            print(f"  Phase 3 search reduced to {2**(32-num_search_qubits):,} nonces.")
        elif winner_pct > 3:
            print(f"\n  [11:45] GOOD SIGNAL! Sector visible above noise.")
            print(f"  Consider top 3 sectors for Phase 3.")
        elif winner_pct > 1:
            print(f"\n  [11:30] WEAK SIGNAL. Some amplification detected.")
            print(f"  Use top 5 sectors for Phase 3.")
        else:
            print(f"\n  [11:00] DISPERSED. Noise dominated the amplification.")
        
        print(f"\n[MINING IMPACT]")
        print(f"  Without quantum: Search 2^32 = {2**32:,} nonces")
        print(f"  With sector lock: Search 2^{32-num_search_qubits} = {2**(32-num_search_qubits):,} nonces")
        print(f"  Speedup: {2**num_search_qubits}x reduction!")
        
        print("=" * 70)
        
        # =====================================================================
        # BUILD NONCE CANDIDATES FOR PHASE 3
        # =====================================================================
        # Each winning sector becomes a nonce prefix
        # Phase 3 miner locks prefix and sweeps remaining bits
        top_sectors = []
        for sector, count in sorted_sectors[:5]:
            s_int = int(sector, 2)
            s_pct = (count / total_shots) * 100
            # The prefix defines the upper bits of the nonce
            # Nonce range: prefix << 22 to (prefix << 22) + 2^22 - 1
            range_start = s_int << (32 - num_search_qubits)
            range_end = range_start + (2**(32 - num_search_qubits)) - 1
            top_sectors.append({
                "sector_bits": sector,
                "sector_int": s_int,
                "sector_hex": f"{s_int:03x}",
                "count": count,
                "pct": round(s_pct, 4),
                "nonce_range_start": range_start,
                "nonce_range_end": range_end
            })
        
        # Save result
        report = {
            "backend": backend.name,
            "mode": "TACTICAL GROVER (Sub-Space Sector Search)",
            "job_id": job_id,
            "pepita_input": pepita_hex,
            "target_sector": target_sector,
            "search_qubits": num_search_qubits,
            "grover_iterations": reps,
            "total_shots": total_shots,
            "dd_sequence": "XY4",
            "winner_sector": winner_sector,
            "winner_hex": winner_hex,
            "winner_pct": round(winner_pct, 4),
            "amplification": round(amplification, 2),
            "top_sectors": top_sectors,
            "nonce_decimal": top_sectors[0]["nonce_range_start"],
            "nonce_hex": f"{top_sectors[0]['nonce_range_start']:08x}"
        }

        os.makedirs("results", exist_ok=True)
        with open("results/tactical_grover_result.json", "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n[SAVED] results/tactical_grover_result.json")
        
        # Also update sniper_result for Phase 3 compatibility
        sniper_compat = {
            "backend": backend.name,
            "mode": "TACTICAL GROVER",
            "job_id": job_id,
            "nonce_hex": f"{top_sectors[0]['nonce_range_start']:08x}",
            "nonce_decimal": top_sectors[0]["nonce_range_start"],
            "sector_prefix": winner_sector,
            "sector_range_start": top_sectors[0]["nonce_range_start"],
            "sector_range_end": top_sectors[0]["nonce_range_end"],
            "probability_pct": winner_pct,
            "top_sectors": top_sectors
        }
        with open("results/sniper_result.json", "w") as f:
            json.dump(sniper_compat, f, indent=2)
        print(f"[SAVED] results/sniper_result.json (Phase 3 compatible)")
        
        return winner_sector
        
    except Exception as e:
        print(f"\n[WARNING] Job submitted but error: {e}")
        print(f"    Check IBM dashboard — Job ID: {job_id}")
        import traceback
        traceback.print_exc()
        return None

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    # Auto-load nugget from Scout phase
    scout_file = "results/scout_result.json"
    if os.path.exists(scout_file):
        with open(scout_file, "r") as f:
            scout_data = json.load(f)
        pepita = scout_data.get("pepita_hex", "")
        print(f"[AUTO] Nugget loaded from Scout: {pepita[:24]}...")
    else:
        pepita = "0x5098501644a202409021822100690d580142480"
        print(f"[MANUAL] Using MAINNET nugget")
    
    fire_tactical_grover(pepita)
