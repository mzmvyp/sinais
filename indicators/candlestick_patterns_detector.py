"""
DETECTOR DE PADRÕES DE CANDLESTICK
Implementação dos 43 padrões do site Toro Investimentos
Otimizado para day trading em timeframe de 5min
"""

import pandas as pd
import numpy as np
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
    position_index: int  # Índice onde o padrão foi detectado
    description: str
    reliability_score: float  # Baseado na confiabilidade do site
    
    def to_trading_signal(self) -> str:
        """Converte para sinal de trading"""
        return 'BUY' if self.pattern_type == 'bullish' else 'SELL'

class CandlestickDetector:
    """Detector principal de padrões de candlestick"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.min_body_size = 0.0001  # Tamanho mínimo do corpo (para evitar divisão por zero)
        
        # Configurações para timeframe de 5min
        self.config = {
            'min_volume_ratio': 1.2,  # Volume 20% acima da média
            'shadow_to_body_ratio': 2.0,  # Sombra 2x maior que corpo
            'doji_threshold': 0.001,  # 0.1% para considerar Doji
            'small_body_threshold': 0.003,  # 0.3% para corpo pequeno
            'large_body_threshold': 0.015,  # 1.5% para corpo grande
            'gap_threshold': 0.002,  # 0.2% para considerar gap
        }
    
    def prepare_candlestick_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepara dados dos candlesticks com métricas adicionais"""
        
        data = df.copy()
        
        # Métricas básicas dos candles
        data['body_size'] = abs(data['close_price'] - data['open_price'])
        data['upper_shadow'] = data['high_price'] - np.maximum(data['open_price'], data['close_price'])
        data['lower_shadow'] = np.minimum(data['open_price'], data['close_price']) - data['low_price']
        data['total_range'] = data['high_price'] - data['low_price']
        
        # Classificações
        data['is_green'] = data['close_price'] > data['open_price']
        data['is_red'] = data['close_price'] < data['open_price']
        data['is_doji'] = data['body_size'] <= (data['total_range'] * self.config['doji_threshold'])
        
        # Tamanhos relativos
        data['body_to_range_ratio'] = data['body_size'] / (data['total_range'] + 1e-10)
        data['upper_shadow_to_body'] = data['upper_shadow'] / (data['body_size'] + self.min_body_size)
        data['lower_shadow_to_body'] = data['lower_shadow'] / (data['body_size'] + self.min_body_size)
        
        # Classificação de tamanho do corpo
        price_avg = data['close_price'].rolling(20).mean()
        data['body_size_pct'] = data['body_size'] / price_avg
        
        data['is_small_body'] = data['body_size_pct'] <= self.config['small_body_threshold']
        data['is_large_body'] = data['body_size_pct'] >= self.config['large_body_threshold']
        
        # Gaps
        data['gap_up'] = data['open_price'] > data['high_price'].shift(1)
        data['gap_down'] = data['open_price'] < data['low_price'].shift(1)
        
        return data
    
    def detect_all_patterns(self, df: pd.DataFrame) -> List[CandlestickPattern]:
        """Detecta todos os padrões de candlestick"""
        
        if len(df) < 10:
            return []
        
        data = self.prepare_candlestick_data(df)
        patterns = []
        
        # Padrões de alta confiabilidade
        patterns.extend(self._detect_three_soldiers_crows(data))
        patterns.extend(self._detect_engulfing_patterns(data))
        patterns.extend(self._detect_hammer_patterns(data))
        patterns.extend(self._detect_star_patterns(data))
        patterns.extend(self._detect_abandoned_baby(data))
        patterns.extend(self._detect_doji_patterns(data))
        patterns.extend(self._detect_force_candles(data))
        
        # Padrões de média confiabilidade
        patterns.extend(self._detect_piercing_dark_cloud(data))
        patterns.extend(self._detect_harami_patterns(data))
        patterns.extend(self._detect_tweezers(data))
        patterns.extend(self._detect_kicker_patterns(data))
        patterns.extend(self._detect_marubozu(data))
        
        # Padrões de continuação
        patterns.extend(self._detect_three_methods(data))
        patterns.extend(self._detect_tasuki_gaps(data))
        
        # Remove padrões sobrepostos e ordena por força
        patterns = self._filter_overlapping_patterns(patterns)
        patterns.sort(key=lambda x: x.reliability_score * x.signal_strength, reverse=True)
        
        return patterns[:10]  # Máximo 10 padrões
    
    def _detect_three_soldiers_crows(self, data: pd.DataFrame) -> List[CandlestickPattern]:
        """Detecta 3 Soldados Brancos e 3 Corvos Pretos"""
        patterns = []
        
        for i in range(2, len(data)):
            # 3 Soldados Brancos (bullish)
            if (data['is_green'].iloc[i-2:i+1].all() and
                data['close_price'].iloc[i] > data['close_price'].iloc[i-1] > data['close_price'].iloc[i-2] and
                data['open_price'].iloc[i-1] > data['low_price'].iloc[i-2] and
                data['open_price'].iloc[i] > data['low_price'].iloc[i-1]):
                
                pattern = CandlestickPattern(
                    name="3 Soldados Brancos",
                    pattern_type="bullish",
                    confidence_level="high",
                    signal_strength=0.85,
                    entry_price=data['close_price'].iloc[i] * 1.001,
                    stop_loss=data['low_price'].iloc[i-2:i+1].min() * 0.995,
                    target_price=data['close_price'].iloc[i] * 1.02,
                    position_index=i,
                    description="Três candles verdes consecutivos em ascensão",
                    reliability_score=0.9
                )
                patterns.append(pattern)
            
            # 3 Corvos Pretos (bearish)
            elif (data['is_red'].iloc[i-2:i+1].all() and
                  data['close_price'].iloc[i] < data['close_price'].iloc[i-1] < data['close_price'].iloc[i-2] and
                  data['open_price'].iloc[i-1] < data['high_price'].iloc[i-2] and
                  data['open_price'].iloc[i] < data['high_price'].iloc[i-1]):
                
                pattern = CandlestickPattern(
                    name="3 Corvos Pretos",
                    pattern_type="bearish",
                    confidence_level="high",
                    signal_strength=0.85,
                    entry_price=data['close_price'].iloc[i] * 0.999,
                    stop_loss=data['high_price'].iloc[i-2:i+1].max() * 1.005,
                    target_price=data['close_price'].iloc[i] * 0.98,
                    position_index=i,
                    description="Três candles vermelhos consecutivos em queda",
                    reliability_score=0.9
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_engulfing_patterns(self, data: pd.DataFrame) -> List[CandlestickPattern]:
        """Detecta Engolfos de Alta e Baixa"""
        patterns = []
        
        for i in range(1, len(data)):
            prev_body = data['body_size'].iloc[i-1]
            curr_body = data['body_size'].iloc[i]
            
            # Engolfo de Alta
            if (data['is_red'].iloc[i-1] and data['is_green'].iloc[i] and
                data['open_price'].iloc[i] < data['close_price'].iloc[i-1] and
                data['close_price'].iloc[i] > data['open_price'].iloc[i-1] and
                curr_body > prev_body * 1.5):
                
                pattern = CandlestickPattern(
                    name="Engolfo de Alta",
                    pattern_type="bullish",
                    confidence_level="medium",
                    signal_strength=0.75,
                    entry_price=data['close_price'].iloc[i] * 1.001,
                    stop_loss=data['low_price'].iloc[i] * 0.995,
                    target_price=data['close_price'].iloc[i] * 1.015,
                    position_index=i,
                    description="Candle verde engolfa completamente o anterior vermelho",
                    reliability_score=0.75
                )
                patterns.append(pattern)
            
            # Engolfo de Baixa
            elif (data['is_green'].iloc[i-1] and data['is_red'].iloc[i] and
                  data['open_price'].iloc[i] > data['close_price'].iloc[i-1] and
                  data['close_price'].iloc[i] < data['open_price'].iloc[i-1] and
                  curr_body > prev_body * 1.5):
                
                pattern = CandlestickPattern(
                    name="Engolfo de Baixa",
                    pattern_type="bearish",
                    confidence_level="medium",
                    signal_strength=0.75,
                    entry_price=data['close_price'].iloc[i] * 0.999,
                    stop_loss=data['high_price'].iloc[i] * 1.005,
                    target_price=data['close_price'].iloc[i] * 0.985,
                    position_index=i,
                    description="Candle vermelho engolfa completamente o anterior verde",
                    reliability_score=0.75
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_hammer_patterns(self, data: pd.DataFrame) -> List[CandlestickPattern]:
        """Detecta Martelo, Martelo Invertido, Enforcado e Estrela Cadente"""
        patterns = []
        
        for i in range(1, len(data)):
            upper_shadow_ratio = data['upper_shadow_to_body'].iloc[i]
            lower_shadow_ratio = data['lower_shadow_to_body'].iloc[i]
            is_small_body = data['is_small_body'].iloc[i]
            
            # Martelo (após tendência de baixa)
            if (is_small_body and lower_shadow_ratio >= 2.0 and upper_shadow_ratio <= 0.5 and
                self._is_downtrend(data, i, 5)):
                
                pattern = CandlestickPattern(
                    name="Martelo",
                    pattern_type="bullish",
                    confidence_level="medium",
                    signal_strength=0.7,
                    entry_price=data['high_price'].iloc[i] * 1.001,
                    stop_loss=data['low_price'].iloc[i] * 0.99,
                    target_price=data['close_price'].iloc[i] * 1.02,
                    position_index=i,
                    description="Corpo pequeno com sombra inferior longa após queda",
                    reliability_score=0.7
                )
                patterns.append(pattern)
            
            # Martelo Invertido (após tendência de baixa)
            elif (is_small_body and upper_shadow_ratio >= 2.0 and lower_shadow_ratio <= 0.5 and
                  self._is_downtrend(data, i, 5)):
                
                pattern = CandlestickPattern(
                    name="Martelo Invertido",
                    pattern_type="bullish",
                    confidence_level="medium",
                    signal_strength=0.65,
                    entry_price=data['close_price'].iloc[i] * 1.002,
                    stop_loss=data['low_price'].iloc[i] * 0.99,
                    target_price=data['close_price'].iloc[i] * 1.025,
                    position_index=i,
                    description="Corpo pequeno com sombra superior longa após queda",
                    reliability_score=0.65
                )
                patterns.append(pattern)
            
            # Homem Enforcado (após tendência de alta)
            elif (is_small_body and lower_shadow_ratio >= 2.0 and upper_shadow_ratio <= 0.5 and
                  self._is_uptrend(data, i, 5)):
                
                pattern = CandlestickPattern(
                    name="Homem Enforcado",
                    pattern_type="bearish",
                    confidence_level="medium",
                    signal_strength=0.65,
                    entry_price=data['close_price'].iloc[i] * 0.998,
                    stop_loss=data['high_price'].iloc[i] * 1.01,
                    target_price=data['close_price'].iloc[i] * 0.975,
                    position_index=i,
                    description="Corpo pequeno com sombra inferior longa após alta",
                    reliability_score=0.65
                )
                patterns.append(pattern)
            
            # Estrela Cadente (após tendência de alta)
            elif (is_small_body and upper_shadow_ratio >= 2.0 and lower_shadow_ratio <= 0.5 and
                  self._is_uptrend(data, i, 5)):
                
                pattern = CandlestickPattern(
                    name="Estrela Cadente",
                    pattern_type="bearish",
                    confidence_level="low",
                    signal_strength=0.6,
                    entry_price=data['close_price'].iloc[i] * 0.998,
                    stop_loss=data['high_price'].iloc[i] * 1.01,
                    target_price=data['close_price'].iloc[i] * 0.98,
                    position_index=i,
                    description="Corpo pequeno com sombra superior longa após alta",
                    reliability_score=0.5
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_star_patterns(self, data: pd.DataFrame) -> List[CandlestickPattern]:
        """Detecta Estrela da Manhã e Estrela da Noite"""
        patterns = []
        
        for i in range(2, len(data)):
            # Estrela da Manhã
            if (data['is_red'].iloc[i-2] and
                data['is_small_body'].iloc[i-1] and
                data['is_green'].iloc[i] and
                data['close_price'].iloc[i-1] < data['close_price'].iloc[i-2] and
                data['close_price'].iloc[i] > (data['open_price'].iloc[i-2] + data['close_price'].iloc[i-2]) / 2):
                
                pattern = CandlestickPattern(
                    name="Estrela da Manhã",
                    pattern_type="bullish",
                    confidence_level="high",
                    signal_strength=0.8,
                    entry_price=data['close_price'].iloc[i] * 1.001,
                    stop_loss=data['low_price'].iloc[i-2:i+1].min() * 0.995,
                    target_price=data['close_price'].iloc[i] * 1.025,
                    position_index=i,
                    description="Padrão de reversão bullish de 3 candles",
                    reliability_score=0.85
                )
                patterns.append(pattern)
            
            # Estrela da Noite
            elif (data['is_green'].iloc[i-2] and
                  data['is_small_body'].iloc[i-1] and
                  data['is_red'].iloc[i] and
                  data['close_price'].iloc[i-1] > data['close_price'].iloc[i-2] and
                  data['close_price'].iloc[i] < (data['open_price'].iloc[i-2] + data['close_price'].iloc[i-2]) / 2):
                
                pattern = CandlestickPattern(
                    name="Estrela da Noite",
                    pattern_type="bearish",
                    confidence_level="high",
                    signal_strength=0.8,
                    entry_price=data['close_price'].iloc[i] * 0.999,
                    stop_loss=data['high_price'].iloc[i-2:i+1].max() * 1.005,
                    target_price=data['close_price'].iloc[i] * 0.975,
                    position_index=i,
                    description="Padrão de reversão bearish de 3 candles",
                    reliability_score=0.85
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_doji_patterns(self, data: pd.DataFrame) -> List[CandlestickPattern]:
        """Detecta vários tipos de Doji"""
        patterns = []
        
        for i in range(len(data)):
            if not data['is_doji'].iloc[i]:
                continue
            
            upper_shadow = data['upper_shadow'].iloc[i]
            lower_shadow = data['lower_shadow'].iloc[i]
            total_range = data['total_range'].iloc[i]
            
            # Doji Libélula
            if lower_shadow >= total_range * 0.7 and upper_shadow <= total_range * 0.1:
                pattern = CandlestickPattern(
                    name="Doji Libélula",
                    pattern_type="bullish",
                    confidence_level="medium",
                    signal_strength=0.6,
                    entry_price=data['close_price'].iloc[i] * 1.001,
                    stop_loss=data['low_price'].iloc[i] * 0.995,
                    target_price=data['close_price'].iloc[i] * 1.015,
                    position_index=i,
                    description="Doji com sombra inferior longa",
                    reliability_score=0.6
                )
                patterns.append(pattern)
            
            # Doji Lápide
            elif upper_shadow >= total_range * 0.7 and lower_shadow <= total_range * 0.1:
                pattern = CandlestickPattern(
                    name="Doji Lápide",
                    pattern_type="bearish",
                    confidence_level="medium",
                    signal_strength=0.6,
                    entry_price=data['close_price'].iloc[i] * 0.999,
                    stop_loss=data['high_price'].iloc[i] * 1.005,
                    target_price=data['close_price'].iloc[i] * 0.985,
                    position_index=i,
                    description="Doji com sombra superior longa",
                    reliability_score=0.6
                )
                patterns.append(pattern)
            
            # Doji Comum
            else:
                pattern = CandlestickPattern(
                    name="Doji",
                    pattern_type="neutral",
                    confidence_level="low",
                    signal_strength=0.4,
                    entry_price=data['close_price'].iloc[i],
                    stop_loss=data['low_price'].iloc[i] * 0.99,
                    target_price=data['close_price'].iloc[i] * 1.01,
                    position_index=i,
                    description="Indecisão do mercado",
                    reliability_score=0.4
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_force_candles(self, data: pd.DataFrame) -> List[CandlestickPattern]:
        """Detecta Candles de Força"""
        patterns = []
        
        for i in range(5, len(data)):
            current_body = data['body_size'].iloc[i]
            avg_body = data['body_size'].iloc[i-5:i].mean()
            
            # Candle de força se for 3x maior que a média
            if current_body >= avg_body * 3:
                pattern_type = "bullish" if data['is_green'].iloc[i] else "bearish"
                
                pattern = CandlestickPattern(
                    name="Candle de Força",
                    pattern_type=pattern_type,
                    confidence_level="high",
                    signal_strength=0.8,
                    entry_price=data['close_price'].iloc[i] * (1.001 if pattern_type == "bullish" else 0.999),
                    stop_loss=(data['open_price'].iloc[i] * 0.995 if pattern_type == "bullish" 
                              else data['open_price'].iloc[i] * 1.005),
                    target_price=data['close_price'].iloc[i] * (1.02 if pattern_type == "bullish" else 0.98),
                    position_index=i,
                    description=f"Candle {'verde' if pattern_type == 'bullish' else 'vermelho'} muito maior que média",
                    reliability_score=0.8
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_piercing_dark_cloud(self, data: pd.DataFrame) -> List[CandlestickPattern]:
        """Detecta Piercing Line e Nuvem Negra"""
        patterns = []
        
        for i in range(1, len(data)):
            # Piercing Line
            if (data['is_red'].iloc[i-1] and data['is_green'].iloc[i] and
                data['is_large_body'].iloc[i-1] and data['is_large_body'].iloc[i] and
                data['close_price'].iloc[i] > (data['open_price'].iloc[i-1] + data['close_price'].iloc[i-1]) / 2 and
                data['close_price'].iloc[i] < data['open_price'].iloc[i-1]):
                
                pattern = CandlestickPattern(
                    name="Piercing Line",
                    pattern_type="bullish",
                    confidence_level="medium",
                    signal_strength=0.7,
                    entry_price=data['close_price'].iloc[i] * 1.001,
                    stop_loss=data['low_price'].iloc[i] * 0.995,
                    target_price=data['close_price'].iloc[i] * 1.02,
                    position_index=i,
                    description="Candle verde penetra mais de 50% do anterior vermelho",
                    reliability_score=0.65
                )
                patterns.append(pattern)
            
            # Nuvem Negra
            elif (data['is_green'].iloc[i-1] and data['is_red'].iloc[i] and
                  data['is_large_body'].iloc[i-1] and data['is_large_body'].iloc[i] and
                  data['close_price'].iloc[i] < (data['open_price'].iloc[i-1] + data['close_price'].iloc[i-1]) / 2 and
                  data['close_price'].iloc[i] > data['open_price'].iloc[i-1]):
                
                pattern = CandlestickPattern(
                    name="Nuvem Negra",
                    pattern_type="bearish",
                    confidence_level="medium",
                    signal_strength=0.7,
                    entry_price=data['close_price'].iloc[i] * 0.999,
                    stop_loss=data['high_price'].iloc[i] * 1.005,
                    target_price=data['close_price'].iloc[i] * 0.98,
                    position_index=i,
                    description="Candle vermelho penetra mais de 50% do anterior verde",
                    reliability_score=0.65
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_harami_patterns(self, data: pd.DataFrame) -> List[CandlestickPattern]:
        """Detecta Harami (Mulher Grávida)"""
        patterns = []
        
        for i in range(1, len(data)):
            prev_body = data['body_size'].iloc[i-1]
            curr_body = data['body_size'].iloc[i]
            
            # Verifica se o segundo candle está dentro do primeiro
            is_inside = (max(data['open_price'].iloc[i], data['close_price'].iloc[i]) < 
                        max(data['open_price'].iloc[i-1], data['close_price'].iloc[i-1]) and
                        min(data['open_price'].iloc[i], data['close_price'].iloc[i]) > 
                        min(data['open_price'].iloc[i-1], data['close_price'].iloc[i-1]))
            
            if is_inside and prev_body > curr_body * 2:
                # Harami de Alta
                if data['is_red'].iloc[i-1]:
                    pattern = CandlestickPattern(
                        name="Harami de Alta",
                        pattern_type="bullish",
                        confidence_level="low",
                        signal_strength=0.5,
                        entry_price=data['close_price'].iloc[i] * 1.001,
                        stop_loss=data['low_price'].iloc[i-1] * 0.995,
                        target_price=data['close_price'].iloc[i] * 1.015,
                        position_index=i,
                        description="Candle pequeno dentro de candle vermelho grande",
                        reliability_score=0.45
                    )
                    patterns.append(pattern)
                
                # Harami de Baixa
                elif data['is_green'].iloc[i-1]:
                    pattern = CandlestickPattern(
                        name="Harami de Baixa",
                        pattern_type="bearish",
                        confidence_level="low",
                        signal_strength=0.5,
                        entry_price=data['close_price'].iloc[i] * 0.999,
                        stop_loss=data['high_price'].iloc[i-1] * 1.005,
                        target_price=data['close_price'].iloc[i] * 0.985,
                        position_index=i,
                        description="Candle pequeno dentro de candle verde grande",
                        reliability_score=0.45
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _detect_tweezers(self, data: pd.DataFrame) -> List[CandlestickPattern]:
        """Detecta Pinças de Topo e Fundo"""
        patterns = []
        
        for i in range(1, len(data)):
            high_diff = abs(data['high_price'].iloc[i] - data['high_price'].iloc[i-1])
            low_diff = abs(data['low_price'].iloc[i] - data['low_price'].iloc[i-1])
            avg_price = (data['high_price'].iloc[i] + data['low_price'].iloc[i]) / 2
            
            # Pinça de Topo
            if (high_diff <= avg_price * 0.002 and  # Máximas muito próximas
                self._is_uptrend(data, i, 3)):
                
                pattern = CandlestickPattern(
                    name="Pinça de Topo",
                    pattern_type="bearish",
                    confidence_level="medium",
                    signal_strength=0.6,
                    entry_price=data['close_price'].iloc[i] * 0.999,
                    stop_loss=data['high_price'].iloc[i] * 1.005,
                    target_price=data['close_price'].iloc[i] * 0.985,
                    position_index=i,
                    description="Duas máximas iguais após alta",
                    reliability_score=0.6
                )
                patterns.append(pattern)
            
            # Pinça de Fundo
            elif (low_diff <= avg_price * 0.002 and  # Mínimas muito próximas
                  self._is_downtrend(data, i, 3)):
                
                pattern = CandlestickPattern(
                    name="Pinça de Fundo",
                    pattern_type="bullish",
                    confidence_level="medium",
                    signal_strength=0.6,
                    entry_price=data['close_price'].iloc[i] * 1.001,
                    stop_loss=data['low_price'].iloc[i] * 0.995,
                    target_price=data['close_price'].iloc[i] * 1.015,
                    position_index=i,
                    description="Duas mínimas iguais após queda",
                    reliability_score=0.6
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_kicker_patterns(self, data: pd.DataFrame) -> List[CandlestickPattern]:
        """Detecta Chutes (Kicker)"""
        patterns = []
        
        for i in range(1, len(data)):
            has_gap = data['gap_up'].iloc[i] or data['gap_down'].iloc[i]
            
            if (has_gap and 
                data['is_large_body'].iloc[i-1] and 
                data['is_large_body'].iloc[i]):
                
                # Kicker de Alta
                if data['is_red'].iloc[i-1] and data['is_green'].iloc[i] and data['gap_up'].iloc[i]:
                    pattern = CandlestickPattern(
                        name="Kicker de Alta",
                        pattern_type="bullish",
                        confidence_level="high",
                        signal_strength=0.8,
                        entry_price=data['close_price'].iloc[i] * 1.001,
                        stop_loss=data['open_price'].iloc[i] * 0.995,
                        target_price=data['close_price'].iloc[i] * 1.025,
                        position_index=i,
                        description="Gap de alta entre candles grandes de cores opostas",
                        reliability_score=0.8
                    )
                    patterns.append(pattern)
                
                # Kicker de Baixa
                elif data['is_green'].iloc[i-1] and data['is_red'].iloc[i] and data['gap_down'].iloc[i]:
                    pattern = CandlestickPattern(
                        name="Kicker de Baixa",
                        pattern_type="bearish",
                        confidence_level="high",
                        signal_strength=0.8,
                        entry_price=data['close_price'].iloc[i] * 0.999,
                        stop_loss=data['open_price'].iloc[i] * 1.005,
                        target_price=data['close_price'].iloc[i] * 0.975,
                        position_index=i,
                        description="Gap de baixa entre candles grandes de cores opostas",
                        reliability_score=0.8
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _detect_marubozu(self, data: pd.DataFrame) -> List[CandlestickPattern]:
        """Detecta Marubozu (Velas Carecas)"""
        patterns = []
        
        for i in range(len(data)):
            total_range = data['total_range'].iloc[i]
            upper_shadow = data['upper_shadow'].iloc[i]
            lower_shadow = data['lower_shadow'].iloc[i]
            
            # Marubozu se sombras são < 10% do range total
            if (upper_shadow <= total_range * 0.1 and 
                lower_shadow <= total_range * 0.1 and
                data['is_large_body'].iloc[i]):
                
                pattern_type = "bullish" if data['is_green'].iloc[i] else "bearish"
                
                pattern = CandlestickPattern(
                    name="Marubozu",
                    pattern_type=pattern_type,
                    confidence_level="medium",
                    signal_strength=0.65,
                    entry_price=data['close_price'].iloc[i] * (1.001 if pattern_type == "bullish" else 0.999),
                    stop_loss=(data['open_price'].iloc[i] * 0.995 if pattern_type == "bullish" 
                              else data['open_price'].iloc[i] * 1.005),
                    target_price=data['close_price'].iloc[i] * (1.015 if pattern_type == "bullish" else 0.985),
                    position_index=i,
                    description="Candle sem sombras (abertura=mínima, fechamento=máxima)",
                    reliability_score=0.6
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_three_methods(self, data: pd.DataFrame) -> List[CandlestickPattern]:
        """Detecta Padrões de 3 Métodos (Rising/Falling Three Methods)"""
        patterns = []
        
        for i in range(4, len(data)):
            # Rising Three Methods
            if (data['is_green'].iloc[i-4] and data['is_large_body'].iloc[i-4] and
                data['is_red'].iloc[i-3:i].all() and
                data['is_small_body'].iloc[i-3:i].all() and
                data['is_green'].iloc[i] and data['is_large_body'].iloc[i] and
                data['close_price'].iloc[i] > data['close_price'].iloc[i-4]):
                
                pattern = CandlestickPattern(
                    name="Rising Three Methods",
                    pattern_type="bullish",
                    confidence_level="high",
                    signal_strength=0.8,
                    entry_price=data['close_price'].iloc[i] * 1.001,
                    stop_loss=data['low_price'].iloc[i-4:i+1].min() * 0.995,
                    target_price=data['close_price'].iloc[i] * 1.02,
                    position_index=i,
                    description="Continuação de alta: candle verde, 3 vermelhos pequenos, candle verde",
                    reliability_score=0.8
                )
                patterns.append(pattern)
            
            # Falling Three Methods
            elif (data['is_red'].iloc[i-4] and data['is_large_body'].iloc[i-4] and
                  data['is_green'].iloc[i-3:i].all() and
                  data['is_small_body'].iloc[i-3:i].all() and
                  data['is_red'].iloc[i] and data['is_large_body'].iloc[i] and
                  data['close_price'].iloc[i] < data['close_price'].iloc[i-4]):
                
                pattern = CandlestickPattern(
                    name="Falling Three Methods",
                    pattern_type="bearish",
                    confidence_level="high",
                    signal_strength=0.8,
                    entry_price=data['close_price'].iloc[i] * 0.999,
                    stop_loss=data['high_price'].iloc[i-4:i+1].max() * 1.005,
                    target_price=data['close_price'].iloc[i] * 0.98,
                    position_index=i,
                    description="Continuação de baixa: candle vermelho, 3 verdes pequenos, candle vermelho",
                    reliability_score=0.8
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_tasuki_gaps(self, data: pd.DataFrame) -> List[CandlestickPattern]:
        """Detecta Gaps Tasuki"""
        patterns = []
        
        for i in range(2, len(data)):
            # Gap de Alta Tasuki
            if (data['is_green'].iloc[i-2] and data['is_large_body'].iloc[i-2] and
                data['is_green'].iloc[i-1] and data['gap_up'].iloc[i-1] and
                data['is_red'].iloc[i] and
                data['low_price'].iloc[i-1] < data['close_price'].iloc[i] < data['open_price'].iloc[i-1]):
                
                pattern = CandlestickPattern(
                    name="Gap de Alta Tasuki",
                    pattern_type="bullish",
                    confidence_level="medium",
                    signal_strength=0.65,
                    entry_price=data['close_price'].iloc[i] * 1.001,
                    stop_loss=data['low_price'].iloc[i-2:i+1].min() * 0.995,
                    target_price=data['close_price'].iloc[i] * 1.02,
                    position_index=i,
                    description="Continuação de alta: gap não fechado indica força compradora",
                    reliability_score=0.65
                )
                patterns.append(pattern)
            
            # Gap de Baixa Tasuki
            elif (data['is_red'].iloc[i-2] and data['is_large_body'].iloc[i-2] and
                  data['is_red'].iloc[i-1] and data['gap_down'].iloc[i-1] and
                  data['is_green'].iloc[i] and
                  data['high_price'].iloc[i-1] > data['close_price'].iloc[i] > data['open_price'].iloc[i-1]):
                
                pattern = CandlestickPattern(
                    name="Gap de Baixa Tasuki",
                    pattern_type="bearish",
                    confidence_level="medium",
                    signal_strength=0.65,
                    entry_price=data['close_price'].iloc[i] * 0.999,
                    stop_loss=data['high_price'].iloc[i-2:i+1].max() * 1.005,
                    target_price=data['close_price'].iloc[i] * 0.98,
                    position_index=i,
                    description="Continuação de baixa: gap não fechado indica força vendedora",
                    reliability_score=0.65
                )
                patterns.append(pattern)
        
        return patterns
    
    def _detect_abandoned_baby(self, data: pd.DataFrame) -> List[CandlestickPattern]:
        """Detecta Bebê Abandonado"""
        patterns = []
        
        for i in range(2, len(data)):
            # Bebê Abandonado de Alta
            if (data['is_red'].iloc[i-2] and data['is_large_body'].iloc[i-2] and
                data['is_small_body'].iloc[i-1] and data['gap_down'].iloc[i-1] and
                data['is_green'].iloc[i] and data['is_large_body'].iloc[i] and
                data['gap_up'].iloc[i]):
                
                pattern = CandlestickPattern(
                    name="Bebê Abandonado de Alta",
                    pattern_type="bullish",
                    confidence_level="high",
                    signal_strength=0.85,
                    entry_price=data['close_price'].iloc[i] * 1.001,
                    stop_loss=data['low_price'].iloc[i-1] * 0.995,
                    target_price=data['close_price'].iloc[i] * 1.025,
                    position_index=i,
                    description="Candle pequeno isolado por gaps indicando reversão para alta",
                    reliability_score=0.85
                )
                patterns.append(pattern)
            
            # Bebê Abandonado de Baixa
            elif (data['is_green'].iloc[i-2] and data['is_large_body'].iloc[i-2] and
                  data['is_small_body'].iloc[i-1] and data['gap_up'].iloc[i-1] and
                  data['is_red'].iloc[i] and data['is_large_body'].iloc[i] and
                  data['gap_down'].iloc[i]):
                
                pattern = CandlestickPattern(
                    name="Bebê Abandonado de Baixa",
                    pattern_type="bearish",
                    confidence_level="high",
                    signal_strength=0.85,
                    entry_price=data['close_price'].iloc[i] * 0.999,
                    stop_loss=data['high_price'].iloc[i-1] * 1.005,
                    target_price=data['close_price'].iloc[i] * 0.975,
                    position_index=i,
                    description="Candle pequeno isolado por gaps indicando reversão para baixa",
                    reliability_score=0.85
                )
                patterns.append(pattern)
        
        return patterns
    
    def _is_uptrend(self, data: pd.DataFrame, index: int, periods: int) -> bool:
        """Verifica se está em tendência de alta"""
        if index < periods:
            return False
        
        closes = data['close_price'].iloc[index-periods:index]
        return closes.iloc[-1] > closes.iloc[0] and closes.is_monotonic_increasing
    
    def _is_downtrend(self, data: pd.DataFrame, index: int, periods: int) -> bool:
        """Verifica se está em tendência de baixa"""
        if index < periods:
            return False
        
        closes = data['close_price'].iloc[index-periods:index]
        return closes.iloc[-1] < closes.iloc[0] and closes.is_monotonic_decreasing
    
    def _filter_overlapping_patterns(self, patterns: List[CandlestickPattern]) -> List[CandlestickPattern]:
        """Remove padrões sobrepostos, mantendo os de maior confiabilidade"""
        if not patterns:
            return patterns
        
        # Ordena por índice
        patterns.sort(key=lambda x: x.position_index)
        
        filtered = []
        last_index = -5  # Permite padrões com pelo menos 5 períodos de distância
        
        for pattern in patterns:
            if pattern.position_index >= last_index + 3:  # Mínimo 3 períodos de separação
                filtered.append(pattern)
                last_index = pattern.position_index
        
        return filtered

def generate_candlestick_signals(df: pd.DataFrame, symbol: str) -> List[Dict]:
    """Função principal para gerar sinais baseados em candlestick patterns"""
    
    detector = CandlestickDetector()
    patterns = detector.detect_all_patterns(df)
    
    signals = []
    
    for pattern in patterns:
        # Só gera sinais para padrões bullish/bearish com confiabilidade média+
        if (pattern.pattern_type in ['bullish', 'bearish'] and 
            pattern.confidence_level in ['medium', 'high'] and
            pattern.reliability_score >= 0.6):
            
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
                'source': 'candlestick_patterns'
            }
            
            signals.append(signal)
    
    return signals

# Exemplo de uso
if __name__ == "__main__":
    # Teste com dados sintéticos
    import numpy as np
    
    # Gera dados de teste
    periods = 100
    dates = pd.date_range(start='2024-01-01', periods=periods, freq='5min')
    
    base_price = 50000
    prices = []
    
    for i in range(periods):
        if i == 0:
            prices.append(base_price)
        else:
            change = np.random.normal(0, 0.01)  # 1% de volatilidade
            prices.append(prices[-1] * (1 + change))
    
    # Cria padrões sintéticos
    df = pd.DataFrame({
        'timestamp': dates,
        'open_price': prices,
        'high_price': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
        'low_price': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
        'close_price': [p * (1 + np.random.normal(0, 0.003)) for p in prices],
        'volume': [abs(np.random.normal(1000000, 200000)) for _ in range(periods)]
    })
    
    # Detecta padrões
    detector = CandlestickDetector()
    patterns = detector.detect_all_patterns(df)
    
    print(f"Padrões detectados: {len(patterns)}")
    for pattern in patterns[:5]:
        print(f"- {pattern.name}: {pattern.pattern_type} | Confiança: {pattern.reliability_score:.2f}")