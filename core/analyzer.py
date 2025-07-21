# analyzer.py - VERSÃO COM ANTI-CONFLITO INTEGRADO

import logging
import time
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta

from core.data_reader import DataReader, MarketData
from core.signal_writer import EnhancedSignalWriter, EnhancedTradingSignal
from indicators.technical import TechnicalAnalyzer, RSIAnalyzer 

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

from config.settings import settings


class SignalConflictResolver:
    """Resolve conflitos entre sinais automaticamente"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def resolve_conflicts(self, signals: List[EnhancedTradingSignal]) -> List[EnhancedTradingSignal]:
        """
        Resolve conflitos garantindo apenas UM sinal por símbolo por timeframe
        
        Prioridades:
        1. Maior confidence
        2. Detector técnico > padrões > candlestick  
        3. Mais recente
        """
        if not signals:
            return signals
        
        # Agrupa por símbolo + timeframe
        grouped = {}
        for signal in signals:
            key = f"{signal.symbol}_{signal.timeframe}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(signal)
        
        resolved_signals = []
        conflicts_resolved = 0
        
        for key, group_signals in grouped.items():
            if len(group_signals) == 1:
                # Sem conflito
                resolved_signals.append(group_signals[0])
            else:
                # CONFLITO DETECTADO - RESOLVER
                conflicts_resolved += 1
                symbol = group_signals[0].symbol
                timeframe = group_signals[0].timeframe
                
                self.logger.warning(f"🚨 CONFLITO: {symbol} {timeframe} - {len(group_signals)} sinais")
                
                # Log detalhado do conflito
                for signal in group_signals:
                    self.logger.warning(f"   • {signal.signal_type} | {signal.detector_name} | Conf: {signal.confidence:.3f}")
                
                # Escolhe o melhor sinal
                best_signal = self._select_best_signal(group_signals)
                resolved_signals.append(best_signal)
                
                self.logger.info(f"✅ RESOLVIDO: {symbol} → {best_signal.signal_type} | {best_signal.detector_name} | Conf: {best_signal.confidence:.3f}")
        
        if conflicts_resolved > 0:
            self.logger.warning(f"🚨 Total de conflitos resolvidos: {conflicts_resolved}")
        
        return resolved_signals
    
    def _select_best_signal(self, signals: List[EnhancedTradingSignal]) -> EnhancedTradingSignal:
        """Seleciona o melhor sinal baseado em critérios hierárquicos"""
        
        # CRITÉRIO 1: Maior confidence
        max_confidence = max(s.confidence for s in signals)
        high_confidence_signals = [s for s in signals if s.confidence == max_confidence]
        
        if len(high_confidence_signals) == 1:
            return high_confidence_signals[0]
        
        # CRITÉRIO 2: Prioridade por tipo de detector
        detector_priority = {
            'technical': 10,     # MAIOR prioridade (RSI, MACD)
            'pattern': 5,        # Média prioridade (padrões gráficos)
            'candlestick': 1     # MENOR prioridade (mais propenso a conflitos)
        }
        
        # Encontra a maior prioridade disponível
        best_priority = max(detector_priority.get(s.detector_type, 0) for s in high_confidence_signals)
        priority_signals = [s for s in high_confidence_signals 
                          if detector_priority.get(s.detector_type, 0) == best_priority]
        
        if len(priority_signals) == 1:
            return priority_signals[0]
        
        # CRITÉRIO 3: Detector específico (dentro do mesmo tipo)
        specific_detector_priority = {
            # Técnicos
            'RSI': 12,
            'MACD': 11, 
            # Padrões
            'Head_and_Shoulders': 7,
            'Double_Top': 6,
            'Cup_and_Handle': 6,
            # Candlesticks (só se chegou até aqui)
            'Bullish_Engulfing': 3,
            'Bearish_Engulfing': 3,
            'Hammer': 2,
            'Shooting_Star': 2
        }
        
        best_specific = max(specific_detector_priority.get(s.detector_name, 0) for s in priority_signals)
        if best_specific > 0:
            specific_signals = [s for s in priority_signals 
                              if specific_detector_priority.get(s.detector_name, 0) == best_specific]
            if len(specific_signals) == 1:
                return specific_signals[0]
            priority_signals = specific_signals
        
        # CRITÉRIO 4: Mais recente
        return max(priority_signals, key=lambda s: s.timestamp)


class MultiTimeframeAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_reader = DataReader()
        self.signal_writer = EnhancedSignalWriter()
        self.technical_analyzers = {tf: TechnicalAnalyzer() for tf in settings.get_enabled_timeframes()}
        if PATTERNS_AVAILABLE:
            self.pattern_analyzers = {tf: PatternAnalyzer() for tf in settings.get_enabled_timeframes()}

        # Sistema anti-conflito
        self.conflict_resolver = SignalConflictResolver()

        # Cache para evitar buscar microestrutura desnecessariamente
        self._microstructure_cache = {}
        self._microstructure_last_check = None
        self._microstructure_available = None

        self.logger.info("MultiTimeframeAnalyzer inicializado com SISTEMA ANTI-CONFLITO integrado.")

    def analyze_symbol_all_timeframes(self, symbol: str) -> Dict[str, Any]:
        """Análise com resolução automática de conflitos"""
        self.logger.info(f"Análise iniciada para: {symbol}")
        enabled_timeframes = settings.get_enabled_timeframes()
        all_signals = []

        market_data_by_tf = {}
        for tf in enabled_timeframes:
            try:
                market_data = self.data_reader.get_latest_data(symbol, tf)
                market_data_by_tf[tf] = market_data
            except Exception as e:
                self.logger.error(f"Erro ao buscar dados para {symbol} {tf}: {e}")
                market_data_by_tf[tf] = None

        for timeframe, market_data in market_data_by_tf.items():
            if market_data and market_data.is_sufficient_data:
                try:
                    tf_result = self._analyze_single_timeframe(symbol, timeframe, market_data)
                    all_signals.extend(tf_result.get('signals', []))
                except Exception as e:
                    self.logger.error(f"Erro na análise de {symbol} em {timeframe}: {e}")
            else:
                self.logger.warning(f"Análise para {symbol} em {timeframe} pulada (dados insuficientes).")

        # RESOLVE CONFLITOS ANTES DA VALIDAÇÃO
        if len(all_signals) > 1:
            self.logger.debug(f"Verificando conflitos em {len(all_signals)} sinais para {symbol}")
            all_signals = self.conflict_resolver.resolve_conflicts(all_signals)
            self.logger.debug(f"Após resolução de conflitos: {len(all_signals)} sinais para {symbol}")

        # Sistema de validação INTELIGENTE  
        validated_signals = self._intelligent_signal_validation(all_signals, market_data_by_tf)

        signals_saved = 0
        if validated_signals:
            validated_signals.sort(key=lambda s: s.confidence, reverse=True)
            for signal in validated_signals[:settings.system.max_total_signals_per_symbol]:
                try:
                    if self.signal_writer.write_enhanced_signal(signal):
                        signals_saved += 1
                        self.logger.info(f"🎯 SINAL APROVADO: {symbol} | {signal.detector_name} | {signal.signal_type} | Conf: {signal.confidence:.3f}")
                except Exception as e:
                    self.logger.error(f"Erro ao salvar sinal para {symbol}: {e}")

        return {
            'symbol': symbol, 
            'status': 'success', 
            'signals_detected': len(all_signals), 
            'signals_validated': len(validated_signals), 
            'signals_saved': signals_saved
        }

    def _analyze_single_timeframe(self, symbol: str, timeframe: str, market_data: MarketData) -> Dict[str, Any]:
        """Análise de um único timeframe COM PROTEÇÃO ANTI-CONFLITO"""
        tf_config = settings.get_timeframe_config(timeframe)
        signals = []

        if len(market_data.data) < 2:
            return {'signals': []}
            
        closed_candle = market_data.data.iloc[-2]
        entry_price = float(closed_candle['close_price'])
        signal_timestamp = closed_candle['timestamp'].to_pydatetime()

        def create_valid_signal(**kwargs):
            try:
                base_args = {
                    'symbol': symbol, 
                    'timeframe': timeframe, 
                    'entry_price': entry_price, 
                    'timestamp': signal_timestamp
                }
                final_args = {**kwargs, **base_args}
                allowed_keys = EnhancedTradingSignal.__annotations__.keys()
                filtered_args = {k: v for k, v in final_args.items() if k in allowed_keys}
                
                signal = EnhancedTradingSignal(**filtered_args)
                signals.append(signal)
                self.logger.debug(f"Sinal criado: {signal.detector_name} | {signal.signal_type} | {signal.confidence:.3f}")
            except Exception as e:
                self.logger.warning(f"Sinal para {symbol} em {timeframe} descartado: {e}")

        # ANÁLISE TÉCNICA (prioridade máxima)
        if 'technical' in tf_config.enabled_detectors:
            try:
                tech_analyzer = self.technical_analyzers[timeframe]
                technical_results = tech_analyzer.analyze_all(market_data, timeframe)
                raw_signals = tech_analyzer.generate_trading_signals(market_data, technical_results, timeframe)
                for s in raw_signals:
                    create_valid_signal(**s.__dict__)
                self.logger.debug(f"Sinais técnicos gerados para {symbol} {timeframe}: {len(raw_signals)}")
            except Exception as e:
                self.logger.error(f"Erro na análise técnica para {symbol} {timeframe}: {e}")

        # ANÁLISE DE PADRÕES (prioridade média)
        if 'patterns' in tf_config.enabled_detectors and PATTERNS_AVAILABLE:
            try:
                pattern_analyzer = self.pattern_analyzers[timeframe]
                pattern_results = pattern_analyzer.analyze_all_patterns(market_data)
                raw_signals = pattern_analyzer.generate_pattern_signals(market_data, pattern_results)
                for s in raw_signals:
                     create_valid_signal(**s.__dict__)
                self.logger.debug(f"Sinais de padrões gerados para {symbol} {timeframe}: {len(raw_signals)}")
            except Exception as e:
                self.logger.error(f"Erro na análise de padrões para {symbol} {timeframe}: {e}")

        # ANÁLISE DE CANDLESTICK (prioridade baixa - mais limitada)
        if 'candlestick' in tf_config.enabled_detectors and CANDLESTICK_AVAILABLE:
            try:
                df_for_cs = market_data.data.iloc[:-1]
                if not df_for_cs.empty:
                    # LIMITA CANDLESTICK para evitar excesso de sinais conflitantes
                    cs_signals_raw = generate_candlestick_signals(df_for_cs, symbol)
                    
                    # FILTRA apenas padrões de alta confiança
                    high_quality_cs = [cs for cs in cs_signals_raw if cs.get('confidence', 0) >= 0.8]
                    
                    for cs in high_quality_cs[:2]:  # Máximo 2 sinais de candlestick
                        create_valid_signal(**cs)
                    
                    self.logger.debug(f"Sinais de candlestick gerados para {symbol} {timeframe}: {len(high_quality_cs)} (de {len(cs_signals_raw)} detectados)")
            except Exception as e:
                self.logger.error(f"Erro na análise de candlestick para {symbol} {timeframe}: {e}")

        self.logger.debug(f"Timeframe {timeframe} gerou {len(signals)} sinais para {symbol}")
        return {'signals': signals}

    def _intelligent_signal_validation(self, signals: List[EnhancedTradingSignal], market_data_by_tf: Dict) -> List[EnhancedTradingSignal]:
        """Sistema de validação INTELIGENTE com resolução final de conflitos"""
        if not signals:
            return []

        validated_signals = []
        
        # Verifica disponibilidade de microestrutura uma vez por ciclo
        microstructure_available = self._check_microstructure_availability()
        
        for signal in signals:
            validation_score = 0
            validation_notes = []
            max_score = 0

            # 1. VALIDAÇÃO DE MICROESTRUTURA (se disponível)
            max_score += 3
            primary_validation_passed = False
            if microstructure_available:
                is_micro_valid, micro_note = self._validate_with_microstructure_smart(signal)
                if is_micro_valid:
                    validation_score += 3
                    validation_notes.append(f"✅ Micro: {micro_note}")
                    primary_validation_passed = True
                else:
                    # Anota a falha da microestrutura, o fallback será usado a seguir.
                    validation_notes.append(f"⚠️  Micro: {micro_note}")

            # Use o fallback de momentum se a validação primária não passou (ou não estava disponível)
            if not primary_validation_passed:
                is_momentum_valid, momentum_note = self._validate_with_technical_momentum(signal, market_data_by_tf)
                if is_momentum_valid:
                    # O fallback concede 2 pontos em vez de 3, pois é uma confirmação mais fraca.
                    validation_score += 2
                    validation_notes.append(f"✅ Momentum Fallback: {momentum_note}")
                else:
                    # Se o fallback também falhar, anote a falha final.
                    validation_notes.append(f"❌ Momentum Fallback: {momentum_note}")


            # 2. VALIDAÇÃO DE VOLUME
            max_score += 2
            is_volume_valid, volume_note = self._validate_with_volume_smart(signal, market_data_by_tf)
            if is_volume_valid:
                validation_score += 2
                validation_notes.append(f"✅ Volume: {volume_note}")
            else:
                validation_notes.append(f"❌ Volume: {volume_note}")

            # 3. VALIDAÇÃO DE CONFIDENCE
            max_score += 1
            if signal.confidence >= settings.analysis.confidence_threshold:
                validation_score += 1
                validation_notes.append(f"✅ Conf: {signal.confidence:.3f}")
            else:
                validation_notes.append(f"❌ Conf: {signal.confidence:.3f}")

            # DECISÃO INTELIGENTE
            success_rate = validation_score / max_score
            
            # Critérios flexíveis baseados na disponibilidade de dados
            if microstructure_available:
                # Com microestrutura: mais rigoroso (70% de aprovação)
                required_rate = 0.70
            else:
                # Sem microestrutura: mais flexível (60% de aprovação)
                required_rate = 0.60

            if success_rate >= required_rate:
                signal.market_conditions['validation_score'] = validation_score
                signal.market_conditions['max_score'] = max_score
                signal.market_conditions['success_rate'] = success_rate
                signal.market_conditions['validation_notes'] = validation_notes
                validated_signals.append(signal)
                
                self.logger.info(f"✅ SINAL VALIDADO: {signal.symbol} | {signal.detector_name} | Score: {validation_score}/{max_score} | Notas: {validation_notes}")
            else:
                # Log de FALHA na validação (MUITO IMPORTANTE PARA DEBUG)
                self.logger.warning(f"❌ SINAL REJEITADO: {signal.symbol} | {signal.detector_name} | Score: {validation_score}/{max_score} < {required_rate:.2f} | Notas: {validation_notes}")

        # VERIFICAÇÃO FINAL DE CONFLITOS (segurança extra)
        if len(validated_signals) > 1:
            validated_signals = self.conflict_resolver.resolve_conflicts(validated_signals)
        
        return validated_signals

    def _check_microstructure_availability(self) -> bool:
        """Verifica se microestrutura está disponível (cache de 5 minutos)"""
        now = datetime.now()
        
        # Usa cache por 5 minutos
        if (self._microstructure_last_check and 
            (now - self._microstructure_last_check).seconds < 300 and
            self._microstructure_available is not None):
            return self._microstructure_available
        
        try:
            test_result = self.data_reader.test_microstructure_connection()
            self._microstructure_available = (
                test_result.get('table_exists', False) and 
                test_result.get('has_data', False) and
                test_result.get('sample_data_count', 0) > 100  # Pelo menos 100 registros
            )
            self._microstructure_last_check = now
            
            if self._microstructure_available:
                self.logger.debug(f"✅ Microestrutura disponível: {test_result.get('sample_data_count', 0)} registros")
            else:
                self.logger.debug("⚠️ Microestrutura indisponível - usando validação técnica")
                
        except Exception as e:
            self._microstructure_available = False
            self._microstructure_last_check = now
            self.logger.warning(f"❌ Erro ao verificar microestrutura: {e}")
        
        return self._microstructure_available

    def _validate_with_microstructure_smart(self, signal: EnhancedTradingSignal) -> Tuple[bool, str]:
        """Validação de microestrutura INTELIGENTE"""
        try:
            conf = settings.validation
            
            # Busca dados com janela mais ampla (últimos 3 minutos em vez de futuros)
            search_start = signal.timestamp - timedelta(minutes=3)
            search_end = signal.timestamp + timedelta(minutes=2)
            
            micro_df = self.data_reader.get_microstructure_for_validation(
                signal.symbol,
                search_start,
                5  # 5 minutos de janela
            )

            if micro_df is None or micro_df.empty:
                # Tenta busca mais ampla
                search_start = signal.timestamp - timedelta(minutes=10)
                micro_df = self.data_reader.get_microstructure_for_validation(
                    signal.symbol,
                    search_start,
                    15  # 15 minutos de janela
                )
                
                if micro_df is None or micro_df.empty:
                    return False, "Sem dados de microestrutura na janela estendida"

            rsi_analyzer = RSIAnalyzer()
            micro_rsi = rsi_analyzer.calculate_rsi(micro_df['close_price'])

            if micro_rsi.empty or len(micro_rsi) < 5:
                return False, "RSI de microestrutura insuficiente"

            # Análise de momentum mais sofisticada
            recent_rsi = micro_rsi.tail(3).mean()  # Média dos últimos 3 pontos
            rsi_trend = micro_rsi.tail(3).iloc[-1] - micro_rsi.tail(3).iloc[0]  # Tendência

            if 'BUY' in signal.signal_type:
                momentum_ok = recent_rsi > conf.buy_momentum_threshold
                trend_ok = rsi_trend > -5  # Não deve estar caindo muito
                if momentum_ok and trend_ok:
                    return True, f"Momentum BUY confirmado (RSI: {recent_rsi:.1f}, Trend: {rsi_trend:+.1f})"
                return False, f"Momentum BUY fraco (RSI: {recent_rsi:.1f}, Trend: {rsi_trend:+.1f})"
            
            elif 'SELL' in signal.signal_type:
                momentum_ok = recent_rsi < conf.sell_momentum_threshold
                trend_ok = rsi_trend < 5  # Não deve estar subindo muito
                if momentum_ok and trend_ok:
                    return True, f"Momentum SELL confirmado (RSI: {recent_rsi:.1f}, Trend: {rsi_trend:+.1f})"
                return False, f"Momentum SELL fraco (RSI: {recent_rsi:.1f}, Trend: {rsi_trend:+.1f})"
            
            return False, "Tipo de sinal não reconhecido"
            
        except Exception as e:
            return False, f"Erro na validação: {str(e)[:50]}"

    # Substitua a função inteira por esta versão corrigida
    def _validate_with_technical_momentum(self, signal: EnhancedTradingSignal, market_data_by_tf: Dict) -> Tuple[bool, str]:
        """Validação por momentum técnico quando microestrutura não disponível (LÓGICA CORRIGIDA)"""
        try:
            market_data = market_data_by_tf.get(signal.timeframe)
            if not market_data or len(market_data.data) < 20:
                return True, "Dados insuficientes para momentum - aprovado por padrão"

            rsi_analyzer = RSIAnalyzer()
            rsi = rsi_analyzer.calculate_rsi(market_data.data['close_price'])
            
            if rsi.empty or len(rsi) < 5:
                return True, "RSI insuficiente para momentum - aprovado por padrão"

            current_rsi = rsi.iloc[-1]
            rsi_trend = rsi.iloc[-1] - rsi.iloc[-3] if len(rsi) >= 3 else 0

            if 'BUY' in signal.signal_type:
                # Para COMPRA: momentum deve ser de alta ou neutro (RSI > 45) e sem forte queda recente.
                if current_rsi > 45 and rsi_trend > -5:
                    return True, f"Momentum técnico OK (RSI: {current_rsi:.1f}, Trend: {rsi_trend:+.1f})"
                return False, f"Momentum técnico contrário (RSI: {current_rsi:.1f}, Trend: {rsi_trend:+.1f})"
            
            elif 'SELL' in signal.signal_type:
                # Para VENDA: momentum deve ser de baixa ou neutro (RSI < 55) e sem forte alta recente.
                if current_rsi < 55 and rsi_trend < 5:
                    return True, f"Momentum técnico OK (RSI: {current_rsi:.1f}, Trend: {rsi_trend:+.1f})"
                return False, f"Momentum técnico contrário (RSI: {current_rsi:.1f}, Trend: {rsi_trend:+.1f})"
            
            return True, "Tipo de sinal indefinido - aprovado"
            
        except Exception as e:
            self.logger.warning(f"Erro na validação de momentum, aprovando por segurança: {e}")
            return True, f"Erro no momentum - aprovado: {str(e)[:30]}"
    
    
    def _validate_with_volume_smart(self, signal: EnhancedTradingSignal, market_data_by_tf: Dict) -> Tuple[bool, str]:
        """Validação de volume FLEXÍVEL"""
        try:
            market_data = market_data_by_tf.get(signal.timeframe)
            if not market_data or len(market_data.data) < 22:
                return True, "Volume: dados insuficientes - aprovado"

            volume_ma_period = min(20, len(market_data.data) - 2)
            signal_candle_index = -2
            
            avg_volume = market_data.data['volume'].iloc[signal_candle_index - volume_ma_period : signal_candle_index].mean()
            signal_candle_volume = market_data.data['volume'].iloc[signal_candle_index]

            if avg_volume <= 0:
                return True, "Volume: média zero - aprovado"

            volume_ratio = signal_candle_volume / avg_volume
            
            # Thresholds flexíveis baseados no timeframe e confidence
            base_threshold = settings.get_timeframe_config(signal.timeframe).volume_threshold_multiplier
            
            # Ajusta threshold baseado na confidence do sinal
            if signal.confidence >= 0.8:
                # Sinais de alta confidence: threshold mais baixo
                adjusted_threshold = base_threshold * 0.8
            elif signal.confidence >= 0.7:
                adjusted_threshold = base_threshold * 0.9
            else:
                adjusted_threshold = base_threshold

            if volume_ratio >= adjusted_threshold:
                return True, f"Volume confirmado ({volume_ratio:.2f} >= {adjusted_threshold:.2f})"
            
            # Segunda chance: se o volume está pelo menos 50% do threshold
            if volume_ratio >= adjusted_threshold * 0.5:
                return True, f"Volume aceitável ({volume_ratio:.2f} >= {adjusted_threshold*0.5:.2f})"
            
            return False, f"Volume insuficiente ({volume_ratio:.2f} < {adjusted_threshold:.2f})"
            
        except Exception as e:
            return True, f"Volume: erro - aprovado: {str(e)[:30]}"

    def run_continuous_multi_timeframe_analysis(self, base_interval: int = None):
        """Execução contínua com sistema anti-conflito"""
        if base_interval is None: 
            base_interval = settings.system.analysis_interval
        symbols_to_analyze = settings.get_analysis_symbols()
        
        self.logger.info(f"🚀 Iniciando análise contínua COM SISTEMA ANTI-CONFLITO")
        self.logger.info(f"⏱️ Intervalo: {base_interval}s | Símbolos: {len(symbols_to_analyze)} | Anti-conflito: ATIVO")
        
        cycle_count = 0
        while True:
            try:
                cycle_count += 1
                cycle_start = time.time()
                total_signals = 0
                
                self.logger.info(f"🔄 Ciclo {cycle_count} iniciado")
                
                for i, symbol in enumerate(symbols_to_analyze, 1):
                    try:
                        symbol_start = time.time()
                        result = self.analyze_symbol_all_timeframes(symbol)
                        symbol_time = time.time() - symbol_start
                        
                        signals_saved = result.get('signals_saved', 0)
                        total_signals += signals_saved
                        
                        status_icon = "🎯" if signals_saved > 0 else "✓"
                        self.logger.info(f"{status_icon} {symbol} ({i}/{len(symbols_to_analyze)}): {signals_saved} sinais em {symbol_time:.1f}s")
                        
                        time.sleep(0.5)  # Pequena pausa entre símbolos
                    except Exception as e:
                        self.logger.error(f"❌ Erro em {symbol}: {e}")
                        continue
                
                cycle_time = time.time() - cycle_start
                self.logger.info(f"✅ Ciclo {cycle_count} concluído: {total_signals} sinais em {cycle_time:.1f}s | Sistema anti-conflito: ATIVO")
                
            except KeyboardInterrupt:
                self.logger.info("🛑 Análise interrompida pelo usuário")
                break
            except Exception as e:
                self.logger.error(f"❌ Erro no ciclo: {e}", exc_info=True)
            
            self.logger.info(f"⏳ Aguardando {base_interval}s para próximo ciclo...")
            time.sleep(base_interval)

    # Métodos de compatibilidade (mantidos do código anterior)
    def get_system_status(self) -> Dict[str, Any]:
        """Retorna status do sistema"""
        try:
            symbols = settings.get_analysis_symbols()
            enabled_timeframes = settings.get_enabled_timeframes()
            
            # Verifica microestrutura
            microstructure_status = self._check_microstructure_availability()
            
            components = {
                'database': 'OK' if self._test_database_connection() else 'ERROR',
                'technical_analyzer': 'OK',
                'patterns_analyzer': 'OK' if PATTERNS_AVAILABLE else 'NOT_AVAILABLE',
                'candlestick_analyzer': 'OK' if CANDLESTICK_AVAILABLE else 'NOT_AVAILABLE',
                'microstructure_validation': 'OK' if microstructure_status else 'FALLBACK_MODE',
                'anti_conflict_system': 'ACTIVE'  # NOVO STATUS
            }
            
            return {
                'status': 'OK' if all(c in ['OK', 'NOT_AVAILABLE', 'FALLBACK_MODE', 'ACTIVE'] for c in components.values()) else 'ERROR',
                'system_type': 'Intelligent Multi-Timeframe Trading Analyzer with Anti-Conflict System',
                'timestamp': datetime.now().isoformat(),
                'components': components,
                'symbols_available': len(symbols),
                'enabled_timeframes': enabled_timeframes,
                'microstructure_available': microstructure_status,
                'configuration': {
                    'multi_timeframe_enabled': settings.system.multi_timeframe_enabled,
                    'analysis_interval': settings.system.analysis_interval,
                    'intelligent_validation': True,
                    'anti_conflict_system': True  # NOVO
                }
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def _test_database_connection(self) -> bool:
        """Testa conexão com banco de dados"""
        try:
            test_data = self.data_reader.get_latest_data('BTC', '1h')
            return test_data is not None
        except Exception:
            return False

    def analyze_symbol(self, symbol: str, timeframe: str = None) -> Dict[str, Any]:
        """Análise de um símbolo específico"""
        return self.analyze_symbol_all_timeframes(symbol)

    def analyze_multiple_symbols(self, symbols: List[str] = None, timeframe: str = None) -> Dict[str, Any]:
        """Análise de múltiplos símbolos"""
        if symbols is None:
            symbols = settings.get_analysis_symbols()
        
        results = {}
        successful_analyses = 0
        total_signals = 0
        start_time = time.time()
        
        for symbol in symbols:
            try:
                result = self.analyze_symbol_all_timeframes(symbol)
                results[symbol] = result
                if result.get('status') == 'success':
                    successful_analyses += 1
                    total_signals += result.get('signals_saved', 0)
            except Exception as e:
                results[symbol] = {'status': 'error', 'message': str(e)}
        
        results['_summary'] = {
            'symbols_analyzed': len(symbols),
            'successful_analyses': successful_analyses,
            'total_signals_generated': total_signals,
            'total_execution_time': time.time() - start_time
        }
        
        return results

    def get_signals_comparison(self, days: int) -> Dict[str, Any]:
        """Comparação de sinais (implementação básica)"""
        try:
            return {
                'comparison_period_days': days,
                'general_stats': {
                    'total_signals': 0,
                    'active_signals': 0,
                    'symbols_count': len(settings.get_analysis_symbols()),
                    'avg_confidence': 0.75,
                    'by_type': {'BUY_LONG': 0, 'SELL_SHORT': 0}
                },
                'note': 'Implementação básica - requer histórico de performance'
            }
        except Exception as e:
            return {'error': str(e)}

    def cleanup_old_data(self, days: int) -> Dict[str, Any]:
        """Limpeza de dados antigos"""
        try:
            return {
                'status': 'success',
                'removed_signals': 0,
                'message': f'Limpeza simulada para sinais com mais de {days} dias'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}


# Alias para manter compatibilidade
TradingAnalyzer = MultiTimeframeAnalyzer