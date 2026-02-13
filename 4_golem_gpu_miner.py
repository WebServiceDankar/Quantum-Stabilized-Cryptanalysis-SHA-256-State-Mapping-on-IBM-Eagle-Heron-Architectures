#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
GOLEM GPU ENGINE v2 — CUDA SHA-256 Miner (CuPy + nvrtc fix)
  Hardware: NVIDIA GeForce GTX 750 (Maxwell, Compute 5.0)
===============================================================================
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ============================================================================
# FIX: Add NVIDIA nvrtc DLLs to system PATH before importing CuPy
# ============================================================================
import os
import site

site_packages = site.getusersitepackages()
nvrtc_path = os.path.join(site_packages, "nvidia", "cuda_nvrtc", "bin")
cuda_runtime_path = os.path.join(site_packages, "nvidia", "cuda_runtime", "bin")

# Also check torch path
torch_lib = os.path.join(site_packages, "torch", "lib")

for p in [nvrtc_path, cuda_runtime_path, torch_lib]:
    if os.path.isdir(p):
        os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")
        print(f"[PATH] Added: {p}")

# Now import CuPy
import cupy as cp
import numpy as np
import struct
import hashlib
import time
import json

# =============================================================================
# CUDA KERNEL: SHA-256 Double Hash Engine
# =============================================================================
SHA256_KERNEL = r"""
extern "C" {

__device__ __forceinline__ unsigned int ror32(unsigned int x, unsigned int n) {
    return (x >> n) | (x << (32 - n));
}

__device__ void sha256_transform(unsigned int state[8], const unsigned int data[16]) {
    const unsigned int k[64] = {
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
    };

    unsigned int w[64];
    for (int i = 0; i < 16; i++) w[i] = data[i];
    for (int i = 16; i < 64; i++) {
        unsigned int s0 = ror32(w[i-15], 7) ^ ror32(w[i-15], 18) ^ (w[i-15] >> 3);
        unsigned int s1 = ror32(w[i-2], 17) ^ ror32(w[i-2], 19) ^ (w[i-2] >> 10);
        w[i] = w[i-16] + s0 + w[i-7] + s1;
    }

    unsigned int s[8];
    for (int i = 0; i < 8; i++) s[i] = state[i];

    for (int i = 0; i < 64; i++) {
        unsigned int S1 = ror32(s[4], 6) ^ ror32(s[4], 11) ^ ror32(s[4], 25);
        unsigned int ch = (s[4] & s[5]) ^ (~s[4] & s[6]);
        unsigned int t1 = s[7] + S1 + ch + k[i] + w[i];
        unsigned int S0 = ror32(s[0], 2) ^ ror32(s[0], 13) ^ ror32(s[0], 22);
        unsigned int maj = (s[0] & s[1]) ^ (s[0] & s[2]) ^ (s[1] & s[2]);
        unsigned int t2 = S0 + maj;

        s[7] = s[6]; s[6] = s[5]; s[5] = s[4]; s[4] = s[3] + t1;
        s[3] = s[2]; s[2] = s[1]; s[1] = s[0]; s[0] = t1 + t2;
    }

    for (int i = 0; i < 8; i++) state[i] += s[i];
}

// Each thread hashes one nonce, writes leading-zero count to output
__global__ void mine_batch(
    const unsigned int* header20,  // 20 uint32 words (80 bytes)
    unsigned int nonce_start,
    unsigned int* out_best_nonce,
    unsigned int* out_best_zeros,
    unsigned int target_zeros
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    unsigned int nonce = nonce_start + (unsigned int)idx;

    // === FIRST SHA-256: hash 80-byte block header ===
    // Block 1: words 0..15
    unsigned int block1[16];
    for (int i = 0; i < 16; i++) block1[i] = header20[i];

    unsigned int state1[8] = {
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    };
    sha256_transform(state1, block1);

    // Block 2: words 16..19 + nonce + padding
    unsigned int block2[16];
    for (int i = 0; i < 16; i++) block2[i] = 0;
    block2[0] = header20[16];
    block2[1] = header20[17];
    block2[2] = header20[18];
    // Word 19 is the nonce (already little-endian in Bitcoin)
    block2[3] = nonce;
    block2[4] = 0x80000000u;  // padding start
    block2[15] = 640;  // length in bits (80 * 8)
    sha256_transform(state1, block2);

    // === SECOND SHA-256: hash of hash (32 bytes) ===
    unsigned int hash_in[16];
    for (int i = 0; i < 16; i++) hash_in[i] = 0;
    for (int i = 0; i < 8; i++) hash_in[i] = state1[i];
    hash_in[8] = 0x80000000u;
    hash_in[15] = 256;  // 32 * 8

    unsigned int state2[8] = {
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    };
    sha256_transform(state2, hash_in);

    // === Count leading zeros of the final hash ===
    // Bitcoin hash is displayed in reverse byte order.
    // state2[7] reversed = first 4 bytes of display hash
    // We byte-swap to get big-endian display order
    unsigned int first4 = 
        ((state2[7] & 0xFF) << 24) |
        (((state2[7] >> 8) & 0xFF) << 16) |
        (((state2[7] >> 16) & 0xFF) << 8) |
        ((state2[7] >> 24) & 0xFF);
    
    unsigned int hex_zeros = 0;
    if (first4 == 0) {
        hex_zeros = 8;
        unsigned int next4 = 
            ((state2[6] & 0xFF) << 24) |
            (((state2[6] >> 8) & 0xFF) << 16) |
            (((state2[6] >> 16) & 0xFF) << 8) |
            ((state2[6] >> 24) & 0xFF);
        if (next4 == 0) {
            hex_zeros = 16;
        } else {
            unsigned int bits = __clz(next4);
            hex_zeros += bits / 4;
        }
    } else {
        unsigned int bits = __clz(first4);
        hex_zeros = bits / 4;
    }

    // Update global best via atomics
    if (hex_zeros >= target_zeros) {
        atomicMax(out_best_zeros, hex_zeros);
        atomicExch(out_best_nonce, nonce);
    }
    // Also track any improvement
    unsigned int old = atomicMax(out_best_zeros, hex_zeros);
    if (hex_zeros > old) {
        atomicExch(out_best_nonce, nonce);
    }
}

}  // extern "C"
"""

