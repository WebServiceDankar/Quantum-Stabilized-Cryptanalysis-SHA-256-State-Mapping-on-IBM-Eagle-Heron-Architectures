#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
FASE 2b: THE SNIPER - IONQ FORTE-1 (36 Qubits, Trapped Ions)
===============================================================================
Alternativa ao IBM Torino para a fase Sniper.
Usa a API nativa da IonQ (sem Qiskit) para maximo controle.

VANTAGENS IONQ:
  - Conectividade ALL-TO-ALL (zero SWAP gates)
  - Fidelidade 99.5%+ por gate (vs ~99% IBM)
  - Ideal para Grover: oracle + difusor sem overhead

PIPELINE:
  Scout (IBM Fez 156q) -> SNIPER (IonQ Forte 36q) -> Miner (CPU)

Input:  PEPITA_DO_FEZ (HEX da Fase 1)
Output: NONCE QUANTICO (32 bits em HEX)
===============================================================================
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import json
import time
import os
import math
import numpy as np

# =============================================================================
# CONFIGURACAO
# =============================================================================
IONQ_API_KEY = os.environ.get("IONQ_API_KEY", "COLOQUE_SEU_TOKEN_IONQ_AQUI")
IONQ_API_URL = "https://api.ionq.co/v0.3"
HEADERS = {
    "Authorization": f"apiKey {IONQ_API_KEY}",
    "Content-Type": "application/json"
}

# Backend: "simulator" (gratuito, 29q) ou "qpu.forte-1" (real, 36q)
TARGET_BACKEND = "simulator"  # Simulador IonQ (gratuito)
NONCE_QUBITS = 20  # 20 qubits = 1M estados (viavel para simulador)
AUX_QUBITS = 0
TOTAL_QUBITS = NONCE_QUBITS + AUX_QUBITS
NUM_SHOTS = 1024
GROVER_ITERATIONS = 1  # Numero de iteracoes de Grover

def build_sniper_circuit(pepita_hex, num_qubits=29):
    """
    Constroi circuito Grover-Ouroboros no formato IonQ JSON.
    
    Arquitetura (IonQ all-to-all):
      Q0-Q28:  Registro de Nonce (29 bits de busca)
      
    Fases:
      1. Superposicao uniforme (H em todos)
      2. Oraculo de Ressonancia (CZ baseado na Pepita)
      3. Difusor de Grover (H-X-CZ-X-H)
      4. Ouroboros Bite (CZ do ultimo ao primeiro)
    """
    circuit = []
    
    # =========================================================================
    # PHASE 1: SUPERPOSICAO (Hadamard em todos os qubits de nonce)
    # =========================================================================
    for i in range(num_qubits):
        circuit.append({"gate": "h", "target": i})
    
    # =========================================================================
    # PHASE 2: ORACULO DE RESSONANCIA (Pepita -> Phase Kickback)
    # =========================================================================
    # Converte Pepita para bits de referencia
    pepita_clean = pepita_hex.replace("0x", "")
    pepita_int = int(pepita_clean, 16)
    pepita_bits = bin(pepita_int)[2:].zfill(155)
    
    # Usa os primeiros bits da pepita para modular rotacoes (Warm Start)
    # Em vez de CZ oracle classico, usamos Ry rotations baseadas na pepita
    # Isso "inclina" a superposicao na direcao sugerida pelo Fez
    for i in range(num_qubits):
        bit_idx = i % len(pepita_bits)
        if pepita_bits[bit_idx] == '1':
            # Rotacao forte para qubits que a pepita marca como '1'
            angle = 0.15  # Turns (IonQ usa turns, nao radianos: 1 turn = 2*pi)
            circuit.append({"gate": "ry", "rotation": angle, "target": i})
    
    # Entanglement Oracle: CNOT entre pares correlacionados pela pepita
    # IonQ permite CNOT entre QUALQUER par (all-to-all!) - sem SWAP!
    oracle_pairs = []
    for i in range(num_qubits - 1):
        bit_i = pepita_bits[i % len(pepita_bits)]
        bit_next = pepita_bits[(i + 1) % len(pepita_bits)]
        if bit_i == '1' and bit_next == '1':
            oracle_pairs.append((i, i + 1))
            circuit.append({"gate": "cnot", "control": i, "target": i + 1})
    
    # Cross-correlacoes longas (so possivel no IonQ!)
    # Conecta qubits distantes que compartilham padrao na pepita
    for i in range(0, num_qubits - 8, 8):
        j = i + 8
        if j < num_qubits:
            bit_i = pepita_bits[i % len(pepita_bits)]
            bit_j = pepita_bits[j % len(pepita_bits)]
            if bit_i == bit_j == '1':
                circuit.append({"gate": "cnot", "control": i, "target": j})
    
    # =========================================================================
    # PHASE 3: DIFUSOR DE GROVER
    # =========================================================================
    for iteration in range(GROVER_ITERATIONS):
        # H em todos
        for i in range(num_qubits):
            circuit.append({"gate": "h", "target": i})
        
        # X em todos
        for i in range(num_qubits):
            circuit.append({"gate": "x", "target": i})
        
        # Multi-controlled Z simplificado: CZ entre vizinhos + long-range
        # Versao leve para compatibilidade com simulador
        for i in range(0, num_qubits - 1, 2):
            circuit.append({"gate": "cnot", "control": i, "target": i + 1})
        circuit.append({"gate": "z", "target": num_qubits - 1})
        for i in range(num_qubits - 3, -1, -2):
            circuit.append({"gate": "cnot", "control": i, "target": i + 1})
        
        # X em todos
        for i in range(num_qubits):
            circuit.append({"gate": "x", "target": i})
        
        # H em todos
        for i in range(num_qubits):
            circuit.append({"gate": "h", "target": i})
    
    # =========================================================================
    # PHASE 4: OUROBOROS BITE (Estabilizacao Circular)
    # =========================================================================
    # Fecha o loop: ultimo qubit -> primeiro
    circuit.append({"gate": "cnot", "control": num_qubits - 1, "target": 0})
    # Phase lock
    circuit.append({"gate": "rz", "rotation": 0.0625, "target": 0})  # pi/16 phase
    
    return circuit

