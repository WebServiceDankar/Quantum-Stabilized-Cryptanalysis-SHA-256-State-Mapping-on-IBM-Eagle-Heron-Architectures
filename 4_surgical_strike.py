#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
SURGICAL STRIKE MINER — Quantum Sector Attack
===============================================================================
Uses the quantum sector from Tactical Grover to perform a surgical CPU sweep.
Scans ONLY the quantum-identified nonce range (~4M hashes per sector).
Then expands to the Super-Sector if needed.
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

# --- QUANTUM INTELLIGENCE FROM TORINO ---
QUANTUM_SECTORS = [
    {"hex": "0a7", "bits": "0010100111", "pct": 0.39},
    {"hex": "0a4", "bits": "0010100100", "pct": 0.33},
    {"hex": "0b6", "bits": "0010110110", "pct": 0.32},
    {"hex": "067", "bits": "0001100111", "pct": 0.31},
    {"hex": "3be", "bits": "1110111110", "pct": 0.31},
]
SECTOR_WIDTH = 10
NONCE_WIDTH = 32

def worker(start_nonce, end_nonce, header_hex, target_zeros, queue, worker_id):
    """Hash sweep within a nonce range using real Mainnet header."""
    best_zeros = 0
    best_nonce = start_nonce
    best_hash = ""
    tested = 0
    
    for n in range(start_nonce, end_nonce):
        # Build proper Bitcoin block header with nonce in little-endian
        nonce_le = struct.pack("<I", n & 0xFFFFFFFF).hex()
        h_hex = header_hex[:-8] + nonce_le
        h_bytes = bytes.fromhex(h_hex)
        
        # Double SHA-256 (Bitcoin standard)
        h_result = hashlib.sha256(hashlib.sha256(h_bytes).digest()).digest()[::-1].hex()
        
        zeros = len(h_result) - len(h_result.lstrip('0'))
        
        if zeros > best_zeros:
            best_zeros = zeros
            best_nonce = n
            best_hash = h_result
            queue.put(("BETTER", n, h_result, zeros, worker_id))
        
        if zeros >= target_zeros:
            queue.put(("SHARE", n, h_result, zeros, worker_id))
        
        tested += 1
        if tested % 500_000 == 0:
            queue.put(("PROGRESS", tested, best_zeros, n, worker_id))
    
    queue.put(("DONE", best_nonce, best_hash, best_zeros, worker_id))

