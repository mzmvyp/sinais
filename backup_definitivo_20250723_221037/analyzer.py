# analyzer.py - PRIORIDADE 15m + SCORE RIGOROSO PARA 5m + SEM LOCKS

import logging
import time
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta

from core.data_reader import DataReader, MarketData
from core.signal_writer import EnhancedSignalWriter, EnhancedTradingSignal
from indicators.technical import TechnicalAnalyzer, RSIAnalyzer 

try:
    from core.improved_signal_quality_system import (
        create_rigorous_quality_system,
        SignalEffectivenessAnalyzer,
        RigorousQualityConfig
    )
    RIGOROUS_QUALITY_AVAILABLE = True
except ImportError:
    RIGOROUS_QUALITY_AVAILABLE = False
    logging.warning("⚠️ Sistema rigoroso de qualidade não disponível")

try:
    from indicators.patterns import PatternAnalyzer
    PATTERNS_AVAILABLE = True
except ImportError as e:
    PATTERNS_AVAILABLE = False
    logging.warning(f"Padrões gráficos não disponíveis: {e}")

try:
    from indicators.candlestick_patterns_detector import generate_candlestick_signals
    CANDLESTICK_AVAILABLE = True
except ImportError as e:
    CANDLESTICK_AVAILABLE = False
    logging.warning(f"Detector de Candlestick não disponível: {e}")

# Sistema de monitoramento em tempo real DESABILITADO para evitar locks
REAL_TIME_MONITORING_AVAILABLE = False
logging.info("🚫 Monitoramento em tempo real DESABILITADO (evita locks de DB)")

from config.settings import settings

