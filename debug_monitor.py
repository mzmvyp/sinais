#!/usr/bin/env python3
# debug_monitor.py - Monitor de debug em tempo real

import time
import sys
from datetime import datetime

def monitor_system():
    """Monitora o sistema em tempo real"""
    print("🔍 MONITOR DE DEBUG EM TEMPO REAL")
    print("=" * 50)
    print("⏱️ Inicia monitoramento...")
    
    cycle_count = 0
    
    while True:
        try:
            cycle_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Verifica se sistema ainda está rodando
            try:
                # Aqui poderia verificar logs, processos, etc
                status = "🟢 RODANDO"
            except:
                status = "🔴 PARADO"
            
            print(f"[{timestamp}] Monitor {cycle_count}: {status}")
            
            # Heartbeat a cada 30s
            time.sleep(30)
            
        except KeyboardInterrupt:
            print(f"\n🛑 Monitor interrompido")
            break
        except Exception as e:
            print(f"❌ Erro no monitor: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor_system()
