"""
Padrões Gráficos - Detecção de formações através de análise de dados
OHO, OCO, Fundo Duplo, Cup & Handle, Triângulos, etc.
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

class HeadAndShouldersDetector:
    """Detector de Ombro-Cabeça-Ombro (OHO) e Invertido (OCO)"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.shoulder_tolerance = settings.patterns.hs_shoulder_tolerance
        self.min_duration = settings.patterns.hs_min_duration
    
    def detect_head_and_shoulders(self, market_data: MarketData) -> List[PatternResult]:
        """Detecta padrões OHO (bearish) e OCO (bullish)"""
        df = market_data.data
        patterns = []
        
        if len(df) < self.min_duration * 3:
            return patterns
        
        # Detecta OHO (Head and Shoulders) - bearish
        hs_patterns = self._find_head_and_shoulders_top(df)
        patterns.extend(hs_patterns)
        
        # Detecta OCO (Inverse Head and Shoulders) - bullish  
        ihs_patterns = self._find_inverse_head_and_shoulders(df)
        patterns.extend(ihs_patterns)
        
        return patterns
    
    def _find_head_and_shoulders_top(self, df: pd.DataFrame) -> List[PatternResult]:
        """Detecta OHO (padrão de topo - bearish)"""
        patterns = []
        high_prices = df['high_price']
        low_prices = df['low_price']
        
        # Encontra picos locais
        peaks = self._find_local_peaks(high_prices, window=5)
        
        if len(peaks) < 3:
            return patterns
        
        # Verifica cada combinação de 3 picos consecutivos
        for i in range(len(peaks) - 2):
            left_shoulder_idx = peaks[i]
            head_idx = peaks[i + 1]
            right_shoulder_idx = peaks[i + 2]
            
            left_shoulder = high_prices.iloc[left_shoulder_idx]
            head = high_prices.iloc[head_idx]
            right_shoulder = high_prices.iloc[right_shoulder_idx]
            
            # Verifica se forma OHO válido
            if self._is_valid_head_and_shoulders(left_shoulder, head, right_shoulder):
                
                # Encontra linha de pescoço (neckline)
                neckline = self._find_neckline(df, left_shoulder_idx, head_idx, right_shoulder_idx)
                
                if neckline:
                    pattern = self._create_hs_pattern(
                        df, left_shoulder_idx, head_idx, right_shoulder_idx, 
                        neckline, 'bearish'
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _find_inverse_head_and_shoulders(self, df: pd.DataFrame) -> List[PatternResult]:
        """Detecta OCO (padrão de fundo - bullish)"""
        patterns = []
        high_prices = df['high_price']
        low_prices = df['low_price']
        
        # Encontra vales locais
        valleys = self._find_local_valleys(low_prices, window=5)
        
        if len(valleys) < 3:
            return patterns
        
        # Verifica cada combinação de 3 vales consecutivos
        for i in range(len(valleys) - 2):
            left_shoulder_idx = valleys[i]
            head_idx = valleys[i + 1]
            right_shoulder_idx = valleys[i + 2]
            
            left_shoulder = low_prices.iloc[left_shoulder_idx]
            head = low_prices.iloc[head_idx]
            right_shoulder = low_prices.iloc[right_shoulder_idx]
            
            # Verifica se forma OCO válido (invertido)
            if self._is_valid_inverse_head_and_shoulders(left_shoulder, head, right_shoulder):
                
                # Encontra linha de pescoço (neckline)
                neckline = self._find_neckline_inverse(df, left_shoulder_idx, head_idx, right_shoulder_idx)
                
                if neckline:
                    pattern = self._create_hs_pattern(
                        df, left_shoulder_idx, head_idx, right_shoulder_idx, 
                        neckline, 'bullish'
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _is_valid_head_and_shoulders(self, left_shoulder: float, head: float, right_shoulder: float) -> bool:
        """Valida se é um OHO válido"""
        # Cabeça deve ser maior que os ombros
        if head <= left_shoulder or head <= right_shoulder:
            return False
        
        # Cabeça deve ser significativamente maior (nova validação)
        head_prominence = min((head - left_shoulder) / head, (head - right_shoulder) / head)
        if head_prominence < settings.patterns.hs_min_head_prominence:
            return False
        
        # Ombros devem estar dentro da tolerância
        shoulder_diff = abs(left_shoulder - right_shoulder) / max(left_shoulder, right_shoulder)
        
        return shoulder_diff <= self.shoulder_tolerance
    
    def _is_valid_inverse_head_and_shoulders(self, left_shoulder: float, head: float, right_shoulder: float) -> bool:
        """Valida se é um OCO válido"""
        # Cabeça deve ser menor que os ombros (padrão invertido)
        if head >= left_shoulder or head >= right_shoulder:
            return False
        
        # Cabeça deve ser significativamente menor (nova validação)
        head_prominence = min((left_shoulder - head) / left_shoulder, (right_shoulder - head) / right_shoulder)
        if head_prominence < settings.patterns.hs_min_head_prominence:
            return False
        
        # Ombros devem estar dentro da tolerância
        shoulder_diff = abs(left_shoulder - right_shoulder) / max(left_shoulder, right_shoulder)
        
        return shoulder_diff <= self.shoulder_tolerance
    
    def _find_neckline(self, df: pd.DataFrame, left_idx: int, head_idx: int, right_idx: int) -> Optional[float]:
        """Encontra linha de pescoço para OHO"""
        try:
            # Encontra vales entre os picos
            left_section = df['low_price'].iloc[left_idx:head_idx]
            right_section = df['low_price'].iloc[head_idx:right_idx]
            
            if left_section.empty or right_section.empty:
                return None
            
            left_valley = left_section.min()
            right_valley = right_section.min()
            
            # Verifica se há valores válidos
            if pd.isna(left_valley) or pd.isna(right_valley):
                return None
            
            # Neckline é aproximadamente a média dos vales
            return (left_valley + right_valley) / 2
        except Exception:
            return None
    
    def _find_neckline_inverse(self, df: pd.DataFrame, left_idx: int, head_idx: int, right_idx: int) -> Optional[float]:
        """Encontra linha de pescoço para OCO"""
        try:
            # Encontra picos entre os vales
            left_section = df['high_price'].iloc[left_idx:head_idx]
            right_section = df['high_price'].iloc[head_idx:right_idx]
            
            if left_section.empty or right_section.empty:
                return None
            
            left_peak = left_section.max()
            right_peak = right_section.max()
            
            # Verifica se há valores válidos
            if pd.isna(left_peak) or pd.isna(right_peak):
                return None
            
            # Neckline é aproximadamente a média dos picos
            return (left_peak + right_peak) / 2
        except Exception:
            return None
    
    def _create_hs_pattern(self, df: pd.DataFrame, left_idx: int, head_idx: int, 
                          right_idx: int, neckline: float, pattern_type: str) -> PatternResult:
        """Cria resultado do padrão OHO/OCO"""
        
        current_price = df['close_price'].iloc[-1]
        
        if pattern_type == 'bearish':  # OHO
            entry_price = neckline
            target_price = neckline - (df['high_price'].iloc[head_idx] - neckline)
            stop_loss = df['high_price'].iloc[head_idx] * 1.02  # 2% acima da cabeça
            confidence = 0.75
        else:  # OCO
            entry_price = neckline
            target_price = neckline + (neckline - df['low_price'].iloc[head_idx])
            stop_loss = df['low_price'].iloc[head_idx] * 0.98  # 2% abaixo da cabeça
            confidence = 0.75
        
        # Pontos-chave do padrão
        key_points = [
            {'type': 'left_shoulder', 'index': left_idx, 'price': df['high_price' if pattern_type == 'bearish' else 'low_price'].iloc[left_idx]},
            {'type': 'head', 'index': head_idx, 'price': df['high_price' if pattern_type == 'bearish' else 'low_price'].iloc[head_idx]},
            {'type': 'right_shoulder', 'index': right_idx, 'price': df['high_price' if pattern_type == 'bearish' else 'low_price'].iloc[right_idx]},
            {'type': 'neckline', 'price': neckline}
        ]
        
        # Calcula força baseada na proporção
        head_price = df['high_price' if pattern_type == 'bearish' else 'low_price'].iloc[head_idx]
        shoulder_avg = (df['high_price' if pattern_type == 'bearish' else 'low_price'].iloc[left_idx] + 
                       df['high_price' if pattern_type == 'bearish' else 'low_price'].iloc[right_idx]) / 2
        
        strength = min(0.9, abs(head_price - shoulder_avg) / shoulder_avg * 5)
        
        return PatternResult(
            pattern_name=f"Head and Shoulders {'Top' if pattern_type == 'bearish' else 'Bottom'}",
            pattern_type=pattern_type,
            confidence=confidence,
            strength=strength,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            key_points=key_points,
            formation_data={
                'neckline': neckline,
                'duration': right_idx - left_idx,
                'height': abs(head_price - neckline)
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

class DoubleTopBottomDetector:
    """Detector de Topo Duplo e Fundo Duplo"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tolerance = settings.patterns.double_tolerance
        self.min_distance = settings.patterns.double_min_distance
        self.min_significance = settings.patterns.double_min_significance
    
    def detect_double_patterns(self, market_data: MarketData) -> List[PatternResult]:
        """Detecta padrões de topo duplo e fundo duplo"""
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
        
        return patterns
    
    def _find_double_tops(self, df: pd.DataFrame) -> List[PatternResult]:
        """Detecta padrões de topo duplo"""
        patterns = []
        high_prices = df['high_price']
        
        # Encontra picos
        peaks = self._find_local_peaks(high_prices, window=3)
        
        if len(peaks) < 2:
            return patterns
        
        # Verifica cada par de picos
        for i in range(len(peaks) - 1):
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
        
        # Verifica cada par de vales
        for i in range(len(valleys) - 1):
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
        """Cria padrão de topo duplo"""
        
        peak1_price = df['high_price'].iloc[peak1_idx]
        peak2_price = df['high_price'].iloc[peak2_idx]
        avg_peak = (peak1_price + peak2_price) / 2
        
        entry_price = valley_price  # Break abaixo do vale
        target_price = valley_price - (avg_peak - valley_price)  # Altura do padrão
        stop_loss = avg_peak * 1.02  # 2% acima dos picos
        
        key_points = [
            {'type': 'first_top', 'index': peak1_idx, 'price': peak1_price},
            {'type': 'valley', 'index': valley_idx, 'price': valley_price},
            {'type': 'second_top', 'index': peak2_idx, 'price': peak2_price}
        ]
        
        # Força baseada na altura do padrão
        pattern_height = avg_peak - valley_price
        strength = min(0.9, pattern_height / valley_price * 2)
        
        return PatternResult(
            pattern_name="Double Top",
            pattern_type="bearish",
            confidence=0.7,
            strength=strength,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            key_points=key_points,
            formation_data={
                'pattern_height': pattern_height,
                'duration': peak2_idx - peak1_idx,
                'similarity': 1 - abs(peak1_price - peak2_price) / max(peak1_price, peak2_price)
            }
        )
    
    def _create_double_bottom_pattern(self, df: pd.DataFrame, valley1_idx: int, valley2_idx: int, 
                                     peak_price: float, peak_idx: int) -> PatternResult:
        """Cria padrão de fundo duplo"""
        
        valley1_price = df['low_price'].iloc[valley1_idx]
        valley2_price = df['low_price'].iloc[valley2_idx]
        avg_valley = (valley1_price + valley2_price) / 2
        
        entry_price = peak_price  # Break acima do pico
        target_price = peak_price + (peak_price - avg_valley)  # Altura do padrão
        stop_loss = avg_valley * 0.98  # 2% abaixo dos vales
        
        key_points = [
            {'type': 'first_bottom', 'index': valley1_idx, 'price': valley1_price},
            {'type': 'peak', 'index': peak_idx, 'price': peak_price},
            {'type': 'second_bottom', 'index': valley2_idx, 'price': valley2_price}
        ]
        
        # Força baseada na altura do padrão
        pattern_height = peak_price - avg_valley
        strength = min(0.9, pattern_height / avg_valley * 2)
        
        return PatternResult(
            pattern_name="Double Bottom",
            pattern_type="bullish",
            confidence=0.7,
            strength=strength,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            key_points=key_points,
            formation_data={
                'pattern_height': pattern_height,
                'duration': valley2_idx - valley1_idx,
                'similarity': 1 - abs(valley1_price - valley2_price) / max(valley1_price, valley2_price)
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

class CupAndHandleDetector:
    """Detector de Xícara com Alça (Cup and Handle)"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.min_depth = settings.patterns.cup_min_depth
        self.max_depth = settings.patterns.cup_max_depth
        self.min_duration = settings.patterns.cup_min_duration
        self.handle_max_retrace = settings.patterns.handle_max_retrace
    
    def detect_cup_and_handle(self, market_data: MarketData) -> List[PatternResult]:
        """Detecta padrões de xícara com alça"""
        df = market_data.data
        patterns = []
        
        if len(df) < self.min_duration * 2:
            return patterns
        
        high_prices = df['high_price']
        low_prices = df['low_price']
        
        # Procura por formações de xícara
        for start_idx in range(len(df) - self.min_duration):
            for end_idx in range(start_idx + self.min_duration, min(start_idx + self.min_duration * 3, len(df))):
                
                cup_pattern = self._analyze_cup_formation(df, start_idx, end_idx)
                
                if cup_pattern:
                    # Procura por alça após a xícara
                    handle_pattern = self._find_handle_after_cup(df, end_idx, cup_pattern)
                    
                    if handle_pattern:
                        # Combina xícara + alça
                        pattern = self._create_cup_and_handle_pattern(df, cup_pattern, handle_pattern)
                        patterns.append(pattern)
        
        return patterns
    
    def _analyze_cup_formation(self, df: pd.DataFrame, start_idx: int, end_idx: int) -> Optional[Dict]:
        """Analisa se há formação de xícara no período"""
        
        try:
            start_price = df['high_price'].iloc[start_idx]
            end_price = df['high_price'].iloc[end_idx]
            
            # Seção da xícara
            cup_section = df['low_price'].iloc[start_idx:end_idx]
            
            if cup_section.empty or cup_section.isna().all():
                return None
            
            lowest_price = cup_section.min()
            
            # Encontra o índice do menor preço de forma segura
            lowest_mask = cup_section == lowest_price
            if not lowest_mask.any():
                return None
            
            lowest_idx = cup_section[lowest_mask].index[0]
            
            # Verifica se forma uma xícara válida
            if pd.isna(start_price) or pd.isna(end_price) or pd.isna(lowest_price):
                return None
            
            depth = (start_price - lowest_price) / start_price
            
            # Verifica critérios da xícara
            if not (self.min_depth <= depth <= self.max_depth):
                return None
            
            # Preços de início e fim devem ser similares (±5%)
            price_similarity = abs(start_price - end_price) / start_price
            if price_similarity > 0.05:
                return None
            
            # O fundo deve estar aproximadamente no meio
            bottom_position = (lowest_idx - start_idx) / (end_idx - start_idx)
            if not (0.3 <= bottom_position <= 0.7):
                return None
            
            return {
                'start_idx': start_idx,
                'end_idx': end_idx,
                'start_price': start_price,
                'end_price': end_price,
                'lowest_price': lowest_price,
                'lowest_idx': lowest_idx,
                'depth': depth,
                'duration': end_idx - start_idx
            }
        except Exception as e:
            self.logger.debug(f"Erro na análise de xícara: {e}")
            return None
    
    def _find_handle_after_cup(self, df: pd.DataFrame, cup_end_idx: int, cup_data: Dict) -> Optional[Dict]:
        """Procura alça após a formação da xícara"""
        
        # A alça deve começar próximo ao fim da xícara
        handle_start_idx = cup_end_idx
        max_handle_length = min(cup_data['duration'] // 3, len(df) - cup_end_idx)
        
        if max_handle_length < 5:  # Alça muito curta
            return None
        
        # Procura por uma correção (alça) após a xícara
        for handle_end_idx in range(handle_start_idx + 5, handle_start_idx + max_handle_length):
            if handle_end_idx >= len(df):
                break
            
            handle_high = df['high_price'].iloc[handle_start_idx:handle_end_idx].max()
            handle_low = df['low_price'].iloc[handle_start_idx:handle_end_idx].min()
            
            # A alça não deve retracear muito da xícara
            retrace = (handle_high - handle_low) / handle_high
            
            if retrace <= self.handle_max_retrace:
                return {
                    'start_idx': handle_start_idx,
                    'end_idx': handle_end_idx,
                    'high_price': handle_high,
                    'low_price': handle_low,
                    'retrace': retrace,
                    'duration': handle_end_idx - handle_start_idx
                }
        
        return None
    
    def _create_cup_and_handle_pattern(self, df: pd.DataFrame, cup_data: Dict, handle_data: Dict) -> PatternResult:
        """Cria padrão de xícara com alça"""
        
        # Preço de entrada: break acima da resistência da alça
        entry_price = handle_data['high_price'] * 1.01  # 1% acima da alça
        
        # Target: altura da xícara projetada
        cup_height = cup_data['start_price'] - cup_data['lowest_price']
        target_price = entry_price + cup_height
        
        # Stop loss: abaixo da alça
        stop_loss = handle_data['low_price'] * 0.98
        
        key_points = [
            {'type': 'cup_start', 'index': cup_data['start_idx'], 'price': cup_data['start_price']},
            {'type': 'cup_bottom', 'index': cup_data['lowest_idx'], 'price': cup_data['lowest_price']},
            {'type': 'cup_end', 'index': cup_data['end_idx'], 'price': cup_data['end_price']},
            {'type': 'handle_start', 'index': handle_data['start_idx'], 'price': handle_data['high_price']},
            {'type': 'handle_end', 'index': handle_data['end_idx'], 'price': handle_data['low_price']}
        ]
        
        # Força baseada na qualidade da formação
        depth_score = min(1.0, cup_data['depth'] / 0.3)  # Depth ideal ~30%
        duration_score = min(1.0, cup_data['duration'] / 50)  # Duração ideal ~50 barras
        handle_score = 1 - handle_data['retrace']  # Alça menor é melhor
        
        strength = (depth_score + duration_score + handle_score) / 3
        
        return PatternResult(
            pattern_name="Cup and Handle",
            pattern_type="bullish",
            confidence=0.8,  # Padrão muito confiável
            strength=strength,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            key_points=key_points,
            formation_data={
                'cup_depth': cup_data['depth'],
                'cup_duration': cup_data['duration'],
                'handle_retrace': handle_data['retrace'],
                'handle_duration': handle_data['duration'],
                'total_duration': handle_data['end_idx'] - cup_data['start_idx']
            }
        )

class PatternAnalyzer:
    """Analisador principal de padrões gráficos"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.hs_detector = HeadAndShouldersDetector()
        self.double_detector = DoubleTopBottomDetector()
        self.cup_detector = CupAndHandleDetector()
    
    def analyze_all_patterns(self, market_data: MarketData) -> List[PatternResult]:
        """Executa todos os detectores de padrões"""
        all_patterns = []
        
        try:
            # Head and Shoulders (OHO/OCO)
            hs_patterns = self.hs_detector.detect_head_and_shoulders(market_data)
            all_patterns.extend(hs_patterns)
            
            # Double Top/Bottom
            double_patterns = self.double_detector.detect_double_patterns(market_data)
            all_patterns.extend(double_patterns)
            
            # Cup and Handle
            cup_patterns = self.cup_detector.detect_cup_and_handle(market_data)
            all_patterns.extend(cup_patterns)
            
            # Filtra por força mínima e limita quantidade
            quality_patterns = [
                p for p in all_patterns 
                if p.strength >= settings.patterns.min_pattern_strength
            ]
            
            # Ordena por confiança * força e pega os melhores
            quality_patterns.sort(key=lambda x: x.confidence * x.strength, reverse=True)
            final_patterns = quality_patterns[:settings.patterns.max_patterns_per_analysis]
            
            self.logger.info(
                f"Padrões detectados para {market_data.symbol}: "
                f"OHO/OCO={len(hs_patterns)}, Duplos={len(double_patterns)}, "
                f"Cup&Handle={len(cup_patterns)} → {len(final_patterns)} selecionados"
            )
            
        except Exception as e:
            self.logger.error(f"Erro na análise de padrões para {market_data.symbol}: {e}")
            return []
        
        return final_patterns
    
    def generate_pattern_signals(self, market_data: MarketData, patterns: List[PatternResult]) -> List[TradingSignal]:
        """Gera sinais de trading baseados nos padrões detectados"""
        signals = []
        
        for pattern in patterns:
            # Só gera sinais para padrões com confiança suficiente
            if pattern.confidence >= settings.analysis.confidence_threshold:
                
                signal_type = 'BUY' if pattern.pattern_type == 'bullish' else 'SELL'
                
                trading_signal = TradingSignal(
                    symbol=market_data.symbol,
                    signal_type=signal_type,
                    strategy=f"PATTERN_{pattern.pattern_name.replace(' ', '_')}",
                    confidence=pattern.confidence,
                    strength=pattern.strength,
                    entry_price=pattern.entry_price,
                    stop_loss=pattern.stop_loss,
                    take_profit=pattern.target_price,
                    target_timeframe=market_data.timeframe,
                    pattern_data=pattern.formation_data,
                    notes=f"Padrão {pattern.pattern_name} detectado"
                )
                
                signals.append(trading_signal)
        
        return signals