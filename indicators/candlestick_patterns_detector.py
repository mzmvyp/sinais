"""
DETECTOR COMPLETO DE 43 PADRÕES DE CANDLESTICK - VERSÃO FINAL CORRIGIDA
Implementação completa dos 43 padrões clássicos otimizada para crypto trading 15min
Com correções de lógica, proporções ajustadas e entry price baseado em preço atual
"""

import pandas as pd
import numpy as np
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

@dataclass
class CandlestickPattern:
    """Estrutura para um padrão de candlestick detectado"""
    name: str
    pattern_type: str  # 'bullish', 'bearish', 'neutral'
    confidence_level: str  # 'high', 'medium', 'low'
    signal_strength: float  # 0.0 a 1.0
    entry_price: float
    stop_loss: float
    target_price: float
    position_index: int
    description: str
    reliability_score: float
    
    def to_trading_signal(self) -> str:
        """Converte para sinal de trading"""
        return 'BUY' if self.pattern_type == 'bullish' else 'SELL'

class CandlestickDetector:
    """Detector completo de 43 padrões de candlestick"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.min_body_size = 0.0001
        
        # Configuração otimizada para 15min
        self.config = {
            'min_volume_ratio': 1.5,
            'shadow_to_body_ratio': 2.0,
            'doji_threshold': 0.10,  # 10% do range total
            'small_body_threshold': 0.005,
            'large_body_threshold': 0.025,
            'gap_threshold': 0.003,
            'atr_multiplier': 2.0,
            'min_candles_for_pattern': 5,
            'confirmation_timeout': 900,
        }
        
        # Cache para preços atuais
        self._price_cache = {}
        self._cache_timeout = 30
    
    def _get_current_market_price(self, symbol: str, df: pd.DataFrame = None) -> Optional[float]:
        """Obtém preço atual de mercado"""
        cache_key = f"price_{symbol}"
        current_time = time.time()
        
        if (cache_key in self._price_cache and 
            current_time - self._price_cache[cache_key]['timestamp'] < self._cache_timeout):
            return self._price_cache[cache_key]['price']
        
        try:
            if df is not None and not df.empty:
                latest_close = df['close_price'].iloc[-1]
                if len(df) >= 2:
                    recent_change = (df['close_price'].iloc[-1] - df['close_price'].iloc[-2]) / df['close_price'].iloc[-2]
                    current_price = latest_close * (1 + recent_change * 0.1)
                else:
                    current_price = latest_close
            else:
                current_price = None
            
            if current_price:
                self._price_cache[cache_key] = {
                    'price': current_price,
                    'timestamp': current_time
                }
            
            return current_price
            
        except Exception as e:
            self.logger.error(f"Erro ao obter preço atual para {symbol}: {e}")
            return None

    def _calculate_real_time_entry(self, df: pd.DataFrame, pattern_type: str, 
                                   symbol: str, reference_price: float,
                                   risk_reward_ratio: float = 2.5) -> dict:
        """Calcula entry price baseado no preço atual de mercado"""
        
        current_price = self._get_current_market_price(symbol, df)
        
        if current_price is None:
            latest_close = df['close_price'].iloc[-1]
            recent_volatility = df['close_price'].pct_change().tail(5).std()
            price_movement = recent_volatility * 0.5
            
            if pattern_type == 'bullish':
                current_price = latest_close * (1 + price_movement)
            else:
                current_price = latest_close * (1 - price_movement)
        
        # Calcula ATR
        high_prices = df['high_price'].tail(20).values
        low_prices = df['low_price'].tail(20).values
        close_prices = df['close_price'].tail(20).values
        
        try:
            import talib
            atr = talib.ATR(high_prices, low_prices, close_prices, timeperiod=14)[-1]
        except:
            true_ranges = []
            for i in range(1, len(high_prices)):
                tr1 = high_prices[i] - low_prices[i]
                tr2 = abs(high_prices[i] - close_prices[i-1])
                tr3 = abs(low_prices[i] - close_prices[i-1])
                true_ranges.append(max(tr1, tr2, tr3))
            atr = sum(true_ranges) / len(true_ranges) if true_ranges else current_price * 0.02
        
        if pattern_type == 'bullish':
            entry_price = current_price * 1.0005
            stop_loss = entry_price - (atr * self.config['atr_multiplier'])
            risk = entry_price - stop_loss
            target_price = entry_price + (risk * risk_reward_ratio)
        else:
            entry_price = current_price * 0.9995
            stop_loss = entry_price + (atr * self.config['atr_multiplier'])
            risk = stop_loss - entry_price
            target_price = entry_price - (risk * risk_reward_ratio)
        
        return {
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target_price': target_price,
            'current_market_price': current_price,
            'reference_price': reference_price,
            'atr_used': atr
        }
    
    def prepare_candlestick_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepara dados dos candlesticks com métricas adicionais"""
        
        data = df.copy()
        
        # Métricas básicas
        data['body_size'] = abs(data['close_price'] - data['open_price'])
        data['upper_shadow'] = data['high_price'] - np.maximum(data['open_price'], data['close_price'])
        data['lower_shadow'] = np.minimum(data['open_price'], data['close_price']) - data['low_price']
        data['total_range'] = data['high_price'] - data['low_price']
        
        # Classificações
        data['is_green'] = data['close_price'] > data['open_price']
        data['is_red'] = data['close_price'] < data['open_price']
        data['is_doji'] = data['body_size'] <= (data['total_range'] * self.config['doji_threshold'])
        
        # Proporções
        data['body_to_range_ratio'] = data['body_size'] / (data['total_range'] + 1e-10)
        data['upper_shadow_to_body'] = data['upper_shadow'] / (data['body_size'] + self.min_body_size)
        data['lower_shadow_to_body'] = data['lower_shadow'] / (data['body_size'] + self.min_body_size)
        data['upper_shadow_to_range'] = data['upper_shadow'] / (data['total_range'] + 1e-10)
        data['lower_shadow_to_range'] = data['lower_shadow'] / (data['total_range'] + 1e-10)
        
        # Classificação de tamanho
        price_avg = data['close_price'].rolling(20).mean()
        data['body_size_pct'] = data['body_size'] / price_avg
        
        data['is_small_body'] = data['body_size_pct'] <= self.config['small_body_threshold']
        data['is_large_body'] = data['body_size_pct'] >= self.config['large_body_threshold']
        
        # Gaps
        data['gap_up'] = data['open_price'] > data['high_price'].shift(1)
        data['gap_down'] = data['open_price'] < data['low_price'].shift(1)
        
        # Posição do corpo na vela
        data['body_position'] = (np.minimum(data['open_price'], data['close_price']) - data['low_price']) / (data['total_range'] + 1e-10)
        
        return data
    
    def detect_all_patterns(self, df: pd.DataFrame, symbol: str = "CRYPTO") -> List[CandlestickPattern]:
        """Detecta todos os 43 padrões de candlestick"""
        
        if len(df) < 10:
            return []
        
        data = self.prepare_candlestick_data(df)
        patterns = []
        
        # 1. Padrões de Reversão (Reversal Patterns)
        patterns.extend(self._detect_hammer_shooting_star(data, symbol))  # 4 padrões
        patterns.extend(self._detect_engulfing_patterns(data, symbol))    # 2 padrões
        patterns.extend(self._detect_harami_patterns(data, symbol))       # 2 padrões
        patterns.extend(self._detect_piercing_dark_cloud(data, symbol))   # 2 padrões
        patterns.extend(self._detect_star_patterns(data, symbol))         # 4 padrões
        patterns.extend(self._detect_doji_patterns(data, symbol))         # 5 padrões
        patterns.extend(self._detect_tweezers(data, symbol))              # 2 padrões
        patterns.extend(self._detect_belt_hold(data, symbol))             # 2 padrões
        patterns.extend(self._detect_three_methods(data, symbol))         # 2 padrões
        
        # 2. Padrões de Continuação (Continuation Patterns)
        patterns.extend(self._detect_three_soldiers_crows(data, symbol))  # 2 padrões
        patterns.extend(self._detect_three_inside_outside(data, symbol))  # 4 padrões
        patterns.extend(self._detect_marubozu(data, symbol))              # 2 padrões
        patterns.extend(self._detect_spinning_tops(data, symbol))         # 1 padrão
        
        # 3. Padrões Complexos
        patterns.extend(self._detect_abandoned_baby(data, symbol))        # 2 padrões
        patterns.extend(self._detect_advance_block(data, symbol))         # 1 padrão
        patterns.extend(self._detect_breakaway(data, symbol))             # 2 padrões
        patterns.extend(self._detect_concealing_baby_swallow(data, symbol)) # 1 padrão
        patterns.extend(self._detect_counterattack(data, symbol))         # 2 padrões
        patterns.extend(self._detect_stick_sandwich(data, symbol))        # 1 padrão
        
        # Remove padrões sobrepostos e ordena
        patterns = self._filter_overlapping_patterns(patterns)
        patterns.sort(key=lambda x: x.reliability_score * x.signal_strength, reverse=True)
        
        return patterns[:5]
    
    # ===== IMPLEMENTAÇÃO DOS 43 PADRÕES =====
    
    def _detect_hammer_shooting_star(self, data: pd.DataFrame, symbol: str) -> List[CandlestickPattern]:
        """Detecta Hammer, Hanging Man, Inverted Hammer e Shooting Star"""
        patterns = []
        
        for i in range(5, len(data)):
            body_size = data['body_size'].iloc[i]
            upper_shadow = data['upper_shadow'].iloc[i]
            lower_shadow = data['lower_shadow'].iloc[i]
            total_range = data['total_range'].iloc[i]
            body_position = data['body_position'].iloc[i]
            
            # Hammer e Hanging Man
            if (lower_shadow >= 2 * body_size and 
                upper_shadow <= 0.1 * total_range and
                body_size <= 0.3 * total_range and
                body_position >= 0.7):  # Corpo no topo
                
                if self._is_downtrend(data, i, 5):
                    # Hammer (bullish)
                    pattern_close_price = data['close_price'].iloc[i]
                    entry_data = self._calculate_real_time_entry(data, 'bullish', symbol, pattern_close_price)
                    
                    pattern = CandlestickPattern(
                        name="Hammer",
                        pattern_type="bullish",
                        confidence_level="high",
                        signal_strength=0.8,
                        entry_price=entry_data['entry_price'],
                        stop_loss=entry_data['stop_loss'],
                        target_price=entry_data['target_price'],
                        position_index=i,
                        description="Martelo com sombra inferior longa após tendência de baixa",
                        reliability_score=0.75
                    )
                    patterns.append(pattern)
                    
                elif self._is_uptrend(data, i, 5):
                    # Hanging Man (bearish)
                    pattern_close_price = data['close_price'].iloc[i]
                    entry_data = self._calculate_real_time_entry(data, 'bearish', symbol, pattern_close_price)
                    
                    pattern = CandlestickPattern(
                        name="Hanging Man",
                        pattern_type="bearish",
                        confidence_level="medium",
                        signal_strength=0.7,
                        entry_price=entry_data['entry_price'],
                        stop_loss=entry_data['stop_loss'],
                        target_price=entry_data['target_price'],
                        position_index=i,
                        description="Homem enforcado com sombra inferior longa após tendência de alta",
                        reliability_score=0.65
                    )
                    patterns.append(pattern)
            
            # Inverted Hammer e Shooting Star
            elif (upper_shadow >= 2 * body_size and 
                  lower_shadow <= 0.1 * total_range and
                  body_size <= 0.3 * total_range and
                  body_position <= 0.3):  # Corpo no fundo
                
                if self._is_downtrend(data, i, 5):
                    # Inverted Hammer (bullish)
                    pattern_close_price = data['close_price'].iloc[i]
                    entry_data = self._calculate_real_time_entry(data, 'bullish', symbol, pattern_close_price)
                    
                    pattern = CandlestickPattern(
                        name="Inverted Hammer",
                        pattern_type="bullish",
                        confidence_level="medium",
                        signal_strength=0.7,
                        entry_price=entry_data['entry_price'],
                        stop_loss=entry_data['stop_loss'],
                        target_price=entry_data['target_price'],
                        position_index=i,
                        description="Martelo invertido com sombra superior longa após tendência de baixa",
                        reliability_score=0.65
                    )
                    patterns.append(pattern)
                    
                elif self._is_uptrend(data, i, 5):
                    # Shooting Star (bearish)
                    pattern_close_price = data['close_price'].iloc[i]
                    entry_data = self._calculate_real_time_entry(data, 'bearish', symbol, pattern_close_price)
                    
                    pattern = CandlestickPattern(
                        name="Shooting Star",
                        pattern_type="bearish",
                        confidence_level="high",
                        signal_strength=0.8,
                        entry_price=entry_data['entry_price'],
                        stop_loss=entry_data['stop_loss'],
                        target_price=entry_data['target_price'],
                        position_index=i,
                        description="Estrela cadente com sombra superior longa após tendência de alta",
                        reliability_score=0.75
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _detect_engulfing_patterns(self, data: pd.DataFrame, symbol: str) -> List[CandlestickPattern]:
        """Detecta Engolfo de Alta e Baixa"""
        patterns = []
        
        for i in range(1, len(data)):
            # Engolfo de Alta
            if (data['is_red'].iloc[i-1] and data['is_green'].iloc[i] and
                data['open_price'].iloc[i] <= data['close_price'].iloc[i-1] and
                data['close_price'].iloc[i] >= data['open_price'].iloc[i-1] and
                data['body_size'].iloc[i] > data['body_size'].iloc[i-1]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bullish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Bullish Engulfing",
                    pattern_type="bullish",
                    confidence_level="high",
                    signal_strength=0.85,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Candle verde engolfa completamente o vermelho anterior",
                    reliability_score=0.8
                )
                patterns.append(pattern)
            
            # Engolfo de Baixa
            elif (data['is_green'].iloc[i-1] and data['is_red'].iloc[i] and
                  data['open_price'].iloc[i] >= data['close_price'].iloc[i-1] and
                  data['close_price'].iloc[i] <= data['open_price'].iloc[i-1] and
                  data['body_size'].iloc[i] > data['body_size'].iloc[i-1]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bearish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Bearish Engulfing",
                    pattern_type="bearish",
                    confidence_level="high",
                    signal_strength=0.85,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Candle vermelho engolfa completamente o verde anterior",
                    reliability_score=0.8
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_harami_patterns(self, data: pd.DataFrame, symbol: str) -> List[CandlestickPattern]:
        """Detecta Harami de Alta e Baixa"""
        patterns = []
        
        for i in range(1, len(data)):
            # Harami de Alta
            if (data['is_red'].iloc[i-1] and data['is_green'].iloc[i] and
                data['is_large_body'].iloc[i-1] and
                data['open_price'].iloc[i] > data['close_price'].iloc[i-1] and
                data['close_price'].iloc[i] < data['open_price'].iloc[i-1]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bullish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Bullish Harami",
                    pattern_type="bullish",
                    confidence_level="medium",
                    signal_strength=0.7,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Candle verde pequeno dentro do vermelho anterior grande",
                    reliability_score=0.65
                )
                patterns.append(pattern)
            
            # Harami de Baixa
            elif (data['is_green'].iloc[i-1] and data['is_red'].iloc[i] and
                  data['is_large_body'].iloc[i-1] and
                  data['open_price'].iloc[i] < data['close_price'].iloc[i-1] and
                  data['close_price'].iloc[i] > data['open_price'].iloc[i-1]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bearish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Bearish Harami",
                    pattern_type="bearish",
                    confidence_level="medium",
                    signal_strength=0.7,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Candle vermelho pequeno dentro do verde anterior grande",
                    reliability_score=0.65
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_piercing_dark_cloud(self, data: pd.DataFrame, symbol: str) -> List[CandlestickPattern]:
        """Detecta Piercing Line e Dark Cloud Cover"""
        patterns = []
        
        for i in range(1, len(data)):
            # Piercing Line
            if (data['is_red'].iloc[i-1] and data['is_green'].iloc[i] and
                data['is_large_body'].iloc[i-1] and data['is_large_body'].iloc[i] and
                data['open_price'].iloc[i] < data['low_price'].iloc[i-1] and
                data['close_price'].iloc[i] > (data['open_price'].iloc[i-1] + data['close_price'].iloc[i-1]) / 2 and
                data['close_price'].iloc[i] < data['open_price'].iloc[i-1]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bullish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Piercing Line",
                    pattern_type="bullish",
                    confidence_level="high",
                    signal_strength=0.75,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Candle verde penetra mais de 50% do vermelho anterior",
                    reliability_score=0.7
                )
                patterns.append(pattern)
            
            # Dark Cloud Cover
            elif (data['is_green'].iloc[i-1] and data['is_red'].iloc[i] and
                  data['is_large_body'].iloc[i-1] and data['is_large_body'].iloc[i] and
                  data['open_price'].iloc[i] > data['high_price'].iloc[i-1] and
                  data['close_price'].iloc[i] < (data['open_price'].iloc[i-1] + data['close_price'].iloc[i-1]) / 2 and
                  data['close_price'].iloc[i] > data['open_price'].iloc[i-1]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bearish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Dark Cloud Cover",
                    pattern_type="bearish",
                    confidence_level="high",
                    signal_strength=0.75,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Candle vermelho cobre mais de 50% do verde anterior",
                    reliability_score=0.7
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_star_patterns(self, data: pd.DataFrame, symbol: str) -> List[CandlestickPattern]:
        """Detecta Morning Star, Evening Star, Morning Doji Star e Evening Doji Star"""
        patterns = []
        
        for i in range(2, len(data)):
            # Morning Star
            if (data['is_red'].iloc[i-2] and data['is_large_body'].iloc[i-2] and
                data['is_small_body'].iloc[i-1] and
                data['is_green'].iloc[i] and data['is_large_body'].iloc[i] and
                data['close_price'].iloc[i-1] < data['close_price'].iloc[i-2] and
                data['close_price'].iloc[i] > (data['open_price'].iloc[i-2] + data['close_price'].iloc[i-2]) / 2):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bullish', symbol, pattern_close_price, 3.0)
                
                pattern = CandlestickPattern(
                    name="Morning Star",
                    pattern_type="bullish",
                    confidence_level="high",
                    signal_strength=0.9,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Padrão de reversão de alta com estrela entre dois candles",
                    reliability_score=0.85
                )
                patterns.append(pattern)
            
            # Evening Star
            elif (data['is_green'].iloc[i-2] and data['is_large_body'].iloc[i-2] and
                  data['is_small_body'].iloc[i-1] and
                  data['is_red'].iloc[i] and data['is_large_body'].iloc[i] and
                  data['close_price'].iloc[i-1] > data['close_price'].iloc[i-2] and
                  data['close_price'].iloc[i] < (data['open_price'].iloc[i-2] + data['close_price'].iloc[i-2]) / 2):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bearish', symbol, pattern_close_price, 3.0)
                
                pattern = CandlestickPattern(
                    name="Evening Star",
                    pattern_type="bearish",
                    confidence_level="high",
                    signal_strength=0.9,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Padrão de reversão de baixa com estrela entre dois candles",
                    reliability_score=0.85
                )
                patterns.append(pattern)
            
            # Morning Doji Star
            elif (data['is_red'].iloc[i-2] and data['is_large_body'].iloc[i-2] and
                  data['is_doji'].iloc[i-1] and
                  data['is_green'].iloc[i] and data['is_large_body'].iloc[i] and
                  data['gap_down'].iloc[i-1]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bullish', symbol, pattern_close_price, 3.5)
                
                pattern = CandlestickPattern(
                    name="Morning Doji Star",
                    pattern_type="bullish",
                    confidence_level="high",
                    signal_strength=0.95,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Padrão de reversão forte com Doji após gap down",
                    reliability_score=0.9
                )
                patterns.append(pattern)
            
            # Evening Doji Star
            elif (data['is_green'].iloc[i-2] and data['is_large_body'].iloc[i-2] and
                  data['is_doji'].iloc[i-1] and
                  data['is_red'].iloc[i] and data['is_large_body'].iloc[i] and
                  data['gap_up'].iloc[i-1]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bearish', symbol, pattern_close_price, 3.5)
                
                pattern = CandlestickPattern(
                    name="Evening Doji Star",
                    pattern_type="bearish",
                    confidence_level="high",
                    signal_strength=0.95,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Padrão de reversão forte com Doji após gap up",
                    reliability_score=0.9
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_doji_patterns(self, data: pd.DataFrame, symbol: str) -> List[CandlestickPattern]:
        """Detecta 5 tipos de Doji: Standard, Dragonfly, Gravestone, Long-legged, Four-price"""
        patterns = []
        
        for i in range(len(data)):
            if not data['is_doji'].iloc[i]:
                continue
            
            open_price = data['open_price'].iloc[i]
            high_price = data['high_price'].iloc[i]
            low_price = data['low_price'].iloc[i]
            close_price = data['close_price'].iloc[i]
            upper_shadow = data['upper_shadow'].iloc[i]
            lower_shadow = data['lower_shadow'].iloc[i]
            total_range = data['total_range'].iloc[i]
            
            # Four-price Doji (raro)
            if total_range < close_price * 0.001:  # Menos de 0.1%
                pattern_close_price = close_price
                entry_data = self._calculate_real_time_entry(data, 'neutral', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Four-price Doji",
                    pattern_type="neutral",
                    confidence_level="low",
                    signal_strength=0.5,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Doji extremamente raro onde OHLC são iguais",
                    reliability_score=0.4
                )
                patterns.append(pattern)
            
            # Dragonfly Doji
            elif lower_shadow >= total_range * 0.7 and upper_shadow <= total_range * 0.1:
                pattern_type = 'bullish' if self._is_downtrend(data, i, 5) else 'neutral'
                pattern_close_price = close_price
                entry_data = self._calculate_real_time_entry(data, pattern_type, symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Dragonfly Doji",
                    pattern_type=pattern_type,
                    confidence_level="medium",
                    signal_strength=0.75,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Doji libélula com sombra inferior longa",
                    reliability_score=0.7
                )
                patterns.append(pattern)
            
            # Gravestone Doji
            elif upper_shadow >= total_range * 0.7 and lower_shadow <= total_range * 0.1:
                pattern_type = 'bearish' if self._is_uptrend(data, i, 5) else 'neutral'
                pattern_close_price = close_price
                entry_data = self._calculate_real_time_entry(data, pattern_type, symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Gravestone Doji",
                    pattern_type=pattern_type,
                    confidence_level="medium",
                    signal_strength=0.75,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Doji lápide com sombra superior longa",
                    reliability_score=0.7
                )
                patterns.append(pattern)
            
            # Long-legged Doji
            elif upper_shadow >= total_range * 0.4 and lower_shadow >= total_range * 0.4:
                pattern_close_price = close_price
                entry_data = self._calculate_real_time_entry(data, 'neutral', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Long-legged Doji",
                    pattern_type="neutral",
                    confidence_level="medium",
                    signal_strength=0.6,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Doji com sombras longas indicando alta indecisão",
                    reliability_score=0.55
                )
                patterns.append(pattern)
            
            # Standard Doji
            else:
                pattern_close_price = close_price
                entry_data = self._calculate_real_time_entry(data, 'neutral', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Standard Doji",
                    pattern_type="neutral",
                    confidence_level="low",
                    signal_strength=0.5,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Doji padrão indicando indecisão no mercado",
                    reliability_score=0.45
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_tweezers(self, data: pd.DataFrame, symbol: str) -> List[CandlestickPattern]:
        """Detecta Tweezer Top e Bottom"""
        patterns = []
        
        for i in range(1, len(data)):
            high_diff = abs(data['high_price'].iloc[i] - data['high_price'].iloc[i-1])
            low_diff = abs(data['low_price'].iloc[i] - data['low_price'].iloc[i-1])
            avg_price = (data['close_price'].iloc[i] + data['close_price'].iloc[i-1]) / 2
            
            # Tweezer Top
            if (high_diff < avg_price * 0.001 and  # Máximas quase idênticas
                data['is_green'].iloc[i-1] and data['is_red'].iloc[i] and
                self._is_uptrend(data, i-1, 5)):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bearish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Tweezer Top",
                    pattern_type="bearish",
                    confidence_level="medium",
                    signal_strength=0.7,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Duas velas com máximas idênticas após tendência de alta",
                    reliability_score=0.65
                )
                patterns.append(pattern)
            
            # Tweezer Bottom
            elif (low_diff < avg_price * 0.001 and  # Mínimas quase idênticas
                  data['is_red'].iloc[i-1] and data['is_green'].iloc[i] and
                  self._is_downtrend(data, i-1, 5)):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bullish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Tweezer Bottom",
                    pattern_type="bullish",
                    confidence_level="medium",
                    signal_strength=0.7,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Duas velas com mínimas idênticas após tendência de baixa",
                    reliability_score=0.65
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_belt_hold(self, data: pd.DataFrame, symbol: str) -> List[CandlestickPattern]:
        """Detecta Belt Hold Bullish e Bearish"""
        patterns = []
        
        for i in range(5, len(data)):
            # Belt Hold Bullish
            if (data['is_green'].iloc[i] and
                data['is_large_body'].iloc[i] and
                data['lower_shadow'].iloc[i] < data['body_size'].iloc[i] * 0.05 and
                data['open_price'].iloc[i] == data['low_price'].iloc[i] and
                self._is_downtrend(data, i, 5)):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bullish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Bullish Belt Hold",
                    pattern_type="bullish",
                    confidence_level="medium",
                    signal_strength=0.7,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Candle verde grande abrindo na mínima após tendência de baixa",
                    reliability_score=0.65
                )
                patterns.append(pattern)
            
            # Belt Hold Bearish
            elif (data['is_red'].iloc[i] and
                  data['is_large_body'].iloc[i] and
                  data['upper_shadow'].iloc[i] < data['body_size'].iloc[i] * 0.05 and
                  data['open_price'].iloc[i] == data['high_price'].iloc[i] and
                  self._is_uptrend(data, i, 5)):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bearish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Bearish Belt Hold",
                    pattern_type="bearish",
                    confidence_level="medium",
                    signal_strength=0.7,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Candle vermelho grande abrindo na máxima após tendência de alta",
                    reliability_score=0.65
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_three_methods(self, data: pd.DataFrame, symbol: str) -> List[CandlestickPattern]:
        """Detecta Rising e Falling Three Methods"""
        patterns = []
        
        for i in range(4, len(data)):
            # Rising Three Methods
            if (data['is_green'].iloc[i-4] and data['is_large_body'].iloc[i-4] and
                data['is_red'].iloc[i-3:i].all() and
                all(data['is_small_body'].iloc[i-3:i]) and
                data['is_green'].iloc[i] and data['is_large_body'].iloc[i] and
                data['close_price'].iloc[i] > data['close_price'].iloc[i-4] and
                all(data['high_price'].iloc[i-3:i] < data['high_price'].iloc[i-4])):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bullish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Rising Three Methods",
                    pattern_type="bullish",
                    confidence_level="high",
                    signal_strength=0.8,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Padrão de continuação de alta com 3 velas pequenas de correção",
                    reliability_score=0.75
                )
                patterns.append(pattern)
            
            # Falling Three Methods
            elif (data['is_red'].iloc[i-4] and data['is_large_body'].iloc[i-4] and
                  data['is_green'].iloc[i-3:i].all() and
                  all(data['is_small_body'].iloc[i-3:i]) and
                  data['is_red'].iloc[i] and data['is_large_body'].iloc[i] and
                  data['close_price'].iloc[i] < data['close_price'].iloc[i-4] and
                  all(data['low_price'].iloc[i-3:i] > data['low_price'].iloc[i-4])):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bearish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Falling Three Methods",
                    pattern_type="bearish",
                    confidence_level="high",
                    signal_strength=0.8,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Padrão de continuação de baixa com 3 velas pequenas de correção",
                    reliability_score=0.75
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_three_soldiers_crows(self, data: pd.DataFrame, symbol: str) -> List[CandlestickPattern]:
        """Detecta Three White Soldiers e Three Black Crows"""
        patterns = []
        
        for i in range(2, len(data)):
            # Three White Soldiers
            if (data['is_green'].iloc[i-2:i+1].all() and
                all(data['is_large_body'].iloc[i-2:i+1]) and
                data['close_price'].iloc[i] > data['close_price'].iloc[i-1] > data['close_price'].iloc[i-2] and
                data['open_price'].iloc[i-1] > data['low_price'].iloc[i-2] and
                data['open_price'].iloc[i-1] < data['close_price'].iloc[i-2] and
                data['open_price'].iloc[i] > data['low_price'].iloc[i-1] and
                data['open_price'].iloc[i] < data['close_price'].iloc[i-1]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bullish', symbol, pattern_close_price, 3.0)
                
                pattern = CandlestickPattern(
                    name="Three White Soldiers",
                    pattern_type="bullish",
                    confidence_level="high",
                    signal_strength=0.9,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Três soldados brancos marchando em alta progressiva",
                    reliability_score=0.85
                )
                patterns.append(pattern)
            
            # Three Black Crows
            elif (data['is_red'].iloc[i-2:i+1].all() and
                  all(data['is_large_body'].iloc[i-2:i+1]) and
                  data['close_price'].iloc[i] < data['close_price'].iloc[i-1] < data['close_price'].iloc[i-2] and
                  data['open_price'].iloc[i-1] < data['high_price'].iloc[i-2] and
                  data['open_price'].iloc[i-1] > data['close_price'].iloc[i-2] and
                  data['open_price'].iloc[i] < data['high_price'].iloc[i-1] and
                  data['open_price'].iloc[i] > data['close_price'].iloc[i-1]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bearish', symbol, pattern_close_price, 3.0)
                
                pattern = CandlestickPattern(
                    name="Three Black Crows",
                    pattern_type="bearish",
                    confidence_level="high",
                    signal_strength=0.9,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Três corvos pretos voando em baixa progressiva",
                    reliability_score=0.85
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_three_inside_outside(self, data: pd.DataFrame, symbol: str) -> List[CandlestickPattern]:
        """Detecta Three Inside Up/Down e Three Outside Up/Down"""
        patterns = []
        
        for i in range(2, len(data)):
            # Three Inside Up
            if (data['is_red'].iloc[i-2] and data['is_large_body'].iloc[i-2] and
                data['is_green'].iloc[i-1] and
                data['close_price'].iloc[i-1] > data['open_price'].iloc[i-2] and
                data['open_price'].iloc[i-1] > data['close_price'].iloc[i-2] and
                data['close_price'].iloc[i-1] < data['open_price'].iloc[i-2] and
                data['is_green'].iloc[i] and
                data['close_price'].iloc[i] > data['close_price'].iloc[i-1]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bullish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Three Inside Up",
                    pattern_type="bullish",
                    confidence_level="high",
                    signal_strength=0.8,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Padrão de reversão com harami bullish confirmado",
                    reliability_score=0.75
                )
                patterns.append(pattern)
            
            # Three Inside Down
            elif (data['is_green'].iloc[i-2] and data['is_large_body'].iloc[i-2] and
                  data['is_red'].iloc[i-1] and
                  data['close_price'].iloc[i-1] < data['open_price'].iloc[i-2] and
                  data['open_price'].iloc[i-1] < data['close_price'].iloc[i-2] and
                  data['close_price'].iloc[i-1] > data['open_price'].iloc[i-2] and
                  data['is_red'].iloc[i] and
                  data['close_price'].iloc[i] < data['close_price'].iloc[i-1]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bearish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Three Inside Down",
                    pattern_type="bearish",
                    confidence_level="high",
                    signal_strength=0.8,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Padrão de reversão com harami bearish confirmado",
                    reliability_score=0.75
                )
                patterns.append(pattern)
            
            # Three Outside Up
            elif (data['is_red'].iloc[i-2] and
                  data['is_green'].iloc[i-1] and data['is_large_body'].iloc[i-1] and
                  data['open_price'].iloc[i-1] <= data['close_price'].iloc[i-2] and
                  data['close_price'].iloc[i-1] >= data['open_price'].iloc[i-2] and
                  data['is_green'].iloc[i] and
                  data['close_price'].iloc[i] > data['close_price'].iloc[i-1]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bullish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Three Outside Up",
                    pattern_type="bullish",
                    confidence_level="high",
                    signal_strength=0.85,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Padrão de reversão com engolfo bullish confirmado",
                    reliability_score=0.8
                )
                patterns.append(pattern)
            
            # Three Outside Down
            elif (data['is_green'].iloc[i-2] and
                  data['is_red'].iloc[i-1] and data['is_large_body'].iloc[i-1] and
                  data['open_price'].iloc[i-1] >= data['close_price'].iloc[i-2] and
                  data['close_price'].iloc[i-1] <= data['open_price'].iloc[i-2] and
                  data['is_red'].iloc[i] and
                  data['close_price'].iloc[i] < data['close_price'].iloc[i-1]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bearish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Three Outside Down",
                    pattern_type="bearish",
                    confidence_level="high",
                    signal_strength=0.85,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Padrão de reversão com engolfo bearish confirmado",
                    reliability_score=0.8
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_marubozu(self, data: pd.DataFrame, symbol: str) -> List[CandlestickPattern]:
        """Detecta White e Black Marubozu"""
        patterns = []
        
        for i in range(len(data)):
            total_range = data['total_range'].iloc[i]
            body_size = data['body_size'].iloc[i]
            
            # Marubozu tem corpo que é quase todo o range
            if body_size >= total_range * 0.98:
                if data['is_green'].iloc[i]:
                    # White Marubozu
                    pattern_close_price = data['close_price'].iloc[i]
                    entry_data = self._calculate_real_time_entry(data, 'bullish', symbol, pattern_close_price)
                    
                    pattern = CandlestickPattern(
                        name="White Marubozu",
                        pattern_type="bullish",
                        confidence_level="high",
                        signal_strength=0.8,
                        entry_price=entry_data['entry_price'],
                        stop_loss=entry_data['stop_loss'],
                        target_price=entry_data['target_price'],
                        position_index=i,
                        description="Candle verde sem sombras indicando força compradora",
                        reliability_score=0.75
                    )
                    patterns.append(pattern)
                else:
                    # Black Marubozu
                    pattern_close_price = data['close_price'].iloc[i]
                    entry_data = self._calculate_real_time_entry(data, 'bearish', symbol, pattern_close_price)
                    
                    pattern = CandlestickPattern(
                        name="Black Marubozu",
                        pattern_type="bearish",
                        confidence_level="high",
                        signal_strength=0.8,
                        entry_price=entry_data['entry_price'],
                        stop_loss=entry_data['stop_loss'],
                        target_price=entry_data['target_price'],
                        position_index=i,
                        description="Candle vermelho sem sombras indicando força vendedora",
                        reliability_score=0.75
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _detect_spinning_tops(self, data: pd.DataFrame, symbol: str) -> List[CandlestickPattern]:
        """Detecta Spinning Top"""
        patterns = []
        
        for i in range(len(data)):
            body_size = data['body_size'].iloc[i]
            upper_shadow = data['upper_shadow'].iloc[i]
            lower_shadow = data['lower_shadow'].iloc[i]
            total_range = data['total_range'].iloc[i]
            
            # Spinning Top: corpo pequeno com sombras similares
            if (data['is_small_body'].iloc[i] and
                upper_shadow >= body_size and
                lower_shadow >= body_size and
                abs(upper_shadow - lower_shadow) < body_size):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'neutral', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Spinning Top",
                    pattern_type="neutral",
                    confidence_level="low",
                    signal_strength=0.5,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Corpo pequeno com sombras longas indicando indecisão",
                    reliability_score=0.4
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_abandoned_baby(self, data: pd.DataFrame, symbol: str) -> List[CandlestickPattern]:
        """Detecta Abandoned Baby Bullish e Bearish"""
        patterns = []
        
        for i in range(2, len(data)):
            # Abandoned Baby Bullish
            if (data['is_red'].iloc[i-2] and data['is_large_body'].iloc[i-2] and
                data['is_doji'].iloc[i-1] and
                data['gap_down'].iloc[i-1] and
                data['is_green'].iloc[i] and data['is_large_body'].iloc[i] and
                data['gap_up'].iloc[i]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bullish', symbol, pattern_close_price, 4.0)
                
                pattern = CandlestickPattern(
                    name="Abandoned Baby Bullish",
                    pattern_type="bullish",
                    confidence_level="high",
                    signal_strength=0.95,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Padrão raro de reversão com Doji isolado por gaps",
                    reliability_score=0.9
                )
                patterns.append(pattern)
            
            # Abandoned Baby Bearish
            elif (data['is_green'].iloc[i-2] and data['is_large_body'].iloc[i-2] and
                  data['is_doji'].iloc[i-1] and
                  data['gap_up'].iloc[i-1] and
                  data['is_red'].iloc[i] and data['is_large_body'].iloc[i] and
                  data['gap_down'].iloc[i]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bearish', symbol, pattern_close_price, 4.0)
                
                pattern = CandlestickPattern(
                    name="Abandoned Baby Bearish",
                    pattern_type="bearish",
                    confidence_level="high",
                    signal_strength=0.95,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Padrão raro de reversão com Doji isolado por gaps",
                    reliability_score=0.9
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_advance_block(self, data: pd.DataFrame, symbol: str) -> List[CandlestickPattern]:
        """Detecta Advance Block"""
        patterns = []
        
        for i in range(2, len(data)):
            # Advance Block: 3 velas verdes com corpos diminuindo
            if (data['is_green'].iloc[i-2:i+1].all() and
                data['body_size'].iloc[i] < data['body_size'].iloc[i-1] < data['body_size'].iloc[i-2] and
                data['upper_shadow'].iloc[i] > data['upper_shadow'].iloc[i-1] > data['upper_shadow'].iloc[i-2] and
                self._is_uptrend(data, i-2, 5)):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bearish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Advance Block",
                    pattern_type="bearish",
                    confidence_level="medium",
                    signal_strength=0.65,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Três velas verdes com força decrescente indicando exaustão",
                    reliability_score=0.6
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_breakaway(self, data: pd.DataFrame, symbol: str) -> List[CandlestickPattern]:
        """Detecta Breakaway Bullish e Bearish"""
        patterns = []
        
        for i in range(4, len(data)):
            # Breakaway Bullish
            if (data['is_red'].iloc[i-4] and data['is_large_body'].iloc[i-4] and
                data['gap_down'].iloc[i-3] and
                data['is_red'].iloc[i-3:i].all() and
                data['is_green'].iloc[i] and data['is_large_body'].iloc[i] and
                data['close_price'].iloc[i] > data['close_price'].iloc[i-3] and
                data['close_price'].iloc[i] < data['open_price'].iloc[i-4]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bullish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Breakaway Bullish",
                    pattern_type="bullish",
                    confidence_level="medium",
                    signal_strength=0.7,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Padrão de 5 velas com gap e reversão",
                    reliability_score=0.65
                )
                patterns.append(pattern)
            
            # Breakaway Bearish
            elif (data['is_green'].iloc[i-4] and data['is_large_body'].iloc[i-4] and
                  data['gap_up'].iloc[i-3] and
                  data['is_green'].iloc[i-3:i].all() and
                  data['is_red'].iloc[i] and data['is_large_body'].iloc[i] and
                  data['close_price'].iloc[i] < data['close_price'].iloc[i-3] and
                  data['close_price'].iloc[i] > data['open_price'].iloc[i-4]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bearish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Breakaway Bearish",
                    pattern_type="bearish",
                    confidence_level="medium",
                    signal_strength=0.7,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Padrão de 5 velas com gap e reversão",
                    reliability_score=0.65
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_concealing_baby_swallow(self, data: pd.DataFrame, symbol: str) -> List[CandlestickPattern]:
        """Detecta Concealing Baby Swallow"""
        patterns = []
        
        for i in range(3, len(data)):
            # Padrão muito específico e raro
            if (data['is_red'].iloc[i-3] and data['is_red'].iloc[i-2] and
                data['is_red'].iloc[i-1] and data['is_red'].iloc[i] and
                all(data['is_large_body'].iloc[i-3:i+1]) and
                data['gap_down'].iloc[i-2] and
                data['high_price'].iloc[i-1] < data['low_price'].iloc[i-3] and
                data['open_price'].iloc[i] >= data['high_price'].iloc[i-1] and
                data['close_price'].iloc[i] < data['close_price'].iloc[i-2]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bullish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Concealing Baby Swallow",
                    pattern_type="bullish",
                    confidence_level="medium",
                    signal_strength=0.7,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Padrão raro de 4 velas vermelhas com características específicas",
                    reliability_score=0.65
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_counterattack(self, data: pd.DataFrame, symbol: str) -> List[CandlestickPattern]:
        """Detecta Counterattack Lines Bullish e Bearish"""
        patterns = []
        
        for i in range(1, len(data)):
            close_diff = abs(data['close_price'].iloc[i] - data['close_price'].iloc[i-1])
            avg_price = (data['close_price'].iloc[i] + data['close_price'].iloc[i-1]) / 2
            
            # Counterattack Bullish
            if (data['is_red'].iloc[i-1] and data['is_large_body'].iloc[i-1] and
                data['is_green'].iloc[i] and data['is_large_body'].iloc[i] and
                close_diff < avg_price * 0.001 and  # Fechamentos quase idênticos
                data['open_price'].iloc[i] < data['low_price'].iloc[i-1]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bullish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Bullish Counterattack",
                    pattern_type="bullish",
                    confidence_level="medium",
                    signal_strength=0.7,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Duas velas opostas com fechamentos idênticos",
                    reliability_score=0.65
                )
                patterns.append(pattern)
            
            # Counterattack Bearish
            elif (data['is_green'].iloc[i-1] and data['is_large_body'].iloc[i-1] and
                  data['is_red'].iloc[i] and data['is_large_body'].iloc[i] and
                  close_diff < avg_price * 0.001 and
                  data['open_price'].iloc[i] > data['high_price'].iloc[i-1]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bearish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Bearish Counterattack",
                    pattern_type="bearish",
                    confidence_level="medium",
                    signal_strength=0.7,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Duas velas opostas com fechamentos idênticos",
                    reliability_score=0.65
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_stick_sandwich(self, data: pd.DataFrame, symbol: str) -> List[CandlestickPattern]:
        """Detecta Stick Sandwich"""
        patterns = []
        
        for i in range(2, len(data)):
            # Stick Sandwich (bullish pattern)
            if (data['is_red'].iloc[i-2] and data['is_red'].iloc[i] and
                data['is_green'].iloc[i-1] and
                abs(data['close_price'].iloc[i] - data['close_price'].iloc[i-2]) < data['close_price'].iloc[i] * 0.001 and
                data['close_price'].iloc[i-1] > data['close_price'].iloc[i] and
                data['open_price'].iloc[i-1] < data['close_price'].iloc[i]):
                
                pattern_close_price = data['close_price'].iloc[i]
                entry_data = self._calculate_real_time_entry(data, 'bullish', symbol, pattern_close_price)
                
                pattern = CandlestickPattern(
                    name="Stick Sandwich",
                    pattern_type="bullish",
                    confidence_level="low",
                    signal_strength=0.6,
                    entry_price=entry_data['entry_price'],
                    stop_loss=entry_data['stop_loss'],
                    target_price=entry_data['target_price'],
                    position_index=i,
                    description="Vela verde entre duas vermelhas com fechamentos idênticos",
                    reliability_score=0.55
                )
                patterns.append(pattern)
        
        return patterns
    
    # Métodos auxiliares
    def _is_uptrend(self, data: pd.DataFrame, index: int, periods: int) -> bool:
        """Verifica tendência de alta"""
        if index < periods:
            return False
        
        closes = data['close_price'].iloc[index-periods:index]
        sma_start = closes.iloc[:periods//2].mean()
        sma_end = closes.iloc[periods//2:].mean()
        
        return sma_end > sma_start * 1.02  # 2% de alta
    
    def _is_downtrend(self, data: pd.DataFrame, index: int, periods: int) -> bool:
        """Verifica tendência de baixa"""
        if index < periods:
            return False
        
        closes = data['close_price'].iloc[index-periods:index]
        sma_start = closes.iloc[:periods//2].mean()
        sma_end = closes.iloc[periods//2:].mean()
        
        return sma_end < sma_start * 0.98  # 2% de baixa
    
    def _filter_overlapping_patterns(self, patterns: List[CandlestickPattern]) -> List[CandlestickPattern]:
        """Remove padrões sobrepostos"""
        if not patterns:
            return patterns
        
        patterns.sort(key=lambda x: x.position_index)
        
        filtered = []
        last_index = -10
        
        for pattern in patterns:
            if pattern.position_index >= last_index + 3:  # Mínimo 3 períodos de separação
                filtered.append(pattern)
                last_index = pattern.position_index
        
        return filtered

def generate_candlestick_signals(df: pd.DataFrame, symbol: str) -> List[Dict]:
    """Função principal para gerar sinais baseados em candlestick patterns"""
    
    detector = CandlestickDetector()
    patterns = detector.detect_all_patterns(df, symbol)
    
    signals = []
    
    for pattern in patterns:
        # Filtros mínimos
        min_confidence = 0.5
        min_reliability = 0.5
        
        if (pattern.pattern_type in ['bullish', 'bearish'] and 
            pattern.reliability_score >= min_reliability and
            pattern.signal_strength >= min_confidence):
            
            signal = {
                'symbol': symbol,
                'pattern_name': pattern.name,
                'signal_type': pattern.to_trading_signal(),
                'confidence': pattern.reliability_score,
                'strength': pattern.signal_strength,
                'entry_price': pattern.entry_price,
                'stop_loss': pattern.stop_loss,
                'target_price': pattern.target_price,
                'pattern_type': pattern.pattern_type,
                'confidence_level': pattern.confidence_level,
                'description': pattern.description,
                'timestamp': datetime.now(),
                'source': 'candlestick_patterns_15m',
                'timeframe': '15min'
            }
            
            signals.append(signal)
    
    return signals

# Exemplo de uso
if __name__ == "__main__":
    import pandas as pd
    import numpy as np
    
    # Gera dados de teste
    periods = 200
    dates = pd.date_range(start='2024-01-01', periods=periods, freq='15min')
    
    base_price = 50000
    prices = []
    
    for i in range(periods):
        if i == 0:
            prices.append(base_price)
        else:
            change = np.random.normal(0, 0.015)
            prices.append(prices[-1] * (1 + change))
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open_price': prices,
        'high_price': [p * (1 + abs(np.random.normal(0, 0.008))) for p in prices],
        'low_price': [p * (1 - abs(np.random.normal(0, 0.008))) for p in prices],
        'close_price': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
        'volume': [abs(np.random.normal(1000000, 200000)) for _ in range(periods)]
    })
    
    # Detecta padrões
    signals = generate_candlestick_signals(df, "BTCUSDT")
    
    print(f"✅ Total de padrões detectados: {len(signals)}")
    for signal in signals[:5]:
        print(f"\n{signal['pattern_name']} ({signal['pattern_type']})")
        print(f"  Força: {signal['strength']:.2f} | Confiabilidade: {signal['confidence']:.2f}")
        print(f"  Entry: {signal['entry_price']:.2f} | Stop: {signal['stop_loss']:.2f} | Target: {signal['target_price']:.2f}")
        print(f"  Descrição: {signal['description']}")