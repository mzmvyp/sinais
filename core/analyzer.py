# analyzer.py

"""
Multi-Timeframe Trading Analyzer - VERSÃO COMPLETA E FINAL
Contém todas as funções necessárias e correções implementadas.
"""
import logging
import time
from typing import Dict, List, Any

from core.data_reader import DataReader, MarketData
from core.signal_writer import EnhancedSignalWriter, EnhancedTradingSignal
from indicators.technical import TechnicalAnalyzer

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

class MultiTimeframeAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_reader = DataReader()
        self.signal_writer = EnhancedSignalWriter()
        self.technical_analyzers = {tf: TechnicalAnalyzer() for tf in settings.get_enabled_timeframes()}
        if PATTERNS_AVAILABLE:
            self.pattern_analyzers = {tf: PatternAnalyzer() for tf in settings.get_enabled_timeframes()}
        
        self.logger.info("MultiTimeframeAnalyzer inicializado com todas as correções.")

    def analyze_symbol_all_timeframes(self, symbol: str) -> Dict[str, Any]:
        """
        Função principal que orquestra a análise completa de um símbolo em múltiplos timeframes.
        """
        self.logger.info(f"Análise multi-timeframe iniciada para: {symbol}")
        enabled_timeframes = settings.get_enabled_timeframes()
        all_signals = []
        coordination_data = {}
        
        market_data_by_tf = {
            tf: self.data_reader.get_latest_data(symbol, tf) for tf in enabled_timeframes
        }

        for timeframe, market_data in market_data_by_tf.items():
            if market_data and market_data.is_sufficient_data:
                tf_result = self._analyze_single_timeframe(symbol, timeframe, market_data)
                all_signals.extend(tf_result.get('signals', []))
                coordination_data[timeframe] = {'trend': self._determine_trend(market_data)}
            else:
                 self.logger.warning(f"Análise para {symbol} em {timeframe} pulada (dados insuficientes ou antigos).")

        validated_signals = self._validate_and_coordinate_signals(all_signals, coordination_data, market_data_by_tf)
        
        signals_saved = 0
        if validated_signals:
            best_signal = max(validated_signals, key=lambda s: s.confidence)
            if self.signal_writer.write_enhanced_signal(best_signal):
                signals_saved += 1
                self.logger.info(f"✅ SINAL SALVO para {symbol}: {best_signal.detector_name} em {best_signal.timeframe}")

        return {'symbol': symbol, 'status': 'success', 'signals_detected': len(all_signals), 'signals_saved': signals_saved}

    def _analyze_single_timeframe(self, symbol: str, timeframe: str, market_data: MarketData) -> Dict[str, Any]:
        """
        Executa todas as análises configuradas para um único timeframe e lida com a criação de sinais.
        """
        tf_config = settings.get_timeframe_config(timeframe)
        signals = []
        
        def create_valid_signal(**kwargs):
            """Função auxiliar para criar sinais de forma segura, capturando erros de validação."""
            try:
                signal = EnhancedTradingSignal(**kwargs)
                signals.append(signal)
            except ValueError as e:
                self.logger.warning(f"Sinal para {symbol} em {timeframe} descartado na criação: {e}")

        if 'technical' in tf_config.enabled_detectors:
            tech_analyzer = self.technical_analyzers[timeframe]
            technical_results = tech_analyzer.analyze_all(market_data, timeframe)
            raw_signals = tech_analyzer.generate_trading_signals(market_data, technical_results, timeframe)
            for s in raw_signals:
                create_valid_signal(**s.__dict__)

        if 'patterns' in tf_config.enabled_detectors and PATTERNS_AVAILABLE:
            pattern_analyzer = self.pattern_analyzers[timeframe]
            pattern_results = pattern_analyzer.analyze_all_patterns(market_data)
            raw_signals = pattern_analyzer.generate_pattern_signals(market_data, pattern_results)
            for s in raw_signals:
                 create_valid_signal(**s.__dict__)

        if 'candlestick' in tf_config.enabled_detectors and CANDLESTICK_AVAILABLE:
            closed_candle_data = market_data.data.iloc[:-1]
            if not closed_candle_data.empty:
                cs_signals_raw = generate_candlestick_signals(closed_candle_data, symbol)
                for cs in cs_signals_raw:
                    create_valid_signal(symbol=symbol, timeframe=timeframe, **cs)
        
        return {'signals': signals}

    def _validate_and_coordinate_signals(self, all_signals: List[EnhancedTradingSignal], coordination_data: Dict, market_data_by_tf: Dict[str, MarketData]) -> List[EnhancedTradingSignal]:
        """Aplica filtros de qualidade finais (tendência, volume) nos sinais gerados."""
        if not all_signals: return []
        
        higher_tf_trend = coordination_data.get('1h', {}).get('trend', 0)
        validated = []
        
        for signal in all_signals:
            is_valid = True
            
            # Filtro de Tendência
            if (higher_tf_trend > 0.1 and 'SELL' in signal.signal_type) or \
               (higher_tf_trend < -0.1 and 'BUY' in signal.signal_type):
                self.logger.info(f"Sinal {signal.detector_name} em {signal.timeframe} filtrado por desalinhamento com tendência de 1h.")
                is_valid = False
            
            # Filtro de Volume
            if is_valid and signal.detector_type == 'candlestick':
                market_data = market_data_by_tf.get(signal.timeframe)
                if market_data and len(market_data.data) > 21:
                    signal_candle = market_data.data.iloc[-2]
                    avg_volume = market_data.data['volume'].iloc[-22:-2].mean()
                    volume_ratio = signal_candle['volume'] / (avg_volume + 1e-10)
                    if volume_ratio < 1.3:
                        self.logger.info(f"Sinal {signal.detector_name} em {signal.timeframe} filtrado por BAIXO VOLUME (Ratio: {volume_ratio:.2f}).")
                        is_valid = False

            if is_valid:
                validated.append(signal)

        return validated

    def _determine_trend(self, market_data: MarketData) -> float:
        """Determina a tendência de curto prazo para fins de filtro."""
        try:
            closes = market_data.data['close_price'].tail(50)
            if len(closes) < 50: return 0.0
            ema_fast = closes.ewm(span=20, adjust=False).mean().iloc[-1]
            ema_slow = closes.ewm(span=50, adjust=False).mean().iloc[-1]
            return 1.0 if ema_fast > ema_slow else -1.0
        except: return 0.0

    def run_continuous_multi_timeframe_analysis(self, base_interval: int = None):
        """Loop principal para execução contínua do analisador."""
        if base_interval is None: base_interval = settings.system.analysis_interval
        symbols_to_analyze = settings.get_analysis_symbols()
        self.logger.info(f"Iniciando análise contínua para {len(symbols_to_analyze)} símbolos.")
        while True:
            try:
                for symbol in symbols_to_analyze:
                    self.analyze_symbol_all_timeframes(symbol) # Esta linha agora funciona
                    time.sleep(1)
            except Exception as e:
                self.logger.error(f"Erro no ciclo de análise contínua: {e}", exc_info=True)
            self.logger.info(f"Ciclo concluído. Aguardando {base_interval} segundos...")
            time.sleep(base_interval)

# Alias para manter compatibilidade com o `main.py`
TradingAnalyzer = MultiTimeframeAnalyzer