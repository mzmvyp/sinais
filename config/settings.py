"""
Configurações do Sistema de Análise Técnica - CORRIGIDO
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
    signals_table: str = "traiding_signals_v2"  # CORRIGIDO: era "trading_signals_v2"

@dataclass
class AnalysisConfig:
    """Configurações de análise"""
    default_timeframe: str = "5m"
    min_data_points: int = 50       # REDUZIDO: era 100, agora mais permissivo
    lookback_hours: int = 24        # Quantas horas olhar para trás
    confidence_threshold: float = 0.5  # REDUZIDO: era 0.6, agora mais permissivo para gerar mais sinais
    
    # Symbols para análise
    symbols: List[str] = None
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["BNB", "BTC", "ENA", "ETH", "HBAR", "NEAR", "OMNI", "SOL"]

@dataclass
class IndicatorConfig:
    """Configurações dos indicadores técnicos - AJUSTADO para gerar mais sinais"""
    # RSI - mais sensível
    rsi_period: int = 14
    rsi_overbought: float = 65      # REDUZIDO: era 70, agora mais sensível
    rsi_oversold: float = 35        # AUMENTADO: era 30, agora mais sensível
    rsi_divergence_lookback: int = 15  # REDUZIDO: era 20, mais ágil
    
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
    """Configurações para detecção de padrões - AJUSTADO"""
    # Cup & Handle - mais permissivo
    cup_min_depth: float = 0.10     # REDUZIDO: era 0.15, agora mais permissivo
    cup_max_depth: float = 0.50     
    cup_min_duration: int = 20      # REDUZIDO: era 30
    handle_max_retrace: float = 0.30 # AUMENTADO: era 0.25, mais permissivo
    
    # Double Top/Bottom - mais permissivo
    double_tolerance: float = 0.025  # AUMENTADO: era 0.015, mais permissivo
    double_min_distance: int = 10    # REDUZIDO: era 15
    double_min_significance: float = 0.05  # REDUZIDO: era 0.08, mais permissivo
    
    # Head & Shoulders - mais permissivo
    hs_shoulder_tolerance: float = 0.05  # AUMENTADO: era 0.03, mais permissivo
    hs_min_duration: int = 15            # REDUZIDO: era 20
    hs_min_head_prominence: float = 0.03 # REDUZIDO: era 0.05, mais permissivo
    
    # Triangles (para futuro)
    triangle_min_touches: int = 4
    triangle_min_duration: int = 15
    
    # Configurações gerais - mais permissivo
    min_pattern_strength: float = 0.4  # REDUZIDO: era 0.6, muito mais permissivo
    max_patterns_per_analysis: int = 10  # AUMENTADO: era 5, permite mais padrões

@dataclass
class SystemConfig:
    """Configurações do sistema"""
    analysis_interval: int = 300     # Executar a cada 5 minutos (segundos)
    max_signals_per_symbol: int = 10  # AUMENTADO: era 5, permite mais sinais
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
            print(f"[WARNING] Banco de sinais será criado em: {self.database.signals_db_path}")
            
        return stream_exists  # Só o stream é obrigatório, signals pode ser criado
    
    def get_analysis_symbols(self) -> List[str]:
        """Retorna lista de symbols para análise"""
        return self.analysis.symbols
    
    def update_symbol_list(self, symbols: List[str]):
        """Atualiza lista de symbols"""
        self.analysis.symbols = symbols
    
    def enable_debug_mode(self):
        """Ativa modo debug com configurações mais permissivas"""
        print("🔧 Ativando modo debug (configurações mais permissivas)")
        
        # Torna thresholds ainda mais permissivos
        self.analysis.confidence_threshold = 0.3
        self.analysis.min_data_points = 30
        
        # RSI mais sensível
        self.indicators.rsi_overbought = 60
        self.indicators.rsi_oversold = 40
        
        # Padrões mais permissivos
        self.patterns.min_pattern_strength = 0.3
        self.patterns.max_patterns_per_analysis = 15
        
        # Permite mais sinais
        self.system.max_signals_per_symbol = 20
        
        print("✅ Modo debug ativado - sistema muito mais permissivo")

# Instância global das configurações
settings = Settings()

# Funções auxiliares para diagnóstico
def get_current_settings_summary():
    """Retorna resumo das configurações atuais"""
    return {
        'database': {
            'stream_table': settings.database.stream_table,
            'signals_table': settings.database.signals_table,
            'stream_db_exists': os.path.exists(settings.database.stream_db_path),
            'signals_db_exists': os.path.exists(settings.database.signals_db_path),
        },
        'analysis': {
            'confidence_threshold': settings.analysis.confidence_threshold,
            'min_data_points': settings.analysis.min_data_points,
            'symbols_count': len(settings.analysis.symbols),
        },
        'indicators': {
            'rsi_levels': f"{settings.indicators.rsi_oversold}-{settings.indicators.rsi_overbought}",
        },
        'patterns': {
            'min_strength': settings.patterns.min_pattern_strength,
            'max_per_analysis': settings.patterns.max_patterns_per_analysis,
        }
    }

def apply_permissive_settings():
    """Aplica configurações muito permissivas para garantir geração de sinais"""
    global settings
    
    print("🔧 Aplicando configurações ultra-permissivas...")
    
    # Analysis - muito permissivo
    settings.analysis.confidence_threshold = 0.2  # Muito baixo
    settings.analysis.min_data_points = 20        # Muito baixo
    
    # RSI - faixa ampla
    settings.indicators.rsi_overbought = 55       # Muito sensível
    settings.indicators.rsi_oversold = 45         # Muito sensível
    
    # Padrões - aceita quase tudo
    settings.patterns.min_pattern_strength = 0.2
    settings.patterns.max_patterns_per_analysis = 20
    
    # Cup & Handle - muito permissivo
    settings.patterns.cup_min_depth = 0.05       # Qualquer correção
    settings.patterns.handle_max_retrace = 0.40  # Alça grande permitida
    
    # Double patterns - muito tolerante
    settings.patterns.double_tolerance = 0.04
    settings.patterns.double_min_significance = 0.03
    
    # Head & Shoulders - tolerante
    settings.patterns.hs_shoulder_tolerance = 0.08
    settings.patterns.hs_min_head_prominence = 0.02
    
    print("✅ Configurações ultra-permissivas aplicadas")
    print("   - Confidence threshold: 0.2")
    print("   - RSI levels: 45-55")
    print("   - Pattern strength mínima: 0.2")
    print("   - Máximo 20 padrões por análise")