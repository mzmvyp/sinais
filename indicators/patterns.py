"""
Padrões Gráficos SIMPLIFICADOS - Apenas Double Top/Bottom
OHO, OCO e Cup & Handle DESABILITADOS conforme solicitado
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging
from datetime import datetime

from core.data_reader import MarketData
from core.signal_writer import TradingSignal
from config.settings import settings

@dataclass
class PatternResult:
    """Resultado de detecção de padrão"""
    pattern_name: str
    pattern_type: str  # 'bullish', 'bearish', 'neutral'
    confidence: float
    strength: float
    entry_price: float
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    key_points: List[Dict] = None
    formation_data: Dict = None
    
    def __post_init__(self):
        if self.key_points is None:
            self.key_points = []
        if self.formation_data is None:
            self.formation_data = {}

class DoubleTopBottomDetector:
    """Detector de Topo Duplo e Fundo Duplo - ÚNICO PADRÃO ATIVO"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tolerance = settings.patterns.double_tolerance
        self.min_distance = settings.patterns.double_min_distance
        self.min_significance = settings.patterns.double_min_significance
    
    def detect_double_patterns(self, market_data: MarketData) -> List[PatternResult]:
        """Detecta APENAS padrões de topo duplo e fundo duplo"""
        df = market_data.data
        patterns = []
        
        # Verifica se há dados suficientes
        min_required = self.min_distance * 4
        if len(df) < min_required:
            self.logger.debug(f"Dados insuficientes para double patterns: {len(df)} < {min_required}")
            return patterns
        
        # Detecta Topo Duplo (bearish)
        double_tops = self._find_double_tops(df)
        patterns.extend(double_tops)
        
        # Detecta Fundo Duplo (bullish)
        double_bottoms = self._find_double_bottoms(df)
        patterns.extend(double_bottoms)
        
        # Filtra e limita padrões de qualidade
        quality_patterns = [
            p for p in patterns 
            if p.strength >= settings.patterns.min_pattern_strength
        ]
        
        # Ordena por confiança e pega os melhores
        quality_patterns.sort(key=lambda x: x.confidence * x.strength, reverse=True)
        final_patterns = quality_patterns[:2]  # Máximo 2 padrões
        
        self.logger.debug(f"Double patterns para {market_data.symbol}: {len(final_patterns)} detectados")
        return final_patterns
    
    def _find_double_tops(self, df: pd.DataFrame) -> List[PatternResult]:
        """Detecta padrões de topo duplo"""
        patterns = []
        high_prices = df['high_price']
        
        # Encontra picos
        peaks = self._find_local_peaks(high_prices, window=3)
        
        if len(peaks) < 2:
            return patterns
        
        # Verifica cada par de picos (apenas os mais recentes)
        for i in range(max(0, len(peaks) - 5), len(peaks) - 1):
            for j in range(i + 1, len(peaks)):
                peak1_idx = peaks[i]
                peak2_idx = peaks[j]
                
                # Verifica distância mínima
                if peak2_idx - peak1_idx < self.min_distance:
                    continue
                
                peak1_price = high_prices.iloc[peak1_idx]
                peak2_price = high_prices.iloc[peak2_idx]
                
                # Verifica se os picos são similares
                if self._are_prices_similar(peak1_price, peak2_price, self.tolerance):
                    
                    # Encontra vale entre os picos de forma segura
                    valley_section = df['low_price'].iloc[peak1_idx:peak2_idx]
                    
                    if valley_section.empty or valley_section.isna().all():
                        continue
                    
                    valley_between = valley_section.min()
                    
                    # Encontra índice do vale de forma segura
                    valley_mask = valley_section == valley_between
                    if not valley_mask.any():
                        continue
                    
                    valley_idx = valley_section[valley_mask].index[0]
                    
                    # Valida que há diferença suficiente entre picos e vale
                    movement_significance = (peak1_price - valley_between) / peak1_price
                    if pd.isna(valley_between) or movement_significance < self.min_significance:
                        continue
                    
                    # Cria padrão de topo duplo
                    pattern = self._create_double_top_pattern(
                        df, peak1_idx, peak2_idx, valley_between, valley_idx
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _find_double_bottoms(self, df: pd.DataFrame) -> List[PatternResult]:
        """Detecta padrões de fundo duplo"""
        patterns = []
        low_prices = df['low_price']
        
        # Encontra vales
        valleys = self._find_local_valleys(low_prices, window=3)
        
        if len(valleys) < 2:
            return patterns
        
        # Verifica cada par de vales (apenas os mais recentes)
        for i in range(max(0, len(valleys) - 5), len(valleys) - 1):
            for j in range(i + 1, len(valleys)):
                valley1_idx = valleys[i]
                valley2_idx = valleys[j]
                
                # Verifica distância mínima
                if valley2_idx - valley1_idx < self.min_distance:
                    continue
                
                valley1_price = low_prices.iloc[valley1_idx]
                valley2_price = low_prices.iloc[valley2_idx]
                
                # Verifica se os vales são similares
                if self._are_prices_similar(valley1_price, valley2_price, self.tolerance):
                    
                    # Encontra pico entre os vales de forma segura
                    peak_section = df['high_price'].iloc[valley1_idx:valley2_idx]
                    
                    if peak_section.empty or peak_section.isna().all():
                        continue
                    
                    peak_between = peak_section.max()
                    
                    # Encontra índice do pico de forma segura
                    peak_mask = peak_section == peak_between
                    if not peak_mask.any():
                        continue
                    
                    peak_idx = peak_section[peak_mask].index[0]
                    
                    # Valida que há diferença suficiente entre pico e vales
                    movement_significance = (peak_between - valley1_price) / valley1_price
                    if pd.isna(peak_between) or movement_significance < self.min_significance:
                        continue
                    
                    # Cria padrão de fundo duplo
                    pattern = self._create_double_bottom_pattern(
                        df, valley1_idx, valley2_idx, peak_between, peak_idx
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _are_prices_similar(self, price1: float, price2: float, tolerance: float) -> bool:
        """Verifica se dois preços são similares dentro da tolerância"""
        diff = abs(price1 - price2) / max(price1, price2)
        return diff <= tolerance
    
    def _create_double_top_pattern(self, df: pd.DataFrame, peak1_idx: int, peak2_idx: int, 
                                  valley_price: float, valley_idx: int) -> PatternResult:
        """Cria padrão de topo duplo SIMPLIFICADO"""
        
        peak1_price = df['high_price'].iloc[peak1_idx]
        peak2_price = df['high_price'].iloc[peak2_idx]
        avg_peak = (peak1_price + peak2_price) / 2
        
        # Entrada conservadora: break abaixo do vale
        entry_price = valley_price * 0.995  # 0.5% abaixo do vale
        
        # Target simplificado: altura do padrão
        pattern_height = avg_peak - valley_price
        target_price = valley_price - (pattern_height * 0.8)  # 80% da altura
        
        # Stop loss: ligeiramente acima dos picos
        stop_loss = avg_peak * 1.015  # 1.5% acima dos picos
        
        key_points = [
            {'type': 'first_top', 'index': peak1_idx, 'price': peak1_price},
            {'type': 'valley', 'index': valley_idx, 'price': valley_price},
            {'type': 'second_top', 'index': peak2_idx, 'price': peak2_price}
        ]
        
        # Força baseada na qualidade do padrão
        price_similarity = 1 - abs(peak1_price - peak2_price) / max(peak1_price, peak2_price)
        duration_factor = min(1.0, (peak2_idx - peak1_idx) / 50)  # Duração ideal ~50 barras
        depth_factor = min(1.0, pattern_height / valley_price * 5)  # Profundidade ideal
        
        strength = (price_similarity + duration_factor + depth_factor) / 3
        
        return PatternResult(
            pattern_name="Double Top",
            pattern_type="bearish",
            confidence=0.72,  # Confiança moderada
            strength=strength,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            key_points=key_points,
            formation_data={
                'pattern_height': pattern_height,
                'duration': peak2_idx - peak1_idx,
                'similarity': price_similarity,
                'depth_factor': depth_factor
            }
        )
    
    def _create_double_bottom_pattern(self, df: pd.DataFrame, valley1_idx: int, valley2_idx: int, 
                                     peak_price: float, peak_idx: int) -> PatternResult:
        """Cria padrão de fundo duplo SIMPLIFICADO"""
        
        valley1_price = df['low_price'].iloc[valley1_idx]
        valley2_price = df['low_price'].iloc[valley2_idx]
        avg_valley = (valley1_price + valley2_price) / 2
        
        # Entrada conservadora: break acima do pico
        entry_price = peak_price * 1.005  # 0.5% acima do pico
        
        # Target simplificado: altura do padrão
        pattern_height = peak_price - avg_valley
        target_price = peak_price + (pattern_height * 0.8)  # 80% da altura
        
        # Stop loss: ligeiramente abaixo dos vales
        stop_loss = avg_valley * 0.985  # 1.5% abaixo dos vales
        
        key_points = [
            {'type': 'first_bottom', 'index': valley1_idx, 'price': valley1_price},
            {'type': 'peak', 'index': peak_idx, 'price': peak_price},
            {'type': 'second_bottom', 'index': valley2_idx, 'price': valley2_price}
        ]
        
        # Força baseada na qualidade do padrão
        price_similarity = 1 - abs(valley1_price - valley2_price) / max(valley1_price, valley2_price)
        duration_factor = min(1.0, (valley2_idx - valley1_idx) / 50)  # Duração ideal ~50 barras
        height_factor = min(1.0, pattern_height / avg_valley * 5)  # Altura ideal
        
        strength = (price_similarity + duration_factor + height_factor) / 3
        
        return PatternResult(
            pattern_name="Double Bottom",
            pattern_type="bullish",
            confidence=0.72,  # Confiança moderada
            strength=strength,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            key_points=key_points,
            formation_data={
                'pattern_height': pattern_height,
                'duration': valley2_idx - valley1_idx,
                'similarity': price_similarity,
                'height_factor': height_factor
            }
        )
    
    def _find_local_peaks(self, series: pd.Series, window: int) -> List[int]:
        """Encontra picos locais"""
        peaks = []
        for i in range(window, len(series) - window):
            if series.iloc[i] == series.iloc[i-window:i+window+1].max():
                peaks.append(i)
        return peaks
    
    def _find_local_valleys(self, series: pd.Series, window: int) -> List[int]:
        """Encontra vales locais"""
        valleys = []
        for i in range(window, len(series) - window):
            if series.iloc[i] == series.iloc[i-window:i+window+1].min():
                valleys.append(i)
        return valleys

# CLASSES DESABILITADAS - Mantidas apenas para compatibilidade
class HeadAndShouldersDetector:
    """DESABILITADO - OHO e OCO não são mais analisados"""
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("HeadAndShouldersDetector DESABILITADO conforme configuração")
    
    def detect_head_and_shoulders(self, market_data: MarketData) -> List[PatternResult]:
        return []  # Sempre retorna lista vazia

class CupAndHandleDetector:
    """DESABILITADO - Cup and Handle não é mais analisado"""
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("CupAndHandleDetector DESABILITADO conforme configuração")
    
    def detect_cup_and_handle(self, market_data: MarketData) -> List[PatternResult]:
        return []  # Sempre retorna lista vazia

class PatternAnalyzer:
    """Analisador SIMPLIFICADO de padrões - Apenas Double Top/Bottom"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Apenas Double Top/Bottom está ativo
        self.double_detector = DoubleTopBottomDetector()
        self.logger.info("PatternAnalyzer SIMPLIFICADO - APENAS Double Top/Bottom")
        
        # Detectores desabilitados (mantidos para compatibilidade)
        self.hs_detector = HeadAndShouldersDetector()
        self.cup_detector = CupAndHandleDetector()
        
    
    def analyze_all_patterns(self, market_data: MarketData) -> List[PatternResult]:
        """Executa APENAS detector de Double Top/Bottom"""
        all_patterns = []
        
        try:
            # APENAS Double Top/Bottom (sempre habilitado na versão simplificada)
            double_patterns = self.double_detector.detect_double_patterns(market_data)
            all_patterns.extend(double_patterns)
            
            self.logger.debug(f"Double patterns detectados para {market_data.symbol}: {len(double_patterns)}")
            
            # Filtra por força mínima
            quality_patterns = [
                p for p in all_patterns 
                if p.strength >= settings.patterns.min_pattern_strength
            ]
            
            # Ordena e limita
            quality_patterns.sort(key=lambda x: x.confidence * x.strength, reverse=True)
            final_patterns = quality_patterns[:settings.patterns.max_patterns_per_analysis]
            
            self.logger.info(f"Padrões para {market_data.symbol}: {len(final_patterns)} selecionados")
            
        except Exception as e:
            self.logger.error(f"Erro na análise de padrões para {market_data.symbol}: {e}")
            return []
        
        return final_patterns
    
    def generate_pattern_signals(self, market_data, patterns: List[PatternResult]) -> List[TradingSignal]:
        """Gera sinais de trading baseados nos padrões detectados"""
        signals = []
        
        for pattern in patterns:
            if pattern.confidence >= settings.analysis.confidence_threshold:
                
                signal_type = 'BUY_LONG' if pattern.pattern_type == 'bullish' else 'SELL_SHORT'
                
                # Cria sinal com market_data para cálculo técnico de stop/targets
                trading_signal = TradingSignal(
                    symbol=market_data.symbol,
                    signal_type=signal_type,
                    timeframe=market_data.timeframe,
                    detector_type='pattern',
                    detector_name=pattern.pattern_name.replace(' ', '_'),
                    confidence=pattern.confidence,
                    entry_price=pattern.entry_price,
                    market_data=market_data.data,  # NOVO: Dados para cálculo técnico
                    pattern_data=pattern.formation_data,
                )
                
                signals.append(trading_signal)
        
        return signals