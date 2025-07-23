# signal_writer.py - LÓGICA CORRIGIDA - 2 TARGETS APENAS

"""
Signal Writer - CORREÇÃO DA LÓGICA: 2 targets apenas
- BLOQUEAR: ACTIVE ou TARGET_HIT com targets_hit=[true,false]  
- PERMITIR: STOP_HIT ou TARGET_HIT com targets_hit=[true,true]
"""
import sqlite3
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
import logging
import hashlib

from config.settings import settings

@dataclass
class EnhancedTradingSignal:
    """Estrutura de sinal com INTEGRAÇÃO TÉCNICA CORRETA"""
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
    
    # 🚨 INTEGRAÇÃO CORRIGIDA: Análises técnicas
    stop_loss_analysis: Optional[Dict] = None
    targets_analysis: Optional[Dict] = None

    def __post_init__(self):
        # 🚨 CORREÇÃO: Inicializa logger
        self.logger = logging.getLogger(__name__)
        
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

        # 🚨 INTEGRAÇÃO CORRIGIDA: Cálculo técnico completo
        if self.stop_loss is None: 
            self.stop_loss, self.stop_loss_analysis = self._calculate_technical_stop_loss_integrated()
        if self.targets is None: 
            self.targets, self.targets_analysis = self._calculate_technical_targets_integrated()
        
        if self.indicators_used is None: 
            self.indicators_used = [f"{self.detector_name.lower()}_analyze"]
        if self.targets_hit is None: 
            self.targets_hit = [False, False]  # 🚨 CORRIGIDO: Apenas 2 targets
        
        self._apply_precisions()
        self._validate_stop_and_targets()

    def _normalize_signal_type(self):
        if self.signal_type.upper() in ['BUY', 'BULLISH']: 
            self.signal_type = 'BUY_LONG'
        elif self.signal_type.upper() in ['SELL', 'BEARISH']: 
            self.signal_type = 'SELL_SHORT'

    def _calculate_technical_stop_loss_integrated(self) -> tuple[float, Dict]:
        """🚨 INTEGRAÇÃO CORRIGIDA com technical_stop_loss.py"""
        try:
            from core.technical_stop_loss import TechnicalStopLossCalculator
            from core.data_reader import MarketData
            
            calculator = TechnicalStopLossCalculator()
            
            # Cria MarketData object se necessário
            if isinstance(self.market_data, pd.DataFrame):
                market_data_obj = MarketData(
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    data=self.market_data,
                    last_update=datetime.now()
                )
            else:
                # Fallback se não há dados
                return self._calculate_fallback_stop_loss(), {
                    'method_used': 'Fallback_No_Data',
                    'confidence': 0.3,
                    'risk_percentage': 2.0,
                    'atr_value': 0,
                    'analysis_details': {'error': 'No market data available'}
                }
            
            # 🚨 CHAMA O SISTEMA TÉCNICO
            stop_result = calculator.calculate_intelligent_stop_loss(
                market_data_obj, 
                self.signal_type, 
                self.entry_price, 
                self.timeframe
            )
            
            # 🚨 CONVERTE StopLossAnalysis PARA DICT (compatível com JSON)
            analysis_dict = {
                'method_used': stop_result.method_used,
                'confidence': stop_result.confidence,
                'risk_percentage': stop_result.risk_percentage,
                'atr_value': stop_result.atr_value,
                'nearest_support_resistance': stop_result.nearest_support_resistance,
                'analysis_details': stop_result.analysis_details
            }
            
            self.logger.debug(f"Stop loss técnico calculado: {stop_result.method_used} para {self.symbol}")
            return stop_result.recommended_stop, analysis_dict
            
        except Exception as e:
            self.logger.error(f"Erro no cálculo técnico de stop loss para {self.symbol}: {e}")
            return self._calculate_fallback_stop_loss(), {
                'method_used': 'Error_Fallback',
                'confidence': 0.2,
                'error': str(e),
                'risk_percentage': 2.0,
                'atr_value': 0,
                'analysis_details': {'error': str(e)}
            }
    
    def _calculate_technical_targets_integrated(self) -> tuple[List[float], Dict]:
        """🚨 INTEGRAÇÃO COM SISTEMA TÉCNICO DE TARGETS - 2 TARGETS"""
        try:
            from core.technical_targets import TechnicalTargetsCalculator
            from core.data_reader import MarketData
            
            calculator = TechnicalTargetsCalculator()
            
            # Cria MarketData object se necessário
            if isinstance(self.market_data, pd.DataFrame):
                market_data_obj = MarketData(
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    data=self.market_data,
                    last_update=datetime.now()
                )
            else:
                return self._calculate_fallback_targets(), {
                    'method_used': 'Fallback_No_Data',
                    'confidence': 0.3,
                    'analysis_details': {'error': 'No market data available'}
                }
            
            # Calcula targets técnicos (precisa do stop loss para calcular risco)
            temp_stop = self.stop_loss if self.stop_loss else self._calculate_fallback_stop_loss()
            
            # 🚨 CHAMA O SISTEMA TÉCNICO DE TARGETS
            targets_result = calculator.calculate_intelligent_targets(
                market_data_obj,
                self.signal_type,
                self.entry_price,
                temp_stop,
                self.timeframe
            )
            
            # 🚨 GARANTE APENAS 2 TARGETS
            final_targets = targets_result.targets[:2] if len(targets_result.targets) >= 2 else targets_result.targets
            if len(final_targets) < 2:
                final_targets = self._calculate_fallback_targets()
            
            # 🚨 CONVERTE TargetsAnalysis PARA DICT (compatível com JSON)
            analysis_dict = {
                'method_used': targets_result.method_used,
                'confidence': targets_result.confidence,
                'target_levels': targets_result.target_levels[:2] if targets_result.target_levels else [],
                'resistance_levels': targets_result.resistance_levels,
                'support_levels': targets_result.support_levels,
                'risk_reward_ratios': targets_result.risk_reward_ratios[:2] if targets_result.risk_reward_ratios else [],
                'analysis_details': targets_result.analysis_details
            }
            
            self.logger.debug(f"Targets técnicos calculados: {targets_result.method_used} para {self.symbol} (2 targets)")
            return final_targets, analysis_dict
            
        except ImportError:
            # Fallback se o sistema de targets não existe ainda
            self.logger.warning("Sistema técnico de targets não disponível, usando fallback")
            return self._calculate_simple_technical_targets(), {
                'method_used': 'Simple_Technical_Fallback',
                'confidence': 0.5,
                'analysis_details': {'note': 'Technical targets system not available'}
            }
        except Exception as e:
            self.logger.error(f"Erro no cálculo técnico de targets para {self.symbol}: {e}")
            return self._calculate_fallback_targets(), {
                'method_used': 'Error_Fallback',
                'confidence': 0.2,
                'error': str(e),
                'analysis_details': {'error': str(e)}
            }

    def _calculate_simple_technical_targets(self) -> List[float]:
        """Targets técnicos simples baseados em ATR e estrutura - 2 TARGETS"""
        try:
            if self.market_data is None or len(self.market_data) < 20:
                return self._calculate_fallback_targets()
            
            # Calcula ATR para targets
            atr = self._calculate_atr(self.market_data, 14)
            
            # Encontra resistências/suportes próximos
            resistance_levels, support_levels = self._find_nearby_levels(self.market_data)
            
            if 'BUY' in self.signal_type:
                # Para LONG: busca resistências acima como targets
                valid_resistances = [r for r in resistance_levels if r > self.entry_price]
                if len(valid_resistances) >= 2:
                    targets = sorted(valid_resistances)[:2]
                else:
                    targets = [
                        self.entry_price + atr * 2.0,  # Target 1: 2x ATR
                        self.entry_price + atr * 3.5   # Target 2: 3.5x ATR
                    ]
            else:
                # Para SHORT: busca suportes abaixo como targets
                valid_supports = [s for s in support_levels if s < self.entry_price]
                if len(valid_supports) >= 2:
                    targets = sorted(valid_supports, reverse=True)[:2]
                else:
                    targets = [
                        self.entry_price - atr * 2.0,  # Target 1: 2x ATR
                        self.entry_price - atr * 3.5   # Target 2: 3.5x ATR
                    ]
            
            return targets
            
        except Exception as e:
            self.logger.warning(f"Erro no cálculo simples de targets técnicos: {e}")
            return self._calculate_fallback_targets()

    def _find_nearby_levels(self, df: pd.DataFrame) -> tuple[List[float], List[float]]:
        """Encontra níveis de suporte e resistência próximos"""
        try:
            # Pega últimas 50 barras para análise
            recent_data = df.tail(50)
            
            # Encontra picos e vales
            highs = recent_data['high_price']
            lows = recent_data['low_price']
            
            # Resistências (picos locais)
            resistance_levels = []
            for i in range(2, len(highs) - 2):
                if (highs.iloc[i] > highs.iloc[i-1] and highs.iloc[i] > highs.iloc[i-2] and
                    highs.iloc[i] > highs.iloc[i+1] and highs.iloc[i] > highs.iloc[i+2]):
                    resistance_levels.append(highs.iloc[i])
            
            # Suportes (vales locais)
            support_levels = []
            for i in range(2, len(lows) - 2):
                if (lows.iloc[i] < lows.iloc[i-1] and lows.iloc[i] < lows.iloc[i-2] and
                    lows.iloc[i] < lows.iloc[i+1] and lows.iloc[i] < lows.iloc[i+2]):
                    support_levels.append(lows.iloc[i])
            
            return resistance_levels, support_levels
            
        except Exception as e:
            self.logger.warning(f"Erro na busca de níveis S/R: {e}")
            return [], []

    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calcula ATR (Average True Range) - COM DEBUG"""
        try:
            if data is None or len(data) < period + 2:
                fallback_atr = self.entry_price * 0.015
                print(f"🔧 ATR fallback usado: {fallback_atr:.4f} (dados insuficientes)")
                return fallback_atr
            
            df = data.iloc[:-1].copy() if len(data) > 1 else data.copy()
            
            if len(df) < period:
                fallback_atr = self.entry_price * 0.015
                print(f"🔧 ATR fallback usado: {fallback_atr:.4f} (período insuficiente)")
                return fallback_atr
            
            # Calcula True Range
            df['prev_close'] = df['close_price'].shift(1)
            df['tr1'] = df['high_price'] - df['low_price']
            df['tr2'] = abs(df['high_price'] - df['prev_close'])
            df['tr3'] = abs(df['low_price'] - df['prev_close'])
            
            df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
            atr = df['true_range'].ewm(span=period, adjust=False).mean().iloc[-1]
            
            # Validação
            min_atr = self.entry_price * 0.005
            max_atr = self.entry_price * 0.03
            atr_final = max(min_atr, min(max_atr, atr)) if pd.notna(atr) and atr > 0 else self.entry_price * 0.015
            
            print(f"🔧 ATR calculado: {atr_final:.4f} para {self.symbol} (entry: {self.entry_price:.4f})")
            return float(atr_final)
            
        except Exception as e:
            fallback_atr = self.entry_price * 0.015
            print(f"🔧 ATR ERRO, usando fallback: {fallback_atr:.4f} - {e}")
            return fallback_atr
    
    def _calculate_fallback_stop_loss(self) -> float:
        """Stop loss de emergência - CORRIGIDO"""
        stop_percentage = 0.02  # 2% conservador
        
        if 'BUY' in self.signal_type:
            # Para LONG: stop deve ser MENOR que entry (subtrai)
            return self.entry_price * (1 - stop_percentage)  # entry * 0.98
        else:
            # Para SHORT: stop deve ser MAIOR que entry (soma)
            return self.entry_price * (1 + stop_percentage)  # entry * 1.02

    def _calculate_fallback_targets(self) -> List[float]:
        """Targets de emergência - APENAS 2"""
        if 'BUY' in self.signal_type:
            return [
                self.entry_price * 1.02,  # Target 1: +2%
                self.entry_price * 1.04   # Target 2: +4%
            ]
        else:
            return [
                self.entry_price * 0.98,  # Target 1: -2%
                self.entry_price * 0.96   # Target 2: -4%
            ]

    def _apply_precisions(self):
        """Aplica precisão de preços"""
        precision = settings.get_price_precision(self.symbol)
        self.entry_price = round(self.entry_price, precision)
        self.stop_loss = round(self.stop_loss, precision)
        self.targets = [round(t, precision) for t in self.targets]

    def _validate_stop_and_targets(self):
        """Valida stop loss e targets - CORRIGIDO"""
        try:
            # VALIDAÇÃO 1: Direção correta do stop loss
            if 'BUY' in self.signal_type:
                if self.stop_loss >= self.entry_price:
                    # Para LONG: stop deve ser MENOR que entry
                    self.stop_loss = self.entry_price * 0.985  # 1.5% abaixo
                    self.logger.warning(f"🔧 Stop loss LONG corrigido para {self.symbol}: {self.stop_loss:.4f} (era >= entry)")
            
            elif 'SELL' in self.signal_type:
                if self.stop_loss <= self.entry_price:
                    # Para SHORT: stop deve ser MAIOR que entry  
                    self.stop_loss = self.entry_price * 1.015  # 1.5% acima
                    self.logger.warning(f"🔧 Stop loss SHORT corrigido para {self.symbol}: {self.stop_loss:.4f} (era <= entry)")
            
            # VALIDAÇÃO 2: Garante apenas 2 targets
            if len(self.targets) > 2:
                self.targets = self.targets[:2]
                self.logger.debug(f"🎯 Limitado a 2 targets para {self.symbol}")
            elif len(self.targets) < 2:
                self.targets = self._calculate_fallback_targets()
                self.logger.warning(f"🎯 Targets insuficientes para {self.symbol}, calculados automaticamente")
            
            # VALIDAÇÃO 3: Targets na direção correta
            for i, target in enumerate(self.targets):
                if 'BUY' in self.signal_type:
                    if target <= self.entry_price:
                        self.targets[i] = self.entry_price * (1.02 + i * 0.02)  # 2%, 4%
                        self.logger.warning(f"🎯 Target {i+1} LONG corrigido: {self.targets[i]:.4f}")
                else:  # SELL
                    if target >= self.entry_price:
                        self.targets[i] = self.entry_price * (0.98 - i * 0.02)  # -2%, -4%
                        self.logger.warning(f"🎯 Target {i+1} SHORT corrigido: {self.targets[i]:.4f}")
            
            # VALIDAÇÃO 4: Ordem dos targets
            if 'BUY' in self.signal_type:
                self.targets.sort()  # Crescente para LONG
            else:
                self.targets.sort(reverse=True)  # Decrescente para SHORT
                
        except Exception as e:
            self.logger.error(f"❌ Erro na validação de stop/targets para {self.symbol}: {e}")

class EnhancedSignalWriter:
    """Signal Writer LÓGICA CORRIGIDA - 2 targets apenas"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db_path = settings.database.signals_db_path
        self.signals_table = settings.database.signals_table
        self.backup_table = settings.database.backup_table
        self._ensure_tables_exist()
        self.logger.info("EnhancedSignalWriter LÓGICA CORRIGIDA - 2 targets apenas")
        
    def _get_connection(self):
        return sqlite3.connect(self.db_path, timeout=10)

    def _ensure_tables_exist(self):
        """Garante que as tabelas existam com colunas para análises técnicas"""
        create_signals_table = f"""
        CREATE TABLE IF NOT EXISTS {self.signals_table} (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            detector_type TEXT NOT NULL,
            detector_name TEXT NOT NULL,
            signal_source TEXT,
            signal_hash TEXT,
            entry_price REAL NOT NULL,
            targets TEXT,
            stop_loss REAL NOT NULL,
            confidence REAL NOT NULL,
            confluence_score INTEGER DEFAULT 95,
            status TEXT DEFAULT 'ACTIVE',
            created_at TEXT NOT NULL,
            entry_time TEXT,
            current_price REAL,
            targets_hit TEXT,
            indicators_used TEXT,
            updated_at TEXT,
            timeframe_analysis TEXT,
            market_conditions TEXT,
            pattern_data TEXT,
            technical_data TEXT,
            stop_loss_analysis TEXT,
            targets_analysis TEXT
        )
        """
        
        create_backup_table = f"""
        CREATE TABLE IF NOT EXISTS {self.backup_table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_id TEXT,
            symbol TEXT,
            signal_type TEXT,
            timeframe TEXT,
            detector_type TEXT,
            detector_name TEXT,
            signal_source TEXT,
            signal_hash TEXT,
            entry_price REAL,
            confidence REAL,
            confluence_score INTEGER,
            status TEXT,
            created_at TEXT,
            backup_reason TEXT,
            targets TEXT,
            stop_loss REAL,
            indicators_used TEXT,
            timeframe_analysis TEXT,
            market_conditions TEXT,
            pattern_data TEXT,
            technical_data TEXT,
            stop_loss_analysis TEXT,
            targets_analysis TEXT,
            backup_timestamp TEXT
        )
        """
        
        try:
            with self._get_connection() as conn:
                conn.execute(create_signals_table)
                conn.execute(create_backup_table)
                conn.commit()
                self.logger.debug("Tabelas verificadas/criadas com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao criar tabelas: {e}")
    
   
    def check_existing_active_signals(self, symbol: str) -> bool:
        """
        CORRIGIDO: Verifica se há sinal que bloqueia novos sinais
        
        BLOQUEAR quando:
        - Status = ACTIVE (nenhum target atingido)
        - Status = TARGET_1_HIT (só primeiro target)
        
        PERMITIR quando:
        - Status = TARGET_2_HIT (ambos targets atingidos)
        - Status = STOP_HIT (stop loss atingido)
        - Status = EXPIRED ou MANUALLY_CLOSED
        """
        query = f"""
        SELECT id, status, targets_hit, created_at 
        FROM {self.signals_table} 
        WHERE symbol = ? AND status IN ('ACTIVE', 'TARGET_1_HIT')
        ORDER BY created_at DESC
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (symbol,))
                signals = cursor.fetchall()
                
                blocking_signals = []
                
                for signal in signals:
                    signal_id, status, targets_hit_str, created_at = signal
                    
                    # Parse targets_hit
                    try:
                        targets_hit = json.loads(targets_hit_str) if targets_hit_str else [False, False]
                    except:
                        targets_hit = [False, False]
                    
                    # LÓGICA CORRIGIDA:
                    should_block = False
                    
                    if status == 'ACTIVE':
                        should_block = True
                        reason = "ACTIVE (aguardando resultado)"
                        
                    elif status == 'TARGET_1_HIT':
                        should_block = True  # TARGET_1_HIT ainda bloqueia
                        reason = "TARGET_1_HIT (ainda ativo)"
                    
                    if should_block:
                        blocking_signals.append((signal_id, status, targets_hit, reason))
                        self.logger.debug(f"🚫 BLOQUEIO para {symbol}: {signal_id} | Status: {status} | Motivo: {reason}")
                
                has_blocking = len(blocking_signals) > 0
                if has_blocking:
                    self.logger.info(f"🚫 {symbol} BLOQUEADO: {len(blocking_signals)} sinal(s) ativo(s)")
                
                return has_blocking
                    
        except Exception as e:
            self.logger.error(f"Erro ao verificar sinais bloqueadores para {symbol}: {e}")
            return False
   
   
    def write_enhanced_signal(self, signal: EnhancedTradingSignal) -> bool:
        """Escreve sinal no banco com LÓGICA CORRIGIDA"""
        
        # 🚨 NOVO: Verificação de Sinal Obsoleto
        if signal.signal_type == 'BUY_LONG' and signal.entry_price >= signal.targets[0]:
            self.logger.warning(f"🚫 Sinal OBsoleto para {signal.symbol}: Preço de entrada ({signal.entry_price}) maior ou igual ao alvo 1 ({signal.targets[0]})")
            self._backup_signal(signal, "blocked_stale_signal_entry_too_high")
            return False
        elif signal.signal_type == 'SELL_SHORT' and signal.entry_price <= signal.targets[0]:
            self.logger.warning(f"🚫 Sinal OBsoleto para {signal.symbol}: Preço de entrada ({signal.entry_price}) menor ou igual ao alvo 1 ({signal.targets[0]})")
            self._backup_signal(signal, "blocked_stale_signal_entry_too_low")
            return False
        
        # VERIFICAÇÃO CRÍTICA COM LÓGICA CORRIGIDA
        if self.check_existing_active_signals(signal.symbol):
            self.logger.info(f"🚫 SINAL BLOQUEADO para {signal.symbol}: Existe sinal ativo ou TARGET_HIT parcial")
            self._backup_signal(signal, "blocked_existing_active_signal")
            return False
        
        # 🚨 LOG DE DEBUG PARA ENTENDER O QUE ESTÁ ACONTECENDO
        self.logger.info(f"🔍 TENTANDO GRAVAR: {signal.symbol} | Status será: {signal.status}")

        # Verifica se já existe sinal ativo (log detalhado)
        existing_check = self.check_existing_active_signals(signal.symbol)
        if existing_check:
            self.logger.warning(f"⚠️ ATENÇÃO: {signal.symbol} tem sinal ativo, mas prosseguindo com gravação")
                
        sql = f"""
        INSERT OR REPLACE INTO {self.signals_table} (
            id, symbol, signal_type, timeframe, detector_type, detector_name,
            signal_source, signal_hash, entry_price, targets, stop_loss,
            confidence, confluence_score, status, created_at, entry_time,
            current_price, targets_hit, indicators_used, updated_at,
            timeframe_analysis, market_conditions, pattern_data, technical_data,
            stop_loss_analysis, targets_analysis
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    json.dumps(signal.technical_data),
                    json.dumps(signal.stop_loss_analysis),
                    json.dumps(signal.targets_analysis)
                )
                conn.execute(sql, values)
                conn.commit()
            
            # Log com informações técnicas detalhadas - 2 TARGETS
            risk_pct = abs(signal.stop_loss - signal.entry_price) / signal.entry_price * 100
            target1_pct = abs(signal.targets[0] - signal.entry_price) / signal.entry_price * 100
            target2_pct = abs(signal.targets[1] - signal.entry_price) / signal.entry_price * 100
            
            stop_method = signal.stop_loss_analysis.get('method_used', 'Unknown') if signal.stop_loss_analysis else 'Unknown'
            targets_method = signal.targets_analysis.get('method_used', 'Unknown') if signal.targets_analysis else 'Unknown'
            
            self.logger.info(
                f"✅ SINAL 2-TARGETS: {signal.symbol} {signal.timeframe} | "
                f"Entry: {signal.entry_price:.4f} | "
                f"Stop: {signal.stop_loss:.4f} ({risk_pct:.1f}%) [{stop_method}] | "
                f"T1: {signal.targets[0]:.4f} ({target1_pct:.1f}%) | "
                f"T2: {signal.targets[1]:.4f} ({target2_pct:.1f}%) [{targets_method}]"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao gravar sinal: {e}")
            self._backup_signal(signal, f"insert_error: {e}")
            return False

    def get_active_signals_count(self, symbol: str) -> int:
        """
        LÓGICA CORRIGIDA: Conta sinais que REALMENTE bloqueiam novos sinais
        """
        query = f"""
        SELECT status, targets_hit 
        FROM {self.signals_table} 
        WHERE symbol = ? AND status IN ('ACTIVE', 'TARGET_HIT')
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (symbol,))
                signals = cursor.fetchall()
                
                blocking_count = 0
                
                for status, targets_hit_str in signals:
                    try:
                        targets_hit = json.loads(targets_hit_str) if targets_hit_str else [False, False]
                    except:
                        targets_hit = [False, False]
                    
                    # Aplica a mesma lógica de bloqueio
                    if status == 'ACTIVE':
                        blocking_count += 1
                    elif status == 'TARGET_HIT':
                        if len(targets_hit) >= 2 and targets_hit[0] and not targets_hit[1]:
                            blocking_count += 1  # Apenas primeiro target atingido - ainda bloqueia
                        # Se targets_hit = [true, true], não conta (sinal finalizado)
                
                return blocking_count
                
        except Exception as e:
            self.logger.error(f"Erro ao contar sinais bloqueadores para {symbol}: {e}")
            return 0

    def move_inactive_signals_to_backup(self) -> Dict[str, int]:
        """Move sinais REALMENTE finalizados para backup"""
        moved_counts = {'STOP_HIT': 0, 'TARGET_2_COMPLETE': 0, 'EXPIRED': 0, 'MANUALLY_CLOSED': 0}
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Move sinais com STOP_HIT (sempre finalizados)
                final_statuses = ['STOP_HIT', 'EXPIRED', 'MANUALLY_CLOSED']
                
                for status in final_statuses:
                    select_query = f"""
                    SELECT * FROM {self.signals_table} 
                    WHERE status = ?
                    """
                    cursor.execute(select_query, (status,))
                    signals_to_move = cursor.fetchall()
                    
                    if signals_to_move:
                        for signal in signals_to_move:
                            self._backup_signal_from_row(signal, f"moved_to_backup_{status.lower()}")
                        
                        delete_query = f"""
                        DELETE FROM {self.signals_table} 
                        WHERE status = ?
                        """
                        cursor.execute(delete_query, (status,))
                        
                        moved_counts[status] = len(signals_to_move)
                        self.logger.info(f"Movidos {len(signals_to_move)} sinais {status} para backup")
                
                # 2. Move sinais TARGET_HIT com ambos targets atingidos
                cursor.execute(f"""
                    SELECT * FROM {self.signals_table} 
                    WHERE status = 'TARGET_HIT'
                """)
                target_hit_signals = cursor.fetchall()
                
                target_2_complete_count = 0
                
                for signal in target_hit_signals:
                    try:
                        targets_hit_str = signal[17]  # índice da coluna targets_hit
                        targets_hit = json.loads(targets_hit_str) if targets_hit_str else [False, False]
                        
                        # Se ambos targets foram atingidos, move para backup
                        if len(targets_hit) >= 2 and targets_hit[0] and targets_hit[1]:
                            self._backup_signal_from_row(signal, "moved_to_backup_target_2_complete")
                            
                            cursor.execute(f"DELETE FROM {self.signals_table} WHERE id = ?", (signal[0],))
                            target_2_complete_count += 1
                            
                    except Exception as e:
                        self.logger.warning(f"Erro ao processar sinal TARGET_HIT {signal[0]}: {e}")
                
                if target_2_complete_count > 0:
                    moved_counts['TARGET_2_COMPLETE'] = target_2_complete_count
                    self.logger.info(f"Movidos {target_2_complete_count} sinais TARGET_HIT completos para backup")
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Erro ao mover sinais finalizados para backup: {e}")
        
        return moved_counts
    
    def mark_expired_signals_as_killed(self) -> int:
        """Marca apenas sinais ACTIVE antigos como expirados"""
        hours_limit = settings.system.signal_lifecycle_hours
        cutoff_time = datetime.now() - timedelta(hours=hours_limit)
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Apenas marca sinais ACTIVE como expirados
                # TARGET_HIT pode demorar mais para finalizar
                update_query = f"""
                UPDATE {self.signals_table} 
                SET status = 'EXPIRED', updated_at = ?
                WHERE status = 'ACTIVE' AND created_at < ?
                """
                
                cursor.execute(update_query, (datetime.now().isoformat(), cutoff_time.isoformat()))
                expired_count = cursor.rowcount
                conn.commit()
                
                if expired_count > 0:
                    self.logger.info(f"⏰ {expired_count} sinais ACTIVE marcados como EXPIRED (lifecycle: {hours_limit}h)")
                
                return expired_count
                
        except Exception as e:
            self.logger.error(f"Erro ao marcar sinais como EXPIRED: {e}")
            return 0
    
    def _backup_signal_from_row(self, signal_row: tuple, reason: str):
        """Faz backup de um sinal a partir de uma row do banco"""
        sql = f"""
        INSERT INTO {self.backup_table} (
            original_id, symbol, signal_type, timeframe, detector_type, detector_name,
            signal_source, signal_hash, entry_price, confidence, confluence_score,
            status, created_at, backup_reason,
            targets, stop_loss, indicators_used, timeframe_analysis, market_conditions,
            pattern_data, technical_data, stop_loss_analysis, targets_analysis, backup_timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with self._get_connection() as conn:
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
                    signal_row[24] if len(signal_row) > 24 else None,  # stop_loss_analysis
                    signal_row[25] if len(signal_row) > 25 else None,  # targets_analysis
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
            pattern_data, technical_data, stop_loss_analysis, targets_analysis, backup_timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    json.dumps(signal.stop_loss_analysis),
                    json.dumps(signal.targets_analysis),
                    datetime.now().isoformat()
                )
                conn.execute(sql, values)
                conn.commit()
        except Exception as e:
            self.logger.error(f"Erro ao fazer backup do sinal: {e}")

# Apelidos para compatibilidade
TradingSignal = EnhancedTradingSignal
SignalWriter = EnhancedSignalWriter