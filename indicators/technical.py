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
        # _#_CORRIGIDO_: Garante que a análise use um slice que termina no candle fechado.
        df_closed = market_data.data.iloc[:-1]

        if len(df_closed) < self.period + 5:
            return IndicatorResult("RSI", pd.Series(dtype=float), [], {})

        close_prices = df_closed['close_price']
        rsi_levels = settings.get_rsi_levels(timeframe)
        overbought = rsi_levels['overbought']
        oversold = rsi_levels['oversold']

        rsi = self.calculate_rsi(close_prices)
        if rsi.empty:
            return IndicatorResult("RSI", rsi, [], {})

        # Pega o valor mais recente do RSI, que corresponde ao último candle fechado.
        latest_rsi = rsi.iloc[-1]

        signals = []
        if latest_rsi >= overbought:
            signals.append({'type': 'rsi_overbought', 'signal_type': 'SELL_SHORT', 'confidence': 0.75, 'priority': 'high'})
        elif latest_rsi <= oversold:
            signals.append({'type': 'rsi_oversold', 'signal_type': 'BUY_LONG', 'confidence': 0.75, 'priority': 'high'})

        # O metadata pode usar o RSI do candle atual para simples informação
        current_rsi_full = self.calculate_rsi(market_data.data['close_price'])
        return IndicatorResult("RSI", rsi, signals, {'current_rsi': current_rsi_full.iloc[-1] if not current_rsi_full.empty else 50.0})

# Substitua a classe MACDAnalyzer inteira por este código:
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
        params = settings.get_macd_params(timeframe)
        # _#_CORRIGIDO_: Garante que a análise use um slice que termina no candle fechado.
        df_closed = market_data.data.iloc[:-1]

        if len(df_closed) < params['slow'] + 5:
            return IndicatorResult("MACD", pd.Series(dtype=float), [], {})

        close_prices = df_closed['close_price']
        macd, signal, _ = self.calculate_macd(close_prices, params)

        if len(macd) < 2:
            return IndicatorResult("MACD", macd, [], {})

        # Usa os dois últimos pontos de dados (que são do penúltimo e antepenúltimo candles fechados)
        latest_macd, prev_macd = macd.iloc[-1], macd.iloc[-2]
        latest_signal, prev_signal = signal.iloc[-1], signal.iloc[-2]

        signals = []
        # Detecção de cruzamento
        if prev_macd <= prev_signal and latest_macd > latest_signal:
            signals.append({'type': 'macd_bullish_crossover', 'signal_type': 'BUY_LONG', 'confidence': 0.8, 'priority': 'crossover'})
        elif prev_macd >= prev_signal and latest_macd < latest_signal:
            signals.append({'type': 'macd_bearish_crossover', 'signal_type': 'SELL_SHORT', 'confidence': 0.8, 'priority': 'crossover'})

        # O metadata pode usar o MACD do candle atual para simples informação
        full_macd, full_signal, _ = self.calculate_macd(market_data.data['close_price'], params)
        return IndicatorResult("MACD", macd, signals, {'current_macd': full_macd.iloc[-1], 'current_signal': full_signal.iloc[-1]})


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

        # NOVO: Inclui market_data para cálculo técnico de stop/targets
        return [EnhancedTradingSignal(
            symbol=market_data.symbol,
            signal_type=best_signal['signal_type'],
            entry_price=market_data.latest_price,
            confidence=best_signal['confidence'],
            timeframe=timeframe,
            detector_type='technical',
            detector_name=best_signal['indicator'],
            market_data=market_data.data  # ADICIONADO para cálculo técnico
        )]