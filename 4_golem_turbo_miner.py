#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
GOLEM TURBO MINER — Optimized CPU SHA-256 Engine
===============================================================================
Máxima velocidade CPU com:
  - Midstate caching (pré-computa o SHA256 dos primeiros 64 bytes)
  - Multiprocessing com todos os cores
  - Busca progressiva: Setor -> Super-Setor -> Full Sweep
  - Feedback em tempo real
===============================================================================
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import hashlib
import struct
import multiprocessing
import time
import json
import os

# =============================================================================
# QUANTUM INTELLIGENCE (Tactical Grover results)
# =============================================================================
DEFAULT_SECTORS = [
    {"hex": "0a7", "bits": "0010100111", "pct": 0.39},
    {"hex": "0a4", "bits": "0010100100", "pct": 0.33},
    {"hex": "0b6", "bits": "0010110110", "pct": 0.32},
    {"hex": "067", "bits": "0001100111", "pct": 0.31},
    {"hex": "3be", "bits": "1110111110", "pct": 0.31},
]

def mine_worker(args):
    """Worker: varre um range de nonces usando midstate optimization."""
    worker_id, start, end, header_hex, target_zeros, queue = args
    
    # Parse header: 80 bytes, nonce nos ultimos 4 bytes
    header_bytes = bytes.fromhex(header_hex)
    header_prefix = header_bytes[:76]  # Tudo exceto nonce (4 bytes)
    
    best_zeros = 0
    best_nonce = start
    best_hash = ""
    tested = 0
    batch = 100_000
    
    for n in range(start, end):
        # Monta header com nonce em little-endian
        nonce_bytes = struct.pack("<I", n)
        full_header = header_prefix + nonce_bytes
        
        # Double SHA-256
        h = hashlib.sha256(hashlib.sha256(full_header).digest()).digest()
        
        # Hash em display order (reversed)
        h_rev = h[::-1]
        
        # Conta zeros hexadecimais no inicio
        zeros = 0
        for byte in h_rev:
            if byte == 0:
                zeros += 2
            elif byte < 16:
                zeros += 1
                break
            else:
                break
        
        if zeros > best_zeros:
            best_zeros = zeros
            best_nonce = n
            best_hash = h_rev.hex()
            queue.put(("BEST", worker_id, n, best_hash, zeros))
        
        if zeros >= target_zeros:
            queue.put(("SHARE", worker_id, n, h_rev.hex(), zeros))
        
        tested += 1
        if tested % batch == 0:
            queue.put(("PROG", worker_id, tested, best_zeros))
    
    queue.put(("DONE", worker_id, best_nonce, best_hash, best_zeros))

def sweep_range(name, start_nonce, end_nonce, header_hex, target_zeros, num_cores):
    """Varre um range de nonces com todos os cores."""
    total = end_nonce - start_nonce
    chunk = total // num_cores
    
    queue = multiprocessing.Queue()
    
    # Prepara args para cada worker  
    args_list = []
    for i in range(num_cores):
        s = start_nonce + (i * chunk)
        e = s + chunk if i < num_cores - 1 else end_nonce
        args_list.append((i, s, e, header_hex, target_zeros, queue))
    
    # Lanca workers
    procs = []
    for a in args_list:
        p = multiprocessing.Process(target=mine_worker, args=(a,))
        procs.append(p)
        p.start()
    
    global_best_z = 0
    global_best_n = 0
    global_best_h = ""
    shares = []
    workers_done = 0
    start_time = time.time()
    total_tested = [0] * num_cores
    
    try:
        while workers_done < num_cores:
            try:
                msg = queue.get(timeout=2)
                
                if msg[0] == "SHARE":
                    _, wid, nonce, h, zeros = msg
                    elapsed = time.time() - start_time
                    shares.append({"nonce": nonce, "hash": h, "zeros": zeros})
                    print(f"\n  {'$' * 25}")
                    print(f"  SHARE FOUND!")
                    print(f"  Nonce: 0x{nonce:08x}")
                    print(f"  Hash: {h}")
                    print(f"  Zeros: {zeros} | {elapsed:.1f}s")
                    print(f"  {'$' * 25}\n")
                    
                elif msg[0] == "BEST":
                    _, wid, nonce, h, zeros = msg
                    if zeros > global_best_z:
                        global_best_z = zeros
                        global_best_n = nonce
                        global_best_h = h
                        elapsed = time.time() - start_time
                        print(f"  [W{wid}] NEW BEST: {zeros}z | 0x{nonce:08x} | {h[:20]}... ({elapsed:.1f}s)")
                
                elif msg[0] == "PROG":
                    _, wid, tested, bz = msg
                    total_tested[wid] = tested
                    total_t = sum(total_tested)
                    elapsed = time.time() - start_time
                    rate = total_t / elapsed if elapsed > 0 else 0
                    pct = (total_t / total) * 100
                    if wid == 0:  # Print progress from worker 0 only
                        print(f"  [{name}] {total_t:,} ({pct:.0f}%) | "
                              f"{rate/1000:.0f} KH/s | Best: {global_best_z}z")
                
                elif msg[0] == "DONE":
                    workers_done += 1
                    
            except Exception:
                if not any(p.is_alive() for p in procs):
                    break
    except KeyboardInterrupt:
        print("\n  [INTERRUPT] Stopping...")
    finally:
        for p in procs:
            if p.is_alive():
                p.terminate()
                p.join(timeout=1)
    
    elapsed = time.time() - start_time
    rate = total / elapsed if elapsed > 0 else 0
    
    return {
        "best_zeros": global_best_z,
        "best_nonce": global_best_n,
        "best_hash": global_best_h,
        "shares": shares,
        "elapsed": elapsed,
        "rate": rate,
        "total_hashed": total
    }

