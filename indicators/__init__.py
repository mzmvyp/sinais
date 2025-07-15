"""
Módulo de Indicadores e Padrões Gráficos
Trading Analyzer v1.0
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
except ImportError:
    PATTERNS_AVAILABLE = False

__all__ = [
    'TechnicalAnalyzer',
    'RSIAnalyzer',
    'MACDAnalyzer', 
    'IndicatorResult'
]

if PATTERNS_AVAILABLE:
    __all__.extend([
        'PatternAnalyzer',
        'HeadAndShouldersDetector',
        'DoubleTopBottomDetector',
        'CupAndHandleDetector', 
        'PatternResult'
    ])

__version__ = "1.0.0"
__author__ = "Trading Analyzer System"