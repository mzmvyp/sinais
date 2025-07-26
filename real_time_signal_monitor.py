#!/usr/bin/env python3
# real_time_signal_monitor_corrected.py - MONITOR CORRIGIDO COM DADOS LOCAIS

"""
Monitor em tempo real CORRIGIDO que:
1. Usa dados da tabela kline_microstructure_1m para current_price
2. Banco correto: crypto_stream.db
3. Lógica: filtra por símbolo e pega MAX close como current_price
4. Atualiza status: ACTIVE → TARGET_1_HIT → TARGET_2_HIT/STOP_HIT
5. NÃO usa APIs externas para preços
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
import traceback
import argparse

class CorrectedSignalMonitor:
    """Monitor de sinais corrigido - usa dados locais do crypto_stream.db"""
    
    def __init__(self, check_interval: int = 60):
        self._setup_logging()
        
        self.logger = logging.getLogger(__name__)
        self.check_interval = check_interval
        
        # Controle de execução
        self.running = False
        self.monitor_thread = None
        
        # Estatísticas
        self.total_checks = 0
        self.total_updates = 0
        self.transitions_detected = 0
        self.price_updates_success = 0
        self.price_updates_failed = 0
        self.start_time = None
        
        # BANCOS DE DADOS CORRETOS
        self.stream_db_path = r"C:\Users\mzmvy\Documents\python\trading_system\data\crypto_stream.db"
        self.signals_db_path = r"C:\Users\mzmvy\Documents\python\trading_system\data\trading_analyzer_v2.db"
        
        # Cache de última verificação para detectar transições
        self.last_check_results = {}
        
        self.logger.info(f"🔄 Monitor Corrigido inicializado (intervalo: {check_interval}s)")
        self.logger.info(f"📊 Stream DB: {self.stream_db_path}")
        self.logger.info(f"📊 Signals DB: {self.signals_db_path}")
    
    def _setup_logging(self):
        """Configuração de logging"""
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler para arquivo
        try:
            file_handler = logging.FileHandler('monitor_corrected.log', encoding='utf-8')
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.INFO)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Erro ao configurar log de arquivo: {e}")
        
        # Handler para console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)
        
        logger.setLevel(logging.INFO)
    
    def start_monitoring(self):
        """Inicia monitoramento"""
        if self.running:
            self.logger.warning("Monitor já está em execução")
            return
        
        # Verifica bancos de dados
        if not self._check_databases():
            self.logger.error("❌ Problemas com bancos de dados")
            return False
        
        self.running = True
        self.start_time = datetime.now()
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info(f"🚀 MONITOR CORRIGIDO INICIADO")
        self.logger.info(f"⏱️ Intervalo: {self.check_interval}s")
        self.logger.info(f"🎯 Usando dados locais da tabela kline_microstructure_1m")
        
        return True
    
    def _check_databases(self) -> bool:
        """Verifica conectividade com ambos os bancos"""
        try:
            # Verifica banco de stream
            if not os.path.exists(self.stream_db_path):
                self.logger.error(f"❌ Banco de stream não encontrado: {self.stream_db_path}")
                return False
            
            conn_stream = sqlite3.connect(self.stream_db_path)
            cursor_stream = conn_stream.cursor()
            
            # Verifica tabela kline_microstructure_1m
            cursor_stream.execute("SELECT COUNT(*) FROM kline_microstructure_1m")
            stream_count = cursor_stream.fetchone()[0]
            
            # Verifica símbolos disponíveis
            cursor_stream.execute("SELECT DISTINCT symbol FROM kline_microstructure_1m ORDER BY symbol")
            available_symbols = [row[0] for row in cursor_stream.fetchall()]
            
            conn_stream.close()
            
            # Verifica banco de sinais
            if not os.path.exists(self.signals_db_path):
                self.logger.error(f"❌ Banco de sinais não encontrado: {self.signals_db_path}")
                return False
            
            conn_signals = sqlite3.connect(self.signals_db_path)
            cursor_signals = conn_signals.cursor()
            
            cursor_signals.execute("SELECT COUNT(*) FROM trading_signals_v2")
            signals_count = cursor_signals.fetchone()[0]
            
            cursor_signals.execute("SELECT COUNT(*) FROM trading_signals_v2 WHERE status = 'ACTIVE'")
            active_signals_count = cursor_signals.fetchone()[0]
            
            conn_signals.close()
            
            self.logger.info(f"📊 Stream DB: {stream_count} registros kline")
            self.logger.info(f"📊 Símbolos disponíveis: {len(available_symbols)} -> {available_symbols}")
            self.logger.info(f"📊 Signals DB: {signals_count} sinais total, {active_signals_count} ativos")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao verificar bancos: {e}")
            return False
    
    def _get_current_price_from_kline(self, symbol: str) -> Optional[float]:
        """
        MÉTODO CORRIGIDO: Obtém current_price da tabela kline_microstructure_1m
        Filtra por símbolo e pega o close mais recente
        """
        try:
            conn = sqlite3.connect(self.stream_db_path)
            cursor = conn.cursor()
            
            # Busca o close mais recente para o símbolo
            cursor.execute("""
                SELECT close, timestamp_end 
                FROM kline_microstructure_1m 
                WHERE symbol = ? 
                ORDER BY timestamp_end DESC 
                LIMIT 1
            """, (symbol,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                close_price = float(result[0])
                timestamp_end = result[1]
                
                self.logger.debug(f"📊 {symbol}: Último close = {close_price:.6f} (timestamp: {timestamp_end})")
                return close_price
            else:
                self.logger.warning(f"⚠️ Nenhum dado encontrado para {symbol} na tabela kline_microstructure_1m")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao buscar preço de {symbol}: {e}")
            return None
    
    def _get_active_signals(self) -> List[Dict]:
        """Obtém sinais ativos do banco de sinais"""
        try:
            conn = sqlite3.connect(self.signals_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, symbol, signal_type, entry_price, current_price, 
                       targets, stop_loss, created_at, status, updated_at
                FROM trading_signals_v2 
                WHERE status = 'ACTIVE'
                ORDER BY created_at DESC
            """)
            
            signals = []
            for row in cursor.fetchall():
                signal_id, symbol, signal_type, entry_price, current_price, targets_json, stop_loss, created_at, status, updated_at = row
                
                # Parse targets
                try:
                    targets = json.loads(targets_json) if targets_json else []
                except:
                    targets = []
                
                signals.append({
                    'id': signal_id,
                    'symbol': symbol,
                    'signal_type': signal_type,
                    'entry_price': float(entry_price),
                    'current_price': float(current_price) if current_price else float(entry_price),
                    'targets': targets,
                    'stop_loss': float(stop_loss),
                    'created_at': created_at,
                    'status': status,
                    'updated_at': updated_at
                })
            
            conn.close()
            return signals
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao buscar sinais ativos: {e}")
            return []
    
    def _monitoring_loop(self):
        """Loop principal do monitoramento"""
        self.logger.info("🔄 Loop de monitoramento iniciado")
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.running:
            try:
                start_time = time.time()
                
                # Obtém sinais ativos
                active_signals = self._get_active_signals()
                
                if not active_signals:
                    self.logger.debug("🔄 Nenhum sinal ativo encontrado")
                    time.sleep(self.check_interval)
                    continue
                
                # Processa cada sinal
                updates_count = 0
                transitions = []
                
                for signal in active_signals:
                    result = self._process_signal_corrected(signal)
                    if result['updated']:
                        updates_count += 1
                    if result['transition']:
                        transitions.append(result['transition'])
                
                self.total_checks += 1
                self.total_updates += updates_count
                self.transitions_detected += len(transitions)
                consecutive_errors = 0
                
                execution_time = time.time() - start_time
                
                # Log das transições
                for transition in transitions:
                    self._log_transition(transition)
                
                # Log do ciclo
                if updates_count > 0 or transitions:
                    self.logger.info(
                        f"🔄 Ciclo #{self.total_checks}: {len(active_signals)} ativos | "
                        f"{updates_count} atualizações | {len(transitions)} transições | "
                        f"{execution_time:.2f}s"
                    )
                else:
                    self.logger.debug(
                        f"🔄 Ciclo #{self.total_checks}: {len(active_signals)} ativos | "
                        f"sem mudanças | {execution_time:.2f}s"
                    )
                
                # Estatísticas periódicas
                if self.total_checks % 60 == 0:
                    self._log_periodic_statistics()
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"❌ Erro no loop #{consecutive_errors}: {e}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                
                if consecutive_errors >= max_consecutive_errors:
                    self.logger.critical(f"❌ MUITOS ERROS CONSECUTIVOS - PARANDO MONITOR")
                    break
                
                time.sleep(min(self.check_interval * 2, 300))
        
        self.logger.info("🛑 Loop de monitoramento finalizado")
    
    def _process_signal_corrected(self, signal: Dict) -> Dict:
        """MÉTODO CORRIGIDO: Processa sinal usando dados locais"""
        result = {'updated': False, 'transition': None}
        
        try:
            symbol = signal['symbol']
            signal_id = signal['id']
            old_status = signal['status']
            old_price = signal['current_price']
            
            # OBTÉM PREÇO ATUAL DA TABELA KLINE_MICROSTRUCTURE_1M
            current_price = self._get_current_price_from_kline(symbol)
            
            if current_price is None:
                self.logger.warning(f"⚠️ Não foi possível obter preço para {symbol}")
                self.price_updates_failed += 1
                return result
            
            # Verifica se preço mudou significativamente (mínimo 0.01%)
            price_change_percent = abs((current_price - old_price) / old_price) * 100
            min_change_percent = 0.01
            
            # Calcula novo status
            new_status = self._calculate_signal_status(signal, current_price)
            
            # Verifica se houve mudança
            price_changed = price_change_percent >= min_change_percent
            status_changed = new_status != old_status
            
            if price_changed or status_changed:
                # Atualiza no banco
                updated = self._update_signal_in_db(signal_id, current_price, new_status)
                
                if updated:
                    result['updated'] = True
                    self.price_updates_success += 1
                    
                    # Log da mudança de preço
                    self.logger.info(
                        f"📈 {symbol}: {old_price:.6f} → {current_price:.6f} "
                        f"({((current_price - old_price) / old_price * 100):+.3f}%)"
                    )
                    
                    # Detecta transição de status
                    if status_changed:
                        result['transition'] = {
                            'signal_id': signal_id,
                            'symbol': symbol,
                            'timeframe': '1m',  # Usando dados de 1 minuto
                            'old_status': old_status,
                            'new_status': new_status,
                            'price': current_price,
                            'reason': self._get_transition_reason(signal, current_price, new_status),
                            'timestamp': datetime.now().isoformat()
                        }
                else:
                    self.price_updates_failed += 1
            else:
                self.logger.debug(f"📊 {symbol}: Sem mudança significativa ({price_change_percent:.3f}%)")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao processar sinal {signal['id']}: {e}")
            self.price_updates_failed += 1
            return result
    
    def _calculate_signal_status(self, signal: Dict, current_price: float) -> str:
        """Calcula status baseado no preço atual"""
        signal_type = signal['signal_type']
        targets = signal['targets']
        stop_loss = signal['stop_loss']
        
        if signal_type in ['BUY_LONG', 'BUY']:
            # Sinais de compra (LONG)
            if current_price <= stop_loss:
                return 'STOP_HIT'
            elif len(targets) >= 2 and current_price >= targets[1]:
                return 'TARGET_2_HIT'
            elif len(targets) >= 1 and current_price >= targets[0]:
                return 'TARGET_1_HIT'
            else:
                return 'ACTIVE'
        
        elif signal_type in ['SELL_SHORT', 'SELL']:
            # Sinais de venda (SHORT)
            if current_price >= stop_loss:
                return 'STOP_HIT'
            elif len(targets) >= 2 and current_price <= targets[1]:
                return 'TARGET_2_HIT'
            elif len(targets) >= 1 and current_price <= targets[0]:
                return 'TARGET_1_HIT'
            else:
                return 'ACTIVE'
        
        return 'ACTIVE'
    
    def _get_transition_reason(self, signal: Dict, current_price: float, new_status: str) -> str:
        """Gera motivo da transição"""
        if new_status == 'TARGET_1_HIT':
            return f"Preço atingiu Target 1: {signal['targets'][0]:.6f}"
        elif new_status == 'TARGET_2_HIT':
            return f"Preço atingiu Target 2: {signal['targets'][1]:.6f}"
        elif new_status == 'STOP_HIT':
            return f"Preço atingiu Stop Loss: {signal['stop_loss']:.6f}"
        else:
            return f"Atualização de preço: {current_price:.6f}"
    
    def _update_signal_in_db(self, signal_id: str, current_price: float, new_status: str) -> bool:
        """Atualiza sinal no banco de dados"""
        try:
            conn = sqlite3.connect(self.signals_db_path)
            cursor = conn.cursor()
            
            if new_status == 'ACTIVE':
                # Apenas atualiza preço
                cursor.execute("""
                    UPDATE trading_signals_v2 
                    SET current_price = ?, updated_at = datetime('now')
                    WHERE id = ?
                """, (current_price, signal_id))
            else:
                # Atualiza preço, status e calcula PnL
                cursor.execute("SELECT entry_price, signal_type FROM trading_signals_v2 WHERE id = ?", (signal_id,))
                result = cursor.fetchone()
                if result:
                    entry_price, signal_type = result
                    pnl_percentage = self._calculate_pnl_percentage(
                        float(entry_price), current_price, signal_type
                    )
                else:
                    pnl_percentage = 0
                
                cursor.execute("""
                    UPDATE trading_signals_v2 
                    SET current_price = ?, status = ?, updated_at = datetime('now'), 
                        exit_time = datetime('now'), pnl_percentage = ?
                    WHERE id = ?
                """, (current_price, new_status, pnl_percentage, signal_id))
            
            conn.commit()
            updated = cursor.rowcount > 0
            conn.close()
            
            if updated:
                self.logger.debug(f"✅ Atualizado {signal_id}: preço={current_price:.6f}, status={new_status}")
            
            return updated
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao atualizar sinal {signal_id}: {e}")
            return False
    
    def _calculate_pnl_percentage(self, entry_price: float, exit_price: float, signal_type: str) -> float:
        """Calcula PnL em porcentagem"""
        try:
            if signal_type in ['BUY_LONG', 'BUY']:
                return ((exit_price - entry_price) / entry_price) * 100
            elif signal_type in ['SELL_SHORT', 'SELL']:
                return ((entry_price - exit_price) / entry_price) * 100
            return 0
        except:
            return 0
    
    def _log_transition(self, transition: Dict):
        """Log detalhado de uma transição de status"""
        symbol = transition['symbol']
        old_status = transition['old_status']
        new_status = transition['new_status']
        price = transition['price']
        reason = transition['reason']
        
        # Ícones baseados na transição
        if new_status == 'TARGET_1_HIT':
            icon = "🎯"
            level = logging.INFO
        elif new_status == 'TARGET_2_HIT':
            icon = "🏆"
            level = logging.INFO
        elif new_status == 'STOP_HIT':
            icon = "🛑"
            level = logging.WARNING
        elif new_status == 'EXPIRED':
            icon = "⏰"
            level = logging.WARNING
        else:
            icon = "🔄"
            level = logging.INFO
        
        message = f"{symbol}: {old_status} → {new_status} | Preço: {price:.6f} | {reason}"
        self.logger.log(level, f"{icon} {message}")
    
    def _log_periodic_statistics(self):
        """Log de estatísticas periódicas"""
        if not self.start_time:
            return
            
        uptime = datetime.now() - self.start_time
        
        try:
            conn = sqlite3.connect(self.signals_db_path)
            cursor = conn.cursor()
            
            # Conta sinais ativos
            cursor.execute("SELECT COUNT(*) FROM trading_signals_v2 WHERE status = 'ACTIVE'")
            active_count = cursor.fetchone()[0]
            
            # Conta transições recentes (última hora)
            one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
            cursor.execute("""
                SELECT COUNT(*) FROM trading_signals_v2 
                WHERE updated_at > ? AND status != 'ACTIVE'
            """, (one_hour_ago,))
            recent_transitions = cursor.fetchone()[0]
            
            conn.close()
            
            # Verifica dados de stream recentes
            conn_stream = sqlite3.connect(self.stream_db_path)
            cursor_stream = conn_stream.cursor()
            
            # Últimos dados de stream (últimos 5 minutos)
            five_min_ago = (datetime.now() - timedelta(minutes=5)).timestamp() * 1000  # em ms
            cursor_stream.execute("""
                SELECT COUNT(DISTINCT symbol) FROM kline_microstructure_1m 
                WHERE timestamp_end > ?
            """, (five_min_ago,))
            recent_symbols = cursor_stream.fetchone()[0]
            
            conn_stream.close()
            
            self.logger.info(f"📊 ESTATÍSTICAS HORÁRIAS:")
            self.logger.info(f"   ⏱️ Uptime: {self._format_timedelta(uptime)}")
            self.logger.info(f"   🔄 Verificações: {self.total_checks}")
            self.logger.info(f"   📝 Atualizações: {self.total_updates}")
            self.logger.info(f"   🔄 Transições: {self.transitions_detected}")
            self.logger.info(f"   🎯 Sinais ativos: {active_count}")
            self.logger.info(f"   ✅ Preços atualizados: {self.price_updates_success}")
            self.logger.info(f"   ❌ Falhas de preço: {self.price_updates_failed}")
            self.logger.info(f"   🆕 Transições recentes: {recent_transitions}")
            self.logger.info(f"   📊 Símbolos com dados recentes: {recent_symbols}")
            
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
    
    def stop_monitoring(self):
        """Para o monitoramento"""
        if not self.running:
            self.logger.info("Monitor já está parado")
            return
        
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        
        uptime = datetime.now() - self.start_time if self.start_time else timedelta()
        
        self.logger.info(f"🛑 MONITOR CORRIGIDO PARADO")
        self.logger.info(f"⏱️ Tempo ativo: {self._format_timedelta(uptime)}")
        self.logger.info(f"📊 Estatísticas finais:")
        self.logger.info(f"   Verificações: {self.total_checks}")
        self.logger.info(f"   Atualizações: {self.total_updates}")
        self.logger.info(f"   Transições: {self.transitions_detected}")
        self.logger.info(f"   Preços atualizados: {self.price_updates_success}")
        self.logger.info(f"   Falhas de preço: {self.price_updates_failed}")
    
    def get_monitoring_status(self) -> Dict:
        """Retorna status atual do monitoramento"""
        return {
            'running': self.running,
            'check_interval': self.check_interval,
            'total_checks': self.total_checks,
            'total_updates': self.total_updates,
            'transitions_detected': self.transitions_detected,
            'price_updates_success': self.price_updates_success,
            'price_updates_failed': self.price_updates_failed,
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            'start_time': self.start_time.isoformat() if self.start_time else None
        }
    
    def force_check_now(self) -> Dict:
        """Força uma verificação imediata"""
        self.logger.info("🔄 VERIFICAÇÃO FORÇADA COM DADOS LOCAIS")
        
        try:
            signals = self._get_active_signals()
            
            if not signals:
                return {'status': 'success', 'message': 'Nenhum sinal ativo encontrado'}
            
            updated_count = 0
            transitions = []
            price_details = []
            
            for signal in signals:
                symbol = signal['symbol']
                old_price = signal['current_price']
                
                # Obtém preço atual da tabela kline
                new_price = self._get_current_price_from_kline(symbol)
                
                detail = {
                    'symbol': symbol,
                    'old_price': old_price,
                    'new_price': new_price,
                    'updated': False
                }
                
                if new_price:
                    result = self._process_signal_corrected(signal)
                    if result['updated']:
                        updated_count += 1
                        detail['updated'] = True
                    if result['transition']:
                        transitions.append(result['transition'])
                
                price_details.append(detail)
            
            # Log das transições
            for transition in transitions:
                self._log_transition(transition)
            
            # Log detalhado dos preços
            self.logger.info("📊 DETALHES DOS PREÇOS (TABELA KLINE):")
            for detail in price_details:
                status = "✅ ATUALIZADO" if detail['updated'] else "📊 SEM MUDANÇA"
                new_price_str = f"{detail['new_price']:.6f}" if detail['new_price'] else "N/A"
                self.logger.info(
                    f"   {detail['symbol']}: {detail['old_price']:.6f} → {new_price_str} | {status}"
                )
            
            self.total_checks += 1
            self.total_updates += updated_count
            self.transitions_detected += len(transitions)
            
            return {
                'status': 'success',
                'signals_checked': len(signals),
                'signals_updated': updated_count,
                'transitions_detected': len(transitions),
                'price_details': price_details,
                'message': f'Verificação concluída: {updated_count}/{len(signals)} atualizados, {len(transitions)} transições'
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def test_price_data_availability(self):
        """Testa disponibilidade de dados de preços"""
        self.logger.info("🔍 TESTANDO DISPONIBILIDADE DE DADOS DE PREÇOS")
        
        try:
            # Verifica símbolos com dados recentes
            conn = sqlite3.connect(self.stream_db_path)
            cursor = conn.cursor()
            
            # Últimos 10 minutos
            ten_min_ago = (datetime.now() - timedelta(minutes=10)).timestamp() * 1000
            
            cursor.execute("""
                SELECT symbol, MAX(timestamp_end) as last_update, close
                FROM kline_microstructure_1m 
                WHERE timestamp_end > ?
                GROUP BY symbol
                ORDER BY symbol
            """, (ten_min_ago,))
            
            recent_data = cursor.fetchall()
            conn.close()
            
            if recent_data:
                self.logger.info(f"📊 {len(recent_data)} símbolos com dados recentes:")
                for symbol, last_update, close in recent_data:
                    last_update_dt = datetime.fromtimestamp(last_update / 1000)
                    self.logger.info(f"   {symbol}: {close:.6f} (atualizado: {last_update_dt})")
            else:
                self.logger.warning("⚠️ Nenhum símbolo com dados recentes encontrado")
            
            # Verifica se há sinais para símbolos com dados
            if recent_data:
                symbols_with_data = [row[0] for row in recent_data]
                
                conn = sqlite3.connect(self.signals_db_path)
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT symbol, COUNT(*) as count
                    FROM trading_signals_v2 
                    WHERE status = 'ACTIVE' AND symbol IN ({})
                    GROUP BY symbol
                """.format(','.join('?' * len(symbols_with_data))), symbols_with_data)
                
                signals_with_data = cursor.fetchall()
                conn.close()
                
                if signals_with_data:
                    self.logger.info(f"🎯 Sinais ativos com dados disponíveis:")
                    for symbol, count in signals_with_data:
                        self.logger.info(f"   {symbol}: {count} sinais")
                else:
                    self.logger.warning("⚠️ Nenhum sinal ativo tem dados de preço disponíveis")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao testar dados: {e}")

def main():
    """Execução principal"""
    parser = argparse.ArgumentParser(description="Monitor de Sinais Corrigido - Dados Locais")
    parser.add_argument('--interval', type=int, default=60, help='Intervalo em segundos')
    parser.add_argument('--force-check', action='store_true', help='Força verificação e sai')
    parser.add_argument('--test-data', action='store_true', help='Testa disponibilidade de dados')
    
    args = parser.parse_args()
    
    print(f"🚀 MONITOR DE SINAIS CORRIGIDO")
    print(f"⏱️ Intervalo: {args.interval} segundos")
    print(f"📊 Usando dados locais da tabela kline_microstructure_1m")
    print("="*60)
    
    try:
        monitor = CorrectedSignalMonitor(args.interval)
        
        if args.test_data:
            monitor.test_price_data_availability()
            return
        
        if args.force_check:
            result = monitor.force_check_now()
            print(f"Resultado: {result}")
            return
        
        if not monitor.start_monitoring():
            print("❌ Falha ao iniciar monitor")
            return
        
        # Menu interativo
        while monitor.running:
            print("\n" + "="*50)
            print("MONITOR CORRIGIDO - MENU")
            print("="*50)
            print("1. Status do monitor")
            print("2. Forçar verificação")
            print("3. Testar dados de preços")
            print("4. Parar monitor")
            print("0. Sair")
            
            try:
                choice = input("\nEscolha uma opção: ").strip()
                
                if choice == '1':
                    status = monitor.get_monitoring_status()
                    print(f"\n📊 STATUS DO MONITOR:")
                    print(f"   Rodando: {'✅ SIM' if status['running'] else '❌ NÃO'}")
                    print(f"   Uptime: {status.get('uptime_seconds', 0)/3600:.1f} horas")
                    print(f"   Verificações: {status['total_checks']}")
                    print(f"   Atualizações: {status['total_updates']}")
                    print(f"   Transições: {status['transitions_detected']}")
                    print(f"   Preços atualizados: {status['price_updates_success']}")
                    print(f"   Falhas de preço: {status['price_updates_failed']}")
                
                elif choice == '2':
                    print("🔄 Forçando verificação...")
                    result = monitor.force_check_now()
                    print(f"Resultado: {result['message']}")
                
                elif choice == '3':
                    monitor.test_price_data_availability()
                
                elif choice == '4':
                    monitor.stop_monitoring()
                    print("🛑 Monitor parado")
                    break
                
                elif choice == '0':
                    break
                
                else:
                    print("❌ Opção inválida")
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Erro: {e}")
            
            if monitor.running:
                input("\nPressione Enter para continuar...")
            
    except KeyboardInterrupt:
        print("\n🛑 Interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        traceback.print_exc()
    finally:
        if 'monitor' in locals():
            monitor.stop_monitoring()

if __name__ == "__main__":
    main()