#!/usr/bin/env python3
"""
GOLEM MAINNET QUICK TEST - Log em arquivo para monitoramento
Busca shares (8 zeros) no header REAL da Bitcoin Mainnet.
"""
import hashlib
import json
import time
import struct

# Carrega dados
with open("results/mainnet_target.json") as f:
    net = json.load(f)
with open("results/sniper_result.json") as f:
    sniper = json.load(f)

header_template = net["header_template"]
center = sniper["nonce_decimal"]
radius = 50_000_000  # 50M para teste

log = []
log.append(f"[START] MAINNET Mining Quick Test")
log.append(f"Network: {net['network']}")
log.append(f"Block: #{net['block_height_ref']}")
log.append(f"Quantum Center: {center} (0x{sniper['nonce_hex']})")
log.append(f"Radius: +/- {radius:,}")
log.append(f"Target: 8 zeros (Share)\n")

start_t = time.time()
best_z = 0
best_n = center
best_h = ""

for n in range(center - radius, center + radius):
    # Nonce em Little Endian
    nonce_le = struct.pack("<I", n & 0xFFFFFFFF).hex()
    h_hex = header_template[:-8] + nonce_le
    h_bytes = bytes.fromhex(h_hex)
    h_result = hashlib.sha256(hashlib.sha256(h_bytes).digest()).digest()[::-1].hex()
    
    zeros = len(h_result) - len(h_result.lstrip('0'))
    
    if zeros > best_z:
        best_z = zeros
        best_n = n
        best_h = h_result
        log.append(f"[BETTER] Nonce={n} (0x{n:08x}), Zeros={zeros}, Hash={h_result[:32]}...")
    
    if zeros >= 8:
        elapsed = time.time() - start_t
        log.append(f"\n[SHARE FOUND!!!]")
        log.append(f"Nonce: {n} (0x{n:08x})")
        log.append(f"Hash: {h_result}")
        log.append(f"Zeros: {zeros}")
        log.append(f"Distance: {n - center:+,}")
        log.append(f"Time: {elapsed:.2f}s")
        # Nao para, continua buscando mais shares!
    
    if (n - (center - radius)) % 2_000_000 == 0:
        elapsed = time.time() - start_t
        rate = (n - (center - radius)) / elapsed if elapsed > 0 else 0
        log.append(f"[Progress] {n - (center - radius):,} tested | best={best_z} zeros | {rate:,.0f} H/s")

elapsed = time.time() - start_t
log.append(f"\n[COMPLETE] Total Time: {elapsed:.2f}s")
log.append(f"Best: {best_z} zeros at nonce {best_n} (0x{best_n:08x})")
log.append(f"Hash: {best_h}")

# Write log
with open("mainnet_mining_log.txt", "w") as f:
    f.write("\n".join(log))

print("Log saved to: mainnet_mining_log.txt")
for line in log[-20:]:
    print(line)