def submit_job(circuit, num_qubits, target_backend, shots):
    """Envia job para a API IonQ."""
    payload = {
        "target": target_backend,
        "shots": shots,
        "input": {
            "format": "ionq.circuit.v0",
            "gateset": "qis",
            "qubits": num_qubits,
            "circuit": circuit
        }
    }
    
    response = requests.post(
        f"{IONQ_API_URL}/jobs",
        headers=HEADERS,
        json=payload,
        timeout=30
    )
    
    if response.status_code in [200, 201]:
        return response.json()
    else:
        print(f"[ERRO] Status: {response.status_code}")
        print(f"[ERRO] Response: {response.text}")
        return None

def poll_job(job_id, max_wait=600):
    """Monitora job ate completar."""
    start = time.time()
    while time.time() - start < max_wait:
        response = requests.get(
            f"{IONQ_API_URL}/jobs/{job_id}",
            headers=HEADERS,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "unknown")
            
            if status == "completed":
                return data
            elif status in ["failed", "canceled"]:
                print(f"[ERRO] Job {status}: {data.get('error', 'unknown')}")
                return None
            else:
                elapsed = time.time() - start
                print(f"  [Status: {status}] Aguardando... ({elapsed:.0f}s)")
                time.sleep(5)
        else:
            print(f"[ERRO] Poll failed: {response.status_code}")
            time.sleep(5)
    
    print("[TIMEOUT] Job excedeu tempo maximo")
    return None

