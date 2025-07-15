"""
Configurações do Sistema de Análise Técnica
"""
import os
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class DatabaseConfig:
    """Configurações de banco de dados"""
    stream_db_path: str = r"C:\Users\mzmvy\Documents\python\trading_system\data\crypto_stream.db"
    signals_db_path: str = r"C:\Users\mzmvy\Documents\python\trading_system\data\trading_analyzer_v2.db"
    stream_table: str = "crypto_stream"
    signals_table: str = "traiding_signals_v2"

@dataclass
class AnalysisConfig:
    """Configurações de análise"""
    default_timeframe: str = "5m"
    min_data_points: int = 100  # Mínimo de pontos para análise
    lookback_hours: int = 24    # Quantas horas olhar para trás
    confidence_threshold: float = 0.6  # Confiança mínima para sinal
    
    # Symbols para análise
    symbols: List[str] = None
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["BNB", "BTC", "ENA", "ETH", "HBAR", "NEAR", "OMNI", "SOL"]

@dataclass
class IndicatorConfig:
    """Configurações dos indicadores técnicos"""
    # RSI
    rsi_period: int = 14
    rsi_overbought: float = 70
    rsi_oversold: float = 30
    rsi_divergence_lookback: int = 20
    
    # MACD
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # Bollinger Bands
    bb_period: int = 20
    bb_std: float = 2.0
    
    # Moving Averages
    ema_fast: int = 8
    ema_slow: int = 21
    sma_period: int = 50
    
    # Volume
    volume_ma_period: int = 20
    volume_spike_threshold: float = 2.0

@dataclass
class PatternConfig:
    """Configurações para detecção de padrões"""
    # Cup & Handle
    cup_min_depth: float = 0.15     # 15% mínimo de profundidade (era 10%)
    cup_max_depth: float = 0.50     # 50% máximo de profundidade
    cup_min_duration: int = 30      # Mínimo de barras (era 20)
    handle_max_retrace: float = 0.25 # 25% máximo do handle (era 33%)
    
    # Double Top/Bottom
    double_tolerance: float = 0.015  # 1.5% de tolerância (era 2%)
    double_min_distance: int = 15    # Distância mínima entre picos (era 10)
    double_min_significance: float = 0.08  # 8% mínimo de movimento entre pico/vale
    
    # Head & Shoulders
    hs_shoulder_tolerance: float = 0.03  # 3% tolerância ombros (era 5%)
    hs_min_duration: int = 20            # Mínimo de barras (era 15)
    hs_min_head_prominence: float = 0.05 # 5% mínimo que a cabeça deve sobressair
    
    # Triangles (para futuro)
    triangle_min_touches: int = 4    # Mínimo de toques nas linhas
    triangle_min_duration: int = 15
    
    # Configurações gerais
    min_pattern_strength: float = 0.6  # Força mínima para considerar padrão
    max_patterns_per_analysis: int = 5  # Máximo de padrões por análise

@dataclass
class SystemConfig:
    """Configurações do sistema"""
    analysis_interval: int = 300     # Executar a cada 5 minutos (segundos)
    max_signals_per_symbol: int = 5  # Máximo sinais ativos por symbol
    log_level: str = "INFO"
    log_file: str = "trading_analyzer.log"
    
    # Performance
    parallel_analysis: bool = True
    max_workers: int = 4

class Settings:
    """Classe principal de configurações"""
    
    def __init__(self):
        self.database = DatabaseConfig()
        self.analysis = AnalysisConfig()
        self.indicators = IndicatorConfig()
        self.patterns = PatternConfig()
        self.system = SystemConfig()
    
    def validate_paths(self) -> bool:
        """Valida se os caminhos dos bancos existem"""
        stream_exists = os.path.exists(self.database.stream_db_path)
        signals_exists = os.path.exists(self.database.signals_db_path)
        
        if not stream_exists:
            print(f"[ERROR] Banco de stream não encontrado: {self.database.stream_db_path}")
        
        if not signals_exists:
            print(f"[ERROR] Banco de sinais não encontrado: {self.database.signals_db_path}")
            
        return stream_exists and signals_exists
    
    def get_analysis_symbols(self) -> List[str]:
        """Retorna lista de symbols para análise"""
        return self.analysis.symbols
    
    def update_symbol_list(self, symbols: List[str]):
        """Atualiza lista de symbols"""
        self.analysis.symbols = symbols

# Instância global das configurações
settings = Settings()