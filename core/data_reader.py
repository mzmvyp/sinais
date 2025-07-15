"""
Data Reader - Leitura de dados do banco de stream
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging
from dataclasses import dataclass

from config.settings import settings

@dataclass
class MarketData:
    """Estrutura para dados de mercado"""
    symbol: str
    timeframe: str
    data: pd.DataFrame
    last_update: datetime
    
    def __post_init__(self):
        """Garante que o DataFrame tenha as colunas necessárias"""
        required_columns = ['timestamp', 'open_price', 'high_price', 'low_price', 'close_price', 'volume']
        missing_columns = [col for col in required_columns if col not in self.data.columns]
        
        if missing_columns:
            raise ValueError(f"Colunas obrigatórias ausentes: {missing_columns}")
    
    @property
    def latest_price(self) -> float:
        """Retorna o último preço de fechamento"""
        return float(self.data['close_price'].iloc[-1]) if not self.data.empty else 0.0
    
    @property
    def data_points(self) -> int:
        """Número de pontos de dados disponíveis"""
        return len(self.data)
    
    @property
    def is_sufficient_data(self) -> bool:
        """Verifica se há dados suficientes para análise"""
        return self.data_points >= settings.analysis.min_data_points

class DataReader:
    """Classe para leitura de dados do banco de stream"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.stream_db_path = settings.database.stream_db_path
        self.stream_table = settings.database.stream_table
        
    def _get_connection(self) -> sqlite3.Connection:
        """Cria conexão com o banco de dados"""
        try:
            conn = sqlite3.connect(self.stream_db_path)
            return conn
        except sqlite3.Error as e:
            self.logger.error(f"Erro ao conectar com banco: {e}")
            raise
    
    def get_latest_data(self, symbol: str, timeframe: str = None, 
                       hours_back: int = None) -> Optional[MarketData]:
        """
        Busca dados mais recentes para um symbol
        
        Args:
            symbol: Symbol da crypto (ex: BTCUSDT)
            timeframe: Timeframe dos dados (padrão: 5m)
            hours_back: Quantas horas buscar (padrão: configuração)
        
        Returns:
            MarketData com os dados ou None se não encontrar
        """
        if timeframe is None:
            timeframe = settings.analysis.default_timeframe
        
        if hours_back is None:
            hours_back = settings.analysis.lookback_hours
        
        # Calcula timestamp de início
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)
        
        query = """
        SELECT 
            timestamp,
            open_price,
            high_price,
            low_price,
            close_price,
            volume,
            volume_24h,
            market_cap,
            price_change_24h,
            number_of_trades,
            kline_open_time,
            kline_close_time
        FROM {table}
        WHERE symbol = ? 
            AND timeframe = ?
            AND timestamp >= ?
        ORDER BY timestamp ASC
        """.format(table=self.stream_table)
        
        try:
            with self._get_connection() as conn:
                df = pd.read_sql_query(
                    query, 
                    conn, 
                    params=[symbol, timeframe, start_time]
                )
                
                if df.empty:
                    self.logger.warning(f"Nenhum dado encontrado para {symbol} {timeframe}")
                    return None
                
                # Converte timestamp para datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # Ordena por timestamp
                df = df.sort_values('timestamp').reset_index(drop=True)
                
                self.logger.info(f"Carregados {len(df)} pontos para {symbol} {timeframe}")
                
                return MarketData(
                    symbol=symbol,
                    timeframe=timeframe,
                    data=df,
                    last_update=df['timestamp'].iloc[-1] if not df.empty else datetime.now()
                )
                
        except Exception as e:
            self.logger.error(f"Erro ao buscar dados para {symbol}: {e}")
            return None
    
    def get_multiple_symbols_data(self, symbols: List[str], 
                                 timeframe: str = None) -> Dict[str, MarketData]:
        """
        Busca dados para múltiplos symbols
        
        Args:
            symbols: Lista de symbols
            timeframe: Timeframe dos dados
        
        Returns:
            Dicionário {symbol: MarketData}
        """
        results = {}
        
        for symbol in symbols:
            data = self.get_latest_data(symbol, timeframe)
            if data and data.is_sufficient_data:
                results[symbol] = data
            else:
                self.logger.warning(f"Dados insuficientes para {symbol}")
        
        return results
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Busca informações básicas de um symbol
        
        Args:
            symbol: Symbol da crypto
        
        Returns:
            Dicionário com informações básicas
        """
        query = """
        SELECT 
            symbol,
            close_price as latest_price,
            volume_24h,
            market_cap,
            price_change_24h,
            timestamp,
            COUNT(*) as total_records
        FROM {table}
        WHERE symbol = ?
        ORDER BY timestamp DESC
        LIMIT 1
        """.format(table=self.stream_table)
        
        try:
            with self._get_connection() as conn:
                result = pd.read_sql_query(query, conn, params=[symbol])
                
                if result.empty:
                    return None
                
                return result.iloc[0].to_dict()
                
        except Exception as e:
            self.logger.error(f"Erro ao buscar info de {symbol}: {e}")
            return None
    
    def get_available_symbols(self) -> List[str]:
        """
        Retorna lista de symbols disponíveis no banco
        
        Returns:
            Lista de symbols únicos
        """
        query = f"SELECT DISTINCT symbol FROM {self.stream_table} ORDER BY symbol"
        
        try:
            with self._get_connection() as conn:
                result = pd.read_sql_query(query, conn)
                return result['symbol'].tolist()
                
        except Exception as e:
            self.logger.error(f"Erro ao buscar symbols disponíveis: {e}")
            return []
    
    def get_timeframes(self, symbol: str) -> List[str]:
        """
        Retorna timeframes disponíveis para um symbol
        
        Args:
            symbol: Symbol da crypto
        
        Returns:
            Lista de timeframes disponíveis
        """
        query = f"""
        SELECT DISTINCT timeframe 
        FROM {self.stream_table} 
        WHERE symbol = ? 
        ORDER BY timeframe
        """
        
        try:
            with self._get_connection() as conn:
                result = pd.read_sql_query(query, conn, params=[symbol])
                return result['timeframe'].tolist()
                
        except Exception as e:
            self.logger.error(f"Erro ao buscar timeframes para {symbol}: {e}")
            return []
    
    def validate_data_quality(self, market_data: MarketData) -> Dict[str, Any]:
        """
        Valida qualidade dos dados
        
        Args:
            market_data: Dados de mercado
        
        Returns:
            Dicionário com resultados da validação
        """
        df = market_data.data
        
        validation_results = {
            'total_records': len(df),
            'missing_values': df.isnull().sum().to_dict(),
            'data_completeness': (1 - df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100,
            'price_gaps': 0,
            'volume_zeros': (df['volume'] == 0).sum(),
            'time_gaps': [],
            'is_valid': True
        }
        
        # Verifica gaps de preço (variações > 10%)
        if len(df) > 1:
            price_changes = df['close_price'].pct_change().abs()
            large_gaps = price_changes > 0.10
            validation_results['price_gaps'] = large_gaps.sum()
        
        # Verifica gaps de tempo
        if len(df) > 1:
            df_sorted = df.sort_values('timestamp')
            time_diffs = df_sorted['timestamp'].diff()
            expected_interval = pd.Timedelta(minutes=5)  # Assumindo 5m
            
            large_time_gaps = time_diffs > expected_interval * 2
            if large_time_gaps.any():
                gap_indices = df_sorted[large_time_gaps].index.tolist()
                validation_results['time_gaps'] = gap_indices
        
        # Determina se os dados são válidos
        validation_results['is_valid'] = (
            validation_results['data_completeness'] > 95 and
            validation_results['price_gaps'] < len(df) * 0.05 and
            len(validation_results['time_gaps']) < len(df) * 0.1
        )
        
        return validation_results