def extract_nonce(result_data, num_qubits):
    """Extrai o nonce quantico dos resultados."""
    # IonQ retorna probabilidades por estado
    probabilities = result_data.get("data", {}).get("probabilities", {})
    
    if not probabilities:
        # Tenta formato alternativo (histogram)
        histogram = result_data.get("data", {}).get("histogram", {})
        if histogram:
            probabilities = histogram
    
    if not probabilities:
        # Tenta buscar no results_url separado (padrao IonQ)
        results_url = result_data.get("results_url", "")
        if results_url:
            print(f"  Buscando resultados em {results_url}...")
            full_url = f"https://api.ionq.co{results_url}" if results_url.startswith("/") else results_url
            resp = requests.get(full_url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                results_body = resp.json()
                # Pode ser dict direto ou ter chave "probabilities"
                if isinstance(results_body, dict):
                    probabilities = results_body.get("probabilities", results_body)
                print(f"  [OK] {len(probabilities)} estados recebidos")
    
    if not probabilities:
        print("[ERRO] Sem dados de probabilidade no resultado")
        print(f"[DEBUG] Keys disponiveis: {list(result_data.get('data', {}).keys())}")
        print(f"[DEBUG] Full data: {json.dumps(result_data.get('data', {}), indent=2)[:1000]}")
        return None
    
    # Mostra top 5 estados
    sorted_states = sorted(probabilities.items(), key=lambda x: float(x[1]), reverse=True)
    print(f"  Top 5 estados:")
    for s, p in sorted_states[:5]:
        print(f"    State {s}: {float(p)*100:.4f}%")
    
    # Encontra estado mais provavel
    best_state = sorted_states[0]
    state_key = best_state[0]
    state_prob = float(best_state[1])
    
    # Converte estado para inteiro
    # IonQ pode retornar como int string ou bitstring
    try:
        nonce_int = int(state_key)
    except ValueError:
        # E uma bitstring
        nonce_int = int(state_key, 2)
    
    # Garante 32 bits (pad ou truncate)
    nonce_int = nonce_int & 0xFFFFFFFF
    nonce_hex = f"{nonce_int:08x}"
    nonce_bits = f"{nonce_int:032b}"
    
    return {
        "nonce_int": nonce_int,
        "nonce_hex": nonce_hex,
        "nonce_bits": nonce_bits,
        "probability": state_prob
    }

def run_sniper_ionq(pepita_hex):
    """Executa o Sniper completo na IonQ."""
    
    print("=" * 70)
    print("FASE 2b: SNIPER IONQ - Trapped Ion Precision")
    print("=" * 70)
    print(f"\n[CONFIGURACAO]")
    print(f"  Backend: {TARGET_BACKEND}")
    print(f"  Qubits: {NONCE_QUBITS}")
    print(f"  Shots: {NUM_SHOTS}")
    print(f"  Grover Iterations: {GROVER_ITERATIONS}")
    print(f"  Pepita Input: {pepita_hex[:24]}...")
    
    # =========================================================================
    # CONSTRUIR CIRCUITO
    # =========================================================================
    print(f"\n[1/4] Construindo circuito Grover-Ouroboros...")
    circuit = build_sniper_circuit(pepita_hex, NONCE_QUBITS)
    print(f"  Total de gates: {len(circuit)}")
    
    # Conta tipos de gate
    gate_counts = {}
    for gate in circuit:
        g = gate["gate"]
        gate_counts[g] = gate_counts.get(g, 0) + 1
    for g, c in sorted(gate_counts.items()):
        print(f"    {g}: {c}")
    
    # =========================================================================
    # SUBMETER JOB
    # =========================================================================
    print(f"\n[2/4] Submetendo job para {TARGET_BACKEND}...")
    job_result = submit_job(circuit, NONCE_QUBITS, TARGET_BACKEND, NUM_SHOTS)
    
    if not job_result:
        print("[ERRO CRITICO] Falha na submissao do job")
        return None
    
    job_id = job_result.get("id", "unknown")
    print(f"  Job ID: {job_id}")
    print(f"  Status: {job_result.get('status', 'unknown')}")
    
    # =========================================================================
    # AGUARDAR RESULTADO
    # =========================================================================
    print(f"\n[3/4] Aguardando execucao quantica...")
    
    # Se ja completou (simulador e rapido)
    if job_result.get("status") == "completed":
        final_result = job_result
    else:
        final_result = poll_job(job_id)
    
    if not final_result:
        print("[ERRO] Job nao completou")
        return None
    
    # =========================================================================
    # EXTRAIR NONCE
    # =========================================================================
    print(f"\n[4/4] Extraindo Nonce Quantico...")
    nonce_data = extract_nonce(final_result, NONCE_QUBITS)
    
    if not nonce_data:
        print("[ERRO] Falha na extracao do nonce")
        print(f"[DEBUG] Result data: {json.dumps(final_result, indent=2)[:500]}")
        return None
    
    # =========================================================================
    # RELATORIO
    # =========================================================================
    print("\n" + "=" * 70)
    print("RELATORIO SNIPER - IONQ FORTE")
    print("=" * 70)
    print(f"\n[NONCE QUANTICO ENCONTRADO]")
    print(f"  Binario: {nonce_data['nonce_bits']}")
    print(f"  Decimal: {nonce_data['nonce_int']}")
    print(f"  HEX: {nonce_data['nonce_hex']}")
    print(f"  Probabilidade: {nonce_data['probability']*100:.4f}%")
    print(f"\n[HARDWARE]")
    print(f"  Backend: {TARGET_BACKEND}")
    print(f"  Qubits: {NONCE_QUBITS}")
    print(f"  Shots: {NUM_SHOTS}")
    print(f"  Gates: {len(circuit)}")
    print(f"\n[PROXIMO PASSO]")
    print(f"  Use o nonce no minerador:")
    print(f"  QUANTUM_NONCE_HEX = \"{nonce_data['nonce_hex']}\"")
    print("=" * 70)
    
    # Salvar resultado
    report = {
        "backend": TARGET_BACKEND,
        "hardware": "IonQ (Trapped Ions)",
        "job_id": job_id,
        "pepita_input": pepita_hex,
        "nonce_hex": nonce_data["nonce_hex"],
        "nonce_decimal": nonce_data["nonce_int"],
        "nonce_binary": nonce_data["nonce_bits"],
        "probability": nonce_data["probability"],
        "num_qubits": NONCE_QUBITS,
        "num_shots": NUM_SHOTS,
        "total_gates": len(circuit)
    }
    
    os.makedirs("results", exist_ok=True)
    with open("results/sniper_result.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n[SALVO] results/sniper_result.json")
    
    return nonce_data["nonce_hex"]

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    # Carrega pepita automaticamente do Scout
    scout_file = "results/scout_result.json"
    if os.path.exists(scout_file):
        with open(scout_file, "r") as f:
            scout_data = json.load(f)
        pepita = scout_data.get("pepita_hex", "")
        print(f"[AUTO] Pepita carregada do Scout: {pepita[:24]}...")
    else:
        # Fallback: Pepita da MAINNET (Bloco #935,838)
        pepita = "0x5098501644a202409021822100690d580142480"
        print(f"[MANUAL] Usando pepita hardcoded")
    
    run_sniper_ionq(pepita)
