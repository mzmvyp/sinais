# analyzer.py - PRIORIDADE 15m + SCORE RIGOROSO PARA 5m + SEM LOCKS + FILTRO CANDLESTICK

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


# 🔧 CORREÇÃO 1: Adicionar imports de candlestick
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

        # NOVA LÓGICA: Prioridade 15m + Score rigoroso para 5m
        self.conflict_resolver = PrioritySignalResolver()
        self.quality_mode = "15m_priority_5m_rigorous"

        self._last_cleanup = datetime.now()
        
        # Monitoramento em tempo real DESABILITADO
        self.real_time_monitor = None
        self.monitoring_enabled = False

        # CONFIGURAÇÕES OTIMIZADAS - sem locks
        self.MAX_SYMBOL_TIME = 8  # Reduzido para 8s
        self.MAX_VALIDATION_TIME = 2  # Reduzido para 2s
        self.DISABLE_MICROSTRUCTURE = True  # Desabilita microestrutura
        
        self.logger.info("MultiTimeframeAnalyzer com PRIORIDADE 15m + FILTRO CANDLESTICK inicializado:")
        self.logger.info(f"  • Timeframes: {enabled_timeframes} (PRIORIDADE: 15m)")
        self.logger.info(f"  • Score mínimo 5m: {self.conflict_resolver.MIN_5M_SCORE}")
        self.logger.info(f"  • Vantagem necessária 5m: +{self.conflict_resolver.SCORE_ADVANTAGE_REQUIRED} pontos")
        self.logger.info(f"  • Microestrutura: DESABILITADA (evita locks)")
        self.logger.info(f"  • Monitoramento tempo real: DESABILITADO (evita locks)")
        # 🔧 CORREÇÃO 3: Logs do filtro candlestick
        
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
            if price_diff_pct > 1.0:  # Máximo 1% de divergência
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
            max_age = 2 if signal.timeframe == "5m" else 5  # Máximo 2min para 5m, 5min para 15m
            
            if signal_age_minutes > max_age:
                return False, f"SINAL EXPIRADO: {signal_age_minutes:.1f}min > {max_age}min"
            
            return True, f"VÁLIDO (diff: {price_diff_pct:.2f}%, age: {signal_age_minutes:.1f}min)"
            
        except Exception as e:
            return False, f"Erro na validação: {e}"    
    
      
    # 🔧 CORREÇÃO 4: Adicionar método de backup
    def process_candlesticks_for_backup(self, backup_patterns: List[Dict], symbol: str, timeframe: str):
        """
        🗄️ PROCESSA BACKUP DE TODOS OS 43 CANDLESTICK PATTERNS
        """
        if not backup_patterns:
            return
        
        try:
            # Log detalhado do backup
            pattern_names = [p.get('pattern_name', 'unknown') for p in backup_patterns]
            unique_patterns = len(set(pattern_names))
            
            self.logger.debug(f"🗄️ Backup {symbol} {timeframe}: {len(backup_patterns)} detecções de {unique_patterns} patterns únicos")
            
            # Estatísticas rápidas
            high_quality = [p for p in backup_patterns if p.get('would_be_signal', False)]
            if high_quality:
                self.logger.debug(f"🎯 {len(high_quality)} patterns com qualidade para sinal")
            
            # TODO: Implementar salvamento no banco se necessário
            # Por enquanto, dados estão sendo salvos automaticamente pelo filtro
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao processar backup de patterns: {e}")
        
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
                
                # USAR DADOS LIVE PARA 5m E 15m
                if tf in ["5m", "15m"]:
                    market_data = self.data_reader.get_enhanced_data(symbol, tf)
                    self.logger.debug(f"🔴 {symbol} {tf}: Dados LIVE requisitados")
                else:
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
                    
                    # 🔥 LOG DETALHADO
                    self.logger.info(f"🔍 {symbol} {timeframe}: {len(tf_signals)} sinais detectados em {tf_time:.1f}s")
                    for sig in tf_signals:
                        self.logger.info(f"   → {sig.detector_name} | {sig.signal_type} | Conf: {sig.confidence:.3f}")
                            
                except Exception as e:
                    self.logger.error(f"❌ {symbol} {timeframe}: Erro - {e}")

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
                        'execution_time': time.time() - symbol_start_time
                    }
                
                signal.status = "ACTIVE"
                
                if self.signal_writer.write_enhanced_signal(signal):
                    signals_saved = 1
                    
                    total_time = time.time() - symbol_start_time
                    score = signal.confidence * 100
                    self.logger.info(
                        f"💾 {symbol}: GRAVADO | {signal.timeframe} | {signal.detector_name} | "
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
            'priority_logic': '15m_first_5m_rigorous'
        }
     
    def _analyze_single_timeframe_fast(self, symbol: str, timeframe: str, market_data: MarketData) -> Dict[str, Any]:
        """Análise SEMPRE usa candle fechado, validação usa candle dinâmico"""
        
        tf_config = settings.get_timeframe_config(timeframe)
        signals = []

        if len(market_data.data) < 3:  # Precisa de pelo menos 3 candles
            return {'signals': []}

        # 🔥 ANÁLISE: SEMPRE usa CANDLE FECHADO (confirmado)
        try:
            # Candle fechado para análise (penúltimo)
            analysis_candle = market_data.data.iloc[-2]
            analysis_price = float(analysis_candle['close_price'])
            analysis_timestamp = analysis_candle['timestamp'].to_pydatetime()
            
            # Candle dinâmico para validação pré-gravação
            dynamic_candle = market_data.data.iloc[-1]
            dynamic_price = float(dynamic_candle['close_price'])
            
            self.logger.debug(f"📊 {symbol} {timeframe}: Análise=${analysis_price:.4f} | Dinâmico=${dynamic_price:.4f}")
            
        except Exception as e:
            self.logger.error(f"Erro ao obter preços para {symbol} {timeframe}: {e}")
            return {'signals': []}
        
        # 🔧 CORREÇÃO 5: Definir create_signal_fast no local correto
        # 🔥 FUNÇÃO PARA CRIAR SINAIS (usa preço de análise)
        def create_signal_fast(**kwargs):
            try:
                base_args = {
                    'symbol': symbol, 
                    'timeframe': timeframe, 
                    'entry_price': analysis_price,  # 🔥 SEMPRE preço do candle fechado
                    'timestamp': analysis_timestamp,
                    'market_data': market_data.data.iloc[:-1],  # 🔥 Dados SEM candle dinâmico
                    'status': 'ACTIVE',
                    'dynamic_validation_price': dynamic_price  # 🔥 NOVO: para validação
                }
                final_args = {**kwargs, **base_args}
                allowed_keys = EnhancedTradingSignal.__annotations__.keys()
                filtered_args = {k: v for k, v in final_args.items() if k in allowed_keys}
                
                signal = EnhancedTradingSignal(**filtered_args)
                
                # 🔥 VALIDAÇÃO DINÂMICA antes de adicionar
                if self._validate_signal_with_dynamic_price(signal, dynamic_price):
                    # Evita duplicatas
                    existing_detectors = [s.detector_name for s in signals]
                    if signal.detector_name not in existing_detectors:
                        signals.append(signal)
                        score = signal.confidence * 100
                        self.logger.debug(f"➕ {timeframe} {signal.detector_name} | Score: {score:.1f} | Dinâmico OK")
                else:
                    self.logger.debug(f"❌ {timeframe} {kwargs.get('detector_name', 'unknown')}: Invalidado por candle dinâmico")
                    
            except Exception as e:
                self.logger.debug(f"⏭️ Sinal descartado: {e}")

        # 🔧 CORREÇÃO 6: CANDLESTICK COM FILTRO RIGOROSO
        # CANDLESTICK SIMPLIFICADO - apenas engolfo de alta performance
        if 'candlestick' in tf_config.enabled_detectors and CANDLESTICK_AVAILABLE:
            try:
                cs_start = time.time()
                # USA dados fechados sempre
                if timeframe in ["5m", "15m"] and len(market_data.data) > 2:
                    df_for_cs = market_data.data.iloc[:-2]
                else:
                    df_for_cs = market_data.data.iloc[:-1]
                
                if len(df_for_cs) >= 10:
                    # SEM FILTRO - usa detector direto
                    cs_signals_raw = generate_candlestick_signals(df_for_cs, symbol)
                    cs_time = time.time() - cs_start
                    
                    # FILTRA apenas engolfo (os únicos que funcionam)
                    quality_signals = []
                    for cs in cs_signals_raw:
                        detector_name = cs.get('detector_name', '')
                        if 'Engulfing' in detector_name and cs.get('confidence', 0) >= 0.75:
                            quality_signals.append(cs)
                    
                    for cs in quality_signals[:2]:  # Máximo 2
                        create_signal_fast(**cs)
                        
                    self.logger.debug(f"🕯️ Candlestick {symbol} {timeframe}: {len(quality_signals)} engolfos em {cs_time:.2f}s")
                                
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
        """Execução contínua DEFINITIVA com logs verbosos"""
        if base_interval is None: 
           base_interval = getattr(settings.system, 'analysis_interval', 300)
        
        self.logger.info("🚀 ANÁLISE CONTÍNUA DEFINITIVA - PRIORIDADE 15m + FILTRO CANDLESTICK")
        self.logger.info(f"⏱️ Intervalo entre ciclos: {base_interval}s")
        
        valid_symbols = self.data_reader.get_valid_symbols_for_analysis()
        
        if not valid_symbols:
            self.logger.error("❌ Nenhum símbolo válido encontrado!")
            return
        
        self.logger.info(f"✅ Símbolos: {valid_symbols}")
        
        cycle_count = 0
        
        while True:
            try:
                cycle_count += 1
                cycle_start = time.time()
                total_signals = 0
                blocked_count = 0
                error_count = 0
                
                self.logger.info(f"🔄 Ciclo {cycle_count} - Prioridade 15m + Filtro Candlestick")
                
                for i, symbol in enumerate(valid_symbols, 1):
                    try:
                        symbol_start = time.time()
                        result = self.analyze_symbol_all_timeframes(symbol)
                        symbol_time = time.time() - symbol_start
                        
                        if result.get('status') == 'blocked':
                            blocked_count += 1
                        elif result.get('status') == 'error':
                            error_count += 1
                        else:
                            signals_saved = result.get('signals_saved', 0)
                            total_signals += signals_saved
                            if signals_saved > 0:
                                self.logger.info(f"🎯 {symbol} ({i}/{len(valid_symbols)}): {signals_saved} ATIVO")
                            else:
                                self.logger.debug(f"✓ {symbol} ({i}/{len(valid_symbols)}): OK em {symbol_time:.1f}s")
                        
                        time.sleep(0.1)
                        
                    except Exception as e:
                        error_count += 1
                        self.logger.error(f"❌ Erro em {symbol}: {e}")
                
                cycle_time = time.time() - cycle_start
                
                # RESUMO DO CICLO COM LOGS VERBOSOS
                self.logger.info(
                    f"✅ Ciclo {cycle_count}: {total_signals} novos ACTIVE | "
                    f"{blocked_count} bloqueados | {error_count} erros | {cycle_time:.1f}s"
                )
                
                # LOG VERBOSE DO FINAL DO CICLO
                self.logger.info(f"📊 Ciclo {cycle_count} finalizado com sucesso!")
                self.logger.info(f"⏳ Iniciando aguardo de {base_interval}s...")
                
                # SLEEP COM HEARTBEAT
                sleep_start = time.time()
                heartbeat_interval = 60  # Heartbeat a cada 60s
                next_heartbeat = heartbeat_interval
                
                while True:
                    elapsed_sleep = time.time() - sleep_start
                    
                    if elapsed_sleep >= base_interval:
                        break
                    
                    # Heartbeat
                    if elapsed_sleep >= next_heartbeat:
                        remaining = base_interval - elapsed_sleep
                        self.logger.info(f"💓 Heartbeat: aguardando mais {remaining:.0f}s até próximo ciclo...")
                        next_heartbeat += heartbeat_interval
                    
                    time.sleep(1)  # Sleep curto para permitir heartbeat
                
                self.logger.info(f"⏰ Aguardo de {base_interval}s concluído. Iniciando Ciclo {cycle_count + 1}...")
                
            except KeyboardInterrupt:
                self.logger.info("🛑 Análise interrompida pelo usuário")
                break
            except Exception as e:
                self.logger.error(f"❌ Erro crítico no ciclo {cycle_count}: {e}")
                import traceback
                self.logger.error(f"Stack trace: {traceback.format_exc()}")
                
                self.logger.info(f"🔄 Tentando recuperar em 10s...")
                time.sleep(10)
                continue
        
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
        """Status com nova lógica de prioridade"""
        try:
            symbols = settings.get_analysis_symbols()
            enabled_timeframes = settings.get_enabled_timeframes()
            
            components = {
                'database': 'OK_NO_LOCKS',
                'technical_analyzer': 'OPTIMIZED',
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
                'system_type': 'Trading Analyzer - PRIORIDADE 15m + FILTRO CANDLESTICK + SEM LOCKS',
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
                'priority_logic': '15M_PREFERRED_5M_RIGOROUS',
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

# Alias para compatibilidade
TradingAnalyzer = MultiTimeframeAnalyzer