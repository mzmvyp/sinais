# signal_manager.py - UTILITÁRIO DE GERENCIAMENTO DE SINAIS

"""
Utilitário para gerenciar sinais ativos no sistema anti-spam
Permite visualizar, desativar e gerenciar sinais por symbol/timeframe
"""

import json
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

from config.settings import settings
from core.signal_writer import EnhancedSignalWriter

class SignalManager:
    """Gerenciador de sinais ativos - Utilitário administrativo"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.signal_writer = EnhancedSignalWriter()
        self.db_path = settings.database.signals_db_path
        self.signals_table = settings.database.signals_table
        self.backup_table = settings.database.backup_table
        
        self.logger.info("SignalManager inicializado")
    
    def _get_connection(self):
        return sqlite3.connect(self.db_path, timeout=10)
    
    def get_active_signals_overview(self) -> Dict:
        """
        📊 Visão geral completa dos sinais ativos CORRIGIDA
        Considera apenas sinais que REALMENTE bloqueiam timeframes
        """
        # 🚨 CORRIGIDO: Estados que bloqueiam timeframes
        blocking_statuses = ['ACTIVE', 'TARGET_1_HIT', 'TARGET_2_HIT']
        placeholders = ', '.join(['?' for _ in blocking_statuses])
        
        sql = f"""
        SELECT 
            symbol, timeframe, detector_name, signal_type, confidence, 
            entry_price, created_at, status, targets_hit, stop_loss, targets
        FROM {self.signals_table}
        WHERE status IN ({placeholders})
        ORDER BY symbol, timeframe, created_at DESC
        """
        
        try:
            with self._get_connection() as conn:
                df = pd.read_sql_query(sql, conn, params=blocking_statuses)
            
            if df.empty:
                return {
                    'total_active': 0,
                    'symbols_with_signals': 0,
                    'by_symbol': {},
                    'by_timeframe': {},
                    'by_status': {},
                    'signals': []
                }
            
            # Agrupa por symbol
            by_symbol = {}
            for symbol, group in df.groupby('symbol'):
                by_symbol[symbol] = {
                    'total': len(group),
                    'timeframes': group['timeframe'].tolist(),
                    'detectors': group['detector_name'].tolist(),
                    'avg_confidence': round(group['confidence'].mean(), 3),
                    'statuses': group['status'].tolist()
                }
            
            # Agrupa por timeframe
            by_timeframe = df['timeframe'].value_counts().to_dict()
            
            # 🚨 NOVO: Agrupa por status
            by_status = df['status'].value_counts().to_dict()
            
            return {
                'total_active': len(df),
                'symbols_with_signals': len(by_symbol),
                'by_symbol': by_symbol,
                'by_timeframe': by_timeframe,
                'by_status': by_status,  # NOVO
                'signals': df.to_dict('records')
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter visão geral dos sinais: {e}")
            return {'error': str(e)}
    
    def get_signals_by_symbol(self, symbol: str) -> Dict:
        """
        🔍 Detalhes dos sinais de um symbol específico CORRIGIDO
        """
        # 🚨 CORRIGIDO: Estados que bloqueiam timeframes
        blocking_statuses = ['ACTIVE', 'TARGET_1_HIT', 'TARGET_2_HIT']
        placeholders = ', '.join(['?' for _ in blocking_statuses])
        
        sql = f"""
        SELECT 
            id, timeframe, detector_name, signal_type, confidence, 
            entry_price, stop_loss, targets, created_at, status, targets_hit, current_price
        FROM {self.signals_table}
        WHERE symbol = ? AND status IN ({placeholders})
        ORDER BY timeframe, created_at DESC
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, [symbol] + blocking_statuses)
                results = cursor.fetchall()
                
                if not results:
                    return {
                        'symbol': symbol,
                        'active_signals': 0,
                        'signals': [],
                        'blocked_timeframes': [],
                        'available_timeframes': settings.get_enabled_timeframes()
                    }
                
                signals = []
                blocked_timeframes = []
                
                for row in results:
                    # Parse de dados JSON
                    try:
                        targets = json.loads(row[7]) if row[7] else []
                        targets_hit = json.loads(row[10]) if row[10] else [False, False, False]
                    except (json.JSONDecodeError, TypeError):
                        targets = []
                        targets_hit = [False, False, False]
                    
                    signal_data = {
                        'id': row[0],
                        'timeframe': row[1],
                        'detector_name': row[2],
                        'signal_type': row[3],
                        'confidence': row[4],
                        'entry_price': row[5],
                        'stop_loss': row[6],
                        'targets': targets,
                        'created_at': row[8],
                        'status': row[9],
                        'targets_hit': targets_hit,
                        'current_price': row[11],
                        # 🚨 NOVO: Calcula progresso do sinal
                        'progress': self._calculate_signal_progress(targets_hit, row[9])
                    }
                    signals.append(signal_data)
                    blocked_timeframes.append(row[1])
                
                enabled_timeframes = settings.get_enabled_timeframes()
                available_timeframes = [tf for tf in enabled_timeframes if tf not in blocked_timeframes]
                
                return {
                    'symbol': symbol,
                    'active_signals': len(signals),
                    'signals': signals,
                    'blocked_timeframes': blocked_timeframes,
                    'available_timeframes': available_timeframes
                }
                
        except Exception as e:
            self.logger.error(f"Erro ao obter sinais do symbol {symbol}: {e}")
            return {'error': str(e)}
    
    def _calculate_signal_progress(self, targets_hit: List[bool], status: str) -> str:
        """🚨 NOVO: Calcula progresso do sinal"""
        if status == 'TARGET_2_HIT':
            return "TARGET 2/3 ATINGIDO"
        elif status == 'TARGET_1_HIT':
            return "TARGET 1/3 ATINGIDO"
        elif status == 'ACTIVE':
            return "AGUARDANDO RESULTADO"
        else:
            return status
    
    def deactivate_signal_by_id(self, signal_id: str, reason: str = "manual_admin") -> bool:
        """
        🔴 Desativa um sinal específico pelo ID
        """
        sql = f"""
        UPDATE {self.signals_table}
        SET status = 'INACTIVE', updated_at = ?
        WHERE id = ? AND status = 'ACTIVE'
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (datetime.now().isoformat(), signal_id))
                affected_rows = cursor.rowcount
                conn.commit()
                
                if affected_rows > 0:
                    self.logger.info(f"🔴 SINAL DESATIVADO POR ID: {signal_id} | Motivo: {reason}")
                    return True
                else:
                    self.logger.warning(f"⚠️ Sinal não encontrado ou já inativo: {signal_id}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Erro ao desativar sinal {signal_id}: {e}")
            return False
    
    def deactivate_signals_by_symbol(self, symbol: str, timeframe: Optional[str] = None, reason: str = "manual_admin") -> int:
        """
        🔴 Desativa sinais de um symbol CORRIGIDO (apenas sinais que bloqueiam timeframes)
        """
        blocking_statuses = ['ACTIVE', 'TARGET_1_HIT', 'TARGET_2_HIT']
        placeholders = ', '.join(['?' for _ in blocking_statuses])
        
        if timeframe:
            sql = f"""
            UPDATE {self.signals_table}
            SET status = 'MANUALLY_CLOSED', updated_at = ?
            WHERE symbol = ? AND timeframe = ? AND status IN ({placeholders})
            """
            params = [datetime.now().isoformat(), symbol, timeframe] + blocking_statuses
            action_desc = f"{symbol} {timeframe}"
        else:
            sql = f"""
            UPDATE {self.signals_table}
            SET status = 'MANUALLY_CLOSED', updated_at = ?
            WHERE symbol = ? AND status IN ({placeholders})
            """
            params = [datetime.now().isoformat(), symbol] + blocking_statuses
            action_desc = f"{symbol} (todos timeframes)"
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                affected_rows = cursor.rowcount
                conn.commit()
                
                if affected_rows > 0:
                    self.logger.info(f"🔴 {affected_rows} SINAIS DESATIVADOS: {action_desc} | Motivo: {reason}")
                    return affected_rows
                else:
                    self.logger.warning(f"⚠️ Nenhum sinal ativo encontrado para: {action_desc}")
                    return 0
                    
        except Exception as e:
            self.logger.error(f"Erro ao desativar sinais de {action_desc}: {e}")
            return 0
    
    def deactivate_old_signals(self, hours_old: int = 24, reason: str = "auto_cleanup_old") -> int:
        """
        🔴 Desativa sinais mais antigos que X horas
        """
        cutoff_time = datetime.now() - timedelta(hours=hours_old)
        
        sql = f"""
        UPDATE {self.signals_table}
        SET status = 'INACTIVE', updated_at = ?
        WHERE status = 'ACTIVE' AND datetime(created_at) < ?
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (datetime.now().isoformat(), cutoff_time.isoformat()))
                affected_rows = cursor.rowcount
                conn.commit()
                
                if affected_rows > 0:
                    self.logger.info(f"🔴 {affected_rows} SINAIS ANTIGOS DESATIVADOS (>{hours_old}h) | Motivo: {reason}")
                    return affected_rows
                else:
                    self.logger.info(f"✅ Nenhum sinal antigo encontrado (>{hours_old}h)")
                    return 0
                    
        except Exception as e:
            self.logger.error(f"Erro ao desativar sinais antigos: {e}")
            return 0
    
    def get_backup_signals_stats(self, days: int = 1) -> Dict:
        """
        📦 Estatísticas dos sinais enviados para backup
        """
        start_date = datetime.now() - timedelta(days=days)
        
        sql = f"""
        SELECT 
            symbol, timeframe, detector_name, backup_reason,
            COUNT(*) as count,
            AVG(confidence) as avg_confidence
        FROM {self.backup_table}
        WHERE datetime(backup_timestamp) >= ?
        GROUP BY symbol, timeframe, detector_name, backup_reason
        ORDER BY count DESC
        """
        
        try:
            with self._get_connection() as conn:
                df = pd.read_sql_query(sql, conn, params=(start_date.isoformat(),))
            
            if df.empty:
                return {
                    'period_days': days,
                    'total_backups': 0,
                    'by_reason': {},
                    'by_symbol': {},
                    'details': []
                }
            
            # Agrupa por motivo
            df['reason_category'] = df['backup_reason'].str.split(':').str[0]
            by_reason = df.groupby('reason_category')['count'].sum().to_dict()
            
            # Agrupa por symbol
            by_symbol = df.groupby('symbol')['count'].sum().to_dict()
            
            return {
                'period_days': days,
                'total_backups': df['count'].sum(),
                'by_reason': by_reason,
                'by_symbol': by_symbol,
                'details': df.to_dict('records')
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter estatísticas de backup: {e}")
            return {'error': str(e)}
    
    def force_clear_all_active_signals(self, confirmation_code: str = None) -> Dict:
        """
        ⚠️ FUNÇÃO PERIGOSA: Limpa TODOS os sinais ativos 
        Requer código de confirmação por segurança
        """
        expected_code = "CLEAR_ALL_SIGNALS_CONFIRMED"
        
        if confirmation_code != expected_code:
            return {
                'status': 'error',
                'message': f'Código de confirmação incorreto. Use: {expected_code}',
                'signals_cleared': 0
            }
        
        sql = f"""
        UPDATE {self.signals_table}
        SET status = 'INACTIVE', updated_at = ?
        WHERE status = 'ACTIVE'
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (datetime.now().isoformat(),))
                affected_rows = cursor.rowcount
                conn.commit()
                
                self.logger.warning(f"⚠️ LIMPEZA TOTAL EXECUTADA: {affected_rows} sinais desativados | Confirmação: {confirmation_code}")
                
                return {
                    'status': 'success',
                    'message': 'Todos os sinais ativos foram desativados',
                    'signals_cleared': affected_rows,
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Erro na limpeza total: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'signals_cleared': 0
            }

def print_active_signals_table(symbol: str = None):
    """
    🖨️ Função utilitária para imprimir tabela formatada dos sinais ativos CORRIGIDA
    """
    manager = SignalManager()
    
    if symbol:
        data = manager.get_signals_by_symbol(symbol.upper())
        if 'error' in data:
            print(f"❌ Erro: {data['error']}")
            return
        
        print(f"\n📊 SINAIS ATIVOS PARA {symbol.upper()}")
        print("=" * 80)
        
        if data['active_signals'] == 0:
            print("✅ Nenhum sinal ativo - Symbol disponível para novos sinais")
            print(f"Timeframes disponíveis: {data['available_timeframes']}")
            return
        
        print(f"Total de sinais ativos: {data['active_signals']}")
        print(f"Timeframes bloqueados: {data['blocked_timeframes']}")
        print(f"Timeframes disponíveis: {data['available_timeframes']}")
        print("\nDetalhes dos sinais:")
        print("-" * 80)
        
        for signal in data['signals']:
            # 🚨 CORRIGIDO: Mostra progresso do sinal
            progress = signal.get('progress', 'ATIVO')
            targets_info = ""
            if signal.get('targets_hit'):
                hits = sum(signal['targets_hit'])
                targets_info = f" | Targets: {hits}/3"
            
            status_icon = {
                'ACTIVE': '🔴',
                'TARGET_1_HIT': '🟡', 
                'TARGET_2_HIT': '🟠'
            }.get(signal['status'], '🔴')
            
            print(f"{status_icon} {signal['timeframe']} | {signal['detector_name']} | {signal['signal_type']} | "
                  f"Conf: {signal['confidence']:.3f} | Entry: ${signal['entry_price']:,.4f} | "
                  f"Stop: ${signal['stop_loss']:,.4f}{targets_info} | "
                  f"Status: {progress} | Criado: {signal['created_at'][:19]}")
    
    else:
        data = manager.get_active_signals_overview()
        if 'error' in data:
            print(f"❌ Erro: {data['error']}")
            return
        
        print(f"\n📊 VISÃO GERAL DOS SINAIS ATIVOS")
        print("=" * 80)
        
        if data['total_active'] == 0:
            print("✅ Nenhum sinal ativo no sistema - Todos os symbols disponíveis")
            return
        
        print(f"Total de sinais ativos: {data['total_active']}")
        print(f"Symbols com sinais: {data['symbols_with_signals']}")
        
        # 🚨 NOVO: Mostra distribuição por status
        if 'by_status' in data and data['by_status']:
            print(f"\nPor status: {data['by_status']}")
        
        print(f"Por timeframe: {data['by_timeframe']}")
        print("\nPor symbol:")
        print("-" * 80)
        
        for symbol, info in data['by_symbol'].items():
            timeframes_str = ', '.join(info['timeframes'])
            # 🚨 NOVO: Mostra status dos sinais
            status_summary = ""
            if 'statuses' in info:
                status_counts = {}
                for status in info['statuses']:
                    status_counts[status] = status_counts.get(status, 0) + 1
                status_summary = f" | Status: {status_counts}"
            
            print(f"• {symbol:8} | {info['total']} sinais | TF: {timeframes_str} | "
                  f"Conf média: {info['avg_confidence']:.3f}{status_summary}")

def clear_symbol_signals(symbol: str, timeframe: str = None):
    """
    🔴 Função utilitária para limpar sinais de um symbol
    """
    manager = SignalManager()
    
    if timeframe:
        cleared = manager.deactivate_signals_by_symbol(symbol.upper(), timeframe, "manual_utility_clear")
        print(f"🔴 {cleared} sinais desativados para {symbol.upper()} {timeframe}")
    else:
        cleared = manager.deactivate_signals_by_symbol(symbol.upper(), None, "manual_utility_clear")
        print(f"🔴 {cleared} sinais desativados para {symbol.upper()} (todos timeframes)")

if __name__ == "__main__":
    # Exemplo de uso standalone
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "overview":
            print_active_signals_table()
        
        elif command == "symbol" and len(sys.argv) > 2:
            symbol = sys.argv[2]
            print_active_signals_table(symbol)
        
        elif command == "clear" and len(sys.argv) > 2:
            symbol = sys.argv[2]
            timeframe = sys.argv[3] if len(sys.argv) > 3 else None
            clear_symbol_signals(symbol, timeframe)
        
        else:
            print("Uso:")
            print("  python signal_manager.py overview           # Visão geral")
            print("  python signal_manager.py symbol BTC         # Sinais do BTC") 
            print("  python signal_manager.py clear BTC          # Limpa sinais do BTC")
            print("  python signal_manager.py clear BTC 5m       # Limpa sinal BTC 5m")
    
    else:
        print_active_signals_table()