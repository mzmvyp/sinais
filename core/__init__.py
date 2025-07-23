"""
Módulo Core do Trading Analyzer
Componentes principais do sistema
"""
from .analyzer import TradingAnalyzer
from .data_reader import DataReader, MarketData
from .signal_writer import SignalWriter, TradingSignal
from .signal_manager import SignalManager, print_active_signals_table, clear_symbol_signals

__all__ = [
    'TradingAnalyzer',
    'DataReader',
    'MarketData', 
    'SignalWriter',
    'TradingSignal',
    'SignalManager', 
    'print_active_signals_table',
    'clear_symbol_signals'
]

__version__ = "1.0.0"