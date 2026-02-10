# ===============================================================================
#                    FASE 3: THE HYBRID MINER (A Escavadeira)
#                    Hardware: Seu PC (CPU Multi-Core)
# ===============================================================================
#
# Função: Varrer a vizinhança do Nonce Quântico para encontrar o hash válido
#         final ("O 12:00" - o hash com os zeros necessários).
#
# Input:  QUANTUM_NONCE_HEX (HEX da Fase 2)
# Output: HASH VÁLIDO (ou tentativa mais próxima)
#
# ===============================================================================

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import hashlib
import multiprocessing
import time
import json
import os

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO CRÍTICA (Vinda da Fase 2)
# ═══════════════════════════════════════════════════════════════════════════════


QUANTUM_NONCE_HEX = "1d09268a"      # RESULTADO TESTNET (Bloco #4,840,846)
SEARCH_RADIUS = 100_000_000         # Raio de busca (+/- 100 milhões)
DIFFICULTY_TARGET = 14              # Zeros da Testnet (real)

# Carregar Block Header REAL da Testnet
import json
import os

network_file = "results/network_target.json"
if os.path.exists(network_file):
    with open(network_file, "r") as f:
        network_data = json.load(f)
    BLOCK_HEADER_TEMPLATE = network_data["header_template"]
    DIFFICULTY_TARGET = network_data["target_zeros"]
    print(f"[MODO TESTNET] Bloco #{network_data['block_height_ref']}")
else:
    # Fallback para teste
    BLOCK_HEADER_TEMPLATE = "01000000" + "00"*32 + "00"*32 + "00000000"
    print("[MODO SIMULAÇÃO] Usando header falso")

# ═══════════════════════════════════════════════════════════════════════════════

def worker(start, end, target_zeros, header_template, queue, worker_id):
    """Worker que busca nonces em um range específico."""
    best_zeros = 0
    best_nonce = start
    best_hash = ""
    
    for n in range(start, end):
        # Monta o header completo com o nonce (Bitcoin usa Little Endian)
        header_hex = header_template[:-8] + f"{n:08x}"  # Substitui últimos 8 chars
        header_bytes = bytes.fromhex(header_hex)
        
        # Hash Duplo (SHA-256^2) - como no Bitcoin real
        h = hashlib.sha256(hashlib.sha256(header_bytes).digest())
        h_hex = h.digest()[::-1].hex()  # Little -> Big Endian para display
        
        # Contar zeros iniciais
        zeros = len(h_hex) - len(h_hex.lstrip('0'))
        
        if zeros > best_zeros:
            best_zeros = zeros
            best_nonce = n
            best_hash = h_hex
        
        # Encontrou o target!
        if h_hex.startswith("0" * target_zeros):
            queue.put(("SUCCESS", n, h_hex, worker_id))
            return
        
        # Report de progresso a cada 1M
        if n % 1_000_000 == 0 and n > start:
            queue.put(("PROGRESS", n - start, best_zeros, worker_id))
    
    # Não encontrou, mas reporta o melhor
    queue.put(("BEST", best_nonce, best_hash, best_zeros))

