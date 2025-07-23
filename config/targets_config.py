# targets_config.py - CONFIGURAÇÕES AVANÇADAS DOS TARGETS TÉCNICOS

"""
Configurações avançadas e ajustes finos para o sistema de targets inteligentes
Permite personalização por symbol, timeframe e condições de mercado
Complementa o stop_loss_config.py
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class TargetsConfig:
    """Configuração avançada do sistema de targets inteligentes"""
    
    # Configurações gerais por timeframe
    timeframe_configs: Dict[str, Dict] = field(default_factory=lambda: {
        '5m': {
            'fibonacci_levels': [0.618, 1.0, 1.618, 2.618],
            'max_target_distance_pct': 6.0,
            'min_risk_reward': 1.5,
            'max_risk_reward': 4.0,
            'preferred_risk_reward': 2.5,
            'resistance_lookback': 20,
            'support_lookback': 20,
            'structure_lookback': 15,
            'atr_multipliers': [1.5, 3.5],
            'preferred_methods': ['Resistance_Levels', 'Support_Levels', 'Market_Structure', 'Fibonacci_Projection'],
            'enable_fibonacci': True,
            'enable_structure_analysis': True
        },
        '15m': {
            'fibonacci_levels': [0.618, 1.0, 1.618, 2.618],
            'max_target_distance_pct': 8.0,
            'min_risk_reward': 1.8,
            'max_risk_reward': 5.0,
            'preferred_risk_reward': 3.0,
            'resistance_lookback': 30,
            'support_lookback': 30,
            'structure_lookback': 20,
            'atr_multipliers': [2.5, 4.0],
            'preferred_methods': ['Market_Structure', 'Resistance_Levels', 'Support_Levels', 'Fibonacci_Projection'],
            'enable_fibonacci': True,
            'enable_structure_analysis': True
        },
        '1h': {
            'fibonacci_levels': [0.618, 1.0, 1.618, 2.618],
            'max_target_distance_pct': 10.0,
            'min_risk_reward': 2.0,
            'max_risk_reward': 6.0,
            'preferred_risk_reward': 3.5,
            'resistance_lookback': 50,
            'support_lookback': 50,
            'structure_lookback': 30,
            'atr_multipliers': [3.0, 5.0],
            'preferred_methods': ['Market_Structure', 'Fibonacci_Projection', 'Resistance_Levels', 'Support_Levels'],
            'enable_fibonacci': True,
            'enable_structure_analysis': True
        }
    })
    
    # Configurações específicas por symbol
    symbol_overrides: Dict[str, Dict] = field(default_factory=lambda: {
        'PEPE': {
            'max_risk_reward_multiplier': 0.8,  # 20% menos targets para memecoins
            'max_target_distance_pct': 4.0,  # Mais conservador
            'preferred_methods': ['ATR_Dynamic', 'Market_Structure'],  # Métodos mais simples
            'enable_fibonacci': False  # Desabilita Fibonacci para alta volatilidade
        },
        'TURBO': {
            'max_risk_reward_multiplier': 0.8,
            'max_target_distance_pct': 4.0,
            'preferred_methods': ['ATR_Dynamic', 'Market_Structure'],
            'enable_fibonacci': False
        },
        'BTC': {
            'max_risk_reward_multiplier': 1.2,  # 20% mais ambicioso para BTC
            'max_target_distance_pct': 12.0,
            'preferred_methods': ['Market_Structure', 'Fibonacci_Projection', 'Resistance_Levels', 'Support_Levels'],
            'enable_fibonacci': True,
            'fibonacci_levels': [0.618, 1.0, 1.618, 2.618, 4.236]  # Mais níveis para BTC
        },
        'ETH': {
            'max_risk_reward_multiplier': 1.1,
            'max_target_distance_pct': 10.0,
            'preferred_methods': ['Market_Structure', 'Fibonacci_Projection', 'Resistance_Levels', 'Support_Levels'],
            'enable_fibonacci': True
        }
    })
    
    # Prioridades dos métodos (maior número = maior prioridade)
    method_priorities: Dict[str, int] = field(default_factory=lambda: {
        'Resistance_Levels': 10,           # Máxima prioridade
        'Support_Levels': 10,              # Máxima prioridade  
        'Market_Structure': 9,             # Muito alta prioridade
        'Fibonacci_Projection': 8,         # Alta prioridade
        'ATR_Dynamic': 6,                  # Prioridade média
        'Structure_Confluence': 7,         # Boa prioridade (combinação)
        'Simple_Fallback': 3,              # Baixa prioridade
        'Emergency_Fallback': 1            # Mínima prioridade
    })
    
    # Configurações de validação
    validation_config: Dict = field(default_factory=lambda: {
        'enable_direction_check': True,       # Verifica direção dos targets
        'enable_rr_limits': True,             # Aplica limites de risk/reward
        'enable_distance_limits': True,       # Aplica limites de distância
        'max_correction_attempts': 2,         # Máximo de tentativas de correção
        'emergency_fallback_rr': 2.0,         # RR para fallback de emergência
        'min_target_separation_pct': 1.0      # Separação mínima entre targets (%)
    })
    
    # Configurações de qualidade
    quality_thresholds: Dict = field(default_factory=lambda: {
        'min_method_confidence': 0.6,         # Confiança mínima do método
        'preferred_rr_range': (2.0, 4.0),     # Faixa de RR preferida
        'max_fibonacci_extension': 4.236,     # Máxima extensão Fibonacci
        'min_sr_significance': 3,             # Mínimo de toques em S/R
        'sr_proximity_threshold': 1.0         # % máximo de distância para S/R ser relevante
    })
    
    # Configurações por condição de mercado
    market_condition_adjustments: Dict = field(default_factory=lambda: {
        'high_volatility': {
            'rr_reduction_factor': 0.8,       # Reduz targets em alta volatilidade
            'max_distance_reduction': 0.7,    # Reduz distância máxima
            'preferred_methods': ['Market_Structure', 'ATR_Dynamic'],
            'disable_fibonacci': True          # Desabilita Fibonacci em alta vol
        },
        'low_volatility': {
            'rr_increase_factor': 1.2,        # Aumenta targets em baixa volatilidade  
            'max_distance_increase': 1.3,     # Aumenta distância máxima
            'preferred_methods': ['Fibonacci_Projection', 'Resistance_Levels', 'Support_Levels'],
            'enable_extended_fibonacci': True  # Habilita extensões Fibonacci
        },
        'trending_market': {
            'structure_weight_increase': 1.4,  # Aumenta peso da estrutura
            'fibonacci_weight_increase': 1.2,  # Aumenta peso do Fibonacci
            'preferred_methods': ['Market_Structure', 'Fibonacci_Projection', 'ATR_Dynamic']
        },
        'sideways_market': {
            'sr_weight_increase': 1.5,        # Aumenta peso de S/R
            'reduce_targets_distance': 0.8,   # Reduz distância em lateral
            'preferred_methods': ['Resistance_Levels', 'Support_Levels', 'Market_Structure']
        }
    })
    
    # Configurações de combinação de métodos
    confluence_config: Dict = field(default_factory=lambda: {
        'enable_method_confluence': True,      # Habilita confluência de métodos
        'min_confluence_methods': 2,           # Mínimo de métodos para confluência
        'confluence_tolerance_pct': 0.5,       # Tolerância para considerar confluência
        'confluence_bonus_confidence': 0.1,    # Bonus de confiança para confluência
        'preferred_confluences': [
            ['Resistance_Levels', 'Fibonacci_Projection'],
            ['Support_Levels', 'Fibonacci_Projection'], 
            ['Market_Structure', 'ATR_Dynamic']
        ]
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
        if 'max_risk_reward_multiplier' in symbol_adjustments:
            base_config['min_risk_reward'] *= symbol_adjustments['max_risk_reward_multiplier']
            base_config['max_risk_reward'] *= symbol_adjustments['max_risk_reward_multiplier']
            base_config['preferred_risk_reward'] *= symbol_adjustments['max_risk_reward_multiplier']
        
        if 'max_target_distance_pct' in symbol_adjustments:
            base_config['max_target_distance_pct'] = symbol_adjustments['max_target_distance_pct']
        
        if 'preferred_methods' in symbol_adjustments:
            base_config['preferred_methods'] = symbol_adjustments['preferred_methods']
        
        if 'enable_fibonacci' in symbol_adjustments:
            base_config['enable_fibonacci'] = symbol_adjustments['enable_fibonacci']
        
        if 'fibonacci_levels' in symbol_adjustments:
            base_config['fibonacci_levels'] = symbol_adjustments['fibonacci_levels']
        
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
    
    def calculate_optimal_rr_range(self, symbol: str, timeframe: str) -> tuple[float, float]:
        """Calcula faixa ótima de risk/reward para symbol+timeframe"""
        config = self.get_adjusted_config(symbol, timeframe)
        min_rr = config.get('min_risk_reward', 1.5)
        max_rr = config.get('max_risk_reward', 4.0)
        preferred_rr = config.get('preferred_risk_reward', 2.5)
        
        return min_rr, max_rr, preferred_rr
    
    def should_enable_fibonacci(self, symbol: str, timeframe: str) -> bool:
        """Verifica se Fibonacci deve ser habilitado para symbol+timeframe"""
        config = self.get_adjusted_config(symbol, timeframe)
        return config.get('enable_fibonacci', True)
    
    def get_fibonacci_levels(self, symbol: str, timeframe: str) -> List[float]:
        """Retorna níveis de Fibonacci para symbol+timeframe"""
        config = self.get_adjusted_config(symbol, timeframe)
        return config.get('fibonacci_levels', [0.618, 1.0, 1.618])

# Instância global da configuração
targets_config = TargetsConfig()

# Funções de conveniência para usar no sistema principal
def get_targets_config_for_symbol(symbol: str, timeframe: str) -> Dict:
    """Função de conveniência para obter configuração ajustada de targets"""
    return targets_config.get_adjusted_config(symbol, timeframe)

def is_high_volatility_symbol_targets(symbol: str) -> bool:
    """Identifica symbols de alta volatilidade para targets"""
    high_vol_symbols = ['PEPE', 'TURBO', 'HYPE', 'MEME', 'DOGE', 'SHIB']
    return any(vol_symbol in symbol.upper() for vol_symbol in high_vol_symbols)

def is_stable_symbol_targets(symbol: str) -> bool:
    """Identifica symbols mais estáveis para targets"""
    stable_symbols = ['BTC', 'ETH', 'BNB', 'USDT', 'USDC']
    return any(stable_symbol in symbol.upper() for stable_symbol in stable_symbols)

def get_symbol_category_targets(symbol: str) -> str:
    """Categoriza o symbol para aplicar configurações apropriadas de targets"""
    if is_high_volatility_symbol_targets(symbol):
        return 'high_volatility'
    elif is_stable_symbol_targets(symbol):
        return 'stable'
    else:
        return 'standard'

def update_targets_config_for_symbol(symbol: str, config_updates: Dict):
    """Atualiza configuração de targets para um symbol específico"""
    if symbol not in targets_config.symbol_overrides:
        targets_config.symbol_overrides[symbol] = {}
    
    targets_config.symbol_overrides[symbol].update(config_updates)

def get_optimal_targets_method(symbol: str, timeframe: str, available_methods: List[str]) -> str:
    """Retorna o método ótimo de targets para symbol+timeframe"""
    config = targets_config.get_adjusted_config(symbol, timeframe)
    preferred_methods = config.get('preferred_methods', [])
    
    # Retorna o primeiro método preferido que está disponível
    for method in preferred_methods:
        if method in available_methods:
            return method
    
    # Fallback para o primeiro disponível
    return available_methods[0] if available_methods else 'ATR_Dynamic'

def print_targets_config():
    """Imprime configuração atual dos targets para debug"""
    print("\n🎯 CONFIGURAÇÃO ATUAL DOS TARGETS INTELIGENTES")
    print("=" * 60)
    
    print("\n📊 Por Timeframe:")
    for tf, config in targets_config.timeframe_configs.items():
        rr_range = f"{config['min_risk_reward']:.1f}-{config['max_risk_reward']:.1f}"
        distance = config['max_target_distance_pct']
        print(f"  {tf}: RR {rr_range} | Distância {distance:.1f}% | Fibonacci: {config.get('enable_fibonacci', False)}")
    
    print("\n🪙 Ajustes por Symbol:")
    for symbol, adjustments in targets_config.symbol_overrides.items():
        print(f"  {symbol}: {adjustments}")
    
    print("\n🎯 Prioridades dos Métodos:")
    sorted_methods = sorted(targets_config.method_priorities.items(), key=lambda x: x[1], reverse=True)
    for method, priority in sorted_methods[:5]:  # Top 5
        print(f"  {method}: {priority}")
    
    print("\n🔧 Configurações de Qualidade:")
    quality = targets_config.quality_thresholds
    print(f"  • Confiança mínima: {quality['min_method_confidence']:.2f}")
    print(f"  • RR preferido: {quality['preferred_rr_range'][0]:.1f}-{quality['preferred_rr_range'][1]:.1f}")
    print(f"  • Max Fibonacci: {quality['max_fibonacci_extension']:.3f}")

if __name__ == "__main__":
    # Teste da configuração
    print_targets_config()
    
    # Exemplo de uso
    print(f"\n📝 Exemplo - Configuração para PEPE 5m:")
    pepe_config = get_targets_config_for_symbol('PEPE', '5m')
    print(f"  RR máximo: {pepe_config['max_risk_reward']:.1f}")
    print(f"  Distância máxima: {pepe_config['max_target_distance_pct']:.1f}%")
    print(f"  Métodos preferidos: {pepe_config['preferred_methods']}")
    print(f"  Fibonacci habilitado: {pepe_config.get('enable_fibonacci', True)}")
    
    print(f"\n📝 Exemplo - Configuração para BTC 1h:")
    btc_config = get_targets_config_for_symbol('BTC', '1h')
    print(f"  RR máximo: {btc_config['max_risk_reward']:.1f}")
    print(f"  Distância máxima: {btc_config['max_target_distance_pct']:.1f}%")
    print(f"  Métodos preferidos: {btc_config['preferred_methods']}")
    print(f"  Níveis Fibonacci: {btc_config.get('fibonacci_levels', [])}")