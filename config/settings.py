# settings.py

# -*- coding: utf-8 -*-
"""
Configuracoes Multi-Timeframe do Sistema de Trading - VERSÃO FINAL CORRIGIDA
"""
import os
from dataclasses import dataclass, field
from typing import List, Dict

# _#_NOVO_: Classe para configurar a precisão decimal de cada ativo.
@dataclass
class PrecisionConfig:
    """Configurações de precisão para a exchange."""
    # Mapeia o símbolo para o número de casas decimais do PREÇO.
    # Adicione ou modifique os pares conforme sua necessidade.
    symbol_price_precision: Dict[str, int] = field(default_factory=lambda: {
        'BTC': 2,
        'ETH': 2,
        'BNB': 2,
        'SOL': 2,
        'ENA': 4,
        'HBAR': 5,
        'NEAR': 3,
        'OMNI': 3,
        'SUI': 4,
        'PEPE': 8,
        'TURBO': 6,
        'IMX': 4,
        'CRV': 4,
        'HYPE': 6, # Exemplo, ajuste se necessário
        # Adicione outros símbolos aqui
        'DEFAULT': 4 # Valor padrão para símbolos não listados
    })

@dataclass
class DatabaseConfig:
    """Configuracoes de banco de dados"""
    stream_db_path: str = r"C:\Users\mzmvy\Documents\python\trading_system\data\crypto_stream.db"
    signals_db_path: str = r"C:\Users\mzmvy\Documents\python\trading_system\data\trading_analyzer_v2.db"
    stream_table: str = "crypto_stream"
    signals_table: str = "trading_signals_v2"
    backup_table: str = "signal_backup_v2"

@dataclass
class TimeframeConfig:
    """Configuracao para cada timeframe INDIVIDUAL"""
    timeframe: str
    min_data_points: int
    lookback_hours: int
    confidence_threshold: float
    max_signals_per_symbol: int
    analysis_priority: int
    enabled_detectors: List[str] = field(default_factory=lambda: ['technical', 'patterns', 'candlestick'])
    rsi_sensitivity: float = 1.0
    volume_threshold_multiplier: float = 1.0
    pattern_min_strength: float = 0.6

@dataclass
class MultiTimeframeConfig:
    """Configuracao multi-timeframe"""
    enabled_timeframes: List[str] = None
    timeframe_configs: Dict[str, TimeframeConfig] = None
    allow_conflicting_signals: bool = False
    cross_timeframe_confirmation: bool = True
    hierarchy_priority: bool = True

    def __post_init__(self):
        if self.enabled_timeframes is None:
            self.enabled_timeframes = ["5m", "15m", "1h"]
        if self.timeframe_configs is None:
            self.timeframe_configs = {
                "5m": TimeframeConfig(
                    timeframe="5m", min_data_points=150, lookback_hours=12,
                    confidence_threshold=0.80, max_signals_per_symbol=2, analysis_priority=3,
                    enabled_detectors=['technical', 'candlestick'], rsi_sensitivity=1.2,
                    volume_threshold_multiplier=1.8, pattern_min_strength=0.65
                ),
                "15m": TimeframeConfig(
                    timeframe="15m", min_data_points=100, lookback_hours=24,
                    confidence_threshold=0.75, max_signals_per_symbol=1, analysis_priority=2,
                    enabled_detectors=['technical', 'patterns', 'candlestick'], rsi_sensitivity=1.0,
                    volume_threshold_multiplier=1.5, pattern_min_strength=0.6
                ),
                "1h": TimeframeConfig(
                    timeframe="1h", min_data_points=80, lookback_hours=48,
                    confidence_threshold=0.70, max_signals_per_symbol=1, analysis_priority=1,
                    enabled_detectors=['technical', 'patterns'], rsi_sensitivity=0.8,
                    volume_threshold_multiplier=1.2, pattern_min_strength=0.55
                )
            }

@dataclass
class AnalysisConfig:
    """Configuracoes de analise"""
    multi_timeframe: MultiTimeframeConfig = None
    default_timeframe: str = "15m"
    min_data_points: int = 100
    lookback_hours: int = 24
    confidence_threshold: float = 0.75
    symbols: List[str] = None

    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["BNB", "BTC", "ENA", "ETH", "HBAR", "NEAR", "OMNI", "SOL", "SUI", "HYPE", "PEPE", "TURBO", "IMX", "CRV"]
        if self.multi_timeframe is None:
            self.multi_timeframe = MultiTimeframeConfig()

@dataclass
class IndicatorConfig:
    """Configuracoes dos indicadores tecnicos"""
    rsi_period: int = 14
    rsi_overbought: Dict[str, float] = None
    rsi_oversold: Dict[str, float] = None
    macd_fast: Dict[str, int] = None
    macd_slow: Dict[str, int] = None
    macd_signal: Dict[str, int] = None
    volume_ma_period: int = 20
    min_volume_ratio: Dict[str, float] = None

    def __post_init__(self):
        if self.rsi_overbought is None: self.rsi_overbought = {"5m": 72, "15m": 70, "1h": 68}
        if self.rsi_oversold is None: self.rsi_oversold = {"5m": 28, "15m": 30, "1h": 32}
        if self.macd_fast is None: self.macd_fast = {"5m": 10, "15m": 12, "1h": 14}
        if self.macd_slow is None: self.macd_slow = {"5m": 22, "15m": 26, "1h": 30}
        if self.macd_signal is None: self.macd_signal = {"5m": 8, "15m": 9, "1h": 10}
        if self.min_volume_ratio is None: self.min_volume_ratio = {"5m": 1.8, "15m": 1.5, "1h": 1.2}