class PrioritySignalResolver:
    """Resolve conflitos com PRIORIDADE 15m + Score rigoroso para 5m"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # NOVA LÓGICA: 15m tem prioridade, 5m precisa score >= 90 e ser 10+ pontos maior
        self.MIN_5M_SCORE = 90.0
        self.SCORE_ADVANTAGE_REQUIRED = 10.0
    
    def resolve_conflicts(self, signals: List[EnhancedTradingSignal]) -> List[EnhancedTradingSignal]:
        """
        NOVA LÓGICA DE PRIORIDADE:
        1. 15m tem prioridade por padrão
        2. 5m só ganha se: score >= 90 E score_5m > score_15m + 10
        """
        if not signals:
            return signals
        
        start_time = time.time()
        
        grouped = {}
        for signal in signals:
            symbol = signal.symbol
            if symbol not in grouped:
                grouped[symbol] = []
            grouped[symbol].append(signal)
        
        resolved_signals = []
        conflicts_resolved = 0
        
        for symbol, group_signals in grouped.items():
            if len(group_signals) == 1:
                resolved_signals.append(group_signals[0])
            else:
                conflicts_resolved += 1
                
                # Separa por timeframe
                signals_15m = [s for s in group_signals if s.timeframe == "15m"]
                signals_5m = [s for s in group_signals if s.timeframe == "5m"]
                
                best_signal = None
                
                if signals_15m and signals_5m:
                    # NOVA LÓGICA: Comparação 15m vs 5m
                    best_15m = max(signals_15m, key=lambda s: s.confidence)
                    best_5m = max(signals_5m, key=lambda s: s.confidence)
                    
                    # Converte confidence para score (0-100)
                    score_15m = best_15m.confidence * 100
                    score_5m = best_5m.confidence * 100
                    
                    # 5m só ganha se score >= 90 E for 10+ pontos maior que 15m
                    if (score_5m >= self.MIN_5M_SCORE and 
                        score_5m > score_15m + self.SCORE_ADVANTAGE_REQUIRED):
                        best_signal = best_5m
                        self.logger.info(f"✅ 5m VENCEU: {symbol} → {best_5m.detector_name} | Score: {score_5m:.1f} vs 15m: {score_15m:.1f}")
                    else:
                        best_signal = best_15m
                        reason = f"Score 5m: {score_5m:.1f}" 
                        if score_5m < self.MIN_5M_SCORE:
                            reason += f" < {self.MIN_5M_SCORE} (mínimo)"
                        else:
                            reason += f" não supera 15m: {score_15m:.1f} + {self.SCORE_ADVANTAGE_REQUIRED}"
                        self.logger.info(f"✅ 15m PREFERIDO: {symbol} → {best_15m.detector_name} | {reason}")
                
                elif signals_15m:
                    # Só tem 15m
                    best_signal = max(signals_15m, key=lambda s: s.confidence)
                    self.logger.debug(f"✅ 15m ÚNICO: {symbol} → {best_signal.detector_name}")
                
                elif signals_5m:
                    # Só tem 5m - aplica filtro rigoroso
                    qualified_5m = [s for s in signals_5m if s.confidence * 100 >= self.MIN_5M_SCORE]
                    if qualified_5m:
                        best_signal = max(qualified_5m, key=lambda s: s.confidence)
                        self.logger.info(f"✅ 5m QUALIFICADO: {symbol} → {best_signal.detector_name} | Score: {best_signal.confidence * 100:.1f}")
                    else:
                        # Nenhum 5m qualificado - pega o melhor mesmo assim mas com warning
                        best_signal = max(signals_5m, key=lambda s: s.confidence)
                        self.logger.warning(f"⚠️ 5m FORÇADO: {symbol} → {best_signal.detector_name} | Score: {best_signal.confidence * 100:.1f} < {self.MIN_5M_SCORE}")
                
                else:
                    # Outros timeframes - pega o melhor
                    best_signal = max(group_signals, key=lambda s: s.confidence)
                    self.logger.debug(f"✅ OUTRO TF: {symbol} → {best_signal.timeframe} {best_signal.detector_name}")
                
                if best_signal:
                    resolved_signals.append(best_signal)
        
        elapsed = time.time() - start_time
        if conflicts_resolved > 0:
            self.logger.info(f"🚨 {conflicts_resolved} conflitos resolvidos com PRIORIDADE 15m em {elapsed:.2f}s")
        
        return resolved_signals

class MultiTimeframeAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_reader = DataReader()
        self.signal_writer = EnhancedSignalWriter()
        
        enabled_timeframes = settings.get_enabled_timeframes()
        self.technical_analyzers = {tf: TechnicalAnalyzer() for tf in enabled_timeframes}
        if PATTERNS_AVAILABLE:
            self.pattern_analyzers = {tf: PatternAnalyzer() for tf in enabled_timeframes}

        # NOVA LÓGICA: Prioridade 15m + Score rigoroso para 5m
        self.conflict_resolver = PrioritySignalResolver()
        self.quality_mode = "15m_priority_5m_rigorous"

        self._last_cleanup = datetime.now()
        
        # Monitoramento em tempo real DESABILITADO
        self.real_time_monitor = None
        self.monitoring_enabled = False

        # CONFIGURAÇÕES OTIMIZADAS - sem locks
        self.MAX_SYMBOL_TIME = 10  # Reduzido para 10s
        self.MAX_VALIDATION_TIME = 3  # Reduzido para 3s
        self.DISABLE_MICROSTRUCTURE = True  # Desabilita microestrutura
        
        self.logger.info("MultiTimeframeAnalyzer com PRIORIDADE 15m inicializado:")
        self.logger.info(f"  • Timeframes: {enabled_timeframes} (PRIORIDADE: 15m)")
        self.logger.info(f"  • Score mínimo 5m: {self.conflict_resolver.MIN_5M_SCORE}")
        self.logger.info(f"  • Vantagem necessária 5m: +{self.conflict_resolver.SCORE_ADVANTAGE_REQUIRED} pontos")
        self.logger.info(f"  • Microestrutura: DESABILITADA (evita locks)")
        self.logger.info(f"  • Monitoramento tempo real: DESABILITADO (evita locks)")
        
    def analyze_symbol_all_timeframes(self, symbol: str) -> Dict[str, Any]:
        """Análise com PRIORIDADE 15m e proteção anti-lock"""
        
        symbol_start_time = time.time()
        
        # VERIFICAÇÃO RÁPIDA de sinais bloqueadores
        if self.signal_writer.check_existing_active_signals(symbol):
            return {
                'symbol': symbol, 
                'status': 'blocked', 
                'reason': 'existing_blocking_signal',
                'signals_detected': 0, 
                'signals_validated': 0, 
                'signals_saved': 0,
                'execution_time': time.time() - symbol_start_time
            }
        
        self.logger.info(f"🔍 {symbol}: Análise (prioridade 15m)")
        
        # ORDEM PRIORITÁRIA: 15m primeiro, depois 5m
        timeframes_prioritized = ["15m", "5m"]
        all_signals = []

        # Busca dados COM TIMEOUT
        market_data_by_tf = {}
        for tf in timeframes_prioritized:
            try:
                data_start = time.time()
                market_data = self.data_reader.get_latest_data(symbol, tf)
                data_time = time.time() - data_start
                
                if data_time > 2:  # Se demorou mais que 2s
                    self.logger.warning(f"⏰ {symbol} {tf}: Dados lentos ({data_time:.1f}s)")
                
                market_data_by_tf[tf] = market_data
                    
            except Exception as e:
                self.logger.warning(f"❌ {symbol} {tf}: Erro nos dados - {e}")
                market_data_by_tf[tf] = None

        # Análise por timeframe COM TIMEOUT
        for timeframe in timeframes_prioritized:
            # Verifica timeout geral
            if time.time() - symbol_start_time > self.MAX_SYMBOL_TIME:
                self.logger.warning(f"⏰ {symbol}: Timeout geral ({self.MAX_SYMBOL_TIME}s)")
                break
                
            market_data = market_data_by_tf[timeframe]
            if market_data and market_data.is_sufficient_data:
                try:
                    tf_start = time.time()
                    tf_result = self._analyze_single_timeframe_fast(symbol, timeframe, market_data)
                    tf_time = time.time() - tf_start
                    
                    tf_signals = tf_result.get('signals', [])
                    all_signals.extend(tf_signals)
                    
                    self.logger.debug(f"✓ {symbol} {timeframe}: {len(tf_signals)} sinais em {tf_time:.1f}s")
                            
                except Exception as e:
                    self.logger.warning(f"❌ {symbol} {timeframe}: Erro - {e}")

        # Resolução de conflitos com NOVA LÓGICA
        if len(all_signals) > 1:
            conflict_start = time.time()
            filtered_signals = self.conflict_resolver.resolve_conflicts(all_signals)
            conflict_time = time.time() - conflict_start
            self.logger.debug(f"🔧 {symbol}: {len(all_signals)} → {len(filtered_signals)} em {conflict_time:.2f}s")
        else:
            filtered_signals = all_signals

        # Validação SIMPLIFICADA (sem microestrutura)
        validated_signals = self._simple_validation_no_locks(filtered_signals, market_data_by_tf)

        # Gravação
        signals_saved = 0
        if validated_signals:
            signal = validated_signals[0]
            try:
                signal.status = "ACTIVE"
                
                if self.signal_writer.write_enhanced_signal(signal):
                    signals_saved = 1
                    
                    total_time = time.time() - symbol_start_time
                    score = signal.confidence * 100
                    self.logger.info(
                        f"💾 {symbol}: GRAVADO | {signal.timeframe} | {signal.detector_name} | "
                        f"Score: {score:.1f} | Entry: ${signal.entry_price:.4f} | "
                        f"Stop: ${signal.stop_loss:.4f} | T1: ${signal.targets[0]:.4f} | "
                        f"T2: ${signal.targets[1]:.4f} | {total_time:.1f}s"
                    )
                        
                else:
                    self.logger.warning(f"❌ {symbol}: FALHA NA GRAVAÇÃO")
            except Exception as e:
                self.logger.error(f"❌ {symbol}: Erro ao salvar - {e}")

        total_time = time.time() - symbol_start_time
        
        return {
            'symbol': symbol, 
            'status': 'success', 
            'signals_detected': len(all_signals), 
            'signals_validated': len(validated_signals), 
            'signals_saved': signals_saved,
            'execution_time': total_time,
            'priority_logic': '15m_first_5m_rigorous'
        }
     
    def _analyze_single_timeframe_fast(self, symbol: str, timeframe: str, market_data: MarketData) -> Dict[str, Any]:
        """Análise de timeframe RÁPIDA sem locks"""
        
        tf_config = settings.get_timeframe_config(timeframe)
        signals = []

        if len(market_data.data) < 2:
            return {'signals': []}
            
        closed_candle = market_data.data.iloc[-2]
        entry_price = float(closed_candle['close_price'])
        signal_timestamp = closed_candle['timestamp'].to_pydatetime()

        def create_signal_fast(**kwargs):
            try:
                base_args = {
                    'symbol': symbol, 
                    'timeframe': timeframe, 
                    'entry_price': entry_price, 
                    'timestamp': signal_timestamp,
                    'market_data': market_data.data,
                    'status': 'ACTIVE'
                }
                final_args = {**kwargs, **base_args}
                allowed_keys = EnhancedTradingSignal.__annotations__.keys()
                filtered_args = {k: v for k, v in final_args.items() if k in allowed_keys}
                
                signal = EnhancedTradingSignal(**filtered_args)
                
                # Evita duplicatas
                existing_detectors = [s.detector_name for s in signals]
                if signal.detector_name not in existing_detectors:
                    signals.append(signal)
                    score = signal.confidence * 100
                    self.logger.debug(f"➕ {timeframe} {signal.detector_name} | Score: {score:.1f}")
                    
            except Exception as e:
                self.logger.debug(f"⏭️ Sinal descartado: {e}")
        
        # ANÁLISE TÉCNICA LIMITADA
        if 'technical' in tf_config.enabled_detectors:
            try:
                tech_start = time.time()
                tech_analyzer = self.technical_analyzers[timeframe]
                technical_results = tech_analyzer.analyze_all(market_data, timeframe)
                raw_signals = tech_analyzer.generate_trading_signals(market_data, technical_results, timeframe)
                tech_time = time.time() - tech_start
                
                if tech_time > 3:
                    self.logger.warning(f"⏰ {symbol} {timeframe}: Técnico lento ({tech_time:.1f}s)")
                
                # LIMITE: máximo 2 sinais técnicos
                for s in raw_signals[:2]:
                    create_signal_fast(**s.__dict__)
                    
            except Exception as e:
                self.logger.warning(f"❌ Erro técnico {symbol} {timeframe}: {e}")

        # PADRÕES LIMITADOS (só se for rápido)
        if 'patterns' in tf_config.enabled_detectors and PATTERNS_AVAILABLE:
            try:
                pattern_start = time.time()
                pattern_analyzer = self.pattern_analyzers[timeframe]
                pattern_results = pattern_analyzer.analyze_all_patterns(market_data)
                raw_signals = pattern_analyzer.generate_pattern_signals(market_data, pattern_results)
                pattern_time = time.time() - pattern_start
                
                if pattern_time < 2:  # Só usa se for rápido
                    for s in raw_signals[:1]:  # Máximo 1 padrão
                        create_signal_fast(**s.__dict__)
                else:
                    self.logger.debug(f"⏰ {symbol} {timeframe}: Padrões lentos, pulando")
                    
            except Exception as e:
                self.logger.warning(f"❌ Erro padrões {symbol} {timeframe}: {e}")

        # CANDLESTICK MUITO LIMITADO
        if 'candlestick' in tf_config.enabled_detectors and CANDLESTICK_AVAILABLE:
            try:
                cs_start = time.time()
                df_for_cs = market_data.data.iloc[:-1]
                
                if len(df_for_cs) >= 10:
                    cs_signals_raw = generate_candlestick_signals(df_for_cs, symbol)
                    cs_time = time.time() - cs_start
                    
                    if cs_time < 1:  # Só usa se for muito rápido
                        # Score muito alto para candlesticks
                        ultra_high_quality = [cs for cs in cs_signals_raw if cs.get('confidence', 0) >= 0.95]
                        
                        for cs in ultra_high_quality[:1]:  # Máximo 1
                            create_signal_fast(**cs)
                    else:
                        self.logger.debug(f"⏰ {symbol} {timeframe}: Candlesticks lentos, pulando")
                        
            except Exception as e:
                self.logger.warning(f"❌ Erro candlestick {symbol} {timeframe}: {e}")

        return {'signals': signals}
   
    def _simple_validation_no_locks(self, signals: List[EnhancedTradingSignal], market_data_by_tf: Dict) -> List[EnhancedTradingSignal]:
        """Validação SUPER SIMPLES sem microestrutura para evitar locks"""
        if not signals:
            return []

        validated_signals = []
        
        for signal in signals:
            validation_start = time.time()
            
            # VALIDAÇÃO ULTRA SIMPLIFICADA
            validation_score = 0
            max_score = 2
            
            # 1. Confidence - peso maior
            if signal.timeframe == "15m":
                min_confidence = 0.70  # Mais permissivo para 15m
            else:  # 5m
                min_confidence = 0.85  # Mais rigoroso para 5m
            
            if signal.confidence >= min_confidence:
                validation_score += 2
            elif signal.confidence >= min_confidence - 0.05:  # Tolerance
                validation_score += 1
            
            # Sem outras validações para evitar locks de DB
            
            validation_time = time.time() - validation_start
            
            # Decisão
            success_rate = validation_score / max_score
            required_rate = 0.5  # Bem permissivo
            
            if success_rate >= required_rate:
                signal.status = "ACTIVE"
                validated_signals.append(signal)
                score = signal.confidence * 100
                self.logger.debug(f"✅ {signal.symbol} {signal.timeframe}: Score {score:.1f} validado em {validation_time:.2f}s")
            else:
                score = signal.confidence * 100
                self.logger.debug(f"❌ {signal.symbol} {signal.timeframe}: Score {score:.1f} rejeitado")

        return validated_signals

    def run_continuous_multi_timeframe_analysis(self, base_interval: int = None):
        """Execução contínua com PRIORIDADE 15m - SEM LOCKS"""
        if base_interval is None: 
           base_interval = settings.system.analysis_interval
        
        self.logger.info("🚀 ANÁLISE CONTÍNUA - PRIORIDADE 15m (SEM LOCKS)")
        self.logger.info(f"📊 Lógica: 15m preferido, 5m precisa score >= {self.conflict_resolver.MIN_5M_SCORE}")
        self.logger.info(f"⚡ 5m só vence se superar 15m em +{self.conflict_resolver.SCORE_ADVANTAGE_REQUIRED} pontos")
        self.logger.info("🚫 Microestrutura e monitoramento DESABILITADOS (evita locks)")
        
        valid_symbols = self.data_reader.get_valid_symbols_for_analysis()
        
        if not valid_symbols:
            self.logger.error("❌ Nenhum símbolo válido encontrado!")
            return
        
        self.logger.info(f"✅ Símbolos: {len(valid_symbols)} | Prioridade: 15m > 5m")
        
        cycle_count = 0
        
        while True:
            try:
                cycle_count += 1
                cycle_start = time.time()
                total_signals = 0
                blocked_count = 0
                error_count = 0
                
                self.logger.info(f"🔄 Ciclo {cycle_count} (15m prioridade)")
                
                # Limpeza automática
                if cycle_count % 10 == 1:
                    self._perform_quick_cleanup()
                
                # Re-verifica símbolos
                if cycle_count % 20 == 1 and cycle_count > 1:
                    valid_symbols = self.data_reader.get_valid_symbols_for_analysis()
                
                for i, symbol in enumerate(valid_symbols, 1):
                    try:
                        symbol_start = time.time()
                        
                        result = self.analyze_symbol_all_timeframes(symbol)
                        symbol_time = time.time() - symbol_start
                        
                        if result.get('status') == 'blocked':
                            blocked_count += 1
                            self.logger.debug(f"🚫 {symbol} ({i}/{len(valid_symbols)}): BLOQUEADO")
                        elif result.get('status') == 'error':
                            error_count += 1
                            self.logger.warning(f"❌ {symbol} ({i}/{len(valid_symbols)}): ERRO")
                        else:
                            signals_saved = result.get('signals_saved', 0)
                            total_signals += signals_saved
                            if signals_saved > 0:
                                self.logger.info(f"🎯 {symbol} ({i}/{len(valid_symbols)}): {signals_saved} ATIVO em {symbol_time:.1f}s")
                            else:
                                self.logger.debug(f"✓ {symbol} ({i}/{len(valid_symbols)}): OK em {symbol_time:.1f}s")
                        
                        time.sleep(0.1)  # Pausa para evitar sobrecarga
                        
                    except Exception as e:
                        error_count += 1
                        self.logger.error(f"❌ Erro em {symbol}: {e}")
                        continue
                
                cycle_time = time.time() - cycle_start
                
                self.logger.info(
                    f"✅ Ciclo {cycle_count}: {total_signals} novos ACTIVE (15m prioridade) | "
                    f"{blocked_count} bloqueados | {error_count} erros | {cycle_time:.1f}s"
                )
                
            except KeyboardInterrupt:
                self.logger.info("🛑 Análise interrompida pelo usuário")
                break
            except Exception as e:
                self.logger.error(f"❌ Erro crítico no ciclo: {e}")
                time.sleep(10)
            
            self.logger.info(f"⏳ Aguardando {base_interval}s...")
            time.sleep(base_interval)
    
    def _perform_quick_cleanup(self):
        """Limpeza rápida sem locks"""
        now = datetime.now()
        hours_since_cleanup = (now - self._last_cleanup).total_seconds() / 3600
        
        if hours_since_cleanup >= settings.system.cleanup_interval_hours:
            self.logger.info("🧹 Limpeza rápida...")
            
            try:
                cleanup_start = time.time()
                killed_count = self.signal_writer.mark_expired_signals_as_killed()
                moved_counts = self.signal_writer.move_inactive_signals_to_backup()
                total_moved = sum(moved_counts.values())
                cleanup_time = time.time() - cleanup_start
                
                if killed_count > 0 or total_moved > 0:
                    self.logger.info(f"✅ Limpeza: {killed_count} EXPIRED + {total_moved} movidos em {cleanup_time:.1f}s")
                    
                self._last_cleanup = now
                
            except Exception as e:
                self.logger.error(f"❌ Erro na limpeza: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Status com nova lógica de prioridade"""
        try:
            symbols = settings.get_analysis_symbols()
            enabled_timeframes = settings.get_enabled_timeframes()
            
            components = {
                'database': 'OK_NO_LOCKS',
                'technical_analyzer': 'OPTIMIZED',
                'patterns_analyzer': 'LIMITED' if PATTERNS_AVAILABLE else 'DISABLED',
                'candlestick_analyzer': 'LIMITED' if CANDLESTICK_AVAILABLE else 'DISABLED',
                'microstructure_validation': 'DISABLED_NO_LOCKS',
                'quality_system': '15M_PRIORITY_5M_RIGOROUS',
                'signal_status_logic': 'CORRECTED_2_TARGETS',
                'new_signals_status': 'ALWAYS_ACTIVE',
                'blocking_logic': 'ACTIVE_AND_TARGET_1_HIT_ONLY',
                'real_time_monitoring': 'DISABLED_NO_LOCKS',
                'priority_logic': '15M_PREFERRED_5M_RIGOROUS',
                'anti_lock_protection': 'ACTIVE'
            }
            
            return {
                'status': 'OK',
                'system_type': 'Trading Analyzer - PRIORIDADE 15m + SEM LOCKS',
                'timestamp': datetime.now().isoformat(),
                'components': components,
                'symbols_available': len(symbols),
                'enabled_timeframes': enabled_timeframes,
                'signal_flow': 'ACTIVE → TARGET_1_HIT → TARGET_2_HIT/STOP_HIT',
                'blocking_states': ['ACTIVE', 'TARGET_1_HIT'],
                'completed_states': ['TARGET_2_HIT', 'STOP_HIT', 'EXPIRED'],
                'priority_logic': {
                    'preferred_timeframe': '15m',
                    'min_5m_score': self.conflict_resolver.MIN_5M_SCORE,
                    'advantage_required': self.conflict_resolver.SCORE_ADVANTAGE_REQUIRED,
                    'description': '15m tem prioridade, 5m precisa score >= 90 e superar 15m em +10 pontos'
                },
                'anti_lock_settings': {
                    'microstructure_disabled': self.DISABLE_MICROSTRUCTURE,
                    'monitoring_disabled': True,
                    'max_symbol_time': self.MAX_SYMBOL_TIME,
                    'max_validation_time': self.MAX_VALIDATION_TIME,
                    'connection_optimized': True
                },
                'configuration': {
                    'multi_timeframe_enabled': True,
                    'timeframes_active': enabled_timeframes,
                    'single_signal_per_crypto': True,
                    'signal_status_corrected': True,
                    'targets_count': 2,
                    'new_signals_always_active': True,
                    'priority_15m_over_5m': True,
                    'rigorous_5m_scoring': True,
                    'anti_lock_protection': True,
                    'no_database_locks': True
                }
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    # Métodos de compatibilidade
    def analyze_symbol(self, symbol: str, timeframe: str = None) -> Dict[str, Any]:
        return self.analyze_symbol_all_timeframes(symbol)

    def analyze_multiple_symbols(self, symbols: List[str] = None, timeframe: str = None) -> Dict[str, Any]:
        if symbols is None:
            symbols = settings.get_analysis_symbols()
        
        results = {}
        successful_analyses = 0
        total_signals = 0
        blocked_analyses = 0
        start_time = time.time()
        
        for symbol in symbols:
            try:
                result = self.analyze_symbol_all_timeframes(symbol)
                results[symbol] = result
                if result.get('status') == 'success':
                    successful_analyses += 1
                    total_signals += result.get('signals_saved', 0)
                elif result.get('status') == 'blocked':
                    blocked_analyses += 1
            except Exception as e:
                results[symbol] = {'status': 'error', 'message': str(e)}
        
        results['_summary'] = {
            'symbols_analyzed': len(symbols),
            'successful_analyses': successful_analyses,
            'blocked_analyses': blocked_analyses,
            'total_signals_generated': total_signals,
            'total_execution_time': time.time() - start_time,
            'priority_logic': '15M_PREFERRED_5M_RIGOROUS',
            'anti_lock_protection': True,
            'signal_status_logic': 'CORRECTED - ACTIVE → TARGET_1_HIT → TARGET_2_HIT/STOP_HIT'
        }
        
        return results

    def cleanup_old_data(self, days: int) -> Dict[str, Any]:
        """Limpeza manual"""
        try:
            moved_counts = self.signal_writer.move_inactive_signals_to_backup()
            total_moved = sum(moved_counts.values())
            
            return {
                'status': 'success',
                'removed_signals': total_moved,
                'details': moved_counts,
                'message': f'Limpeza concluída: {total_moved} sinais finalizados movidos para backup',
                'signal_status_info': 'Apenas TARGET_2_HIT, STOP_HIT, EXPIRED, MANUALLY_CLOSED são considerados finalizados',
                'priority_logic': '15M_PREFERRED_5M_RIGOROUS'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

# Alias para compatibilidade
TradingAnalyzer = MultiTimeframeAnalyzer