"""
Trading Analyzer CORRIGIDO - Sem travamentos e com configurações menos restritivas
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

class TradingAnalyzer:
    """Trading Analyzer CORRIGIDO para evitar travamentos e gerar mais sinais"""
    
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
        self.technical_analyzer = TechnicalAnalyzer()
        
        # NOVO: Lock para evitar concorrência
        self._analysis_lock = threading.Lock()
        
        # NOVO: Cache de análises recentes
        self._analysis_cache = {}
        self._cache_expiry = {}
        self._cache_timeout = 300  # 5 minutos
        
        # NOVO: Contador de sinais gerados
        self._signals_generated_today = 0
        self._last_reset_date = datetime.now().date()
        
        self.logger.info("✅ Trading Analyzer corrigido inicializado")
        self.logger.info(f"📊 Configurações atuais:")
        self.logger.info(f"   Confidence threshold: {settings.analysis.confidence_threshold}")
        self.logger.info(f"   RSI levels: {settings.indicators.rsi_oversold}-{settings.indicators.rsi_overbought}")
        self.logger.info(f"   Volume min ratio: {settings.indicators.min_volume_ratio}x")
    
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
    
    def analyze_symbol(self, symbol: str, timeframe: str = None) -> Dict:
        """
        Analisa symbol específico - VERSÃO CORRIGIDA
        """
        if timeframe is None:
            timeframe = settings.analysis.default_timeframe
        
        # Reset contador se necessário
        self._reset_daily_counter()
        
        cache_key = f"{symbol}_{timeframe}"
        start_time = time.time()
        
        self.logger.info(f"🔍 Analisando {symbol} {timeframe}")
        
        # Verifica cache primeiro
        if self._is_cache_valid(cache_key):
            cached_result = self._analysis_cache[cache_key]
            self.logger.debug(f"📋 Usando análise em cache para {symbol}")
            return cached_result
        
        try:
            with self._analysis_lock:  # NOVO: Lock para evitar concorrência
                
                # 1. Buscar dados com filtros para dados limpos
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
                
                # 2. Análise técnica
                technical_results = self.technical_analyzer.analyze_all(market_data)
                
                # 3. Gera sinais de trading
                trading_signals = self.technical_analyzer.generate_trading_signals(
                    market_data, technical_results
                )
                
                # 4. Escreve sinais se houver
                signals_saved = 0
                if trading_signals:
                    signals_saved = self.signal_writer.write_multiple_signals(trading_signals)
                    if signals_saved > 0:
                        self._signals_generated_today += signals_saved
                
                # 5. Prepara resultado
                execution_time = time.time() - start_time
                
                # Coleta métricas dos indicadores
                rsi_value = 50.0
                macd_value = 0.0
                
                if 'RSI' in technical_results:
                    rsi_value = technical_results['RSI'].latest_value
                
                if 'MACD' in technical_results:
                    macd_value = technical_results['MACD'].latest_value
                
                result = {
                    'symbol': symbol,
                    'status': 'success',
                    'timeframe': timeframe,
                    'data_points': market_data.data_points,
                    'latest_price': market_data.latest_price,
                    
                    # Indicadores
                    'rsi_value': rsi_value,
                    'macd_value': macd_value,
                    
                    # Sinais
                    'signals_generated': len(trading_signals),
                    'signals_saved': signals_saved,
                    'trading_signals': [
                        {
                            'signal_type': signal.signal_type,
                            'confidence': signal.confidence,
                            'entry_price': signal.entry_price,
                            'targets': signal.targets,
                            'stop_loss': signal.stop_loss
                        } for signal in trading_signals
                    ],
                    
                    # Metadata
                    'execution_time': round(execution_time, 3),
                    'timestamp': datetime.now(),
                    'analysis_method': 'corrected_analyzer'
                }
                
                # Log resultado
                if signals_saved > 0:
                    self.logger.info(f"✅ {symbol}: {signals_saved} SINAIS GERADOS! RSI:{rsi_value:.1f} Preço:${market_data.latest_price:,.2f}")
                else:
                    self.logger.info(f"➖ {symbol}: Sem sinais. RSI:{rsi_value:.1f} Dados:{market_data.data_points} Tempo:{execution_time:.2f}s")
                
                # Atualiza cache
                self._update_cache(cache_key, result)
                
                return result
                
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"❌ Erro na análise de {symbol}: {e}")
            
            result = {
                'symbol': symbol,
                'status': 'error',
                'message': str(e),
                'execution_time': round(execution_time, 3),
                'timestamp': datetime.now()
            }
            
            return result
    
    def analyze_multiple_symbols(self, symbols: List[str] = None, 
                                timeframe: str = None) -> Dict[str, Dict]:
        """
        Analisa múltiplos symbols - SEQUENCIAL para evitar locks
        """
        if symbols is None:
            symbols = settings.get_analysis_symbols()
        
        if timeframe is None:
            timeframe = settings.analysis.default_timeframe
        
        # Filtra apenas symbols com dados disponíveis
        available_symbols = self.data_reader.get_available_symbols()
        valid_symbols = [s for s in symbols if s in available_symbols]
        
        self.logger.info(f"🚀 Análise múltipla: {len(valid_symbols)} symbols válidos")
        
        results = {}
        total_signals = 0
        successful_analyses = 0
        
        start_time = time.time()
        
        # NOVO: Análise SEQUENCIAL em vez de paralela para evitar locks
        for symbol in valid_symbols:
            try:
                result = self.analyze_symbol(symbol, timeframe)
                results[symbol] = result
                
                if result['status'] == 'success':
                    successful_analyses += 1
                    total_signals += result.get('signals_saved', 0)
                
                # NOVO: Pequena pausa entre análises para evitar sobrecarga
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
        
        # Log resumo
        self.logger.info(f"📊 RESUMO: {successful_analyses}/{len(valid_symbols)} OK, "
                        f"{total_signals} sinais gerados em {total_time:.1f}s")
        
        # Adiciona metadata
        results['_summary'] = {
            'symbols_analyzed': len(valid_symbols),
            'successful_analyses': successful_analyses,
            'total_signals_generated': total_signals,
            'total_execution_time': round(total_time, 2),
            'signals_today': self._signals_generated_today,
            'timestamp': datetime.now()
        }
        
        return results
    
    def run_continuous_analysis(self, interval_seconds: int = None):
        """
        Execução contínua - CORRIGIDA para evitar travamentos
        """
        if interval_seconds is None:
            interval_seconds = settings.system.analysis_interval
        
        self.logger.info(f"🔄 Iniciando análise contínua (intervalo: {interval_seconds}s)")
        self.logger.info("Pressione Ctrl+C para parar")
        
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        try:
            while True:
                cycle_start = time.time()
                
                try:
                    self.logger.info(f"\n⚡ CICLO DE ANÁLISE - {datetime.now().strftime('%H:%M:%S')}")
                    
                    # Executa análise de todos os symbols
                    results = self.analyze_multiple_symbols()
                    
                    # Estatísticas do ciclo
                    summary = results.get('_summary', {})
                    signals_generated = summary.get('total_signals_generated', 0)
                    successful = summary.get('successful_analyses', 0)
                    total_analyzed = summary.get('symbols_analyzed', 0)
                    
                    self.logger.info(f"📊 Ciclo completo: {successful}/{total_analyzed} OK, "
                                   f"{signals_generated} sinais, "
                                   f"Total hoje: {self._signals_generated_today}")
                    
                    # Reset contador de erros se sucesso
                    consecutive_errors = 0
                    
                except Exception as e:
                    consecutive_errors += 1
                    self.logger.error(f"❌ Erro no ciclo #{consecutive_errors}: {e}")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        self.logger.error(f"🛑 Muitos erros consecutivos ({consecutive_errors}). Parando...")
                        break
                
                # Calcula tempo restante para próximo ciclo
                cycle_duration = time.time() - cycle_start
                sleep_time = max(0, interval_seconds - cycle_duration)
                
                if sleep_time > 0:
                    self.logger.info(f"😴 Aguardando {sleep_time:.1f}s para próximo ciclo...")
                    time.sleep(sleep_time)
                else:
                    self.logger.warning(f"⚠️ Ciclo demorou {cycle_duration:.1f}s (limite: {interval_seconds}s)")
        
        except KeyboardInterrupt:
            self.logger.info("🛑 Análise contínua interrompida pelo usuário")
        except Exception as e:
            self.logger.error(f"❌ Erro fatal na análise contínua: {e}")
    
    def get_system_status(self) -> Dict:
        """Retorna status do sistema"""
        try:
            # Testa componentes
            available_symbols = self.data_reader.get_available_symbols()
            signal_stats = self.signal_writer.get_signal_statistics()
            
            # Testa análise rápida
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
                'timestamp': datetime.now(),
                'components': {
                    'data_reader': 'OK' if available_symbols else 'NO_DATA',
                    'signal_writer': 'OK' if 'error' not in signal_stats else 'ERROR',
                    'technical_analyzer': 'OK'
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
                    'volume_min_ratio': settings.indicators.min_volume_ratio,
                    'parallel_analysis': settings.system.parallel_analysis
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
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

# Funções utilitárias para diagnóstico
def test_analyzer():
    """Testa o analyzer corrigido"""
    print("🧪 TESTANDO ANALYZER CORRIGIDO")
    print("=" * 35)
    
    try:
        analyzer = TradingAnalyzer()
        
        # Status do sistema
        print("📊 STATUS DO SISTEMA:")
        status = analyzer.get_system_status()
        print(f"   Status: {status['status']}")
        print(f"   Symbols disponíveis: {status['symbols_available']}")
        print(f"   Sinais ativos: {status['active_signals']}")
        print(f"   Sinais hoje: {status['signals_today']}")
        
        # Teste de análise
        if status['symbols_available'] > 0:
            print(f"\n🔍 TESTE DE ANÁLISE:")
            
            symbols = analyzer.data_reader.get_available_symbols()
            test_symbol = symbols[0]
            
            print(f"   Testando: {test_symbol}")
            
            result = analyzer.analyze_symbol(test_symbol)
            
            print(f"   Status: {result['status']}")
            print(f"   RSI: {result.get('rsi_value', 'N/A')}")
            print(f"   Sinais gerados: {result.get('signals_generated', 0)}")
            print(f"   Sinais salvos: {result.get('signals_saved', 0)}")
            print(f"   Tempo: {result.get('execution_time', 0)}s")
            
            if result.get('signals_saved', 0) > 0:
                print(f"   ✅ SINAL GERADO COM SUCESSO!")
            else:
                print(f"   ⚠️  Nenhum sinal gerado (normal se não há setup)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

if __name__ == "__main__":
    test_analyzer()