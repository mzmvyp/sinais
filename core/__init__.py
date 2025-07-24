# core/__init__.py - IMPORTS CORRIGIDOS

"""
Módulo core com importações corrigidas para o sistema de sinais
"""

try:
    from .analyzer import MultiTimeframeAnalyzer, TradingAnalyzer
except ImportError as e:
    print(f"⚠️ Erro ao importar analyzer: {e}")
    MultiTimeframeAnalyzer = None
    TradingAnalyzer = None

try:
    from .signal_writer import EnhancedSignalWriter, EnhancedTradingSignal, SignalWriter, TradingSignal
except ImportError as e:
    print(f"⚠️ Erro ao importar signal_writer: {e}")
    EnhancedSignalWriter = None
    EnhancedTradingSignal = None
    SignalWriter = None
    TradingSignal = None

try:
    from .signal_monitor import SignalStatusMonitor
except ImportError as e:
    print(f"⚠️ Erro ao importar signal_monitor: {e}")
    SignalStatusMonitor = None

try:
    from .data_reader import DataReader, MarketData
except ImportError as e:
    print(f"⚠️ Erro ao importar data_reader: {e}")
    DataReader = None
    MarketData = None

try:
    from .signal_manager import SignalManager
except ImportError as e:
    print(f"⚠️ Erro ao importar signal_manager: {e}")
    SignalManager = None

# Exporta as classes principais
__all__ = [
    'MultiTimeframeAnalyzer',
    'TradingAnalyzer',
    'EnhancedSignalWriter', 
    'EnhancedTradingSignal',
    'SignalWriter',
    'TradingSignal',
    'SignalStatusMonitor',
    'DataReader',
    'MarketData',
    'SignalManager'
]

# Informações da versão
__version__ = "2.1.0"
__author__ = "Trading System"
__description__ = "Sistema Completo de Trading com Análise Técnica"