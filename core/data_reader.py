# data_reader.py

"""
Data Reader - Versão SEM verificação de dados recentes (mais permissivo).
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
        self.logger.info("DataReader inicializado (sem verificação de dados recentes).")
        
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
            
            # _#_REMOVIDO_: Bloco de verificação de dados recentes foi removido desta seção.
            # O sistema agora analisará os dados encontrados, independentemente de quão antigos sejam.

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

    def get_available_symbols(self) -> List[str]:
        query = f"SELECT DISTINCT symbol FROM {self.stream_table}"
        try:
            with self._get_connection() as conn:
                result = pd.read_sql_query(query, conn)
                return result['symbol'].tolist()
        except Exception as e:
            self.logger.error(f"Erro ao buscar symbols disponíveis: {e}")
            return []