def run_miner():
    center = int(QUANTUM_NONCE_HEX, 16)
    
    print("═" * 70)
    print("         🔨 FASE 3: HYBRID MINER - ESCAVADEIRA QUÂNTICO-CLÁSSICA")
    print("═" * 70)
    print(f"\n[CONFIGURAÇÃO]")
    print(f"  Nonce Quântico: {QUANTUM_NONCE_HEX} (decimal: {center})")
    print(f"  Raio de Busca: +/- {SEARCH_RADIUS:,}")
    print(f"  Target: {DIFFICULTY_TARGET} zeros iniciais")
    print(f"  Range Total: {SEARCH_RADIUS * 2:,} nonces")

    num_cores = multiprocessing.cpu_count()
    print(f"  CPUs Disponíveis: {num_cores}")
    
    chunk = (SEARCH_RADIUS * 2) // num_cores
    queue = multiprocessing.Queue()
    procs = []

    start_time = time.time()
    start_n = max(0, center - SEARCH_RADIUS)
    
    print(f"\n[INICIANDO BUSCA]")
    print(f"  De: {start_n:,}")
    print(f"  Até: {start_n + SEARCH_RADIUS * 2:,}")
    
    # Inicia os processos paralelos
    for i in range(num_cores):
        s = start_n + (i * chunk)
        e = s + chunk
        p = multiprocessing.Process(
            target=worker, 
            args=(s, e, DIFFICULTY_TARGET, BLOCK_HEADER_TEMPLATE, queue, i)
        )
        procs.append(p)
        p.start()
        print(f"  Worker {i}: {s:,} → {e:,}")

    print(f"\n{'─' * 70}")
    print("  Buscando... (Ctrl+C para parar)")
    print(f"{'─' * 70}")

    # Monitora
    found = False
    global_best_zeros = 0
    global_best_nonce = center
    global_best_hash = ""
    
    try:
        while any(p.is_alive() for p in procs):
            try:
                msg = queue.get(timeout=1)
                
                if msg[0] == "SUCCESS":
                    _, nonce, h_val, worker_id = msg
                    elapsed = time.time() - start_time
                    
                    print("\n" + "🏆" * 35)
                    print("         💰 SUCESSO! MINERAÇÃO HÍBRIDA CONFIRMADA!")
                    print("🏆" * 35)
                    print(f"\n[RESULTADO]")
                    print(f"  💎 Nonce Final: {nonce} (Hex: {hex(nonce)[2:]})")
                    print(f"  📜 Hash: {h_val}")
                    print(f"  ⏱️ Tempo: {elapsed:.2f}s")
                    print(f"  📍 Distância do Quantum: {nonce - center:+,}")
                    print(f"  🤖 Worker: {worker_id}")
                    print("\n" + "🏆" * 35)
                    
                    # Salvar resultado
                    result = {
                        "success": True,
                        "nonce_decimal": nonce,
                        "nonce_hex": hex(nonce)[2:],
                        "hash": h_val,
                        "zeros": DIFFICULTY_TARGET,
                        "quantum_center": center,
                        "distance_from_quantum": nonce - center,
                        "time_seconds": elapsed
                    }
                    with open("results/miner_result.json", "w") as f:
                        json.dump(result, f, indent=2)
                    print("[SALVO] results/miner_result.json")
                    
                    found = True
                    break
                    
                elif msg[0] == "PROGRESS":
                    _, count, best_z, worker_id = msg
                    print(f"  [Worker {worker_id}] {count:,} testados, melhor: {best_z} zeros")
                    
                elif msg[0] == "BEST":
                    _, nonce, h_val, zeros = msg
                    if zeros > global_best_zeros:
                        global_best_zeros = zeros
                        global_best_nonce = nonce
                        global_best_hash = h_val
                        
            except:
                pass
                
    except KeyboardInterrupt:
        print("\n⚠️ Interrompido pelo usuário")
        
    finally:
        for p in procs:
            p.terminate()
            p.join()
        
        if not found:
            elapsed = time.time() - start_time
            print(f"\n{'─' * 70}")
            print(f"[BUSCA COMPLETA - TARGET NÃO ENCONTRADO]")
            print(f"  Tempo total: {elapsed:.2f}s")
            print(f"  Melhor resultado: {global_best_zeros} zeros")
            print(f"  Nonce: {global_best_nonce} (Hex: {hex(global_best_nonce)[2:]})")
            print(f"  Hash: {global_best_hash}")
            print(f"\n[SUGESTÕES]")
            print(f"  • Aumentar SEARCH_RADIUS")
            print(f"  • Usar outro QUANTUM_NONCE_HEX da Fase 2")
            print(f"  • Reduzir DIFFICULTY_TARGET para teste")
            print(f"{'─' * 70}")

if __name__ == "__main__":
    # Garantir que a pasta results existe
    os.makedirs("results", exist_ok=True)
    run_miner()
