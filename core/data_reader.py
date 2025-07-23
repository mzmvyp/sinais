# data_reader.py - CORRIGIDO PARA APENAS 5m e 15m + ANTI-TRAVAMENTO

"""
Data Reader - Versão corrigida para trabalhar apenas com 5m e 15m
Sistema anti-travamento implementado
"""
import sqlite3
import pandas as pd
import time
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
        self.logger.info("DataReader inicializado (OTIMIZADO para 5m/15m).")
        
        # Cache para evitar consultas repetidas
        self._cache = {}
        self._cache_timeout = 60  # 1 minuto de cache
        
    def _get_connection(self, timeout: int = 5) -> sqlite3.Connection:
        """Conexão com timeout reduzido"""
        try:
            conn = sqlite3.connect(self.stream_db_path, timeout=timeout)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA temp_store=memory")  # Otimização
            return conn
        except sqlite3.Error as e:
            self.logger.error(f"Erro ao conectar com banco: {e}")
            raise
    
    def get_latest_data(self, symbol: str, timeframe: str = None) -> Optional[MarketData]:
        """Busca dados com cache e timeout"""
        
        # PROTEÇÃO: Força apenas timeframes permitidos
        if timeframe not in ["5m", "15m"]:
            self.logger.warning(f"Timeframe {timeframe} não permitido, usando 5m")
            timeframe = "5m"
        
        # Verifica cache
        cache_key = f"{symbol}_{timeframe}"
        now = time.time()
        
        if cache_key in self._cache:
            cached_data, cache_time = self._cache[cache_key]
            if now - cache_time < self._cache_timeout:
                self.logger.debug(f"Cache hit para {cache_key}")
                return cached_data
        
        start_time = time.time()
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
            with self._get_connection(timeout=5) as conn:
                df = pd.read_sql_query(query, conn, params=[symbol, timeframe, start_time_filter])
                
            elapsed = time.time() - start_time
            if elapsed > 2.0:
                self.logger.warning(f"Consulta lenta para {symbol} {timeframe}: {elapsed:.1f}s")
                
            if df.empty:
                self.logger.warning(f"Nenhum dado encontrado para {symbol} {timeframe}")
                return None
            
            # DEBUG: Log quantidade de dados com limites de configuração REDUZIDOS
            required_points = tf_config.min_data_points
            self.logger.debug(f"Dados para {symbol} {timeframe}: {len(df)} registros (mín: {required_points})")
            
            df = df.drop_duplicates(subset=['timestamp'], keep='last').reset_index(drop=True)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            last_timestamp = df['timestamp'].iloc[-1].to_pydatetime()

            market_data = MarketData(
                symbol=symbol,
                timeframe=timeframe,
                data=df,
                last_update=last_timestamp
            )
            
            # DEBUG: Log se dados são suficientes com configuração RELAXADA
            if not market_data.is_sufficient_data:
                self.logger.warning(f"Dados insuficientes para {symbol} {timeframe}: {len(df)} < {required_points}")
            
            # Atualiza cache
            self._cache[cache_key] = (market_data, now)
            
            return market_data
                
        except Exception as e:
            self.logger.error(f"Erro ao buscar dados para {symbol} {timeframe}: {e}", exc_info=True)
            return None
    
    def get_microstructure_for_validation(self, symbol: str, start_time: datetime, window_minutes: int) -> Optional[pd.DataFrame]:
        """CORRIGIDO: Busca melhorada com múltiplas tentativas + TIMEOUT"""
        microstructure_table = settings.validation.microstructure_table
        
        # TIMEOUT: Máximo 3 segundos para esta operação
        operation_start = time.time()
        timeout_seconds = 3.0
        
        try:
            # Estratégia 1: Busca na janela solicitada
            end_time = start_time + timedelta(minutes=window_minutes)
            start_unix = int(start_time.timestamp())
            end_unix = int(end_time.timestamp())
            
            query = f"""
            SELECT kline_close_time as timestamp, open_price, high_price, low_price, close_price, volume
            FROM {microstructure_table}
            WHERE symbol = ? AND kline_close_time BETWEEN ? AND ?
            ORDER BY kline_close_time ASC
            LIMIT 100
            """
            
            with self._get_connection(timeout=2) as conn:  # Timeout reduzido
                df = pd.read_sql_query(query, conn, params=[symbol, start_unix, end_unix])
            
            elapsed = time.time() - operation_start
            if elapsed > timeout_seconds:
                self.logger.warning(f"Microestrutura timeout para {symbol}: {elapsed:.1f}s")
                return None
            
            # Se não encontrou dados suficientes, tenta janela expandida (apenas se não demorou muito)
            if (df.empty or len(df) < 3) and elapsed < 1.5:
                # Estratégia 2: Busca em janela mais ampla (para trás)
                extended_start = start_time - timedelta(minutes=30)  # Reduzido de 60 para 30
                extended_end = start_time + timedelta(minutes=15)   # Reduzido de 30 para 15
                
                start_unix_ext = int(extended_start.timestamp())
                end_unix_ext = int(extended_end.timestamp())
                
                df = pd.read_sql_query(query, conn, params=[symbol, start_unix_ext, end_unix_ext])
                
                if not df.empty:
                    self.logger.debug(f"Microestrutura expandida para {symbol}: {len(df)} pontos")
            
            if df.empty:
                self.logger.debug(f"Nenhum dado de microestrutura para {symbol}")
                return None
                
            # Converte timestamp e filtra dados próximos ao sinal
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df['time_diff'] = abs((df['timestamp'] - start_time).dt.total_seconds())
            
            # Pega os dados mais próximos do tempo do sinal
            closest_data = df.nsmallest(min(20, len(df)), 'time_diff')  # Limitado a 20 pontos
            
            self.logger.debug(f"Microestrutura para {symbol}: {len(closest_data)} pontos próximos")
            return closest_data
            
        except Exception as e:
            elapsed = time.time() - operation_start
            self.logger.warning(f"Erro na microestrutura para {symbol} (após {elapsed:.1f}s): {e}")
            return None
    
    def check_symbol_data_availability(self, symbol: str, min_records: int = 50) -> Dict[str, Any]:
        """Verifica se o símbolo tem dados suficientes APENAS em 5m e 15m"""
        enabled_timeframes = ["5m", "15m"]  # HARDCODED para evitar problemas
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
                with self._get_connection(timeout=3) as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, (symbol, timeframe))
                    row = cursor.fetchone()
                    
                    count = row[0] if row else 0
                    
                    # CONFIGURAÇÃO RELAXADA: Usa configuração dinâmica
                    tf_config = settings.get_timeframe_config(timeframe)
                    min_required = tf_config.min_data_points
                    
                    results[timeframe] = {
                        'count': count,
                        'sufficient': count >= min_required,
                        'min_required': min_required,
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
        """Retorna apenas símbolos com dados suficientes - VERSÃO ROBUSTA"""
        all_symbols = settings.get_analysis_symbols()
        valid_symbols = []
        
        self.logger.info(f"Verificando {len(all_symbols)} símbolos...")
        
        for i, symbol in enumerate(all_symbols, 1):
            try:
                start_time = time.time()
                check_result = self.check_symbol_data_availability(symbol)
                elapsed = time.time() - start_time
                
                if elapsed > 2.0:
                    self.logger.warning(f"Verificação lenta para {symbol}: {elapsed:.1f}s")
                
                if check_result['has_sufficient_data']:
                    valid_symbols.append(symbol)
                    self.logger.debug(f"✅ {symbol} ({i}/{len(all_symbols)}): Válido")
                else:
                    timeframes_info = check_result['timeframes']
                    missing_info = []
                    for tf, info in timeframes_info.items():
                        if not info['sufficient']:
                            missing_info.append(f"{tf}:{info['count']}/{info.get('min_required', 0)}")
                    
                    self.logger.warning(f"❌ {symbol} ({i}/{len(all_symbols)}): Dados insuficientes - {', '.join(missing_info)}")
                
                # Pausa pequena para evitar sobrecarga
                time.sleep(0.05)
                
            except Exception as e:
                self.logger.error(f"Erro ao verificar {symbol}: {e}")
                continue
        
        self.logger.info(f"✅ Símbolos válidos: {len(valid_symbols)}/{len(all_symbols)} - {valid_symbols}")
        return valid_symbols
    
    def get_available_symbols(self) -> List[str]:
        """Lista símbolos disponíveis no banco com timeout"""
        query = f"SELECT DISTINCT symbol FROM {self.stream_table} LIMIT 100"
        try:
            with self._get_connection(timeout=3) as conn:
                result = pd.read_sql_query(query, conn)
                return result['symbol'].tolist()
        except Exception as e:
            self.logger.error(f"Erro ao buscar symbols disponíveis: {e}")
            return []
    
    def test_microstructure_connection(self) -> dict:
        """Testa a conexão e estrutura da tabela de microestrutura COM TIMEOUT"""
        microstructure_table = settings.validation.microstructure_table
        
        result = {
            'table_exists': False,
            'has_data': False,
            'sample_symbols': [],
            'sample_data_count': 0,
            'latest_data': None,
            'error': None
        }
        
        start_time = time.time()
        timeout_seconds = 3.0
        
        try:
            with self._get_connection(timeout=2) as conn:
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
                
                # Timeout check
                if time.time() - start_time > timeout_seconds:
                    result['error'] = "Timeout na verificação"
                    return result
                
                # Verifica se há dados (com LIMIT para evitar lentidão)
                recent_time_filter = int((datetime.utcnow() - timedelta(hours=24)).timestamp())
                cursor.execute(f"SELECT 1 FROM {microstructure_table} WHERE kline_close_time >= ? LIMIT 1", (recent_time_filter,))
                count = cursor.fetchone()[0]
                result['has_data'] = count > 0
                result['sample_data_count'] = min(count, 10000)  # Limita para não sobrecarregar
                
                if count > 0:
                    # Busca símbolos únicos (limitado)
                    cursor.execute(f"SELECT DISTINCT symbol FROM {microstructure_table} LIMIT 5")
                    symbols = [row[0] for row in cursor.fetchall()]
                    result['sample_symbols'] = symbols
                    
                    # Timeout check novamente
                    if time.time() - start_time > timeout_seconds:
                        result['error'] = "Timeout na amostragem"
                        return result
                    
                    # Busca dados mais recentes (limitado)
                    cursor.execute(f"""
                        SELECT symbol, kline_close_time, close_price 
                        FROM {microstructure_table} 
                        ORDER BY kline_close_time DESC 
                        LIMIT 3
                    """)
                    latest = cursor.fetchall()
                    result['latest_data'] = latest
                    
                    elapsed = time.time() - start_time
                    self.logger.debug(f"Teste de microestrutura: {count} registros, símbolos: {symbols} ({elapsed:.1f}s)")
                
        except Exception as e:
            elapsed = time.time() - start_time
            result['error'] = f"{str(e)} (após {elapsed:.1f}s)"
            self.logger.warning(f"Erro ao testar microestrutura: {result['error']}")
        
        return result

    def clear_cache(self):
        """Limpa o cache interno"""
        self._cache.clear()
        self.logger.debug("Cache limpo")