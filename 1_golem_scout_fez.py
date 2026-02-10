# ═══════════════════════════════════════════════════════════════════════════════
#                    FASE 1: THE SCOUT (O Explorador)
#                    Hardware: IBM Fez (156 Qubits - Eagle r3)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Função: Criar o "Pentagrama" (155 bits) que aponta para a região de menor
#         entropia (vácuo) do espaço de busca SHA-256.
#
# Output: PEPITA (Estado mais frequente em HEX)
#         → Copiar para a Fase 2
#
# ═══════════════════════════════════════════════════════════════════════════════

import sys
import numpy as np

try:
    from qiskit import QuantumCircuit, transpile
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "qiskit", "qiskit-ibm-runtime"])
    from qiskit import QuantumCircuit, transpile
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

def run_scout():
    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIGURAÇÃO - INSIRA SUA CHAVE IBM AQUI
    # ═══════════════════════════════════════════════════════════════════════════
    API_KEY = "nMvJnquaNusDZYB77_bBM-LO5-XPrJBjVRq2hytFub2n"
    
    # Fix encoding para Windows
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except: pass
    
    try:
        service = QiskitRuntimeService(token=API_KEY)
        backend = service.backend("ibm_fez")
        print(f"🛰️  FASE 1: SCOUT - Iniciando Sonda Pentagram")
        print(f"    Backend: {backend.name} ({backend.num_qubits} qubits)")
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return None

    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIGURAÇÃO GEOMÉTRICA (Vogel/Fibonacci + MERKLE ROOT SEED)
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Ler dados da rede (gerados pelo 0_get_network_data.py)
    import json
    import os
    
    network_file = "results/network_target.json"
    if os.path.exists(network_file):
        with open(network_file, "r") as f:
            network_data = json.load(f)
        merkle_seed = network_data["merkle_root"]
        print(f"\n🌐 MODO TESTNET ATIVO")
        print(f"   Merkle Root Seed: {merkle_seed[:16]}...{merkle_seed[-16:]}")
        print(f"   Target Zeros: {network_data['target_zeros']}")
        
        # Converte Merkle Root em array de floats para modular rotação
        merkle_bytes = bytes.fromhex(merkle_seed)
        merkle_floats = np.array([b/255.0 for b in merkle_bytes])
    else:
        print(f"\n⚠️  MODO SIMULAÇÃO (sem dados da rede)")
        merkle_floats = np.random.rand(32)  # Fallback

    num_qubits = 155  # 5 segmentos de 31 bits
    step = 31
    
    # Geometria Sagrada
    indices = np.arange(0, num_qubits, dtype=float) + 0.5
    phi = (1 + 5**0.5) / 2  # Proporção Áurea
    
    qc = QuantumCircuit(num_qubits)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FASE 1.1: INJEÇÃO GEOMÉTRICA (O Mapa) - MODULADO PELO MERKLE ROOT
    # ═══════════════════════════════════════════════════════════════════════════
    print("\n🧬 Injetando Geometria Fibonacci (Modulada pela Testnet)...")
    
    for i in range(num_qubits):
        angle = np.pi * phi * i
        
        # NOVA LÓGICA: Modula ângulo com bytes do Merkle Root
        merkle_mod = merkle_floats[i % len(merkle_floats)]
        
        qc.ry((np.cos(angle) + merkle_mod * 0.3) * np.pi * 0.45, i)
        qc.rz((np.sin(angle) + merkle_mod * 0.15) * np.pi / 4, i)

    # ═══════════════════════════════════════════════════════════════════════════
    # FASE 1.2: PIPELINE PENTAGRAM (A→B→C→D→E)
    # Transmissão de Memória em 5 estágios
    # ═══════════════════════════════════════════════════════════════════════════
    print("⏳ Ativando Pipeline Pentagram (5 gerações)...")
    
    for s in range(4):  # 4 saltos entre 5 segmentos
        for i in range(step):
            qc.rxx(np.pi/8, i + s*step, i + (s+1)*step)
            qc.ryy(np.pi/8, i + s*step, i + (s+1)*step)

    # ═══════════════════════════════════════════════════════════════════════════
    # FASE 1.3: MORDIDA DO OUROBOROS (Estabilização)
    # Conecta o fim (E) ao início (A) para fechar a fase
    # ═══════════════════════════════════════════════════════════════════════════
    print("🐍 Fechando loop Ouroboros (Q154 → Q0)...")
    qc.cz(154, 0)
    
    qc.measure_all()

    # ═══════════════════════════════════════════════════════════════════════════
    # EXECUÇÃO
    # ═══════════════════════════════════════════════════════════════════════════
    print(f"\n⚙️  Transpilando Ouroboros...")
    qc_t = transpile(qc, backend, optimization_level=3)
    print(f"    Profundidade: {qc_t.depth()}")
    
    num_shots = 4096
    print(f"\n⚡ Disparando Sonda ({num_shots} shots)...")
    
    try:
        sampler = SamplerV2(mode=backend)
        job = sampler.run([qc_t], shots=num_shots)
        print(f"✅ Job Enviado! ID: {job.job_id()}")
        print("⏳ Aguardando resultado...")
        
        result = job.result()
        counts = result[0].data.meas.get_counts()
        
        # Encontrar a PEPITA (estado mais frequente)
        best_state = max(counts.items(), key=lambda x: x[1])
        state_str = best_state[0][::-1]  # Reverter
        count = best_state[1]
        
        # Converter para HEX
        pepita_int = int(state_str, 2)
        pepita_hex = hex(pepita_int)
        
        print("\n" + "🔮" * 35)
        print(f"RELATÓRIO SCOUT - {backend.name.upper()}")
        print("🔮" * 35)
        print(f"\n[PEPITA ENCONTRADA]")
        print(f"  Binário: {state_str[:32]}...{state_str[-32:]}")
        print(f"  HEX: {pepita_hex}")
        print(f"  Frequência: {count}/{num_shots} ({count/num_shots*100:.2f}%)")
        print(f"  Peso (1s): {state_str.count('1')}/155")
        print(f"  Pureza (0s): {state_str.count('0')/155*100:.1f}%")
        print(f"\n[PRÓXIMO PASSO]")
        print(f"  Copie este HEX para a Fase 2 (golem_sniper_torino.py):")
        print(f"  PEPITA_DO_FEZ = \"{pepita_hex}\"")
        print("\n" + "🔮" * 35)
        
        # Salvar resultado
        import json
        report = {
            "job_id": job.job_id(),
            "backend": backend.name,
            "shots": num_shots,
            "pepita_hex": pepita_hex,
            "pepita_bin": state_str,
            "frequency": count,
            "purity": state_str.count('0') / 155
        }
        
        with open("results/scout_result.json", "w") as f:
            json.dump(report, f, indent=2)
        print("[SALVO] results/scout_result.json")
        
        return pepita_hex
        
    except Exception as e:
        print(f"❌ Erro na execução: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    run_scout()
