# progress_monitor.py - Monitor de progresso em tempo real

import time
import threading
from datetime import datetime

class ProgressMonitor:
    def __init__(self):
        self.current_symbol = None
        self.current_timeframe = None
        self.start_time = None
        self.warning_time = 5  # Avisa após 5s
        self.timeout_time = 10  # Timeout após 10s
        self._monitor_thread = None
        self._stop_monitor = False
    
    def start_monitoring(self, symbol: str, timeframe: str = None):
        """Inicia monitoramento de um símbolo"""
        self.current_symbol = symbol
        self.current_timeframe = timeframe
        self.start_time = time.time()
        self._stop_monitor = False
        
        # Thread de monitoramento
        self._monitor_thread = threading.Thread(target=self._monitor_progress, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Para o monitoramento"""
        self._stop_monitor = True
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1)
    
    def _monitor_progress(self):
        """Thread que monitora progresso"""
        while not self._stop_monitor and self.start_time:
            elapsed = time.time() - self.start_time
            
            if elapsed > self.warning_time:
                symbol_info = f"{self.current_symbol}"
                if self.current_timeframe:
                    symbol_info += f" {self.current_timeframe}"
                    
                print(f"⏰ AVISO: {symbol_info} está demorando {elapsed:.1f}s")
                self.warning_time += 5  # Próximo aviso em 5s
            
            if elapsed > self.timeout_time:
                print(f"🚨 TIMEOUT: {self.current_symbol} excedeu {self.timeout_time}s - FORÇANDO PARADA")
                # Aqui poderia forçar uma interrupção se necessário
                break
                
            time.sleep(0.5)

# Monitor global
progress_monitor = ProgressMonitor()
