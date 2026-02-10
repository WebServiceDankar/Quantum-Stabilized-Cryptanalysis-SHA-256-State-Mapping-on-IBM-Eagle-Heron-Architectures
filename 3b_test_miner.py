#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLEM TESTNET MINER - TESTE REDUZIDO (6 ZEROS)
Para validar o protocolo antes de tentar a dificuldade total (14 zeros)
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import hashlib
import json
import os
import time

# Carregar dados da Testnet
with open("results/network_target.json", "r") as f:
    network_data = json.load(f)

# Carregar nonce quântico
with open("results/sniper_result.json", "r") as f:
    sniper_data = json.load(f)

HEADER_TEMPLATE = network_data["header_template"]
QUANTUM_NONCE = sniper_data["nonce_decimal"]
SEARCH_RADIUS = 10_000_000  # Apenas 10M para teste rápido
TARGET_ZEROS = 6  # Reduzido para validação

print("=" * 70)
print("GOLEM TESTNET MINER - TESTE REDUZIDO")
print("=" * 70)
print(f"\nHeader Template: {HEADER_TEMPLATE[:32]}...{HEADER_TEMPLATE[-16:]}")
print(f"Quantum Center: {QUANTUM_NONCE} (0x{sniper_data['nonce_hex']})")
print(f"Search Range: +/- {SEARCH_RADIUS:,}")
print(f"Target: {TARGET_ZEROS} zeros\n")
print("-" * 70)

start_time = time.time()
best_zeros = 0
best_nonce = QUANTUM_NONCE
best_hash = ""

# Busca simples (single-thread para teste)
for n in range(QUANTUM_NONCE - SEARCH_RADIUS, QUANTUM_NONCE + SEARCH_RADIUS):
    # Monta header com nonce
    header_hex = HEADER_TEMPLATE[:-8] + f"{n:08x}"
    header_bytes = bytes.fromhex(header_hex)
    
    # Double SHA-256
    h = hashlib.sha256(hashlib.sha256(header_bytes).digest())
    h_hex = h.digest()[::-1].hex()
    
    # Conta zeros
    zeros = len(h_hex) - len(h_hex.lstrip('0'))
    
    if zeros > best_zeros:
        best_zeros = zeros
        best_nonce = n
        best_hash = h_hex
        print(f"[MELHOR] Nonce: {n:,} | Zeros: {zeros} | Hash: {h_hex[:32]}...")
    
    # Achou!
    if zeros >= TARGET_ZEROS:
        elapsed = time.time() - start_time
        print("\n" + "=" * 70)
        print("SUCESSO! BLOCO MINERADO (TESTNET SIMULADO)")
        print("=" * 70)
        print(f"Nonce: {n} (0x{n:08x})")
        print(f"Hash: {h_hex}")
        print(f"Zeros: {zeros}")
        print(f"Distancia do Quantum: {n - QUANTUM_NONCE:+,}")
        print(f"Tempo: {elapsed:.2f}s")
        print("=" * 70)
        
        # Salvar
        result = {
            "testnet_block": network_data["block_height_ref"],
            "quantum_nonce_center": QUANTUM_NONCE,
            "final_nonce": n,
            "final_hash": h_hex,
            "zeros_found": zeros,
            "distance_from_quantum": n - QUANTUM_NONCE,
            "time_seconds": elapsed
        }
        with open("results/testnet_test_result.json", "w") as f:
            json.dump(result, f, indent=2)
        
        break
    
    # Progress report
    if (n - (QUANTUM_NONCE - SEARCH_RADIUS)) % 500_000 == 0:
        tested = n - (QUANTUM_NONCE - SEARCH_RADIUS)
        print(f"[{tested:,} testados] Melhor: {best_zeros} zeros")

else:
    elapsed = time.time() - start_time
    print("\n" + "-" * 70)
    print("BUSCA COMPLETA - TARGET NAO ENCONTRADO")
    print("-" * 70)
    print(f"Melhor: {best_zeros} zeros")
    print(f"Nonce: {best_nonce} (0x{best_nonce:08x})")
    print(f"Hash: {best_hash}")
    print(f"Tempo: {elapsed:.2f}s")
    print("\nSUGESTAO: Aumente SEARCH_RADIUS ou reduza TARGET_ZEROS")
    print("-" * 70)
