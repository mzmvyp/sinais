#!/usr/bin/env python3
# real_time_signal_monitor.py - MONITORAMENTO EM TEMPO REAL DOS SINAIS

"""
Monitor em tempo real que:
1. Verifica preços a cada 1 minuto 
2. Atualiza status: ACTIVE → TARGET_1_HIT → TARGET_2_HIT/STOP_HIT
3. Funciona como serviço contínuo
4. Logs detalhados de todas as transições
"""

import sys
import os
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import sqlite3

# Adiciona o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.signal_monitor import SignalStatusMonitor
from core.data_reader import DataReader
from config.settings import settings

class RealTimeSignalMonitor:
    """Monitor de sinais em tempo real - Atualiza status automaticamente"""
    
    def __init__(self, check_interval: int = 60):
        self.logger = logging.getLogger(__name__)
        self.signal_monitor = SignalStatusMonitor()
        self.data_reader = DataReader()
        self.check_interval = check_interval  # segundos
        
        # Controle de execução
        self.running = False
        self.monitor_thread = None
        
        # Estatísticas
        self.total_checks = 0
        self.total_updates = 0
        self.transitions_detected = 0
        self.start_time = None
        
        # Cache de última verificação para evitar spam
        self.last_check_results = {}
        
        self.logger.info(f"🔄 RealTimeSignalMonitor inicializado (intervalo: {check_interval}s)")
    
    def start_monitoring(self):
        """Inicia o monitoramento em tempo real como thread"""
        if self.running:
            self.logger.warning("Monitor já está em execução")
            return
        
        self.running = True
        self.start_time = datetime.now()
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info(f"🚀 MONITORAMENTO EM TEMPO REAL INICIADO")
        self.logger.info(f"⏱️ Verificando sinais a cada {self.check_interval} segundos")
        self.logger.info(f"🎯 Atualizando: ACTIVE → TARGET_1_HIT → TARGET_2_HIT/STOP_HIT")
    
    def stop_monitoring(self):
        """Para o monitoramento"""
        if not self.running:
            return
        
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        uptime = datetime.now() - self.start_time if self.start_time else timedelta()
        
        self.logger.info(f"🛑 MONITORAMENTO INTERROMPIDO")
        self.logger.info(f"⏱️ Tempo ativo: {self._format_timedelta(uptime)}")
        self.logger.info(f"📊 Estatísticas: {self.total_checks} verificações | {self.total_updates} atualizações | {self.transitions_detected} transições")
    
    def _monitoring_loop(self):
        """Loop principal de monitoramento"""
        self.logger.info("🔄 Loop de monitoramento iniciado")
        
        while self.running:
            try:
                start_time = time.time()
                
                # Verifica e atualiza sinais ativos
                results = self.signal_monitor.check_active_signals(update_status=True)
                
                if 'error' not in results:
                    self.total_checks += 1
                    updates_this_cycle = results.get('signals_updated', 0)
                    self.total_updates += updates_this_cycle
                    
                    # Detecta transições
                    transitions = self._detect_status_transitions(results.get('signals', []))
                    self.transitions_detected += len(transitions)
                    
                    # Log resumido a cada verificação
                    active_count = results.get('total_active_signals', 0)
                    execution_time = time.time() - start_time
                    
                    if updates_this_cycle > 0 or transitions:
                        # Log detalhado se houve mudanças
                        self.logger.info(
                            f"🔄 Ciclo #{self.total_checks}: {active_count} ativos | "
                            f"{updates_this_cycle} atualizações | {len(transitions)} transições | "
                            f"{execution_time:.2f}s"
                        )
                        
                        # Log das transições
                        for transition in transitions:
                            self._log_transition(transition)
                    else:
                        # Log simplificado se não houve mudanças
                        self.logger.debug(
                            f"🔄 Ciclo #{self.total_checks}: {active_count} ativos | "
                            f"sem mudanças | {execution_time:.2f}s"
                        )
                    
                    # A cada 60 ciclos (1 hora se intervalo = 60s), mostra estatísticas
                    if self.total_checks % 60 == 0:
                        self._log_periodic_statistics()
                        
                else:
                    self.logger.error(f"❌ Erro no monitoramento: {results['error']}")
                
                # Aguarda próximo ciclo
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"❌ Erro crítico no loop de monitoramento: {e}")
                time.sleep(self.check_interval)  # Continua mesmo com erro
    
    def _detect_status_transitions(self, current_signals: List[Dict]) -> List[Dict]:
        """Detecta mudanças de status desde a última verificação"""
        transitions = []
        current_state = {}
        
        # Mapeia estado atual
        for signal in current_signals:
            signal_id = signal['id']
            calculated_status = signal.get('calculated_status', {})
            new_status = calculated_status.get('new_status', signal['status'])
            
            current_state[signal_id] = {
                'symbol': signal['symbol'],
                'timeframe': signal['timeframe'],
                'status': new_status,
                'reason': calculated_status.get('reason', ''),
                'priority': calculated_status.get('priority', 'low')
            }
        
        # Compara com estado anterior
        for signal_id, current in current_state.items():
            if signal_id in self.last_check_results:
                last = self.last_check_results[signal_id]
                
                if last['status'] != current['status']:
                    # Detectou transição!
                    transition = {
                        'signal_id': signal_id,
                        'symbol': current['symbol'],
                        'timeframe': current['timeframe'],
                        'old_status': last['status'],
                        'new_status': current['status'],
                        'reason': current['reason'],
                        'priority': current['priority'],
                        'timestamp': datetime.now().isoformat()
                    }
                    transitions.append(transition)
        
        # Atualiza estado para próxima verificação
        self.last_check_results = current_state
        
        return transitions
    
    def _log_transition(self, transition: Dict):
        """Log detalhado de uma transição de status"""
        symbol = transition['symbol']
        timeframe = transition['timeframe']
        old_status = transition['old_status']
        new_status = transition['new_status']
        reason = transition['reason']
        priority = transition['priority']
        
        # Ícones baseados na transição
        if new_status == 'TARGET_1_HIT':
            icon = "🎯"
            level = logging.INFO
            message = f"TARGET 1 ATINGIDO: {symbol} {timeframe} | {old_status} → {new_status}"
        elif new_status == 'TARGET_2_HIT':
            icon = "🏆"
            level = logging.INFO
            message = f"TARGET 2 ATINGIDO - SUCESSO: {symbol} {timeframe} | {old_status} → {new_status}"
        elif new_status == 'STOP_HIT':
            icon = "🛑"
            level = logging.INFO
            message = f"STOP LOSS ATINGIDO: {symbol} {timeframe} | {old_status} → {new_status}"
        elif new_status == 'EXPIRED':
            icon = "⏰"
            level = logging.WARNING
            message = f"SINAL EXPIRADO: {symbol} {timeframe} | {old_status} → {new_status}"
        else:
            icon = "🔄"
            level = logging.INFO
            message = f"TRANSIÇÃO: {symbol} {timeframe} | {old_status} → {new_status}"
        
        # Adiciona motivo se disponível
        if reason:
            message += f" | Motivo: {reason}"
        
        self.logger.log(level, f"{icon} {message}")
    
    def _log_periodic_statistics(self):
        """Log de estatísticas periódicas"""
        uptime = datetime.now() - self.start_time if self.start_time else timedelta()
        
        # Busca resumo atual dos sinais
        try:
            blocking_info = self.signal_monitor.get_truly_active_signals()
            monitoring_stats = self.signal_monitor.get_monitoring_statistics()
            
            self.logger.info(f"📊 ESTATÍSTICAS HORÁRIAS:")
            self.logger.info(f"   ⏱️ Uptime: {self._format_timedelta(uptime)}")
            self.logger.info(f"   🔄 Verificações: {self.total_checks}")
            self.logger.info(f"   📝 Atualizações: {self.total_updates}")
            self.logger.info(f"   🔄 Transições: {self.transitions_detected}")
            self.logger.info(f"   🚫 Sinais bloqueando: {blocking_info.get('total_blocking_signals', 0)}")
            
            if 'summary' in monitoring_stats:
                summary = monitoring_stats['summary']
                win_rate = summary.get('overall_win_rate', 0)
                if win_rate > 0:
                    self.logger.info(f"   🎯 Win Rate geral: {win_rate:.1f}%")
                    
        except Exception as e:
            self.logger.warning(f"Erro ao obter estatísticas: {e}")
    
    def _format_timedelta(self, td):
        """Formata timedelta de forma legível"""
        total_seconds = int(td.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def get_monitoring_status(self) -> Dict:
        """Retorna status atual do monitoramento"""
        return {
            'running': self.running,
            'check_interval': self.check_interval,
            'total_checks': self.total_checks,
            'total_updates': self.total_updates,
            'transitions_detected': self.transitions_detected,
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            'start_time': self.start_time.isoformat() if self.start_time else None
        }
    
    def force_check_now(self) -> Dict:
        """Força uma verificação imediata"""
        self.logger.info("🔄 Verificação forçada solicitada")
        
        try:
            results = self.signal_monitor.check_active_signals(update_status=True)
            
            if 'error' not in results:
                self.total_checks += 1
                updates = results.get('signals_updated', 0)
                self.total_updates += updates
                
                transitions = self._detect_status_transitions(results.get('signals', []))
                self.transitions_detected += len(transitions)
                
                for transition in transitions:
                    self._log_transition(transition)
                
                return {
                    'status': 'success',
                    'signals_checked': results.get('signals_checked', 0),
                    'signals_updated': updates,
                    'transitions_detected': len(transitions)
                }
            else:
                return {'status': 'error', 'message': results['error']}
                
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

class RealTimeMonitorService:
    """Serviço de monitoramento que pode ser controlado externamente"""
    
    def __init__(self):
        self.monitor = None
        self.logger = logging.getLogger(__name__)
    
    def start_service(self, check_interval: int = 60):
        """Inicia o serviço de monitoramento"""
        if self.monitor and self.monitor.running:
            return {'status': 'already_running'}
        
        self.monitor = RealTimeSignalMonitor(check_interval)
        self.monitor.start_monitoring()
        
        return {
            'status': 'started',
            'check_interval': check_interval,
            'message': f'Monitoramento iniciado com intervalo de {check_interval}s'
        }
    
    def stop_service(self):
        """Para o serviço de monitoramento"""
        if not self.monitor or not self.monitor.running:
            return {'status': 'not_running'}
        
        self.monitor.stop_monitoring()
        
        return {
            'status': 'stopped',
            'message': 'Monitoramento interrompido'
        }
    
    def get_status(self):
        """Retorna status do serviço"""
        if not self.monitor:
            return {'status': 'not_initialized'}
        
        return self.monitor.get_monitoring_status()
    
    def force_check(self):
        """Força verificação imediata"""
        if not self.monitor or not self.monitor.running:
            return {'status': 'not_running'}
        
        return self.monitor.force_check_now()

# Instância global do serviço
monitor_service = RealTimeMonitorService()

def start_real_time_monitoring(check_interval: int = 60):
    """Função de conveniência para iniciar monitoramento"""
    return monitor_service.start_service(check_interval)

def stop_real_time_monitoring():
    """Função de conveniência para parar monitoramento"""
    return monitor_service.stop_service()

def get_monitoring_status():
    """Função de conveniência para obter status"""
    return monitor_service.get_status()

def force_signals_check():
    """Função de conveniência para forçar verificação"""
    return monitor_service.force_check()

def main():
    """Execução standalone do monitor"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor de Sinais em Tempo Real")
    parser.add_argument('--interval', type=int, default=60,
                       help='Intervalo de verificação em segundos (padrão: 60)')
    parser.add_argument('--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Nível de log')
    
    args = parser.parse_args()
    
    # Configura logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('real_time_monitor.log')
        ]
    )
    
    print(f"🚀 INICIANDO MONITOR EM TEMPO REAL")
    print(f"⏱️ Intervalo: {args.interval} segundos")
    print(f"📊 Log level: {args.log_level}")
    print(f"🎯 Atualizando status: ACTIVE → TARGET_1_HIT → TARGET_2_HIT/STOP_HIT")
    print(f"Pressione Ctrl+C para parar\n")
    
    try:
        monitor = RealTimeSignalMonitor(args.interval)
        monitor.start_monitoring()
        
        # Mantém o programa rodando
        while monitor.running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Interrompido pelo usuário")
        if 'monitor' in locals():
            monitor.stop_monitoring()
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        if 'monitor' in locals():
            monitor.stop_monitoring()

if __name__ == "__main__":
    main()