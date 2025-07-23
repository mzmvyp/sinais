# advanced_technical.py - BANDAS DE BOLLINGER + VWAP COMO FILTROS DE CONFIRMAÇÃO

"""
Indicadores Avançados para Filtros de Confirmação
- Bandas de Bollinger: Filtro de volatilidade para candlesticks
- VWAP: Referência dinâmica para sinais técnicos
- Sistema de confluência para aumentar confidence dos sinais
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass
from datetime import datetime

@dataclass
class BollingerBandsResult:
    """Resultado das Bandas de Bollinger"""
    upper_band: pd.Series
    middle_band: pd.Series  # SMA
    lower_band: pd.Series
    bb_width: pd.Series     # Largura das bandas (volatilidade)
    bb_squeeze: bool        # Indica se as bandas estão contraídas
    current_position: str   # 'above_upper', 'above_middle', 'below_middle', 'below_lower'
    price_to_upper_pct: float  # Distância percentual até banda superior
    price_to_lower_pct: float  # Distância percentual até banda inferior

@dataclass
class VWAPResult:
    """Resultado do VWAP"""
    vwap: pd.Series
    vwap_bands: Dict[str, pd.Series]  # Bandas de desvio do VWAP
    current_position: str  # 'above', 'below', 'at'
    distance_pct: float    # Distância percentual do preço ao VWAP
    volume_profile: str    # 'high_volume', 'low_volume', 'average_volume'
    trend_bias: str        # 'bullish', 'bearish', 'neutral'

@dataclass
class ConfluenceAnalysis:
    """Análise de confluência entre indicadores"""
    bollinger_signal: str      # 'bullish_extreme', 'bearish_extreme', 'neutral'
    vwap_signal: str          # 'bullish_support', 'bearish_resistance', 'neutral'
    confluence_score: float   # 0.0 a 1.0 - quanto maior, mais forte a confluência
    confidence_boost: float   # Multiplicador para aumentar confidence (1.0-2.0)
    confluence_description: str

class BollingerBandsAnalyzer:
    """Analisador de Bandas de Bollinger como filtro de confirmação"""
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.logger = logging.getLogger(__name__)
        self.period = period
        self.std_dev = std_dev
        
        # Configurações para detectar extremos
        self.extreme_threshold = 0.95  # 95% da largura da banda
        self.squeeze_threshold = 0.1   # 10% da média histórica = squeeze
        
    def calculate_bollinger_bands(self, prices: pd.Series) -> BollingerBandsResult:
        """
        🎯 CALCULA BANDAS DE BOLLINGER COMPLETAS
        """
        try:
            if len(prices) < self.period + 5:
                return self._create_empty_bb_result()
            
            # 1. Calcula SMA (banda do meio)
            middle_band = prices.rolling(window=self.period).mean()
            
            # 2. Calcula desvio padrão
            std = prices.rolling(window=self.period).std()
            
            # 3. Calcula bandas superior e inferior
            upper_band = middle_band + (std * self.std_dev)
            lower_band = middle_band - (std * self.std_dev)
            
            # 4. Calcula largura das bandas (indicador de volatilidade)
            bb_width = (upper_band - lower_band) / middle_band
            
            # 5. Detecta squeeze (bandas contraídas)
            avg_width = bb_width.rolling(window=50).mean()
            current_width = bb_width.iloc[-1]
            bb_squeeze = current_width < (avg_width.iloc[-1] * self.squeeze_threshold) if pd.notna(avg_width.iloc[-1]) else False
            
            # 6. Analisa posição atual do preço
            current_price = prices.iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_middle = middle_band.iloc[-1]
            current_lower = lower_band.iloc[-1]
            
            # Determina posição
            if current_price > current_upper:
                position = 'above_upper'
            elif current_price > current_middle:
                position = 'above_middle'
            elif current_price > current_lower:
                position = 'below_middle'
            else:
                position = 'below_lower'
            
            # 7. Calcula distâncias percentuais
            price_to_upper_pct = ((current_upper - current_price) / current_price) * 100
            price_to_lower_pct = ((current_price - current_lower) / current_price) * 100
            
            return BollingerBandsResult(
                upper_band=upper_band,
                middle_band=middle_band,
                lower_band=lower_band,
                bb_width=bb_width,
                bb_squeeze=bb_squeeze,
                current_position=position,
                price_to_upper_pct=price_to_upper_pct,
                price_to_lower_pct=price_to_lower_pct
            )
            
        except Exception as e:
            self.logger.error(f"Erro no cálculo das Bandas de Bollinger: {e}")
            return self._create_empty_bb_result()
    
    def _create_empty_bb_result(self) -> BollingerBandsResult:
        """Resultado vazio em caso de erro"""
        empty_series = pd.Series(dtype=float)
        return BollingerBandsResult(
            upper_band=empty_series,
            middle_band=empty_series,
            lower_band=empty_series,
            bb_width=empty_series,
            bb_squeeze=False,
            current_position='neutral',
            price_to_upper_pct=0.0,
            price_to_lower_pct=0.0
        )

class VWAPAnalyzer:
    """Analisador de VWAP como referência dinâmica"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Configurações para bandas de desvio do VWAP
        self.vwap_bands_multipliers = [0.5, 1.0, 1.5, 2.0]  # Múltiplos do desvio padrão
        
    def calculate_vwap(self, df: pd.DataFrame, reset_daily: bool = False) -> VWAPResult:
        """
        🎯 CALCULA VWAP COMPLETO COM BANDAS E ANÁLISE
        """
        try:
            if len(df) < 10:
                return self._create_empty_vwap_result()
            
            # 1. Calcula VWAP básico
            typical_price = (df['high_price'] + df['low_price'] + df['close_price']) / 3
            volume = df['volume']
            
            if reset_daily:
                # VWAP que reseta diariamente (para timeframes baixos)
                vwap = self._calculate_daily_vwap(typical_price, volume, df.index)
            else:
                # VWAP cumulativo (para análise intraday)
                vwap = self._calculate_cumulative_vwap(typical_price, volume)
            
            # 2. Calcula bandas de desvio do VWAP
            vwap_bands = self._calculate_vwap_bands(typical_price, volume, vwap)
            
            # 3. Analisa posição atual
            current_price = df['close_price'].iloc[-1]
            current_vwap = vwap.iloc[-1]
            current_volume = volume.iloc[-1]
            
            # Posição relativa ao VWAP
            if current_price > current_vwap * 1.002:  # 0.2% acima
                position = 'above'
                distance_pct = ((current_price - current_vwap) / current_vwap) * 100
            elif current_price < current_vwap * 0.998:  # 0.2% abaixo
                position = 'below'
                distance_pct = ((current_vwap - current_price) / current_vwap) * 100
            else:
                position = 'at'
                distance_pct = 0.0
            
            # 4. Analisa perfil de volume
            avg_volume = volume.rolling(window=20).mean().iloc[-1]
            if current_volume > avg_volume * 1.5:
                volume_profile = 'high_volume'
            elif current_volume < avg_volume * 0.7:
                volume_profile = 'low_volume'
            else:
                volume_profile = 'average_volume'
            
            # 5. Determina bias de tendência baseado no VWAP
            vwap_slope = self._calculate_vwap_slope(vwap)
            if vwap_slope > 0.001:
                trend_bias = 'bullish'
            elif vwap_slope < -0.001:
                trend_bias = 'bearish'
            else:
                trend_bias = 'neutral'
            
            return VWAPResult(
                vwap=vwap,
                vwap_bands=vwap_bands,
                current_position=position,
                distance_pct=distance_pct,
                volume_profile=volume_profile,
                trend_bias=trend_bias
            )
            
        except Exception as e:
            self.logger.error(f"Erro no cálculo do VWAP: {e}")
            return self._create_empty_vwap_result()
    
    def _calculate_cumulative_vwap(self, typical_price: pd.Series, volume: pd.Series) -> pd.Series:
        """Calcula VWAP cumulativo"""
        pv = typical_price * volume
        cumulative_pv = pv.expanding().sum()
        cumulative_volume = volume.expanding().sum()
        
        # Evita divisão por zero
        vwap = cumulative_pv / (cumulative_volume + 1e-10)
        return vwap
    
    def _calculate_daily_vwap(self, typical_price: pd.Series, volume: pd.Series, index) -> pd.Series:
        """Calcula VWAP que reseta diariamente"""
        # Para simplificar, usa VWAP de janela móvel de 100 períodos
        window = min(100, len(typical_price))
        pv = typical_price * volume
        
        rolling_pv = pv.rolling(window=window).sum()
        rolling_volume = volume.rolling(window=window).sum()
        
        vwap = rolling_pv / (rolling_volume + 1e-10)
        return vwap
    
    def _calculate_vwap_bands(self, typical_price: pd.Series, volume: pd.Series, vwap: pd.Series) -> Dict[str, pd.Series]:
        """Calcula bandas de desvio do VWAP"""
        bands = {}
        
        # Calcula desvio padrão ponderado por volume
        price_variance = ((typical_price - vwap) ** 2) * volume
        cumulative_variance = price_variance.expanding().sum()
        cumulative_volume = volume.expanding().sum()
        
        vwap_std = np.sqrt(cumulative_variance / (cumulative_volume + 1e-10))
        
        # Cria bandas
        for multiplier in self.vwap_bands_multipliers:
            bands[f'upper_{multiplier}'] = vwap + (vwap_std * multiplier)
            bands[f'lower_{multiplier}'] = vwap - (vwap_std * multiplier)
        
        return bands
    
    def _calculate_vwap_slope(self, vwap: pd.Series) -> float:
        """Calcula inclinação do VWAP (tendência)"""
        if len(vwap) < 10:
            return 0.0
        
        recent_vwap = vwap.tail(10)
        x = np.arange(len(recent_vwap))
        
        # Regressão linear simples
        slope = np.polyfit(x, recent_vwap, 1)[0]
        
        # Normaliza pela magnitude do preço
        normalized_slope = slope / recent_vwap.iloc[-1] if recent_vwap.iloc[-1] != 0 else 0.0
        
        return normalized_slope
    
    def _create_empty_vwap_result(self) -> VWAPResult:
        """Resultado vazio em caso de erro"""
        empty_series = pd.Series(dtype=float)
        return VWAPResult(
            vwap=empty_series,
            vwap_bands={},
            current_position='neutral',
            distance_pct=0.0,
            volume_profile='unknown',
            trend_bias='neutral'
        )

