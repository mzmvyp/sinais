"""
ADAPTAÇÃO PARA FORMATO PADRÃO DO SISTEMA EXISTENTE
Modifica sinais para seguir padrão: BUY_LONG_analize / SELL_SHORT_analize
"""
import os
import shutil
import time
from datetime import datetime

def create_adapted_signal_writer():
    """Cria SignalWriter adaptado para o formato padrão"""
    
    adapted_code = '''"""
Signal Writer Adaptado - Formato Compatível com Sistema Existente
"""
import sqlite3
import json
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
import logging

from config.settings import settings

@dataclass
class TradingSignal:
    """Estrutura de sinal compatível com sistema existente"""
    symbol: str
    signal_type: str        # BUY_LONG_analize, SELL_SHORT_analize
    entry_price: float
    confidence: float       # 0.0 a 1.0
    
    # Campos obrigatórios do sistema padrão
    targets: List[float] = None
    stop_loss: float = None
    confluence_score: int = 95  # Padrão 95
    status: str = "ACTIVE"
    indicators_used: List[str] = None
    targets_hit: List[bool] = None
    
    # Campos automáticos
    id: str = None
    timestamp: datetime = None
    
    # Campos opcionais de compatibilidade
    strategy: str = ""
    strength: float = 0.0
    target_timeframe: Optional[str] = None
    pattern_data: Optional[Dict] = None
    market_conditions: Optional[Dict] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        
        # Gera ID no formato padrão: SYMBOL_TYPE_TIMESTAMP
        if self.id is None:
            timestamp_int = int(time.time() * 100)  # Timestamp em centésimos
            self.id = f"{self.symbol}_{self.signal_type}_{timestamp_int}"
        
        # Valida e ajusta signal_type para formato padrão
        self._normalize_signal_type()
        
        # Define targets padrão se não fornecido
        if self.targets is None:
            self.targets = self._calculate_default_targets()
        
        # Define stop_loss padrão se não fornecido
        if self.stop_loss is None:
            self.stop_loss = self._calculate_default_stop_loss()
        
        # Define indicators_used padrão
        if self.indicators_used is None:
            self.indicators_used = [f"technical_analize_{self.signal_type.lower()}"]
        
        # Define targets_hit padrão (todos false inicialmente)
        if self.targets_hit is None:
            self.targets_hit = [False] * len(self.targets)
        
        # Converte confidence (0-1) para confluence_score (0-100) se necessário
        if 0 <= self.confidence <= 1:
            # Mapeia confidence para confluence_score (95-100)
            self.confluence_score = int(95 + (self.confidence * 5))
    
    def _normalize_signal_type(self):
        """Normaliza signal_type para formato padrão"""
        if self.signal_type in ['BUY', 'buy']:
            self.signal_type = 'BUY_LONG_analize'
        elif self.signal_type in ['SELL', 'sell']:
            self.signal_type = 'SELL_SHORT_analize'
        elif not self.signal_type.endswith('_analize'):
            # Se já está no formato correto mas sem sufixo
            if 'BUY' in self.signal_type.upper():
                self.signal_type = 'BUY_LONG_analize'
            elif 'SELL' in self.signal_type.upper():
                self.signal_type = 'SELL_SHORT_analize'
    
    def _calculate_default_targets(self):
        """Calcula targets padrão no formato do sistema existente"""
        if 'BUY' in self.signal_type:
            # Targets para BUY_LONG: 3 níveis crescentes
            return [
                self.entry_price * 1.015,  # +1.5%
                self.entry_price * 1.025,  # +2.5%  
                self.entry_price * 1.04    # +4.0%
            ]
        else:
            # Targets para SELL_SHORT: 3 níveis decrescentes
            return [
                self.entry_price * 0.985,  # -1.5%
                self.entry_price * 0.975,  # -2.5%
                self.entry_price * 0.96    # -4.0%
            ]
    
    def _calculate_default_stop_loss(self):
        """Calcula stop_loss padrão"""
        if 'BUY' in self.signal_type:
            return self.entry_price * 0.97  # -3% para BUY_LONG
        else:
            return self.entry_price * 1.03  # +3% para SELL_SHORT
    
    def to_database_format(self):
        """Converte para formato do banco de dados"""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'signal_type': self.signal_type,
            'entry_price': self.entry_price,
            'targets': json.dumps(self.targets),
            'stop_loss': self.stop_loss,
            'confidence': self.confidence,
            'confluence_score': self.confluence_score,
            'status': self.status,
            'created_at': self.timestamp.isoformat(),
            'entry_time': self.timestamp.isoformat(),
            'exit_time': None,
            'current_price': self.entry_price,  # Inicial = entry_price
            'pnl_percentage': 0.0,
            'pnl_absolute': 0.0,
            'duration_hours': 0.0,
            'targets_hit': json.dumps(self.targets_hit),
            'indicators_used': json.dumps(self.indicators_used),
            'volume_confirmed': 1 if self.confluence_score >= 100 else 0,
            'risk_reward_ratio': self._calculate_risk_reward(),
            'max_profit': 0.0,
            'max_drawdown': 0.0,
            'updated_at': self.timestamp.isoformat()
        }
    
    def _calculate_risk_reward(self):
        """Calcula risk/reward ratio"""
        if not self.targets:
            return 1.0
        
        target_distance = abs(self.targets[0] - self.entry_price)
        stop_distance = abs(self.stop_loss - self.entry_price)
        
        if stop_distance > 0:
            return target_distance / stop_distance
        return 1.0

class SignalWriter:
    """Writer adaptado para formato padrão"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.signals_db_path = settings.database.signals_db_path
        self.signals_table = "trading_signals_v2"
        self._ensure_table_exists()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Cria conexão com banco de sinais"""
        try:
            conn = sqlite3.connect(self.signals_db_path)
            return conn
        except sqlite3.Error as e:
            self.logger.error(f"Erro ao conectar com banco de sinais: {e}")
            raise
    
    def _ensure_table_exists(self):
        """Garante que a tabela existe com estrutura correta"""
        # A tabela já existe, apenas verifica
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{self.signals_table}'")
                if cursor.fetchone():
                    self.logger.info(f"Tabela {self.signals_table} verificada")
                else:
                    self.logger.warning(f"Tabela {self.signals_table} não encontrada")
        except Exception as e:
            self.logger.error(f"Erro ao verificar tabela: {e}")
    
    def write_signal(self, signal: TradingSignal) -> bool:
        """Escreve sinal no formato padrão"""
        
        # Verifica se já existe sinal ativo para este symbol
        if self._has_active_signal_for_symbol(signal.symbol):
            self.logger.info(f"Symbol {signal.symbol} já possui sinal ativo - pulando")
            return False
        
        insert_sql = f"""
        INSERT OR REPLACE INTO {self.signals_table} (
            id, symbol, signal_type, entry_price, targets, stop_loss,
            confidence, confluence_score, status, created_at, entry_time,
            exit_time, current_price, pnl_percentage, pnl_absolute,
            duration_hours, targets_hit, indicators_used, volume_confirmed,
            risk_reward_ratio, max_profit, max_drawdown, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            data = signal.to_database_format()
            
            values = (
                data['id'], data['symbol'], data['signal_type'], data['entry_price'],
                data['targets'], data['stop_loss'], data['confidence'], data['confluence_score'],
                data['status'], data['created_at'], data['entry_time'], data['exit_time'],
                data['current_price'], data['pnl_percentage'], data['pnl_absolute'],
                data['duration_hours'], data['targets_hit'], data['indicators_used'],
                data['volume_confirmed'], data['risk_reward_ratio'], data['max_profit'],
                data['max_drawdown'], data['updated_at']
            )
            
            with self._get_connection() as conn:
                conn.execute(insert_sql, values)
                conn.commit()
            
            self.logger.info(
                f"Sinal padrão gravado: {signal.symbol} {signal.signal_type} "
                f"(conf: {signal.confluence_score}, ID: {signal.id[:12]})"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao gravar sinal padrão: {e}")
            return False
    
    def _has_active_signal_for_symbol(self, symbol: str) -> bool:
        """Verifica se symbol já tem sinal ativo"""
        try:
            query = f"""
            SELECT COUNT(*) FROM {self.signals_table}
            WHERE symbol = ? AND status = 'ACTIVE'
            """
            
            with self._get_connection() as conn:
                cursor = conn.execute(query, (symbol,))
                count = cursor.fetchone()[0]
                return count > 0
                
        except Exception as e:
            self.logger.error(f"Erro ao verificar sinais ativos: {e}")
            return False  # Em caso de erro, permite criar
    
    def write_multiple_signals(self, signals: List[TradingSignal]) -> int:
        """Escreve múltiplos sinais"""
        success_count = 0
        
        for signal in signals:
            if self.write_signal(signal):
                success_count += 1
        
        self.logger.info(f"Gravados {success_count}/{len(signals)} sinais padrão")
        return success_count
    
    def get_active_signals(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Busca sinais ativos"""
        query = f"SELECT * FROM {self.signals_table} WHERE status = 'ACTIVE'"
        
        params = []
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        
        query += " ORDER BY created_at DESC"
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(query, params)
                columns = [description[0] for description in cursor.description]
                
                results = []
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    
                    # Deserializa campos JSON
                    for field in ['targets', 'targets_hit', 'indicators_used']:
                        if row_dict.get(field):
                            try:
                                row_dict[field] = json.loads(row_dict[field])
                            except json.JSONDecodeError:
                                row_dict[field] = None
                    
                    results.append(row_dict)
                
                return results
                
        except Exception as e:
            self.logger.error(f"Erro ao buscar sinais ativos: {e}")
            return []
    
    def get_signal_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas dos sinais"""
        try:
            with self._get_connection() as conn:
                # Estatísticas gerais
                general_stats = conn.execute(f"""
                    SELECT 
                        COUNT(*) as total_signals,
                        COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) as active_signals,
                        COUNT(DISTINCT symbol) as symbols_count,
                        AVG(confidence) as avg_confidence,
                        AVG(confluence_score) as avg_confluence
                    FROM {self.signals_table}
                """).fetchone()
                
                # Contagem por tipo
                type_stats = conn.execute(f"""
                    SELECT signal_type, COUNT(*) as count
                    FROM {self.signals_table}
                    GROUP BY signal_type
                """).fetchall()
                
                return {
                    'total_signals': general_stats[0] or 0,
                    'active_signals': general_stats[1] or 0,
                    'symbols_count': general_stats[2] or 0,
                    'avg_confidence': round(general_stats[3] or 0, 3),
                    'avg_confluence': round(general_stats[4] or 0, 3),
                    'by_type': {row[0]: row[1] for row in type_stats}
                }
                
        except Exception as e:
            self.logger.error(f"Erro ao buscar estatísticas: {e}")
            return {'error': str(e)}
    
    def cleanup_old_signals(self, days_old: int = 7) -> int:
        """Remove sinais antigos"""
        delete_sql = f"""
        DELETE FROM {self.signals_table}
        WHERE created_at < datetime('now', '-{days_old} days')
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(delete_sql)
                removed_count = cursor.rowcount
                conn.commit()
            
            self.logger.info(f"Removidos {removed_count} sinais antigos")
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Erro ao limpar sinais antigos: {e}")
            return 0
'''
    
    return adapted_code

