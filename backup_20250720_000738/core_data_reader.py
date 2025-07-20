"""
Data Reader CORRIGIDO - Sem travamentos e filtrando dados sujos
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging
from dataclasses import dataclass
import time

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
    """Classe para leitura de dados do banco de stream - CORRIGIDA"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.stream_db_path = settings.database.stream_db_path
        self.stream_table = settings.database.stream_table
        
        # NOVO: Configurações de timeout
        self.connection_timeout = getattr(settings.database, 'connection_timeout', 30)
        self.query_timeout = getattr(settings.database, 'query_timeout', 10)
        
        self.logger.info("DataReader inicializado com proteção contra travamentos")
        
    def _get_connection(self) -> sqlite3.Connection:
        """Cria conexão com o banco de dados COM TIMEOUT"""
        try:
            conn = sqlite3.connect(
                self.stream_db_path, 
                timeout=self.connection_timeout  # NOVO: Timeout para evitar travamentos
            )
            
            # NOVO: Configurações para evitar locks
            conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            conn.execute("PRAGMA synchronous=NORMAL")  # Menos restritivo
            conn.execute("PRAGMA cache_size=10000")    # Cache maior
            conn.execute("PRAGMA temp_store=memory")   # Temp em memória
            
            return conn
        except sqlite3.Error as e:
            self.logger.error(f"Erro ao conectar com banco: {e}")
            raise
    
    def _build_clean_data_query(self, base_query: str) -> str:
        """Adiciona filtros para dados limpos - REMOVE DADOS SUJOS"""
        
        # NOVO: Filtros para excluir dados sujos
        clean_filters = [
            "open_price IS NOT NULL",
            "high_price IS NOT NULL", 
            "low_price IS NOT NULL",
            "close_price IS NOT NULL",
            "volume IS NOT NULL",
            "kline_open_time IS NOT NULL",  # FILTRO ESPECÍFICO SOLICITADO
            "kline_close_time IS NOT NULL",
            "open_price > 0",
            "high_price > 0",
            "low_price > 0", 
            "close_price > 0",
            "volume >= 0",
            "high_price >= low_price",      # Consistência OHLC
            "high_price >= open_price",
            "high_price >= close_price",
            "low_price <= open_price",
            "low_price <= close_price"
        ]
        
        # Adiciona filtros à query
        if "WHERE" in base_query.upper():
            # Já tem WHERE, adiciona AND
            for filter_condition in clean_filters:
                base_query += f" AND {filter_condition}"
        else:
            # Não tem WHERE, adiciona
            base_query += f" WHERE {' AND '.join(clean_filters)}"
        
        return base_query
    
    def get_latest_data(self, symbol: str, timeframe: str = None, 
                       hours_back: int = None) -> Optional[MarketData]:
        """
        Busca dados mais recentes para um symbol - COM PROTEÇÃO CONTRA TRAVAMENTOS
        """
        if timeframe is None:
            timeframe = settings.analysis.default_timeframe
        
        if hours_back is None:
            hours_back = settings.analysis.lookback_hours
        
        # Calcula timestamp de início
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)
        
        # Query base
        base_query = f"""
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
        FROM {self.stream_table}
        WHERE symbol = ? 
            AND timeframe = ?
            AND timestamp >= ?
        """
        
        # NOVO: Adiciona filtros para dados limpos
        clean_query = self._build_clean_data_query(base_query)
        
        # Adiciona ORDER BY
        clean_query += " ORDER BY timestamp ASC"
        
        # NOVO: Adiciona LIMIT para evitar queries muito grandes
        max_records = hours_back * 12 + 100  # ~12 records/hora para 5min + buffer
        clean_query += f" LIMIT {max_records}"
        
        start_query_time = time.time()
        
        try:
            with self._get_connection() as conn:
                # NOVO: Timeout para a query
                conn.execute("PRAGMA busy_timeout = 5000")  # 5 segundos
                
                df = pd.read_sql_query(
                    clean_query, 
                    conn, 
                    params=[symbol, timeframe, start_time]
                )
                
                query_duration = time.time() - start_query_time
                
                if df.empty:
                    self.logger.warning(f"Nenhum dado LIMPO encontrado para {symbol} {timeframe}")
                    return None
                
                # Validação adicional dos dados
                original_count = len(df)
                
                # Remove duplicatas por timestamp
                df = df.drop_duplicates(subset=['timestamp'], keep='last')
                
                # Converte timestamp para datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # Ordena por timestamp
                df = df.sort_values('timestamp').reset_index(drop=True)
                
                # Validação final de consistência
                df = self._validate_ohlc_data(df)
                
                final_count = len(df)
                
                self.logger.info(
                    f"✅ {symbol} {timeframe}: {final_count} pontos limpos "
                    f"(filtrados: {original_count - final_count}) em {query_duration:.2f}s"
                )
                
                if final_count < settings.analysis.min_data_points:
                    self.logger.warning(f"Dados insuficientes após limpeza: {final_count}")
                    return None
                
                return MarketData(
                    symbol=symbol,
                    timeframe=timeframe,
                    data=df,
                    last_update=df['timestamp'].iloc[-1] if not df.empty else datetime.now()
                )
                
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower():
                self.logger.error(f"🔒 Banco travado para {symbol} - tentando novamente em 2s")
                time.sleep(2)
                # Tenta uma vez mais
                try:
                    with self._get_connection() as conn:
                        df = pd.read_sql_query(clean_query, conn, params=[symbol, timeframe, start_time])
                        if not df.empty:
                            df['timestamp'] = pd.to_datetime(df['timestamp'])
                            df = df.sort_values('timestamp').reset_index(drop=True)
                            return MarketData(symbol=symbol, timeframe=timeframe, data=df, 
                                            last_update=df['timestamp'].iloc[-1])
                except Exception:
                    pass
            self.logger.error(f"Erro de banco para {symbol}: {e}")
            return None
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar dados para {symbol}: {e}")
            return None
    
    def _validate_ohlc_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Valida e corrige inconsistências nos dados OHLC"""
        try:
            if df.empty:
                return df
            
            # Remove linhas com preços inválidos ou inconsistentes
            valid_mask = (
                (df['high_price'] >= df['open_price']) &
                (df['high_price'] >= df['close_price']) &
                (df['high_price'] >= df['low_price']) &
                (df['low_price'] <= df['open_price']) &
                (df['low_price'] <= df['close_price']) &
                (df['open_price'] > 0) &
                (df['high_price'] > 0) &
                (df['low_price'] > 0) &
                (df['close_price'] > 0) &
                (df['volume'] >= 0)
            )
            
            invalid_count = (~valid_mask).sum()
            if invalid_count > 0:
                self.logger.warning(f"Removendo {invalid_count} registros com dados OHLC inconsistentes")
            
            return df[valid_mask].reset_index(drop=True)
            
        except Exception as e:
            self.logger.error(f"Erro na validação OHLC: {e}")
            return df
    
    def get_multiple_symbols_data(self, symbols: List[str], 
                                 timeframe: str = None) -> Dict[str, MarketData]:
        """
        Busca dados para múltiplos symbols - SEM TRAVAMENTOS
        """
        results = {}
        
        for symbol in symbols:
            try:
                data = self.get_latest_data(symbol, timeframe)
                if data and data.is_sufficient_data:
                    results[symbol] = data
                else:
                    self.logger.warning(f"Dados insuficientes para {symbol}")
                    
                # NOVO: Pequena pausa entre symbols para evitar sobrecarga
                time.sleep(0.1)
                    
            except Exception as e:
                self.logger.error(f"Erro ao buscar {symbol}: {e}")
                continue
        
        return results
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Busca informações básicas de um symbol - COM FILTROS LIMPOS"""
        
        base_query = f"""
        SELECT 
            symbol,
            close_price as latest_price,
            volume_24h,
            market_cap,
            price_change_24h,
            timestamp,
            COUNT(*) as total_records
        FROM {self.stream_table}
        WHERE symbol = ?
        """
        
        # Adiciona filtros para dados limpos
        clean_query = self._build_clean_data_query(base_query)
        clean_query += " ORDER BY timestamp DESC LIMIT 1"
        
        try:
            with self._get_connection() as conn:
                conn.execute("PRAGMA busy_timeout = 3000")
                result = pd.read_sql_query(clean_query, conn, params=[symbol])
                
                if result.empty:
                    return None
                
                return result.iloc[0].to_dict()
                
        except Exception as e:
            self.logger.error(f"Erro ao buscar info de {symbol}: {e}")
            return None
    
    def get_available_symbols(self) -> List[str]:
        """Retorna lista de symbols disponíveis no banco - APENAS DADOS LIMPOS"""
        
        # Query que só pega symbols com dados limpos recentes
        query = f"""
        SELECT DISTINCT symbol 
        FROM {self.stream_table} 
        WHERE kline_open_time IS NOT NULL 
            AND kline_close_time IS NOT NULL
            AND open_price IS NOT NULL 
            AND high_price IS NOT NULL 
            AND low_price IS NOT NULL 
            AND close_price IS NOT NULL
            AND volume IS NOT NULL
            AND open_price > 0
            AND high_price > 0 
            AND low_price > 0
            AND close_price > 0
            AND timestamp >= datetime('now', '-24 hours')  -- Só symbols com dados recentes
        ORDER BY symbol
        """
        
        try:
            with self._get_connection() as conn:
                conn.execute("PRAGMA busy_timeout = 3000")
                result = pd.read_sql_query(query, conn)
                symbols = result['symbol'].tolist()
                
                self.logger.info(f"📊 Encontrados {len(symbols)} symbols com dados limpos")
                return symbols
                
        except Exception as e:
            self.logger.error(f"Erro ao buscar symbols disponíveis: {e}")
            return []
    
    def get_data_quality_report(self, symbol: str = None) -> Dict[str, Any]:
        """NOVO: Relatório de qualidade dos dados"""
        
        base_where = "WHERE 1=1"
        params = []
        
        if symbol:
            base_where += " AND symbol = ?"
            params.append(symbol)
        
        queries = {
            'total_records': f"SELECT COUNT(*) as count FROM {self.stream_table} {base_where}",
            'null_kline_open': f"SELECT COUNT(*) as count FROM {self.stream_table} {base_where} AND kline_open_time IS NULL",
            'null_kline_close': f"SELECT COUNT(*) as count FROM {self.stream_table} {base_where} AND kline_close_time IS NULL", 
            'null_prices': f"SELECT COUNT(*) as count FROM {self.stream_table} {base_where} AND (open_price IS NULL OR high_price IS NULL OR low_price IS NULL OR close_price IS NULL)",
            'zero_prices': f"SELECT COUNT(*) as count FROM {self.stream_table} {base_where} AND (open_price <= 0 OR high_price <= 0 OR low_price <= 0 OR close_price <= 0)",
            'invalid_ohlc': f"SELECT COUNT(*) as count FROM {self.stream_table} {base_where} AND (high_price < low_price OR high_price < open_price OR high_price < close_price OR low_price > open_price OR low_price > close_price)"
        }
        
        results = {}
        
        try:
            with self._get_connection() as conn:
                for key, query in queries.items():
                    try:
                        result = pd.read_sql_query(query, conn, params=params)
                        results[key] = result['count'].iloc[0]
                    except Exception as e:
                        results[key] = f"Erro: {e}"
                        
        except Exception as e:
            return {'error': str(e)}
        
        # Calcula percentuais
        total = results.get('total_records', 1)
        if total > 0:
            results['dirty_data_percentage'] = (
                results.get('null_kline_open', 0) + 
                results.get('null_kline_close', 0) + 
                results.get('null_prices', 0) + 
                results.get('zero_prices', 0) + 
                results.get('invalid_ohlc', 0)
            ) / total * 100
            
            results['clean_data_percentage'] = 100 - results['dirty_data_percentage']
        
        return results

