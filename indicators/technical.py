# technical.py

"""
Technical Analyzer Adaptado - Gera sinais no formato padrão
VERSÃO CORRIGIDA: Usa configs por timeframe e evita repainting.
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from config.settings import settings

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False

@dataclass
class IndicatorResult:
    name: str
    values: pd.Series
    signals: List[Dict[str, Any]]
    metadata: Dict[str, Any]

class RSIAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.period = settings.indicators.rsi_period

    def calculate_rsi(self, close_prices: pd.Series) -> pd.Series:
        if len(close_prices) < self.period:
            return pd.Series(dtype=float)
        delta = close_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        rs = gain / (loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50.0)

    def analyze(self, market_data, timeframe: str):
        self.logger.debug(f"Analisando RSI para {market_data.symbol} no timeframe {timeframe}")
        df = market_data.data
        if len(df) < self.period + 5:
            return IndicatorResult("RSI", pd.Series(dtype=float), [], {})

        close_prices = df['close_price']
        rsi_levels = settings.get_rsi_levels(timeframe)
        overbought = rsi_levels['overbought']
        oversold = rsi_levels['oversold']

        rsi = self.calculate_rsi(close_prices)
        if len(rsi) < 2:
            return IndicatorResult("RSI", rsi, [], {})
        
        # _#_ALTERADO_: Opera na vela fechada para evitar repainting
        latest_rsi = rsi.iloc[-2]

        signals = []
        if latest_rsi >= overbought:
            signals.append({'type': 'rsi_overbought', 'signal_type': 'SELL_SHORT', 'confidence': 0.75, 'priority': 'high'})
        elif latest_rsi <= oversold:
            signals.append({'type': 'rsi_oversold', 'signal_type': 'BUY_LONG', 'confidence': 0.75, 'priority': 'high'})

        return IndicatorResult("RSI", rsi, signals, {'current_rsi': rsi.iloc[-1]})

class MACDAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def calculate_macd(self, close_prices: pd.Series, params: Dict) -> Tuple[pd.Series, pd.Series, pd.Series]:
        ema_fast = close_prices.ewm(span=params['fast'], adjust=False).mean()
        ema_slow = close_prices.ewm(span=params['slow'], adjust=False).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=params['signal'], adjust=False).mean()
        histogram = macd - signal
        return macd, signal, histogram

    def analyze(self, market_data, timeframe: str):
        self.logger.debug(f"Analisando MACD para {market_data.symbol} no timeframe {timeframe}")
        df = market_data.data
        params = settings.get_macd_params(timeframe)

        if len(df) < params['slow'] + 5:
            return IndicatorResult("MACD", pd.Series(dtype=float), [], {})

        close_prices = df['close_price']
        macd, signal, _ = self.calculate_macd(close_prices, params)

        if len(macd) < 3:
            return IndicatorResult("MACD", macd, [], {})

        # _#_ALTERADO_: Usa velas fechadas para o sinal (evita repainting)
        latest_macd, prev_macd = macd.iloc[-2], macd.iloc[-3]
        latest_signal, prev_signal = signal.iloc[-2], signal.iloc[-3]

        signals = []
        if prev_macd <= prev_signal and latest_macd > latest_signal:
            signals.append({'type': 'macd_bullish_crossover', 'signal_type': 'BUY_LONG', 'confidence': 0.8, 'priority': 'crossover'})
        elif prev_macd >= prev_signal and latest_macd < latest_signal:
            signals.append({'type': 'macd_bearish_crossover', 'signal_type': 'SELL_SHORT', 'confidence': 0.8, 'priority': 'crossover'})

        return IndicatorResult("MACD", macd, signals, {'current_macd': macd.iloc[-1], 'current_signal': signal.iloc[-1]})

class TechnicalAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.rsi_analyzer = RSIAnalyzer()
        self.macd_analyzer = MACDAnalyzer()

    def analyze_all(self, market_data, timeframe: str):
        results = {}
        try:
            results['RSI'] = self.rsi_analyzer.analyze(market_data, timeframe)
            results['MACD'] = self.macd_analyzer.analyze(market_data, timeframe)
        except Exception as e:
            self.logger.error(f"Erro na análise técnica para {market_data.symbol} {timeframe}: {e}")
        return results

    # _#_ALTERADO_: A função agora recebe 'timeframe' para criar o sinal corretamente.
    def generate_trading_signals(self, market_data, analysis_results, timeframe: str):
        from core.signal_writer import EnhancedTradingSignal

        all_signals = []
        for indicator_name, result in analysis_results.items():
            for signal_data in result.signals:
                signal_data['indicator'] = indicator_name
                all_signals.append(signal_data)

        if not all_signals:
            return []

        best_signal = max(all_signals, key=lambda x: x.get('confidence', 0.5))

        # _#_ALTERADO_: Todos os campos obrigatórios são fornecidos aqui.
        return [EnhancedTradingSignal(
            symbol=market_data.symbol,
            signal_type=best_signal['signal_type'],
            entry_price=market_data.latest_price,
            confidence=best_signal['confidence'],
            timeframe=timeframe,
            detector_type='technical',
            detector_name=best_signal['indicator']
        )]