# data_reader.py - CORRIGIDO PARA kline_close_time

"""
Data Reader - Versão corrigida para trabalhar com a estrutura real das tabelas
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Any
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
            
            df = df.drop_duplicates(subset=['timestamp'], keep='last').reset_index(drop=True)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            last_timestamp = df['timestamp'].iloc[-1].to_pydatetime()

            return MarketData(
                symbol=symbol,
                timeframe=timeframe,
                data=df,
                last_update=last_timestamp
            )
                
        except Exception as e:
            self.logger.error(f"Erro ao buscar dados para {symbol} {timeframe}: {e}", exc_info=True)
            return None
    
    def get_microstructure_for_validation(self, symbol: str, start_time: datetime, window_minutes: int) -> Optional[pd.DataFrame]:
        """
        CORRIGIDO: Busca dados da tabela de microestrutura usando kline_close_time
        
        Estrutura da tabela:
        - id INTEGER PRIMARY KEY AUTOINCREMENT
        - symbol TEXT NOT NULL
        - kline_close_time DATETIME NOT NULL UNIQUE  ← ESTA É A COLUNA DE TEMPO
        - open_price REAL NOT NULL
        - high_price REAL NOT NULL
        - low_price REAL NOT NULL
        - close_price REAL NOT NULL
        - volume REAL NOT NULL
        - data_hash TEXT UNIQUE
        """
        microstructure_table = settings.validation.microstructure_table
        end_time = start_time + timedelta(minutes=window_minutes)

        # Etapa 1: Converter a janela de tempo para o formato Unix (inteiro)
        try:
            start_unix = int(start_time.timestamp())
            end_unix = int((start_time + timedelta(minutes=window_minutes)).timestamp())
        except Exception as e:
            self.logger.error(f"Erro ao converter tempo para timestamp Unix: {e}")
            return None

        # Etapa 2: A query SQL agora faz uma busca numérica simples e rápida
        query = f"""
        SELECT 
            kline_close_time as timestamp,
            open_price, high_price, low_price, close_price, volume
        FROM {microstructure_table}
        WHERE symbol = ? AND kline_close_time > ? AND kline_close_time <= ?
        ORDER BY kline_close_time ASC
        """

        try:
            with self._get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=[symbol, start_unix, end_unix])

            if df.empty:
                self.logger.warning(f"Microestrutura: Nenhum dado para {symbol} encontrado na janela de {start_time} a {start_time + timedelta(minutes=window_minutes)}")
                return None

            # Etapa 3: Converter a coluna de timestamp Unix de volta para um objeto datetime.
            # Este passo é essencial para que o resto do sistema funcione corretamente.
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            
            self.logger.debug(f"Microestrutura carregada para {symbol}: {len(df)} pontos.")
            return df

        except Exception as e:
            self.logger.error(f"Erro ao buscar dados de microestrutura (Unix) para {symbol}: {e}", exc_info=True)
            return None
    
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