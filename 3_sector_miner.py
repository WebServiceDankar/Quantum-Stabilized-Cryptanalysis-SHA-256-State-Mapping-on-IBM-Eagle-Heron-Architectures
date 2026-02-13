#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PHASE 3: SECTOR MINER — Quantum-Guided CPU Sweep
===============================================================================
Uses the Top 5 sectors from Tactical Grover (Phase 2d) to reduce search space.
Instead of 4 billion nonces, sweeps only ~20M (Top 5 sectors x 4M each).
===============================================================================
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import hashlib
import json
import time
import struct
import os
import multiprocessing

def worker_sector(sector_info, header_template, share_target, queue, worker_id):
    """Sweep a single sector for valid hashes."""
    start = sector_info["nonce_range_start"]
    end = sector_info["nonce_range_end"]
    sector_hex = sector_info["sector_hex"]
    best_zeros = 0
    best_nonce = start
    best_hash = ""
    tested = 0
    
    for n in range(start, end + 1):
        nonce_le = struct.pack("<I", n & 0xFFFFFFFF).hex()
        h_hex = header_template[:-8] + nonce_le
        h_bytes = bytes.fromhex(h_hex)
        h_result = hashlib.sha256(hashlib.sha256(h_bytes).digest()).digest()[::-1].hex()
        
        zeros = len(h_result) - len(h_result.lstrip('0'))
        
        if zeros > best_zeros:
            best_zeros = zeros
            best_nonce = n
            best_hash = h_result
            queue.put(("BETTER", n, h_result, zeros, worker_id, sector_hex))
        
        if zeros >= share_target:
            queue.put(("SHARE", n, h_result, zeros, worker_id, sector_hex))
        
        tested += 1
        if tested % 1_000_000 == 0:
            queue.put(("PROGRESS", tested, best_zeros, n, worker_id, sector_hex))
    
    queue.put(("DONE", best_nonce, best_hash, best_zeros, worker_id, sector_hex))