class ConfluenceAnalyzer:
    """Analisador de confluência entre Bollinger Bands, VWAP e sinais"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_confluence(self, signal_type: str, bb_result: BollingerBandsResult, 
                         vwap_result: VWAPResult, detector_name: str) -> ConfluenceAnalysis:
        """
        🎯 ANÁLISE DE CONFLUÊNCIA PRINCIPAL
        Determina se Bollinger + VWAP confirmam o sinal
        """
        try:
            # 1. ANÁLISE BOLLINGER - Extremos são OURO para confirmação
            bollinger_signal = self._analyze_bollinger_confluence(signal_type, bb_result)
            
            # 2. ANÁLISE VWAP - Suporte/Resistência dinâmico
            vwap_signal = self._analyze_vwap_confluence(signal_type, vwap_result)
            
            # 3. ANÁLISE ESPECÍFICA POR TIPO DE DETECTOR
            detector_bonus = self._get_detector_specific_bonus(detector_name, bollinger_signal, vwap_signal)
            
            # 4. CÁLCULO DO SCORE DE CONFLUÊNCIA
            confluence_score = self._calculate_confluence_score(
                bollinger_signal, vwap_signal, detector_bonus
            )
            
            # 5. MULTIPLICADOR DE CONFIDENCE
            confidence_boost = self._calculate_confidence_boost(confluence_score)
            
            # 6. DESCRIÇÃO DA CONFLUÊNCIA
            description = self._generate_confluence_description(
                bollinger_signal, vwap_signal, detector_bonus, signal_type
            )
            
            return ConfluenceAnalysis(
                bollinger_signal=bollinger_signal,
                vwap_signal=vwap_signal,
                confluence_score=confluence_score,
                confidence_boost=confidence_boost,
                confluence_description=description
            )
            
        except Exception as e:
            self.logger.error(f"Erro na análise de confluência: {e}")
            return self._create_neutral_confluence()
    
    def _analyze_bollinger_confluence(self, signal_type: str, bb_result: BollingerBandsResult) -> str:
        """Analisa confluência com Bandas de Bollinger"""
        
        # BULLISH SIGNALS - Procura por extremos de oversold
        if 'BUY' in signal_type:
            if bb_result.current_position == 'below_lower':
                return 'bullish_extreme'  # OURO! Preço abaixo da banda inferior
            elif bb_result.current_position == 'below_middle' and bb_result.price_to_lower_pct < 2.0:
                return 'bullish_moderate'  # Muito próximo da banda inferior
            elif bb_result.bb_squeeze:
                return 'bullish_squeeze'  # Squeeze indica possível breakout
            else:
                return 'neutral'
        
        # BEARISH SIGNALS - Procura por extremos de overbought
        elif 'SELL' in signal_type:
            if bb_result.current_position == 'above_upper':
                return 'bearish_extreme'  # OURO! Preço acima da banda superior
            elif bb_result.current_position == 'above_middle' and bb_result.price_to_upper_pct < 2.0:
                return 'bearish_moderate'  # Muito próximo da banda superior
            elif bb_result.bb_squeeze:
                return 'bearish_squeeze'  # Squeeze indica possível breakout
            else:
                return 'neutral'
        
        return 'neutral'
    
    def _analyze_vwap_confluence(self, signal_type: str, vwap_result: VWAPResult) -> str:
        """Analisa confluência com VWAP"""
        
        # BULLISH SIGNALS - VWAP como suporte
        if 'BUY' in signal_type:
            if vwap_result.current_position == 'above' and vwap_result.distance_pct < 1.0:
                return 'bullish_support'  # Preço ligeiramente acima do VWAP (suporte confirmado)
            elif vwap_result.current_position == 'at':
                return 'bullish_support'  # Preço exatamente no VWAP (teste de suporte)
            elif vwap_result.trend_bias == 'bullish' and vwap_result.volume_profile == 'high_volume':
                return 'bullish_momentum'  # VWAP subindo com volume alto
            else:
                return 'neutral'
        
        # BEARISH SIGNALS - VWAP como resistência
        elif 'SELL' in signal_type:
            if vwap_result.current_position == 'below' and vwap_result.distance_pct < 1.0:
                return 'bearish_resistance'  # Preço ligeiramente abaixo do VWAP (resistência confirmada)
            elif vwap_result.current_position == 'at':
                return 'bearish_resistance'  # Preço exatamente no VWAP (teste de resistência)
            elif vwap_result.trend_bias == 'bearish' and vwap_result.volume_profile == 'high_volume':
                return 'bearish_momentum'  # VWAP descendo com volume alto
            else:
                return 'neutral'
        
        return 'neutral'
    
    def _get_detector_specific_bonus(self, detector_name: str, bollinger_signal: str, vwap_signal: str) -> float:
        """Bonus específico para cada tipo de detector"""
        
        # CANDLESTICK PATTERNS - São PERFEITOS com Bollinger extremos
        if any(pattern in detector_name for pattern in ['Engulfing', 'Hammer', 'Shooting_Star', 'Doji']):
            if 'extreme' in bollinger_signal:
                return 0.3  # 30% de bonus para candlesticks em extremos de Bollinger
            elif 'moderate' in bollinger_signal:
                return 0.15  # 15% de bonus para candlesticks próximos dos extremos
        
        # RSI - Combina bem com Bollinger
        elif detector_name == 'RSI':
            if 'extreme' in bollinger_signal:
                return 0.25  # RSI + Bollinger extremo = confluência forte
        
        # MACD - Combina bem com VWAP
        elif detector_name == 'MACD':
            if 'support' in vwap_signal or 'resistance' in vwap_signal:
                return 0.20  # MACD + VWAP como S/R = boa confluência
        
        # DOUBLE PATTERNS - Funcionam bem com ambos
        elif 'Double' in detector_name:
            if 'extreme' in bollinger_signal and ('support' in vwap_signal or 'resistance' in vwap_signal):
                return 0.25  # Double pattern + ambos confirmando = excelente
        
        return 0.0
    
    def _calculate_confluence_score(self, bollinger_signal: str, vwap_signal: str, detector_bonus: float) -> float:
        """Calcula score de confluência (0.0 a 1.0)"""
        
        score = 0.0
        
        # BOLLINGER SCORING
        if 'extreme' in bollinger_signal:
            score += 0.4  # Extremos de Bollinger valem muito
        elif 'moderate' in bollinger_signal:
            score += 0.25
        elif 'squeeze' in bollinger_signal:
            score += 0.15
        
        # VWAP SCORING  
        if 'support' in vwap_signal or 'resistance' in vwap_signal:
            score += 0.3  # VWAP como S/R vale muito
        elif 'momentum' in vwap_signal:
            score += 0.2
        
        # DETECTOR BONUS
        score += detector_bonus
        
        # Normaliza para 0-1
        return min(1.0, score)
    
    def _calculate_confidence_boost(self, confluence_score: float) -> float:
        """Calcula multiplicador de confidence baseado na confluência"""
        
        if confluence_score >= 0.8:
            return 1.5  # 50% de aumento na confidence
        elif confluence_score >= 0.6:
            return 1.3  # 30% de aumento
        elif confluence_score >= 0.4:
            return 1.15  # 15% de aumento
        elif confluence_score >= 0.2:
            return 1.05  # 5% de aumento
        else:
            return 1.0  # Sem alteração
    
    def _generate_confluence_description(self, bollinger_signal: str, vwap_signal: str, 
                                       detector_bonus: float, signal_type: str) -> str:
        """Gera descrição detalhada da confluência"""
        
        descriptions = []
        
        # Bollinger descriptions
        if bollinger_signal == 'bullish_extreme':
            descriptions.append("🎯 PREÇO ABAIXO DA BANDA INFERIOR - Oversold extremo")
        elif bollinger_signal == 'bearish_extreme':
            descriptions.append("🎯 PREÇO ACIMA DA BANDA SUPERIOR - Overbought extremo")
        elif 'moderate' in bollinger_signal:
            descriptions.append("📊 Próximo aos extremos de Bollinger")
        elif 'squeeze' in bollinger_signal:
            descriptions.append("🔒 Bollinger Squeeze - Breakout iminente")
        
        # VWAP descriptions
        if vwap_signal == 'bullish_support':
            descriptions.append("💪 VWAP atuando como SUPORTE")
        elif vwap_signal == 'bearish_resistance':
            descriptions.append("🚧 VWAP atuando como RESISTÊNCIA")
        elif 'momentum' in vwap_signal:
            descriptions.append("🚀 VWAP confirmando momentum")
        
        # Detector bonus
        if detector_bonus > 0.2:
            descriptions.append("⭐ CONFLUÊNCIA PERFEITA para este tipo de sinal")
        elif detector_bonus > 0.1:
            descriptions.append("✅ Boa confluência com indicadores")
        
        if not descriptions:
            return "Confluência neutra"
        
        return " | ".join(descriptions)
    
    def _create_neutral_confluence(self) -> ConfluenceAnalysis:
        """Confluência neutra em caso de erro"""
        return ConfluenceAnalysis(
            bollinger_signal='neutral',
            vwap_signal='neutral',
            confluence_score=0.0,
            confidence_boost=1.0,
            confluence_description='Confluência neutra'
        )

# Integração com o sistema existente
class AdvancedTechnicalAnalyzer:
    """Analisador principal que integra Bollinger + VWAP + Confluência"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.bollinger_analyzer = BollingerBandsAnalyzer()
        self.vwap_analyzer = VWAPAnalyzer()
        self.confluence_analyzer = ConfluenceAnalyzer()
        
        self.logger.info("🎯 AdvancedTechnicalAnalyzer inicializado - Bollinger + VWAP")
    
    def analyze_confluence_for_signal(self, signal_dict: Dict, market_data) -> Dict:
        """
        🚀 FUNÇÃO PRINCIPAL - Analisa confluência para um sinal
        
        Retorna o sinal original com confidence ajustada pela confluência
        """
        try:
            # 1. Calcula Bollinger Bands
            bb_result = self.bollinger_analyzer.calculate_bollinger_bands(
                market_data.data['close_price']
            )
            
            # 2. Calcula VWAP
            vwap_result = self.vwap_analyzer.calculate_vwap(market_data.data)
            
            # 3. Analisa confluência
            confluence = self.confluence_analyzer.analyze_confluence(
                signal_dict['signal_type'],
                bb_result,
                vwap_result,
                signal_dict.get('detector_name', 'unknown')
            )
            
            # 4. Ajusta confidence do sinal
            original_confidence = signal_dict.get('confidence', 0.7)
            boosted_confidence = min(0.98, original_confidence * confluence.confidence_boost)
            
            # 5. Adiciona dados de confluência ao sinal
            enhanced_signal = signal_dict.copy()
            enhanced_signal['confidence'] = boosted_confidence
            enhanced_signal['confluence_data'] = {
                'original_confidence': original_confidence,
                'confluence_score': confluence.confluence_score,
                'confidence_boost': confluence.confidence_boost,
                'bollinger_signal': confluence.bollinger_signal,
                'vwap_signal': confluence.vwap_signal,
                'description': confluence.confluence_description,
                'bollinger_position': bb_result.current_position,
                'vwap_position': vwap_result.current_position,
                'vwap_trend': vwap_result.trend_bias
            }
            
            # 6. Log da confluência
            if confluence.confidence_boost > 1.1:  # Apenas se houve boost significativo
                self.logger.info(
                    f"🎯 CONFLUÊNCIA DETECTADA: {signal_dict.get('detector_name', 'unknown')} | "
                    f"Confidence: {original_confidence:.3f} → {boosted_confidence:.3f} "
                    f"(+{((confluence.confidence_boost - 1) * 100):.0f}%) | "
                    f"Score: {confluence.confluence_score:.2f} | "
                    f"{confluence.confluence_description}"
                )
            
            return enhanced_signal
            
        except Exception as e:
            self.logger.error(f"Erro na análise de confluência: {e}")
            return signal_dict  # Retorna sinal original sem modificação
    
    def get_market_context(self, market_data) -> Dict:
        """Retorna contexto do mercado (Bollinger + VWAP) para logging/debug"""
        try:
            bb_result = self.bollinger_analyzer.calculate_bollinger_bands(
                market_data.data['close_price']
            )
            vwap_result = self.vwap_analyzer.calculate_vwap(market_data.data)
            
            return {
                'bollinger_position': bb_result.current_position,
                'bollinger_squeeze': bb_result.bb_squeeze,
                'vwap_position': vwap_result.current_position,
                'vwap_trend': vwap_result.trend_bias,
                'vwap_distance_pct': vwap_result.distance_pct,
                'volume_profile': vwap_result.volume_profile
            }
        except Exception as e:
            self.logger.error(f"Erro ao obter contexto do mercado: {e}")
            return {}

