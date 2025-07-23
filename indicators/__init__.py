"""
Módulo de Indicadores e Padrões Gráficos - CORRIGIDO
Trading Analyzer v2.0 - TODOS OS DETECTORES INTEGRADOS
"""

# Importações dos indicadores técnicos
from .technical import (
    TechnicalAnalyzer,
    RSIAnalyzer, 
    MACDAnalyzer,
    IndicatorResult
)

# Importações dos padrões gráficos
try:
    from .patterns import (
        PatternAnalyzer,
        HeadAndShouldersDetector,
        DoubleTopBottomDetector, 
        CupAndHandleDetector,
        PatternResult
    )
    PATTERNS_AVAILABLE = True
    print("✅ Padrões SIMPLIFICADOS carregados: Apenas Double Top/Bottom")
except ImportError as e:
    PATTERNS_AVAILABLE = False
    print(f"⚠️ Padrões gráficos não disponíveis: {e}")

# ✅ NOVA IMPORTAÇÃO CORRIGIDA: Candlestick Patterns
try:
    from .candlestick_patterns_detector import (
        CandlestickDetector,
        CandlestickPattern,
        generate_candlestick_signals,
        verify_patterns_implementation
    )
    CANDLESTICK_AVAILABLE = True
    print("✅ Detector de Candlestick carregado: 43 padrões disponíveis")
    
    # Verifica se todos os 43 padrões estão implementados
    try:
        implementation_complete = verify_patterns_implementation()
        if implementation_complete:
            print("🎯 Implementação COMPLETA: Todos os 43 padrões de candlestick")
        else:
            print("⚠️ Implementação INCOMPLETA: Alguns padrões podem estar faltando")
    except Exception as verify_error:
        print(f"⚠️ Erro na verificação de implementação: {verify_error}")
        
except ImportError as e:
    CANDLESTICK_AVAILABLE = False
    print(f"⚠️ Detector de Candlestick não disponível: {e}")
except Exception as e:
    CANDLESTICK_AVAILABLE = False
    print(f"❌ Erro no detector de Candlestick: {e}")

# Lista base de exportações
__all__ = [
    'TechnicalAnalyzer',
    'RSIAnalyzer',
    'MACDAnalyzer', 
    'IndicatorResult'
]

# Adiciona padrões gráficos se disponíveis
if PATTERNS_AVAILABLE:
    __all__.extend([
        'PatternAnalyzer',
        'HeadAndShouldersDetector',
        'DoubleTopBottomDetector',
        'CupAndHandleDetector', 
        'PatternResult'
    ])

# ✅ ADICIONADO: Candlestick patterns se disponíveis
if CANDLESTICK_AVAILABLE:
    __all__.extend([
        'CandlestickDetector',
        'CandlestickPattern',
        'generate_candlestick_signals',
        'verify_patterns_implementation'
    ])

# Constantes de status
AVAILABLE_COMPONENTS = {
    'technical_indicators': True,  # Sempre disponível
    'chart_patterns': PATTERNS_AVAILABLE,
    'candlestick_patterns': CANDLESTICK_AVAILABLE
}

def get_available_detectors():
    """Retorna lista de detectores OTIMIZADOS"""
    detectors = ['Technical Indicators (RSI, MACD) - Timeframes: 5m, 15m']
    
    if PATTERNS_AVAILABLE:
        detectors.append('Chart Patterns (APENAS Double Top/Bottom)')
    
    if CANDLESTICK_AVAILABLE:
        detectors.append('Candlestick Patterns (43 patterns - filtrados)')
    
    return detectors


def get_system_status():
    """Status do sistema OTIMIZADO - CORRIGIDO"""
    return {
        'technical_indicators': 'OK - 5m/15m only',
        'chart_patterns': 'SIMPLIFIED - Double Top/Bottom only' if PATTERNS_AVAILABLE else 'DISABLED',
        'candlestick_patterns': 'OK - High confidence only' if CANDLESTICK_AVAILABLE else 'DISABLED',
        'total_pattern_types': sum([
            1,  # Technical sempre disponível
            1 if PATTERNS_AVAILABLE else 0,  # Patterns se disponível
            1 if CANDLESTICK_AVAILABLE else 0  # Candlestick se disponível
        ]),
        'candlestick_patterns_count': 43 if CANDLESTICK_AVAILABLE else 0,
        'disabled_patterns': ['Head&Shoulders', 'Cup&Handle', '1h timeframe'],
        'optimization': 'Single signal per crypto + 5m priority',
        'anti_hang_protection': 'ACTIVE'
    }

__version__ = "2.0.1"
__author__ = "Trading Analyzer System - COMPLETE EDITION - ANTI-HANG"

# Informações de inicialização CORRIGIDAS
print(f"\n📊 TRADING ANALYZER INDICATORS v{__version__}")
print("=" * 50)
print("Componentes carregados:")
for detector in get_available_detectors():
    print(f"  ✅ {detector}")

status = get_system_status()
print(f"\nSistema OTIMIZADO:")
print(f"  • Timeframes ativos: 5m, 15m (preferência 5m)")
print(f"  • Padrões: Apenas Double Top/Bottom" if PATTERNS_AVAILABLE else "  • Padrões: DESABILITADOS")
print(f"  • Candlesticks: {status['candlestick_patterns_count']} padrões (filtrados)" if CANDLESTICK_AVAILABLE else "  • Candlesticks: DESABILITADOS")
print(f"  • Otimização: {status['optimization']}")
print(f"  • Proteção: {status['anti_hang_protection']}")
if status.get('disabled_patterns'):
    print(f"  • Desabilitados: {', '.join(status['disabled_patterns'])}")
print("=" * 50)