def run_sector_miner():
    # Load tactical grover results
    tac_file = "results/tactical_grover_result.json"
    net_file = "results/mainnet_target.json"
    
    if not os.path.exists(tac_file):
        print("[ERROR] No tactical_grover_result.json found. Run Phase 2d first.")
        return
    
    with open(tac_file, "r") as f:
        tac_data = json.load(f)
    
    if os.path.exists(net_file):
        with open(net_file, "r") as f:
            net_data = json.load(f)
        header_template = net_data["header_template"]
        network = net_data.get("network", "MAINNET")
        block_height = net_data.get("block_height_ref", "?")
    else:
        print("[ERROR] No mainnet_target.json found. Run Phase 0 first.")
        return
    
    top_sectors = tac_data["top_sectors"]
    share_target = 7  # Target: 7 zeros for a meaningful share
    
    print("=" * 70)
    print("PHASE 3: SECTOR MINER — Quantum-Guided CPU Sweep")
    print("=" * 70)
    print(f"\n[CONFIGURATION]")
    print(f"  Network: {network}")
    print(f"  Block: #{block_height}")
    print(f"  Share Target: {share_target} zeros")
    print(f"  Sectors to sweep: {len(top_sectors)}")
    
    total_nonces = 0
    for i, sec in enumerate(top_sectors):
        rng = sec["nonce_range_end"] - sec["nonce_range_start"] + 1
        total_nonces += rng
        print(f"  Sector #{i+1}: 0x{sec['sector_hex']} ({sec['sector_bits']}) | "
              f"Range: {sec['nonce_range_start']:,} - {sec['nonce_range_end']:,} | "
              f"{rng:,} nonces | Quantum: {sec['pct']:.2f}%")
    
    print(f"\n  TOTAL NONCES: {total_nonces:,} (vs {2**32:,} brute-force)")
    print(f"  REDUCTION: {2**32 // total_nonces:,}x faster!")
    
    # Launch workers — one per sector
    queue = multiprocessing.Queue()
    procs = []
    start_time = time.time()
    
    print(f"\n[LAUNCHING] {len(top_sectors)} sector workers...")
    for i, sec in enumerate(top_sectors):
        p = multiprocessing.Process(
            target=worker_sector,
            args=(sec, header_template, share_target, queue, i)
        )
        procs.append(p)
        p.start()
        print(f"  Worker {i}: Sector 0x{sec['sector_hex']} STARTED")
    
    print(f"\n{'=' * 70}")
    print(f"  Mining {len(top_sectors)} quantum sectors...")
    print(f"{'=' * 70}")
    
    found_shares = []
    global_best = 0
    global_best_hash = ""
    global_best_nonce = 0
    workers_done = 0
    
    try:
        while workers_done < len(top_sectors):
            try:
                msg = queue.get(timeout=2)
                msg_type = msg[0]
                
                if msg_type == "SHARE":
                    _, nonce, h_val, zeros, wid, sec_hex = msg
                    elapsed = time.time() - start_time
                    found_shares.append({
                        "nonce": nonce,
                        "nonce_hex": f"{nonce:08x}",
                        "hash": h_val,
                        "zeros": zeros,
                        "sector": sec_hex,
                        "time": elapsed
                    })
                    print(f"\n  [!!!] SHARE FOUND! Sector 0x{sec_hex}")
                    print(f"        Nonce: 0x{nonce:08x} | {zeros} zeros")
                    print(f"        Hash: {h_val}")
                    print(f"        Time: {elapsed:.1f}s")
                    
                elif msg_type == "BETTER":
                    _, nonce, h_val, zeros, wid, sec_hex = msg
                    if zeros > global_best:
                        global_best = zeros
                        global_best_hash = h_val
                        global_best_nonce = nonce
                        print(f"  [W{wid}|0x{sec_hex}] NEW BEST: {zeros} zeros | "
                              f"0x{nonce:08x} | {h_val[:20]}...")
                    
                elif msg_type == "PROGRESS":
                    _, tested, best_z, _, wid, sec_hex = msg
                    elapsed = time.time() - start_time
                    rate = tested / elapsed if elapsed > 0 else 0
                    print(f"  [W{wid}|0x{sec_hex}] {tested:,} tested | "
                          f"Best: {best_z}z | {rate:,.0f} H/s")
                    
                elif msg_type == "DONE":
                    workers_done += 1
                    _, nonce, h_val, zeros, wid, sec_hex = msg
                    print(f"  [W{wid}|0x{sec_hex}] COMPLETE | Best: {zeros} zeros")
                    
            except:
                pass
                
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Stopping workers...")
    
    finally:
        for p in procs:
            p.terminate()
            p.join()
        
        elapsed = time.time() - start_time
        
        print("\n" + "=" * 70)
        print(f"SECTOR MINER FINAL REPORT")
        print("=" * 70)
        print(f"  Total Time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
        print(f"  Sectors Swept: {len(top_sectors)}")
        print(f"  Nonces Tested: ~{total_nonces:,}")
        print(f"  Shares Found: {len(found_shares)}")
        print(f"  Best Difficulty: {global_best} zeros")
        print(f"  Best Hash: {global_best_hash}")
        print(f"  Best Nonce: 0x{global_best_nonce:08x}")
        
        if found_shares:
            print(f"\n  [SHARES]:")
            for s in found_shares:
                print(f"    0x{s['nonce_hex']} | {s['zeros']}z | Sector 0x{s['sector']}")
        
        # Save results
        result = {
            "network": network,
            "block_height": block_height,
            "share_target": share_target,
            "sectors_swept": len(top_sectors),
            "total_nonces": total_nonces,
            "shares_found": found_shares,
            "best_zeros": global_best,
            "best_nonce": f"{global_best_nonce:08x}",
            "best_hash": global_best_hash,
            "total_time": elapsed
        }
        
        with open("results/sector_mining_result.json", "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n[SAVED] results/sector_mining_result.json")
        print("=" * 70)

if __name__ == "__main__":
    run_sector_miner()
