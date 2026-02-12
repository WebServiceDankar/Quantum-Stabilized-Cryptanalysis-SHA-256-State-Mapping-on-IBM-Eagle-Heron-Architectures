# ═══════════════════════════════════════════════════════════════════════════════
#                    FASE 2: THE SNIPER (O Atirador)
#                    Hardware: IBM Torino (133 Qubits - Heron r2)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Função: Usar a "Pepita" da Fase 1 como filtro para encontrar o Nonce Quântico
#         usando o Algoritmo de Grover.
#
# Input:  PEPITA_DO_FEZ (HEX da Fase 1)
# Output: NONCE QUÂNTICO (32 bits em HEX)
#         → Copiar para a Fase 3
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

def run_sniper(pepita_hex):
    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIGURAÇÃO - INSIRA SUA CHAVE IBM AQUI
    # ═══════════════════════════════════════════════════════════════════════════
    API_KEY = os.environ.get("IBM_QUANTUM_TOKEN", "COLOQUE_SEU_TOKEN_IBM_AQUI")
    
    # Fix encoding para Windows
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except: pass
    
    try:
        service = QiskitRuntimeService(token=API_KEY)
        backend = service.backend("ibm_torino")
        print(f"🎯 FASE 2: SNIPER - Iniciando Busca de Nonce")
        print(f"    Backend: {backend.name} ({backend.num_qubits} qubits)")
        print(f"    Pepita Input: {pepita_hex[:20]}...")
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return None

    # ═══════════════════════════════════════════════════════════════════════════
    # PROCESSAR PEPITA
    # ═══════════════════════════════════════════════════════════════════════════
    # Converter Pepita para Binário (Target)
    pepita_clean = pepita_hex.replace("0x", "")
    target_int = int(pepita_clean, 16)
    target_bits = bin(target_int)[2:].zfill(155)[:133]  # Ajuste para 133q
    
    print(f"    Target bits: {target_bits[:32]}...")
    
    num_qubits = 133
    qc = QuantumCircuit(num_qubits)

    # ═══════════════════════════════════════════════════════════════════════════
    # FASE 2.1: SUPERPOSIÇÃO DE NONCES (32 bits)
    # ═══════════════════════════════════════════════════════════════════════════
    print("\n🌀 Criando superposição de 2^32 nonces...")
    qc.h(range(32))

    # ═══════════════════════════════════════════════════════════════════════════
    # FASE 2.2: ORÁCULO DE RESSONÂNCIA (Baseado na Pepita do Fez)
    # ═══════════════════════════════════════════════════════════════════════════
    print("🔮 Aplicando Oráculo de Ressonância...")
    
    for i in range(32):
        if target_bits[i] == '1':
            qc.cz(i, i + 32)  # Inversão de fase se der match

    # ═══════════════════════════════════════════════════════════════════════════
    # FASE 2.3: DIFUSOR DE GROVER (Motor de Amplificação)
    # ═══════════════════════════════════════════════════════════════════════════
    print("⚡ Aplicando Difusor de Grover...")
    
    qc.h(range(32))
    qc.x(range(32))
    qc.cz(31, 0)  # Reflexão
    qc.x(range(32))
    qc.h(range(32))

    # ═══════════════════════════════════════════════════════════════════════════
    # FASE 2.4: ESTABILIZAÇÃO OUROBOROS (Versão Heron)
    # ═══════════════════════════════════════════════════════════════════════════
    print("🐍 Fechando loop Ouroboros (Q132 → Q0)...")
    qc.cz(132, 0)
    
    qc.measure_all()

    # ═══════════════════════════════════════════════════════════════════════════
    # EXECUÇÃO
    # ═══════════════════════════════════════════════════════════════════════════
    print(f"\n⚙️  Transpilando Sniper...")
    qc_t = transpile(qc, backend, optimization_level=3)
    print(f"    Profundidade: {qc_t.depth()}")
    
    num_shots = 1024  # Precisão sobre quantidade
    print(f"\n⚡ Disparando Grover ({num_shots} shots de precisão)...")
    
    try:
        sampler = SamplerV2(mode=backend)
        job = sampler.run([qc_t], shots=num_shots)
        print(f"✅ Job Enviado! ID: {job.job_id()}")
        print("⏳ Aguardando resultado...")
        
        result = job.result()
        counts = result[0].data.meas.get_counts()
        
        # Encontrar o Nonce Quântico (primeiros 32 bits mais frequentes)
        best_state = max(counts.items(), key=lambda x: x[1])
        state_str = best_state[0][::-1]  # Reverter
        count = best_state[1]
        
        # Extrair os 32 bits do nonce
        nonce_bits = state_str[:32]
        nonce_int = int(nonce_bits, 2)
        nonce_hex = hex(nonce_int)[2:].zfill(8)
        
        print("\n" + "🎯" * 35)
        print(f"RELATÓRIO SNIPER - {backend.name.upper()}")
        print("🎯" * 35)
        print(f"\n[NONCE QUÂNTICO ENCONTRADO]")
        print(f"  Binário: {nonce_bits}")
        print(f"  Decimal: {nonce_int}")
        print(f"  HEX: {nonce_hex}")
        print(f"  Frequência: {count}/{num_shots} ({count/num_shots*100:.2f}%)")
        print(f"\n[PRÓXIMO PASSO]")
        print(f"  Copie este HEX para a Fase 3 (golem_hybrid_miner.py):")
        print(f"  QUANTUM_NONCE_HEX = \"{nonce_hex}\"")
        print("\n" + "🎯" * 35)
        
        # Salvar resultado
        import json
        report = {
            "job_id": job.job_id(),
            "backend": backend.name,
            "pepita_input": pepita_hex,
            "nonce_hex": nonce_hex,
            "nonce_decimal": nonce_int,
            "nonce_binary": nonce_bits,
            "frequency": count
        }
        
        with open("results/sniper_result.json", "w") as f:
            json.dump(report, f, indent=2)
        print("[SALVO] results/sniper_result.json")
        
        return nonce_hex
        
    except Exception as e:
        print(f"❌ Erro na execução: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # ═══════════════════════════════════════════════════════════════════════════
    # COLOQUE AQUI O RESULTADO DA FASE 1 (SCOUT)
    # ═══════════════════════════════════════════════════════════════════════════
    PEPITA_DO_FEZ = "0x5098501644a202409021822100690d580142480"  # MAINNET REAL (Bloco #935,838)
    
    run_sniper(PEPITA_DO_FEZ)
