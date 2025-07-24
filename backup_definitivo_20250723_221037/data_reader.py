# data_reader.py - CORRIGIDO PARA CONFIGURAÇÃO EXISTENTE + SEM LOCKS

"""
Data Reader otimizado para evitar locks de banco:
1. Compatível com configuração existente
2. Conexões sem locks longos
3. Timeouts agressivos
4. READ UNCOMMITTED para evitar blocking
"""

import sqlite3
import pandas as pd
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from config.settings import settings

@dataclass
class MarketData:
    """Estrutura para dados de mercado"""
    symbol: str
    timeframe: str
    data: pd.DataFrame
    last_update: datetime
    
    @property
    def is_sufficient_data(self) -> bool:
        """Verifica se há dados suficientes para análise"""
        return len(self.data) >= 50

class DataReader:
    """Data Reader otimizado sem locks - COMPATÍVEL COM CONFIGURAÇÃO EXISTENTE"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # CONFIGURAÇÃO COMPATÍVEL - detecta automaticamente a configuração correta
        try:
            # Primeira prioridade: stream_db_path (configuração atual detectada)
            if hasattr(settings.database, 'stream_db_path'):
                self.db_path = settings.database.stream_db_path
                self.table_name = getattr(settings.database, 'stream_table', 'crypto_ohlc')
                self.logger.info(f"✅ Usando configuração STREAM: {self.db_path}")
            
            # Segunda prioridade: market_data_db_path
            elif hasattr(settings.database, 'market_data_db_path'):
                self.db_path = settings.database.market_data_db_path
                self.table_name = settings.database.market_data_table
                self.logger.info(f"✅ Usando configuração MARKET_DATA: {self.db_path}")
            
            # Terceira prioridade: configuração alternativa
            elif hasattr(settings.database, 'market_data_path'):
                self.db_path = settings.database.market_data_path
                self.table_name = getattr(settings.database, 'market_data_table', 'market_data')
                self.logger.info(f"✅ Usando configuração ALT: {self.db_path}")
            
            # Quarta prioridade: configuração básica
            elif hasattr(settings.database, 'path'):
                self.db_path = settings.database.path
                self.table_name = getattr(settings.database, 'table', 'market_data')
                self.logger.info(f"✅ Usando configuração BÁSICA: {self.db_path}")
            
            # Fallback para configuração padrão
            else:
                self.db_path = "data/market_data.db"
                self.table_name = "market_data"
                self.logger.warning(f"⚠️ Usando configuração padrão: {self.db_path}")
                
        except Exception as e:
            # Fallback absoluto
            self.db_path = "data/market_data.db" 
            self.table_name = "market_data"
            self.logger.error(f"❌ Erro na configuração DB, usando padrão: {e}")
        
        # CONFIGURAÇÕES ANTI-LOCK
        self.CONNECTION_TIMEOUT = 3  # Máximo 3s para conectar
        self.QUERY_TIMEOUT = 5       # Máximo 5s para query
        self.MAX_RETRIES = 2         # Máximo 2 tentativas
        
        self.logger.info(f"DataReader OTIMIZADO inicializado:")
        self.logger.info(f"  • DB: {self.db_path}")
        self.logger.info(f"  • Tabela: {self.table_name}")
        self.logger.info(f"  • Anti-locks: ATIVO")
    
    def _get_optimized_connection(self):
        """Conexão otimizada sem locks longos"""
        try:
            conn = sqlite3.connect(
                self.db_path, 
                timeout=self.CONNECTION_TIMEOUT,
                check_same_thread=False,
                isolation_level=None  # Autocommit mode
            )
            
            # CONFIGURAÇÕES ANTI-LOCK
            conn.execute("PRAGMA read_uncommitted = true")  # Não bloqueia leituras
            conn.execute("PRAGMA journal_mode = WAL")       # Write-Ahead Logging
            conn.execute("PRAGMA synchronous = NORMAL")     # Menos sincronização
            conn.execute("PRAGMA cache_size = 10000")       # Cache maior
            conn.execute("PRAGMA temp_store = memory")      # Temp em memória
            
            return conn
            
        except Exception as e:
            self.logger.error(f"Erro na conexão otimizada: {e}")
            raise
    
    def get_latest_data(self, symbol: str, timeframe: str, limit: int = 200) -> Optional[MarketData]:
        """
        Busca dados mais recentes SEM LOCK
        """
        start_time = time.time()
        
        try:
            # Query otimizada com LIMIT para ser rápida
            query = f"""
            SELECT timestamp, open_price, high_price, low_price, close_price, volume
            FROM {self.table_name}
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """
            
            for attempt in range(self.MAX_RETRIES):
                try:
                    with self._get_optimized_connection() as conn:
                        # Timeout na query
                        conn.execute("PRAGMA busy_timeout = 1000")  # 1s timeout
                        
                        df = pd.read_sql_query(
                            query, 
                            conn, 
                            params=(symbol, timeframe, limit)
                        )
                    
                    break  # Sucesso
                    
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e).lower() and attempt < self.MAX_RETRIES - 1:
                        self.logger.warning(f"DB locked, tentativa {attempt + 1}/{self.MAX_RETRIES}")
                        time.sleep(0.1 * (attempt + 1))  # Backoff exponencial
                        continue
                    else:
                        raise
            
            execution_time = time.time() - start_time
            
            if execution_time > self.QUERY_TIMEOUT:
                self.logger.warning(f"Query lenta para {symbol} {timeframe}: {execution_time:.2f}s")
            
            if df.empty:
                self.logger.warning(f"Nenhum dado encontrado para {symbol} {timeframe}")
                return None
            
            # Converte timestamp e ordena corretamente
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # Converte tipos numéricos
            numeric_columns = ['open_price', 'high_price', 'low_price', 'close_price', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Remove linhas com dados inválidos
            df = df.dropna().reset_index(drop=True)
            
            self.logger.debug(f"✅ {symbol} {timeframe}: {len(df)} registros em {execution_time:.2f}s")
            
            return MarketData(
                symbol=symbol,
                timeframe=timeframe,
                data=df,
                last_update=datetime.now()
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"❌ Erro ao buscar {symbol} {timeframe} em {execution_time:.2f}s: {e}")
            return None
    
    def get_valid_symbols_for_analysis(self) -> List[str]:
        """
        Retorna símbolos válidos SEM LOCK
        """
        try:
            # Query rápida para símbolos únicos
            query = f"""
            SELECT DISTINCT symbol
            FROM {self.table_name}
            WHERE timeframe IN ('5m', '15m')
            AND timestamp > datetime('now', '-7 days')
            LIMIT 50
            """
            
            with self._get_optimized_connection() as conn:
                conn.execute("PRAGMA busy_timeout = 500")  # 0.5s timeout
                
                cursor = conn.cursor()
                cursor.execute(query)
                results = cursor.fetchall()
            
            symbols = [row[0] for row in results]
            
            # Filtra símbolos que têm dados suficientes
            valid_symbols = []
            for symbol in symbols:
                try:
                    # Verifica rapidamente se tem dados recentes
                    quick_check = f"""
                    SELECT COUNT(*) 
                    FROM {self.table_name} 
                    WHERE symbol = ? AND timeframe = '5m' 
                    AND timestamp > datetime('now', '-2 days')
                    """
                    
                    with self._get_optimized_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(quick_check, (symbol,))
                        count = cursor.fetchone()[0]
                    
                    if count >= 100:  # Pelo menos 100 registros recentes
                        valid_symbols.append(symbol)
                        
                except Exception as e:
                    self.logger.debug(f"Erro na verificação de {symbol}: {e}")
                    continue
            
            # Limita a 8 símbolos para evitar sobrecarga
            valid_symbols = valid_symbols[:8]
            
            self.logger.info(f"✅ Símbolos válidos encontrados: {valid_symbols}")
            return valid_symbols
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao buscar símbolos válidos: {e}")
            
            # FALLBACK: usa símbolos do settings se disponível
            try:
                fallback_symbols = settings.get_analysis_symbols()[:8]
                self.logger.info(f"📋 Usando símbolos do settings: {fallback_symbols}")
                return fallback_symbols
            except:
                # FALLBACK ABSOLUTO: símbolos hardcoded
                fallback_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "DOGEUSDT", "MATICUSDT", "LTCUSDT"]
                self.logger.warning(f"⚠️ Usando símbolos hardcoded: {fallback_symbols}")
                return fallback_symbols
    
    def get_microstructure_for_validation(self, symbol: str, start_time: datetime, duration_minutes: int) -> Optional[pd.DataFrame]:
        """
        DESABILITADO: Microestrutura pode causar locks
        """
        self.logger.debug(f"Microestrutura desabilitada para {symbol} (evita locks)")
        return None
    
    def test_microstructure_connection(self) -> Dict[str, Any]:
        """
        Testa conexão de microestrutura SEM LOCK
        """
        try:
            # Testa apenas a existência da tabela, sem buscar dados
            query = f"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%1m%' OR name LIKE '%minute%'"
            
            with self._get_optimized_connection() as conn:
                conn.execute("PRAGMA busy_timeout = 200")  # 0.2s timeout
                cursor = conn.cursor()
                cursor.execute(query)
                tables = cursor.fetchall()
            
            has_microstructure = len(tables) > 0
            
            return {
                'table_exists': has_microstructure,
                'has_data': False,  # Não verifica dados para evitar locks
                'sample_data_count': 0,
                'status': 'disabled_to_avoid_locks'
            }
            
        except Exception as e:
            self.logger.debug(f"Teste de microestrutura falhou: {e}")
            return {
                'table_exists': False,
                'has_data': False,
                'sample_data_count': 0,
                'error': str(e)
            }
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Busca preço atual SEM LOCK para monitoramento
        """
        try:
            # Query super rápida para preço atual - tenta 1m primeiro
            query_1m = f"""
            SELECT close_price
            FROM {self.table_name}
            WHERE symbol = ? AND timeframe = '1m'
            ORDER BY timestamp DESC
            LIMIT 1
            """
            
            try:
                with self._get_optimized_connection() as conn:
                    conn.execute("PRAGMA busy_timeout = 100")  # 0.1s timeout apenas
                    
                    cursor = conn.cursor()
                    cursor.execute(query_1m, (symbol,))
                    result = cursor.fetchone()
                
                if result:
                    return float(result[0])
            except:
                pass  # Se falhar, tenta 5m
            
            # Fallback para 5m se não tem 1m ou deu timeout
            query_5m = f"""
            SELECT close_price
            FROM {self.table_name}
            WHERE symbol = ? AND timeframe = '5m'
            ORDER BY timestamp DESC
            LIMIT 1
            """
            
            with self._get_optimized_connection() as conn:
                conn.execute("PRAGMA busy_timeout = 100")
                cursor = conn.cursor()
                cursor.execute(query_5m, (symbol,))
                result = cursor.fetchone()
            
            return float(result[0]) if result else None
                
        except Exception as e:
            self.logger.warning(f"Erro ao buscar preço atual de {symbol}: {e}")
            return None
    
    def get_price_at_time(self, symbol: str, target_time: datetime, tolerance_minutes: int = 5) -> Optional[float]:
        """
        Busca preço em momento específico SEM LOCK
        """
        try:
            start_time = target_time - timedelta(minutes=tolerance_minutes)
            end_time = target_time + timedelta(minutes=tolerance_minutes)
            
            # Usa 5m para evitar locks na tabela de 1m
            query = f"""
            SELECT close_price, timestamp
            FROM {self.table_name}
            WHERE symbol = ? AND timeframe = '5m'
            AND timestamp BETWEEN ? AND ?
            ORDER BY ABS(julianday(timestamp) - julianday(?))
            LIMIT 1
            """
            
            with self._get_optimized_connection() as conn:
                conn.execute("PRAGMA busy_timeout = 100")
                
                cursor = conn.cursor()
                cursor.execute(query, (symbol, start_time.isoformat(), end_time.isoformat(), target_time.isoformat()))
                result = cursor.fetchone()
            
            return float(result[0]) if result else None
            
        except Exception as e:
            self.logger.warning(f"Erro ao buscar preço histórico de {symbol}: {e}")
            return None
    
    def test_connection(self) -> Dict[str, Any]:
        """Testa conexão com o banco"""
        try:
            start_time = time.time()
            
            with self._get_optimized_connection() as conn:
                cursor = conn.cursor()
                
                # Teste simples
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]
                
                # Testa se tabela principal existe
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{self.table_name}'")
                main_table_exists = cursor.fetchone() is not None
                
                # Se tabela existe, conta registros
                record_count = 0
                if main_table_exists:
                    cursor.execute(f"SELECT COUNT(*) FROM {self.table_name} LIMIT 1")
                    record_count = cursor.fetchone()[0]
            
            execution_time = time.time() - start_time
            
            return {
                'status': 'success',
                'database_path': self.db_path,
                'main_table': self.table_name,
                'main_table_exists': main_table_exists,
                'total_tables': table_count,
                'sample_record_count': record_count,
                'connection_time': execution_time,
                'anti_lock_enabled': True
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'database_path': self.db_path,
                'main_table': self.table_name,
                'error': str(e),
                'anti_lock_enabled': True
            }