def verify_nonce_cpu(header_hex, nonce):
    """CPU verification of a nonce using Python hashlib."""
    nonce_le = struct.pack("<I", nonce & 0xFFFFFFFF).hex()
    h_hex = header_hex[:-8] + nonce_le
    h_bytes = bytes.fromhex(h_hex)
    result = hashlib.sha256(hashlib.sha256(h_bytes).digest()).digest()[::-1].hex()
    zeros = len(result) - len(result.lstrip('0'))
    return result, zeros

def parse_header_words(header_hex):
    """Parse 80-byte hex header into 20 big-endian uint32 words."""
    hdr = bytes.fromhex(header_hex)
    words = []
    for i in range(0, 80, 4):
        w = struct.unpack(">I", hdr[i:i+4])[0]
        words.append(w)
    return words

def run_gpu_miner():
    # =========================================================================
    # LOAD DATA
    # =========================================================================
    net_file = "results/mainnet_target.json"
    tac_file = "results/tactical_grover_result.json"
    
    if os.path.exists(net_file):
        with open(net_file, "r") as f:
            net_data = json.load(f)
        header_hex = net_data["header_template"]
        block_height = net_data.get("block_height_ref", "?")
    else:
        print("[ERROR] No mainnet_target.json!")
        return

    # Quantum sectors
    if os.path.exists(tac_file):
        with open(tac_file, "r") as f:
            tac = json.load(f)
        top = tac["top_sectors"][0]
        sector_start = top["nonce_range_start"]
        sector_end = top["nonce_range_end"]
        sector_hex = top["sector_hex"]
        sector_bits = top["sector_bits"]
    else:
        sector_hex = "0a7"
        sector_bits = "0010100111"
        sector_start = 0x29C00000
        sector_end = 0x2A000000

    TARGET_ZEROS = 8

    print("=" * 70)
    print("GOLEM GPU ENGINE v2 — CUDA SHA-256 Miner")
    print("=" * 70)

    # GPU info
    dev = cp.cuda.Device(0)
    free_mem, total_mem = cp.cuda.runtime.memGetInfo()
    print(f"\n[GPU] Device 0")
    print(f"[VRAM] {free_mem/1e6:.0f} MB free / {total_mem/1e6:.0f} MB total")
    print(f"[CUDA] Runtime {cp.cuda.runtime.runtimeGetVersion()}")
    print(f"[Block] #{block_height}")

    # =========================================================================
    # COMPILE KERNEL
    # =========================================================================
    print(f"\n[COMPILING] CUDA SHA-256 kernel...")
    t0 = time.time()
    try:
        module = cp.RawModule(code=SHA256_KERNEL, options=('--gpu-architecture=sm_50',))
        kernel = module.get_function("mine_batch")
        print(f"[OK] Kernel compiled in {time.time()-t0:.1f}s")
    except Exception as e:
        print(f"[ERROR] Kernel compilation failed: {e}")
        return

    # =========================================================================
    # PREPARE DATA
    # =========================================================================
    header_words = parse_header_words(header_hex)
    d_header = cp.array(header_words, dtype=cp.uint32)
    
    # GTX 750: 512 CUDA cores, Maxwell
    BLOCK_SIZE = 256
    GRID_SIZE = 2048
    BATCH_SIZE = BLOCK_SIZE * GRID_SIZE  # 524,288 per launch

    d_best_nonce = cp.zeros(1, dtype=cp.uint32)
    d_best_zeros = cp.zeros(1, dtype=cp.uint32)
    
    # =========================================================================
    # PHASE 1: QUANTUM SECTOR (~4M)
    # =========================================================================
    sector_total = sector_end - sector_start
    print(f"\n{'=' * 70}")
    print(f"PHASE 1: Quantum Sector 0x{sector_hex} ({sector_bits})")
    print(f"{'=' * 70}")
    print(f"  Range: {sector_start:,} to {sector_end:,}")
    print(f"  Volume: {sector_total:,}")
    print(f"  Batch: {BATCH_SIZE:,} per kernel launch")
    
    start_time = time.time()
    total = 0
    best_z_seen = 0
    
    for offset in range(0, sector_total, BATCH_SIZE):
        nonce_start = cp.uint32(sector_start + offset)
        d_best_nonce[:] = 0
        
        kernel(
            (GRID_SIZE,), (BLOCK_SIZE,),
            (d_header, nonce_start, d_best_nonce, d_best_zeros, cp.uint32(TARGET_ZEROS))
        )
        cp.cuda.stream.get_current_stream().synchronize()
        
        total += min(BATCH_SIZE, sector_total - offset)
        cur_z = int(d_best_zeros.get()[0])
        cur_n = int(d_best_nonce.get()[0])
        
        if cur_z > best_z_seen:
            best_z_seen = cur_z
            h, hz = verify_nonce_cpu(header_hex, cur_n)
            elapsed = time.time() - start_time
            print(f"  NEW BEST: {hz}z (GPU:{cur_z}z) | 0x{cur_n:08x} | {h[:20]}... ({elapsed:.1f}s)")
        
        if cur_z >= TARGET_ZEROS:
            h, hz = verify_nonce_cpu(header_hex, cur_n)
            print(f"\n  {'$' * 30}")
            print(f"  SHARE FOUND!")
            print(f"  Nonce: 0x{cur_n:08x} | Hash: {h}")
            print(f"  {'$' * 30}")
    
    elapsed_p1 = time.time() - start_time
    rate_p1 = total / elapsed_p1 if elapsed_p1 > 0 else 0
    
    print(f"\n[P1 DONE] {total:,} hashes in {elapsed_p1:.2f}s = {rate_p1/1e6:.2f} MH/s")
    
    # =========================================================================
    # PHASE 2: SUPER-SECTOR (~268M)
    # =========================================================================
    super_prefix = int(sector_bits[:4], 2)
    super_start = super_prefix << 28
    super_end = (super_prefix + 1) << 28
    super_total = super_end - super_start
    
    print(f"\n{'=' * 70}")
    print(f"PHASE 2: Super-Sector 0x{super_prefix:x} ({sector_bits[:4]})")
    print(f"{'=' * 70}")
    eta = super_total / rate_p1 if rate_p1 > 0 else 999
    print(f"  Volume: {super_total:,} (~268M)")
    print(f"  ETA: {eta:.0f}s ({eta/60:.1f} min) at {rate_p1/1e6:.2f} MH/s")
    
    start_time2 = time.time()
    total2 = 0
    d_best_zeros[:] = 0
    best_z_seen = 0
    shares = []
    
    for offset in range(0, super_total, BATCH_SIZE):
        nonce_start = cp.uint32(super_start + offset)
        d_best_nonce[:] = 0
        
        kernel(
            (GRID_SIZE,), (BLOCK_SIZE,),
            (d_header, nonce_start, d_best_nonce, d_best_zeros, cp.uint32(TARGET_ZEROS))
        )
        cp.cuda.stream.get_current_stream().synchronize()
        
        total2 += min(BATCH_SIZE, super_total - offset)
        cur_z = int(d_best_zeros.get()[0])
        cur_n = int(d_best_nonce.get()[0])
        
        if cur_z > best_z_seen:
            best_z_seen = cur_z
            h, hz = verify_nonce_cpu(header_hex, cur_n)
            elapsed = time.time() - start_time2
            print(f"  NEW BEST: {hz}z (GPU:{cur_z}z) | 0x{cur_n:08x} | {h[:20]}... ({elapsed:.1f}s)")
        
        if cur_z >= TARGET_ZEROS:
            h, hz = verify_nonce_cpu(header_hex, cur_n)
            shares.append({"nonce": cur_n, "hash": h, "zeros": hz})
            print(f"\n  {'$' * 30}")
            print(f"  GPU SHARE FOUND!")
            print(f"  Nonce: 0x{cur_n:08x} | Hash: {h} | {hz}z")
            print(f"  {'$' * 30}")
        
        if total2 % (BATCH_SIZE * 128) == 0 and total2 > 0:
            elapsed = time.time() - start_time2
            rate = total2 / elapsed
            pct = (total2 / super_total) * 100
            print(f"  {total2:,} | {rate/1e6:.2f} MH/s | Best: {best_z_seen}z | {pct:.0f}%")
    
    elapsed_p2 = time.time() - start_time2
    rate_p2 = total2 / elapsed_p2 if elapsed_p2 > 0 else 0
    
    # =========================================================================
    # FINAL REPORT
    # =========================================================================
    total_time = time.time() - start_time
    best_z = int(d_best_zeros.get()[0])
    best_n = int(d_best_nonce.get()[0])
    best_hash, best_z_cpu = verify_nonce_cpu(header_hex, best_n) if best_n else ("N/A", 0)
    
    print(f"\n{'=' * 70}")
    print(f"GOLEM GPU ENGINE — FINAL REPORT")
    print(f"{'=' * 70}")
    print(f"  Total Time: {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"  GPU Rate: {max(rate_p1, rate_p2)/1e6:.2f} MH/s")
    print(f"  CPU Equivalent: ~{150_000} H/s")
    print(f"  SPEEDUP: {max(rate_p1, rate_p2)/150_000:.0f}x FASTER!")
    print(f"  Best: {best_z_cpu} zeros")
    print(f"  Best Hash: {best_hash}")
    print(f"  Best Nonce: 0x{best_n:08x}")
    print(f"  Shares: {len(shares)}")
    print(f"{'=' * 70}")
    
    result = {
        "engine": "GOLEM GPU v2 (CuPy CUDA)",
        "best_zeros": best_z_cpu,
        "best_nonce": f"0x{best_n:08x}",
        "best_hash": best_hash,
        "gpu_rate_mhs": round(max(rate_p1, rate_p2)/1e6, 2),
        "speedup_vs_cpu": round(max(rate_p1, rate_p2)/150_000, 0),
        "shares": shares,
        "total_time": round(total_time, 1)
    }
    os.makedirs("results", exist_ok=True)
    with open("results/gpu_mining_result.json", "w") as f:
        json.dump(result, f, indent=2)
    print(f"[SAVED] results/gpu_mining_result.json")

if __name__ == "__main__":
    run_gpu_miner()
