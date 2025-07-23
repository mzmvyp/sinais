# enhanced_volume_validator.py - SISTEMA APRIMORADO DE VALIDAÇÃO DE VOLUME

"""
Sistema Inteligente de Validação de Volume
- Validação rigorosa baseada em múltiplos fatores
- Ajuste dinâmico por volatilidade
- Diferentes thresholds por condição de mercado
- Configurações granulares por symbol/timeframe
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class VolumeAnalysis:
    """Resultado da análise de volume"""
    volume_ratio: float
    volume_trend: str  # 'increasing', 'decreasing', 'stable'
    volatility_factor: float
    market_condition: str  # 'high_vol', 'normal', 'low_vol'
    threshold_used: float
    validation_passed: bool
    confidence_score: float
    analysis_details: Dict

class EnhancedVolumeValidator:
    """Validador inteligente de volume com múltiplos fatores"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Configurações avançadas de volume
        self.config = {
            'base_thresholds': {
                '5m': 1.5,   # Threshold base para 5m
                '15m': 1.3,  # Threshold base para 15m
                '1h': 1.2    # Threshold base para 1h
            },
            'volatility_adjustments': {
                'high_volatility': {
                    'multiplier': 1.4,  # Volume deve ser 40% maior em alta volatilidade
                    'min_threshold': 1.8,
                    'description': 'Alta volatilidade requer volume mais significativo'
                },
                'normal_volatility': {
                    'multiplier': 1.0,  # Volume normal
                    'min_threshold': 1.2,
                    'description': 'Volatilidade normal'
                },
                'low_volatility': {
                    'multiplier': 0.85,  # Aceita volume menor em baixa volatilidade
                    'min_threshold': 1.0,
                    'description': 'Baixa volatilidade permite volume menor'
                }
            },
            'trend_adjustments': {
                'volume_increasing': 0.9,   # Bonus se volume está crescendo
                'volume_stable': 1.0,       # Volume estável
                'volume_decreasing': 1.2    # Penaliza se volume está caindo
            },
            'symbol_specific': {
                # Cryptocurrencies com maior liquidez podem ter thresholds diferentes
                'BTC': {'multiplier': 0.9, 'description': 'BTC tem alta liquidez'},
                'ETH': {'multiplier': 0.95, 'description': 'ETH tem boa liquidez'},
                'BNB': {'multiplier': 1.0, 'description': 'BNB liquidez padrão'},
                # Altcoins menores precisam de mais volume
                'PEPE': {'multiplier': 1.3, 'description': 'Memecoin precisa volume alto'},
                'TURBO': {'multiplier': 1.3, 'description': 'Memecoin precisa volume alto'},
                'HYPE': {'multiplier': 1.2, 'description': 'Token menor precisa mais volume'}
            },
            'signal_type_adjustments': {
                'BUY_LONG': 1.0,     # Volume normal para compra
                'SELL_SHORT': 1.1    # Volume ligeiramente maior para venda
            },
            'confidence_factors': {
                'volume_spike': 1.5,      # Multiplicador quando há spike de volume
                'volume_confirmation': 1.2, # Quando volume confirma movimento
                'volume_divergence': 0.7   # Quando volume diverge do preço
            }
        }
        
        self.logger.info("🔊 Enhanced Volume Validator inicializado")
    
    def validate_volume_intelligent(self, market_data, signal_type: str, 
                                  symbol: str, timeframe: str) -> VolumeAnalysis:
        """
        🎯 VALIDAÇÃO INTELIGENTE DE VOLUME COM MÚLTIPLOS FATORES
        """
        try:
            df = market_data.data
            
            if len(df) < 20:
                return self._create_fallback_analysis("Dados insuficientes")
            
            # 1. ANÁLISE BÁSICA DE VOLUME
            volume_analysis = self._analyze_volume_metrics(df)
            
            # 2. ANÁLISE DE VOLATILIDADE
            volatility_analysis = self._analyze_volatility(df)
            
            # 3. ANÁLISE DE TENDÊNCIA DO VOLUME
            volume_trend = self._analyze_volume_trend(df)
            
            # 4. CÁLCULO DO THRESHOLD DINÂMICO
            dynamic_threshold = self._calculate_dynamic_threshold(
                symbol, timeframe, signal_type, volatility_analysis, volume_trend
            )
            
            # 5. ANÁLISE DE CONFIRMAÇÃO/DIVERGÊNCIA
            price_volume_relation = self._analyze_price_volume_relation(df)
            
            # 6. CÁLCULO DA PONTUAÇÃO DE CONFIANÇA
            confidence_score = self._calculate_volume_confidence(
                volume_analysis, volatility_analysis, volume_trend, 
                price_volume_relation, dynamic_threshold
            )
            
            # 7. DECISÃO FINAL
            validation_passed = (
                volume_analysis['volume_ratio'] >= dynamic_threshold and
                confidence_score >= 0.6  # Mínimo de 60% de confiança
            )
            
            return VolumeAnalysis(
                volume_ratio=volume_analysis['volume_ratio'],
                volume_trend=volume_trend['trend'],
                volatility_factor=volatility_analysis['factor'],
                market_condition=volatility_analysis['condition'],
                threshold_used=dynamic_threshold,
                validation_passed=validation_passed,
                confidence_score=confidence_score,
                analysis_details={
                    'base_analysis': volume_analysis,
                    'volatility_analysis': volatility_analysis,
                    'trend_analysis': volume_trend,
                    'price_volume_relation': price_volume_relation,
                    'adjustments_applied': self._get_applied_adjustments(symbol, timeframe, signal_type)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Erro na validação inteligente de volume: {e}")
            return self._create_fallback_analysis(f"Erro: {e}")
    
    def _analyze_volume_metrics(self, df: pd.DataFrame) -> Dict:
        """Análise básica das métricas de volume"""
        
        # Usa últimas 20 barras para média (excluindo a barra atual)
        volume_data = df['volume'].iloc[:-1]  # Remove barra atual
        signal_volume = df['volume'].iloc[-2]  # Volume da barra do sinal (fechada)
        
        # Calcula diferentes médias
        vol_ma_20 = volume_data.tail(20).mean()
        vol_ma_10 = volume_data.tail(10).mean()
        vol_ma_5 = volume_data.tail(5).mean()
        
        # Volume ratio principal
        volume_ratio = signal_volume / vol_ma_20 if vol_ma_20 > 0 else 0
        
        # Métricas adicionais
        volume_percentile = self._calculate_volume_percentile(signal_volume, volume_data.tail(50))
        
        # Detecta spikes de volume
        volume_spike = signal_volume > vol_ma_20 * 2.0
        
        return {
            'volume_ratio': volume_ratio,
            'signal_volume': signal_volume,
            'vol_ma_20': vol_ma_20,
            'vol_ma_10': vol_ma_10,
            'vol_ma_5': vol_ma_5,
            'volume_percentile': volume_percentile,
            'volume_spike': volume_spike,
            'relative_to_recent': signal_volume / vol_ma_5 if vol_ma_5 > 0 else 0
        }
    
    def _analyze_volatility(self, df: pd.DataFrame) -> Dict:
        """Análise da volatilidade do mercado"""
        
        # Calcula volatilidade baseada em ATR
        recent_data = df.tail(20)
        
        # True Range
        high_low = recent_data['high_price'] - recent_data['low_price']
        high_prev_close = abs(recent_data['high_price'] - recent_data['close_price'].shift())
        low_prev_close = abs(recent_data['low_price'] - recent_data['close_price'].shift())
        
        true_range = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
        atr = true_range.mean()
        
        # Volatilidade relativa
        current_price = df['close_price'].iloc[-1]
        volatility_pct = (atr / current_price) * 100
        
        # Classifica volatilidade
        if volatility_pct > 3.0:
            condition = 'high_volatility'
            factor = 1.4
        elif volatility_pct < 1.0:
            condition = 'low_volatility'
            factor = 0.8
        else:
            condition = 'normal_volatility'
            factor = 1.0
        
        return {
            'atr': atr,
            'volatility_pct': volatility_pct,
            'condition': condition,
            'factor': factor,
            'description': self.config['volatility_adjustments'][condition]['description']
        }
    
    def _analyze_volume_trend(self, df: pd.DataFrame) -> Dict:
        """Análise da tendência do volume"""
        
        # Compara volumes recentes
        vol_recent = df['volume'].tail(5).mean()  # Últimas 5 barras
        vol_older = df['volume'].tail(15).head(10).mean()  # 10 barras anteriores
        
        if vol_recent > vol_older * 1.15:
            trend = 'increasing'
            factor = self.config['trend_adjustments']['volume_increasing']
        elif vol_recent < vol_older * 0.85:
            trend = 'decreasing'
            factor = self.config['trend_adjustments']['volume_decreasing']
        else:
            trend = 'stable'
            factor = self.config['trend_adjustments']['volume_stable']
        
        # Análise de momentum do volume
        volume_momentum = self._calculate_volume_momentum(df['volume'])
        
        return {
            'trend': trend,
            'factor': factor,
            'vol_recent': vol_recent,
            'vol_older': vol_older,
            'momentum': volume_momentum,
            'change_pct': ((vol_recent - vol_older) / vol_older * 100) if vol_older > 0 else 0
        }
    
    def _analyze_price_volume_relation(self, df: pd.DataFrame) -> Dict:
        """Análise da relação preço x volume"""
        
        recent_data = df.tail(10)
        
        # Calcula correlação preço x volume
        price_changes = recent_data['close_price'].pct_change()
        volume_changes = recent_data['volume'].pct_change()
        
        # Remove NaN
        valid_mask = ~(price_changes.isna() | volume_changes.isna())
        price_changes_clean = price_changes[valid_mask]
        volume_changes_clean = volume_changes[valid_mask]
        
        if len(price_changes_clean) > 3:
            correlation = np.corrcoef(price_changes_clean, volume_changes_clean)[0, 1]
            if np.isnan(correlation):
                correlation = 0
        else:
            correlation = 0
        
        # Classificação da relação
        if correlation > 0.3:
            relation = 'confirmation'  # Volume confirma movimento
            factor = self.config['confidence_factors']['volume_confirmation']
        elif correlation < -0.3:
            relation = 'divergence'   # Volume diverge do preço
            factor = self.config['confidence_factors']['volume_divergence']
        else:
            relation = 'neutral'      # Relação neutra
            factor = 1.0
        
        return {
            'correlation': correlation,
            'relation': relation,
            'factor': factor,
            'description': f"Volume {relation} with price movement"
        }
    
    def _calculate_dynamic_threshold(self, symbol: str, timeframe: str, 
                                   signal_type: str, volatility_analysis: Dict, 
                                   volume_trend: Dict) -> float:
        """Calcula threshold dinâmico baseado em múltiplos fatores"""
        
        # 1. Threshold base
        base_threshold = self.config['base_thresholds'].get(timeframe, 1.3)
        
        # 2. Ajuste por volatilidade
        volatility_config = self.config['volatility_adjustments'][volatility_analysis['condition']]
        volatility_multiplier = volatility_config['multiplier']
        min_threshold = volatility_config['min_threshold']
        
        # 3. Ajuste por tendência do volume
        trend_factor = volume_trend['factor']
        
        # 4. Ajuste por symbol específico
        symbol_config = self.config['symbol_specific'].get(symbol, {'multiplier': 1.0})
        symbol_multiplier = symbol_config['multiplier']
        
        # 5. Ajuste por tipo de sinal
        signal_multiplier = self.config['signal_type_adjustments'].get(signal_type, 1.0)
        
        # Cálculo final
        dynamic_threshold = (
            base_threshold * 
            volatility_multiplier * 
            trend_factor * 
            symbol_multiplier * 
            signal_multiplier
        )
        
        # Aplica threshold mínimo
        final_threshold = max(dynamic_threshold, min_threshold)
        
        self.logger.debug(
            f"Threshold dinâmico {symbol} {timeframe}: "
            f"base({base_threshold}) * vol({volatility_multiplier:.2f}) * "
            f"trend({trend_factor:.2f}) * symbol({symbol_multiplier:.2f}) * "
            f"signal({signal_multiplier:.2f}) = {final_threshold:.2f}"
        )
        
        return final_threshold
    
    def _calculate_volume_confidence(self, volume_analysis: Dict, volatility_analysis: Dict,
                                   volume_trend: Dict, price_volume_relation: Dict,
                                   dynamic_threshold: float) -> float:
        """Calcula pontuação de confiança do volume"""
        
        confidence_factors = []
        
        # 1. Fator do volume ratio
        volume_ratio = volume_analysis['volume_ratio']
        if volume_ratio >= dynamic_threshold * 1.5:
            volume_factor = 1.0  # Excelente
        elif volume_ratio >= dynamic_threshold:
            volume_factor = 0.8  # Bom
        elif volume_ratio >= dynamic_threshold * 0.8:
            volume_factor = 0.6  # Aceitável
        else:
            volume_factor = 0.3  # Baixo
        
        confidence_factors.append(('volume_ratio', volume_factor, 0.4))  # Peso 40%
        
        # 2. Fator da volatilidade
        if volatility_analysis['condition'] == 'normal_volatility':
            vol_factor = 1.0
        elif volatility_analysis['condition'] == 'high_volatility':
            vol_factor = 0.8  # Penaliza alta volatilidade
        else:
            vol_factor = 0.9  # Baixa volatilidade é ok
        
        confidence_factors.append(('volatility', vol_factor, 0.2))  # Peso 20%
        
        # 3. Fator da tendência do volume
        if volume_trend['trend'] == 'increasing':
            trend_factor = 1.0
        elif volume_trend['trend'] == 'stable':
            trend_factor = 0.8
        else:
            trend_factor = 0.6  # Volume decrescente é preocupante
        
        confidence_factors.append(('volume_trend', trend_factor, 0.2))  # Peso 20%
        
        # 4. Fator da relação preço-volume
        pv_factor = price_volume_relation['factor']
        normalized_pv_factor = min(1.0, max(0.5, pv_factor))
        
        confidence_factors.append(('price_volume_relation', normalized_pv_factor, 0.2))  # Peso 20%
        
        # 5. Bonus para spikes de volume
        if volume_analysis['volume_spike']:
            confidence_factors.append(('volume_spike', 1.2, 0.1))  # Bonus de 10%
        
        # Cálculo final ponderado
        total_score = 0
        total_weight = 0
        
        for name, score, weight in confidence_factors:
            total_score += score * weight
            total_weight += weight
        
        final_confidence = total_score / total_weight if total_weight > 0 else 0.5
        
        # Garante que fica entre 0 e 1
        final_confidence = max(0.0, min(1.0, final_confidence))
        
        return final_confidence
    
    def _calculate_volume_percentile(self, current_volume: float, historical_volumes: pd.Series) -> float:
        """Calcula percentil do volume atual vs histórico"""
        if len(historical_volumes) == 0:
            return 50.0
        
        rank = (historical_volumes < current_volume).sum()
        percentile = (rank / len(historical_volumes)) * 100
        return percentile
    
    def _calculate_volume_momentum(self, volume_series: pd.Series) -> float:
        """Calcula momentum do volume"""
        if len(volume_series) < 5:
            return 0.0
        
        recent_avg = volume_series.tail(3).mean()
        older_avg = volume_series.tail(10).head(7).mean()
        
        if older_avg > 0:
            momentum = (recent_avg - older_avg) / older_avg
        else:
            momentum = 0.0
        
        return momentum
    
    def _get_applied_adjustments(self, symbol: str, timeframe: str, signal_type: str) -> Dict:
        """Retorna ajustes aplicados para debugging"""
        
        symbol_config = self.config['symbol_specific'].get(symbol, {'multiplier': 1.0, 'description': 'Configuração padrão'})
        
        return {
            'base_threshold': self.config['base_thresholds'].get(timeframe, 1.3),
            'symbol_adjustment': symbol_config,
            'signal_type_adjustment': self.config['signal_type_adjustments'].get(signal_type, 1.0),
            'timeframe': timeframe
        }
    
    def _create_fallback_analysis(self, reason: str) -> VolumeAnalysis:
        """Cria análise de fallback em caso de erro"""
        return VolumeAnalysis(
            volume_ratio=0.0,
            volume_trend='unknown',
            volatility_factor=1.0,
            market_condition='unknown',
            threshold_used=1.5,
            validation_passed=False,
            confidence_score=0.0,
            analysis_details={'error': reason, 'fallback': True}
        )
    
    def format_validation_report(self, analysis: VolumeAnalysis, symbol: str) -> str:
        """Formata relatório de validação para logging"""
        
        status = "✅ APROVADO" if analysis.validation_passed else "❌ REJEITADO"
        
        report = f"""
🔊 VALIDAÇÃO DE VOLUME - {symbol}
{status}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Volume Ratio: {analysis.volume_ratio:.2f} (threshold: {analysis.threshold_used:.2f})
📈 Tendência: {analysis.volume_trend} | Volatilidade: {analysis.market_condition}
🎯 Confiança: {analysis.confidence_score:.1%}
💪 Fator Vol: {analysis.volatility_factor:.2f}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """.strip()
        
        return report

# Integração com o sistema existente
def integrate_enhanced_volume_validation():
    """
    Função para integrar o novo sistema de validação no analyzer.py
    Substitui a função _validate_with_volume_safe existente
    """
    
    enhanced_validator = EnhancedVolumeValidator()
    
    def _validate_with_volume_enhanced(signal, market_data_by_tf) -> Tuple[bool, str]:
        """Nova função de validação de volume aprimorada"""
        try:
            market_data = market_data_by_tf.get(signal.timeframe)
            if not market_data or len(market_data.data) < 20:
                return True, "Dados insuficientes - aprovado por padrão"
            
            # Usa o novo validador
            analysis = enhanced_validator.validate_volume_intelligent(
                market_data, signal.signal_type, signal.symbol, signal.timeframe
            )
            
            # Log detalhado
            if hasattr(enhanced_validator, 'logger'):
                report = enhanced_validator.format_validation_report(analysis, signal.symbol)
                enhanced_validator.logger.debug(report)
            
            # Retorna resultado
            if analysis.validation_passed:
                return True, f"Volume aprovado (ratio: {analysis.volume_ratio:.2f}, conf: {analysis.confidence_score:.1%})"
            else:
                return False, f"Volume insuficiente (ratio: {analysis.volume_ratio:.2f} < {analysis.threshold_used:.2f}, conf: {analysis.confidence_score:.1%})"
        
        except Exception as e:
            return True, f"Erro na validação - aprovado: {str(e)[:30]}"
    
    return _validate_with_volume_enhanced

# Configurações para personalização por exchange/mercado
EXCHANGE_SPECIFIC_CONFIG = {
    'binance': {
        'base_multiplier': 1.0,
        'high_liquidity_pairs': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'],
        'adjustments': {
            'spot': 1.0,
            'futures': 1.1  # Futures precisam de mais volume
        }
    },
    'bybit': {
        'base_multiplier': 1.1,
        'high_liquidity_pairs': ['BTCUSDT', 'ETHUSDT'],
        'adjustments': {
            'spot': 1.0,
            'futures': 1.2
        }
    }
}

# Exemplo de uso e testes
if __name__ == "__main__":
    # Teste do validador
    validator = EnhancedVolumeValidator()
    
    # Simula dados de teste
    import pandas as pd
    test_data = pd.DataFrame({
        'volume': [100, 120, 95, 110, 150, 200, 180, 90, 130, 250],  # Volume crescente com spike
        'high_price': [100, 102, 98, 105, 108, 112, 110, 107, 109, 115],
        'low_price': [98, 100, 95, 103, 105, 108, 107, 105, 107, 110],
        'close_price': [99, 101, 97, 104, 107, 110, 108, 106, 108, 113]
    })
    
    class MockMarketData:
        def __init__(self, symbol, data):
            self.symbol = symbol
            self.data = data
    
    # Testa validação
    market_data = MockMarketData('BTC', test_data)
    
    analysis = validator.validate_volume_intelligent(
        market_data, 'BUY_LONG', 'BTC', '5m'
    )
    
    print("\n🧪 TESTE DO VALIDADOR APRIMORADO")
    print("=" * 50)
    print(f"Volume Ratio: {analysis.volume_ratio:.2f}")
    print(f"Threshold: {analysis.threshold_used:.2f}")
    print(f"Aprovado: {'✅ SIM' if analysis.validation_passed else '❌ NÃO'}")
    print(f"Confiança: {analysis.confidence_score:.1%}")
    print(f"Tendência: {analysis.volume_trend}")
    print(f"Condição: {analysis.market_condition}")
    
    report = validator.format_validation_report(analysis, 'BTC')
    print(report)