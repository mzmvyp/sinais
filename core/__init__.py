"""
Módulo Core do Trading Analyzer
Componentes principais do sistema
"""
from .enhanced_analyzer import EnhancedFilters, EnhancedTradingAnalyzer
from .analyzer import TradingAnalyzer
from .data_reader import DataReader, MarketData
from .signal_writer import SignalWriter, TradingSignal

__all__ = [
    'TradingAnalyzer',
    'DataReader',
    'MarketData', 
    'SignalWriter',
    'TradingSignal'
]

__version__ = "1.0.0"