"""
Indicadores Técnicos - RSI, MACD, Bollinger Bands, etc.
"""
import pandas as pd
import numpy as np
import talib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging

from core.data_reader import MarketData
from core.signal_writer import TradingSignal
from config.settings import settings

@dataclass
class IndicatorResult:
    """Resultado de um indicador"""
    name: str
    values: pd.Series
    signals: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    
    @property
    def latest_value(self) -> float:
        """Último valor do indicador"""
        return float(self.values.iloc[-1]) if not self.values.empty else 0.0
    
    @property
    def has_signals(self) -> bool:
        """Verifica se tem sinais"""
        return len(self.signals) > 0

class RSIAnalyzer:
    """Analisador de RSI com detecção de divergências"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.period = settings.indicators.rsi_period
        self.overbought = settings.indicators.rsi_overbought
        self.oversold = settings.indicators.rsi_oversold
        self.divergence_lookback = settings.indicators.rsi_divergence_lookback
    
    def calculate_rsi(self, close_prices: pd.Series) -> pd.Series:
        """Calcula RSI usando TA-Lib"""
        try:
            rsi = talib.RSI(close_prices.values, timeperiod=self.period)
            return pd.Series(rsi, index=close_prices.index)
        except Exception as e:
            self.logger.error(f"Erro ao calcular RSI: {e}")
            return pd.Series(dtype=float)
    
    def detect_divergences(self, prices: pd.Series, rsi: pd.Series) -> List[Dict[str, Any]]:
        """
        Detecta divergências entre preço e RSI
        
        Args:
            prices: Série de preços de fechamento
            rsi: Série de valores RSI
        
        Returns:
            Lista de divergências encontradas
        """
        divergences = []
        
        if len(prices) < self.divergence_lookback * 2:
            return divergences
        
        # Encontra picos e vales nos preços
        price_peaks = self._find_peaks(prices, self.divergence_lookback // 2)
        price_valleys = self._find_valleys(prices, self.divergence_lookback // 2)
        
        # Encontra picos e vales no RSI
        rsi_peaks = self._find_peaks(rsi, self.divergence_lookback // 2)
        rsi_valleys = self._find_valleys(rsi, self.divergence_lookback // 2)
        
        # Detecta divergência de alta (preço faz vale mais baixo, RSI faz vale mais alto)
        for i in range(1, len(price_valleys)):
            current_valley = price_valleys[i]
            previous_valley = price_valleys[i-1]
            
            # Encontra vales correspondentes no RSI
            rsi_valley_current = self._find_nearest_valley(rsi_valleys, current_valley)
            rsi_valley_previous = self._find_nearest_valley(rsi_valleys, previous_valley)
            
            if rsi_valley_current is not None and rsi_valley_previous is not None:
                # Preço mais baixo, RSI mais alto = divergência de alta
                if (prices.iloc[current_valley] < prices.iloc[previous_valley] and
                    rsi.iloc[rsi_valley_current] > rsi.iloc[rsi_valley_previous]):
                    
                    divergences.append({
                        'type': 'bullish_divergence',
                        'timestamp': prices.index[current_valley],
                        'price_valley': prices.iloc[current_valley],
                        'rsi_valley': rsi.iloc[rsi_valley_current],
                        'strength': self._calculate_divergence_strength(
                            prices.iloc[previous_valley], prices.iloc[current_valley],
                            rsi.iloc[rsi_valley_previous], rsi.iloc[rsi_valley_current]
                        ),
                        'confidence': 0.7
                    })
        
        # Detecta divergência de baixa (preço faz pico mais alto, RSI faz pico mais baixo)
        for i in range(1, len(price_peaks)):
            current_peak = price_peaks[i]
            previous_peak = price_peaks[i-1]
            
            # Encontra picos correspondentes no RSI
            rsi_peak_current = self._find_nearest_peak(rsi_peaks, current_peak)
            rsi_peak_previous = self._find_nearest_peak(rsi_peaks, previous_peak)
            
            if rsi_peak_current is not None and rsi_peak_previous is not None:
                # Preço mais alto, RSI mais baixo = divergência de baixa
                if (prices.iloc[current_peak] > prices.iloc[previous_peak] and
                    rsi.iloc[rsi_peak_current] < rsi.iloc[rsi_peak_previous]):
                    
                    divergences.append({
                        'type': 'bearish_divergence',
                        'timestamp': prices.index[current_peak],
                        'price_peak': prices.iloc[current_peak],
                        'rsi_peak': rsi.iloc[rsi_peak_current],
                        'strength': self._calculate_divergence_strength(
                            prices.iloc[previous_peak], prices.iloc[current_peak],
                            rsi.iloc[rsi_peak_previous], rsi.iloc[rsi_peak_current]
                        ),
                        'confidence': 0.7
                    })
        
        return divergences
    
    def _find_peaks(self, series: pd.Series, window: int) -> List[int]:
        """Encontra picos locais"""
        peaks = []
        for i in range(window, len(series) - window):
            if series.iloc[i] == series.iloc[i-window:i+window+1].max():
                peaks.append(i)
        return peaks
    
    def _find_valleys(self, series: pd.Series, window: int) -> List[int]:
        """Encontra vales locais"""
        valleys = []
        for i in range(window, len(series) - window):
            if series.iloc[i] == series.iloc[i-window:i+window+1].min():
                valleys.append(i)
        return valleys
    
    def _find_nearest_valley(self, valleys: List[int], target_index: int) -> Optional[int]:
        """Encontra vale mais próximo do índice alvo"""
        if not valleys:
            return None
        
        distances = [abs(v - target_index) for v in valleys]
        min_distance_idx = distances.index(min(distances))
        
        # Só aceita se a distância for razoável
        if distances[min_distance_idx] <= self.divergence_lookback // 2:
            return valleys[min_distance_idx]
        
        return None
    
    def _find_nearest_peak(self, peaks: List[int], target_index: int) -> Optional[int]:
        """Encontra pico mais próximo do índice alvo"""
        if not peaks:
            return None
        
        distances = [abs(p - target_index) for p in peaks]
        min_distance_idx = distances.index(min(distances))
        
        # Só aceita se a distância for razoável
        if distances[min_distance_idx] <= self.divergence_lookback // 2:
            return peaks[min_distance_idx]
        
        return None
    
    def _calculate_divergence_strength(self, price1: float, price2: float, 
                                     rsi1: float, rsi2: float) -> float:
        """Calcula força da divergência"""
        price_change = abs((price2 - price1) / price1)
        rsi_change = abs(rsi2 - rsi1) / 100
        
        # Força baseada na magnitude das mudanças
        strength = min(1.0, (price_change + rsi_change) / 0.2)
        return strength
    
    def analyze(self, market_data: MarketData) -> IndicatorResult:
        """
        Analisa RSI e gera sinais
        
        Args:
            market_data: Dados de mercado
        
        Returns:
            Resultado da análise RSI
        """
        df = market_data.data
        close_prices = df['close_price']
        
        # Calcula RSI
        rsi = self.calculate_rsi(close_prices)
        
        if rsi.empty:
            return IndicatorResult(
                name="RSI",
                values=pd.Series(dtype=float),
                signals=[],
                metadata={'error': 'Falha no cálculo do RSI'}
            )
        
        # Detecta sinais básicos
        signals = []
        
        # Sinal de sobrecompra/sobrevenda
        latest_rsi = rsi.iloc[-1]
        
        if latest_rsi >= self.overbought:
            signals.append({
                'type': 'overbought',
                'timestamp': df['timestamp'].iloc[-1],
                'rsi_value': latest_rsi,
                'signal_type': 'SELL',
                'confidence': min(0.8, (latest_rsi - self.overbought) / (100 - self.overbought)),
                'strength': 0.6
            })
        
        elif latest_rsi <= self.oversold:
            signals.append({
                'type': 'oversold',
                'timestamp': df['timestamp'].iloc[-1],
                'rsi_value': latest_rsi,
                'signal_type': 'BUY',
                'confidence': min(0.8, (self.oversold - latest_rsi) / self.oversold),
                'strength': 0.6
            })
        
        # Detecta divergências
        divergences = self.detect_divergences(close_prices, rsi)
        
        for div in divergences:
            signal_type = 'BUY' if div['type'] == 'bullish_divergence' else 'SELL'
            
            signals.append({
                'type': div['type'],
                'timestamp': div['timestamp'],
                'signal_type': signal_type,
                'confidence': div['confidence'],
                'strength': div['strength'],
                'rsi_value': div.get('rsi_valley', div.get('rsi_peak')),
                'price_level': div.get('price_valley', div.get('price_peak'))
            })
        
        # Metadados
        metadata = {
            'rsi_period': self.period,
            'current_rsi': latest_rsi,
            'overbought_level': self.overbought,
            'oversold_level': self.oversold,
            'divergences_found': len(divergences),
            'analysis_timestamp': market_data.last_update
        }
        
        return IndicatorResult(
            name="RSI",
            values=rsi,
            signals=signals,
            metadata=metadata
        )

class MACDAnalyzer:
    """Analisador de MACD"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.fast_period = settings.indicators.macd_fast
        self.slow_period = settings.indicators.macd_slow
        self.signal_period = settings.indicators.macd_signal
    
    def calculate_macd(self, close_prices: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calcula MACD usando TA-Lib"""
        try:
            macd, signal, histogram = talib.MACD(
                close_prices.values,
                fastperiod=self.fast_period,
                slowperiod=self.slow_period,
                signalperiod=self.signal_period
            )
            
            return (
                pd.Series(macd, index=close_prices.index),
                pd.Series(signal, index=close_prices.index),
                pd.Series(histogram, index=close_prices.index)
            )
        except Exception as e:
            self.logger.error(f"Erro ao calcular MACD: {e}")
            return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)
    
    def analyze(self, market_data: MarketData) -> IndicatorResult:
        """Analisa MACD e gera sinais"""
        df = market_data.data
        close_prices = df['close_price']
        
        # Calcula MACD
        macd, signal, histogram = self.calculate_macd(close_prices)
        
        if macd.empty:
            return IndicatorResult(
                name="MACD",
                values=pd.Series(dtype=float),
                signals=[],
                metadata={'error': 'Falha no cálculo do MACD'}
            )
        
        signals = []
        
        # Detecta cruzamentos
        if len(macd) >= 2:
            # Cruzamento de alta (MACD cruza acima da linha de sinal)
            if macd.iloc[-2] <= signal.iloc[-2] and macd.iloc[-1] > signal.iloc[-1]:
                signals.append({
                    'type': 'macd_bullish_crossover',
                    'timestamp': df['timestamp'].iloc[-1],
                    'signal_type': 'BUY',
                    'confidence': 0.65,
                    'strength': min(0.8, abs(macd.iloc[-1] - signal.iloc[-1]) * 1000),
                    'macd_value': macd.iloc[-1],
                    'signal_value': signal.iloc[-1]
                })
            
            # Cruzamento de baixa (MACD cruza abaixo da linha de sinal)
            elif macd.iloc[-2] >= signal.iloc[-2] and macd.iloc[-1] < signal.iloc[-1]:
                signals.append({
                    'type': 'macd_bearish_crossover',
                    'timestamp': df['timestamp'].iloc[-1],
                    'signal_type': 'SELL',
                    'confidence': 0.65,
                    'strength': min(0.8, abs(macd.iloc[-1] - signal.iloc[-1]) * 1000),
                    'macd_value': macd.iloc[-1],
                    'signal_value': signal.iloc[-1]
                })
        
        # Metadados
        metadata = {
            'fast_period': self.fast_period,
            'slow_period': self.slow_period,
            'signal_period': self.signal_period,
            'current_macd': macd.iloc[-1] if not macd.empty else None,
            'current_signal': signal.iloc[-1] if not signal.empty else None,
            'current_histogram': histogram.iloc[-1] if not histogram.empty else None
        }
        
        return IndicatorResult(
            name="MACD",
            values=macd,
            signals=signals,
            metadata=metadata
        )

class TechnicalAnalyzer:
    """Analisador técnico principal que coordena todos os indicadores"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.rsi_analyzer = RSIAnalyzer()
        self.macd_analyzer = MACDAnalyzer()
    
    def analyze_all(self, market_data: MarketData) -> Dict[str, IndicatorResult]:
        """
        Executa todos os indicadores técnicos
        
        Args:
            market_data: Dados de mercado
        
        Returns:
            Dicionário com resultados de todos os indicadores
        """
        results = {}
        
        try:
            # RSI
            rsi_result = self.rsi_analyzer.analyze(market_data)
            results['RSI'] = rsi_result
            
            # MACD
            macd_result = self.macd_analyzer.analyze(market_data)
            results['MACD'] = macd_result
            
            self.logger.info(
                f"Análise técnica concluída para {market_data.symbol}: "
                f"RSI={len(rsi_result.signals)} sinais, "
                f"MACD={len(macd_result.signals)} sinais"
            )
            
        except Exception as e:
            self.logger.error(f"Erro na análise técnica de {market_data.symbol}: {e}")
        
        return results
    
    def generate_trading_signals(self, market_data: MarketData, 
                               analysis_results: Dict[str, IndicatorResult]) -> List[TradingSignal]:
        """
        Gera sinais de trading baseados nos resultados da análise
        
        Args:
            market_data: Dados de mercado
            analysis_results: Resultados dos indicadores
        
        Returns:
            Lista de sinais de trading
        """
        trading_signals = []
        
        for indicator_name, result in analysis_results.items():
            for signal_data in result.signals:
                # Só gera sinais com confiança mínima
                if signal_data.get('confidence', 0) >= settings.analysis.confidence_threshold:
                    
                    trading_signal = TradingSignal(
                        symbol=market_data.symbol,
                        signal_type=signal_data['signal_type'],
                        strategy=f"{indicator_name}_{signal_data['type']}",
                        confidence=signal_data['confidence'],
                        strength=signal_data['strength'],
                        entry_price=market_data.latest_price,
                        timestamp=signal_data['timestamp'],
                        target_timeframe=market_data.timeframe,
                        indicators_used={indicator_name: result.metadata},
                        pattern_data=signal_data,
                        notes=f"Sinal gerado por {indicator_name}"
                    )
                    
                    trading_signals.append(trading_signal)
        
        return trading_signals