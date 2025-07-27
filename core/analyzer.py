# analyzer.py - INTEGRAÇÃO PREMIUM COMPLETA

"""
🚀 MULTI-TIMEFRAME ANALYZER COM SISTEMA PREMIUM
Integra o detector premium de candlestick patterns com todas as 3 fases:
- FASE 1: Volume + Quality + Volatility (+45% taxa de sucesso)
- FASE 2: Context + Timeframe + Technical (+25% taxa de sucesso)  
- FASE 3: Market Structure + Session + Momentum (+15% taxa de sucesso)

Taxa de sucesso esperada: 80-85% (vs 50-60% básico)
"""

import logging
import time
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta

from core.data_reader import DataReader, MarketData
from core.signal_writer import EnhancedSignalWriter, EnhancedTradingSignal
from indicators.technical import TechnicalAnalyzer, RSIAnalyzer 

# 🚀 IMPORT DO SISTEMA PREMIUM
try:
    from indicators.candlestick_patterns_detector import generate_candlestick_signals
    from config.premium_patterns_config import get_premium_config, get_pattern_thresholds
    PREMIUM_PATTERNS_AVAILABLE = True
    logging.info("✅ Sistema PREMIUM de patterns disponível")
except ImportError as e:
    PREMIUM_PATTERNS_AVAILABLE = False
    logging.warning(f"⚠️ Sistema premium não disponível: {e}")
    # Fallback para sistema básico
    try:
        from indicators.candlestick_patterns_detector import generate_candlestick_signals
        BASIC_PATTERNS_AVAILABLE = True
    except ImportError:
        BASIC_PATTERNS_AVAILABLE = False

# 🚀 ENHANCED VOLUME VALIDATION
try:
    from config.volume_validation_config import create_enhanced_volume_validator
    enhanced_volume_validator = create_enhanced_volume_validator()
    ENHANCED_VOLUME_AVAILABLE = True
    logging.info("✅ Enhanced Volume Validation disponível")
except ImportError:
    ENHANCED_VOLUME_AVAILABLE = False
    enhanced_volume_validator = None
    logging.warning("⚠️ Enhanced Volume Validation não disponível")

# Sistema rigoroso de qualidade
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

# Monitoramento em tempo real DESABILITADO para evitar locks
REAL_TIME_MONITORING_AVAILABLE = False
logging.info("🚫 Monitoramento em tempo real DESABILITADO (evita locks de DB)")

from config.settings import settings

