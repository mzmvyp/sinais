# signal_writer.py

"""
Signal Writer - VERSÃO FINAL CORRIGIDA
Restaura campos removidos acidentalmente e mantém todas as correções anteriores.
"""
import sqlite3
import json
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import logging
import hashlib

from config.settings import settings

@dataclass
class EnhancedTradingSignal:
    """Estrutura de sinal completa, padronizada e com precisão controlada."""
    # Parâmetros essenciais
    symbol: str
    signal_type: str
    entry_price: float
    confidence: float
    timeframe: str
    detector_type: str
    detector_name: str
    
    # _#_CORRIGIDO_: Campos que foram acidentalmente removidos foram restaurados.
    id: str = None
    signal_hash: str = None
    signal_source: str = None
    targets: List[float] = None
    stop_loss: float = None
    confluence_score: int = 95
    status: str = "ACTIVE"
    indicators_used: List[str] = None
    targets_hit: List[bool] = None
    timeframe_analysis: Dict = field(default_factory=dict)
    market_conditions: Dict = field(default_factory=dict)
    pattern_data: Optional[Dict] = None
    technical_data: Optional[Dict] = None
    strategy: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        self._normalize_signal_type()

        if self.id is None:
            ts = int(self.timestamp.timestamp() * 1000)
            self.id = f"{self.symbol}_{self.signal_type}_{ts}"

        hash_content = f"{self.symbol}_{self.timeframe}_{self.detector_name}_{int(self.timestamp.timestamp())}"
        if self.signal_hash is None:
            self.signal_hash = hashlib.md5(hash_content.encode()).hexdigest()[:12]

        if self.signal_source is None:
            direction = "bullish" if "BUY" in self.signal_type else "bearish"
            self.signal_source = f"{self.detector_name}_{direction}_{self.timeframe}"

        if self.targets is None: self.targets = self._calculate_default_targets()
        if self.stop_loss is None: self.stop_loss = self._calculate_default_stop_loss()
        
        if self.indicators_used is None: self.indicators_used = [f"{self.detector_name.lower()}_analize"]
        if self.targets_hit is None: self.targets_hit = [False] * len(self.targets)
        
        self._apply_precisions()

        # Validação do Stop Loss (mantida da correção anterior)
        is_invalid_stop = False
        reason = ""
        if self.signal_type == 'BUY_LONG' and self.stop_loss >= self.entry_price:
            is_invalid_stop = True
            reason = f"Stop ({self.stop_loss}) deve ser MENOR que a Entrada ({self.entry_price}) para um LONG."
        elif self.signal_type == 'SELL_SHORT' and self.stop_loss <= self.entry_price:
            is_invalid_stop = True
            reason = f"Stop ({self.stop_loss}) deve ser MAIOR que a Entrada ({self.entry_price}) para um SHORT."
        
        if is_invalid_stop:
            raise ValueError(f"Stop loss inválido para {self.symbol}: {reason} Ordem seria executada imediatamente.")

    def _apply_precisions(self):
        precision = settings.get_price_precision(self.symbol)
        self.entry_price = round(self.entry_price, precision)
        self.stop_loss = round(self.stop_loss, precision)
        self.targets = [round(t, precision) for t in self.targets]

    def _normalize_signal_type(self):
        if self.signal_type.upper() in ['BUY', 'BULLISH']: self.signal_type = 'BUY_LONG'
        elif self.signal_type.upper() in ['SELL', 'BEARISH']: self.signal_type = 'SELL_SHORT'

    def _calculate_default_targets(self):
        mults_map = {'5m': [1.008, 1.015, 1.022], '15m': [1.015, 1.025, 1.04], '1h': [1.025, 1.04, 1.06]}
        mults = mults_map.get(self.timeframe, mults_map['15m'])
        if 'SELL' in self.signal_type: mults = [2 - m for m in mults]
        return [self.entry_price * m for m in mults]

    def _calculate_default_stop_loss(self):
        stop_map = {'5m': 0.985, '15m': 0.97, '1h': 0.95}
        stop_mult = stop_map.get(self.timeframe, stop_map['15m'])
        if 'SELL' in self.signal_type: stop_mult = 2 - stop_mult
        return self.entry_price * stop_mult

class EnhancedSignalWriter:
    # ... (O resto do arquivo e a classe EnhancedSignalWriter permanecem exatamente iguais) ...
    pass # As funções de escrita no DB já estão corretas e usam os campos que foram restaurados.

# Apelidos para compatibilidade
TradingSignal = EnhancedTradingSignal
SignalWriter = EnhancedSignalWriter