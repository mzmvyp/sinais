# data_reader.py - CORRIGIDO PARA kline_close_time

"""
Data Reader - Versão corrigida para trabalhar com a estrutura real das tabelas
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
import logging

from config.settings import settings

@dataclass
class MarketData:
    symbol: str
    timeframe: str
    data: pd.DataFrame
    last_update: datetime
    
    @property
    def latest_price(self) -> float:
        return float(self.data['close_price'].iloc[-1]) if not self.data.empty else 0.0
    
    @property
    def data_points(self) -> int:
        return len(self.data)
    
    @property
    def is_sufficient_data(self) -> bool:
        tf_config = settings.get_timeframe_config(self.timeframe)
        return self.data_points >= tf_config.min_data_points

class DataReader:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.stream_db_path = settings.database.stream_db_path
        self.stream_table = settings.database.stream_table
        self.logger.info("DataReader inicializado (CORRIGIDO para kline_close_time).")
        
    def _get_connection(self) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(self.stream_db_path, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")
            return conn
        except sqlite3.Error as e:
            self.logger.error(f"Erro ao conectar com banco: {e}")
            raise
    
    def get_latest_data(self, symbol: str, timeframe: str = None) -> Optional[MarketData]:
        tf_config = settings.get_timeframe_config(timeframe)
        hours_back = tf_config.lookback_hours
        
        start_time_filter = datetime.utcnow() - timedelta(hours=hours_back)
        
        query = f"""
        SELECT timestamp, open_price, high_price, low_price, close_price, volume
        FROM {self.stream_table}
        WHERE symbol = ? AND timeframe = ? AND timestamp >= ?
        ORDER BY timestamp ASC
        """
        
        try:
            with self._get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=[symbol, timeframe, start_time_filter])
                
            if df.empty:
                self.logger.warning(f"Nenhum dado encontrado para {symbol} {timeframe}")
                return None
            
            # DEBUG: Log quantidade de dados
            self.logger.debug(f"Dados para {symbol} {timeframe}: {len(df)} registros (mín: {tf_config.min_data_points})")
            
            df = df.drop_duplicates(subset=['timestamp'], keep='last').reset_index(drop=True)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            last_timestamp = df['timestamp'].iloc[-1].to_pydatetime()

            market_data = MarketData(
                symbol=symbol,
                timeframe=timeframe,
                data=df,
                last_update=last_timestamp
            )
            
            # DEBUG: Log se dados são suficientes
            if not market_data.is_sufficient_data:
                self.logger.warning(f"Dados insuficientes para {symbol} {timeframe}: {len(df)} < {tf_config.min_data_points}")
            
            return market_data
                
        except Exception as e:
            self.logger.error(f"Erro ao buscar dados para {symbol} {timeframe}: {e}", exc_info=True)
            return None
    
    
    def get_microstructure_for_validation(self, symbol: str, start_time: datetime, window_minutes: int) -> Optional[pd.DataFrame]:
        """CORRIGIDO: Busca melhorada com múltiplas tentativas"""
        microstructure_table = settings.validation.microstructure_table
        
        # Estratégia 1: Busca na janela solicitada
        end_time = start_time + timedelta(minutes=window_minutes)
        start_unix = int(start_time.timestamp())
        end_unix = int(end_time.timestamp())
        
        query = f"""
        SELECT kline_close_time as timestamp, open_price, high_price, low_price, close_price, volume
        FROM {microstructure_table}
        WHERE symbol = ? AND kline_close_time BETWEEN ? AND ?
        ORDER BY kline_close_time ASC
        """
        
        try:
            with self._get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=[symbol, start_unix, end_unix])
            
            # Se não encontrou dados suficientes, tenta janela expandida
            if df.empty or len(df) < 3:
                # Estratégia 2: Busca em janela mais ampla (para trás)
                extended_start = start_time - timedelta(minutes=60)  # 1 hora para trás
                extended_end = start_time + timedelta(minutes=30)   # 30 min para frente
                
                start_unix_ext = int(extended_start.timestamp())
                end_unix_ext = int(extended_end.timestamp())
                
                df = pd.read_sql_query(query, conn, params=[symbol, start_unix_ext, end_unix_ext])
                
                if not df.empty:
                    self.logger.debug(f"Microestrutura expandida para {symbol}: {len(df)} pontos")
            
            if df.empty:
                self.logger.warning(f"Nenhum dado de microestrutura encontrado para {symbol}")
                return None
                
            # Converte timestamp e filtra dados próximos ao sinal
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df['time_diff'] = abs((df['timestamp'] - start_time).dt.total_seconds())
            
            # Pega os dados mais próximos do tempo do sinal
            closest_data = df.nsmallest(min(10, len(df)), 'time_diff')
            
            self.logger.debug(f"Microestrutura para {symbol}: {len(closest_data)} pontos próximos")
            return closest_data
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar microestrutura para {symbol}: {e}")
            return None
    
    def check_symbol_data_availability(self, symbol: str, min_records: int = 50) -> Dict[str, Any]:
        """Verifica se o símbolo tem dados suficientes em cada timeframe"""
        enabled_timeframes = settings.get_enabled_timeframes()
        results = {}
        
        for timeframe in enabled_timeframes:
            query = f"""
            SELECT COUNT(*) as count, 
                MIN(timestamp) as first_record,
                MAX(timestamp) as last_record
            FROM {self.stream_table}
            WHERE symbol = ? AND timeframe = ?
            """
            
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, (symbol, timeframe))
                    row = cursor.fetchone()
                    
                    count = row[0] if row else 0
                    results[timeframe] = {
                        'count': count,
                        'sufficient': count >= min_records,
                        'first_record': row[1] if row and row[1] else None,
                        'last_record': row[2] if row and row[2] else None
                    }
                    
            except Exception as e:
                self.logger.error(f"Erro ao verificar dados para {symbol} {timeframe}: {e}")
                results[timeframe] = {'count': 0, 'sufficient': False, 'error': str(e)}
        
        # Verifica se tem dados suficientes em pelo menos um timeframe
        has_sufficient_data = any(tf['sufficient'] for tf in results.values())
        
        return {
            'symbol': symbol,
            'has_sufficient_data': has_sufficient_data,
            'timeframes': results
        }

    def get_valid_symbols_for_analysis(self) -> List[str]:
        """Retorna apenas símbolos com dados suficientes"""
        all_symbols = settings.get_analysis_symbols()
        valid_symbols = []
        
        for symbol in all_symbols:
            check_result = self.check_symbol_data_availability(symbol)
            if check_result['has_sufficient_data']:
                valid_symbols.append(symbol)
            else:
                self.logger.warning(f"Símbolo {symbol} removido: dados insuficientes")
        
        self.logger.info(f"Símbolos válidos para análise: {valid_symbols}")
        return valid_symbols
    
    def get_available_symbols(self) -> List[str]:
        query = f"SELECT DISTINCT symbol FROM {self.stream_table}"
        try:
            with self._get_connection() as conn:
                result = pd.read_sql_query(query, conn)
                return result['symbol'].tolist()
        except Exception as e:
            self.logger.error(f"Erro ao buscar symbols disponíveis: {e}")
            return []
    
    def test_microstructure_connection(self) -> dict:
        """Testa a conexão e estrutura da tabela de microestrutura"""
        microstructure_table = settings.validation.microstructure_table
        
        result = {
            'table_exists': False,
            'has_data': False,
            'sample_symbols': [],
            'sample_data_count': 0,
            'latest_data': None,
            'error': None
        }
        
        try:
            with self._get_connection() as conn:
                # Verifica se a tabela existe
                cursor = conn.cursor()
                cursor.execute(f"""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='{microstructure_table}'
                """)
                table_exists = cursor.fetchone() is not None
                result['table_exists'] = table_exists
                
                if not table_exists:
                    result['error'] = f"Tabela {microstructure_table} não existe"
                    return result
                
                # Verifica se há dados
                cursor.execute(f"SELECT COUNT(*) as count FROM {microstructure_table}")
                count = cursor.fetchone()[0]
                result['has_data'] = count > 0
                result['sample_data_count'] = count
                
                if count > 0:
                    # Busca símbolos únicos
                    cursor.execute(f"SELECT DISTINCT symbol FROM {microstructure_table} LIMIT 5")
                    symbols = [row[0] for row in cursor.fetchall()]
                    result['sample_symbols'] = symbols
                    
                    # Busca dados mais recentes
                    cursor.execute(f"""
                        SELECT symbol, kline_close_time, close_price 
                        FROM {microstructure_table} 
                        ORDER BY kline_close_time DESC 
                        LIMIT 3
                    """)
                    latest = cursor.fetchall()
                    result['latest_data'] = latest
                    
                    self.logger.info(f"Teste de microestrutura: {count} registros, símbolos: {symbols}")
                
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Erro ao testar microestrutura: {e}")
        
        return result