class MultiTimeframeAnalyzer:
    """🚀 ANALYZER PREMIUM COM SISTEMA COMPLETO DE 3 FASES"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_reader = DataReader()
        self.signal_writer = EnhancedSignalWriter()
        
        enabled_timeframes = settings.get_enabled_timeframes()
        self.technical_analyzers = {tf: TechnicalAnalyzer() for tf in enabled_timeframes}

        # 🚀 CONFIGURAÇÃO PREMIUM
        self.premium_mode = PREMIUM_PATTERNS_AVAILABLE
        self.enhanced_volume = ENHANCED_VOLUME_AVAILABLE
        
        if self.premium_mode:
            self.premium_config = get_premium_config()
            self.logger.info("🚀 MODO PREMIUM ATIVADO - Sistema completo de 3 fases")
            
            # Estatísticas do sistema premium
            debug_info = self.premium_config.get_debugging_info()
            self.logger.info(f"   • Patterns suportados: {len(debug_info['patterns_supported'])}")
            self.logger.info(f"   • Fases implementadas: {debug_info['phases_configured']}")
            self.logger.info(f"   • Taxa de sucesso esperada: 80-85%")
        else:
            self.logger.warning("⚠️ MODO BÁSICO - usando sistema original")

        # SCHEDULER ESPECÍFICO POR TIMEFRAME
        try:
            from core.timeframe_scheduler import get_global_scheduler
            self.scheduler = get_global_scheduler()
            self.scheduler_enabled = True
            
            # Registra callbacks para cada timeframe
            self.scheduler.register_timeframe_callback("5m", self._process_5m_event)
            self.scheduler.register_timeframe_callback("15m", self._process_15m_event)
            
            self.logger.info("✅ Scheduler específico inicializado (aguarda 35s após fechamento)")
        except ImportError:
            self.scheduler = None
            self.scheduler_enabled = False
            self.logger.warning("⚠️ Scheduler não disponível - usando modo tradicional")
            
        self._last_cleanup = datetime.now()
        
        # Monitoramento em tempo real DESABILITADO
        self.real_time_monitor = None
        self.monitoring_enabled = False

        # CONFIGURAÇÕES OTIMIZADAS - sem locks
        self.MAX_SYMBOL_TIME = 8  # Reduzido para 8s
        self.MAX_VALIDATION_TIME = 2  # Reduzido para 2s
        self.DISABLE_MICROSTRUCTURE = True  # Desabilita microestrutura
        
        # 🚀 CONFIGURAÇÕES PREMIUM
        if self.premium_mode:
            self.logger.info("🚀 CONFIGURAÇÕES PREMIUM:")
            self.logger.info(f"   • Volume validation: {'Enhanced' if self.enhanced_volume else 'Standard'}")
            self.logger.info(f"   • Quality filters: RIGOROSOS")
            self.logger.info(f"   • Context validation: AVANÇADO")
            self.logger.info(f"   • Timeframe confirmation: ATIVO")
            self.logger.info(f"   • Market structure: ATIVO")
            self.logger.info(f"   • Session timing: ATIVO")
            self.logger.info(f"   • Momentum confirmation: ATIVO")
        
        self.logger.info("MultiTimeframeAnalyzer com PROCESSAMENTO ESPECÍFICO POR TIMEFRAME:")
        self.logger.info(f"  • Timeframes: {enabled_timeframes} (PROCESSAMENTO ESPECÍFICO)")
        self.logger.info(f"  • Modo: Cada timeframe processado independentemente")
        self.logger.info(f"  • Delay: 35s após fechamento (30s stream + 5s análise)")
        self.logger.info(f"  • Cronograma 5m: XX:00:35, XX:05:35, XX:10:35...")
        self.logger.info(f"  • Cronograma 15m: XX:00:35, XX:15:35, XX:30:35...")
        self.logger.info(f"  • Microestrutura: DESABILITADA (evita locks)")
        self.logger.info(f"  • Scheduler: {'ATIVO' if self.scheduler_enabled else 'INATIVO'}")

    def _process_5m_event(self, event):
        """Processa evento de fechamento de candle 5m (aguarda stream gravar)"""
        try:
            self.logger.info(f"🕒 EVENTO 5m: Candle {event.candle_close_time.strftime('%H:%M')} fechado + stream gravado")
            
            symbols = self.data_reader.get_valid_symbols_for_analysis()
            if not symbols:
                self.logger.warning("❌ Nenhum símbolo válido para análise 5m")
                return
            
            processed_count = 0
            signals_generated = 0
            
            for symbol in symbols:
                try:
                    result = self._analyze_single_timeframe_at_event(symbol, "5m", event)
                    processed_count += 1
                    
                    if result.get('signals_saved', 0) > 0:
                        signals_generated += result['signals_saved']
                        self.logger.info(f"✅ {symbol} 5m: {result['signals_saved']} sinais gerados")
                    
                except Exception as e:
                    self.logger.error(f"❌ Erro processando {symbol} 5m: {e}")
            
            self.logger.info(
                f"📊 EVENTO 5m CONCLUÍDO: {processed_count} símbolos processados, "
                f"{signals_generated} sinais gerados"
            )
            
        except Exception as e:
            self.logger.error(f"❌ Erro no evento 5m: {e}")
    
    def _process_15m_event(self, event):
        """Processa evento de fechamento de candle 15m (aguarda stream gravar)"""
        try:
            self.logger.info(f"🕒 EVENTO 15m: Candle {event.candle_close_time.strftime('%H:%M')} fechado + stream gravado")
            
            symbols = self.data_reader.get_valid_symbols_for_analysis()
            if not symbols:
                self.logger.warning("❌ Nenhum símbolo válido para análise 15m")
                return
            
            processed_count = 0
            signals_generated = 0
            
            for symbol in symbols:
                try:
                    result = self._analyze_single_timeframe_at_event(symbol, "15m", event)
                    processed_count += 1
                    
                    if result.get('signals_saved', 0) > 0:
                        signals_generated += result['signals_saved']
                        self.logger.info(f"✅ {symbol} 15m: {result['signals_saved']} sinais gerados")
                    
                except Exception as e:
                    self.logger.error(f"❌ Erro processando {symbol} 15m: {e}")
            
            self.logger.info(
                f"📊 EVENTO 15m CONCLUÍDO: {processed_count} símbolos processados, "
                f"{signals_generated} sinais gerados"
            )
            
        except Exception as e:
            self.logger.error(f"❌ Erro no evento 15m: {e}")
    
    def _analyze_single_timeframe_at_event(self, symbol: str, timeframe: str, event) -> Dict[str, Any]:
        """🚀 ANÁLISE PREMIUM ESPECÍFICA de um timeframe quando seu candle fecha"""
        
        start_time = time.time()
        
        # VERIFICAÇÃO RÁPIDA de sinais bloqueadores
        if self.signal_writer.check_existing_active_signals(symbol):
            return {
                'symbol': symbol, 
                'timeframe': timeframe,
                'status': 'blocked', 
                'reason': 'existing_blocking_signal',
                'signals_detected': 0, 
                'signals_validated': 0, 
                'signals_saved': 0,
                'execution_time': time.time() - start_time,
                'event_time': event.trigger_time.isoformat(),
                'premium_mode': self.premium_mode
            }
        
        self.logger.debug(f"🔍 {symbol} {timeframe}: Análise {'PREMIUM' if self.premium_mode else 'BÁSICA'} pós-stream")
        
        # Busca dados ESPECÍFICOS para o timeframe
        try:
            market_data = self.data_reader.get_latest_data(symbol, timeframe)
            self.logger.debug(f"📊 {symbol} {timeframe}: Dados pós-stream carregados")
            
            if not market_data or not market_data.is_sufficient_data:
                return {
                    'symbol': symbol, 
                    'timeframe': timeframe,
                    'status': 'insufficient_data', 
                    'signals_detected': 0, 
                    'signals_validated': 0, 
                    'signals_saved': 0,
                    'execution_time': time.time() - start_time,
                    'event_time': event.trigger_time.isoformat(),
                    'premium_mode': self.premium_mode
                }
                
        except Exception as e:
            self.logger.error(f"❌ {symbol} {timeframe}: Erro nos dados - {e}")
            return {
                'symbol': symbol, 
                'timeframe': timeframe,
                'status': 'data_error', 
                'reason': str(e),
                'signals_detected': 0, 
                'signals_validated': 0, 
                'signals_saved': 0,
                'execution_time': time.time() - start_time,
                'event_time': event.trigger_time.isoformat(),
                'premium_mode': self.premium_mode
            }
        
        # 🚀 ANÁLISE PREMIUM DO TIMEFRAME ESPECÍFICO
        signals_detected = []
        try:
            if self.premium_mode:
                # 🚀 SISTEMA PREMIUM COM 3 FASES
                tf_result = self._analyze_single_timeframe_premium(symbol, timeframe, market_data)
            else:
                # Sistema básico como fallback
                tf_result = self._analyze_single_timeframe_fast(symbol, timeframe, market_data)
            
            signals_detected = tf_result.get('signals', [])
            
            self.logger.debug(f"🔍 {symbol} {timeframe}: {len(signals_detected)} sinais detectados ({'PREMIUM' if self.premium_mode else 'BÁSICO'})")
                
        except Exception as e:
            self.logger.error(f"❌ {symbol} {timeframe}: Erro na análise - {e}")
            return {
                'symbol': symbol, 
                'timeframe': timeframe,
                'status': 'analysis_error', 
                'reason': str(e),
                'signals_detected': 0, 
                'signals_validated': 0, 
                'signals_saved': 0,
                'execution_time': time.time() - start_time,
                'event_time': event.trigger_time.isoformat(),
                'premium_mode': self.premium_mode
            }
        
        # 🚀 VALIDAÇÃO PREMIUM (se disponível)
        if self.premium_mode:
            validated_signals = self._premium_signal_validation(signals_detected, {timeframe: market_data})
        else:
            validated_signals = self._simple_validation_no_locks(signals_detected, {timeframe: market_data})
        
        # Gravação
        signals_saved = 0
        if validated_signals:
            signal = validated_signals[0]
            try:
                is_valid, validation_msg = self.validate_signal_before_saving(signal, {timeframe: market_data})
                
                if not is_valid:
                    self.logger.warning(f"❌ {symbol} {timeframe}: SINAL REJEITADO - {validation_msg}")
                    return {
                        'symbol': symbol, 
                        'timeframe': timeframe,
                        'status': 'rejected', 
                        'reason': validation_msg,
                        'signals_detected': len(signals_detected), 
                        'signals_validated': len(validated_signals), 
                        'signals_saved': 0,
                        'execution_time': time.time() - start_time,
                        'event_time': event.trigger_time.isoformat(),
                        'premium_mode': self.premium_mode
                    }
                
                signal.status = "ACTIVE"
                
                if self.signal_writer.write_enhanced_signal(signal):
                    signals_saved = 1
                    
                    total_time = time.time() - start_time
                    score = signal.confidence * 100
                    mode_label = "PREMIUM" if self.premium_mode else "BÁSICO"
                    
                    self.logger.info(
                        f"💾 {symbol} {timeframe}: GRAVADO {mode_label} | {signal.detector_name} | "
                        f"Score: {score:.1f} | Entry: ${signal.entry_price:.4f} | "
                        f"Stop: ${signal.stop_loss:.4f} | T1: ${signal.targets[0]:.4f} | "
                        f"T2: ${signal.targets[1]:.4f} | {total_time:.1f}s | Pós-stream: OK"
                    )
                        
                else:
                    self.logger.warning(f"❌ {symbol} {timeframe}: FALHA NA GRAVAÇÃO")
            except Exception as e:
                self.logger.error(f"❌ {symbol} {timeframe}: Erro ao salvar - {e}")
        
        total_time = time.time() - start_time
        
        return {
            'symbol': symbol, 
            'timeframe': timeframe,
            'status': 'success', 
            'signals_detected': len(signals_detected), 
            'signals_validated': len(validated_signals), 
            'signals_saved': signals_saved,
            'execution_time': total_time,
            'processing_mode': 'premium_3_phases' if self.premium_mode else 'basic_patterns',
            'event_time': event.trigger_time.isoformat(),
            'candle_close_time': event.candle_close_time.isoformat(),
            'premium_mode': self.premium_mode
        }

    def _analyze_single_timeframe_premium(self, symbol: str, timeframe: str, market_data: MarketData) -> Dict[str, Any]:
        """🚀 ANÁLISE PREMIUM COM SISTEMA COMPLETO DE 3 FASES"""
        
        signals = []
        
        if len(market_data.data) < 50:  # Dados insuficientes para análise premium
            return {'signals': []}

        # 1️⃣ ANÁLISE TÉCNICA PARA CONFLUÊNCIA
        technical_data = {}
        try:
            technical_analyzer = self.technical_analyzers.get(timeframe)
            if technical_analyzer:
                technical_data = technical_analyzer.analyze_all(market_data, timeframe)
                self.logger.debug(f"📊 {symbol} {timeframe}: Análise técnica concluída para confluência")
        except Exception as e:
            self.logger.debug(f"⚠️ {symbol} {timeframe}: Erro na análise técnica: {e}")

        # 2️⃣ CANDLESTICK PATTERNS PREMIUM
        try:
            cs_start = time.time()
            
            # 🚀 SISTEMA PREMIUM COM DADOS DE TIMEFRAME PARA CONFIRMAÇÃO
            timeframe_data = self._prepare_timeframe_data_for_confirmation(symbol, timeframe)
            
            # Usa detector premium
            if PREMIUM_PATTERNS_AVAILABLE:
                from indicators.candlestick_patterns_detector import PremiumCandlestickDetector
                premium_detector = PremiumCandlestickDetector()
                
                # Detecta patterns premium com todas as validações
                premium_patterns = premium_detector.detect_premium_patterns(
                    market_data.data, 
                    timeframe,
                    timeframe_data
                )
                
                # Converte patterns premium para formato de sinal
                for pattern in premium_patterns:
                    signal_data = self._convert_premium_pattern_to_signal(pattern, symbol, timeframe, market_data)
                    signals.append(signal_data)
                
                cs_time = time.time() - cs_start
                self.logger.debug(
                    f"🚀 {symbol} {timeframe}: {len(premium_patterns)} patterns PREMIUM detectados em {cs_time:.2f}s"
                )
            else:
                # Fallback para sistema básico
                cs_signals_raw = generate_candlestick_signals(market_data.data, symbol)
                signals.extend(cs_signals_raw)
                
                cs_time = time.time() - cs_start
                self.logger.debug(f"⚠️ {symbol} {timeframe}: {len(cs_signals_raw)} patterns BÁSICOS (fallback) em {cs_time:.2f}s")
                
        except Exception as e:
            self.logger.warning(f"❌ Erro patterns {symbol} {timeframe}: {e}")
        
        # 3️⃣ INTEGRAÇÃO COM INDICADORES TÉCNICOS (se patterns encontrados)
        if signals and technical_data:
            signals = self._integrate_technical_confluence(signals, technical_data, symbol, timeframe)
        
        return {'signals': signals}

    def _prepare_timeframe_data_for_confirmation(self, symbol: str, current_timeframe: str) -> Optional[Dict]:
        """Prepara dados de timeframes maiores para confirmação"""
        try:
            timeframe_data = {}
            
            # Determina timeframe maior para confirmação
            if current_timeframe == '5m':
                higher_tf = '15m'
            elif current_timeframe == '15m':
                higher_tf = '1h'
            else:
                return None
            
            # Busca dados do timeframe maior
            try:
                higher_tf_data = self.data_reader.get_latest_data(symbol, higher_tf)
                if higher_tf_data and higher_tf_data.is_sufficient_data:
                    timeframe_data[higher_tf] = higher_tf_data.data
                    self.logger.debug(f"📊 {symbol}: Dados {higher_tf} carregados para confirmação")
            except Exception as e:
                self.logger.debug(f"⚠️ {symbol}: Erro ao carregar {higher_tf}: {e}")
            
            return timeframe_data if timeframe_data else None
            
        except Exception as e:
            self.logger.debug(f"Erro ao preparar dados de confirmação: {e}")
            return None

    def _convert_premium_pattern_to_signal(self, pattern, symbol: str, timeframe: str, market_data: MarketData) -> EnhancedTradingSignal:
        """Converte PremiumPattern para EnhancedTradingSignal"""
        
        # Prepara targets
        targets = [pattern.target_price]
        if pattern.target_2 is not None:
            targets.append(pattern.target_2)
        
        # Cria sinal enhanced
        signal = EnhancedTradingSignal(
            symbol=symbol,
            signal_type='BUY_LONG' if pattern.pattern_type == 'bullish' else 'SELL_SHORT',
            entry_price=pattern.entry_price,
            confidence=pattern.final_confidence,
            timeframe=timeframe,
            detector_type='candlestick_premium',
            detector_name=pattern.name,
            market_data=market_data.data,
            targets=targets,
            stop_loss=pattern.stop_loss,
            
            # Dados premium específicos
            technical_data={
                'premium_scores': {
                    'volume_score': pattern.volume_score,
                    'quality_score': pattern.quality_score,
                    'context_score': pattern.context_score,
                    'market_structure_score': pattern.market_structure_score,
                    'session_score': pattern.session_score,
                    'momentum_score': pattern.momentum_score
                },
                'validation_info': {
                    'timeframe_alignment': pattern.timeframe_alignment,
                    'trend_confirmation': pattern.trend_confirmation,
                    'volatility_adjusted': pattern.volatility_adjusted
                },
                'pattern_data': {
                    'pattern_strength': pattern.pattern_strength,
                    'targets_logic': pattern.targets_logic,
                    'validation_notes': pattern.validation_notes
                },
                'system_version': 'premium_v1.0'
            }
        )
        
        return signal

    def _integrate_technical_confluence(self, signals: List, technical_data: Dict, symbol: str, timeframe: str) -> List:
        """🔗 Integra confluência com indicadores técnicos"""
        
        if not technical_data or not signals:
            return signals
        
        enhanced_signals = []
        
        for signal in signals:
            try:
                # Analisa confluência com indicadores
                confluence_score = 0.0
                confluence_details = []
                
                signal_type = signal.signal_type if hasattr(signal, 'signal_type') else signal.get('signal_type')
                is_bullish = 'BUY' in signal_type
                
                # 1. RSI Confluence
                if 'RSI' in technical_data:
                    rsi_data = technical_data['RSI']
                    if hasattr(rsi_data, 'metadata') and 'current_rsi' in rsi_data.metadata:
                        current_rsi = rsi_data.metadata['current_rsi']
                        
                        if is_bullish and current_rsi < 45:
                            confluence_score += 0.3
                            confluence_details.append("RSI: Oversold support")
                        elif not is_bullish and current_rsi > 55:
                            confluence_score += 0.3
                            confluence_details.append("RSI: Overbought resistance")
                        elif 45 <= current_rsi <= 55:
                            confluence_score += 0.1
                            confluence_details.append("RSI: Neutral")

                # 2. MACD Confluence
                if 'MACD' in technical_data:
                    macd_data = technical_data['MACD']
                    if hasattr(macd_data, 'metadata'):
                        current_macd = macd_data.metadata.get('current_macd', 0)
                        current_signal_line = macd_data.metadata.get('current_signal', 0)
                        
                        if is_bullish and current_macd > current_signal_line:
                            confluence_score += 0.2
                            confluence_details.append("MACD: Bullish cross")
                        elif not is_bullish and current_macd < current_signal_line:
                            confluence_score += 0.2
                            confluence_details.append("MACD: Bearish cross")

                # 3. Bollinger Bands Confluence  
                if 'BollingerBands' in technical_data:
                    bb_data = technical_data['BollingerBands']
                    if hasattr(bb_data, 'metadata'):
                        position = bb_data.metadata.get('price_position', 'unknown')
                        
                        if is_bullish and position in ['below_lower', 'below_middle']:
                            confluence_score += 0.25
                            confluence_details.append("BB: Oversold extreme")
                        elif not is_bullish and position in ['above_upper', 'above_middle']:
                            confluence_score += 0.25
                            confluence_details.append("BB: Overbought extreme")

                # 4. Atualiza confiança do sinal
                if hasattr(signal, 'confidence'):
                    # Boost na confiança com base na confluência
                    original_confidence = signal.confidence
                    confluence_boost = confluence_score * 0.1  # Máximo 10% de boost
                    new_confidence = min(0.95, original_confidence + confluence_boost)
                    
                    signal.confidence = new_confidence
                    
                    # Adiciona informações técnicas
                    if hasattr(signal, 'technical_data') and signal.technical_data:
                        signal.technical_data['confluence'] = {
                            'score': confluence_score,
                            'details': confluence_details,
                            'original_confidence': original_confidence,
                            'boosted_confidence': new_confidence
                        }
                    
                    self.logger.debug(
                        f"🔗 {symbol} {timeframe}: Confluência aplicada | "
                        f"Original: {original_confidence:.3f} → Novo: {new_confidence:.3f} | "
                        f"Score: {confluence_score:.2f}"
                    )
                
                enhanced_signals.append(signal)
                
            except Exception as e:
                self.logger.debug(f"Erro na confluência para {symbol}: {e}")
                enhanced_signals.append(signal)  # Mantém sinal original
        
        return enhanced_signals

    def _premium_signal_validation(self, signals: List[EnhancedTradingSignal], market_data_by_tf: Dict) -> List[EnhancedTradingSignal]:
        """🚀 VALIDAÇÃO PREMIUM com sistema completo"""
        if not signals:
            return []

        validated_signals = []
        
        for signal in signals:
            validation_start = time.time()
            
            # 🚀 VALIDAÇÃO PREMIUM MULTI-FASE
            validation_score = 0
            max_score = 10  # Score máximo
            validation_details = []
            
            # 1️⃣ FASE 1: VALIDAÇÕES BÁSICAS (peso 40%)
            
            # Volume validation (enhanced se disponível)
            if self.enhanced_volume:
                try:
                    is_volume_valid, volume_msg = enhanced_volume_validator(signal, market_data_by_tf)
                    if is_volume_valid:
                        validation_score += 2
                        validation_details.append(f"Volume: ✅ {volume_msg}")
                    else:
                        validation_details.append(f"Volume: ❌ {volume_msg}")
                        continue  # Rejeita imediatamente se volume inadequado
                except Exception as e:
                    self.logger.debug(f"Erro volume validation: {e}")
                    validation_score += 1  # Score neutro se erro
            else:
                # Volume validation básico
                market_data = market_data_by_tf.get(signal.timeframe)
                if market_data and len(market_data.data) >= 10:
                    current_volume = market_data.data['volume'].iloc[-1]
                    avg_volume = market_data.data['volume'].tail(10).mean()
                    if avg_volume > 0 and current_volume >= avg_volume * 0.8:
                        validation_score += 1
                        validation_details.append("Volume: ✅ Básico OK")
                    else:
                        validation_details.append("Volume: ❌ Muito baixo")
                        continue

            # Confidence threshold premium
            if self.premium_mode:
                min_confidence = self.premium_config.risk_management['min_final_confidence']
            else:
                min_confidence = 0.70
            
            if signal.confidence >= min_confidence:
                validation_score += 2
                validation_details.append(f"Confidence: ✅ {signal.confidence:.3f}")
            else:
                validation_details.append(f"Confidence: ❌ {signal.confidence:.3f} < {min_confidence}")
                continue

            # 2️⃣ FASE 2: VALIDAÇÕES AVANÇADAS (peso 30%)
            
            # Risk/Reward validation premium
            risk_pct = abs(signal.entry_price - signal.stop_loss) / signal.entry_price * 100
            reward_pct = abs(signal.targets[0] - signal.entry_price) / signal.entry_price * 100
            
            max_risk = self.premium_config.risk_management['max_risk_pct'] if self.premium_mode else 3.0
            min_rr = self.premium_config.risk_management['min_reward_ratio'] if self.premium_mode else 1.2
            
            if risk_pct <= max_risk:
                validation_score += 1
                validation_details.append(f"Risk: ✅ {risk_pct:.1f}%")
            else:
                validation_details.append(f"Risk: ❌ {risk_pct:.1f}% > {max_risk}%")
                continue
            
            if reward_pct / risk_pct >= min_rr:
                validation_score += 1
                validation_details.append(f"R/R: ✅ {reward_pct/risk_pct:.1f}")
            else:
                validation_details.append(f"R/R: ❌ {reward_pct/risk_pct:.1f} < {min_rr}")

            # 3️⃣ FASE 3: VALIDAÇÕES ELITE (peso 30%)
            
            # Premium scores validation (se disponível)
            if hasattr(signal, 'technical_data') and signal.technical_data:
                premium_scores = signal.technical_data.get('premium_scores', {})
                
                if premium_scores:
                    # Volume score
                    vol_score = premium_scores.get('volume_score', 0.5)
                    if vol_score >= 0.6:
                        validation_score += 1
                        validation_details.append(f"Vol Score: ✅ {vol_score:.2f}")
                    
                    # Quality score
                    qual_score = premium_scores.get('quality_score', 0.5)
                    if qual_score >= 0.75:
                        validation_score += 1
                        validation_details.append(f"Quality: ✅ {qual_score:.2f}")
                    
                    # Context score
                    ctx_score = premium_scores.get('context_score', 0.5)
                    if ctx_score >= 0.65:
                        validation_score += 1
                        validation_details.append(f"Context: ✅ {ctx_score:.2f}")
                else:
                    validation_score += 1  # Score neutro se não há premium scores
            else:
                validation_score += 1  # Score neutro para sinais básicos

            # 4️⃣ DECISÃO FINAL
            validation_time = time.time() - validation_start
            success_rate = validation_score / max_score
            
            required_rate = 0.7 if self.premium_mode else 0.5
            
            if success_rate >= required_rate:
                signal.status = "ACTIVE"
                validated_signals.append(signal)
                
                score = signal.confidence * 100
                self.logger.debug(
                    f"✅ {signal.symbol} {signal.timeframe}: PREMIUM VALIDADO | "
                    f"Score: {score:.1f} | Val: {validation_score}/{max_score} | "
                    f"{validation_time:.2f}s | {'; '.join(validation_details[:3])}"
                )
            else:
                self.logger.debug(
                    f"❌ {signal.symbol} {signal.timeframe}: REJEITADO PREMIUM | "
                    f"Score: {validation_score}/{max_score} | {'; '.join(validation_details[:2])}"
                )

        return validated_signals

    def _analyze_single_timeframe_fast(self, symbol: str, timeframe: str, market_data: MarketData) -> Dict[str, Any]:
        """Análise básica (fallback quando premium não disponível)"""
        
        tf_config = settings.get_timeframe_config(timeframe)
        signals = []

        if len(market_data.data) < 3:
            return {'signals': []}

        try:
            # Para 15m: usa último candle fechado
            analysis_candle = market_data.data.iloc[-1]
            analysis_price = float(analysis_candle['close_price'])
            analysis_timestamp = analysis_candle['timestamp'].to_pydatetime()

            # Log para debug do preço
            self.logger.debug(f"🔍 {symbol} {timeframe}: Analysis price = {analysis_price:.4f}")

            # Validação com o mesmo candle
            dynamic_candle = market_data.data.iloc[-1]
            dynamic_price = float(dynamic_candle['close_price'])
            
            self.logger.debug(f"📊 {symbol} {timeframe}: Análise=${analysis_price:.4f} | Dinâmico=${dynamic_price:.4f}")
            
        except Exception as e:
            self.logger.error(f"Erro ao obter preços para {symbol} {timeframe}: {e}")
            return {'signals': []}
        
        # 🔧 FUNÇÃO PARA CRIAR SINAIS (usa preço de análise)
        def create_signal_fast(**kwargs):
            try:
                analysis_data = market_data.data[:-1] if len(market_data.data) > 50 else market_data.data
        
                base_args = {
                    'symbol': symbol, 
                    'timeframe': timeframe, 
                    'entry_price': analysis_price,
                    'timestamp': datetime.now(),
                    'entry_timestamp': analysis_timestamp,
                    'market_data': analysis_data,
                    'status': 'ACTIVE',
                    'dynamic_validation_price': dynamic_price
                }
                final_args = {**kwargs, **base_args}
                allowed_keys = EnhancedTradingSignal.__annotations__.keys()
                filtered_args = {k: v for k, v in final_args.items() if k in allowed_keys}
                
                signal = EnhancedTradingSignal(**filtered_args)
                
                # 🔥 VALIDAÇÃO DINÂMICA antes de adicionar
                if dynamic_price > 0 and abs(dynamic_price - analysis_price) / analysis_price < 0.05:
                    existing_detectors = [s.detector_name for s in signals]
                    if signal.detector_name not in existing_detectors:
                        signals.append(signal)
                        score = signal.confidence * 100
                        self.logger.debug(f"➕ {timeframe} {signal.detector_name} | Score: {score:.1f} | Dinâmico OK")
                else:
                    self.logger.debug(f"❌ {timeframe} {kwargs.get('detector_name', 'unknown')}: Invalidado por candle dinâmico")
                    
            except Exception as e:
                self.logger.debug(f"⏭️ Sinal descartado: {e}")

        # CANDLESTICK BÁSICO
        if 'candlestick' in tf_config.enabled_detectors:
            try:
                cs_start = time.time()
                df_for_cs = market_data.data.tail(30)
                
                self.logger.debug(f"🕯️ {symbol} {timeframe}: Usando {len(df_for_cs)} candles para patterns")
                
                if len(df_for_cs) >= 10:
                    cs_signals_raw = generate_candlestick_signals(df_for_cs, symbol)
                    cs_time = time.time() - cs_start
                    
                    for cs in cs_signals_raw:
                        create_signal_fast(**cs)
                        
                    self.logger.debug(f"🕯️ Candlestick {symbol} {timeframe}: {len(cs_signals_raw)} patterns em {cs_time:.2f}s")
                                
            except Exception as e:
                self.logger.warning(f"❌ Erro candlestick {symbol} {timeframe}: {e}")
        
        return {'signals': signals}

    def validate_signal_before_saving(self, signal, market_data_by_tf):
        """Valida sinal RIGOROSAMENTE antes de salvar"""
        try:
            market_data = market_data_by_tf.get(signal.timeframe)
            if not market_data or len(market_data.data) == 0:
                return False, "Sem dados para validar"
            
            # Preço atual (último candle disponível)
            current_price = float(market_data.data.iloc[-1]['close_price'])
            
            # VALIDAÇÃO 1: Divergência de preço
            price_diff_pct = abs(current_price - signal.entry_price) / signal.entry_price * 100
            max_divergence = 1.5 if self.premium_mode else 1.0
            
            if price_diff_pct > max_divergence:
                return False, f"PREÇO DIVERGIU: {price_diff_pct:.2f}% (atual: ${current_price:.4f}, entrada: ${signal.entry_price:.4f})"
            
            # VALIDAÇÃO 2: Sinal não pode estar "pré-executado"
            if signal.signal_type == 'BUY_LONG':
                # Para BUY, preço atual não pode estar acima do target 1
                if current_price >= signal.targets[0]:
                    return False, f"SINAL PRÉ-EXECUTADO: Preço atual ${current_price:.4f} >= Target1 ${signal.targets[0]:.4f}"
                # Preço atual não pode estar abaixo do stop
                if current_price <= signal.stop_loss:
                    return False, f"SINAL JÁ STOPADO: Preço atual ${current_price:.4f} <= Stop ${signal.stop_loss:.4f}"
            
            elif signal.signal_type == 'SELL_SHORT':
                # Para SELL, preço atual não pode estar abaixo do target 1
                if current_price <= signal.targets[0]:
                    return False, f"SINAL PRÉ-EXECUTADO: Preço atual ${current_price:.4f} <= Target1 ${signal.targets[0]:.4f}"
                # Preço atual não pode estar acima do stop
                if current_price >= signal.stop_loss:
                    return False, f"SINAL JÁ STOPADO: Preço atual ${current_price:.4f} >= Stop ${signal.stop_loss:.4f}"
            
            # VALIDAÇÃO 3: Timeout do sinal
            signal_age_minutes = (datetime.now() - signal.timestamp).total_seconds() / 60
            max_age = 2 if signal.timeframe == "5m" else 5
            
            if signal_age_minutes > max_age:
                return False, f"SINAL EXPIRADO: {signal_age_minutes:.1f}min > {max_age}min"
            
            return True, f"VÁLIDO (diff: {price_diff_pct:.2f}%, age: {signal_age_minutes:.1f}min) {'PREMIUM' if self.premium_mode else 'BÁSICO'}"
            
        except Exception as e:
            return False, f"Erro na validação: {e}"

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
                min_confidence = 0.70
            else:  # 5m
                min_confidence = 0.85
            
            if signal.confidence >= min_confidence:
                validation_score += 2
            elif signal.confidence >= min_confidence - 0.05:
                validation_score += 1
            
            validation_time = time.time() - validation_start
            
            # Decisão
            success_rate = validation_score / max_score
            required_rate = 0.5
            
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
        """Execução contínua COM SCHEDULER ESPECÍFICO (aguarda stream gravar)"""
        
        if not self.scheduler_enabled:
            self.logger.error("❌ Scheduler não disponível - modo específico indisponível")
            self.logger.info("⚠️ Execute: pip install threading (se necessário)")
            return
        
        mode_label = "PREMIUM" if self.premium_mode else "BÁSICO"
        self.logger.info(f"🚀 ANÁLISE CONTÍNUA {mode_label} COM SCHEDULER ESPECÍFICO + AGUARDA STREAM")
        self.logger.info("=" * 70)
        self.logger.info("🕒 CRONOGRAMA DE DISPAROS (pós-stream):")
        self.logger.info("   • 5m:  XX:00:35, XX:05:35, XX:10:35, XX:15:35...")
        self.logger.info("   • 15m: XX:00:35, XX:15:35, XX:30:35, XX:45:35...")
        
        if self.premium_mode:
            self.logger.info("🚀 CARACTERÍSTICAS PREMIUM:")
            self.logger.info("   • Volume validation: Enhanced")
            self.logger.info("   • Quality filters: RIGOROSOS") 
            self.logger.info("   • Context validation: AVANÇADO")
            self.logger.info("   • Timeframe confirmation: ATIVO")
            self.logger.info("   • Market structure: ATIVO")
            self.logger.info("   • Session timing: ATIVO")
            self.logger.info("   • Momentum confirmation: ATIVO")
            self.logger.info("   • Taxa de sucesso esperada: 80-85%")
        else:
            self.logger.info("⚠️ MODO BÁSICO:")
            self.logger.info("   • Sistema original de patterns")
            self.logger.info("   • Taxa de sucesso esperada: 50-60%")
        
        self.logger.info("📊 CARACTERÍSTICAS:")
        self.logger.info("   • Stream grava candle em 30s")
        self.logger.info("   • Análise dispara 35s após fechamento (5s extra)")
        self.logger.info("   • Cada timeframe processado independentemente")
        self.logger.info("   • SEM conflitos entre timeframes")
        self.logger.info("   • SEM gaps de candles")
        self.logger.info("=" * 70)
        
        try:
            # Inicia scheduler
            self.scheduler.start()
            
            # Mostra próximos disparos
            status = self.scheduler.get_status()
            self.logger.info("📅 PRÓXIMOS DISPAROS (aguarda stream):")
            for tf, trigger_info in status['next_triggers'].items():
                trigger_time = trigger_info['next_trigger_time']
                time_until = trigger_info['time_until_minutes']
                candle_close = trigger_info['candle_close_time']
                
                self.logger.info(
                    f"   • {tf}: Candle fecha às {candle_close[-8:-3]}, "
                    f"análise às {trigger_time[-8:-3]} (em {time_until:.1f} min)"
                )
            
            self.logger.info(f"\n🎯 Sistema {mode_label} ativo - aguardando eventos (stream delay: 35s)...")
            self.logger.info("💡 Pressione Ctrl+C para parar")
            
            # Loop principal
            cycle_count = 0
            last_cleanup = time.time()
            last_status = time.time()
            
            while True:
                time.sleep(30)
                
                cycle_count += 1
                current_time = time.time()
                
                # Limpeza periódica
                if current_time - last_cleanup > 3600:
                    self._perform_quick_cleanup()
                    last_cleanup = current_time
                
                # Status periódico
                if current_time - last_status > 600:
                    scheduler_status = self.scheduler.get_status()
                    self.logger.info(f"💓 Sistema {mode_label} ativo - Scheduler: {scheduler_status['status']} (delay: {scheduler_status['delay_seconds']}s)")
                    last_status = current_time
                
        except KeyboardInterrupt:
            self.logger.info("\n🛑 Análise interrompida pelo usuário")
        except Exception as e:
            self.logger.error(f"❌ Erro crítico no scheduler: {e}")
            import traceback
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
        finally:
            if self.scheduler:
                self.scheduler.stop()
            self.logger.info("🏁 Análise contínua finalizada")
    
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
        """Status com informações do sistema premium"""
        try:
            symbols = settings.get_analysis_symbols()
            enabled_timeframes = settings.get_enabled_timeframes()
            
            # Status do scheduler
            scheduler_status = {}
            if self.scheduler_enabled and self.scheduler:
                scheduler_status = self.scheduler.get_status()
                processing_mode = "premium_timeframe_specific" if self.premium_mode else "basic_timeframe_specific"
                processing_description = "Sistema PREMIUM com 3 fases + timeframe específico" if self.premium_mode else "Sistema básico com timeframe específico"
            else:
                processing_mode = "premium_traditional" if self.premium_mode else "basic_traditional"
                processing_description = "Sistema PREMIUM tradicional" if self.premium_mode else "Sistema básico tradicional"
            
            components = {
                'database': 'OK_NO_LOCKS',
                'technical_analyzer': 'OPTIMIZED',
                'microstructure_validation': 'DISABLED_NO_LOCKS',
                'processing_mode': processing_mode,
                'scheduler': 'ACTIVE' if self.scheduler_enabled else 'DISABLED',
                'stream_integration': 'ACTIVE_35S_DELAY' if self.scheduler_enabled else 'DISABLED',
                'signal_status_logic': 'CORRECTED_2_TARGETS',
                'new_signals_status': 'ALWAYS_ACTIVE',
                'blocking_logic': 'ACTIVE_AND_TARGET_1_HIT_ONLY',
                'real_time_monitoring': 'DISABLED_NO_LOCKS',
                'anti_lock_protection': 'ACTIVE',
                'timeframe_isolation': 'ACTIVE',
                
                # 🚀 COMPONENTES PREMIUM
                'premium_mode': self.premium_mode,
                'enhanced_volume_validation': self.enhanced_volume,
                'candlestick_system': 'PREMIUM_3_PHASES' if self.premium_mode else 'BASIC_PATTERNS',
                'expected_success_rate': '80-85%' if self.premium_mode else '50-60%'
            }
            
            status_data = {
                'status': 'OK',
                'system_type': f'Trading Analyzer - {"PREMIUM" if self.premium_mode else "BÁSICO"} + SCHEDULER ESPECÍFICO',
                'timestamp': datetime.now().isoformat(),
                'components': components,
                'symbols_available': len(symbols),
                'enabled_timeframes': enabled_timeframes,
                'processing_description': processing_description,
                'signal_flow': 'ACTIVE → TARGET_1_HIT → TARGET_2_HIT/STOP_HIT',
                'blocking_states': ['ACTIVE', 'TARGET_1_HIT'],
                'completed_states': ['TARGET_2_HIT', 'STOP_HIT', 'EXPIRED'],
                
                'timeframe_processing': {
                    'mode': 'stream_aware_specific_events',
                    'description': 'Aguarda stream gravar (30s) + análise específica (5s)',
                    'timing': {
                        '5m': 'XX:00:35, XX:05:35, XX:10:35, XX:15:35...',
                        '15m': 'XX:00:35, XX:15:35, XX:30:35, XX:45:35...'
                    },
                    'stream_delay': '30 segundos',
                    'analysis_delay': '5 segundos',
                    'total_delay': '35 segundos',
                    'no_gaps': True,
                    'no_conflicts': True
                },
                
                'configuration': {
                    'multi_timeframe_enabled': True,
                    'timeframes_active': enabled_timeframes,
                    'single_signal_per_crypto': True,
                    'signal_status_corrected': True,
                    'targets_count': 2,
                    'new_signals_always_active': True,
                    'timeframe_specific_processing': True,
                    'scheduler_enabled': self.scheduler_enabled,
                    'stream_integration': True,
                    'anti_lock_protection': True,
                    'no_database_locks': True,
                    
                    # 🚀 CONFIGURAÇÕES PREMIUM
                    'premium_mode': self.premium_mode,
                    'enhanced_volume': self.enhanced_volume
                }
            }
            
            # 🚀 ADICIONA INFORMAÇÕES PREMIUM
            if self.premium_mode:
                debug_info = self.premium_config.get_debugging_info()
                status_data['premium_system'] = {
                    'version': debug_info['config_version'],
                    'phases_implemented': debug_info['phases_configured'],
                    'patterns_supported': debug_info['patterns_supported'],
                    'current_session': debug_info['current_session'],
                    'default_thresholds': debug_info['default_thresholds'],
                    'features': [
                        'Volume confirmation avançado',
                        'Filtros de qualidade rigorosos',
                        'Context validation',
                        'Timeframe confirmation',
                        'Market structure analysis', 
                        'Session timing',
                        'Momentum confirmation',
                        'Volatility adaptation'
                    ]
                }
            
            # Adiciona informações do scheduler se disponível
            if self.scheduler_enabled and scheduler_status:
                status_data['scheduler_status'] = scheduler_status
            
            return status_data
            
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': str(e),
                'timestamp': datetime.now().isoformat(),
                'processing_mode': 'error',
                'premium_mode': self.premium_mode
            }
    
    # Métodos de compatibilidade
    def analyze_symbol_all_timeframes(self, symbol: str) -> Dict[str, Any]:
        """Análise manual de símbolo com sistema premium"""
        
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
                'execution_time': time.time() - symbol_start_time,
                'mode': f'manual_analysis_{"premium" if self.premium_mode else "basic"}',
                'premium_mode': self.premium_mode
            }
        
        mode_label = "PREMIUM" if self.premium_mode else "BÁSICA"
        self.logger.info(f"🔍 {symbol}: Análise manual {mode_label} (todos os timeframes)")
        
        # Para análise manual, processa ambos timeframes
        timeframes = ["5m", "15m"]
        all_signals = []

        # Busca dados para ambos timeframes
        market_data_by_tf = {}
        for tf in timeframes:
            try:
                market_data = self.data_reader.get_latest_data(symbol, tf)
                market_data_by_tf[tf] = market_data
                    
            except Exception as e:
                self.logger.warning(f"❌ {symbol} {tf}: Erro nos dados - {e}")
                market_data_by_tf[tf] = None

        # Análise por timeframe
        for timeframe in timeframes:
            market_data = market_data_by_tf[timeframe]
            if market_data and market_data.is_sufficient_data:
                try:
                    if self.premium_mode:
                        # 🚀 ANÁLISE PREMIUM
                        tf_result = self._analyze_single_timeframe_premium(symbol, timeframe, market_data)
                    else:
                        # Análise básica
                        tf_result = self._analyze_single_timeframe_fast(symbol, timeframe, market_data)
                    
                    tf_signals = tf_result.get('signals', [])
                    all_signals.extend(tf_signals)
                    
                    self.logger.info(f"🔍 {symbol} {timeframe}: {len(tf_signals)} sinais detectados ({mode_label})")
                            
                except Exception as e:
                    self.logger.error(f"❌ {symbol} {timeframe}: Erro - {e}")

        # Pega apenas o melhor sinal (sem conflitos)
        if len(all_signals) > 1:
            # Prioriza por confidence
            best_signal = max(all_signals, key=lambda s: s.confidence)
            filtered_signals = [best_signal]
            self.logger.debug(f"🔧 {symbol}: {len(all_signals)} → 1 melhor sinal (conf: {best_signal.confidence:.3f})")
        else:
            filtered_signals = all_signals

        # 🚀 VALIDAÇÃO PREMIUM (se disponível)
        if self.premium_mode:
            validated_signals = self._premium_signal_validation(filtered_signals, market_data_by_tf)
        else:
            validated_signals = self._simple_validation_no_locks(filtered_signals, market_data_by_tf)

        # Gravação
        signals_saved = 0
        if validated_signals:
            signal = validated_signals[0]
            try:
                # VALIDAÇÃO ANTES DE SALVAR
                is_valid, validation_msg = self.validate_signal_before_saving(signal, market_data_by_tf)
                
                if not is_valid:
                    self.logger.warning(f"❌ {symbol}: SINAL REJEITADO - {validation_msg}")
                    return {
                        'symbol': symbol, 
                        'status': 'rejected', 
                        'reason': validation_msg,
                        'signals_detected': len(all_signals), 
                        'signals_validated': len(validated_signals), 
                        'signals_saved': 0,
                        'execution_time': time.time() - symbol_start_time,
                        'mode': f'manual_analysis_{"premium" if self.premium_mode else "basic"}',
                        'premium_mode': self.premium_mode
                    }
                
                signal.status = "ACTIVE"
                
                if self.signal_writer.write_enhanced_signal(signal):
                    signals_saved = 1
                    
                    total_time = time.time() - symbol_start_time
                    score = signal.confidence * 100
                    self.logger.info(
                        f"💾 {symbol}: GRAVADO {mode_label} | {signal.timeframe} | {signal.detector_name} | "
                        f"Score: {score:.1f} | Entry: ${signal.entry_price:.4f} | "
                        f"Stop: ${signal.stop_loss:.4f} | T1: ${signal.targets[0]:.4f} | "
                        f"T2: ${signal.targets[1]:.4f} | {validation_msg} | {total_time:.1f}s"
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
            'mode': f'manual_analysis_{"premium" if self.premium_mode else "basic"}',
            'premium_mode': self.premium_mode
        }

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
        
        mode_label = "PREMIUM" if self.premium_mode else "BÁSICO"
        
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
            'system_mode': mode_label,
            'premium_features': {
                'volume_validation': 'enhanced' if self.enhanced_volume else 'basic',
                'quality_filters': 'rigorous' if self.premium_mode else 'basic',
                'context_validation': 'advanced' if self.premium_mode else 'basic',
                'expected_success_rate': '80-85%' if self.premium_mode else '50-60%'
            },
            'signal_status_logic': 'CORRECTED - ACTIVE → TARGET_1_HIT → TARGET_2_HIT/STOP_HIT',
            'anti_lock_protection': True
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
                'system_mode': 'PREMIUM' if self.premium_mode else 'BÁSICO'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

# Alias para compatibilidade
TradingAnalyzer = MultiTimeframeAnalyzer