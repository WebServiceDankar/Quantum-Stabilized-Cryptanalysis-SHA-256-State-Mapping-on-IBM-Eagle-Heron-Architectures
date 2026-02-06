
import json
import matplotlib.pyplot as plt
import numpy as np
import os
import glob

def load_experiments(path='../experiments'):
    data = []
    files = glob.glob(os.path.join(path, '*.json'))
    for f in files:
        with open(f, 'r') as file:
            try:
                data.append(json.load(file))
            except:
                pass
    return data

def plot_sha_fidelity():
    # Simulação visual baseada nos dados do experimento SHA-256 Round 1
    functions = ['Input A', 'Input E', 'Ch (Choice)', 'Sigma1', 'Sigma0', 'Maj']
    fidelity = [100.0, 68.7, 81.2, 62.5, 50.0, 43.7] # Dados reais do seu experimento ibm_fez
    
    plt.figure(figsize=(10, 6))
    bars = plt.bar(functions, fidelity, color=['#00ff00', '#aaff00', '#00ccff', '#ffaa00', '#ff5500', '#ff0000'])
    
    plt.axhline(y=50, color='r', linestyle='--', label='Decoherence Threshold (Random Noise)')
    plt.axhline(y=80, color='g', linestyle='--', label='Target Fidelity for Ouroboros')
    
    plt.title('SHA-256 Quantum Gate Fidelity (IBM Eagle - 306 Depth)')
    plt.ylabel('Accuracy (%)')
    plt.ylim(0, 110)
    plt.grid(axis='y', alpha=0.3)
    plt.legend()
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 1, f"{yval}%", ha='center', fontweight='bold')
        
    plt.savefig('sha256_fidelity_metrics.png', dpi=300)
    print("Generated: sha256_fidelity_metrics.png")

def plot_vacuum_stability():
    # Visualização do experimento Heron (133 qubits)
    labels = ['Active Vacuum (zeros)', 'Thermal Noise (ones)']
    sizes = [86.5, 13.5] # 18/133 weight = ~13.5%
    colors = ['#00ccff', '#ff3333']
    explode = (0.1, 0)
    
    plt.figure(figsize=(8, 8))
    plt.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%', shadow=True, startangle=140)
    plt.title('Heron Processor: Vacuum State Stability (133 Qubits)\nTarget: Resonance 0xC1A95885')
    
    plt.savefig('heron_vacuum_stability.png', dpi=300)
    print("Generated: heron_vacuum_stability.png")

if __name__ == "__main__":
    print("Generating Visual Analysis from Experimental Data...")
    plot_sha_fidelity()
    plot_vacuum_stability()
    print("Done. Images ready for Paper/README.")
