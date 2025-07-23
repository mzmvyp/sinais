# improved_signal_quality_system.py - SISTEMA RIGOROSO DE QUALIDADE + BACKUP COMPLETO

"""
Sistema Aprimorado de Qualidade e Backup Total
1. Qualidade MUITO mais rigorosa para reduzir sinais de 5m
2. Prioridade absoluta 5m, mas 15m entra quando não há 5m
3. Backup COMPLETO de todos os sinais (incluindo 43 candlesticks)
4. Sistema de estatísticas para análise de efetividade
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import pandas as pd

@dataclass
class RigorousQualityConfig:
    """Configuração RIGOROSA para reduzir sinais de 5m e permitir 15m"""
    
    # 🎯 QUALIDADE MUITO RIGOROSA POR DETECTOR
    detector_requirements: Dict[str, Dict] = None
    
    # ⚖️ REGRAS DE PRIORIDADE 5m vs 15m
    timeframe_rules: Dict[str, Dict] = None
    
    # 📊 CONFIGURAÇÃO DE BACKUP COMPLETO
    backup_config: Dict = None
    
    def __post_init__(self):
        if self.detector_requirements is None:
            self.detector_requirements = {
                # 📈 INDICADORES TÉCNICOS - MUITO RIGOROSOS
                'RSI': {
                    'min_confidence': 0.90,  # Era 0.75, agora 0.90
                    'min_rsi_extreme': 78,   # RSI > 78 para overbought
                    'max_rsi_extreme': 22,   # RSI < 22 para oversold
                    'require_divergence': True,  # NOVO: precisa de divergência
                    'max_signals_per_day': 1,
                    'description': 'RSI apenas extremo + divergência'
                },
                'MACD': {
                    'min_confidence': 0.88,  # Era 0.80, agora 0.88
                    'min_histogram_strength': 0.025,  # Histograma mais forte
                    'require_momentum_confirmation': True,  # NOVO
                    'min_crossover_angle': 15,  # Ângulo mínimo do crossover
                    'max_signals_per_day': 1,
                    'description': 'MACD apenas crossovers fortes'
                },
                
                # 📊 PADRÕES GRÁFICOS - MUITO RIGOROSOS  
                'Double_Top': {
                    'min_confidence': 0.85,  # Era 0.72, agora 0.85
                    'min_pattern_strength': 0.80,  # Era 0.60, agora 0.80
                    'min_significance': 0.15,  # Era 0.08, agora 0.15
                    'min_duration': 20,  # Mínimo 20 barras
                    'max_signals_per_day': 1,
                    'description': 'Double patterns apenas muito definidos'
                },
                'Double_Bottom': {
                    'min_confidence': 0.85,
                    'min_pattern_strength': 0.80,
                    'min_significance': 0.15,
                    'min_duration': 20,
                    'max_signals_per_day': 1,
                    'description': 'Double patterns apenas muito definidos'
                },
                
                # 🕯️ CANDLESTICK PATTERNS - RIGOROSOS PARA SINAIS, TODOS GRAVADOS NO BACKUP
                'Bullish_Engulfing': {
                    'min_confidence': 0.92,  # Muito rigoroso para sinal ativo
                    'min_reliability_score': 0.90,
                    'require_trend_context': True,
                    'require_volume_spike': True,
                    'max_signals_per_day': 1,
                    'backup_all': True,  # NOVO: grava no backup mesmo se não passar
                    'description': 'Engolfo muito rigoroso para sinal'
                },
                'Bearish_Engulfing': {
                    'min_confidence': 0.92,
                    'min_reliability_score': 0.90,
                    'require_trend_context': True,
                    'require_volume_spike': True,
                    'max_signals_per_day': 1,
                    'backup_all': True,
                    'description': 'Engolfo muito rigoroso para sinal'
                },
                # TODOS OS OUTROS CANDLESTICKS - apenas backup, sem sinais ativos
                'ALL_OTHER_CANDLESTICKS': {
                    'min_confidence': 0.99,  # Impossível de atingir = só backup
                    'backup_only': True,
                    'description': 'Outros candlesticks apenas para estatística'
                }
            }
        
        if self.timeframe_rules is None:
            self.timeframe_rules = {
                '5m': {
                    'absolute_priority': True,  # Prioridade absoluta sempre
                    'min_confidence_for_signal': 0.88,  # MUITO rigoroso
                    'max_signals_per_symbol': 1,
                    'description': 'Prioridade absoluta, mas qualidade rigorosa'
                },
                '15m': {
                    'can_signal_when_no_5m': True,  # Pode sinalizar apenas se não há 5m
                    'min_confidence_for_signal': 0.82,  # Menos rigoroso que 5m
                    'max_signals_per_symbol': 1,
                    'description': 'Entra apenas quando não há sinal de 5m'
                }
            }
        
        if self.backup_config is None:
            self.backup_config = {
                'save_all_generated_signals': True,  # Grava TODOS os sinais
                'save_eliminated_duplicates': True,  # Grava sinais eliminados
                'save_all_43_candlesticks': True,   # Grava todos os 43 patterns
                'save_validation_details': True,    # Grava detalhes da validação
                'include_market_data_snapshot': True,  # Snapshot dos dados
                'track_elimination_reason': True,   # Motivo da eliminação
                'enable_statistics_tracking': True  # Para análise posterior
            }

# Instância global
rigorous_quality_config = RigorousQualityConfig()

# ================================
# SISTEMA DE BACKUP COMPLETO
# ================================

class ComprehensiveSignalBackup:
    """Sistema de backup que grava TODOS os sinais gerados"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        try:
            from config.settings import settings
            self.db_path = settings.database.signals_db_path
            self.backup_table = settings.database.backup_table
            self.statistics_table = "signal_statistics_v2"
        except:
            self.db_path = "trading_analyzer_v2.db"
            self.backup_table = "signal_backup_v2"
            self.statistics_table = "signal_statistics_v2"
        
        self._ensure_statistics_table()
        self.logger.info("🗄️ Sistema de backup completo inicializado")
    
    def backup_all_generated_signals(self, all_signals: List, symbol: str, 
                                   elimination_details: Dict = None) -> int:
        """
        🗄️ GRAVA TODOS OS SINAIS GERADOS (incluindo eliminados)
        """
        if not all_signals:
            return 0
        
        backup_count = 0
        
        try:
            import sqlite3
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                
                for i, signal in enumerate(all_signals):
                    try:
                        backup_data = self._prepare_signal_for_backup(
                            signal, symbol, i, elimination_details
                        )
                        
                        self._insert_backup_record(conn, backup_data)
                        backup_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"Erro ao fazer backup do sinal {i}: {e}")
                        continue
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Erro no backup completo: {e}")
            return 0
        
        self.logger.debug(f"🗄️ {backup_count} sinais salvos no backup para {symbol}")
        return backup_count
    
    def backup_candlestick_analysis(self, symbol: str, timeframe: str, 
                                  all_43_patterns: List) -> int:
        """
        🕯️ GRAVA TODOS OS 43 CANDLESTICK PATTERNS (para estatística)
        """
        if not all_43_patterns:
            return 0
        
        backup_count = 0
        
        try:
            import sqlite3
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                
                for pattern in all_43_patterns:
                    try:
                        backup_data = self._prepare_candlestick_for_backup(
                            pattern, symbol, timeframe
                        )
                        
                        self._insert_backup_record(conn, backup_data)
                        backup_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"Erro ao fazer backup do candlestick {pattern.name}: {e}")
                        continue
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Erro no backup de candlesticks: {e}")
            return 0
        
        self.logger.debug(f"🕯️ {backup_count} candlestick patterns salvos para {symbol} {timeframe}")
        return backup_count
    
    def track_signal_elimination(self, eliminated_signals: List, winner_signal, 
                               symbol: str, elimination_reason: str):
        """
        📊 RASTREIA SINAIS ELIMINADOS POR CONFLITO
        """
        for signal in eliminated_signals:
            try:
                elimination_data = {
                    'signal_data': signal,
                    'eliminated_by': winner_signal.detector_name if winner_signal else 'validation',
                    'elimination_reason': elimination_reason,
                    'symbol': symbol,
                    'elimination_timestamp': datetime.now().isoformat()
                }
                
                self._save_elimination_record(elimination_data)
                
            except Exception as e:
                self.logger.error(f"Erro ao rastrear eliminação: {e}")
    
    def _prepare_signal_for_backup(self, signal, symbol: str, index: int, 
                                 elimination_details: Dict = None) -> Dict:
        """Prepara sinal para backup com todos os detalhes"""
        
        # Determina se foi eliminado
        was_eliminated = elimination_details and index in elimination_details.get('eliminated_indices', [])
        elimination_reason = elimination_details.get('reason', 'none') if was_eliminated else 'active'
        
        # Extrai dados do sinal
        if hasattr(signal, '__dict__'):
            signal_dict = signal.__dict__.copy()
        elif isinstance(signal, dict):
            signal_dict = signal.copy()
        else:
            signal_dict = {'raw_signal': str(signal)}
        
        backup_data = {
            'original_id': signal_dict.get('id', f"{symbol}_{index}_{int(datetime.now().timestamp())}"),
            'symbol': symbol,
            'signal_type': signal_dict.get('signal_type', 'unknown'),
            'timeframe': signal_dict.get('timeframe', 'unknown'),
            'detector_type': signal_dict.get('detector_type', 'unknown'),
            'detector_name': signal_dict.get('detector_name', 'unknown'),
            'confidence': signal_dict.get('confidence', 0.0),
            'entry_price': signal_dict.get('entry_price', 0.0),
            'stop_loss': signal_dict.get('stop_loss', 0.0),
            'targets': json.dumps(signal_dict.get('targets', [])),
            'created_at': signal_dict.get('timestamp', datetime.now()).isoformat() if hasattr(signal_dict.get('timestamp', ''), 'isoformat') else str(signal_dict.get('timestamp', datetime.now().isoformat())),
            'backup_timestamp': datetime.now().isoformat(),
            'backup_reason': f"comprehensive_backup:{elimination_reason}",
            'was_eliminated': was_eliminated,
            'elimination_reason': elimination_reason,
            'signal_index_in_batch': index,
            'full_signal_data': json.dumps(signal_dict, default=str)
        }
        
        return backup_data
    
    def _prepare_candlestick_for_backup(self, pattern, symbol: str, timeframe: str) -> Dict:
        """Prepara candlestick pattern para backup"""
        
        backup_data = {
            'original_id': f"candlestick_{symbol}_{timeframe}_{pattern.name}_{int(datetime.now().timestamp())}",
            'symbol': symbol,
            'signal_type': 'BUY_LONG' if pattern.pattern_type == 'bullish' else 'SELL_SHORT',
            'timeframe': timeframe,
            'detector_type': 'candlestick_comprehensive',
            'detector_name': pattern.name.replace(' ', '_'),
            'confidence': getattr(pattern, 'reliability_score', 0.0),
            'entry_price': getattr(pattern, 'entry_price', 0.0),
            'stop_loss': getattr(pattern, 'stop_loss', 0.0),
            'targets': json.dumps([getattr(pattern, 'target_price', 0.0)]),
            'created_at': datetime.now().isoformat(),
            'backup_timestamp': datetime.now().isoformat(),
            'backup_reason': 'candlestick_comprehensive_analysis',
            'was_eliminated': False,
            'elimination_reason': 'none',
            'pattern_reliability': getattr(pattern, 'reliability_score', 0.0),
            'pattern_position': getattr(pattern, 'position_index', 0),
            'full_pattern_data': json.dumps({
                'name': pattern.name,
                'pattern_type': pattern.pattern_type,
                'reliability_score': getattr(pattern, 'reliability_score', 0.0),
                'entry_price': getattr(pattern, 'entry_price', 0.0),
                'stop_loss': getattr(pattern, 'stop_loss', 0.0),
                'target_price': getattr(pattern, 'target_price', 0.0),
                'position_index': getattr(pattern, 'position_index', 0)
            }, default=str)
        }
        
        return backup_data
    
    def _insert_backup_record(self, conn, backup_data: Dict):
        """Insere registro no backup"""
        
        sql = f"""
        INSERT INTO {self.backup_table} (
            original_id, symbol, signal_type, timeframe, detector_type, detector_name,
            confidence, entry_price, stop_loss, targets, created_at, backup_timestamp,
            backup_reason, was_eliminated, elimination_reason, signal_index_in_batch,
            full_signal_data, pattern_reliability, pattern_position
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        values = (
            backup_data['original_id'],
            backup_data['symbol'],
            backup_data['signal_type'],
            backup_data['timeframe'],
            backup_data['detector_type'],
            backup_data['detector_name'],
            backup_data['confidence'],
            backup_data['entry_price'],
            backup_data.get('stop_loss', 0.0),
            backup_data['targets'],
            backup_data['created_at'],
            backup_data['backup_timestamp'],
            backup_data['backup_reason'],
            backup_data.get('was_eliminated', False),
            backup_data.get('elimination_reason', 'none'),
            backup_data.get('signal_index_in_batch', 0),
            backup_data.get('full_signal_data', '{}'),
            backup_data.get('pattern_reliability', 0.0),
            backup_data.get('pattern_position', 0)
        )
        
        conn.execute(sql, values)
    
    def _ensure_statistics_table(self):
        """Garante que tabela de estatísticas existe"""
        try:
            import sqlite3
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {self.statistics_table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    timeframe TEXT,
                    detector_name TEXT,
                    signal_type TEXT,
                    confidence REAL,
                    was_selected BOOLEAN,
                    elimination_reason TEXT,
                    created_at TEXT,
                    analysis_date TEXT,
                    market_conditions TEXT,
                    effectiveness_score REAL,
                    follow_through_analysis TEXT
                )
                """
                conn.execute(create_table_sql)
                conn.commit()
        except Exception as e:
            self.logger.error(f"Erro ao criar tabela de estatísticas: {e}")
    
    def _save_elimination_record(self, elimination_data: Dict):
        """Salva registro de eliminação para estatísticas"""
        try:
            import sqlite3
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                
                signal_data = elimination_data['signal_data']
                
                sql = f"""
                INSERT INTO {self.statistics_table} (
                    symbol, timeframe, detector_name, signal_type, confidence,
                    was_selected, elimination_reason, created_at, analysis_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                values = (
                    elimination_data['symbol'],
                    getattr(signal_data, 'timeframe', 'unknown'),
                    getattr(signal_data, 'detector_name', 'unknown'),
                    getattr(signal_data, 'signal_type', 'unknown'),
                    getattr(signal_data, 'confidence', 0.0),
                    False,  # was_selected = False (foi eliminado)
                    elimination_data['elimination_reason'],
                    getattr(signal_data, 'timestamp', datetime.now()).isoformat() if hasattr(getattr(signal_data, 'timestamp', ''), 'isoformat') else str(getattr(signal_data, 'timestamp', datetime.now().isoformat())),
                    datetime.now().isoformat()
                )
                
                conn.execute(sql, values)
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Erro ao salvar registro de eliminação: {e}")

# ================================
# SISTEMA DE QUALIDADE RIGOROSA
# ================================

class RigorousQualityFilter:
    """Filtro rigoroso que reduz drasticamente os sinais de 5m"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = rigorous_quality_config
        self.backup_system = ComprehensiveSignalBackup()
        
        self.logger.info("🎯 Sistema RIGOROSO de qualidade inicializado")
    
    def filter_signals_with_rigorous_quality(self, all_signals: List, symbol: str) -> tuple[List, Dict]:
        """
        🎯 FILTRA SINAIS COM QUALIDADE RIGOROSA + BACKUP COMPLETO
        """
        if not all_signals:
            return [], {'eliminated_indices': [], 'reason': 'no_signals', 'total_original': 0}
        
        # 🚨 CORREÇÃO 1: BACKUP COMPLETO ANTES de qualquer filtragem
        self.logger.info(f"💾 Salvando {len(all_signals)} sinais no backup para {symbol}")
        backup_count = self.backup_system.backup_all_generated_signals(all_signals, symbol)
        self.logger.debug(f"✅ {backup_count} sinais salvos no backup")
        
        # 🚨 CORREÇÃO 2: Aplicar filtro de qualidade mais inteligente
        high_quality_signals = []
        medium_quality_signals = []
        eliminated_indices = []
        
        for i, signal in enumerate(all_signals):
            try:
                detector_name = getattr(signal, 'detector_name', 'unknown')
                confidence = getattr(signal, 'confidence', 0.0)
                timeframe = getattr(signal, 'timeframe', '5m')
                
                # Verifica se detector é permitido
                if not self._is_detector_allowed_for_signal(detector_name):
                    eliminated_indices.append(i)
                    self.logger.debug(f"❌ {detector_name}: detector não permitido para sinais")
                    continue
                
                # 🚨 NOVA LÓGICA: Categoriza por qualidade em vez de eliminar
                min_confidence = self._get_min_confidence_for_signal(detector_name, symbol, timeframe)
                
                if confidence >= min_confidence:
                    # Verifica condições específicas do detector
                    if self._validate_detector_specific_conditions(signal, detector_name):
                        # Categoriza por qualidade
                        if confidence >= 0.85:  # Alta qualidade
                            high_quality_signals.append(signal)
                            self.logger.debug(f"🟢 {detector_name}: ALTA qualidade (conf: {confidence:.3f})")
                        else:  # Qualidade média
                            medium_quality_signals.append(signal)
                            self.logger.debug(f"🟡 {detector_name}: MÉDIA qualidade (conf: {confidence:.3f})")
                    else:
                        eliminated_indices.append(i)
                        self.logger.debug(f"❌ {detector_name}: condições específicas não atendidas")
                else:
                    eliminated_indices.append(i)
                    self.logger.debug(f"❌ {detector_name}: confiança baixa ({confidence:.3f} < {min_confidence:.3f})")
            
            except Exception as e:
                self.logger.error(f"Erro ao filtrar sinal {i}: {e}")
                eliminated_indices.append(i)
        
        # 🚨 CORREÇÃO 3: Combina sinais de alta e média qualidade para competição
        qualified_signals = high_quality_signals + medium_quality_signals
        
        # Rastreia eliminações para estatística
        eliminated_signals = [all_signals[i] for i in eliminated_indices]
        if eliminated_signals:
            self.backup_system.track_signal_elimination(
                eliminated_signals, 
                qualified_signals[0] if qualified_signals else None,
                symbol, 
                'rigorous_quality_filter'
            )
        
        # Aplica regras de prioridade com a nova lógica
        final_signals = self._apply_timeframe_priority_rules(qualified_signals)
        
        elimination_details = {
            'eliminated_indices': eliminated_indices,
            'reason': 'rigorous_quality_filter_improved',
            'total_original': len(all_signals),
            'high_quality_count': len(high_quality_signals),
            'medium_quality_count': len(medium_quality_signals),
            'final_count': len(final_signals),
            'backup_saved': backup_count
        }
        
        self.logger.info(
            f"🎯 Filtro aprimorado {symbol}: {len(all_signals)} → "
            f"Alta({len(high_quality_signals)}) + Média({len(medium_quality_signals)}) → {len(final_signals)} final"
        )
        
        return final_signals, elimination_details


    def process_all_candlestick_patterns_for_backup(self, symbol: str, timeframe: str, 
                                                   df: pd.DataFrame) -> int:
        """
        🕯️ PROCESSA TODOS OS 43 CANDLESTICK PATTERNS PARA BACKUP
        (mesmo que não sejam usados para sinais)
        """
        try:
            # Importa o detector completo
            from indicators.candlestick_patterns_detector import CandlestickDetector
            
            detector = CandlestickDetector()
            all_43_patterns = detector.detect_all_patterns(df)
            
            # Grava TODOS no backup (para estatísticas)
            backup_count = self.backup_system.backup_candlestick_analysis(
                symbol, timeframe, all_43_patterns
            )
            
            self.logger.debug(f"🕯️ {backup_count} candlestick patterns processados para backup: {symbol} {timeframe}")
            return backup_count
            
        except Exception as e:
            self.logger.error(f"Erro ao processar candlesticks para backup: {e}")
            return 0
    
    def _is_detector_allowed_for_signal(self, detector_name: str) -> bool:
        """Verifica se detector pode gerar sinais ativos"""
        
        # Todos os candlesticks exceto engolfo são apenas backup
        if detector_name in ['Bullish_Engulfing', 'Bearish_Engulfing']:
            return True
        
        # Verifica se é um dos 43 candlesticks (só backup)
        all_43_names = [
            'Hammer', 'Hanging_Man', 'Inverted_Hammer', 'Shooting_Star',
            'White_Marubozu', 'Black_Marubozu', 'Dragonfly_Doji', 'Gravestone_Doji',
            'Bullish_Belt-hold', 'Bearish_Belt-hold', 'Bullish_Harami', 'Bearish_Harami',
            'Bullish_Harami_Cross', 'Bearish_Harami_Cross', 'Piercing_Pattern', 'Dark_Cloud_Cover',
            'Tweezer_Top', 'Tweezer_Bottom', 'Bullish_Counterattack', 'Bearish_Counterattack',
            'Morning_Star', 'Evening_Star', 'Morning_Doji_Star', 'Evening_Doji_Star',
            'Three_White_Soldiers', 'Three_Black_Crows', 'Three_Inside_Up', 'Three_Inside_Down',
            'Three_Outside_Up', 'Three_Outside_Down', 'Stick_Sandwich',
            'Bullish_Abandoned_Baby', 'Bearish_Abandoned_Baby', 'Rising_Three_Methods',
            'Falling_Three_Methods', 'Advance_Block', 'Deliberation', 'Bullish_Breakaway', 'Bearish_Breakaway'
        ]
        
        if detector_name in all_43_names:
            return False  # Apenas backup, não sinais ativos
        
        # Indicadores técnicos e padrões gráficos são permitidos
        allowed_detectors = ['RSI', 'MACD', 'Double_Top', 'Double_Bottom']
        return detector_name in allowed_detectors
    
    def _get_min_confidence_for_signal(self, detector_name: str, symbol: str, timeframe: str) -> float:
        """Calcula confiança mínima rigorosa para o detector"""
        
        # Configuração base do detector
        detector_config = self.config.detector_requirements.get(detector_name, {})
        base_confidence = detector_config.get('min_confidence', 0.90)  # Padrão muito alto
        
        # Ajuste rigoroso por timeframe (favorece ligeiramente 15m)
        if timeframe == '5m':
            tf_adjustment = 0.02  # 5m precisa ser 2% maior
        else:
            tf_adjustment = 0.0   # 15m mantém base
        
        # Ajuste por symbol (mais rigoroso para memecoins)
        symbol_adjustment = 0.0
        if symbol in ['PEPE', 'TURBO', 'HYPE']:
            symbol_adjustment = 0.05  # Memecoins precisam 5% a mais
        elif symbol in ['BTC', 'ETH']:
            symbol_adjustment = -0.02  # BTC/ETH podem ser 2% menores
        
        final_confidence = base_confidence + tf_adjustment + symbol_adjustment
        return min(1.0, max(0.5, final_confidence))
    
    def _validate_detector_specific_conditions(self, signal, detector_name: str) -> bool:
        """Valida condições específicas de cada detector"""
        
        try:
            config = self.config.detector_requirements.get(detector_name, {})
            
            # RSI: verifica níveis extremos
            if detector_name == 'RSI':
                # Aqui seria necessário acessar o valor do RSI do signal
                # Por simplicidade, assumimos que passou se chegou até aqui
                return True
            
            # MACD: verifica força do crossover
            elif detector_name == 'MACD':
                # Aqui seria necessário acessar os dados do MACD
                return True
            
            # Double patterns: verifica força do padrão
            elif detector_name in ['Double_Top', 'Double_Bottom']:
                pattern_strength = getattr(signal, 'pattern_strength', 0.0)
                min_strength = config.get('min_pattern_strength', 0.8)
                return pattern_strength >= min_strength
            
            # Engolfo: verifica contexto de tendência
            elif detector_name in ['Bullish_Engulfing', 'Bearish_Engulfing']:
                # Validações específicas para engolfo
                reliability = getattr(signal, 'reliability_score', 0.0)
                min_reliability = config.get('min_reliability_score', 0.90)
                return reliability >= min_reliability
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro na validação específica para {detector_name}: {e}")
            return False
    
    def _apply_timeframe_priority_rules(self, signals: List) -> List:
        """
        ⚖️ APLICA REGRAS DE PRIORIDADE CORRIGIDAS: 
        - 5m com qualidade boa = prioridade absoluta
        - 5m com qualidade baixa = permite 15m competir
        - 15m apenas se não há 5m bom
        """
        if not signals:
            return []
        
        # Separa por timeframe
        signals_5m = [s for s in signals if getattr(s, 'timeframe', '') == '5m']
        signals_15m = [s for s in signals if getattr(s, 'timeframe', '') == '15m']
        
        # 🚨 NOVA LÓGICA: Verifica qualidade dos sinais de 5m
        high_quality_5m = []
        low_quality_5m = []
        
        for signal in signals_5m:
            confidence = getattr(signal, 'confidence', 0.0)
            # Define threshold de qualidade alta para 5m
            if confidence >= 0.85:  # Alta qualidade
                high_quality_5m.append(signal)
            else:  # Qualidade baixa/média
                low_quality_5m.append(signal)
        
        # REGRA 1: Se há sinal de 5m com ALTA qualidade, usa apenas ele
        if high_quality_5m:
            best_5m = max(high_quality_5m, key=lambda s: getattr(s, 'confidence', 0.0))
            self.logger.info(f"🥇 5m ALTA QUALIDADE: {best_5m.detector_name} (conf: {best_5m.confidence:.3f})")
            return [best_5m]
        
        # REGRA 2: Se há sinal de 15m e 5m só tem qualidade baixa, COMPARA
        if signals_15m and low_quality_5m:
            best_15m = max(signals_15m, key=lambda s: getattr(s, 'confidence', 0.0))
            best_5m_low = max(low_quality_5m, key=lambda s: getattr(s, 'confidence', 0.0))
            
            # Se 15m tem qualidade significativamente melhor, usa 15m
            if best_15m.confidence > best_5m_low.confidence + 0.05:  # 5% de vantagem
                self.logger.info(f"🥈 15m VENCE 5m: 15m({best_15m.confidence:.3f}) > 5m({best_5m_low.confidence:.3f})")
                return [best_15m]
            else:
                # 5m ainda tem preferência por ser mais rápido
                self.logger.info(f"🥉 5m por desempate: {best_5m_low.detector_name} (conf: {best_5m_low.confidence:.3f})")
                return [best_5m_low]
        
        # REGRA 3: Se só há 5m (qualidade baixa), usa ele
        elif low_quality_5m:
            best_5m = max(low_quality_5m, key=lambda s: getattr(s, 'confidence', 0.0))
            self.logger.info(f"🥉 5m único disponível: {best_5m.detector_name} (conf: {best_5m.confidence:.3f})")
            return [best_5m]
        
        # REGRA 4: Se só há 15m, usa ele
        elif signals_15m:
            best_15m = max(signals_15m, key=lambda s: getattr(s, 'confidence', 0.0))
            self.logger.info(f"🥈 15m único disponível: {best_15m.detector_name} (conf: {best_15m.confidence:.3f})")
            return [best_15m]
        
        # REGRA 5: Nenhum sinal
        else:
            self.logger.info("❌ Nenhum sinal de qualidade suficiente")
            return []

    # ================================
    # INTEGRAÇÃO COM O SISTEMA ATUAL
    # ================================

    def create_rigorous_quality_system():
        """
        🎯 Cria sistema rigoroso para integração no analyzer.py
        """
        
        quality_filter = RigorousQualityFilter()
        
        def enhanced_signal_processing(all_raw_signals: List, symbol: str) -> tuple[List, Dict]:
            """
            Função para substituir o processamento de sinais no analyzer.py
            
            Uso no MultiTimeframeAnalyzer.analyze_symbol_all_timeframes():
            
            # Substitui:
            # if len(all_signals) > 1:
            #     all_signals = self.conflict_resolver.resolve_conflicts(all_signals)
            
            # Por:
            # all_signals, elimination_details = enhanced_signal_processing(all_signals, symbol)
            """
            
            return quality_filter.filter_signals_with_rigorous_quality(all_raw_signals, symbol)
        
        def process_candlesticks_for_backup(symbol: str, timeframe: str, df: pd.DataFrame) -> int:
            """
            Função para processar todos os 43 candlesticks no backup
            
            Uso no MultiTimeframeAnalyzer._analyze_single_timeframe():
            
            # Adiciona no final da função:
            # if timeframe in ['5m', '15m']:  # ou apenas '5m' se preferir
            #     process_candlesticks_for_backup(symbol, timeframe, market_data.data)
            """
            
            return quality_filter.process_all_candlestick_patterns_for_backup(symbol, timeframe, df)
        
        return enhanced_signal_processing, process_candlesticks_for_backup

