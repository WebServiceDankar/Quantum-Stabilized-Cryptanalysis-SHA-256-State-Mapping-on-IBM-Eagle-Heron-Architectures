#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
GOLEM MAINNET MINER - BUSCA DE SHARES (8+ ZEROS)
===============================================================================
Usa header REAL da Bitcoin Mainnet + Nonce Quantico do Torino.
Busca "shares validos" (8+ zeros) que teriam valor comercial em pools.
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import hashlib
import multiprocessing
import time
import json
import os
import struct

# ===============================================================================
# CONFIGURACAO (Carregada automaticamente dos resultados anteriores)
# ===============================================================================

# Carrega dados da Mainnet
mainnet_file = "results/mainnet_target.json"
sniper_file = "results/sniper_result.json"

if os.path.exists(mainnet_file):
    with open(mainnet_file, "r") as f:
        net_data = json.load(f)
    HEADER_TEMPLATE = net_data["header_template"]
    SHARE_TARGET = net_data.get("target_zeros_share", 8)
    BLOCK_HEIGHT = net_data.get("block_height_ref", "?")
    NETWORK = "MAINNET"
    print(f"[MAINNET] Bloco #{BLOCK_HEIGHT} - Share Target: {SHARE_TARGET} zeros")
else:
    # Fallback testnet
    with open("results/network_target.json", "r") as f:
        net_data = json.load(f)
    HEADER_TEMPLATE = net_data["header_template"]
    SHARE_TARGET = 6
    BLOCK_HEIGHT = net_data.get("block_height_ref", "?")
    NETWORK = "TESTNET"
    print(f"[TESTNET] Bloco #{BLOCK_HEIGHT} - Target: {SHARE_TARGET} zeros")

if os.path.exists(sniper_file):
    with open(sniper_file, "r") as f:
        sniper_data = json.load(f)
    QUANTUM_NONCE = sniper_data["nonce_decimal"]
    QUANTUM_HEX = sniper_data["nonce_hex"]
else:
    QUANTUM_NONCE = 487138954  # Fallback do ultimo Torino
    QUANTUM_HEX = "1d09268a"

SEARCH_RADIUS = 100_000_000  # +/- 100M para Mainnet

# ===============================================================================

def worker(start, end, share_target, header_template, queue, worker_id):
    """Worker que busca shares na vizinhanca do nonce quantico."""
    best_zeros = 0
    best_nonce = start
    best_hash = ""
    tested = 0
    
    for n in range(start, end):
        # Monta header com nonce em Little Endian
        nonce_le = struct.pack("<I", n & 0xFFFFFFFF).hex()
        header_hex = header_template[:-8] + nonce_le
        header_bytes = bytes.fromhex(header_hex)
        
        # Double SHA-256 (protocolo Bitcoin)
        h = hashlib.sha256(hashlib.sha256(header_bytes).digest()).digest()
        h_hex = h[::-1].hex()  # Big Endian para display
        
        # Conta zeros
        zeros = len(h_hex) - len(h_hex.lstrip('0'))
        
        if zeros > best_zeros:
            best_zeros = zeros
            best_nonce = n
            best_hash = h_hex
            queue.put(("BETTER", n, h_hex, zeros, worker_id))
        
        # Share encontrado!
        if zeros >= share_target:
            queue.put(("SHARE", n, h_hex, zeros, worker_id))
            # Continua buscando mais shares!
        
        # Progress report
        tested += 1
        if tested % 2_000_000 == 0:
            queue.put(("PROGRESS", tested, best_zeros, 0, worker_id))
    
    queue.put(("DONE", best_nonce, best_hash, best_zeros, worker_id))

