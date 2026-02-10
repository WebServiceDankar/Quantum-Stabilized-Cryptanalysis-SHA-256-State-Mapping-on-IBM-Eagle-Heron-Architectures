#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
GOLEM TESTNET PROTOCOL - PASSO 0: INTELIGENCIA
===============================================================================
Coleta dados REAIS da Bitcoin Testnet para alimentar o pipeline quantico.
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import struct
import time
import json
import hashlib

def get_testnet_work():
    print("=" * 70)
    print("[PASSO 0] INTELIGENCIA - Coletando dados da Bitcoin Testnet")
    print("=" * 70)
    
    try:
        # 1. Pega o último bloco para obter o Hash Anterior
        print("\n[1/4] Consultando último bloco minerado...")
        last_block_req = requests.get("https://blockstream.info/testnet/api/blocks/tip/hash")
        prev_hash = last_block_req.text.strip()
        print(f"    [OK] Previous Block Hash: {prev_hash[:16]}...{prev_hash[-16:]}")
        
        # 2. Pega os detalhes desse bloco para obter a dificuldade (bits)
        print("\n[2/4] Obtendo parâmetros de dificuldade...")
        block_details = requests.get(f"https://blockstream.info/testnet/api/block/{prev_hash}").json()
        
        version = 0x20000000  # Versão padrão (BIP 9)
        prev_hash_hex = prev_hash
        
        # Simulamos uma Merkle Root (em produção, você montaria isso das transações)
        # Vamos usar um valor que represente "transações pendentes" simuladas
        merkle_root_hex = "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b"
        
        timestamp = int(time.time())
        bits = int(block_details['bits'])
        
        print(f"    [OK] Version:        0x{version:08x}")
        print(f"    [OK] Bits (Target):  0x{bits:08x}")
        print(f"    [OK] Timestamp:      {timestamp}")
        
        # 3. Calcula quantos zeros são necessários
        print("\n[3/4] Analisando dificuldade da rede...")
        target_zeros = calculate_leading_zeros(bits)
        print(f"    [OK] Dificuldade:    ~{target_zeros} zeros hexadecimais")
        
        # 4. Monta o header (SEM o nonce ainda)
        print("\n[4/4] Construindo Block Header Template...")
        
        def swap_endian(hex_str):
            """Inverte ordem dos bytes (Little Endian)"""
            return "".join(reversed([hex_str[i:i+2] for i in range(0, len(hex_str), 2)]))
        
        header_hex = (
            struct.pack("<I", version).hex() +
            swap_endian(prev_hash_hex) +
            swap_endian(merkle_root_hex) +
            struct.pack("<I", timestamp).hex() +
            struct.pack("<I", bits).hex() +
            "00000000"  # Placeholder para o Nonce (será substituído)
        )
        
        print(f"    [OK] Header Size:    {len(header_hex)//2} bytes (80 bytes esperado)")
        
        # 5. Salva os dados para os próximos scripts
        network_data = {
            "prev_hash": prev_hash_hex,
            "merkle_root": merkle_root_hex,
            "timestamp": timestamp,
            "bits": bits,
            "version": version,
            "header_template": header_hex,
            "target_zeros": target_zeros,
            "block_height_ref": block_details.get('height', 0) + 1
        }
        
        with open("results/network_target.json", "w") as f:
            json.dump(network_data, f, indent=2)
        
        print("\n" + "=" * 70)
        print("[DADOS REAIS DA REDE] Salvo em results/network_target.json")
        print("=" * 70)
        print(f"Previous Hash:  {prev_hash_hex}")
        print(f"Merkle Root:    {merkle_root_hex}")
        print(f"Bits (Hex):     0x{bits:08x}")
        print(f"Timestamp:      {timestamp}")
        print(f"Target Zeros:   {target_zeros}")
        print(f"Next Block:     #{network_data['block_height_ref']} (estimado)")
        print("=" * 70)
        
        print("\n[BLOCK HEADER TEMPLATE] Raw Hex:")
        print(header_hex)
        print("\n" + "-" * 70)
        print("[PRONTO] Execute agora: python 1_golem_scout_fez.py")
        print("-" * 70)
        
        return network_data
        
    except Exception as e:
        print(f"\n[ERRO] Nao foi possivel conectar a API da Testnet:")
        print(f"   {e}")
        return None

def calculate_leading_zeros(bits):
    """
    Calcula quantos zeros hexadecimais são esperados com base no 'bits'.
    Bits é a representação compactada do target.
    """
    # Decodifica o target compactado
    exp = bits >> 24
    mant = bits & 0xffffff
    target = mant * (256 ** (exp - 3))
    
    # Converte para hex e conta os zeros iniciais
    target_hex = f"{target:064x}"
    zeros = len(target_hex) - len(target_hex.lstrip('0'))
    
    return zeros

def test_hash_validation():
    """
    Testa se nossa função SHA-256 duplo está correta.
    """
    print("\n[TESTE] Validando funcao SHA-256d...")
    
    # Exemplo conhecido: Genesis Block do Bitcoin
    genesis_header = bytes.fromhex(
        "0100000000000000000000000000000000000000000000000000000000000000"
        "000000003ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa"
        "4b1e5e4a29ab5f49ffff001d1dac2b7c"
    )
    
    expected_hash = "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"
    
    # SHA-256 duplo
    hash_result = hashlib.sha256(hashlib.sha256(genesis_header).digest()).digest()
    hash_hex = hash_result[::-1].hex()  # Little -> Big Endian
    
    if hash_hex == expected_hash:
        print("    [OK] SHA-256d validado com sucesso!")
    else:
        print(f"    [ERRO] Hash nao bateu!")
        print(f"      Esperado: {expected_hash}")
        print(f"      Obtido:   {hash_hex}")

if __name__ == "__main__":
    test_hash_validation()
    get_testnet_work()
