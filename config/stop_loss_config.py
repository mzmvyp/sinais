# stop_loss_config.py - CONFIGURAÇÕES AVANÇADAS DO STOP LOSS INTELIGENTE

"""
Configurações avançadas e ajustes finos para o sistema de stop loss inteligente
Permite personalização por symbol, timeframe e condições de mercado
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class StopLossConfig:
    """Configuração avançada do sistema de stop loss inteligente"""
    
    # Configurações gerais por timeframe
    timeframe_configs: Dict[str, Dict] = field(default_factory=lambda: {
        '5m': {
            'atr_period': 14,
            'atr_multiplier': 1.0,
            'max_risk_pct': 1.5,
            'min_risk_pct': 0.8,
            'support_resistance_lookback': 20,
            'swing_lookback': 10,
            'volatility_adjustment': True,
            'preferred_methods': ['Support_Level', 'Resistance_Level', 'ATR_Dynamic', 'Swing_Level']
        },
        '15m': {
            'atr_period': 14,
            'atr_multiplier': 2.0,
            'max_risk_pct': 3.0,
            'min_risk_pct': 1.0,
            'support_resistance_lookback': 30,
            'swing_lookback': 15,
            'volatility_adjustment': True,
            'preferred_methods': ['Support_Level', 'Resistance_Level', 'Market_Structure', 'ATR_Dynamic']
        },
        '1h': {
            'atr_period': 14,
            'atr_multiplier': 2.5,
            'max_risk_pct': 4.0,
            'min_risk_pct': 1.5,
            'support_resistance_lookback': 50,
            'swing_lookback': 20,
            'volatility_adjustment': True,
            'preferred_methods': ['Market_Structure', 'Support_Level', 'Resistance_Level', 'ATR_Dynamic']
        }
    })
    
    # Configurações específicas por symbol (para cryptos mais voláteis)
    symbol_overrides: Dict[str, Dict] = field(default_factory=lambda: {
        'PEPE': {
            'max_risk_pct_multiplier': 0.8,  # 20% menos risco para memecoins
            'atr_multiplier_adjustment': 0.7,  # ATR mais conservador
            'preferred_methods': ['ATR_Dynamic', 'Swing_Level']  # Métodos mais simples
        },
        'TURBO': {
            'max_risk_pct_multiplier': 0.8,
            'atr_multiplier_adjustment': 0.7,
            'preferred_methods': ['ATR_Dynamic', 'Swing_Level']
        },
        'BTC': {
            'max_risk_pct_multiplier': 1.2,  # 20% mais risco para BTC (mais estável)
            'atr_multiplier_adjustment': 1.1,
            'preferred_methods': ['Market_Structure', 'Support_Level', 'Resistance_Level', 'ATR_Dynamic']
        },
        'ETH': {
            'max_risk_pct_multiplier': 1.1,
            'atr_multiplier_adjustment': 1.05,
            'preferred_methods': ['Market_Structure', 'Support_Level', 'Resistance_Level', 'ATR_Dynamic']
        }
    })
    
    # Prioridades dos métodos (maior número = maior prioridade)
    method_priorities: Dict[str, int] = field(default_factory=lambda: {
        'Support_Level': 10,           # Máxima prioridade
        'Resistance_Level': 10,        # Máxima prioridade
        'Market_Structure': 8,         # Alta prioridade
        'Swing_Level': 7,              # Boa prioridade
        'ATR_Dynamic': 6,              # Prioridade média
        'Improved_Fallback': 3,        # Baixa prioridade
        'Emergency_Fallback': 1,       # Mínima prioridade
        'Error_Fallback': 1            # Mínima prioridade
    })
    
    # Configurações de validação
    validation_config: Dict = field(default_factory=lambda: {
        'enable_direction_check': True,      # Verifica direção do stop
        'enable_risk_limits': True,          # Aplica limites de risco
        'enable_consistency_check': True,    # Verifica consistência com análise
        'max_correction_attempts': 2,        # Máximo de tentativas de correção
        'emergency_fallback_risk': 1.5       # % de risco para fallback de emergência
    })
    
    # Configurações de qualidade
    quality_thresholds: Dict = field(default_factory=lambda: {
        'min_method_confidence': 0.5,        # Confiança mínima do método
        'preferred_risk_range': (1.0, 3.5),  # Faixa de risco preferida (%)
        'max_volatility_adjustment': 2.0,    # Máximo ajuste por volatilidade
        'min_atr_periods': 10,               # Mínimo de períodos para ATR válido
        'sr_proximity_threshold': 0.5        # % máximo de distância para S/R ser relevante
    })
    
    # Configurações por condição de mercado
    market_condition_adjustments: Dict = field(default_factory=lambda: {
        'high_volatility': {
            'atr_multiplier_factor': 0.8,    # Reduz ATR em alta volatilidade
            'max_risk_reduction': 0.2,       # Reduz risco máximo em 20%
            'preferred_methods': ['Support_Level', 'Resistance_Level', 'Market_Structure']
        },
        'low_volatility': {
            'atr_multiplier_factor': 1.2,    # Aumenta ATR em baixa volatilidade
            'max_risk_increase': 0.15,       # Aumenta risco máximo em 15%
            'preferred_methods': ['ATR_Dynamic', 'Swing_Level', 'Market_Structure']
        },
        'trending_market': {
            'structure_weight_increase': 1.3, # Aumenta peso da estrutura
            'preferred_methods': ['Market_Structure', 'Swing_Level', 'ATR_Dynamic']
        },
        'sideways_market': {
            'sr_weight_increase': 1.4,       # Aumenta peso de S/R
            'preferred_methods': ['Support_Level', 'Resistance_Level', 'Swing_Level']
        }
    })

    def get_timeframe_config(self, timeframe: str) -> Dict:
        """Retorna configuração para um timeframe específico"""
        return self.timeframe_configs.get(timeframe, self.timeframe_configs['15m'])
    
    def get_symbol_adjustments(self, symbol: str) -> Dict:
        """Retorna ajustes específicos para um symbol"""
        return self.symbol_overrides.get(symbol, {})
    
    def get_adjusted_config(self, symbol: str, timeframe: str) -> Dict:
        """Retorna configuração ajustada para symbol+timeframe específico"""
        base_config = self.get_timeframe_config(timeframe).copy()
        symbol_adjustments = self.get_symbol_adjustments(symbol)
        
        # Aplica ajustes específicos do symbol
        if 'max_risk_pct_multiplier' in symbol_adjustments:
            base_config['max_risk_pct'] *= symbol_adjustments['max_risk_pct_multiplier']
            base_config['min_risk_pct'] *= symbol_adjustments['max_risk_pct_multiplier']
        
        if 'atr_multiplier_adjustment' in symbol_adjustments:
            base_config['atr_multiplier'] *= symbol_adjustments['atr_multiplier_adjustment']
        
        if 'preferred_methods' in symbol_adjustments:
            base_config['preferred_methods'] = symbol_adjustments['preferred_methods']
        
        return base_config
    
    def is_method_preferred(self, method: str, symbol: str, timeframe: str) -> bool:
        """Verifica se um método é preferido para determinado symbol+timeframe"""
        config = self.get_adjusted_config(symbol, timeframe)
        return method in config.get('preferred_methods', [])
    
    def get_method_priority(self, method: str, symbol: str, timeframe: str) -> int:
        """Retorna prioridade ajustada de um método"""
        base_priority = self.method_priorities.get(method, 0)
        
        # Bonus se for método preferido
        if self.is_method_preferred(method, symbol, timeframe):
            base_priority += 2
        
        return base_priority
    
    def should_apply_market_adjustment(self, market_condition: str) -> bool:
        """Verifica se deve aplicar ajuste por condição de mercado"""
        return market_condition in self.market_condition_adjustments
    
    def get_market_adjustment(self, market_condition: str) -> Dict:
        """Retorna ajustes para condição de mercado específica"""
        return self.market_condition_adjustments.get(market_condition, {})

# Instância global da configuração
stop_loss_config = StopLossConfig()

# Funções de conveniência para usar no sistema principal
def get_stop_config_for_symbol(symbol: str, timeframe: str) -> Dict:
    """Função de conveniência para obter configuração ajustada"""
    return stop_loss_config.get_adjusted_config(symbol, timeframe)

def is_high_volatility_symbol(symbol: str) -> bool:
    """Identifica symbols de alta volatilidade"""
    high_vol_symbols = ['PEPE', 'TURBO', 'HYPE', 'MEME', 'DOGE', 'SHIB']
    return any(vol_symbol in symbol.upper() for vol_symbol in high_vol_symbols)

def is_stable_symbol(symbol: str) -> bool:
    """Identifica symbols mais estáveis"""
    stable_symbols = ['BTC', 'ETH', 'BNB', 'USDT', 'USDC']
    return any(stable_symbol in symbol.upper() for stable_symbol in stable_symbols)

def get_symbol_category(symbol: str) -> str:
    """Categoriza o symbol para aplicar configurações apropriadas"""
    if is_high_volatility_symbol(symbol):
        return 'high_volatility'
    elif is_stable_symbol(symbol):
        return 'stable'
    else:
        return 'standard'

def update_config_for_symbol(symbol: str, config_updates: Dict):
    """Atualiza configuração para um symbol específico"""
    if symbol not in stop_loss_config.symbol_overrides:
        stop_loss_config.symbol_overrides[symbol] = {}
    
    stop_loss_config.symbol_overrides[symbol].update(config_updates)
    
def print_current_config():
    """Imprime configuração atual para debug"""
    print("\n🔧 CONFIGURAÇÃO ATUAL DO STOP LOSS INTELIGENTE")
    print("=" * 60)
    
    print("\n📊 Por Timeframe:")
    for tf, config in stop_loss_config.timeframe_configs.items():
        print(f"  {tf}: ATR {config['atr_multiplier']}x | Risco {config['min_risk_pct']:.1f}-{config['max_risk_pct']:.1f}%")
    
    print("\n🪙 Ajustes por Symbol:")
    for symbol, adjustments in stop_loss_config.symbol_overrides.items():
        print(f"  {symbol}: {adjustments}")
    
    print("\n🎯 Prioridades dos Métodos:")
    sorted_methods = sorted(stop_loss_config.method_priorities.items(), key=lambda x: x[1], reverse=True)
    for method, priority in sorted_methods[:5]:  # Top 5
        print(f"  {method}: {priority}")

if __name__ == "__main__":
    # Teste da configuração
    print_current_config()
    
    # Exemplo de uso
    print(f"\n📝 Exemplo - Configuração para PEPE 5m:")
    pepe_config = get_stop_config_for_symbol('PEPE', '5m')
    print(f"  Risco máximo: {pepe_config['max_risk_pct']:.1f}%")
    print(f"  ATR multiplicador: {pepe_config['atr_multiplier']:.1f}")
    print(f"  Métodos preferidos: {pepe_config['preferred_methods']}")
    
    print(f"\n📝 Exemplo - Configuração para BTC 1h:")
    btc_config = get_stop_config_for_symbol('BTC', '1h')
    print(f"  Risco máximo: {btc_config['max_risk_pct']:.1f}%")
    print(f"  ATR multiplicador: {btc_config['atr_multiplier']:.1f}")
    print(f"  Métodos preferidos: {btc_config['preferred_methods']}")