def run_surgical_strike():
    # =========================================================================
    # LOAD MAINNET DATA
    # =========================================================================
    net_file = "results/mainnet_target.json"
    tac_file = "results/tactical_grover_result.json"
    
    if os.path.exists(net_file):
        with open(net_file, "r") as f:
            net_data = json.load(f)
        header_hex = net_data["header_template"]
        block_height = net_data.get("block_height_ref", "?")
        print(f"[MAINNET] Block #{block_height} header loaded")
    else:
        print("[ERROR] No mainnet_target.json! Run Phase 0 first.")
        return
    
    # Load quantum sectors if available
    sectors = QUANTUM_SECTORS
    if os.path.exists(tac_file):
        with open(tac_file, "r") as f:
            tac_data = json.load(f)
        sectors = [
            {"hex": s["sector_hex"], "bits": s["sector_bits"], "pct": s["pct"]}
            for s in tac_data["top_sectors"]
        ]
        print(f"[QUANTUM] Loaded {len(sectors)} sectors from Tactical Grover")
    
    # =========================================================================
    # PHASE 1: SURGICAL STRIKE — Top quantum sector
    # =========================================================================
    target_sector = sectors[0]
    sector_int = int(target_sector["hex"], 16)
    start_range = sector_int << (NONCE_WIDTH - SECTOR_WIDTH)
    end_range = (sector_int + 1) << (NONCE_WIDTH - SECTOR_WIDTH)
    total_hashes = end_range - start_range
    
    TARGET_ZEROS = 8  # Mainnet-level share
    
    print(f"\n{'=' * 70}")
    print(f"SURGICAL STRIKE — Phase 1: Single Sector Attack")
    print(f"{'=' * 70}")
    print(f"  Quantum Sector: 0x{target_sector['hex']} ({target_sector['bits']})")
    print(f"  Quantum Confidence: {target_sector['pct']:.2f}%")
    print(f"  Range: {start_range:,} to {end_range:,}")
    print(f"  Volume: {total_hashes:,} hashes (tiny for CPU)")
    print(f"  Target: {TARGET_ZEROS} zeros (Mainnet share)")
    
    num_cores = multiprocessing.cpu_count()
    chunk = total_hashes // num_cores
    queue = multiprocessing.Queue()
    procs = []
    
    start_time = time.time()
    
    for i in range(num_cores):
        s = start_range + (i * chunk)
        e = s + chunk
        if i == num_cores - 1:
            e = end_range
        p = multiprocessing.Process(
            target=worker,
            args=(s, e, header_hex, TARGET_ZEROS, queue, i)
        )
        procs.append(p)
        p.start()
    
    shares = []
    global_best = 0
    global_best_hash = ""
    global_best_nonce = 0
    workers_done = 0
    
    try:
        while workers_done < num_cores:
            try:
                msg = queue.get(timeout=1)
                msg_type = msg[0]
                
                if msg_type == "SHARE":
                    _, nonce, h_val, zeros, wid = msg
                    elapsed = time.time() - start_time
                    shares.append({"nonce": nonce, "hash": h_val, "zeros": zeros})
                    print(f"\n  {'$' * 30}")
                    print(f"  TARGET HIT IN QUANTUM SECTOR!")
                    print(f"  Nonce: 0x{nonce:08x} ({nonce})")
                    print(f"  Hash: {h_val}")
                    print(f"  Zeros: {zeros}")
                    print(f"  Time: {elapsed:.2f}s")
                    print(f"  {'$' * 30}\n")
                    
                elif msg_type == "BETTER":
                    _, nonce, h_val, zeros, wid = msg
                    if zeros > global_best:
                        global_best = zeros
                        global_best_hash = h_val
                        global_best_nonce = nonce
                        elapsed = time.time() - start_time
                        print(f"  [W{wid}] NEW BEST: {zeros}z | 0x{nonce:08x} | "
                              f"{h_val[:16]}... ({elapsed:.1f}s)")
                    
                elif msg_type == "PROGRESS":
                    _, tested, best_z, _, wid = msg
                    elapsed = time.time() - start_time
                    rate = tested / elapsed if elapsed > 0 else 0
                    print(f"  [W{wid}] {tested:,} hashes | Best: {best_z}z | {rate:,.0f} H/s")
                    
                elif msg_type == "DONE":
                    workers_done += 1
                    
            except Exception:
                pass
    except KeyboardInterrupt:
        print("\n[INTERRUPTED]")
    finally:
        for p in procs:
            p.terminate()
            p.join()
    
    elapsed_p1 = time.time() - start_time
    rate = total_hashes / elapsed_p1 if elapsed_p1 > 0 else 0
    
    print(f"\n{'=' * 70}")
    print(f"SURGICAL STRIKE — Phase 1 Report")
    print(f"{'=' * 70}")
    print(f"  Sector: 0x{target_sector['hex']}")
    print(f"  Hashes: {total_hashes:,} in {elapsed_p1:.2f}s ({rate:,.0f} H/s)")
    print(f"  Best: {global_best} zeros")
    print(f"  Best Hash: {global_best_hash}")
    print(f"  Best Nonce: 0x{global_best_nonce:08x}")
    print(f"  Shares ({TARGET_ZEROS}z+): {len(shares)}")
    
    if not shares:
        print(f"\n  No {TARGET_ZEROS}-zero shares in sector 0x{target_sector['hex']}.")
        print(f"  Pattern '0010...' is strong. Expanding to SUPER-SECTOR...")
        
        # =================================================================
        # PHASE 2: SUPER-SECTOR (first 4 bits = 0010 = 0x2)
        # =================================================================
        super_sector = int(target_sector['bits'][:4], 2)  # 0010 = 2
        super_start = super_sector << 28  # 4-bit prefix << 28
        super_end = (super_sector + 1) << 28
        super_total = super_end - super_start
        
        print(f"\n{'=' * 70}")
        print(f"SURGICAL STRIKE — Phase 2: Super-Sector Attack")
        print(f"{'=' * 70}")
        print(f"  Super-Sector: 0x{super_sector:x} ({target_sector['bits'][:4]})")
        print(f"  Range: {super_start:,} to {super_end:,}")
        print(f"  Volume: {super_total:,} hashes (~268M)")
        print(f"  Estimated time: {super_total / rate:.0f}s at {rate:,.0f} H/s")
        
        # Reset
        queue2 = multiprocessing.Queue()
        procs2 = []
        chunk2 = super_total // num_cores
        start_time2 = time.time()
        workers_done2 = 0
        
        for i in range(num_cores):
            s = super_start + (i * chunk2)
            e = s + chunk2
            if i == num_cores - 1:
                e = super_end
            p = multiprocessing.Process(
                target=worker,
                args=(s, e, header_hex, TARGET_ZEROS, queue2, i)
            )
            procs2.append(p)
            p.start()
        
        try:
            while workers_done2 < num_cores:
                try:
                    msg = queue2.get(timeout=2)
                    msg_type = msg[0]
                    
                    if msg_type == "SHARE":
                        _, nonce, h_val, zeros, wid = msg
                        elapsed = time.time() - start_time2
                        shares.append({"nonce": nonce, "hash": h_val, "zeros": zeros})
                        print(f"\n  {'$' * 30}")
                        print(f"  SUPER-SECTOR SHARE FOUND!")
                        print(f"  Nonce: 0x{nonce:08x}")
                        print(f"  Hash: {h_val}")
                        print(f"  Zeros: {zeros} | Time: {elapsed:.1f}s")
                        print(f"  {'$' * 30}\n")
                        
                    elif msg_type == "BETTER":
                        _, nonce, h_val, zeros, wid = msg
                        if zeros > global_best:
                            global_best = zeros
                            global_best_hash = h_val
                            global_best_nonce = nonce
                            elapsed = time.time() - start_time2
                            print(f"  [W{wid}] NEW BEST: {zeros}z | 0x{nonce:08x} | "
                                  f"{h_val[:16]}... ({elapsed:.1f}s)")
                        
                    elif msg_type == "PROGRESS":
                        _, tested, best_z, _, wid = msg
                        elapsed = time.time() - start_time2
                        rate2 = tested / elapsed if elapsed > 0 else 0
                        pct_done = (tested * num_cores / super_total) * 100
                        print(f"  [W{wid}] {tested:,} | Best: {best_z}z | "
                              f"{rate2:,.0f} H/s | ~{pct_done:.0f}% done")
                        
                    elif msg_type == "DONE":
                        workers_done2 += 1
                        
                except Exception:
                    pass
        except KeyboardInterrupt:
            print("\n[INTERRUPTED]")
        finally:
            for p in procs2:
                p.terminate()
                p.join()
        
        elapsed_p2 = time.time() - start_time2
    
    # =========================================================================
    # FINAL REPORT
    # =========================================================================
    total_time = time.time() - start_time
    
    print(f"\n{'=' * 70}")
    print(f"SURGICAL STRIKE — FINAL REPORT")
    print(f"{'=' * 70}")
    print(f"  Total Time: {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"  Best Difficulty: {global_best} zeros")
    print(f"  Best Hash: {global_best_hash}")
    print(f"  Best Nonce: 0x{global_best_nonce:08x}")
    print(f"  Total Shares: {len(shares)}")
    
    if shares:
        print(f"\n  SHARES FOUND:")
        for s in shares:
            print(f"    Nonce: 0x{s['nonce']:08x} | {s['zeros']}z | {s['hash'][:24]}...")
    
    # Save
    result = {
        "operation": "SURGICAL_STRIKE",
        "block_height": block_height if 'block_height' in dir() else "?",
        "quantum_sector": target_sector,
        "best_zeros": global_best,
        "best_nonce": f"0x{global_best_nonce:08x}",
        "best_hash": global_best_hash,
        "shares": shares,
        "total_time": total_time
    }
    os.makedirs("results", exist_ok=True)
    with open("results/surgical_strike_result.json", "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n[SAVED] results/surgical_strike_result.json")
    print(f"{'=' * 70}")

if __name__ == "__main__":
    run_surgical_strike()
