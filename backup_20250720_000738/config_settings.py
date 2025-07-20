# -*- coding: utf-8 -*-
"""
Configuracoes Melhoradas do Sistema de Trading
Compativel com Windows
"""
import os
from dataclasses import dataclass
from typing import List

@dataclass
class DatabaseConfig:
    """Configuracoes de banco de dados"""
    stream_db_path: str = r"C:\Users\mzmvy\Documents\python\trading_system\data\crypto_stream.db"
    signals_db_path: str = r"C:\Users\mzmvy\Documents\python\trading_system\data\trading_analyzer_v2.db"
    stream_table: str = "crypto_stream"
    signals_table: str = "traiding_signals_v2"

@dataclass
class AnalysisConfig:
    """Configuracoes de analise"""
    default_timeframe: str = "15m"
    min_data_points: int = 50
    lookback_hours: int = 24
    confidence_threshold: float = 0.70  # CORRIGIDO: era 0.2
    symbols: List[str] = None
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["BNB", "BTC", "ENA", "ETH", "HBAR", "NEAR", "OMNI", "SOL","SUI","HYPE","PEPE","TURBO","IMX","CRV"]

@dataclass
class IndicatorConfig:
    """Configuracoes dos indicadores tecnicos"""
    # RSI - CORRIGIDO
    rsi_period: int = 14
    rsi_overbought: float = 70      # CORRIGIDO: era 58
    rsi_oversold: float = 30        # CORRIGIDO: era 42
    rsi_divergence_lookback: int = 20
    
    # MACD
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # Moving Averages
    ema_fast: int = 20
    ema_slow: int = 50
    sma_period: int = 50
    
    # Volume - NOVO
    volume_ma_period: int = 20
    volume_spike_threshold: float = 1.5
    min_volume_ratio: float = 1.5   # NOVO filtro

@dataclass
class PatternConfig:
    """Configuracoes para deteccao de padroes"""
    # CORRIGIDAS para serem menos permissivas
    cup_min_depth: float = 0.15         # era 0.05
    cup_max_depth: float = 0.40
    cup_min_duration: int = 30          # era 20
    handle_max_retrace: float = 0.25    # era 0.30
    
    double_tolerance: float = 0.02      # era 0.025
    double_min_distance: int = 15       # era 10
    double_min_significance: float = 0.08  # era 0.05
    
    hs_shoulder_tolerance: float = 0.03    # era 0.05
    hs_min_duration: int = 20              # era 15
    hs_min_head_prominence: float = 0.05   # era 0.03
    
    min_pattern_strength: float = 0.6     # era 0.2-0.4
    max_patterns_per_analysis: int = 5    # era 10-20

@dataclass
class SystemConfig:
    """Configuracoes do sistema"""
    analysis_interval: int = 300
    max_signals_per_symbol: int = 2     # era 5-20
    log_level: str = "INFO"
    log_file: str = "trading_analyzer.log"
    parallel_analysis: bool = True
    max_workers: int = 6

class Settings:
    """Classe principal de configuracoes"""
    
    def __init__(self):
        self.database = DatabaseConfig()
        self.analysis = AnalysisConfig()
        self.indicators = IndicatorConfig()
        self.patterns = PatternConfig()
        self.system = SystemConfig()
    
    def validate_paths(self) -> bool:
        """Valida se os caminhos dos bancos existem"""
        stream_exists = os.path.exists(self.database.stream_db_path)
        return stream_exists
    
    def get_analysis_symbols(self) -> List[str]:
        """Retorna lista de symbols para analise"""
        return self.analysis.symbols
    
    def update_symbol_list(self, symbols: List[str]):
        """Atualiza lista de symbols"""
        self.analysis.symbols = symbols

# Instancia global
settings = Settings()

# Funcoes auxiliares para compatibilidade
def get_current_settings_summary():
    return {
        'confidence_threshold': settings.analysis.confidence_threshold,
        'rsi_levels': f"{settings.indicators.rsi_oversold}-{settings.indicators.rsi_overbought}",
        'volume_min_ratio': settings.indicators.min_volume_ratio,
        'pattern_min_strength': settings.patterns.min_pattern_strength
    }

def apply_permissive_settings():
    """Modo mais permissivo"""
    settings.analysis.confidence_threshold = 0.55
    settings.indicators.rsi_overbought = 65
    settings.indicators.rsi_oversold = 35
    settings.indicators.min_volume_ratio = 1.2
    settings.patterns.min_pattern_strength = 0.5
    print("Configuracoes permissivas aplicadas")

# Compatibilidade com imports existentes
DatabaseConfig = DatabaseConfig
AnalysisConfig = AnalysisConfig
IndicatorConfig = IndicatorConfig
PatternConfig = PatternConfig
SystemConfig = SystemConfig
