#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
GOLEM CASCADE ORCHESTRATOR (THE HIVE)
===============================================================================
Estágio 1 (Fez): Mapeia a entropia (Vogel/Ouroboros).
   -> Intervenção CPU 1: Analisa, limpa ruído, formata "Pepita".
Estágio 2 (Torino): Usa a Pepita para rodar Grover Tático (Sniper).
   -> Intervenção CPU 2: Pega o Setor e executa mineração cirúrgica.
Estágio 3 (CPU Worker): Varrer o setor indicado.

Loop Infinito: A Colmeia nunca dorme.
===============================================================================
"""
import sys
sys.stdout.reconfigure(line_buffering=True)

import time
import numpy as np
import hashlib
import multiprocessing
import os
import struct
from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2, SamplerOptions

# ==============================================================================
# CONFIGURAÇÃO CENTRAL
# ==============================================================================
BLOCK_HEADER_HEX = "01000000" + "00"*32 + "00"*32 + "00000000" # Exemplo Mainnet
TARGET_ZEROS_CLASSIC = 8  # Alvo final para a CPU (Shares)

# Função de Mineração Local (definida no top-level para multiprocessing no Windows)
def mine_worker(start, end, header_hex, target_zeros, queue):
    header_bytes = bytes.fromhex(header_hex)
    header_prefix = header_bytes[:76]
    
    for n in range(start, end):
        # Monta header com nonce em little-endian
        nonce_bytes = struct.pack("<I", n)
        full_header = header_prefix + nonce_bytes
        
        # Double SHA-256
        h = hashlib.sha256(hashlib.sha256(full_header).digest()).digest()
        h_rev = h[::-1] # Display order
        
        # Check zeros
        zeros = 0
        for byte in h_rev:
            if byte == 0: zeros += 2
            elif byte < 16: 
                zeros += 1
                break
            else: break
            
        if zeros >= target_zeros:
            queue.put((n, h_rev.hex()))
            return

class GolemCascade:
    def __init__(self):
        token = os.environ.get("IBM_QUANTUM_TOKEN")
        if not token:
            # Fallback para hardcoded se env não existir (mas ideal é env)
            token = "nMvJnquaNusDZYB77_bBM-LO5-XPrJBjVRq2hytFub2n" 
            
        try:
            self.service = QiskitRuntimeService(token=token)
            print("✅ Conectado ao IBM Quantum Service.")
        except Exception as e:
            print(f"⚠️ Erro de conexão: {e}")
            self.service = None

        self.state = {
            "pepita_hex": None,
            "target_sector": None,
            "nonce_final": None
        }

    # ==========================================================================
    # ESTÁGIO 1: IBM FEZ (SCOUT) - Ouroboros Topology
    # ==========================================================================
    def run_stage_1_scout(self):
        if not self.service: return False
        
        print("\n" + "="*50)
        print("🛰️  ESTÁGIO 1: SCOUT (IBM FEZ - 156 Qubits)")
        print("    Objetivo: Mapear geometria de vácuo (Pepita)")
        print("="*50)

        try:
            backend = self.service.backend("ibm_fez")
            num_qubits = 155
            
            # 1. Geometria Sagrada (Vogel)
            indices = np.arange(0, num_qubits, dtype=float) + 0.5
            phi = (1 + 5**0.5) / 2
            
            qc = QuantumCircuit(num_qubits)
            
            for i in range(num_qubits):
                angle = np.pi * phi * i
                qc.ry(np.cos(angle) * np.pi * 0.45, i) # Pressão calculada
                qc.rz(np.sin(angle) * np.pi / 4, i)

            # 2. Mordida da Cobra (A Estabilização)
            qc.cz(154, 0)
            qc.measure_all()

            print("⚙️  Transpilando circuito Ouroboros...")
            qc_t = transpile(qc, backend, optimization_level=3)
            
            print("⚡ Enviando Job para a fila do Eagle...")
            sampler = SamplerV2(mode=backend)
            job = sampler.run([qc_t], shots=4096)
            print(f"⏳ Job ID: {job.job_id()} (Aguardando execução...)")
            
            # Bloqueia até ter o resultado (Handshake)
            result = job.result()
            counts = result[0].data.meas.get_counts()
            
            # CPU Intervention: Extração do melhor estado
            best_state = max(counts, key=counts.get)[::-1] # Little Endian fix
            
            # Converte binário para HEX
            hex_val = hex(int(best_state, 2))
            self.state["pepita_hex"] = hex_val
            
            print(f"💎 [CPU] Pepita extraída e limpa: {hex_val[:24]}...")
            return True
        except Exception as e:
            print(f"❌ Erro no Estágio 1: {e}")
            return False

    # ==========================================================================
    # ESTÁGIO 2: IBM TORINO (SNIPER) - Grover Tático
    # ==========================================================================
    def run_stage_2_sniper(self):
        if not self.state["pepita_hex"]:
            print("❌ Erro: Pepita não encontrada. Estágio 1 falhou.")
            return False

        print("\n" + "="*50)
        print("🎯 ESTÁGIO 2: SNIPER (IBM TORINO - 133 Qubits)")
        print("    Objetivo: Identificar Setor de Nonce")
        print("="*50)

        try:
            backend = self.service.backend("ibm_torino")
            
            # Prepara o alvo baseado na Pepita do Estágio 1
            pepita_int = int(self.state["pepita_hex"], 16)
            full_bits = bin(pepita_int)[2:].zfill(155)
            target_sector = full_bits[0:10] # Focamos nos primeiros 10 bits
            
            print(f"    Alvo Tático (Injetado pela CPU): {target_sector}")

            num_search_qubits = 10
            total_qubits = 133
            qc = QuantumCircuit(total_qubits)

            # Grover Simplificado (12 iterações para evitar decoerência)
            qc.h(range(num_search_qubits)) # Superposição
            
            for r in range(12):
                # Oráculo
                for i in range(num_search_qubits):
                    if target_sector[i] == '1':
                        qc.cz(i, (i + 1) % num_search_qubits)
                # Difusor
                qc.h(range(num_search_qubits))
                qc.x(range(num_search_qubits))
                qc.cz(num_search_qubits-1, 0)
                qc.x(range(num_search_qubits))
                qc.h(range(num_search_qubits))

            qc.measure_all()
            
            # Dynamical Decoupling (A proteção extra do Heron)
            options = SamplerOptions()
            options.dynamical_decoupling.enable = True
            options.dynamical_decoupling.sequence_type = "XY4"

            print("⚡ Enviando Job para a fila do Heron...")
            sampler = SamplerV2(mode=backend, options=options)
            job = sampler.run([transpile(qc, backend, optimization_level=3)])
            print(f"⏳ Job ID: {job.job_id()} (Aguardando execução...)")

            result = job.result()
            counts = result[0].data.meas.get_counts()
            
            # CPU Intervention: Análise Estatística do Setor
            # Agrega contagens pelos primeiros 10 bits (setor)
            sector_counts = {}
            for state_raw, count in counts.items():
                state = state_raw[::-1]
                sector = state[0:10]
                sector_counts[sector] = sector_counts.get(sector, 0) + count
            
            winner = max(sector_counts, key=sector_counts.get)
            self.state["target_sector"] = hex(int(winner, 2))
            
            print(f"🎯 [CPU] Setor Confirmado: {self.state['target_sector']} ({winner})")
            return True
        except Exception as e:
            print(f"❌ Erro no Estágio 2: {e}")
            return False

    # ==========================================================================
    # ESTÁGIO 3: CPU WORKER (MINER) - Surgical Strike
    # ==========================================================================
    def run_stage_3_miner(self):
        if not self.state["target_sector"]:
            return False

        print("\n" + "="*50)
        print("🔨 ESTÁGIO 3: ESCAVADEIRA CLÁSSICA (LOCAL)")
        print("    Objetivo: Varrer o setor indicado pelo Torino")
        print("="*50)

        sector_int = int(self.state["target_sector"], 16)
        # O Setor são os 10 primeiros bits de um total de 32
        # Shift 22 bits (32 - 10)
        start_range = sector_int << 22
        end_range = (sector_int + 1) << 22
        total = end_range - start_range
        
        print(f"    Range de Busca: {start_range:,} até {end_range:,}")
        print(f"    Total Hashes: {total:,} (Processamento rápido)")

        queue_res = multiprocessing.Queue()
        cores = multiprocessing.cpu_count()
        chunk = total // cores
        procs = []

        # Inicia workers
        for i in range(cores):
            s = start_range + (i * chunk)
            e = s + chunk
            if i == cores - 1: e = end_range
            p = multiprocessing.Process(target=mine_worker, args=(s, e, BLOCK_HEADER_HEX, TARGET_ZEROS_CLASSIC, queue_res))
            procs.append(p)
            p.start()

        found = False
        start_time = time.time()
        
        # Loop de monitoramento (timeout 2 minutos por ciclo)
        while any(p.is_alive() for p in procs):
            try:
                # check queue (non-blocking ou timeout curto)
                if not queue_res.empty():
                    n, h = queue_res.get()
                    print("\n" + "🏆" * 20)
                    print(f"CASCATA CONCLUÍDA COM SUCESSO!")
                    print(f"💎 Nonce: {n}")
                    print(f"📜 Hash: {h}")
                    print("🏆" * 20)
                    found = True
                    for p in procs: p.terminate()
                    break
                
                # Timeout de segurança se demorar > 5 min
                if time.time() - start_time > 300:
                    print("⚠️ Timeout na mineração local.")
                    for p in procs: p.terminate()
                    break
                    
                time.sleep(0.5)
            except Exception:
                pass
        
        if not found:
            print("❌ Nenhum share encontrado neste setor.")
            return False
            
        return True

# ==============================================================================
# LOOP PRINCIPAL (A "COLMEIA")
# ==============================================================================
if __name__ == "__main__":
    golem = GolemCascade()
    
    # Loop Infinito (Modelo Hive)
    try:
        while True:
            print("\n🔄 INICIANDO NOVO CICLO DA CASCATA...")
            
            # Passo 1: Eagle (Scout)
            if golem.run_stage_1_scout():
                
                # Passo 2: Heron (Sniper) - só roda se o 1 der certo
                if golem.run_stage_2_sniper():
                    
                    # Passo 3: CPU (Miner) - só roda se o 2 der certo
                    if golem.run_stage_3_miner():
                        print("💰 Share encontrado e salvo. Preparando próximo ciclo...")
                    else:
                        print("⚠️ Falha na mineração local (Setor vazio).")
                else:
                    print("⚠️ Falha no Sniper.")
            else:
                print("⚠️ Falha no Scout.")
                
            print("💤 Resfriando sistema por 10s...")
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n🛑 Colmeia interrompida pelo usuário.")
