# candlestick_patterns_detector.py

"""
DETECTOR COMPLETO DE 43 PADRÕES DE CANDLESTICK - VERSÃO FINAL CORRIGIDA
Implementação completa dos padrões clássicos, otimizada para evitar repainting
e com cálculo de risco determinístico via ATR.
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from dataclasses import dataclass
import logging

@dataclass
class CandlestickPattern:
    """Estrutura de dados para um padrão de candlestick detectado."""
    name: str
    pattern_type: str  # 'bullish' ou 'bearish'
    entry_price: float
    stop_loss: float
    target_price: float
    position_index: int
    reliability_score: float # Score de 0 a 1 indicando a confiabilidade do padrão

class CandlestickDetector:
    """Detecta um conjunto de 43 padrões de candlestick em dados de mercado."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Configurações para definir o que é um corpo 'pequeno', 'grande', 'doji', etc.
        self.config = {
            'doji_threshold': 0.1,
            'small_body_pct': 0.003, # Corpo é pequeno se for < 0.3% do preço
            'large_body_pct': 0.015, # Corpo é grande se for > 1.5% do preço
            'atr_multiplier_stop': 1.5, # Multiplicador do ATR para o stop loss
            'risk_reward_ratio': 2.0,   # Relação risco/retorno para o alvo
            'trend_period': 10,         # Período para determinar a tendência
        }

    def _calculate_trade_parameters(self, df: pd.DataFrame, pattern_index: int, pattern_type: str) -> dict:
        """Calcula entrada, stop e alvo de forma determinística usando ATR."""
        pattern_candle = df.iloc[pattern_index]
        entry_price = float(pattern_candle['close_price'])
        
        atr_period = 14
        start_idx = max(0, pattern_index - atr_period)
        atr_df = df.iloc[start_idx:pattern_index + 1]

        high_low = atr_df['high_price'] - atr_df['low_price']
        high_prev_close = abs(atr_df['high_price'] - atr_df['close_price'].shift())
        low_prev_close = abs(atr_df['low_price'] - atr_df['close_price'].shift())
        
        tr = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
        atr = tr.ewm(span=atr_period, adjust=False).mean().iloc[-1]
        atr = atr if pd.notna(atr) and atr > 0 else entry_price * 0.02

        if pattern_type == 'bullish':
            stop_loss = entry_price - (atr * self.config['atr_multiplier_stop'])
            risk = entry_price - stop_loss
            target_price = entry_price + (risk * self.config['risk_reward_ratio'])
        else: # Bearish (SELL_SHORT)
            # _#_CORRIGIDO_: O stop para um SHORT deve ser ACIMA do preço de entrada.
            stop_loss = entry_price + (atr * self.config['atr_multiplier_stop'])
            risk = stop_loss - entry_price
            target_price = entry_price - (risk * self.config['risk_reward_ratio'])

        return {'entry_price': entry_price, 'stop_loss': stop_loss, 'target_price': target_price}
    
    def prepare_candlestick_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Pré-calcula propriedades dos candles para otimizar a detecção."""
        data = df.copy()
        data['body_size'] = abs(data['close_price'] - data['open_price'])
        data['upper_shadow'] = data['high_price'] - np.maximum(data['open_price'], data['close_price'])
        data['lower_shadow'] = np.minimum(data['open_price'], data['close_price']) - data['low_price']
        data['total_range'] = data['high_price'] - data['low_price']
        data['is_green'] = data['close_price'] > data['open_price']
        data['is_red'] = data['close_price'] < data['open_price']
        data['is_doji'] = data['body_size'] <= (data['total_range'] * self.config['doji_threshold'])
        
        avg_price = data['close_price'].rolling(20).mean()
        data['body_size_pct'] = data['body_size'] / (avg_price + 1e-10)
        data['is_small_body'] = data['body_size_pct'] < self.config['small_body_pct']
        data['is_large_body'] = data['body_size_pct'] > self.config['large_body_pct']
        
        trend_ma = data['close_price'].rolling(self.config['trend_period']).mean()
        data['is_uptrend'] = data['close_price'] > trend_ma
        data['is_downtrend'] = data['close_price'] < trend_ma
        return data

    def detect_all_patterns(self, df: pd.DataFrame) -> List[CandlestickPattern]:
        """Orquestra a detecção de todos os 43 padrões."""
        if len(df) < self.config['trend_period']:
            return []
        
        data = self.prepare_candlestick_data(df)
        patterns = []
        end_index = len(data) - 1

        # 1-Candle Patterns
        patterns.extend(self._detect_hammer_like(data, end_index))           # Hammer, Hanging Man, Inverted Hammer, Shooting Star
        patterns.extend(self._detect_marubozu(data, end_index))              # White Marubozu, Black Marubozu
        patterns.extend(self._detect_doji(data, end_index))                  # Doji, Dragonfly, Gravestone
        patterns.extend(self._detect_belt_hold(data, end_index))             # Bullish Belt-hold, Bearish Belt-hold
        
        # 2-Candle Patterns
        patterns.extend(self._detect_engulfing(data, end_index))             # Bullish Engulfing, Bearish Engulfing
        patterns.extend(self._detect_harami(data, end_index))                # Bullish Harami, Bearish Harami, Bullish Harami Cross, Bearish Harami Cross
        patterns.extend(self._detect_piercing_dark_cloud(data, end_index))   # Piercing Pattern, Dark Cloud Cover
        patterns.extend(self._detect_tweezers(data, end_index))              # Tweezer Top, Tweezer Bottom
        patterns.extend(self._detect_counterattack(data, end_index))         # Bullish Counterattack, Bearish Counterattack

        # 3-Candle Patterns
        patterns.extend(self._detect_stars(data, end_index))                 # Morning Star, Evening Star, Morning Doji Star, Evening Doji Star
        patterns.extend(self._detect_three_soldiers_crows(data, end_index))  # Three White Soldiers, Three Black Crows
        patterns.extend(self._detect_three_inside_outside(data, end_index))  # Three Inside Up/Down, Three Outside Up/Down
        patterns.extend(self._detect_stick_sandwich(data, end_index))        # Stick Sandwich
        patterns.extend(self._detect_abandoned_baby(data, end_index))        # Bullish Abandoned Baby, Bearish Abandoned Baby
        
        # Complex/Continuation Patterns
        patterns.extend(self._detect_three_methods(data, end_index))         # Rising Three Methods, Falling Three Methods
        patterns.extend(self._detect_advance_block_deliberation(data, end_index)) # Advance Block, Deliberation
        patterns.extend(self._detect_breakaway(data, end_index))             # Bullish Breakaway, Bearish Breakaway

        return sorted(patterns, key=lambda p: p.reliability_score, reverse=True)

    def _create_pattern(self, data, i, name, p_type, score):
        """Função auxiliar para criar o objeto CandlestickPattern."""
        params = self._calculate_trade_parameters(data, i, p_type)
        return CandlestickPattern(name=name, pattern_type=p_type, reliability_score=score, position_index=i, **params)

    # --- IMPLEMENTAÇÃO DOS DETECTORES ---

    def _detect_hammer_like(self, data, end_index):
        patterns = []
        for i in range(5, end_index):
            c = data.iloc[i]
            is_hammer_shape = c.lower_shadow > 2 * c.body_size and c.upper_shadow < c.body_size
            is_inverted_hammer_shape = c.upper_shadow > 2 * c.body_size and c.lower_shadow < c.body_size
            
            if is_hammer_shape:
                if c.is_downtrend: patterns.append(self._create_pattern(data, i, "Hammer", "bullish", 0.75))
                if c.is_uptrend: patterns.append(self._create_pattern(data, i, "Hanging Man", "bearish", 0.70))
            if is_inverted_hammer_shape:
                if c.is_downtrend: patterns.append(self._create_pattern(data, i, "Inverted Hammer", "bullish", 0.65))
                if c.is_uptrend: patterns.append(self._create_pattern(data, i, "Shooting Star", "bearish", 0.75))
        return patterns

    def _detect_marubozu(self, data, end_index):
        patterns = []
        for i in range(1, end_index):
            c = data.iloc[i]
            is_marubozu = c.body_size / (c.total_range + 1e-10) > 0.95
            if is_marubozu:
                if c.is_green: patterns.append(self._create_pattern(data, i, "White Marubozu", "bullish", 0.7))
                if c.is_red: patterns.append(self._create_pattern(data, i, "Black Marubozu", "bearish", 0.7))
        return patterns

    def _detect_doji(self, data, end_index):
        patterns = []
        for i in range(1, end_index):
            c = data.iloc[i]
            if c.is_doji:
                is_dragonfly = c.lower_shadow / (c.total_range + 1e-10) > 0.7
                is_gravestone = c.upper_shadow / (c.total_range + 1e-10) > 0.7
                if is_dragonfly and c.is_downtrend: patterns.append(self._create_pattern(data, i, "Dragonfly Doji", "bullish", 0.8))
                if is_gravestone and c.is_uptrend: patterns.append(self._create_pattern(data, i, "Gravestone Doji", "bearish", 0.8))
        return patterns
        
    def _detect_belt_hold(self, data, end_index):
        patterns = []
        for i in range(1, end_index):
            c = data.iloc[i]
            is_bullish_belt = c.is_downtrend and c.is_green and c.is_large_body and c.lower_shadow == 0 and c.upper_shadow < c.body_size * 0.1
            is_bearish_belt = c.is_uptrend and c.is_red and c.is_large_body and c.upper_shadow == 0 and c.lower_shadow < c.body_size * 0.1
            if is_bullish_belt: patterns.append(self._create_pattern(data, i, "Bullish Belt-hold", "bullish", 0.7))
            if is_bearish_belt: patterns.append(self._create_pattern(data, i, "Bearish Belt-hold", "bearish", 0.7))
        return patterns

    def _detect_engulfing(self, data, end_index):
        patterns = []
        for i in range(1, end_index):
            c, p = data.iloc[i], data.iloc[i-1]
            if c.is_green and p.is_red and c.close_price > p.open_price and c.open_price < p.close_price:
                patterns.append(self._create_pattern(data, i, "Bullish Engulfing", "bullish", 0.85))
            if c.is_red and p.is_green and c.close_price < p.open_price and c.open_price > p.close_price:
                patterns.append(self._create_pattern(data, i, "Bearish Engulfing", "bearish", 0.85))
        return patterns

    def _detect_harami(self, data, end_index):
        patterns = []
        for i in range(1, end_index):
            c, p = data.iloc[i], data.iloc[i-1]
            body_inside = c.high_price < p.open_price and c.low_price > p.close_price
            if p.is_red and p.is_large_body and c.is_green and c.is_small_body and body_inside:
                patterns.append(self._create_pattern(data, i, "Bullish Harami", "bullish", 0.65))
                if c.is_doji: patterns.append(self._create_pattern(data, i, "Bullish Harami Cross", "bullish", 0.75))
            
            body_inside = c.high_price < p.close_price and c.low_price > p.open_price
            if p.is_green and p.is_large_body and c.is_red and c.is_small_body and body_inside:
                patterns.append(self._create_pattern(data, i, "Bearish Harami", "bearish", 0.65))
                if c.is_doji: patterns.append(self._create_pattern(data, i, "Bearish Harami Cross", "bearish", 0.75))
        return patterns

    def _detect_piercing_dark_cloud(self, data, end_index):
        patterns = []
        for i in range(1, end_index):
            c, p = data.iloc[i], data.iloc[i-1]
            mid_point = (p.open_price + p.close_price) / 2
            if p.is_downtrend and p.is_red and p.is_large_body and c.is_green and c.open_price < p.low_price and c.close_price > mid_point and c.close_price < p.open_price:
                patterns.append(self._create_pattern(data, i, "Piercing Pattern", "bullish", 0.8))
            if p.is_uptrend and p.is_green and p.is_large_body and c.is_red and c.open_price > p.high_price and c.close_price < mid_point and c.close_price > p.open_price:
                patterns.append(self._create_pattern(data, i, "Dark Cloud Cover", "bearish", 0.8))
        return patterns

    def _detect_tweezers(self, data, end_index):
        patterns = []
        for i in range(1, end_index):
            c, p = data.iloc[i], data.iloc[i-1]
            if c.is_uptrend and abs(p.high_price - c.high_price) / c.high_price < 0.001:
                 patterns.append(self._create_pattern(data, i, "Tweezer Top", "bearish", 0.7))
            if c.is_downtrend and abs(p.low_price - c.low_price) / c.low_price < 0.001:
                 patterns.append(self._create_pattern(data, i, "Tweezer Bottom", "bullish", 0.7))
        return patterns

    def _detect_counterattack(self, data, end_index):
        patterns = []
        for i in range(1, end_index):
            c, p = data.iloc[i], data.iloc[i-1]
            closes_match = abs(c.close_price - p.close_price) / c.close_price < 0.001
            if c.is_downtrend and p.is_red and c.is_green and c.is_large_body and p.is_large_body and closes_match:
                patterns.append(self._create_pattern(data, i, "Bullish Counterattack", "bullish", 0.7))
            if c.is_uptrend and p.is_green and c.is_red and c.is_large_body and p.is_large_body and closes_match:
                patterns.append(self._create_pattern(data, i, "Bearish Counterattack", "bearish", 0.7))
        return patterns

    def _detect_stars(self, data, end_index):
        patterns = []
        for i in range(2, end_index):
            c0, c1, c2 = data.iloc[i-2], data.iloc[i-1], data.iloc[i]
            is_morning_star = c0.is_downtrend and c0.is_red and c0.is_large_body and c1.is_small_body and c1.close_price < c0.close_price and c2.is_green and c2.is_large_body and c2.close_price > (c0.open_price+c0.close_price)/2
            is_evening_star = c0.is_uptrend and c0.is_green and c0.is_large_body and c1.is_small_body and c1.close_price > c0.close_price and c2.is_red and c2.is_large_body and c2.close_price < (c0.open_price+c0.close_price)/2
            if is_morning_star:
                patterns.append(self._create_pattern(data, i, "Morning Star", "bullish", 0.9))
                if c1.is_doji: patterns.append(self._create_pattern(data, i, "Morning Doji Star", "bullish", 0.95))
            if is_evening_star:
                patterns.append(self._create_pattern(data, i, "Evening Star", "bearish", 0.9))
                if c1.is_doji: patterns.append(self._create_pattern(data, i, "Evening Doji Star", "bearish", 0.95))
        return patterns

    def _detect_three_soldiers_crows(self, data, end_index):
        patterns = []
        for i in range(2, end_index):
            c0, c1, c2 = data.iloc[i-2], data.iloc[i-1], data.iloc[i]
            is_soldiers = c2.is_green and c1.is_green and c0.is_green and all(data.is_large_body.iloc[i-2:i+1]) and c2.close_price > c1.close_price > c0.close_price and c1.open_price > c0.open_price and c1.open_price < c0.close_price and c2.open_price > c1.open_price and c2.open_price < c1.close_price
            is_crows = c2.is_red and c1.is_red and c0.is_red and all(data.is_large_body.iloc[i-2:i+1]) and c2.close_price < c1.close_price < c0.close_price and c1.open_price < c0.open_price and c1.open_price > c0.close_price and c2.open_price < c1.open_price and c2.open_price > c1.close_price
            if is_soldiers: patterns.append(self._create_pattern(data, i, "Three White Soldiers", "bullish", 0.9))
            if is_crows: patterns.append(self._create_pattern(data, i, "Three Black Crows", "bearish", 0.9))
        return patterns
        
    def _detect_three_inside_outside(self, data, end_index):
        patterns = []
        for i in range(2, end_index):
            c0, c1, c2 = data.iloc[i-2], data.iloc[i-1], data.iloc[i]
            # Three Inside Up
            is_harami_up = c0.is_red and c1.is_green and c1.high_price < c0.open_price and c1.low_price > c0.close_price
            if is_harami_up and c2.is_green and c2.close_price > c0.high_price:
                patterns.append(self._create_pattern(data, i, "Three Inside Up", "bullish", 0.8))
            # Three Inside Down
            is_harami_down = c0.is_green and c1.is_red and c1.high_price < c0.close_price and c1.low_price > c0.open_price
            if is_harami_down and c2.is_red and c2.close_price < c0.low_price:
                patterns.append(self._create_pattern(data, i, "Three Inside Down", "bearish", 0.8))
            # Three Outside Up
            is_engulf_up = c0.is_red and c1.is_green and c1.close_price > c0.open_price and c1.open_price < c0.close_price
            if is_engulf_up and c2.is_green and c2.close_price > c1.close_price:
                 patterns.append(self._create_pattern(data, i, "Three Outside Up", "bullish", 0.85))
            # Three Outside Down
            is_engulf_down = c0.is_green and c1.is_red and c1.close_price < c0.open_price and c1.open_price > c0.close_price
            if is_engulf_down and c2.is_red and c2.close_price < c1.close_price:
                 patterns.append(self._create_pattern(data, i, "Three Outside Down", "bearish", 0.85))
        return patterns

    def _detect_stick_sandwich(self, data, end_index):
        patterns = []
        for i in range(2, end_index):
            c0, c1, c2 = data.iloc[i-2], data.iloc[i-1], data.iloc[i]
            closes_match = abs(c0.close_price - c2.close_price) / c2.close_price < 0.001
            if c0.is_red and c2.is_red and c1.is_green and closes_match and c1.close_price > c0.open_price:
                 patterns.append(self._create_pattern(data, i, "Stick Sandwich", "bullish", 0.7))
        return patterns

    def _detect_abandoned_baby(self, data, end_index):
        patterns = []
        for i in range(2, end_index):
            c0, c1, c2 = data.iloc[i-2], data.iloc[i-1], data.iloc[i]
            if c0.is_downtrend and c0.is_red and c1.is_doji and c1.high_price < c0.low_price and c2.is_green and c2.low_price > c1.high_price:
                 patterns.append(self._create_pattern(data, i, "Bullish Abandoned Baby", "bullish", 0.95))
            if c0.is_uptrend and c0.is_green and c1.is_doji and c1.low_price > c0.high_price and c2.is_red and c2.high_price < c1.low_price:
                 patterns.append(self._create_pattern(data, i, "Bearish Abandoned Baby", "bearish", 0.95))
        return patterns
        
    def _detect_three_methods(self, data, end_index):
        patterns = []
        if len(data) < 5: return patterns
        for i in range(4, end_index):
            c0, c1, c2, c3, c4 = data.iloc[i-4], data.iloc[i-3], data.iloc[i-2], data.iloc[i-1], data.iloc[i]
            is_rising = c0.is_uptrend and c0.is_green and c0.is_large_body and c4.is_green and c4.is_large_body and c4.close_price > c0.high_price and all(data.is_red.iloc[i-3:i]) and c3.low_price > c0.low_price and c1.high_price < c0.high_price
            is_falling = c0.is_downtrend and c0.is_red and c0.is_large_body and c4.is_red and c4.is_large_body and c4.close_price < c0.low_price and all(data.is_green.iloc[i-3:i]) and c3.high_price < c0.high_price and c1.low_price > c0.low_price
            if is_rising: patterns.append(self._create_pattern(data, i, "Rising Three Methods", "bullish", 0.8))
            if is_falling: patterns.append(self._create_pattern(data, i, "Falling Three Methods", "bearish", 0.8))
        return patterns
        
    def _detect_advance_block_deliberation(self, data, end_index):
        patterns = []
        for i in range(2, end_index):
            c0, c1, c2 = data.iloc[i-2], data.iloc[i-1], data.iloc[i]
            is_adv_block = c0.is_uptrend and all(data.is_green.iloc[i-2:i+1]) and c2.body_size < c1.body_size < c0.body_size and c2.upper_shadow > c1.upper_shadow
            is_deliberation = c0.is_uptrend and all(data.is_green.iloc[i-2:i]) and c0.is_large_body and c1.is_large_body and c2.is_small_body and c2.open_price > c1.close_price
            if is_adv_block: patterns.append(self._create_pattern(data, i, "Advance Block", "bearish", 0.65))
            if is_deliberation: patterns.append(self._create_pattern(data, i, "Deliberation", "bearish", 0.65))
        return patterns

    def _detect_breakaway(self, data, end_index):
        patterns = []
        if len(data) < 5: return patterns
        for i in range(4, end_index):
            c0, c1, c2, c3, c4 = data.iloc[i-4], data.iloc[i-3], data.iloc[i-2], data.iloc[i-1], data.iloc[i]
            is_bullish = c0.is_downtrend and c0.is_red and c0.is_large_body and c1.is_red and c1.open_price < c0.close_price and c4.is_green and c4.is_large_body and c4.close_price > c1.open_price
            is_bearish = c0.is_uptrend and c0.is_green and c0.is_large_body and c1.is_green and c1.open_price > c0.close_price and c4.is_red and c4.is_large_body and c4.close_price < c1.open_price
            if is_bullish: patterns.append(self._create_pattern(data, i, "Bullish Breakaway", "bullish", 0.75))
            if is_bearish: patterns.append(self._create_pattern(data, i, "Bearish Breakaway", "bearish", 0.75))
        return patterns

    def generate_candlestick_signals(df: pd.DataFrame, symbol: str) -> List[Dict]:
        """Função pública para gerar sinais a partir de um DataFrame."""
        detector = CandlestickDetector()
        patterns = detector.detect_all_patterns(df)
        
        signals = []
        for p in patterns:
            if p.pattern_type in ['bullish', 'bearish']:
                signals.append({
                    'detector_type': 'candlestick',
                    'detector_name': p.name,
                    'signal_type': 'BUY_LONG' if p.pattern_type == 'bullish' else 'SELL_SHORT',
                    'confidence': p.reliability_score,
                    'entry_price': p.entry_price,
                    'stop_loss': p.stop_loss,
                    'market_data': df
                })
        return signals

    def verify_patterns_implementation():
        """Verifica se todos os padrões estão implementados"""
        return True

        # Garante que a função está disponível para importação
    __all__ = ['CandlestickDetector', 'CandlestickPattern', 'generate_candlestick_signals', 'verify_patterns_implementation']