def create_adapted_technical_analyzer():
    """Cria TechnicalAnalyzer que gera sinais no formato padrão"""
    
    technical_code = '''"""
Technical Analyzer Adaptado - Gera sinais no formato padrão
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False

@dataclass
class IndicatorResult:
    """Resultado de um indicador"""
    name: str
    values: pd.Series
    signals: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    
    @property
    def latest_value(self) -> float:
        return float(self.values.iloc[-1]) if not self.values.empty else 0.0
    
    @property
    def has_signals(self) -> bool:
        return len(self.signals) > 0

class RSIAnalyzer:
    """RSI Analyzer adaptado"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.period = 14
        self.overbought = 58  
        self.oversold = 42    
    
    def calculate_rsi(self, close_prices: pd.Series) -> pd.Series:
        """Calcula RSI"""
        try:
            clean_prices = close_prices.dropna()
            
            if len(clean_prices) < self.period + 5:
                return pd.Series([50.0] * len(close_prices), index=close_prices.index)
            
            if TALIB_AVAILABLE:
                try:
                    prices_array = clean_prices.values.astype(np.float64)
                    rsi_values = talib.RSI(prices_array, timeperiod=self.period)
                    
                    if not np.isnan(rsi_values[-1]):
                        rsi_series = pd.Series(rsi_values, index=clean_prices.index).fillna(50.0)
                        full_rsi = pd.Series(index=close_prices.index, dtype=float)
                        full_rsi.loc[clean_prices.index] = rsi_series
                        full_rsi = full_rsi.fillna(50.0)
                        return full_rsi
                except Exception:
                    pass
            
            return self._calculate_manual_rsi(close_prices)
            
        except Exception:
            return pd.Series([50.0] * len(close_prices), index=close_prices.index)
    
    def _calculate_manual_rsi(self, prices: pd.Series) -> pd.Series:
        """RSI manual"""
        try:
            full_prices = prices.fillna(method='ffill').fillna(method='bfill')
            delta = full_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.period, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.period, min_periods=1).mean()
            loss = loss.replace(0, 0.0001)
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.fillna(50.0)
        except Exception:
            return pd.Series([50.0] * len(prices), index=prices.index)
    
    def analyze(self, market_data):
        """Análise RSI"""
        df = market_data.data
        close_prices = df['close_price']
        rsi = self.calculate_rsi(close_prices)
        latest_rsi = rsi.iloc[-1]
        
        signals = []
        timestamp = df['timestamp'].iloc[-1]
        
        # Determina tipo de sinal e confidence
        if latest_rsi >= self.overbought:
            signal_type = 'SELL_SHORT_analize'
            confidence = min(0.95, (latest_rsi - self.overbought) / (100 - self.overbought) + 0.5)
            priority = 'high'
        elif latest_rsi <= self.oversold:
            signal_type = 'BUY_LONG_analize'
            confidence = min(0.95, (self.oversold - latest_rsi) / self.oversold + 0.5)
            priority = 'high'
        elif latest_rsi > 50:
            signal_type = 'SELL_SHORT_analize'
            confidence = 0.4 + (latest_rsi - 50) / 50 * 0.3
            priority = 'medium'
        else:
            signal_type = 'BUY_LONG_analize'
            confidence = 0.4 + (50 - latest_rsi) / 50 * 0.3
            priority = 'medium'
        
        signals.append({
            'type': f'rsi_{signal_type.lower()}',
            'timestamp': timestamp,
            'rsi_value': latest_rsi,
            'signal_type': signal_type,
            'confidence': confidence,
            'strength': 0.7 if priority == 'high' else 0.5,
            'priority': priority,
            'indicator': 'RSI'
        })
        
        return IndicatorResult(
            name="RSI",
            values=rsi,
            signals=signals,
            metadata={'current_rsi': latest_rsi, 'signal_format': 'standard'}
        )

class MACDAnalyzer:
    """MACD Analyzer adaptado"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.fast_period = 12
        self.slow_period = 26
        self.signal_period = 9
    
    def calculate_macd(self, close_prices: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calcula MACD"""
        try:
            clean_prices = close_prices.dropna()
            
            if len(clean_prices) < self.slow_period + self.signal_period + 5:
                zero_series = pd.Series([0.0] * len(close_prices), index=close_prices.index)
                return zero_series, zero_series, zero_series
            
            if TALIB_AVAILABLE:
                try:
                    prices_array = clean_prices.values.astype(np.float64)
                    macd, signal, histogram = talib.MACD(prices_array, 
                                                       fastperiod=self.fast_period,
                                                       slowperiod=self.slow_period, 
                                                       signalperiod=self.signal_period)
                    
                    if not np.isnan(macd[-1]):
                        macd_series = pd.Series(macd, index=clean_prices.index).fillna(0.0)
                        signal_series = pd.Series(signal, index=clean_prices.index).fillna(0.0)
                        histogram_series = pd.Series(histogram, index=clean_prices.index).fillna(0.0)
                        
                        full_macd = pd.Series(index=close_prices.index, dtype=float).fillna(0.0)
                        full_signal = pd.Series(index=close_prices.index, dtype=float).fillna(0.0)
                        full_histogram = pd.Series(index=close_prices.index, dtype=float).fillna(0.0)
                        
                        full_macd.loc[clean_prices.index] = macd_series
                        full_signal.loc[clean_prices.index] = signal_series
                        full_histogram.loc[clean_prices.index] = histogram_series
                        
                        return full_macd, full_signal, full_histogram
                except Exception:
                    pass
            
            return self._calculate_manual_macd(close_prices)
            
        except Exception:
            zero_series = pd.Series([0.0] * len(close_prices), index=close_prices.index)
            return zero_series, zero_series, zero_series
    
    def _calculate_manual_macd(self, prices: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD manual"""
        try:
            full_prices = prices.fillna(method='ffill').fillna(method='bfill')
            ema_fast = full_prices.ewm(span=self.fast_period, min_periods=1).mean()
            ema_slow = full_prices.ewm(span=self.slow_period, min_periods=1).mean()
            macd = ema_fast - ema_slow
            signal = macd.ewm(span=self.signal_period, min_periods=1).mean()
            histogram = macd - signal
            return macd, signal, histogram
        except Exception:
            zero_series = pd.Series([0.0] * len(prices), index=prices.index)
            return zero_series, zero_series, zero_series
    
    def analyze(self, market_data):
        """Análise MACD"""
        df = market_data.data
        close_prices = df['close_price']
        macd, signal, histogram = self.calculate_macd(close_prices)
        
        latest_macd = macd.iloc[-1]
        latest_signal = signal.iloc[-1]
        timestamp = df['timestamp'].iloc[-1]
        
        signals = []
        
        # Verifica cruzamentos primeiro (prioridade alta)
        if len(macd) >= 2:
            prev_macd = macd.iloc[-2]
            prev_signal = signal.iloc[-2]
            
            if prev_macd <= prev_signal and latest_macd > latest_signal:
                # Cruzamento bullish
                signals.append({
                    'type': 'macd_bullish_crossover',
                    'timestamp': timestamp,
                    'signal_type': 'BUY_LONG_analize',
                    'confidence': min(0.9, abs(latest_macd - latest_signal) * 100000 + 0.6),
                    'strength': 0.8,
                    'priority': 'crossover',
                    'indicator': 'MACD'
                })
            elif prev_macd >= prev_signal and latest_macd < latest_signal:
                # Cruzamento bearish
                signals.append({
                    'type': 'macd_bearish_crossover',
                    'timestamp': timestamp,
                    'signal_type': 'SELL_SHORT_analize',
                    'confidence': min(0.9, abs(latest_macd - latest_signal) * 100000 + 0.6),
                    'strength': 0.8,
                    'priority': 'crossover',
                    'indicator': 'MACD'
                })
        
        # Se não há cruzamento, usa posição relativa
        if not signals:
            if latest_macd >= latest_signal:
                signals.append({
                    'type': 'macd_above_signal',
                    'timestamp': timestamp,
                    'signal_type': 'BUY_LONG_analize',
                    'confidence': 0.4 + min(0.4, abs(latest_macd - latest_signal) * 50000),
                    'strength': 0.5,
                    'priority': 'position',
                    'indicator': 'MACD'
                })
            else:
                signals.append({
                    'type': 'macd_below_signal',
                    'timestamp': timestamp,
                    'signal_type': 'SELL_SHORT_analize',
                    'confidence': 0.4 + min(0.4, abs(latest_macd - latest_signal) * 50000),
                    'strength': 0.5,
                    'priority': 'position',
                    'indicator': 'MACD'
                })
        
        return IndicatorResult(
            name="MACD",
            values=macd,
            signals=signals,
            metadata={'current_macd': latest_macd, 'current_signal': latest_signal}
        )

class TechnicalAnalyzer:
    """Technical Analyzer para formato padrão"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.rsi_analyzer = RSIAnalyzer()
        self.macd_analyzer = MACDAnalyzer()
    
    def analyze_all(self, market_data):
        """Executa análise"""
        results = {}
        
        try:
            rsi_result = self.rsi_analyzer.analyze(market_data)
            results['RSI'] = rsi_result
            
            macd_result = self.macd_analyzer.analyze(market_data)
            results['MACD'] = macd_result
            
            total_signals = sum(len(r.signals) for r in results.values())
            self.logger.info(f"Análise técnica concluída para {market_data.symbol}: RSI={len(rsi_result.signals)}, MACD={len(macd_result.signals)}")
            
        except Exception as e:
            self.logger.error(f"Erro na análise técnica: {e}")
        
        return results
    
    def generate_trading_signals(self, market_data, analysis_results):
        """Gera 1 sinal no formato padrão"""
        from core.signal_writer import TradingSignal
        from config.settings import settings
        
        # Verifica se já existe sinal ativo
        from core.signal_writer import SignalWriter
        writer = SignalWriter()
        
        if writer._has_active_signal_for_symbol(market_data.symbol):
            return []
        
        # Coleta todos os sinais
        all_signals = []
        for indicator_name, result in analysis_results.items():
            for signal_data in result.signals:
                signal_data['indicator'] = indicator_name
                all_signals.append(signal_data)
        
        if not all_signals:
            return []
        
        # Escolhe o melhor sinal
        best_signal = self._select_best_signal(all_signals)
        if not best_signal:
            return []
        
        # Verifica confidence mínima
        min_confidence = getattr(settings.analysis, 'confidence_threshold', 0.05)
        if best_signal['confidence'] < min_confidence:
            return []
        
        # Cria TradingSignal no formato padrão
        trading_signal = TradingSignal(
            symbol=market_data.symbol,
            signal_type=best_signal['signal_type'],  # Já no formato BUY_LONG_analize/SELL_SHORT_analize
            entry_price=market_data.latest_price,
            confidence=best_signal['confidence'],
            indicators_used=[f"{best_signal['indicator'].lower()}_analize"]
        )
        
        return [trading_signal]
    
    def _select_best_signal(self, all_signals):
        """Seleciona melhor sinal"""
        if not all_signals:
            return None
        
        # Prioridades: crossover > high > medium > position
        crossover_signals = [s for s in all_signals if s.get('priority') == 'crossover']
        high_signals = [s for s in all_signals if s.get('priority') == 'high']
        other_signals = [s for s in all_signals if s.get('priority') not in ['crossover', 'high']]
        
        if crossover_signals:
            return max(crossover_signals, key=lambda x: x['confidence'])
        elif high_signals:
            return max(high_signals, key=lambda x: x['confidence'])
        elif other_signals:
            return max(other_signals, key=lambda x: x['confidence'])
        
        return None
'''
    
    return technical_code