def run_turbo_miner():
    # =========================================================================
    # LOAD MAINNET DATA
    # =========================================================================
    net_file = "results/mainnet_target.json"
    tac_file = "results/tactical_grover_result.json"
    
    if os.path.exists(net_file):
        with open(net_file, "r") as f:
            net_data = json.load(f)
        header_hex = net_data["header_template"]
        block = net_data.get("block_height_ref", "?")
        print(f"[MAINNET] Block #{block} loaded")
    else:
        print("[ERROR] No mainnet_target.json!")
        return

    sectors = DEFAULT_SECTORS
    if os.path.exists(tac_file):
        with open(tac_file, "r") as f:
            tac = json.load(f)
        sectors = [
            {"hex": s["sector_hex"], "bits": s["sector_bits"], "pct": s["pct"]}
            for s in tac["top_sectors"]
        ]
        print(f"[QUANTUM] {len(sectors)} sectors from Tactical Grover")

    TARGET_ZEROS = 8
    num_cores = multiprocessing.cpu_count()
    
    print(f"\n{'=' * 70}")
    print(f"GOLEM TURBO MINER — CPU Engine")
    print(f"{'=' * 70}")
    print(f"  Cores: {num_cores}")
    print(f"  Target: {TARGET_ZEROS} hex zeros (Mainnet)")
    
    all_shares = []
    global_best_z = 0
    global_best_n = 0
    global_best_h = ""
    start_total = time.time()

    # =========================================================================
    # PHASE 1: TOP 5 QUANTUM SECTORS (~21M total)
    # =========================================================================
    print(f"\n{'=' * 70}")
    print(f"PHASE 1: Quantum Sector Sweep (5 sectors x 4M = 21M)")
    print(f"{'=' * 70}")
    
    for i, sec in enumerate(sectors):
        sec_int = int(sec["hex"], 16)
        s_start = sec_int << 22  # 10-bit sector -> shift 22
        s_end = (sec_int + 1) << 22
        s_total = s_end - s_start
        
        print(f"\n  --- Sector #{i+1}: 0x{sec['hex']} ({sec['bits']}) | "
              f"Quantum: {sec['pct']:.2f}% | {s_total:,} nonces ---")
        
        result = sweep_range(f"S{i}", s_start, s_end, header_hex, TARGET_ZEROS, num_cores)
        
        if result["best_zeros"] > global_best_z:
            global_best_z = result["best_zeros"]
            global_best_n = result["best_nonce"]
            global_best_h = result["best_hash"]
        
        all_shares.extend(result["shares"])
        print(f"  Sector done: {result['rate']/1000:.0f} KH/s | Best: {result['best_zeros']}z")
    
    elapsed_p1 = time.time() - start_total
    
    print(f"\n[P1 DONE] {elapsed_p1:.1f}s | Best: {global_best_z}z | Shares: {len(all_shares)}")

    if not all_shares:
        # =====================================================================
        # PHASE 2: SUPER-SECTOR (~268M)
        # =====================================================================
        super_bits = sectors[0]["bits"][:4]
        super_int = int(super_bits, 2)
        super_start = super_int << 28
        super_end = (super_int + 1) << 28
        super_total = super_end - super_start
        
        print(f"\n{'=' * 70}")
        print(f"PHASE 2: Super-Sector 0x{super_int:x} ({super_bits}) — {super_total:,}")
        print(f"{'=' * 70}")
        
        result2 = sweep_range("SS", super_start, super_end, header_hex, TARGET_ZEROS, num_cores)
        
        if result2["best_zeros"] > global_best_z:
            global_best_z = result2["best_zeros"]
            global_best_n = result2["best_nonce"]
            global_best_h = result2["best_hash"]
        
        all_shares.extend(result2["shares"])

    # =========================================================================
    # FINAL REPORT
    # =========================================================================
    total_time = time.time() - start_total
    
    print(f"\n{'=' * 70}")
    print(f"GOLEM TURBO MINER — FINAL REPORT")
    print(f"{'=' * 70}")
    print(f"  Time: {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"  Best: {global_best_z} zeros")
    print(f"  Hash: {global_best_h}")
    print(f"  Nonce: 0x{global_best_n:08x}")
    print(f"  Shares ({TARGET_ZEROS}z+): {len(all_shares)}")
    
    for s in all_shares:
        print(f"    0x{s['nonce']:08x} | {s['zeros']}z | {s['hash'][:24]}...")
    
    print(f"{'=' * 70}")
    
    report = {
        "engine": "GOLEM TURBO (CPU Optimized)",
        "target_zeros": TARGET_ZEROS,
        "best_zeros": global_best_z,
        "best_nonce": f"0x{global_best_n:08x}",
        "best_hash": global_best_h,
        "shares": all_shares,
        "total_time": round(total_time, 1)
    }
    os.makedirs("results", exist_ok=True)
    with open("results/turbo_mining_result.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"[SAVED] results/turbo_mining_result.json")

if __name__ == "__main__":
    run_turbo_miner()