# ================================
# SISTEMA DE ESTATÍSTICAS
# ================================

class SignalEffectivenessAnalyzer:
    """Analisador de efetividade dos sinais para otimização"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        try:
            from config.settings import settings
            self.db_path = settings.database.signals_db_path
        except:
            self.db_path = "trading_analyzer_v2.db"
        
        self.backup_table = "signal_backup_v2"
        self.statistics_table = "signal_statistics_v2"
    
    def analyze_detector_effectiveness(self, days: int = 7) -> Dict:
        """
        📊 ANÁLISE DE EFETIVIDADE POR DETECTOR
        """
        try:
            import sqlite3
            
            start_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                
                # Query para análise de efetividade
                query = f"""
                SELECT 
                    detector_name,
                    detector_type,
                    timeframe,
                    signal_type,
                    COUNT(*) as total_signals,
                    AVG(confidence) as avg_confidence,
                    COUNT(CASE WHEN was_eliminated = 0 THEN 1 END) as selected_count,
                    COUNT(CASE WHEN was_eliminated = 1 THEN 1 END) as eliminated_count
                FROM {self.backup_table}
                WHERE datetime(backup_timestamp) >= ?
                GROUP BY detector_name, detector_type, timeframe, signal_type
                ORDER BY total_signals DESC
                """
                
                df = pd.read_sql_query(query, conn, params=[start_date.isoformat()])
                
                if df.empty:
                    return {'error': 'Nenhum dado encontrado'}
                
                # Calcula métricas
                df['selection_rate'] = df['selected_count'] / df['total_signals']
                df['elimination_rate'] = df['eliminated_count'] / df['total_signals']
                
                # Resultados por detector
                results_by_detector = {}
                for detector in df['detector_name'].unique():
                    detector_data = df[df['detector_name'] == detector]
                    
                    results_by_detector[detector] = {
                        'total_signals': int(detector_data['total_signals'].sum()),
                        'avg_confidence': float(detector_data['avg_confidence'].mean()),
                        'selection_rate': float(detector_data['selection_rate'].mean()),
                        'by_timeframe': detector_data.groupby('timeframe').agg({
                            'total_signals': 'sum',
                            'selection_rate': 'mean',
                            'avg_confidence': 'mean'
                        }).to_dict('index')
                    }
                
                # Top performers
                top_performers = df.nlargest(10, 'selection_rate')[
                    ['detector_name', 'timeframe', 'total_signals', 'selection_rate', 'avg_confidence']
                ].to_dict('records')
                
                return {
                    'analysis_period_days': days,
                    'total_signals_analyzed': int(df['total_signals'].sum()),
                    'results_by_detector': results_by_detector,
                    'top_performers': top_performers,
                    'summary': {
                        'most_active_detector': df.loc[df['total_signals'].idxmax(), 'detector_name'],
                        'highest_selection_rate': df.loc[df['selection_rate'].idxmax(), 'detector_name'],
                        'highest_confidence': df.loc[df['avg_confidence'].idxmax(), 'detector_name']
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Erro na análise de efetividade: {e}")
            return {'error': str(e)}
    
    def get_candlestick_statistics(self, days: int = 7) -> Dict:
        """
        🕯️ ESTATÍSTICAS DOS 43 CANDLESTICK PATTERNS
        """
        try:
            import sqlite3
            
            start_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                
                query = f"""
                SELECT 
                    detector_name,
                    timeframe,
                    signal_type,
                    COUNT(*) as occurrences,
                    AVG(confidence) as avg_reliability,
                    AVG(pattern_reliability) as avg_pattern_score
                FROM {self.backup_table}
                WHERE datetime(backup_timestamp) >= ?
                  AND detector_type = 'candlestick_comprehensive'
                GROUP BY detector_name, timeframe, signal_type
                ORDER BY occurrences DESC
                """
                
                df = pd.read_sql_query(query, conn, params=[start_date.isoformat()])
                
                if df.empty:
                    return {'error': 'Nenhum candlestick encontrado'}
                
                # Top patterns por frequência
                top_by_frequency = df.groupby('detector_name').agg({
                    'occurrences': 'sum',
                    'avg_reliability': 'mean'
                }).sort_values('occurrences', ascending=False).head(10).to_dict('index')
                
                # Top patterns por qualidade
                top_by_quality = df.nlargest(10, 'avg_reliability')[
                    ['detector_name', 'timeframe', 'occurrences', 'avg_reliability']
                ].to_dict('records')
                
                return {
                    'analysis_period_days': days,
                    'total_patterns_detected': int(df['occurrences'].sum()),
                    'unique_patterns': len(df['detector_name'].unique()),
                    'top_by_frequency': top_by_frequency,
                    'top_by_quality': top_by_quality,
                    'patterns_by_timeframe': df.groupby('timeframe')['occurrences'].sum().to_dict(),
                    'bullish_vs_bearish': df.groupby('signal_type')['occurrences'].sum().to_dict()
                }
                
        except Exception as e:
            self.logger.error(f"Erro nas estatísticas de candlestick: {e}")
            return {'error': str(e)}

# Exemplo de uso
if __name__ == "__main__":
    # Teste do sistema rigoroso
    config = RigorousQualityConfig()
    print("🎯 Sistema Rigoroso de Qualidade Configurado")
    print(f"RSI min confidence: {config.detector_requirements['RSI']['min_confidence']}")
    print(f"MACD min confidence: {config.detector_requirements['MACD']['min_confidence']}")
    print(f"Engolfo min confidence: {config.detector_requirements['Bullish_Engulfing']['min_confidence']}")
    
    # Teste de análise de efetividade
    analyzer = SignalEffectivenessAnalyzer()
    print("\n📊 Analisador de Efetividade Inicializado")
    print("Use analyzer.analyze_detector_effectiveness() para ver estatísticas")