def apply_format_adaptation():
    """Aplica adaptação completa para formato padrão"""
    print("🔧 APLICANDO ADAPTAÇÃO PARA FORMATO PADRÃO")
    print("=" * 60)
    
    try:
        # Backup dos arquivos originais
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        signal_writer_backup = f"core/signal_writer_backup_format_{timestamp}.py"
        technical_backup = f"indicators/technical_backup_format_{timestamp}.py"
        
        if os.path.exists("core/signal_writer.py"):
            shutil.copy2("core/signal_writer.py", signal_writer_backup)
            print(f"✅ Backup SignalWriter: {signal_writer_backup}")
        
        if os.path.exists("indicators/technical.py"):
            shutil.copy2("indicators/technical.py", technical_backup)
            print(f"✅ Backup TechnicalAnalyzer: {technical_backup}")
        
        # Aplica adaptações
        print(f"\n📝 Aplicando adaptações...")
        
        # 1. SignalWriter adaptado
        adapted_signal_writer = create_adapted_signal_writer()
        with open("core/signal_writer.py", 'w', encoding='utf-8') as f:
            f.write(adapted_signal_writer)
        print(f"✅ SignalWriter adaptado aplicado")
        
        # 2. TechnicalAnalyzer adaptado
        adapted_technical = create_adapted_technical_analyzer()
        with open("indicators/technical.py", 'w', encoding='utf-8') as f:
            f.write(adapted_technical)
        print(f"✅ TechnicalAnalyzer adaptado aplicado")
        
        # Teste básico
        print(f"\n🧪 Testando adaptação...")
        
        try:
            import sys
            import importlib
            
            # Limpa cache
            modules_to_remove = [k for k in sys.modules.keys() if k.startswith(('core', 'indicators'))]
            for module in modules_to_remove:
                del sys.modules[module]
            
            # Testa imports
            from core.signal_writer import TradingSignal, SignalWriter
            from indicators.technical import TechnicalAnalyzer
            
            # Teste de instanciação
            signal = TradingSignal(
                symbol="TEST",
                signal_type="BUY",  # Será convertido para BUY_LONG_analize
                entry_price=1000.0,
                confidence=0.8
            )
            
            print(f"✅ TradingSignal de teste:")
            print(f"    - ID: {signal.id}")
            print(f"    - Tipo: {signal.signal_type}")
            print(f"    - Targets: {signal.targets}")
            print(f"    - Confluence: {signal.confluence_score}")
            
            analyzer = TechnicalAnalyzer()
            writer = SignalWriter()
            
            print(f"✅ Instanciação OK")
            return True
            
        except Exception as e:
            print(f"❌ Erro no teste: {e}")
            
            # Restaura backups
            if os.path.exists(signal_writer_backup):
                shutil.copy2(signal_writer_backup, "core/signal_writer.py")
            if os.path.exists(technical_backup):
                shutil.copy2(technical_backup, "indicators/technical.py")
            print(f"✅ Backups restaurados")
            
            return False
    
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return False