@dataclass
class PatternConfig:
    """Configuracoes para deteccao de padroes"""
    cup_min_depth: float = 0.15
    cup_max_depth: float = 0.40
    cup_min_duration: int = 30
    handle_max_retrace: float = 0.25
    double_tolerance: float = 0.02
    double_min_distance: int = 15
    double_min_significance: float = 0.08
    hs_shoulder_tolerance: float = 0.03
    hs_min_duration: int = 20
    hs_min_head_prominence: float = 0.05
    min_pattern_strength: float = 0.6
    max_patterns_per_analysis: int = 5

@dataclass
class SystemConfig:
    """Configuracoes do sistema"""
    multi_timeframe_enabled: bool = True
    analysis_interval: int = 300
    backup_all_signals: bool = True
    max_total_signals_per_symbol: int = 4
    log_level: str = "INFO"
    log_file: str = "trading_analyzer_multi.log"
    parallel_analysis: bool = True
    max_workers: int = 6

@dataclass
class ValidationConfig:
    """Configurações para a validação de sinais com microestrutura (Sniper)."""
    enabled: bool = True
    # _#_NOVO_: Nome da tabela de microestrutura adicionado aqui.
    microstructure_table: str = "kline_microstructure_1m"
    validation_window_minutes: int = 5  # Quantos minutos olhar à frente na microestrutura.
    momentum_period: int = 5            # Período para o RSI de momentum na microestrutura.
    buy_momentum_threshold: float = 55.0  # RSI de 1m deve estar acima deste valor para validar uma COMPRA.
    sell_momentum_threshold: float = 45.0 # RSI de 1m deve estar abaixo deste valor para validar uma VENDA.



class Settings:
    """Classe principal de configuracoes"""
    def __init__(self):
        self.database = DatabaseConfig()
        self.analysis = AnalysisConfig()
        self.indicators = IndicatorConfig()
        self.patterns = PatternConfig()
        self.system = SystemConfig()
        self.precisions = PrecisionConfig()
        self.validation = ValidationConfig() # _#_NOVO_: Adiciona as configurações de validação

    def get_timeframe_config(self, timeframe: str) -> TimeframeConfig:
        return self.analysis.multi_timeframe.timeframe_configs.get(timeframe, self.analysis.multi_timeframe.timeframe_configs["15m"])

    def get_enabled_timeframes(self) -> List[str]:
        return self.analysis.multi_timeframe.enabled_timeframes if self.system.multi_timeframe_enabled else [self.analysis.default_timeframe]

    def get_rsi_levels(self, timeframe: str) -> Dict[str, float]:
        return {'overbought': self.indicators.rsi_overbought.get(timeframe, 70), 'oversold': self.indicators.rsi_oversold.get(timeframe, 30)}

    def get_macd_params(self, timeframe: str) -> Dict[str, int]:
        return {'fast': self.indicators.macd_fast.get(timeframe, 12), 'slow': self.indicators.macd_slow.get(timeframe, 26), 'signal': self.indicators.macd_signal.get(timeframe, 9)}

    def get_analysis_symbols(self) -> List[str]:
        return self.analysis.symbols
    
    def get_price_precision(self, symbol: str) -> int:
        return self.precisions.symbol_price_precision.get(symbol, self.precisions.symbol_price_precision['DEFAULT'])

    """Classe principal de configuracoes"""
    def __init__(self):
        self.database = DatabaseConfig()
        self.analysis = AnalysisConfig()
        self.indicators = IndicatorConfig()
        self.patterns = PatternConfig()
        self.system = SystemConfig()
        self.precisions = PrecisionConfig() # _#_NOVO_: Adiciona as configurações de precisão

    def get_timeframe_config(self, timeframe: str) -> TimeframeConfig:
        return self.analysis.multi_timeframe.timeframe_configs.get(timeframe, self.analysis.multi_timeframe.timeframe_configs["15m"])

    def get_enabled_timeframes(self) -> List[str]:
        return self.analysis.multi_timeframe.enabled_timeframes if self.system.multi_timeframe_enabled else [self.analysis.default_timeframe]

    def get_rsi_levels(self, timeframe: str) -> Dict[str, float]:
        return {'overbought': self.indicators.rsi_overbought.get(timeframe, 70), 'oversold': self.indicators.rsi_oversold.get(timeframe, 30)}

    def get_macd_params(self, timeframe: str) -> Dict[str, int]:
        return {'fast': self.indicators.macd_fast.get(timeframe, 12), 'slow': self.indicators.macd_slow.get(timeframe, 26), 'signal': self.indicators.macd_signal.get(timeframe, 9)}

    def get_analysis_symbols(self) -> List[str]:
        return self.analysis.symbols
    
    # _#_NOVO_: Função para obter a precisão de um símbolo
    def get_price_precision(self, symbol: str) -> int:
        return self.precisions.symbol_price_precision.get(symbol, self.precisions.symbol_price_precision['DEFAULT'])


settings = Settings()