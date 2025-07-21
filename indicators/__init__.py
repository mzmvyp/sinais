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
    print("✅ Padrões gráficos carregados: Head&Shoulders, Double Top/Bottom, Cup&Handle")
except ImportError as e:
    PATTERNS_AVAILABLE = False
    print(f"⚠️ Padrões gráficos não disponíveis: {e}")

# ✅ NOVA IMPORTAÇÃO: Candlestick Patterns (43 padrões)
try:
    from .candlestick_patterns_detector import (
        CandlestickDetector,
        CandlestickPattern,
        generate_candlestick_signals,
        verify_patterns_implementation
    )
    CANDLESTICK_AVAILABLE = False
    print("✅ Detector de Candlestick carregado: 43 padrões disponíveis")
    
    # Verifica se todos os 43 padrões estão implementados
    implementation_complete = verify_patterns_implementation()
    if implementation_complete:
        print("🎯 Implementação COMPLETA: Todos os 43 padrões de candlestick")
    else:
        print("⚠️ Implementação INCOMPLETA: Alguns padrões podem estar faltando")
        
except ImportError as e:
    CANDLESTICK_AVAILABLE = False
    print(f"⚠️ Detector de Candlestick não disponível: {e}")

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
    """Retorna lista de detectores disponíveis"""
    detectors = ['Technical Indicators (RSI, MACD)']
    
    if PATTERNS_AVAILABLE:
        detectors.append('Chart Patterns (H&S, Double Top/Bottom, Cup&Handle)')
    
    if CANDLESTICK_AVAILABLE:
        detectors.append('Candlestick Patterns (43 patterns)')
    
    return detectors

def get_system_status():
    """Retorna status completo do sistema de indicadores"""
    return {
        'technical_indicators': 'OK',
        'chart_patterns': 'OK' if PATTERNS_AVAILABLE else 'NOT_AVAILABLE',
        'candlestick_patterns': 'OK' if CANDLESTICK_AVAILABLE else 'NOT_AVAILABLE',
        'total_pattern_types': sum([
            1,  # Technical sempre disponível
            1 if PATTERNS_AVAILABLE else 0,
            1 if CANDLESTICK_AVAILABLE else 0
        ]),
        'candlestick_patterns_count': 43 if CANDLESTICK_AVAILABLE else 0
    }

__version__ = "2.0.0"
__author__ = "Trading Analyzer System - COMPLETE EDITION"

# Informações de inicialização
print(f"\n📊 TRADING ANALYZER INDICATORS v{__version__}")
print("=" * 50)
print("Componentes carregados:")
for detector in get_available_detectors():
    print(f"  ✅ {detector}")

status = get_system_status()
print(f"\nTotal de tipos de análise: {status['total_pattern_types']}/3")
if status['candlestick_patterns_count'] > 0:
    print(f"Padrões de candlestick: {status['candlestick_patterns_count']}")
print("=" * 50)