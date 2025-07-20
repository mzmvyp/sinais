"""
Trading Analyzer CORRIGIDO - INTEGRAÇÃO COMPLETA
Integra TODOS os componentes: Técnicos + Padrões Gráficos + 43 Candlestick Patterns
"""
import logging
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import concurrent.futures
import threading

# Imports do sistema existente
from core.data_reader import DataReader, MarketData
from core.signal_writer import SignalWriter, TradingSignal
from indicators.technical import TechnicalAnalyzer
from config.settings import settings

# NOVO: Imports dos detectores que estavam FALTANDO
try:
    from indicators.patterns import PatternAnalyzer
    PATTERNS_AVAILABLE = True
except ImportError:
    PATTERNS_AVAILABLE = False

try:
    from indicators.candlestick_patterns_detector import CandlestickDetector, generate_candlestick_signals
    CANDLESTICK_AVAILABLE = True
except ImportError:
    CANDLESTICK_AVAILABLE = False

class UnifiedTradingAnalyzer:
    """Trading Analyzer CORRIGIDO com INTEGRAÇÃO COMPLETA de todos os detectores"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Configurar handler se não existe
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Componentes principais
        self.data_reader = DataReader()
        self.signal_writer = SignalWriter()
        
        # CORRIGIDO: Integra TODOS os analisadores
        self.technical_analyzer = TechnicalAnalyzer()
        
        if PATTERNS_AVAILABLE:
            self.pattern_analyzer = PatternAnalyzer()
            self.logger.info("✅ PatternAnalyzer integrado")
        else:
            self.pattern_analyzer = None
            self.logger.warning("⚠️ PatternAnalyzer não disponível")
        
        if CANDLESTICK_AVAILABLE:
            self.candlestick_detector = CandlestickDetector()
            self.logger.info("✅ CandlestickDetector integrado (43 padrões)")
        else:
            self.candlestick_detector = None
            self.logger.warning("⚠️ CandlestickDetector não disponível")
        
        # NOVO: Lock para evitar concorrência
        self._analysis_lock = threading.Lock()
        
        # NOVO: Cache de análises recentes
        self._analysis_cache = {}
        self._cache_expiry = {}
        self._cache_timeout = 300  # 5 minutos
        
        # NOVO: Contador de sinais gerados
        self._signals_generated_today = 0
        self._last_reset_date = datetime.now().date()
        
        # CORRIGIDO: Configurações menos restritivas
        self._apply_optimized_settings()
        
        self.logger.info("🚀 Trading Analyzer UNIFICADO inicializado")
        self.logger.info(f"📊 Componentes ativos:")
        self.logger.info(f"   • Indicadores Técnicos: ✅")
        self.logger.info(f"   • Padrões Gráficos: {'✅' if PATTERNS_AVAILABLE else '❌'}")
        self.logger.info(f"   • Candlestick (43): {'✅' if CANDLESTICK_AVAILABLE else '❌'}")
    
    def _apply_optimized_settings(self):
        """Aplica configurações otimizadas para gerar mais sinais"""
        # CORRIGIDO: Configurações menos restritivas
        settings.analysis.confidence_threshold = 0.3  # Era 0.70
        settings.indicators.rsi_overbought = 65        # Era 70
        settings.indicators.rsi_oversold = 35          # Era 30
        settings.indicators.min_volume_ratio = 1.2     # Era 1.5
        settings.patterns.min_pattern_strength = 0.3   # Era 0.6
        settings.system.max_signals_per_symbol = 3     # Era 1
        
        self.logger.info("🔧 Configurações otimizadas aplicadas:")
        self.logger.info(f"   • Confidence: {settings.analysis.confidence_threshold}")
        self.logger.info(f"   • RSI: {settings.indicators.rsi_oversold}-{settings.indicators.rsi_overbought}")
        self.logger.info(f"   • Pattern strength: {settings.patterns.min_pattern_strength}")
        self.logger.info(f"   • Max sinais: {settings.system.max_signals_per_symbol}")
    
    def _reset_daily_counter(self):
        """Reseta contador diário se necessário"""
        current_date = datetime.now().date()
        if current_date != self._last_reset_date:
            self._signals_generated_today = 0
            self._last_reset_date = current_date
            self.logger.info("🔄 Contador diário resetado")
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Verifica se cache ainda é válido"""
        now = time.time()
        return (cache_key in self._cache_expiry and 
                self._cache_expiry[cache_key] > now)
    
    def _update_cache(self, cache_key: str, result: Dict):
        """Atualiza cache de análise"""
        self._analysis_cache[cache_key] = result
        self._cache_expiry[cache_key] = time.time() + self._cache_timeout
    
    def analyze_symbol_unified(self, symbol: str, timeframe: str = None) -> Dict:
        """
        Análise UNIFICADA de symbol - INTEGRA TODOS OS DETECTORES
        """
        if timeframe is None:
            timeframe = settings.analysis.default_timeframe
        
        # Reset contador se necessário
        self._reset_daily_counter()
        
        cache_key = f"{symbol}_{timeframe}"
        start_time = time.time()
        
        self.logger.info(f"🔍 Análise UNIFICADA: {symbol} {timeframe}")
        
        # Verifica cache primeiro
        if self._is_cache_valid(cache_key):
            cached_result = self._analysis_cache[cache_key]
            self.logger.debug(f"📋 Usando análise em cache para {symbol}")
            return cached_result
        
        try:
            with self._analysis_lock:
                
                # 1. Buscar dados
                market_data = self.data_reader.get_latest_data(symbol, timeframe)
                
                if not market_data:
                    result = {
                        'symbol': symbol,
                        'status': 'no_data',
                        'message': 'Nenhum dado encontrado',
                        'timestamp': datetime.now()
                    }
                    self._update_cache(cache_key, result)
                    return result
                
                if not market_data.is_sufficient_data:
                    result = {
                        'symbol': symbol,
                        'status': 'insufficient_data',
                        'data_points': market_data.data_points,
                        'required': settings.analysis.min_data_points,
                        'message': f'Dados insuficientes: {market_data.data_points}/{settings.analysis.min_data_points}',
                        'timestamp': datetime.now()
                    }
                    self._update_cache(cache_key, result)
                    return result
                
                # 2. ANÁLISE UNIFICADA - TODOS OS COMPONENTES
                all_signals = []
                analysis_components = {}
                
                # 2.1 Indicadores Técnicos
                technical_results = self.technical_analyzer.analyze_all(market_data)
                technical_signals = self.technical_analyzer.generate_trading_signals(
                    market_data, technical_results
                )
                all_signals.extend(technical_signals)
                analysis_components['technical'] = {
                    'indicators': len(technical_results),
                    'signals': len(technical_signals),
                    'rsi_value': technical_results.get('RSI', type('obj', (object,), {'latest_value': 50})).latest_value,
                    'macd_value': technical_results.get('MACD', type('obj', (object,), {'latest_value': 0})).latest_value
                }
                
                # 2.2 Padrões Gráficos
                if self.pattern_analyzer:
                    try:
                        pattern_results = self.pattern_analyzer.analyze_all_patterns(market_data)
                        pattern_signals = self.pattern_analyzer.generate_pattern_signals(market_data, pattern_results)
                        
                        # Converte para TradingSignal se necessário
                        for pattern_signal in pattern_signals:
                            if not isinstance(pattern_signal, TradingSignal):
                                # Converte dict para TradingSignal
                                converted_signal = TradingSignal(
                                    symbol=symbol,
                                    signal_type=pattern_signal.get('signal_type', 'BUY_LONG'),
                                    entry_price=pattern_signal.get('entry_price', market_data.latest_price),
                                    confidence=pattern_signal.get('confidence', 0.5),
                                    strategy=f"PATTERN_{pattern_signal.get('strategy', 'unknown')}",
                                    indicators_used=[f"pattern_{pattern_signal.get('pattern_name', 'unknown')}"]
                                )
                                all_signals.append(converted_signal)
                            else:
                                all_signals.append(pattern_signal)
                        
                        analysis_components['patterns'] = {
                            'patterns_detected': len(pattern_results),
                            'signals': len(pattern_signals)
                        }
                        
                    except Exception as e:
                        self.logger.error(f"Erro nos padrões gráficos para {symbol}: {e}")
                        analysis_components['patterns'] = {'error': str(e)}
                else:
                    analysis_components['patterns'] = {'status': 'not_available'}
                
                # 2.3 Padrões de Candlestick (43 padrões)
                if self.candlestick_detector:
                    try:
                        candlestick_signals = generate_candlestick_signals(market_data.data, symbol)
                        
                        # Converte candlestick signals para TradingSignal
                        for cs_signal in candlestick_signals:
                            if cs_signal.get('confidence', 0) >= settings.analysis.confidence_threshold:
                                converted_signal = TradingSignal(
                                    symbol=symbol,
                                    signal_type=cs_signal.get('signal_type', 'BUY_LONG'),
                                    entry_price=cs_signal.get('entry_price', market_data.latest_price),
                                    confidence=cs_signal.get('confidence', 0.5),
                                    strategy=f"CANDLESTICK_{cs_signal.get('pattern_name', 'unknown').replace(' ', '_')}",
                                    indicators_used=[f"candlestick_{cs_signal.get('pattern_name', 'unknown')}"]
                                )
                                all_signals.append(converted_signal)
                        
                        analysis_components['candlestick'] = {
                            'patterns_detected': len(candlestick_signals),
                            'signals': len([s for s in candlestick_signals if s.get('confidence', 0) >= settings.analysis.confidence_threshold]),
                            'pattern_names': [s['pattern_name'] for s in candlestick_signals[:3]]  # Top 3
                        }
                        
                    except Exception as e:
                        self.logger.error(f"Erro nos candlestick patterns para {symbol}: {e}")
                        analysis_components['candlestick'] = {'error': str(e)}
                else:
                    analysis_components['candlestick'] = {'status': 'not_available'}
                
                # 3. SCORING UNIFICADO
                unified_score = self._calculate_unified_score(analysis_components, market_data)
                
                # 4. FILTRAGEM E RANKING DE SINAIS
                quality_signals = self._filter_and_rank_signals(all_signals, unified_score)
                
                # 5. SALVA OS MELHORES SINAIS
                signals_saved = 0
                if quality_signals:
                    # CORRIGIDO: Permite múltiplos sinais por symbol
                    max_signals = min(len(quality_signals), settings.system.max_signals_per_symbol)
                    top_signals = quality_signals[:max_signals]
                    
                    signals_saved = self.signal_writer.write_multiple_signals(top_signals)
                    if signals_saved > 0:
                        self._signals_generated_today += signals_saved
                
                # 6. Prepara resultado UNIFICADO
                execution_time = time.time() - start_time
                
                result = {
                    'symbol': symbol,
                    'status': 'success',
                    'timeframe': timeframe,
                    'data_points': market_data.data_points,
                    'latest_price': market_data.latest_price,
                    
                    # NOVO: Componentes de análise
                    'analysis_components': analysis_components,
                    
                    # NOVO: Scoring unificado
                    'unified_score': unified_score,
                    'score_components': unified_score.get('components', {}),
                    'recommendation': unified_score.get('recommendation', 'NEUTRAL'),
                    'is_valid': unified_score.get('is_valid', False),
                    
                    # Contadores por tipo
                    'technical_signals': len([s for s in all_signals if 'technical' in s.strategy.lower()]),
                    'pattern_signals': len([s for s in all_signals if 'pattern' in s.strategy.lower()]),
                    'candlestick_signals': len([s for s in all_signals if 'candlestick' in s.strategy.lower()]),
                    
                    # Sinais
                    'total_signals_detected': len(all_signals),
                    'quality_signals': len(quality_signals),
                    'signals_saved': signals_saved,
                    'trading_signals': [
                        {
                            'signal_type': signal.signal_type,
                            'strategy': signal.strategy,
                            'confidence': signal.confidence,
                            'entry_price': signal.entry_price,
                            'targets': signal.targets,
                            'stop_loss': signal.stop_loss
                        } for signal in quality_signals[:5]  # Top 5 para visualização
                    ],
                    
                    # Metadata
                    'execution_time': round(execution_time, 3),
                    'timestamp': datetime.now(),
                    'analysis_method': 'unified_analyzer'
                }
                
                # Log resultado DETALHADO
                tech_count = result['technical_signals']
                pattern_count = result['pattern_signals']
                candlestick_count = result['candlestick_signals']
                score = unified_score.get('total_score', 0)
                recommendation = unified_score.get('recommendation', 'NEUTRAL')
                
                if signals_saved > 0:
                    self.logger.info(
                        f"✅ {symbol}: {signals_saved} SINAIS! Score:{score:.3f} {recommendation} "
                        f"(T:{tech_count} P:{pattern_count} C:{candlestick_count}) "
                        f"Preço:${market_data.latest_price:,.2f}"
                    )
                else:
                    self.logger.info(
                        f"➖ {symbol}: Score:{score:.3f} {recommendation} "
                        f"Detectados:(T:{tech_count} P:{pattern_count} C:{candlestick_count}) "
                        f"Sem sinais válidos. Tempo:{execution_time:.2f}s"
                    )
                
                # Atualiza cache
                self._update_cache(cache_key, result)
                
                return result
                
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"❌ Erro na análise UNIFICADA de {symbol}: {e}")
            
            result = {
                'symbol': symbol,
                'status': 'error',
                'message': str(e),
                'execution_time': round(execution_time, 3),
                'timestamp': datetime.now()
            }
            
            return result
    
    def _calculate_unified_score(self, components: Dict, market_data: MarketData) -> Dict:
        """Calcula score unificado baseado em todos os componentes"""
        
        score_components = {}
        
        # Score técnico (RSI + MACD)
        tech = components.get('technical', {})
        rsi_value = tech.get('rsi_value', 50)
        tech_signals = tech.get('signals', 0)
        
        if rsi_value <= 35:
            score_components['technical'] = 0.8  # Oversold
        elif rsi_value >= 65:
            score_components['technical'] = 0.8  # Overbought
        elif tech_signals > 0:
            score_components['technical'] = 0.6
        else:
            score_components['technical'] = 0.3
        
        # Score de padrões gráficos
        patterns = components.get('patterns', {})
        if 'error' not in patterns and patterns.get('signals', 0) > 0:
            score_components['patterns'] = min(0.9, patterns.get('signals', 0) * 0.3)
        else:
            score_components['patterns'] = 0.0
        
        # Score de candlestick
        candlestick = components.get('candlestick', {})
        if 'error' not in candlestick and candlestick.get('signals', 0) > 0:
            score_components['candlestick'] = min(0.8, candlestick.get('signals', 0) * 0.2)
        else:
            score_components['candlestick'] = 0.0
        
        # Score de volume (simplificado)
        try:
            recent_volume = market_data.data['volume'].tail(5).mean()
            avg_volume = market_data.data['volume'].tail(20).mean()
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            
            if volume_ratio >= 1.5:
                score_components['volume'] = 0.7
            elif volume_ratio >= 1.2:
                score_components['volume'] = 0.5
            else:
                score_components['volume'] = 0.3
        except:
            score_components['volume'] = 0.3
        
        # Score de tendência (simplificado)
        try:
            recent_prices = market_data.data['close_price'].tail(10)
            price_change = (recent_prices.iloc[-1] - recent_prices.iloc[0]) / recent_prices.iloc[0]
            
            if abs(price_change) >= 0.02:  # 2%+
                score_components['trend'] = 0.7
            elif abs(price_change) >= 0.01:  # 1%+
                score_components['trend'] = 0.5
            else:
                score_components['trend'] = 0.3
        except:
            score_components['trend'] = 0.3
        
        # Score total (média ponderada)
        weights = {
            'technical': 0.3,
            'patterns': 0.25,
            'candlestick': 0.2,
            'volume': 0.15,
            'trend': 0.1
        }
        
        total_score = sum(
            score_components.get(component, 0) * weight 
            for component, weight in weights.items()
        )
        
        # Recomendação baseada no score
        if total_score >= 0.7:
            recommendation = "STRONG_SIGNAL"
        elif total_score >= 0.5:
            recommendation = "MODERATE_SIGNAL"
        elif total_score >= 0.3:
            recommendation = "WEAK_SIGNAL"
        else:
            recommendation = "NO_SIGNAL"
        
        # Valida se é um sinal confiável
        is_valid = (
            total_score >= 0.4 and 
            (score_components.get('technical', 0) >= 0.4 or 
             score_components.get('patterns', 0) >= 0.3 or 
             score_components.get('candlestick', 0) >= 0.3)
        )
        
        return {
            'total_score': round(total_score, 3),
            'components': score_components,
            'recommendation': recommendation,
            'is_valid': is_valid,
            'weights_used': weights
        }
    
    def _filter_and_rank_signals(self, all_signals: List[TradingSignal], unified_score: Dict) -> List[TradingSignal]:
        """Filtra e ranqueia sinais baseado na qualidade"""
        
        if not all_signals:
            return []
        
        # Filtra por confidence mínima
        min_confidence = settings.analysis.confidence_threshold
        quality_signals = [s for s in all_signals if s.confidence >= min_confidence]
        
        # Aplica boost baseado no score unificado
        score_boost = unified_score.get('total_score', 0) * 0.2
        
        for signal in quality_signals:
            # Boost de confidence baseado no score unificado
            signal.confidence = min(0.95, signal.confidence + score_boost)
            
            # Ajusta strength baseado no tipo de detector
            if 'candlestick' in signal.strategy.lower():
                signal.strength = signal.confidence * 0.8  # Candlestick tem strength um pouco menor
            elif 'pattern' in signal.strategy.lower():
                signal.strength = signal.confidence * 0.9  # Padrões gráficos são fortes
            else:
                signal.strength = signal.confidence * 0.85  # Técnicos são médios
        
        # Ordena por confidence * strength
        quality_signals.sort(key=lambda s: s.confidence * s.strength, reverse=True)
        
        return quality_signals
    
    def analyze_multiple_symbols(self, symbols: List[str] = None, 
                                timeframe: str = None) -> Dict[str, Dict]:
        """
        Análise UNIFICADA de múltiplos symbols
        """
        if symbols is None:
            symbols = settings.get_analysis_symbols()
        
        if timeframe is None:
            timeframe = settings.analysis.default_timeframe
        
        # Filtra apenas symbols com dados disponíveis
        available_symbols = self.data_reader.get_available_symbols()
        valid_symbols = [s for s in symbols if s in available_symbols]
        
        self.logger.info(f"🚀 Análise UNIFICADA múltipla: {len(valid_symbols)} symbols válidos")
        
        results = {}
        total_signals = 0
        successful_analyses = 0
        
        start_time = time.time()
        
        # Análise sequencial para evitar problemas de concorrência
        for symbol in valid_symbols:
            try:
                result = self.analyze_symbol_unified(symbol, timeframe)
                results[symbol] = result
                
                if result['status'] == 'success':
                    successful_analyses += 1
                    total_signals += result.get('signals_saved', 0)
                
                # Pequena pausa entre análises
                time.sleep(0.2)
                
            except Exception as e:
                self.logger.error(f"Erro ao analisar {symbol}: {e}")
                results[symbol] = {
                    'symbol': symbol,
                    'status': 'error',
                    'message': str(e),
                    'timestamp': datetime.now()
                }
                continue
        
        total_time = time.time() - start_time
        
        # Log resumo UNIFICADO
        self.logger.info(
            f"📊 RESUMO UNIFICADO: {successful_analyses}/{len(valid_symbols)} OK, "
            f"{total_signals} sinais gerados em {total_time:.1f}s"
        )
        
        # Adiciona metadata
        results['_summary'] = {
            'symbols_analyzed': len(valid_symbols),
            'successful_analyses': successful_analyses,
            'total_signals_generated': total_signals,
            'total_execution_time': round(total_time, 2),
            'signals_today': self._signals_generated_today,
            'analysis_method': 'unified_analyzer',
            'timestamp': datetime.now()
        }
        
        return results
    
    def run_continuous_analysis(self, interval_seconds: int = None):
        """
        Execução contínua UNIFICADA
        """
        if interval_seconds is None:
            interval_seconds = settings.system.analysis_interval
        
        self.logger.info(f"🔄 Iniciando análise contínua UNIFICADA (intervalo: {interval_seconds}s)")
        self.logger.info("Pressione Ctrl+C para parar")
        
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        try:
            while True:
                cycle_start = time.time()
                
                try:
                    self.logger.info(f"\n⚡ CICLO UNIFICADO - {datetime.now().strftime('%H:%M:%S')}")
                    
                    # Executa análise unificada de todos os symbols
                    results = self.analyze_multiple_symbols()
                    
                    # Estatísticas do ciclo
                    summary = results.get('_summary', {})
                    signals_generated = summary.get('total_signals_generated', 0)
                    successful = summary.get('successful_analyses', 0)
                    total_analyzed = summary.get('symbols_analyzed', 0)
                    
                    self.logger.info(
                        f"📊 Ciclo UNIFICADO completo: {successful}/{total_analyzed} OK, "
                        f"{signals_generated} sinais, Total hoje: {self._signals_generated_today}"
                    )
                    
                    # Reset contador de erros se sucesso
                    consecutive_errors = 0
                    
                except Exception as e:
                    consecutive_errors += 1
                    self.logger.error(f"❌ Erro no ciclo UNIFICADO #{consecutive_errors}: {e}")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        self.logger.error(f"🛑 Muitos erros consecutivos ({consecutive_errors}). Parando...")
                        break
                
                # Calcula tempo restante para próximo ciclo
                cycle_duration = time.time() - cycle_start
                sleep_time = max(0, interval_seconds - cycle_duration)
                
                if sleep_time > 0:
                    self.logger.info(f"😴 Aguardando {sleep_time:.1f}s para próximo ciclo UNIFICADO...")
                    time.sleep(sleep_time)
                else:
                    self.logger.warning(f"⚠️ Ciclo demorou {cycle_duration:.1f}s (limite: {interval_seconds}s)")
        
        except KeyboardInterrupt:
            self.logger.info("🛑 Análise contínua UNIFICADA interrompida pelo usuário")
        except Exception as e:
            self.logger.error(f"❌ Erro fatal na análise contínua UNIFICADA: {e}")
    
    def get_system_status(self) -> Dict:
        """Retorna status do sistema UNIFICADO"""
        try:
            # Testa componentes
            available_symbols = self.data_reader.get_available_symbols()
            signal_stats = self.signal_writer.get_signal_statistics()
            
            # Testa análise rápida
            test_symbol = available_symbols[0] if available_symbols else None
            test_result = None
            
            if test_symbol:
                test_start = time.time()
                test_result = self.analyze_symbol_unified(test_symbol)
                test_time = time.time() - test_start
            else:
                test_time = 0
            
            return {
                'status': 'operational',
                'system_type': 'unified_analyzer',
                'timestamp': datetime.now(),
                'components': {
                    'data_reader': 'OK' if available_symbols else 'NO_DATA',
                    'signal_writer': 'OK' if 'error' not in signal_stats else 'ERROR',
                    'technical_analyzer': 'OK',
                    'pattern_analyzer': 'OK' if PATTERNS_AVAILABLE else 'NOT_AVAILABLE',
                    'candlestick_detector': 'OK' if CANDLESTICK_AVAILABLE else 'NOT_AVAILABLE'
                },
                'symbols_available': len(available_symbols),
                'active_signals': signal_stats.get('active_signals', 0),
                'signals_today': self._signals_generated_today,
                'last_analysis_time': test_time,
                'test_symbol': test_symbol,
                'test_result': test_result.get('status', 'unknown') if test_result else None,
                'configuration': {
                    'confidence_threshold': settings.analysis.confidence_threshold,
                    'rsi_levels': f"{settings.indicators.rsi_oversold}-{settings.indicators.rsi_overbought}",
                    'pattern_min_strength': settings.patterns.min_pattern_strength,
                    'max_signals_per_symbol': settings.system.max_signals_per_symbol,
                    'analysis_method': 'unified'
                },
                'features': {
                    'technical_indicators': True,
                    'chart_patterns': PATTERNS_AVAILABLE,
                    'candlestick_patterns': CANDLESTICK_AVAILABLE,
                    'unified_scoring': True,
                    'multiple_signals': True
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now()
            }
    
    def get_signals_comparison(self, days: int = 7) -> Dict:
        """Compara efetividade dos diferentes tipos de sinais"""
        try:
            # Busca sinais dos últimos N dias
            active_signals = self.signal_writer.get_active_signals()
            
            # Agrupa por tipo de origem
            technical_signals = [s for s in active_signals if 'technical' in s.get('indicators_used', [''])[0].lower()]
            pattern_signals = [s for s in active_signals if 'pattern' in s.get('indicators_used', [''])[0].lower()]
            candlestick_signals = [s for s in active_signals if 'candlestick' in s.get('indicators_used', [''])[0].lower()]
            
            # Estatísticas gerais
            general_stats = {
                'total_unified_signals': len(active_signals),
                'symbols_count': len(set(s['symbol'] for s in active_signals)),
                'avg_confidence': sum(s.get('confidence', 0) for s in active_signals) / len(active_signals) if active_signals else 0,
                'by_source': {
                    'technical': len(technical_signals),
                    'pattern': len(pattern_signals),
                    'candlestick': len(candlestick_signals)
                }
            }
            
            # Detalhamento por padrão
            detailed_breakdown = []
            
            # Agrupa por estratégia
            from collections import defaultdict
            strategy_groups = defaultdict(list)
            
            for signal in active_signals:
                strategy = signal.get('indicators_used', ['unknown'])[0]
                strategy_groups[strategy].append(signal)
            
            for strategy, signals in strategy_groups.items():
                if len(signals) > 0:
                    avg_conf = sum(s.get('confidence', 0) for s in signals) / len(signals)
                    avg_strength = sum(s.get('confluence_score', 0) for s in signals) / len(signals) / 100  # Normaliza
                    
                    # Determina origem e tipo
                    if 'technical' in strategy:
                        source = 'technical'
                        pattern_type = 'technical'
                    elif 'pattern' in strategy:
                        source = 'pattern'
                        pattern_type = strategy.replace('pattern_', '').replace('_', ' ').title()
                    elif 'candlestick' in strategy:
                        source = 'candlestick'
                        pattern_type = strategy.replace('candlestick_', '').replace('_', ' ').title()
                    else:
                        source = 'unknown'
                        pattern_type = strategy
                    
                    detailed_breakdown.append({
                        'signal_source': source,
                        'pattern_name': pattern_type,
                        'pattern_type': signals[0].get('signal_type', 'unknown'),
                        'total_signals': len(signals),
                        'avg_confidence': round(avg_conf, 3),
                        'avg_strength': round(avg_strength, 3)
                    })
            
            # Ordena por total de sinais
            detailed_breakdown.sort(key=lambda x: x['total_signals'], reverse=True)
            
            return {
                'comparison_period_days': days,
                'general_stats': general_stats,
                'detailed_breakdown': detailed_breakdown,
                'analysis_timestamp': datetime.now(),
                'system_type': 'unified_analyzer'
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'timestamp': datetime.now()
            }
    
    def cleanup_old_data(self, days: int) -> Dict:
        """Limpa dados antigos"""
        try:
            removed_signals = self.signal_writer.cleanup_old_signals(days)
            
            return {
                'status': 'success',
                'removed_signals': removed_signals,
                'days_cleaned': days,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now()
            }

# Alias para compatibilidade
TradingAnalyzer = UnifiedTradingAnalyzer

# Funções utilitárias para diagnóstico
def test_unified_analyzer():
    """Testa o analyzer UNIFICADO"""
    print("🧪 TESTANDO ANALYZER UNIFICADO")
    print("=" * 40)
    
    try:
        analyzer = UnifiedTradingAnalyzer()
        
        # Status do sistema
        print("📊 STATUS DO SISTEMA UNIFICADO:")
        status = analyzer.get_system_status()
        print(f"   Status: {status['status']}")
        print(f"   Tipo: {status['system_type']}")
        print(f"   Symbols disponíveis: {status['symbols_available']}")
        print(f"   Sinais ativos: {status['active_signals']}")
        print(f"   Sinais hoje: {status['signals_today']}")
        
        # Componentes
        components = status['components']
        print(f"\n🧩 COMPONENTES:")
        for component, status_comp in components.items():
            icon = "✅" if status_comp == "OK" else "❌" if status_comp == "ERROR" else "⚠️"
            print(f"   {icon} {component}: {status_comp}")
        
        # Features
        features = status['features']
        print(f"\n🔧 FUNCIONALIDADES:")
        for feature, enabled in features.items():
            icon = "✅" if enabled else "❌"
            print(f"   {icon} {feature}: {enabled}")
        
        # Teste de análise
        if status['symbols_available'] > 0:
            print(f"\n🔍 TESTE DE ANÁLISE UNIFICADA:")
            
            symbols = analyzer.data_reader.get_available_symbols()
            test_symbol = symbols[0]
            
            print(f"   Testando: {test_symbol}")
            
            result = analyzer.analyze_symbol_unified(test_symbol)
            
            print(f"   Status: {result['status']}")
            if result['status'] == 'success':
                print(f"   Score unificado: {result.get('unified_score', {}).get('total_score', 0):.3f}")
                print(f"   Recomendação: {result.get('recommendation', 'N/A')}")
                print(f"   Técnicos: {result.get('technical_signals', 0)}")
                print(f"   Padrões: {result.get('pattern_signals', 0)}")
                print(f"   Candlestick: {result.get('candlestick_signals', 0)}")
                print(f"   Sinais salvos: {result.get('signals_saved', 0)}")
                print(f"   Tempo: {result.get('execution_time', 0)}s")
                
                if result.get('signals_saved', 0) > 0:
                    print(f"   ✅ SINAIS GERADOS COM SUCESSO!")
                else:
                    print(f"   ⚠️  Nenhum sinal gerado (pode ser normal)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

if __name__ == "__main__":
    test_unified_analyzer()