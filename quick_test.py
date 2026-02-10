#!/usr/bin/env python3
"""
QUICK TESTNET VALIDATOR - Versao com logs em arquivo
"""
import hashlib
import json
import time

# Load data
with open("results/network_target.json") as f:
    net = json.load(f)
with open("results/sniper_result.json") as f:
    sniper = json.load(f)

header_template = net["header_template"]
center = sniper["nonce_decimal"]
radius = 5_000_000

log = []
log.append(f"[START] Testnet Miner Quick Test")
log.append(f"Quantum Center: {center}")
log.append(f"Radius: +/- {radius}")
log.append(f"Target: 6 zeros\n")

start_t = time.time()
best_z = 0
best_n = center
best_h = ""

for n in range(center - radius, center + radius):
    h_hex = header_template[:-8] + f"{n:08x}"
    h_bytes = bytes.fromhex(h_hex)
    h_result = hashlib.sha256(hashlib.sha256(h_bytes).digest()).digest()[::-1].hex()
    
    zeros = len(h_result) - len(h_result.lstrip('0'))
    
    if zeros > best_z:
        best_z = zeros
        best_n = n
        best_h = h_result
        log.append(f"[BETTER] Nonce={n}, Zeros={zeros}, Hash={h_result[:32]}...")
    
    if zeros >= 6:
        elapsed = time.time() - start_t
        log.append(f"\n[SUCCESS!!!]")
        log.append(f"Nonce: {n} (hex: {n:08x})")
        log.append(f"Hash: {h_result}")
        log.append(f"Zeros: {zeros}")
        log.append(f"Distance: {n - center:+}")
        log.append(f"Time: {elapsed:.2f}s")
        break
    
    if (n - (center - radius)) % 500_000 == 0:
        log.append(f"[Progress] {n - (center - radius):,} tested, best={best_z} zeros")

else:
    elapsed = time.time() - start_t
    log.append(f"\n[COMPLETE] No 6-zero found")
    log.append(f"Best: {best_z} zeros at nonce {best_n}")
    log.append(f"Time: {elapsed:.2f}s")

# Write log
with open("mining_log.txt", "w") as f:
    f.write("\n".join(log))

print("Log saved to: mining_log.txt")
for line in log:
    print(line)