# Funções de conveniência para integração
def create_advanced_technical_analyzer():
    """Factory function para criar o analisador avançado"""
    return AdvancedTechnicalAnalyzer()

def analyze_signal_confluence(signal_dict: Dict, market_data, analyzer: AdvancedTechnicalAnalyzer = None) -> Dict:
    """Função standalone para analisar confluência de um sinal"""
    if analyzer is None:
        analyzer = AdvancedTechnicalAnalyzer()
    
    return analyzer.analyze_confluence_for_signal(signal_dict, market_data)

# Exemplo de uso
if __name__ == "__main__":
    # Teste do sistema
    import pandas as pd
    
    # Simula dados de mercado
    dates = pd.date_range('2024-01-01', periods=100, freq='5T')
    prices = np.random.randn(100).cumsum() + 100
    volumes = np.random.randint(1000, 10000, 100)
    
    test_data = pd.DataFrame({
        'high_price': prices + np.random.rand(100),
        'low_price': prices - np.random.rand(100),
        'close_price': prices,
        'volume': volumes
    }, index=dates)
    
    class MockMarketData:
        def __init__(self, data):
            self.data = data
    
    # Testa o sistema
    market_data = MockMarketData(test_data)
    analyzer = AdvancedTechnicalAnalyzer()
    
    # Simula um sinal de candlestick
    test_signal = {
        'detector_name': 'Bullish_Engulfing',
        'signal_type': 'BUY_LONG',
        'confidence': 0.75
    }
    
    # Analisa confluência
    enhanced_signal = analyzer.analyze_confluence_for_signal(test_signal, market_data)
    
    print("\n🧪 TESTE DO SISTEMA DE CONFLUÊNCIA")
    print("=" * 50)
    print(f"Confidence original: {test_signal['confidence']:.3f}")
    print(f"Confidence com confluência: {enhanced_signal['confidence']:.3f}")
    print(f"Boost aplicado: {enhanced_signal['confluence_data']['confidence_boost']:.2f}x")
    print(f"Score de confluência: {enhanced_signal['confluence_data']['confluence_score']:.2f}")
    print(f"Descrição: {enhanced_signal['confluence_data']['description']}")
    
    # Testa contexto do mercado
    context = analyzer.get_market_context(market_data)
    print(f"\n📊 CONTEXTO DO MERCADO:")
    for key, value in context.items():
        print(f"  • {key}: {value}")