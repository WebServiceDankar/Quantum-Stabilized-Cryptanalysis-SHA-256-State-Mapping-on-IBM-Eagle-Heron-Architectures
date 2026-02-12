#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
GOLEM MAINNET PROTOCOL - PASSO 0: INTELIGENCIA (ZONA DE GUERRA)
===============================================================================
Coleta dados REAIS da Bitcoin MAINNET para alimentar o pipeline quantico.
Alvo: Shares validos (8-10 zeros) para prova de utilidade comercial.
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import struct
import time
import json
import hashlib
import os

def get_mainnet_work():
    print("=" * 70)
    print("[PASSO 0] INTELIGENCIA MAINNET - Bitcoin Real Time")
    print("=" * 70)
    
    try:
        # 1. Pega o hash do ultimo bloco minerado na rede principal
        print("\n[1/5] Consultando ultimo bloco minerado (MAINNET)...")
        
        # Tenta blockchain.info primeiro, fallback para mempool.space
        try:
            last_block_req = requests.get("https://blockchain.info/q/latesthash", timeout=10)
            prev_hash = last_block_req.text.strip()
            
            # Pega detalhes do bloco
            print("[2/5] Obtendo parametros de dificuldade...")
            block_details = requests.get(
                f"https://blockchain.info/rawblock/{prev_hash}", timeout=15
            ).json()
            
            bits = block_details['bits']
            merkle_root_hex = block_details['mrkl_root']
            block_height = block_details['height']
            
        except Exception as e1:
            print(f"    [WARN] blockchain.info falhou ({e1}), tentando mempool.space...")
            
            # Fallback: mempool.space
            tip_hash = requests.get("https://mempool.space/api/blocks/tip/hash", timeout=10).text.strip()
            prev_hash = tip_hash
            
            block_details = requests.get(
                f"https://mempool.space/api/block/{tip_hash}", timeout=15
            ).json()
            
            bits = block_details['bits']
            merkle_root_hex = block_details['merkle_root']
            block_height = block_details['height']
        
        print(f"    [OK] Ultimo Bloco: #{block_height}")
        print(f"    [OK] Hash: {prev_hash[:16]}...{prev_hash[-16:]}")
        
        # 3. Montando o Cabecalho
        version = 0x20000000  # BIP 9
        prev_hash_hex = prev_hash
        timestamp = int(time.time())
        
        print(f"\n[3/5] Parametros da Rede:")
        print(f"    [OK] Version:      0x{version:08x}")
        print(f"    [OK] Bits (Diff):  {bits} (0x{bits:08x})")
        print(f"    [OK] Merkle Root:  {merkle_root_hex[:16]}...{merkle_root_hex[-16:]}")
        print(f"    [OK] Timestamp:    {timestamp}")
        
        # 4. Calcula dificuldade
        print("\n[4/5] Analisando dificuldade da MAINNET...")
        target_zeros = calculate_leading_zeros(bits)
        print(f"    [!!] Dificuldade MAINNET: ~{target_zeros} zeros hexadecimais")
        print(f"    [!!] SHARE TARGET: 8 zeros (valor comercial)")
        print(f"    [!!] BLOCK TARGET: {target_zeros} zeros (impossivel solo)")
        
        # 5. Monta o header
        print("\n[5/5] Construindo Block Header Template...")
        
        def swap_endian(hex_str):
            return "".join(reversed([hex_str[i:i+2] for i in range(0, len(hex_str), 2)]))
        
        header_hex = (
            struct.pack("<I", version).hex() +
            swap_endian(prev_hash_hex) +
            swap_endian(merkle_root_hex) +
            struct.pack("<I", timestamp).hex() +
            struct.pack("<I", bits).hex() +
            "00000000"  # Placeholder para Nonce
        )
        
        print(f"    [OK] Header Size: {len(header_hex)//2} bytes")
        
        # Salva os dados
        network_data = {
            "network": "MAINNET",
            "prev_hash": prev_hash_hex,
            "merkle_root": merkle_root_hex,
            "timestamp": timestamp,
            "bits": bits,
            "version": version,
            "header_template": header_hex,
            "target_zeros_block": target_zeros,
            "target_zeros_share": 8,
            "block_height_ref": block_height + 1
        }
        
        os.makedirs("results", exist_ok=True)
        with open("results/mainnet_target.json", "w") as f:
            json.dump(network_data, f, indent=2)
        
        print("\n" + "=" * 70)
        print("[DADOS DA ZONA DE GUERRA - MAINNET]")
        print("=" * 70)
        print(f"Network:        BITCOIN MAINNET")
        print(f"Previous Hash:  {prev_hash_hex}")
        print(f"Merkle Root:    {merkle_root_hex}")
        print(f"Bits:           {bits} (0x{bits:08x})")
        print(f"Block Diff:     ~{target_zeros} zeros (IMPOSSIVEL SOLO)")
        print(f"Share Diff:     8 zeros (ALVO COMERCIAL)")
        print(f"Next Block:     #{network_data['block_height_ref']}")
        print("=" * 70)
        
        print(f"\n[MAINNET HEADER] Raw Hex:")
        print(header_hex)
        print("\n" + "-" * 70)
        print("[PRONTO] Salvo em results/mainnet_target.json")
        print("[PROXIMO] Execute: python 1_golem_scout_fez.py")
        print("-" * 70)
        
        return network_data
        
    except Exception as e:
        print(f"\n[ERRO CRITICO] Nao foi possivel conectar a MAINNET:")
        print(f"   {e}")
        return None

def calculate_leading_zeros(bits):
    """Calcula zeros hex esperados a partir do campo 'bits'."""
    exp = bits >> 24
    mant = bits & 0xffffff
    target = mant * (256 ** (exp - 3))
    target_hex = f"{target:064x}"
    zeros = len(target_hex) - len(target_hex.lstrip('0'))
    return zeros

def test_sha256d():
    """Valida SHA-256d com o Genesis Block."""
    print("\n[TESTE] Validando SHA-256d...")
    genesis_header = bytes.fromhex(
        "0100000000000000000000000000000000000000000000000000000000000000"
        "000000003ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa"
        "4b1e5e4a29ab5f49ffff001d1dac2b7c"
    )
    expected = "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"
    result = hashlib.sha256(hashlib.sha256(genesis_header).digest()).digest()[::-1].hex()
    
    if result == expected:
        print("    [OK] SHA-256d validado!")
    else:
        print(f"    [ERRO] Hash nao bateu!")
    return result == expected

if __name__ == "__main__":
    test_sha256d()
    get_mainnet_work()