# Função utilitária para diagnóstico
def diagnose_data_quality():
    """Diagnóstica qualidade dos dados no banco"""
    print("🔍 DIAGNÓSTICO DE QUALIDADE DOS DADOS")
    print("=" * 40)
    
    try:
        reader = DataReader()
        
        # Relatório geral
        general_report = reader.get_data_quality_report()
        
        print("📊 RELATÓRIO GERAL:")
        print(f"   Total de registros: {general_report.get('total_records', 'N/A'):,}")
        print(f"   Dados limpos: {general_report.get('clean_data_percentage', 0):.1f}%")
        print(f"   Dados sujos: {general_report.get('dirty_data_percentage', 0):.1f}%")
        print()
        
        print("🗑️  TIPOS DE DADOS SUJOS:")
        print(f"   kline_open_time NULL: {general_report.get('null_kline_open', 0):,}")
        print(f"   kline_close_time NULL: {general_report.get('null_kline_close', 0):,}")
        print(f"   Preços NULL: {general_report.get('null_prices', 0):,}")
        print(f"   Preços zero/negativos: {general_report.get('zero_prices', 0):,}")
        print(f"   OHLC inconsistente: {general_report.get('invalid_ohlc', 0):,}")
        print()
        
        # Symbols disponíveis
        symbols = reader.get_available_symbols()
        print(f"✅ SYMBOLS COM DADOS LIMPOS: {len(symbols)}")
        if symbols:
            print(f"   Exemplos: {', '.join(symbols[:5])}")
        
        return general_report
        
    except Exception as e:
        print(f"❌ Erro no diagnóstico: {e}")
        return None