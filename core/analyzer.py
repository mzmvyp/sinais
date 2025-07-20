"""
Trading Analyzer CORRIGIDO - INTEGRAÇÃO COMPLETA
Substitui o analyzer original com TODOS os detectores integrados
"""
import logging
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import threading

# Imports do sistema existente
from core.data_reader import DataReader, MarketData
from core.signal_writer import SignalWriter, TradingSignal
from indicators.technical import TechnicalAnalyzer

# INTEGRAÇÃO DOS DETECTORES QUE ESTAVAM FALTANDO
try:
    from indicators.patterns import PatternAnalyzer
    PATTERNS_AVAILABLE = True
except ImportError:
    PATTERNS_AVAILABLE = False
    print("⚠️ PatternAnalyzer não disponível")

try:
    from indicators.candlestick_patterns_detector import CandlestickDetector, generate_candlestick_signals
    CANDLESTICK_AVAILABLE = True
except ImportError:
    CANDLESTICK_AVAILABLE = False
    print("⚠️ CandlestickDetector não disponível")

from config.settings import settings

class TradingAnalyzer:
    """Trading Analyzer CORRIGIDO com TODOS os detectores integrados"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
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
        
        if CANDLESTICK_AVAILABLE:
            self.candlestick_detector = CandlestickDetector()
            self.logger.info("✅ CandlestickDetector integrado (43 padrões)")
        else:
            self.candlestick_detector = None
        
        self._analysis_lock = threading.Lock()
        self._analysis_cache = {}
        self._cache_expiry = {}
        self._cache_timeout = 300
        self._signals_generated_today = 0
        self._last_reset_date = datetime.now().date()
        
        # Aplica configurações otimizadas
        self._apply_optimized_settings()
        
        self.logger.info("🚀 Trading Analyzer CORRIGIDO inicializado")
        self.logger.info(f"📊 Componentes: Técnicos=✅ Padrões={'✅' if PATTERNS_AVAILABLE else '❌'} Candlestick={'✅' if CANDLESTICK_AVAILABLE else '❌'}")
    
    def _apply_optimized_settings(self):
        """Aplica configurações otimizadas"""
        settings.analysis.confidence_threshold = 0.3
        settings.indicators.rsi_overbought = 65
        settings.indicators.rsi_oversold = 35
        settings.indicators.min_volume_ratio = 1.2
        settings.patterns.min_pattern_strength = 0.3
        settings.system.max_signals_per_symbol = 3
        
        self.logger.info("🔧 Configurações otimizadas aplicadas")
    
    def analyze_symbol(self, symbol: str, timeframe: str = None) -> Dict:
        """Análise UNIFICADA com TODOS os detectores"""
        if timeframe is None:
            timeframe = settings.analysis.default_timeframe
        
        start_time = time.time()
        self.logger.info(f"🔍 Análise COMPLETA: {symbol} {timeframe}")
        
        try:
            # 1. Buscar dados
            market_data = self.data_reader.get_latest_data(symbol, timeframe)
            
            if not market_data or not market_data.is_sufficient_data:
                return {
                    'symbol': symbol,
                    'status': 'insufficient_data',
                    'data_points': market_data.data_points if market_data else 0,
                    'timestamp': datetime.now()
                }
            
            # 2. ANÁLISE COMPLETA - TODOS OS COMPONENTES
            all_signals = []
            components = {}
            
            # 2.1 Indicadores Técnicos
            technical_results = self.technical_analyzer.analyze_all(market_data)
            technical_signals = self.technical_analyzer.generate_trading_signals(market_data, technical_results)
            all_signals.extend(technical_signals)
            components['technical'] = {
                'signals': len(technical_signals),
                'rsi': technical_results.get('RSI', type('obj', (), {'latest_value': 50})).latest_value
            }
            
            # 2.2 Padrões Gráficos
            if self.pattern_analyzer:
                try:
                    pattern_results = self.pattern_analyzer.analyze_all_patterns(market_data)
                    pattern_signals = self.pattern_analyzer.generate_pattern_signals(market_data, pattern_results)
                    
                    for ps in pattern_signals:
                        if not isinstance(ps, TradingSignal):
                            signal = TradingSignal(
                                symbol=symbol,
                                signal_type=ps.get('signal_type', 'BUY_LONG'),
                                entry_price=ps.get('entry_price', market_data.latest_price),
                                confidence=ps.get('confidence', 0.5)
                            )
                            all_signals.append(signal)
                        else:
                            all_signals.append(ps)
                    
                    components['patterns'] = {'signals': len(pattern_signals)}
                except Exception as e:
                    components['patterns'] = {'error': str(e)}
            
            # 2.3 Candlestick Patterns (43 padrões)
            if self.candlestick_detector:
                try:
                    cs_signals = generate_candlestick_signals(market_data.data, symbol)
                    
                    for cs in cs_signals:
                        if cs.get('confidence', 0) >= settings.analysis.confidence_threshold:
                            signal = TradingSignal(
                                symbol=symbol,
                                signal_type=cs.get('signal_type', 'BUY_LONG'),
                                entry_price=cs.get('entry_price', market_data.latest_price),
                                confidence=cs.get('confidence', 0.5),
                                strategy=f"CANDLESTICK_{cs.get('pattern_name', 'unknown').replace(' ', '_')}"
                            )
                            all_signals.append(signal)
                    
                    components['candlestick'] = {
                        'total_patterns': len(cs_signals),
                        'valid_signals': len([s for s in cs_signals if s.get('confidence', 0) >= settings.analysis.confidence_threshold]),
                        'patterns': [s['pattern_name'] for s in cs_signals[:3]]
                    }
                except Exception as e:
                    components['candlestick'] = {'error': str(e)}
            
            # 3. Filtra e salva sinais
            valid_signals = [s for s in all_signals if s.confidence >= settings.analysis.confidence_threshold]
            
            # Limita quantidade por symbol
            max_signals = min(len(valid_signals), settings.system.max_signals_per_symbol)
            final_signals = sorted(valid_signals, key=lambda x: x.confidence, reverse=True)[:max_signals]
            
            signals_saved = 0
            if final_signals:
                signals_saved = self.signal_writer.write_multiple_signals(final_signals)
                self._signals_generated_today += signals_saved
            
            execution_time = time.time() - start_time
            
            # 4. Resultado
            result = {
                'symbol': symbol,
                'status': 'success',
                'data_points': market_data.data_points,
                'latest_price': market_data.latest_price,
                'components': components,
                'technical_signals': len([s for s in all_signals if 'technical' in s.strategy.lower()]),
                'pattern_signals': len([s for s in all_signals if 'pattern' in s.strategy.lower()]),  
                'candlestick_signals': len([s for s in all_signals if 'candlestick' in s.strategy.lower()]),
                'total_detected': len(all_signals),
                'valid_signals': len(valid_signals),
                'signals_saved': signals_saved,
                'execution_time': round(execution_time, 3),
                'timestamp': datetime.now()
            }
            
            # Log resultado
            tech = result['technical_signals']
            patt = result['pattern_signals'] 
            cand = result['candlestick_signals']
            
            if signals_saved > 0:
                self.logger.info(f"✅ {symbol}: {signals_saved} SINAIS! (T:{tech} P:{patt} C:{cand}) ${market_data.latest_price:,.2f}")
            else:
                self.logger.info(f"➖ {symbol}: Detectados (T:{tech} P:{patt} C:{cand}) sem sinais válidos")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Erro na análise de {symbol}: {e}")
            return {
                'symbol': symbol,
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now()
            }
    
    def analyze_multiple_symbols(self, symbols: List[str] = None, timeframe: str = None) -> Dict[str, Dict]:
        """Análise múltipla com TODOS os detectores"""
        if symbols is None:
            symbols = settings.get_analysis_symbols()
        
        available_symbols = self.data_reader.get_available_symbols()
        valid_symbols = [s for s in symbols if s in available_symbols]
        
        self.logger.info(f"🚀 Análise múltipla COMPLETA: {len(valid_symbols)} symbols")
        
        results = {}
        total_signals = 0
        successful = 0
        
        for symbol in valid_symbols:
            try:
                result = self.analyze_symbol(symbol, timeframe)
                results[symbol] = result
                
                if result['status'] == 'success':
                    successful += 1
                    total_signals += result.get('signals_saved', 0)
                
                time.sleep(0.2)  # Pausa entre análises
                
            except Exception as e:
                results[symbol] = {'symbol': symbol, 'status': 'error', 'message': str(e)}
        
        self.logger.info(f"📊 RESUMO: {successful}/{len(valid_symbols)} OK, {total_signals} sinais gerados")
        
        results['_summary'] = {
            'symbols_analyzed': len(valid_symbols),
            'successful_analyses': successful,
            'total_signals_generated': total_signals,
            'signals_today': self._signals_generated_today,
            'timestamp': datetime.now()
        }
        
        return results
    
    def run_continuous_analysis(self, interval_seconds: int = None):
        """Execução contínua COMPLETA"""
        if interval_seconds is None:
            interval_seconds = settings.system.analysis_interval
        
        self.logger.info(f"🔄 Análise contínua COMPLETA (intervalo: {interval_seconds}s)")
        
        try:
            while True:
                cycle_start = time.time()
                
                try:
                    self.logger.info(f"\n⚡ CICLO COMPLETO - {datetime.now().strftime('%H:%M:%S')}")
                    results = self.analyze_multiple_symbols()
                    
                    summary = results.get('_summary', {})
                    signals = summary.get('total_signals_generated', 0)
                    successful = summary.get('successful_analyses', 0)
                    total = summary.get('symbols_analyzed', 0)
                    
                    self.logger.info(f"📊 Ciclo: {successful}/{total} OK, {signals} sinais, Total hoje: {self._signals_generated_today}")
                    
                except Exception as e:
                    self.logger.error(f"❌ Erro no ciclo: {e}")
                
                # Aguarda próximo ciclo
                cycle_time = time.time() - cycle_start
                sleep_time = max(0, interval_seconds - cycle_time)
                
                if sleep_time > 0:
                    self.logger.info(f"😴 Aguardando {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
        
        except KeyboardInterrupt:
            self.logger.info("🛑 Análise contínua interrompida")
    
    def get_system_status(self) -> Dict:
        """Status do sistema COMPLETO"""
        try:
            available_symbols = self.data_reader.get_available_symbols()
            signal_stats = self.signal_writer.get_signal_statistics()
            
            test_symbol = available_symbols[0] if available_symbols else None
            test_result = None
            
            if test_symbol:
                test_start = time.time()
                test_result = self.analyze_symbol(test_symbol)
                test_time = time.time() - test_start
            else:
                test_time = 0
            
            return {
                'status': 'operational',
                'system_version': 'corrected_unified',
                'timestamp': datetime.now(),
                'components': {
                    'data_reader': 'OK' if available_symbols else 'NO_DATA',
                    'signal_writer': 'OK',
                    'technical_analyzer': 'OK',
                    'pattern_analyzer': 'OK' if PATTERNS_AVAILABLE else 'NOT_AVAILABLE',
                    'candlestick_detector': 'OK' if CANDLESTICK_AVAILABLE else 'NOT_AVAILABLE'
                },
                'symbols_available': len(available_symbols),
                'active_signals': signal_stats.get('active_signals', 0),
                'signals_today': self._signals_generated_today,
                'test_time': test_time,
                'test_symbol': test_symbol,
                'configuration': {
                    'confidence_threshold': settings.analysis.confidence_threshold,
                    'rsi_levels': f"{settings.indicators.rsi_oversold}-{settings.indicators.rsi_overbought}",
                    'max_signals_per_symbol': settings.system.max_signals_per_symbol,
                    'candlestick_enabled': CANDLESTICK_AVAILABLE,
                    'patterns_enabled': PATTERNS_AVAILABLE
                }
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def cleanup_old_data(self, days: int) -> Dict:
        """Limpa dados antigos"""
        try:
            removed = self.signal_writer.cleanup_old_signals(days)
            return {'status': 'success', 'removed_signals': removed, 'days': days}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
