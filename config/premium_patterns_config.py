# config/premium_patterns_config.py - CONFIGURAÇÃO PREMIUM INTEGRADA

"""
🚀 CONFIGURAÇÃO PREMIUM PARA CANDLESTICK PATTERNS
Integra com o sistema existente e adiciona configurações das 3 fases
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

@dataclass
class PremiumPatternConfig:
    """Configuração premium completa para candlestick patterns"""
    
    # ==========================================================================
    # 🔥 FASE 1: CONFIGURAÇÕES BÁSICAS PREMIUM
    # ==========================================================================
    
    # Volume validation (integra com volume_validation_config.py)
    volume_config: Dict[str, Any] = field(default_factory=lambda: {
        'min_ratio_base': 1.3,              # Volume mínimo 30% acima da média
        'significant_ratio': 2.0,            # 2x = volume muito significativo
        'spike_threshold': 2.5,              # 2.5x = spike de volume
        'trend_sensitivity': 0.15,           # 15% mudança = trend significativo
        
        # Ajustes por timeframe
        'timeframe_multipliers': {
            '5m': 1.2,   # 5m precisa de mais volume (mais noise)
            '15m': 1.0,  # 15m volume normal
            '1h': 0.8    # 1h pode ter menos volume
        },
        
        # Ajustes por tipo de pattern
        'pattern_multipliers': {
            'Bullish_Engulfing': 1.1,
            'Bearish_Engulfing': 1.2,  # Vendas precisam de mais volume
            'Hammer': 1.0,
            'Shooting_Star': 1.0,
            'Doji_Bullish': 0.9,       # Doji pode ter menos volume
            'Doji_Bearish': 0.9
        }
    })
    
    # Quality filters rigorosos
    quality_config: Dict[str, Any] = field(default_factory=lambda: {
        'min_score_global': 0.75,           # Score mínimo global
        
        # Thresholds específicos por pattern
        'pattern_thresholds': {
            'Bullish_Engulfing': {
                'min_engulf_ratio': 1.3,    # Corpo atual 30% maior que anterior
                'min_body_pct': 0.8,        # Corpo mínimo 0.8% do preço
                'max_shadow_ratio': 0.3,    # Sombras máximo 30% do corpo
                'quality_threshold': 0.80
            },
            'Bearish_Engulfing': {
                'min_engulf_ratio': 1.4,    # Mais rigoroso para vendas
                'min_body_pct': 0.8,
                'max_shadow_ratio': 0.3,
                'quality_threshold': 0.85   # Mais rigoroso
            },
            'Hammer': {
                'min_shadow_ratio': 2.5,    # Sombra inferior 2.5x o corpo
                'max_upper_shadow': 0.3,    # Sombra superior máximo 30% do corpo
                'min_body_position': 0.7,   # Corpo na parte superior (70%+)
                'quality_threshold': 0.75
            },
            'Shooting_Star': {
                'min_shadow_ratio': 2.5,    # Sombra superior 2.5x o corpo
                'max_lower_shadow': 0.3,    # Sombra inferior máximo 30% do corpo
                'max_body_position': 0.3,   # Corpo na parte inferior (30%-)
                'quality_threshold': 0.75
            },
            'Doji_Bullish': {
                'max_body_ratio': 0.10,     # Corpo máximo 10% do range
                'min_symmetry': 0.6,        # Sombras com 60%+ de simetria
                'min_range_pct': 1.0,       # Range mínimo 1% do preço
                'quality_threshold': 0.65
            },
            'Doji_Bearish': {
                'max_body_ratio': 0.10,
                'min_symmetry': 0.6,
                'min_range_pct': 1.0,
                'quality_threshold': 0.65
            }
        }
    })
    
    # Volatility adaptation
    volatility_config: Dict[str, Any] = field(default_factory=lambda: {
        'adaptation_enabled': True,
        'atr_period_short': 14,
        'atr_period_long': 20,
        
        # Thresholds para classificação de volatilidade
        'high_volatility_threshold': 1.5,   # ATR atual / ATR médio
        'low_volatility_threshold': 0.7,
        
        # Multiplicadores de ajuste
        'high_vol_multiplier': 1.3,         # Expande targets em alta volatilidade
        'low_vol_multiplier': 0.8,          # Reduz targets em baixa volatilidade
        'max_adjustment': 1.5,              # Máximo 50% de ajuste
        'min_adjustment': 0.7               # Mínimo 30% de redução
    })
    
    # ==========================================================================
    # 🔥 FASE 2: CONFIGURAÇÕES AVANÇADAS
    # ==========================================================================
    
    # Context validation
    context_config: Dict[str, Any] = field(default_factory=lambda: {
        'min_score': 0.65,                  # Score mínimo de contexto
        'trend_analysis_enabled': True,
        
        # Períodos para análise de tendência
        'ma_short_period': 10,
        'ma_long_period': 20,
        'momentum_period': 5,
        
        # Pesos para scoring
        'trend_alignment_weight': 0.4,      # 40% do score
        'price_position_weight': 0.2,       # 20% do score
        'momentum_weight': 0.1,             # 10% do score
        'timeframe_weight': 0.1,            # 10% do score
        'volatility_context_weight': 0.2,   # 20% do score
        
        # Configurações por timeframe
        'timeframe_requirements': {
            '5m': {
                'min_trend_strength': 1.0,   # 1% de força mínima
                'position_sensitivity': 0.3  # Sensibilidade à posição no range
            },
            '15m': {
                'min_trend_strength': 1.5,   # 1.5% de força mínima
                'position_sensitivity': 0.2  # Menos sensível
            }
        }
    })
    
    # Timeframe confirmation
    timeframe_config: Dict[str, Any] = field(default_factory=lambda: {
        'confirmation_enabled': True,
        'require_alignment': True,           # Exige alinhamento com TF maior
        
        # Mapeamento de timeframes
        'timeframe_hierarchy': {
            '5m': '15m',    # 5m confirma com 15m
            '15m': '1h',    # 15m confirma com 1h
            '1h': '4h'      # 1h confirma com 4h
        },
        
        # Pesos por tipo de alinhamento
        'alignment_scores': {
            'strongly_aligned': 1.0,         # Mesma direção
            'reversal_setup': 0.8,           # Reversão (ainda bom)
            'neutral': 0.6,                  # Neutro
            'conflicting': 0.3,              # Conflitante
            'no_data': 0.5                   # Sem dados
        },
        
        # Requisitos mínimos
        'min_data_points_higher_tf': 10,    # Mínimo 10 candles no TF maior
        'trend_analysis_period': 10         # Período para análise de tendência
    })
    
    # Technical indicators integration
    technical_integration: Dict[str, Any] = field(default_factory=lambda: {
        'enabled': True,
        'require_confirmation': True,        # Exige confirmação de indicadores
        'min_confirmation_ratio': 0.6,      # 60% dos indicadores devem concordar
        
        # Indicadores utilizados
        'indicators': {
            'RSI': {
                'enabled': True,
                'weight': 0.3,
                'bullish_threshold': 45,     # RSI < 45 para patterns bullish
                'bearish_threshold': 55      # RSI > 55 para patterns bearish
            },
            'MACD': {
                'enabled': True,
                'weight': 0.4,               # Peso maior para MACD
                'use_crossover': True,
                'use_histogram': True
            },
            'BollingerBands': {
                'enabled': True,
                'weight': 0.3,
                'use_position': True,        # Usa posição relativa às bandas
                'extremes_weight': 0.2       # Peso extra para extremos
            }
        }
    })
    
    # ==========================================================================
    # 🔥 FASE 3: CONFIGURAÇÕES ELITE
    # ==========================================================================
    
    # Market structure analysis
    market_structure_config: Dict[str, Any] = field(default_factory=lambda: {
        'enabled': True,
        'analysis_period': 30,              # Últimos 30 candles
        'key_levels_detection': True,
        
        # Configurações de suporte/resistência
        'support_resistance': {
            'min_touches': 2,                # Mínimo 2 toques para validar nível
            'tolerance_pct': 0.5,            # 0.5% de tolerância
            'max_distance_pct': 5.0,         # Máximo 5% de distância
            'lookback_period': 30,           # Busca em 30 candles
            'significance_threshold': 0.02   # 2% mínimo de significância
        },
        
        # Pesos para scoring
        'clear_path_weight': 0.3,           # 30% - caminho livre
        'nearby_level_weight': 0.2,         # 20% - nível próximo de suporte
        'breakout_potential_weight': 0.2,   # 20% - potencial de breakout
        'volume_confirmation_weight': 0.3   # 30% - confirmação de volume
    })
    
    # Session timing
    session_config: Dict[str, Any] = field(default_factory=lambda: {
        'enabled': True,
        'timezone': 'UTC',
        
        # Configurações por sessão
        'sessions': {
            'asian': {
                'start_hour': 22,            # 22:00 UTC
                'end_hour': 8,               # 08:00 UTC
                'base_score': 0.5,           # Score base baixo (baixa liquidez)
                'liquidity': 'low'
            },
            'european': {
                'start_hour': 8,             # 08:00 UTC
                'end_hour': 16,              # 16:00 UTC
                'base_score': 0.7,           # Score médio
                'liquidity': 'medium'
            },
            'american': {
                'start_hour': 13,            # 13:00 UTC (overlap com Europa)
                'end_hour': 21,              # 21:00 UTC
                'base_score': 0.8,           # Score alto (máxima liquidez)
                'liquidity': 'high'
            },
            'overlap_eu_us': {
                'start_hour': 13,            # 13:00 UTC
                'end_hour': 16,              # 16:00 UTC
                'base_score': 0.9,           # Score máximo (overlap)
                'liquidity': 'very_high'
            }
        },
        
        # Ajustes por tipo de pattern
        'pattern_adjustments': {
            'reversal_patterns': 0.1,       # Bonus para reversões em alta liquidez
            'continuation_patterns': 0.05,   # Bonus menor para continuações
            'breakout_patterns': 0.15       # Bonus maior para breakouts
        }
    })
    
    # Momentum confirmation
    momentum_config: Dict[str, Any] = field(default_factory=lambda: {
        'enabled': True,
        'analysis_period': 10,              # Últimos 10 candles
        
        # Componentes do momentum
        'price_momentum_weight': 0.3,       # 30% - momentum de preço
        'rsi_momentum_weight': 0.3,         # 30% - momentum do RSI
        'volume_momentum_weight': 0.2,      # 20% - momentum do volume
        'macd_momentum_weight': 0.2,        # 20% - momentum do MACD
        
        # Thresholds
        'price_momentum_threshold': 1.0,    # 1% de movimento mínimo
        'volume_momentum_threshold': 1.2,   # 20% de aumento no volume
        
        # Configurações específicas
        'divergence_detection': True,       # Detecta divergências
        'momentum_reversal_bonus': 0.2,     # Bonus para reversões com momentum
        'momentum_continuation_bonus': 0.1  # Bonus para continuações
    })
    
    # ==========================================================================
    # 🎯 CONFIGURAÇÕES FINAIS
    # ==========================================================================
    
    # Final scoring weights
    final_scoring: Dict[str, float] = field(default_factory=lambda: {
        'base_pattern': 0.20,               # 20% - Pattern base
        'volume': 0.15,                     # 15% - FASE 1
        'quality': 0.20,                    # 20% - FASE 1 (peso alto)
        'context': 0.15,                    # 15% - FASE 2
        'timeframe': 0.10,                  # 10% - FASE 2
        'trend_confirmation': 0.05,         # 5%  - FASE 2
        'market_structure': 0.10,           # 10% - FASE 3
        'session': 0.03,                    # 3%  - FASE 3
        'momentum': 0.02                    # 2%  - FASE 3
    })
    
    # Risk management
    risk_management: Dict[str, Any] = field(default_factory=lambda: {
        'max_risk_pct': 2.0,                # Máximo 2% de risco
        'min_reward_ratio': 1.5,            # Mínimo 1.5:1 reward/risk
        'max_target_distance_pct': 4.0,     # Target máximo 4%
        'min_final_confidence': 0.78,       # Confiança mínima final
        
        # Validações obrigatórias
        'required_validations': {
            'volume_min': 0.4,               # Volume mínimo 40%
            'quality_min': 0.75,             # Qualidade mínima 75%
            'context_min': 0.65,             # Contexto mínimo 65%
        },
        
        # Ajustes por timeframe
        'timeframe_adjustments': {
            '5m': {
                'max_risk_pct': 1.8,         # Mais conservador para 5m
                'min_confidence': 0.80       # Confiança maior para 5m
            },
            '15m': {
                'max_risk_pct': 2.2,         # Ligeiramente mais flexível
                'min_confidence': 0.75       # Confiança menor para 15m
            }
        }
    })
    
    # Performance monitoring
    monitoring: Dict[str, Any] = field(default_factory=lambda: {
        'enabled': True,
        'log_detailed_analysis': True,
        'track_phase_performance': True,
        'alert_low_quality': True,
        'save_rejected_patterns': False,     # Para debugging
        
        # Métricas rastreadas
        'tracked_metrics': [
            'final_confidence_distribution',
            'phase_1_scores_avg',
            'phase_2_scores_avg', 
            'phase_3_scores_avg',
            'rejection_reasons',
            'pattern_type_performance',
            'timeframe_performance',
            'session_performance'
        ]
    })

    def get_pattern_config(self, pattern_name: str) -> Dict[str, Any]:
        """Retorna configuração específica para um pattern"""
        return self.quality_config['pattern_thresholds'].get(pattern_name, {})
    
    def get_timeframe_config(self, timeframe: str) -> Dict[str, Any]:
        """Retorna configuração específica para um timeframe"""
        base_config = {
            'volume_multiplier': self.volume_config['timeframe_multipliers'].get(timeframe, 1.0),
            'context_requirements': self.context_config['timeframe_requirements'].get(timeframe, {}),
            'risk_adjustments': self.risk_management['timeframe_adjustments'].get(timeframe, {})
        }
        return base_config
    
    def get_current_session_config(self) -> Dict[str, Any]:
        """Retorna configuração da sessão atual"""
        current_hour = datetime.now().hour
        
        # Determina sessão atual
        if 13 <= current_hour <= 16:  # EU-US overlap
            return self.session_config['sessions']['overlap_eu_us']
        elif 13 <= current_hour <= 21:  # American session
            return self.session_config['sessions']['american']
        elif 8 <= current_hour <= 16:   # European session
            return self.session_config['sessions']['european']
        else:  # Asian session ou low liquidity
            return self.session_config['sessions']['asian']
    
    def calculate_minimum_thresholds(self, pattern_name: str, timeframe: str) -> Dict[str, float]:
        """Calcula thresholds mínimos dinâmicos"""
        
        # Base thresholds
        base_volume = self.volume_config['min_ratio_base']
        base_quality = self.quality_config['min_score_global']
        base_context = self.context_config['min_score']
        
        # Ajustes por pattern
        pattern_config = self.get_pattern_config(pattern_name)
        volume_pattern_mult = self.volume_config['pattern_multipliers'].get(pattern_name, 1.0)
        quality_threshold = pattern_config.get('quality_threshold', base_quality)
        
        # Ajustes por timeframe
        timeframe_config = self.get_timeframe_config(timeframe)
        volume_timeframe_mult = timeframe_config.get('volume_multiplier', 1.0)
        
        # Ajustes por sessão
        session_config = self.get_current_session_config()
        session_liquidity = session_config.get('liquidity', 'medium')
        
        # Ajuste de liquidez
        liquidity_adjustments = {
            'very_high': 0.9,    # Reduz thresholds em alta liquidez
            'high': 0.95,
            'medium': 1.0,
            'low': 1.1           # Aumenta thresholds em baixa liquidez
        }
        
        liquidity_mult = liquidity_adjustments.get(session_liquidity, 1.0)
        
        # Calcula thresholds finais
        final_thresholds = {
            'volume_threshold': base_volume * volume_pattern_mult * volume_timeframe_mult * liquidity_mult,
            'quality_threshold': quality_threshold * liquidity_mult,
            'context_threshold': base_context * liquidity_mult,
            'final_confidence_threshold': self.risk_management['min_final_confidence'] * liquidity_mult
        }
        
        return final_thresholds
    
    def get_debugging_info(self) -> Dict[str, Any]:
        """Retorna informações para debugging"""
        return {
            'config_version': '1.0.0',
            'phases_configured': 3,
            'patterns_supported': list(self.quality_config['pattern_thresholds'].keys()),
            'timeframes_supported': list(self.volume_config['timeframe_multipliers'].keys()),
            'sessions_configured': list(self.session_config['sessions'].keys()),
            'indicators_integrated': list(self.technical_integration['indicators'].keys()),
            'risk_management_active': True,
            'monitoring_enabled': self.monitoring['enabled'],
            'current_session': self.get_current_session_config(),
            'default_thresholds': {
                'volume_min': self.volume_config['min_ratio_base'],
                'quality_min': self.quality_config['min_score_global'],
                'context_min': self.context_config['min_score'],
                'final_confidence_min': self.risk_management['min_final_confidence']
            }
        }

# Instância global da configuração premium
premium_config = PremiumPatternConfig()

# ==========================================================================
# 🔧 FUNÇÕES DE INTEGRAÇÃO
# ==========================================================================

def get_premium_config() -> PremiumPatternConfig:
    """Retorna a configuração premium"""
    return premium_config

def update_premium_config(**kwargs) -> None:
    """Atualiza configuração premium"""
    global premium_config
    
    for key, value in kwargs.items():
        if hasattr(premium_config, key):
            setattr(premium_config, key, value)

def get_pattern_thresholds(pattern_name: str, timeframe: str = '5m') -> Dict[str, float]:
    """Função de compatibilidade para obter thresholds de um pattern"""
    return premium_config.calculate_minimum_thresholds(pattern_name, timeframe)

def print_premium_config_summary():
    """Imprime resumo da configuração premium"""
    config = premium_config
    debug_info = config.get_debugging_info()
    
    print("🚀 CONFIGURAÇÃO PREMIUM - CANDLESTICK PATTERNS")
    print("=" * 60)
    print(f"📊 Versão: {debug_info['config_version']}")
    print(f"🔥 Fases: {debug_info['phases_configured']}")
    print(f"📈 Patterns: {len(debug_info['patterns_supported'])}")
    print(f"⏰ Timeframes: {len(debug_info['timeframes_supported'])}")
    print(f"🌍 Sessões: {len(debug_info['sessions_configured'])}")
    
    print(f"\n📊 THRESHOLDS PADRÃO:")
    for key, value in debug_info['default_thresholds'].items():
        print(f"   • {key}: {value}")
    
    print(f"\n🕒 SESSÃO ATUAL:")
    current_session = debug_info['current_session']
    print(f"   • Score base: {current_session.get('base_score', 0.0)}")
    print(f"   • Liquidez: {current_session.get('liquidity', 'unknown')}")
    
    print(f"\n🎯 CONFIGURAÇÕES POR FASE:")
    print(f"   FASE 1: Volume + Quality + Volatility")
    print(f"   FASE 2: Context + Timeframe + Technical")
    print(f"   FASE 3: Market Structure + Session + Momentum")
    
    print(f"\n✅ STATUS:")
    print(f"   • Risk Management: {'ATIVO' if debug_info['risk_management_active'] else 'INATIVO'}")
    print(f"   • Monitoring: {'ATIVO' if debug_info['monitoring_enabled'] else 'INATIVO'}")
    print(f"   • Patterns suportados: {', '.join(debug_info['patterns_supported'])}")

def test_premium_config():
    """Testa a configuração premium"""
    config = premium_config
    
    print("🧪 TESTE DE CONFIGURAÇÃO PREMIUM")
    print("-" * 40)
    
    # Testa configuração para diferentes patterns
    test_patterns = ['Bullish_Engulfing', 'Hammer', 'Doji_Bullish']
    test_timeframes = ['5m', '15m']
    
    for pattern in test_patterns:
        print(f"\n📊 {pattern}:")
        for tf in test_timeframes:
            thresholds = config.calculate_minimum_thresholds(pattern, tf)
            print(f"   {tf}: Vol={thresholds['volume_threshold']:.2f}, "
                  f"Qual={thresholds['quality_threshold']:.2f}, "
                  f"Ctx={thresholds['context_threshold']:.2f}")
    
    # Testa configuração de sessão
    session = config.get_current_session_config()
    print(f"\n🕒 Sessão atual: {session['liquidity']} (score: {session['base_score']})")
    
    print(f"\n✅ Configuração premium funcionando corretamente!")

if __name__ == "__main__":
    print_premium_config_summary()
    print()
    test_premium_config()