# signal_monitor.py - MONITORAMENTO CORRETO DOS SINAIS

"""
Sistema de monitoramento correto dos sinais ativos
Um sinal só deixa de ser ativo quando:
1. Atinge STOP LOSS (perdedor)
2. Atinge TARGET 3 (completamente realizado)
"""

import sqlite3
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

from config.settings import settings
from core.data_reader import DataReader

class SignalStatusMonitor:
    """Monitor que verifica se sinais ativos atingiram stop ou target final"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db_path = settings.database.signals_db_path
        self.signals_table = settings.database.signals_table
        self.data_reader = DataReader()
        
        # Estados possíveis dos sinais
        self.SIGNAL_STATES = {
            'ACTIVE': 'Sinal ativo aguardando resultado',
            'TARGET_1_HIT': 'Target 1 atingido, ainda ativo',
            'TARGET_2_HIT': 'Target 2 atingido, ainda ativo', 
            'TARGET_3_HIT': 'Target 3 atingido - SINAL COMPLETO',
            'STOP_HIT': 'Stop loss atingido - SINAL PERDEDOR',
            'EXPIRED': 'Sinal expirado por tempo',
            'MANUALLY_CLOSED': 'Fechado manualmente'
        }
        
        # Sinais que ainda estão "ativos" (não liberam timeframe)
        self.ACTIVE_STATES = ['ACTIVE', 'TARGET_1_HIT', 'TARGET_2_HIT']
        
        # Sinais finalizados (liberam timeframe para novos sinais)
        self.COMPLETED_STATES = ['TARGET_3_HIT', 'STOP_HIT', 'EXPIRED', 'MANUALLY_CLOSED']
        
    def _get_connection(self):
        return sqlite3.connect(self.db_path, timeout=10)
    
    def check_active_signals(self, update_status: bool = True) -> Dict:
        """
        🔍 Verifica todos os sinais ativos e seus status atuais
        """
        sql = f"""
        SELECT 
            id, symbol, timeframe, signal_type, entry_price, stop_loss, targets,
            targets_hit, current_price, status, created_at, updated_at
        FROM {self.signals_table}
        WHERE status IN ('ACTIVE', 'TARGET_1_HIT', 'TARGET_2_HIT')
        ORDER BY created_at DESC
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql)
                results = cursor.fetchall()
            
            if not results:
                return {
                    'total_active_signals': 0,
                    'signals_checked': 0,
                    'signals_updated': 0,
                    'signals': []
                }
            
            signals_data = []
            signals_updated = 0
            
            for row in results:
                signal_info = self._process_signal_row(row)
                
                if signal_info:
                    # Verifica preço atual e status
                    current_status = self._check_signal_status(signal_info)
                    signal_info['calculated_status'] = current_status
                    
                    # Atualiza no banco se necessário e solicitado
                    if update_status and current_status['needs_update']:
                        updated = self._update_signal_status(signal_info, current_status)
                        if updated:
                            signals_updated += 1
                            signal_info['status_updated'] = True
                    
                    signals_data.append(signal_info)
            
            return {
                'total_active_signals': len(signals_data),
                'signals_checked': len(signals_data),
                'signals_updated': signals_updated,
                'signals': signals_data,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar sinais ativos: {e}")
            return {'error': str(e)}
    
    def _process_signal_row(self, row) -> Optional[Dict]:
        """Processa uma linha do banco em estrutura de dados"""
        try:
            return {
                'id': row[0],
                'symbol': row[1],
                'timeframe': row[2],
                'signal_type': row[3],
                'entry_price': float(row[4]),
                'stop_loss': float(row[5]),
                'targets': json.loads(row[6]) if row[6] else [],
                'targets_hit': json.loads(row[7]) if row[7] else [False, False, False],
                'current_price': float(row[8]) if row[8] else row[4],
                'status': row[9],
                'created_at': row[10],
                'updated_at': row[11]
            }
        except Exception as e:
            self.logger.warning(f"Erro ao processar linha do sinal: {e}")
            return None
    
    def _check_signal_status(self, signal_info: Dict) -> Dict:
        """
        🎯 LÓGICA PRINCIPAL: Verifica o status correto do sinal
        """
        try:
            # Busca preço atual do mercado
            current_market_price = self._get_current_market_price(
                signal_info['symbol'], signal_info['timeframe']
            )
            
            if current_market_price is None:
                return {
                    'new_status': signal_info['status'],
                    'needs_update': False,
                    'reason': 'Preço de mercado indisponível',
                    'current_price': signal_info['current_price']
                }
            
            # Verifica se stop loss foi atingido
            stop_hit = self._check_stop_loss_hit(signal_info, current_market_price)
            if stop_hit:
                return {
                    'new_status': 'STOP_HIT',
                    'needs_update': True,
                    'reason': f'Stop loss atingido: {current_market_price:.4f} vs {signal_info["stop_loss"]:.4f}',
                    'current_price': current_market_price,
                    'final_result': 'LOSS'
                }
            
            # Verifica targets atingidos
            targets_status = self._check_targets_hit(signal_info, current_market_price)
            
            if targets_status['target_3_hit']:
                return {
                    'new_status': 'TARGET_3_HIT',
                    'needs_update': True,
                    'reason': f'Target 3 atingido: {current_market_price:.4f} vs {signal_info["targets"][2]:.4f}',
                    'current_price': current_market_price,
                    'targets_hit': [True, True, True],
                    'final_result': 'WIN_COMPLETE'
                }
            
            elif targets_status['target_2_hit'] and signal_info['status'] != 'TARGET_2_HIT':
                return {
                    'new_status': 'TARGET_2_HIT',
                    'needs_update': True,
                    'reason': f'Target 2 atingido: {current_market_price:.4f} vs {signal_info["targets"][1]:.4f}',
                    'current_price': current_market_price,
                    'targets_hit': [True, True, False],
                    'partial_result': 'WIN_PARTIAL_2'
                }
            
            elif targets_status['target_1_hit'] and signal_info['status'] != 'TARGET_1_HIT':
                return {
                    'new_status': 'TARGET_1_HIT',
                    'needs_update': True,
                    'reason': f'Target 1 atingido: {current_market_price:.4f} vs {signal_info["targets"][0]:.4f}',
                    'current_price': current_market_price,
                    'targets_hit': [True, False, False],
                    'partial_result': 'WIN_PARTIAL_1'
                }
            
            # Verifica se sinal expirou (mais de 7 dias)
            signal_age = datetime.now() - datetime.fromisoformat(signal_info['created_at'])
            if signal_age.days > 7:
                return {
                    'new_status': 'EXPIRED',
                    'needs_update': True,
                    'reason': f'Sinal expirado após {signal_age.days} dias',
                    'current_price': current_market_price,
                    'final_result': 'EXPIRED'
                }
            
            # Sinal ainda ativo, apenas atualiza preço
            price_needs_update = abs(current_market_price - signal_info['current_price']) / signal_info['current_price'] > 0.001
            
            return {
                'new_status': signal_info['status'],
                'needs_update': price_needs_update,
                'reason': 'Sinal ainda ativo, atualizando preço' if price_needs_update else 'Sinal ativo, sem mudanças',
                'current_price': current_market_price
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar status do sinal {signal_info['id']}: {e}")
            return {
                'new_status': signal_info['status'],
                'needs_update': False,
                'reason': f'Erro na verificação: {e}',
                'current_price': signal_info['current_price']
            }
    
    def _get_current_market_price(self, symbol: str, timeframe: str) -> Optional[float]:
        """Busca preço atual do mercado"""
        try:
            market_data = self.data_reader.get_latest_data(symbol, timeframe)
            if market_data and not market_data.data.empty:
                return float(market_data.data['close_price'].iloc[-1])
            return None
        except Exception as e:
            self.logger.warning(f"Erro ao buscar preço atual de {symbol}: {e}")
            return None
    
    def _check_stop_loss_hit(self, signal_info: Dict, current_price: float) -> bool:
        """Verifica se stop loss foi atingido"""
        stop_loss = signal_info['stop_loss']
        signal_type = signal_info['signal_type']
        
        if signal_type == 'BUY_LONG':
            # Para LONG: stop hit se preço atual <= stop loss
            return current_price <= stop_loss
        else:  # SELL_SHORT
            # Para SHORT: stop hit se preço atual >= stop loss
            return current_price >= stop_loss
    
    def _check_targets_hit(self, signal_info: Dict, current_price: float) -> Dict:
        """Verifica quais targets foram atingidos"""
        targets = signal_info['targets']
        signal_type = signal_info['signal_type']
        
        if len(targets) < 3:
            return {'target_1_hit': False, 'target_2_hit': False, 'target_3_hit': False}
        
        if signal_type == 'BUY_LONG':
            # Para LONG: targets são atingidos quando preço >= target
            target_1_hit = current_price >= targets[0]
            target_2_hit = current_price >= targets[1]
            target_3_hit = current_price >= targets[2]
        else:  # SELL_SHORT
            # Para SHORT: targets são atingidos quando preço <= target
            target_1_hit = current_price <= targets[0]
            target_2_hit = current_price <= targets[1]
            target_3_hit = current_price <= targets[2]
        
        return {
            'target_1_hit': target_1_hit,
            'target_2_hit': target_2_hit,
            'target_3_hit': target_3_hit
        }
    
    def _update_signal_status(self, signal_info: Dict, status_result: Dict) -> bool:
        """Atualiza status do sinal no banco de dados"""
        try:
            updates = {
                'status': status_result['new_status'],
                'current_price': status_result['current_price'],
                'updated_at': datetime.now().isoformat()
            }
            
            # Atualiza targets_hit se fornecido
            if 'targets_hit' in status_result:
                updates['targets_hit'] = json.dumps(status_result['targets_hit'])
            
            # Monta SQL dinâmica
            set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
            values = list(updates.values()) + [signal_info['id']]
            
            sql = f"""
            UPDATE {self.signals_table}
            SET {set_clause}
            WHERE id = ?
            """
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, values)
                conn.commit()
            
            # Log da atualização
            final_result = status_result.get('final_result', '')
            if final_result:
                result_icon = "🎯" if "WIN" in final_result else "🛑" if final_result == "LOSS" else "⏰"
                self.logger.info(
                    f"{result_icon} SINAL FINALIZADO: {signal_info['symbol']} {signal_info['timeframe']} | "
                    f"Status: {status_result['new_status']} | "
                    f"Preço: {status_result['current_price']:.4f} | "
                    f"Resultado: {final_result}"
                )
            else:
                self.logger.debug(
                    f"📊 SINAL ATUALIZADO: {signal_info['symbol']} {signal_info['timeframe']} | "
                    f"Status: {status_result['new_status']} | "
                    f"Preço: {status_result['current_price']:.4f}"
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao atualizar status do sinal {signal_info['id']}: {e}")
            return False
    
    def get_truly_active_signals(self) -> Dict:
        """
        🎯 Retorna apenas sinais que REALMENTE estão ativos (bloqueiam timeframe)
        """
        # Estados que bloqueiam o timeframe para novos sinais
        active_states_str = "', '".join(self.ACTIVE_STATES)
        
        sql = f"""
        SELECT symbol, timeframe, COUNT(*) as count, 
               GROUP_CONCAT(status) as statuses,
               GROUP_CONCAT(id) as signal_ids
        FROM {self.signals_table}
        WHERE status IN ('{active_states_str}')
        GROUP BY symbol, timeframe
        ORDER BY symbol, timeframe
        """
        
        try:
            with self._get_connection() as conn:
                df = pd.read_sql_query(sql, conn)
            
            if df.empty:
                return {
                    'total_blocking_signals': 0,
                    'symbols_with_blocking_signals': 0,
                    'by_symbol': {},
                    'by_timeframe': {},
                    'blocking_combinations': []
                }
            
            # Agrupa por symbol
            by_symbol = {}
            for symbol, group in df.groupby('symbol'):
                by_symbol[symbol] = {
                    'timeframes_blocked': group['timeframe'].tolist(),
                    'total_blocking': int(group['count'].sum())
                }
            
            # Agrupa por timeframe
            by_timeframe = df.groupby('timeframe')['count'].sum().to_dict()
            
            # Lista de combinações bloqueadas
            blocking_combinations = []
            for _, row in df.iterrows():
                blocking_combinations.append({
                    'symbol': row['symbol'],
                    'timeframe': row['timeframe'],
                    'count': int(row['count']),
                    'statuses': row['statuses'].split(','),
                    'signal_ids': row['signal_ids'].split(',')
                })
            
            return {
                'total_blocking_signals': int(df['count'].sum()),
                'symbols_with_blocking_signals': len(by_symbol),
                'by_symbol': by_symbol,
                'by_timeframe': by_timeframe,
                'blocking_combinations': blocking_combinations
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar sinais verdadeiramente ativos: {e}")
            return {'error': str(e)}
    
    def manually_close_signal(self, signal_id: str, reason: str = "manual_close") -> bool:
        """Fecha um sinal manualmente"""
        sql = f"""
        UPDATE {self.signals_table}
        SET status = 'MANUALLY_CLOSED', updated_at = ?
        WHERE id = ? AND status IN ('ACTIVE', 'TARGET_1_HIT', 'TARGET_2_HIT')
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (datetime.now().isoformat(), signal_id))
                affected_rows = cursor.rowcount
                conn.commit()
            
            if affected_rows > 0:
                self.logger.info(f"🔴 SINAL FECHADO MANUALMENTE: {signal_id} | Motivo: {reason}")
                return True
            else:
                self.logger.warning(f"⚠️ Sinal não encontrado ou já finalizado: {signal_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao fechar sinal manualmente {signal_id}: {e}")
            return False
    
    def cleanup_completed_signals(self, days_old: int = 30) -> int:
        """Remove sinais completados muito antigos do banco"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        completed_states_str = "', '".join(self.COMPLETED_STATES)
        
        sql = f"""
        DELETE FROM {self.signals_table}
        WHERE status IN ('{completed_states_str}') 
        AND datetime(updated_at) < ?
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (cutoff_date.isoformat(),))
                deleted_count = cursor.rowcount
                conn.commit()
            
            if deleted_count > 0:
                self.logger.info(f"🗑️ {deleted_count} sinais completados antigos removidos (>{days_old} dias)")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Erro ao limpar sinais completados: {e}")
            return 0

def print_signal_monitoring_report():
    """🖨️ Função utilitária para imprimir relatório de monitoramento"""
    monitor = SignalStatusMonitor()
    
    print("\n📊 RELATÓRIO DE MONITORAMENTO DE SINAIS")
    print("=" * 70)
    
    # Verifica e atualiza status
    print("🔍 Verificando status dos sinais ativos...")
    results = monitor.check_active_signals(update_status=True)
    
    if 'error' in results:
        print(f"❌ Erro: {results['error']}")
        return
    
    print(f"✅ {results['signals_checked']} sinais verificados")
    print(f"📝 {results['signals_updated']} sinais atualizados")
    
    if results['total_active_signals'] == 0:
        print("\n🎉 Nenhum sinal ativo - todos os timeframes disponíveis!")
        return
    
    # Mostra sinais por status
    status_counts = {}
    for signal in results['signals']:
        status = signal.get('calculated_status', {}).get('new_status', signal['status'])
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print(f"\n📈 DISTRIBUIÇÃO POR STATUS:")
    for status, count in sorted(status_counts.items()):
        print(f"  • {status}: {count} sinais")
    
    # Sinais que liberam timeframes
    blocking_info = monitor.get_truly_active_signals()
    
    print(f"\n🚫 TIMEFRAMES BLOQUEADOS:")
    print(f"  Total de bloqueios: {blocking_info['total_blocking_signals']}")
    print(f"  Symbols afetados: {blocking_info['symbols_with_blocking_signals']}")
    
    for combo in blocking_info['blocking_combinations'][:10]:  # Mostra primeiros 10
        statuses_str = ', '.join(set(combo['statuses']))
        print(f"  • {combo['symbol']} {combo['timeframe']}: {combo['count']} sinal(s) ({statuses_str})")
    
    # Estatísticas gerais
    wins = len([s for s in results['signals'] if s.get('calculated_status', {}).get('final_result', '').startswith('WIN')])
    losses = len([s for s in results['signals'] if s.get('calculated_status', {}).get('final_result') == 'LOSS'])
    
    if wins + losses > 0:
        win_rate = wins / (wins + losses) * 100
        print(f"\n🎯 PERFORMANCE:")
        print(f"  • Wins: {wins} | Losses: {losses}")
        print(f"  • Win Rate: {win_rate:.1f}%")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        print_signal_monitoring_report()
    else:
        monitor = SignalStatusMonitor()
        results = monitor.check_active_signals(update_status=True)
        print(f"Verificados: {results.get('signals_checked', 0)} | Atualizados: {results.get('signals_updated', 0)}")