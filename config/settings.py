# settings.py - CORRIGIDO PARA APENAS 5m e 15m

# -*- coding: utf-8 -*-
"""
Configuracoes Multi-Timeframe do Sistema de Trading - VERSÃO FINAL CORRIGIDA
APENAS 5m e 15m ATIVOS
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
    stream_table: str = "crypto_ohlc"
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
    """Configuracao multi-timeframe - APENAS 5m e 15m"""
    enabled_timeframes: List[str] = None
    timeframe_configs: Dict[str, TimeframeConfig] = None
    allow_conflicting_signals: bool = False
    cross_timeframe_confirmation: bool = True
    hierarchy_priority: bool = True

    def __post_init__(self):
        # CORRIGIDO: Apenas 5m e 15m habilitados
        if self.enabled_timeframes is None:
            self.enabled_timeframes = ["5m", "15m"]
        
        if self.timeframe_configs is None:
            self.timeframe_configs = {
                "5m": TimeframeConfig(
                    timeframe="5m", min_data_points=100, lookback_hours=12,  # REDUZIDO de 150 para 100
                    confidence_threshold=0.75, max_signals_per_symbol=1, analysis_priority=1,  # PRIORIDADE 1 (máxima)
                    enabled_detectors=['technical', 'candlestick'], rsi_sensitivity=1.2,
                    volume_threshold_multiplier=1.5, pattern_min_strength=0.65  # RELAXADO
                ),
                "15m": TimeframeConfig(
                    timeframe="15m", min_data_points=80, lookback_hours=24,  # REDUZIDO de 100 para 80
                    confidence_threshold=0.70, max_signals_per_symbol=1, analysis_priority=2,  # PRIORIDADE 2
                    enabled_detectors=['technical', 'candlestick'], rsi_sensitivity=1.0,
                    volume_threshold_multiplier=1.3, pattern_min_strength=0.6  # RELAXADO
                )
                # 1h REMOVIDO COMPLETAMENTE
            }

@dataclass
class AnalysisConfig:
    """Configuracoes de analise - OTIMIZADA"""
    multi_timeframe: MultiTimeframeConfig = None
    default_timeframe: str = "5m"  # MUDADO para 5m como padrão
    min_data_points: int = 80  # REDUZIDO
    lookback_hours: int = 24
    confidence_threshold: float = 0.70  # REDUZIDO para ser mais permissivo
    symbols: List[str] = None

    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["BNB", "BTC", "ENA", "ETH", "NEAR", "SOL", "SUI", "IMX"]
        if self.multi_timeframe is None:
            self.multi_timeframe = MultiTimeframeConfig()

@dataclass
class IndicatorConfig:
    """Configuracoes dos indicadores tecnicos - APENAS 5m e 15m"""
    rsi_period: int = 14
    rsi_overbought: Dict[str, float] = None
    rsi_oversold: Dict[str, float] = None
    macd_fast: Dict[str, int] = None
    macd_slow: Dict[str, int] = None
    macd_signal: Dict[str, int] = None
    volume_ma_period: int = 20
    min_volume_ratio: Dict[str, float] = None

    def __post_init__(self):
        # APENAS 5m e 15m
        if self.rsi_overbought is None: self.rsi_overbought = {"5m": 72, "15m": 70}
        if self.rsi_oversold is None: self.rsi_oversold = {"5m": 28, "15m": 30}
        if self.macd_fast is None: self.macd_fast = {"5m": 10, "15m": 12}
        if self.macd_slow is None: self.macd_slow = {"5m": 22, "15m": 26}
        if self.macd_signal is None: self.macd_signal = {"5m": 8, "15m": 9}
        if self.min_volume_ratio is None: self.min_volume_ratio = {"5m": 1.5, "15m": 1.3}  # RELAXADO

@dataclass
class PatternConfig:
    """Configuracoes para deteccao de padroes SIMPLIFICADAS"""
    double_tolerance: float = 0.02
    double_min_distance: int = 15
    double_min_significance: float = 0.08
    min_pattern_strength: float = 0.60  # REDUZIDO de 0.65
    max_patterns_per_analysis: int = 2
    # ADICIONADO: Configurações de habilitação
    enable_head_shoulders: bool = False      # DESABILITADO
    enable_cup_handle: bool = False         # DESABILITADO  
    enable_double_patterns: bool = True     # HABILITADO

@dataclass
class SystemConfig:
    """Configuracoes do sistema OTIMIZADAS - APENAS 5m/15m"""
    multi_timeframe_enabled: bool = True
    analysis_interval: int = 300
    backup_all_signals: bool = True
    max_total_signals_per_symbol: int = 1
    log_level: str = "INFO"
    log_file: str = "trading_analyzer_optimized.log"
    parallel_analysis: bool = True
    max_workers: int = 4
    
    # ADICIONADO: Configurações de limpeza automática
    auto_cleanup_enabled: bool = True
    cleanup_interval_hours: int = 24      # ADICIONADO
    signal_lifecycle_hours: int = 48      # ADICIONADO
    
    live_data_timeframes: List[str] = field(default_factory=lambda: ["5m", "15m"])  
    live_data_enabled: bool = True
    
    def get_live_data_timeframes(self) -> List[str]:
        """Retorna timeframes que usam dados live"""
        if self.live_data_enabled:
            return self.live_data_timeframes
        else:
            return []

@dataclass
class ValidationConfig:
    """Configurações para a validação de sinais com microestrutura (Sniper) - CORRIGIDA."""
    
    enabled: bool = True
    # _#_NOVO_: Nome da tabela de microestrutura adicionado aqui.
    microstructure_table: str = "kline_microstructure_1m"
    validation_window_minutes: int = 5  # Quantos minutos olhar à frente na microestrutura.
    search_window_extend_minutes: int = 30  # NOVO: Janela de busca ampliada
    min_data_points_required: int = 3  # NOVO: Mínimo de pontos de dados
    momentum_period: int = 5            # Período para o RSI de momentum na microestrutura.
    buy_momentum_threshold: float = 50.0  # REDUZIDO de 55 para 50 (mais flexível)
    sell_momentum_threshold: float = 50.0 # ALTERADO de 45 para 50 (mais flexível)

class Settings:
    """Classe principal de configuracoes - CORRIGIDA PARA 5m/15m APENAS"""
    def __init__(self):
        self.database = DatabaseConfig()
        self.analysis = AnalysisConfig()
        self.indicators = IndicatorConfig()
        self.patterns = PatternConfig()
        self.system = SystemConfig()
        self.precisions = PrecisionConfig()
        self.validation = ValidationConfig()
        # 🔧 CORREÇÃO: Linha comentada para evitar erro
        # self.candlestick = CandlestickConfig()  # COMENTADO - classe não definida

    def get_timeframe_config(self, timeframe: str) -> TimeframeConfig:
        """CORRIGIDO: Fallback para 5m se timeframe não encontrado"""
        valid_timeframes = ["5m", "15m"]
        if timeframe not in valid_timeframes:
            timeframe = "5m"  # Fallback para 5m
        return self.analysis.multi_timeframe.timeframe_configs.get(timeframe, self.analysis.multi_timeframe.timeframe_configs["5m"])

    def get_enabled_timeframes(self) -> List[str]:
        """GARANTIDO: Retorna apenas 5m e 15m"""
        enabled = ["5m", "15m"]  # HARDCODED para evitar problemas
        if self.system.multi_timeframe_enabled:
            return enabled
        else:
            return [self.analysis.default_timeframe]  # "5m"

    def get_rsi_levels(self, timeframe: str) -> Dict[str, float]:
        """CORRIGIDO: Fallback para timeframes válidos"""
        if timeframe not in ["5m", "15m"]:
            timeframe = "5m"
        return {'overbought': self.indicators.rsi_overbought.get(timeframe, 70), 'oversold': self.indicators.rsi_oversold.get(timeframe, 30)}

    def get_macd_params(self, timeframe: str) -> Dict[str, int]:
        """CORRIGIDO: Fallback para timeframes válidos"""
        if timeframe not in ["5m", "15m"]:
            timeframe = "5m"
        return {'fast': self.indicators.macd_fast.get(timeframe, 12), 'slow': self.indicators.macd_slow.get(timeframe, 26), 'signal': self.indicators.macd_signal.get(timeframe, 9)}

    def get_analysis_symbols(self) -> List[str]:
        return self.analysis.symbols
    
    def get_price_precision(self, symbol: str) -> int:
        return self.precisions.symbol_price_precision.get(symbol, self.precisions.symbol_price_precision['DEFAULT'])

    # NOVO: Configurações para stop loss técnico (compatibilidade)
    def get_stop_target_config(self, timeframe: str) -> Dict:
        """Configurações para cálculo de stop loss e targets técnicos"""
        configs = {
            "5m": {
                "atr_period": 14,
                "stop_atr_multiplier": 1.8,
                "min_atr_mult": 1.2,
                "max_atr_mult": 2.5,
                "target_1_ratio": 1.5,
                "target_2_ratio": 3.0
            },
            "15m": {
                "atr_period": 14,
                "stop_atr_multiplier": 2.2,
                "min_atr_mult": 1.5,
                "max_atr_mult": 3.0,
                "target_1_ratio": 1.8,
                "target_2_ratio": 3.5
            }
        }
        
        if timeframe not in configs:
            timeframe = "5m"  # Fallback
        
        return configs[timeframe]

# _#_CORRIGIDO_: Instância única do settings
settings = Settings()