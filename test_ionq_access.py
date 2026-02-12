
import requests
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_KEY = "r4D4SVDLjDrcGhcMnQiJsInQeCq18DQ8"
HEADERS = {
    "Authorization": f"apiKey {API_KEY}",
    "Content-Type": "application/json"
}

def check_ionq_access():
    print("="*60)
    print("🛸 IONQ QUANTUM ACCESS CHECK")
    print("="*60)
    
    url = "https://api.ionq.co/v0.3/backends"
    
    try:
        print(f"Connecting to {url}...")
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            backends = response.json()
            print(f"\n✅ SUCCESS! Access Granted.")
            print(f"   Credits/Status: {response.status_code}")
            print(f"\n📋 AVAILABLE QUANTUM COMPUTERS:")
            
            for backend in backends: # Backends usually return as a list
                name = backend.get('backend', 'Unknown')
                status = backend.get('status', 'Unknown')
                qubits = backend.get('qubits', '?')
                print(f"   - {name.ljust(15)} | Status: {status} | Qubits: {qubits}")
                
            return True
        else:
            print(f"\n❌ ACCESS DENIED / ERROR")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ CONNECTION ERROR: {e}")
        return False

if __name__ == "__main__":
    check_ionq_access()
