"""
Analyzer Core - Orquestrador principal do sistema de análise
"""
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.data_reader import DataReader, MarketData
from core.signal_writer import SignalWriter, TradingSignal
from indicators.technical import TechnicalAnalyzer
from config.settings import settings

class TradingAnalyzer:
    """Classe principal do analisador de trading"""
    
    def __init__(self):
        # Configurar logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Inicializar componentes
        self.data_reader = DataReader()
        self.signal_writer = SignalWriter()
        self.technical_analyzer = TechnicalAnalyzer()
        
        # Validar configurações
        self._validate_setup()
        
        self.logger.info("Trading Analyzer inicializado com sucesso")
    
    def _setup_logging(self):
        """Configura o sistema de logging"""
        logging.basicConfig(
            level=getattr(logging, settings.system.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(settings.system.log_file),
                logging.StreamHandler()
            ]
        )
    
    def _validate_setup(self):
        """Valida se o sistema está configurado corretamente"""
        if not settings.validate_paths():
            raise RuntimeError("Caminhos dos bancos inválidos")
        
        # Testa conexões
        try:
            available_symbols = self.data_reader.get_available_symbols()
            if not available_symbols:
                self.logger.warning("Nenhum symbol encontrado no banco de dados")
            else:
                self.logger.info(f"Symbols disponíveis: {len(available_symbols)}")
                
        except Exception as e:
            self.logger.error(f"Erro ao validar conexão com banco de dados: {e}")
            raise
    
    def analyze_symbol(self, symbol: str, timeframe: str = None) -> Dict[str, any]:
        """
        Analisa um symbol específico
        
        Args:
            symbol: Symbol da crypto
            timeframe: Timeframe para análise
        
        Returns:
            Dicionário com resultados da análise
        """
        if timeframe is None:
            timeframe = settings.analysis.default_timeframe
        
        start_time = time.time()
        
        try:
            # 1. Buscar dados
            self.logger.debug(f"Buscando dados para {symbol} {timeframe}")
            market_data = self.data_reader.get_latest_data(symbol, timeframe)
            
            if not market_data:
                return {
                    'symbol': symbol,
                    'status': 'error',
                    'message': 'Dados não encontrados',
                    'timestamp': datetime.now()
                }
            
            if not market_data.is_sufficient_data:
                return {
                    'symbol': symbol,
                    'status': 'insufficient_data',
                    'message': f'Apenas {market_data.data_points} pontos disponíveis',
                    'timestamp': datetime.now()
                }
            
            # 2. Executar análise técnica
            self.logger.debug(f"Executando análise técnica para {symbol}")
            analysis_results = self.technical_analyzer.analyze_all(market_data)
            
            # 3. Gerar sinais de trading
            trading_signals = self.technical_analyzer.generate_trading_signals(
                market_data, analysis_results
            )
            
            # 4. Salvar sinais válidos
            saved_signals = 0
            if trading_signals:
                saved_signals = self.signal_writer.write_multiple_signals(trading_signals)
            
            # 5. Preparar resultado
            execution_time = time.time() - start_time
            
            result = {
                'symbol': symbol,
                'status': 'success',
                'data_points': market_data.data_points,
                'latest_price': market_data.latest_price,
                'signals_generated': len(trading_signals),
                'signals_saved': saved_signals,
                'execution_time': round(execution_time, 3),
                'timestamp': datetime.now(),
                'analysis_summary': self._create_analysis_summary(analysis_results)
            }
            
            self.logger.info(
                f"[SUCCESS] {symbol}: {len(trading_signals)} sinais gerados, "
                f"{saved_signals} salvos em {execution_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"[ERROR] Erro ao analisar {symbol}: {e}")
            return {
                'symbol': symbol,
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now()
            }
    
    def analyze_multiple_symbols(self, symbols: List[str] = None, 
                                timeframe: str = None) -> Dict[str, Dict]:
        """
        Analisa múltiplos symbols
        
        Args:
            symbols: Lista de symbols (padrão: configuração)
            timeframe: Timeframe para análise
        
        Returns:
            Dicionário com resultados por symbol
        """
        if symbols is None:
            symbols = settings.get_analysis_symbols()
        
        if timeframe is None:
            timeframe = settings.analysis.default_timeframe
        
        start_time = time.time()
        results = {}
        
        self.logger.info(f"[START] Iniciando análise de {len(symbols)} symbols")
        
        # Debug: mostrar symbols disponíveis vs configurados
        available_symbols = self.data_reader.get_available_symbols()
        self.logger.info(f"[DEBUG] Symbols disponíveis no banco: {available_symbols}")
        self.logger.info(f"[DEBUG] Symbols configurados para análise: {symbols}")
        
        # Verificar se há correspondência
        missing_symbols = [s for s in symbols if s not in available_symbols]
        if missing_symbols:
            self.logger.warning(f"[WARNING] Symbols não encontrados no banco: {missing_symbols}")
        
        available_for_analysis = [s for s in symbols if s in available_symbols]
        if available_for_analysis:
            self.logger.info(f"[INFO] Symbols que serão analisados: {available_for_analysis}")
            # Atualiza a lista para só analisar os disponíveis
            symbols = available_for_analysis
        else:
            self.logger.error("[ERROR] Nenhum symbol configurado foi encontrado no banco!")
            return {}
        
        if settings.system.parallel_analysis and len(symbols) > 1:
            # Análise paralela
            with ThreadPoolExecutor(max_workers=settings.system.max_workers) as executor:
                future_to_symbol = {
                    executor.submit(self.analyze_symbol, symbol, timeframe): symbol 
                    for symbol in symbols
                }
                
                for future in as_completed(future_to_symbol):
                    symbol = future_to_symbol[future]
                    try:
                        result = future.result()
                        results[symbol] = result
                    except Exception as e:
                        self.logger.error(f"Erro na análise paralela de {symbol}: {e}")
                        results[symbol] = {
                            'symbol': symbol,
                            'status': 'error',
                            'message': str(e),
                            'timestamp': datetime.now()
                        }
        else:
            # Análise sequencial
            for symbol in symbols:
                results[symbol] = self.analyze_symbol(symbol, timeframe)
        
        # Estatísticas finais
        total_time = time.time() - start_time
        successful = sum(1 for r in results.values() if r['status'] == 'success')
        total_signals = sum(r.get('signals_generated', 0) for r in results.values())
        
        self.logger.info(
            f"[COMPLETE] Análise concluída: {successful}/{len(symbols)} symbols, "
            f"{total_signals} sinais em {total_time:.2f}s"
        )
        
        return results
    
    def _create_analysis_summary(self, analysis_results: Dict) -> Dict:
        """Cria resumo da análise técnica"""
        summary = {}
        
        for indicator_name, result in analysis_results.items():
            summary[indicator_name] = {
                'latest_value': result.latest_value,
                'signals_count': len(result.signals),
                'has_signals': result.has_signals,
                'metadata': result.metadata
            }
        
        return summary
    
    def run_continuous_analysis(self, interval_seconds: int = None):
        """
        Executa análise contínua em loop
        
        Args:
            interval_seconds: Intervalo entre análises (padrão: configuração)
        """
        if interval_seconds is None:
            interval_seconds = settings.system.analysis_interval
        
        self.logger.info(f"[CONTINUOUS] Iniciando análise contínua (intervalo: {interval_seconds}s)")
        
        try:
            while True:
                cycle_start = time.time()
                
                # Executar análise
                results = self.analyze_multiple_symbols()
                
                # Log do ciclo
                successful = sum(1 for r in results.values() if r['status'] == 'success')
                cycle_time = time.time() - cycle_start
                
                self.logger.info(
                    f"[CYCLE] Ciclo concluído: {successful} symbols analisados em {cycle_time:.1f}s"
                )
                
                # Aguardar próximo ciclo
                sleep_time = max(0, interval_seconds - cycle_time)
                if sleep_time > 0:
                    self.logger.debug(f"[WAIT] Aguardando {sleep_time:.1f}s para próximo ciclo")
                    time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            self.logger.info("[STOP] Análise contínua interrompida pelo usuário")
        except Exception as e:
            self.logger.error(f"[ERROR] Erro na análise contínua: {e}")
            raise
    
    def get_system_status(self) -> Dict:
        """Retorna status do sistema"""
        try:
            # Estatísticas dos sinais
            signal_stats = self.signal_writer.get_signal_statistics()
            
            # Symbols disponíveis
            available_symbols = self.data_reader.get_available_symbols()
            
            # Símbolos configurados
            configured_symbols = settings.get_analysis_symbols()
            
            return {
                'status': 'healthy',
                'timestamp': datetime.now(),
                'signal_statistics': signal_stats,
                'available_symbols': len(available_symbols),
                'configured_symbols': len(configured_symbols),
                'database_paths': {
                    'stream_db': settings.database.stream_db_path,
                    'signals_db': settings.database.signals_db_path
                },
                'configuration': {
                    'analysis_interval': settings.system.analysis_interval,
                    'confidence_threshold': settings.analysis.confidence_threshold,
                    'parallel_analysis': settings.system.parallel_analysis
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now()
            }
    
    def cleanup_old_data(self, days_old: int = 7) -> Dict:
        """
        Limpa dados antigos
        
        Args:
            days_old: Dias para considerar como antigo
        
        Returns:
            Resultado da limpeza
        """
        try:
            removed_signals = self.signal_writer.cleanup_old_signals(days_old)
            
            self.logger.info(f"[CLEANUP] Limpeza concluída: {removed_signals} sinais removidos")
            
            return {
                'status': 'success',
                'removed_signals': removed_signals,
                'days_old': days_old,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"Erro na limpeza: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now()
            }

# Exemplo de uso/teste
if __name__ == "__main__":
    # Configura logging para teste
    logging.basicConfig(level=logging.INFO)
    
    # Instancia o analisador
    analyzer = TradingAnalyzer()
    
    # Testa análise de um symbol
    print("=== TESTE DE ANÁLISE INDIVIDUAL ===")
    result = analyzer.analyze_symbol("BTCUSDT")
    print(f"Resultado: {result}")
    
    # Testa status do sistema
    print("\n=== STATUS DO SISTEMA ===")
    status = analyzer.get_system_status()
    print(f"Status: {status}")
    
    # Testa análise múltipla (limitada para teste)
    print("\n=== TESTE DE ANÁLISE MÚLTIPLA ===")
    test_symbols = ["BTCUSDT", "ETHUSDT"]
    multi_results = analyzer.analyze_multiple_symbols(test_symbols)
    
    for symbol, result in multi_results.items():
        print(f"{symbol}: {result['status']} - {result.get('signals_generated', 0)} sinais")