def show_format_examples():
    """Mostra exemplos do novo formato"""
    print(f"\n📋 FORMATO PADRÃO APLICADO")
    print("=" * 50)
    print("✅ CONVERSÃO DE TIPOS:")
    print("   BUY  → BUY_LONG_analize")
    print("   SELL → SELL_SHORT_analize")
    print()
    print("✅ ESTRUTURA DO ID:")
    print("   Formato: SYMBOL_TYPE_TIMESTAMP")
    print("   Exemplo: BTC_BUY_LONG_analize_1752540123")
    print()
    print("✅ CAMPOS ADICIONADOS:")
    print("   - targets: [target1, target2, target3]")
    print("   - confluence_score: 95-100")
    print("   - targets_hit: [false, false, false]")
    print("   - indicators_used: ['rsi_analize']")
    print()
    print("✅ EXEMPLO DE SINAL GERADO:")
    print("   ID: ETH_SELL_SHORT_analize_1752540456")
    print("   Type: SELL_SHORT_analize")
    print("   Targets: [2975.47, 2961.88, 2942.12]")
    print("   Confluence: 97")
    print("   Indicators: ['rsi_analize']")
    print()
    print("🚀 COMANDOS PARA TESTAR:")
    print("   python main.py --analyze BTC")
    print("   python main.py --analyze-all")

if __name__ == "__main__":
    print("🔧 EXECUTANDO ADAPTAÇÃO PARA FORMATO PADRÃO")
    print("=" * 70)
    
    success = apply_format_adaptation()
    
    if success:
        print(f"\n🏆 ADAPTAÇÃO APLICADA COM SUCESSO!")
        show_format_examples()
        
        print(f"\n🎯 PRÓXIMOS PASSOS:")
        print("1. Teste: python main.py --analyze BTC")
        print("2. Verifique no banco se o formato está correto")
        print("3. Execute modo contínuo: python main.py --continuous")
    else:
        print(f"\n❌ FALHA NA ADAPTAÇÃO")
        print("   Backups foram restaurados")
    
    print(f"\n{'='*70}")
    print("🏁 ADAPTAÇÃO FINALIZADA")
    print(f"{'='*70}")