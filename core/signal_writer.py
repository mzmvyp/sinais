# signal_writer.py - STOP LOSS TÉCNICO CORRIGIDO

"""
Signal Writer - VERSÃO COM STOP LOSS TÉCNICO (ATR) E APENAS 2 TARGETS
"""
import sqlite3
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import logging
import hashlib

from config.settings import settings

@dataclass
class EnhancedTradingSignal:
    """Estrutura de sinal com STOP LOSS TÉCNICO (ATR) e 2 TARGETS"""
    symbol: str
    signal_type: str
    entry_price: float
    confidence: float
    timeframe: str
    detector_type: str
    detector_name: str
    
    # Dados de mercado para cálculos técnicos
    market_data: Optional[pd.DataFrame] = None
    
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

        # PRINCIPAL MUDANÇA: Cálculo técnico de stop loss e targets
        if self.targets is None: 
            self.targets = self._calculate_technical_targets()
        if self.stop_loss is None: 
            self.stop_loss = self._calculate_technical_stop_loss()
        
        if self.indicators_used is None: 
            self.indicators_used = [f"{self.detector_name.lower()}_analyze"]
        if self.targets_hit is None: 
            self.targets_hit = [False] * len(self.targets)
        
        self._apply_precisions()
        self._validate_stop_loss()

    def _normalize_signal_type(self):
        if self.signal_type.upper() in ['BUY', 'BULLISH']: 
            self.signal_type = 'BUY_LONG'
        elif self.signal_type.upper() in ['SELL', 'BEARISH']: 
            self.signal_type = 'SELL_SHORT'

    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calcula ATR (Average True Range) para stop loss técnico"""
        try:
            if data is None or len(data) < period + 2:
                # Fallback: 1.5% do preço de entrada
                return self.entry_price * 0.015
            
            # Usa apenas dados fechados (exclui última vela)
            df = data.iloc[:-1].copy() if len(data) > 1 else data.copy()
            
            if len(df) < period:
                return self.entry_price * 0.015
            
            # Calcula True Range
            df['prev_close'] = df['close_price'].shift(1)
            df['tr1'] = df['high_price'] - df['low_price']
            df['tr2'] = abs(df['high_price'] - df['prev_close'])
            df['tr3'] = abs(df['low_price'] - df['prev_close'])
            
            df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
            
            # ATR usando média móvel exponencial
            atr = df['true_range'].ewm(span=period, adjust=False).mean().iloc[-1]
            
            # Validação: ATR deve estar entre 0.5% e 3% do preço
            min_atr = self.entry_price * 0.005  # 0.5%
            max_atr = self.entry_price * 0.03   # 3%
            
            atr = max(min_atr, min(max_atr, atr))
            
            return float(atr)
            
        except Exception as e:
            # Em caso de erro, usa 1.5% do preço
            return self.entry_price * 0.015

    
    def _calculate_technical_stop_loss(self):
        from core.technical_stop_loss import TechnicalStopLossCalculator
        
        calculator = TechnicalStopLossCalculator()
        result = calculator.calculate_intelligent_stop_loss(
            self.market_data, 
            self.signal_type, 
            self.entry_price, 
            self.timeframe
        )
        return result.recommended_stop
    
    def _calculate_fallback_stop_loss(self) -> float:
        """Stop loss de emergência se ATR falhar"""
        stop_percentage = 0.02  # 2% conservador
        
        if 'BUY' in self.signal_type:
            return self.entry_price * (1 - stop_percentage)
        else:
            return self.entry_price * (1 + stop_percentage)

    def _calculate_technical_targets(self) -> List[float]:
        """Calcula APENAS 2 targets técnicos baseados na relação risco/retorno"""
        try:
            # Calcula stop loss primeiro para determinar o risco
            temp_stop = self._calculate_technical_stop_loss()
            risk = abs(self.entry_price - temp_stop)
            
            # Obtém configurações do timeframe
            config = settings.get_stop_target_config(self.timeframe)
            
            if 'BUY' in self.signal_type:
                # Para LONG: targets acima do preço de entrada
                target_1 = self.entry_price + (risk * config['target_1_ratio'])
                target_2 = self.entry_price + (risk * config['target_2_ratio'])
            else:
                # Para SHORT: targets abaixo do preço de entrada
                target_1 = self.entry_price - (risk * config['target_1_ratio'])
                target_2 = self.entry_price - (risk * config['target_2_ratio'])
            
            # Validação: targets devem ser realistas
            max_target_distance = self.entry_price * 0.08  # Máximo 8% do preço
            
            if 'BUY' in self.signal_type:
                target_1 = min(target_1, self.entry_price + max_target_distance * 0.6)
                target_2 = min(target_2, self.entry_price + max_target_distance)
            else:
                target_1 = max(target_1, self.entry_price - max_target_distance * 0.6)
                target_2 = max(target_2, self.entry_price - max_target_distance)
            
            return [float(target_1), float(target_2)]
            
        except Exception as e:
            # Fallback: targets simples
            return self._calculate_fallback_targets()

    def _calculate_fallback_targets(self) -> List[float]:
        """Targets de emergência se cálculo técnico falhar"""
        if 'BUY' in self.signal_type:
            return [
                self.entry_price * 1.02,  # +2%
                self.entry_price * 1.04   # +4%
            ]
        else:
            return [
                self.entry_price * 0.98,  # -2%
                self.entry_price * 0.96   # -4%
            ]

    def _apply_precisions(self):
        """Aplica precisão de preços"""
        precision = settings.get_price_precision(self.symbol)
        self.entry_price = round(self.entry_price, precision)
        self.stop_loss = round(self.stop_loss, precision)
        self.targets = [round(t, precision) for t in self.targets]

    def _validate_stop_loss(self):
        """Valida se o stop loss está correto"""
        try:
            if 'BUY' in self.signal_type and self.stop_loss >= self.entry_price:
                # Stop para LONG deve ser menor que entrada
                self.stop_loss = self.entry_price * 0.98  # -2%
                logging.warning(f"Stop loss LONG corrigido para {self.symbol}: {self.stop_loss:.4f}")
                
            elif 'SELL' in self.signal_type and self.stop_loss <= self.entry_price:
                # Stop para SHORT deve ser maior que entrada
                self.stop_loss = self.entry_price * 1.02  # +2%
                logging.warning(f"Stop loss SHORT corrigido para {self.symbol}: {self.stop_loss:.4f}")
                
            # Verifica se stop não é muito distante (máximo 4%)
            stop_distance_pct = abs(self.stop_loss - self.entry_price) / self.entry_price
            if stop_distance_pct > 0.04:
                if 'BUY' in self.signal_type:
                    self.stop_loss = self.entry_price * 0.96  # -4%
                else:
                    self.stop_loss = self.entry_price * 1.04  # +4%
                logging.warning(f"Stop loss muito distante corrigido para {self.symbol}: {self.stop_loss:.4f}")
                
        except Exception as e:
            logging.error(f"Erro na validação do stop loss para {self.symbol}: {e}")
            # Stop de emergência
            if 'BUY' in self.signal_type:
                self.stop_loss = self.entry_price * 0.98
            else:
                self.stop_loss = self.entry_price * 1.02


class EnhancedSignalWriter:
    """Signal Writer com stop loss técnico e controle de sinais únicos"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db_path = settings.database.signals_db_path
        self.signals_table = settings.database.signals_table
        self.backup_table = settings.database.backup_table
        self._ensure_tables_exist()
        self.logger.info("EnhancedSignalWriter inicializado com stop loss técnico (ATR)")
        
    def _get_connection(self):
        return sqlite3.connect(self.db_path, timeout=10)

    def _ensure_tables_exist(self):
        """Garante que as tabelas existam"""
        pass
    
    def check_existing_active_signals(self, symbol: str) -> bool:
        """Verifica se já existe sinal ativo para o símbolo"""
        query = f"""
        SELECT COUNT(*) as count 
        FROM {self.signals_table} 
        WHERE symbol = ? AND status = 'ACTIVE'
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (symbol,))
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            self.logger.error(f"Erro ao verificar sinais ativos para {symbol}: {e}")
            return False

    def get_active_signals_count(self, symbol: str) -> int:
        """Retorna quantidade de sinais ativos para o símbolo"""
        query = f"""
        SELECT COUNT(*) as count 
        FROM {self.signals_table} 
        WHERE symbol = ? AND status = 'ACTIVE'
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (symbol,))
                return cursor.fetchone()[0]
        except Exception as e:
            self.logger.error(f"Erro ao contar sinais ativos para {symbol}: {e}")
            return 0

    def move_inactive_signals_to_backup(self) -> Dict[str, int]:
        """Move sinais inativos para backup (STOPPED, TARGET_2_HIT, KILLED)"""
        moved_counts = {'STOPPED': 0, 'TARGET_2_HIT': 0, 'KILLED': 0, 'EXPIRED': 0}
        
        # Estados que devem ser movidos para backup
        inactive_statuses = ['STOPPED', 'TARGET_2_HIT', 'KILLED', 'EXPIRED']
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                for status in inactive_statuses:
                    # Busca sinais com este status
                    select_query = f"""
                    SELECT * FROM {self.signals_table} 
                    WHERE status = ?
                    """
                    cursor.execute(select_query, (status,))
                    signals_to_move = cursor.fetchall()
                    
                    if signals_to_move:
                        # Move para backup
                        for signal in signals_to_move:
                            self._backup_signal_from_row(signal, f"moved_to_backup_{status.lower()}")
                        
                        # Remove da tabela principal
                        delete_query = f"""
                        DELETE FROM {self.signals_table} 
                        WHERE status = ?
                        """
                        cursor.execute(delete_query, (status,))
                        
                        moved_counts[status] = len(signals_to_move)
                        self.logger.info(f"Movidos {len(signals_to_move)} sinais {status} para backup")
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Erro ao mover sinais inativos para backup: {e}")
        
        return moved_counts
    
    def mark_expired_signals_as_killed(self) -> int:
        """Marca sinais antigos como KILLED baseado no lifecycle"""
        hours_limit = settings.system.signal_lifecycle_hours
        cutoff_time = datetime.now() - timedelta(hours=hours_limit)
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                update_query = f"""
                UPDATE {self.signals_table} 
                SET status = 'KILLED', updated_at = ?
                WHERE status = 'ACTIVE' AND created_at < ?
                """
                
                cursor.execute(update_query, (datetime.now().isoformat(), cutoff_time.isoformat()))
                killed_count = cursor.rowcount
                conn.commit()
                
                if killed_count > 0:
                    self.logger.info(f"🔪 {killed_count} sinais marcados como KILLED (lifecycle: {hours_limit}h)")
                
                return killed_count
                
        except Exception as e:
            self.logger.error(f"Erro ao marcar sinais como KILLED: {e}")
            return 0
    
    def _backup_signal_from_row(self, signal_row: tuple, reason: str):
        """Faz backup de um sinal a partir de uma row do banco"""
        sql = f"""
        INSERT INTO {self.backup_table} (
            original_id, symbol, signal_type, timeframe, detector_type, detector_name,
            signal_source, signal_hash, entry_price, confidence, confluence_score,
            status, created_at, backup_reason,
            targets, stop_loss, indicators_used, timeframe_analysis, market_conditions,
            pattern_data, technical_data, backup_timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self._get_connection() as conn:
                # Adapta os dados da row para o backup
                values = (
                    signal_row[0],  # id
                    signal_row[1],  # symbol
                    signal_row[2],  # signal_type
                    signal_row[3],  # timeframe
                    signal_row[4],  # detector_type
                    signal_row[5],  # detector_name
                    signal_row[6],  # signal_source
                    signal_row[7],  # signal_hash
                    signal_row[8],  # entry_price
                    signal_row[11], # confidence
                    signal_row[12], # confluence_score
                    signal_row[13], # status
                    signal_row[14], # created_at
                    reason,         # backup_reason
                    signal_row[9],  # targets
                    signal_row[10], # stop_loss
                    signal_row[18], # indicators_used
                    signal_row[20], # timeframe_analysis
                    signal_row[21], # market_conditions
                    signal_row[22], # pattern_data
                    signal_row[23], # technical_data
                    datetime.now().isoformat() # backup_timestamp
                )
                conn.execute(sql, values)
                conn.commit()
        except Exception as e:
            self.logger.error(f"Erro ao fazer backup da row: {e}")

    def _backup_signal(self, signal: EnhancedTradingSignal, reason: str):
        """Faz backup do sinal"""
        sql = f"""
        INSERT INTO {self.backup_table} (
            original_id, symbol, signal_type, timeframe, detector_type, detector_name,
            signal_source, signal_hash, entry_price, confidence, confluence_score,
            status, created_at, backup_reason,
            targets, stop_loss, indicators_used, timeframe_analysis, market_conditions,
            pattern_data, technical_data, backup_timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self._get_connection() as conn:
                values = (
                    signal.id, signal.symbol, signal.signal_type, signal.timeframe,
                    signal.detector_type, signal.detector_name, signal.signal_source,
                    signal.signal_hash, signal.entry_price, signal.confidence,
                    signal.confluence_score, signal.status,
                    signal.timestamp.isoformat(), reason,
                    json.dumps(signal.targets), signal.stop_loss,
                    json.dumps(signal.indicators_used),
                    json.dumps(signal.timeframe_analysis),
                    json.dumps(signal.market_conditions),
                    json.dumps(signal.pattern_data),
                    json.dumps(signal.technical_data),
                    datetime.now().isoformat()
                )
                conn.execute(sql, values)
                conn.commit()
        except Exception as e:
            self.logger.error(f"Erro ao fazer backup do sinal: {e}")

    def write_enhanced_signal(self, signal: EnhancedTradingSignal) -> bool:
        """Escreve sinal no banco APENAS se não houver sinal ativo para o símbolo"""
        
        # VERIFICAÇÃO CRÍTICA: Bloqueia se já há sinal ativo
        if self.check_existing_active_signals(signal.symbol):
            self.logger.info(f"🚫 Sinal BLOQUEADO para {signal.symbol}: Já existe sinal ativo")
            self._backup_signal(signal, "blocked_existing_active_signal")
            return False
        
        sql = f"""
        INSERT OR REPLACE INTO {self.signals_table} (
            id, symbol, signal_type, timeframe, detector_type, detector_name,
            signal_source, signal_hash, entry_price, targets, stop_loss,
            confidence, confluence_score, status, created_at, entry_time,
            current_price, targets_hit, indicators_used, updated_at,
            timeframe_analysis, market_conditions, pattern_data, technical_data
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            self._backup_signal(signal, "generated")

            with self._get_connection() as conn:
                values = (
                    signal.id, signal.symbol, signal.signal_type, signal.timeframe,
                    signal.detector_type, signal.detector_name, signal.signal_source,
                    signal.signal_hash, signal.entry_price, json.dumps(signal.targets),
                    signal.stop_loss, signal.confidence, signal.confluence_score,
                    signal.status, signal.timestamp.isoformat(), signal.timestamp.isoformat(),
                    signal.entry_price, json.dumps(signal.targets_hit),
                    json.dumps(signal.indicators_used), datetime.now().isoformat(),
                    json.dumps(signal.timeframe_analysis),
                    json.dumps(signal.market_conditions),
                    json.dumps(signal.pattern_data),
                    json.dumps(signal.technical_data)
                )
                conn.execute(sql, values)
                conn.commit()
            
            # Log com informações técnicas
            risk_pct = abs(signal.stop_loss - signal.entry_price) / signal.entry_price * 100
            target1_pct = abs(signal.targets[0] - signal.entry_price) / signal.entry_price * 100
            target2_pct = abs(signal.targets[1] - signal.entry_price) / signal.entry_price * 100
            
            self.logger.info(
                f"✅ SINAL TÉCNICO SALVO: {signal.symbol} {signal.timeframe} | "
                f"Entry: {signal.entry_price:.4f} | Stop: {signal.stop_loss:.4f} ({risk_pct:.1f}%) | "
                f"T1: {signal.targets[0]:.4f} ({target1_pct:.1f}%) | "
                f"T2: {signal.targets[1]:.4f} ({target2_pct:.1f}%)"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao gravar sinal técnico: {e}")
            self._backup_signal(signal, f"insert_error: {e}")
            return False

# Apelidos para compatibilidade
TradingSignal = EnhancedTradingSignal
SignalWriter = EnhancedSignalWriter