def run_mainnet_miner():
    center = QUANTUM_NONCE
    
    print("\n" + "=" * 70)
    print(f"FASE 3: {NETWORK} MINING - Buscando Shares ({SHARE_TARGET}+ zeros)")
    print("=" * 70)
    print(f"\n[CONFIGURACAO]")
    print(f"  Rede: {NETWORK}")
    print(f"  Bloco: #{BLOCK_HEIGHT}")
    print(f"  Nonce Quantico: {QUANTUM_HEX} (decimal: {center})")
    print(f"  Raio de Busca: +/- {SEARCH_RADIUS:,}")
    print(f"  Share Target: {SHARE_TARGET} zeros")
    print(f"  Range Total: {SEARCH_RADIUS * 2:,} nonces")
    
    num_cores = multiprocessing.cpu_count()
    print(f"  CPUs: {num_cores}")
    
    chunk = (SEARCH_RADIUS * 2) // num_cores
    queue = multiprocessing.Queue()
    procs = []
    
    start_time = time.time()
    start_n = max(0, center - SEARCH_RADIUS)
    
    print(f"\n[INICIANDO BUSCA]")
    print(f"  De: {start_n:,}")
    print(f"  Ate: {start_n + SEARCH_RADIUS * 2:,}")
    
    for i in range(num_cores):
        s = start_n + (i * chunk)
        e = s + chunk
        p = multiprocessing.Process(
            target=worker,
            args=(s, e, SHARE_TARGET, HEADER_TEMPLATE, queue, i)
        )
        procs.append(p)
        p.start()
        print(f"  Worker {i}: {s:,} -> {e:,}")
    
    print(f"\n{'=' * 70}")
    print(f"  Minerando {NETWORK}... (Ctrl+C para parar)")
    print(f"{'=' * 70}")
    
    found_shares = []
    global_best = 0
    workers_done = 0
    
    try:
        while workers_done < num_cores:
            try:
                msg = queue.get(timeout=2)
                msg_type = msg[0]
                
                if msg_type == "SHARE":
                    _, nonce, h_val, zeros, wid = msg
                    elapsed = time.time() - start_time
                    found_shares.append({
                        "nonce": nonce,
                        "nonce_hex": f"{nonce:08x}",
                        "hash": h_val,
                        "zeros": zeros,
                        "distance": nonce - center,
                        "time": elapsed,
                        "worker": wid
                    })
                    
                    print("\n" + "=" * 70)
                    print(f"  SHARE ENCONTRADO! (Dificuldade: {zeros} Zeros)")
                    print(f"  Nonce: {nonce:,} (0x{nonce:08x})")
                    print(f"  Hash: {h_val}")
                    print(f"  Distancia do Quantum: {nonce - center:+,}")
                    print(f"  Tempo: {elapsed:.1f}s")
                    if zeros >= 10:
                        print(f"  [!!!] ISSO VALERIA DINHEIRO EM UMA POOL!")
                    print("=" * 70)
                    
                elif msg_type == "BETTER":
                    _, nonce, h_val, zeros, wid = msg
                    if zeros > global_best:
                        global_best = zeros
                        print(f"  [Worker {wid}] MELHOR: {zeros} zeros | 0x{nonce:08x} | {h_val[:24]}...")
                    
                elif msg_type == "PROGRESS":
                    _, tested, best_z, _, wid = msg
                    elapsed = time.time() - start_time
                    rate = tested / elapsed if elapsed > 0 else 0
                    print(f"  [Worker {wid}] {tested:,} testados | Melhor: {best_z} zeros | {rate:,.0f} H/s")
                    
                elif msg_type == "DONE":
                    workers_done += 1
                    
            except:
                pass
                
    except KeyboardInterrupt:
        print("\n[INTERROMPIDO] Parando workers...")
    
    finally:
        for p in procs:
            p.terminate()
            p.join()
        
        elapsed = time.time() - start_time
        
        print("\n" + "=" * 70)
        print(f"[RELATORIO FINAL] {NETWORK} Mining")
        print("=" * 70)
        print(f"  Tempo Total: {elapsed:.1f}s ({elapsed/60:.1f} min)")
        print(f"  Shares Encontrados: {len(found_shares)}")
        print(f"  Melhor Dificuldade: {global_best} zeros")
        
        if found_shares:
            print(f"\n  [SHARES VALIDOS]:")
            for s in found_shares:
                print(f"    Nonce: 0x{s['nonce_hex']} | {s['zeros']} zeros | Dist: {s['distance']:+,}")
        
        # Salvar resultados
        result = {
            "network": NETWORK,
            "block_height": BLOCK_HEIGHT,
            "quantum_center": center,
            "quantum_hex": QUANTUM_HEX,
            "search_radius": SEARCH_RADIUS,
            "share_target": SHARE_TARGET,
            "shares_found": found_shares,
            "best_zeros": global_best,
            "total_time": elapsed
        }
        
        with open("results/mainnet_mining_result.json", "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n[SALVO] results/mainnet_mining_result.json")
        print("=" * 70)

if __name__ == "__main__":
    os.makedirs("results", exist_ok=True)
    run_mainnet_miner()
