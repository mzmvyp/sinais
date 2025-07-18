"""
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
            signal_type = 'SELL_SHORT'
            confidence = min(0.95, (latest_rsi - self.overbought) / (100 - self.overbought) + 0.5)
            priority = 'high'
        elif latest_rsi <= self.oversold:
            signal_type = 'BUY_LONG'
            confidence = min(0.95, (self.oversold - latest_rsi) / self.oversold + 0.5)
            priority = 'high'
        elif latest_rsi > 50:
            signal_type = 'SELL_SHORT'
            confidence = 0.4 + (latest_rsi - 50) / 50 * 0.3
            priority = 'medium'
        else:
            signal_type = 'BUY_LONG'
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
                    'signal_type': 'BUY_LONG',
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
                    'signal_type': 'SELL_SHORT',
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
                    'signal_type': 'BUY_LONG',
                    'confidence': 0.4 + min(0.4, abs(latest_macd - latest_signal) * 50000),
                    'strength': 0.5,
                    'priority': 'position',
                    'indicator': 'MACD'
                })
            else:
                signals.append({
                    'type': 'macd_below_signal',
                    'timestamp': timestamp,
                    'signal_type': 'SELL_SHORT',
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
            signal_type=best_signal['signal_type'],  # Já no formato BUY_LONG/SELL_SHORT
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
