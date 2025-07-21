# No arquivo analyzer.py

# Substitua as importações no topo do arquivo para incluir o que faltava
import logging
import time
from typing import Dict, List, Any, Tuple # _#_CORRIGIDO_: Adicionado 'Tuple'

from core.data_reader import DataReader, MarketData
from core.signal_writer import EnhancedSignalWriter, EnhancedTradingSignal
# _#_CORRIGIDO_: Importa RSIAnalyzer diretamente para que possa ser usado
from indicators.technical import TechnicalAnalyzer, RSIAnalyzer 

# (O resto das importações permanece o mesmo)
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


# Agora, substitua a classe MultiTimeframeAnalyzer inteira por este código:
class MultiTimeframeAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_reader = DataReader()
        self.signal_writer = EnhancedSignalWriter()
        self.technical_analyzers = {tf: TechnicalAnalyzer() for tf in settings.get_enabled_timeframes()}
        if PATTERNS_AVAILABLE:
            self.pattern_analyzers = {tf: PatternAnalyzer() for tf in settings.get_enabled_timeframes()}

        self.logger.info("MultiTimeframeAnalyzer inicializado com Validação de Microestrutura (Sniper).")

    def analyze_symbol_all_timeframes(self, symbol: str) -> Dict[str, Any]:
        self.logger.info(f"Análise sniper iniciada para: {symbol}")
        enabled_timeframes = settings.get_enabled_timeframes()
        all_signals = []

        market_data_by_tf = {
            tf: self.data_reader.get_latest_data(symbol, tf) for tf in enabled_timeframes
        }

        for timeframe, market_data in market_data_by_tf.items():
            if market_data and market_data.is_sufficient_data:
                tf_result = self._analyze_single_timeframe(symbol, timeframe, market_data)
                all_signals.extend(tf_result.get('signals', []))
            else:
                self.logger.warning(f"Análise para {symbol} em {timeframe} pulada (dados insuficientes ou antigos).")

        validated_signals = self._validate_and_filter_signals(all_signals, market_data_by_tf)

        signals_saved = 0
        if validated_signals:
            validated_signals.sort(key=lambda s: s.confidence, reverse=True)
            for signal in validated_signals[:settings.system.max_total_signals_per_symbol]:
                if self.signal_writer.write_enhanced_signal(signal):
                    signals_saved += 1
                    self.logger.info(f"🎯 SNIPER HIT: Sinal para {symbol} validado e salvo! Detector: {signal.detector_name} em {signal.timeframe}")

        return {'symbol': symbol, 'status': 'success', 'signals_detected': len(all_signals), 'signals_validated': len(validated_signals), 'signals_saved': signals_saved}

    def _analyze_single_timeframe(self, symbol: str, timeframe: str, market_data: MarketData) -> Dict[str, Any]:
        tf_config = settings.get_timeframe_config(timeframe)
        signals = []

        if len(market_data.data) < 2:
            return {'signals': []}
            
        closed_candle = market_data.data.iloc[-2]
        entry_price = float(closed_candle['close_price'])
        signal_timestamp = closed_candle['timestamp'].to_pydatetime()

        def create_valid_signal(**kwargs):
            try:
                base_args = {'symbol': symbol, 'timeframe': timeframe, 'entry_price': entry_price, 'timestamp': signal_timestamp}
                final_args = {**kwargs, **base_args}
                allowed_keys = EnhancedTradingSignal.__annotations__.keys()
                filtered_args = {k: v for k, v in final_args.items() if k in allowed_keys}
                
                signal = EnhancedTradingSignal(**filtered_args)
                signals.append(signal)
            except (ValueError, TypeError) as e:
                self.logger.warning(f"Sinal para {symbol} em {timeframe} descartado na criação: {e}")

        if 'technical' in tf_config.enabled_detectors:
            tech_analyzer = self.technical_analyzers[timeframe]
            technical_results = tech_analyzer.analyze_all(market_data, timeframe)
            raw_signals = tech_analyzer.generate_trading_signals(market_data, technical_results, timeframe)
            for s in raw_signals:
                create_valid_signal(**s.__dict__)

        if 'candlestick' in tf_config.enabled_detectors and CANDLESTICK_AVAILABLE:
            df_for_cs = market_data.data.iloc[:-1]
            if not df_for_cs.empty:
                cs_signals_raw = generate_candlestick_signals(df_for_cs, symbol)
                for cs in cs_signals_raw:
                    create_valid_signal(**cs)

        if 'patterns' in tf_config.enabled_detectors and PATTERNS_AVAILABLE:
            pattern_analyzer = self.pattern_analyzers[timeframe]
            pattern_results = pattern_analyzer.analyze_all_patterns(market_data)
            raw_signals = pattern_analyzer.generate_pattern_signals(market_data, pattern_results)
            for s in raw_signals:
                 create_valid_signal(**s.__dict__)

        return {'signals': signals}

    def _validate_and_filter_signals(self, signals: List[EnhancedTradingSignal], market_data_by_tf: Dict) -> List[EnhancedTradingSignal]:
        if not signals:
            return []

        validated_signals = []
        for signal in signals:
            is_valid = True
            validation_notes = []

            if settings.validation.enabled:
                is_micro_valid, note = self._validate_with_microstructure(signal)
                if not is_micro_valid:
                    is_valid = False
                validation_notes.append(note)

            if is_valid:
                is_volume_valid, note = self._validate_with_volume(signal, market_data_by_tf)
                if not is_volume_valid:
                    is_valid = False
                validation_notes.append(note)

            if is_valid:
                self.logger.info(f"Sinal {signal.id} para {signal.symbol} passou em todas as validações.")
                signal.market_conditions['validation_notes'] = validation_notes
                validated_signals.append(signal)
            else:
                self.logger.info(f"Sinal {signal.id} para {signal.symbol} REPROVADO. Motivos: {'; '.join(validation_notes)}")
        return validated_signals

    def _validate_with_microstructure(self, signal: EnhancedTradingSignal) -> Tuple[bool, str]:
        conf = settings.validation
        micro_df = self.data_reader.get_microstructure_for_validation(
            signal.symbol,
            signal.timestamp,
            conf.validation_window_minutes
        )

        if micro_df is None or micro_df.empty:
            return False, "Microstructure data not found for validation window"

        rsi_analyzer = RSIAnalyzer()
        micro_rsi = rsi_analyzer.calculate_rsi(micro_df['close_price'])

        if micro_rsi.empty:
            return False, "Could not calculate microstructure momentum (RSI)"

        if 'BUY' in signal.signal_type:
            if (micro_rsi > conf.buy_momentum_threshold).any():
                return True, f"Micro-momentum confirmed BUY (RSI > {conf.buy_momentum_threshold})"
            return False, f"Micro-momentum FAILED BUY (Max RSI was {micro_rsi.max():.2f})"
        elif 'SELL' in signal.signal_type:
            if (micro_rsi < conf.sell_momentum_threshold).any():
                return True, f"Micro-momentum confirmed SELL (RSI < {conf.sell_momentum_threshold})"
            return False, f"Micro-momentum FAILED SELL (Min RSI was {micro_rsi.min():.2f})"
        return False, "Signal type not BUY or SELL"

    def _validate_with_volume(self, signal: EnhancedTradingSignal, market_data_by_tf: Dict) -> Tuple[bool, str]:
        market_data = market_data_by_tf.get(signal.timeframe)
        if not market_data or len(market_data.data) < 22:
            return True, "Volume validation skipped (insufficient data)"

        volume_ma_period = settings.indicators.volume_ma_period
        signal_candle_index = -2
        
        avg_volume = market_data.data['volume'].iloc[signal_candle_index - volume_ma_period : signal_candle_index].mean()
        signal_candle_volume = market_data.data['volume'].iloc[signal_candle_index]

        if avg_volume == 0:
            return True, "Volume validation skipped (avg volume is zero)"

        volume_ratio = signal_candle_volume / avg_volume
        min_ratio = settings.get_timeframe_config(signal.timeframe).volume_threshold_multiplier

        if volume_ratio >= min_ratio:
            return True, f"Volume confirmed (Ratio: {volume_ratio:.2f} >= {min_ratio})"
        return False, f"Volume FAILED (Ratio: {volume_ratio:.2f} < {min_ratio})"

    def run_continuous_multi_timeframe_analysis(self, base_interval: int = None):
        if base_interval is None: base_interval = settings.system.analysis_interval
        symbols_to_analyze = settings.get_analysis_symbols()
        self.logger.info(f"Iniciando análise contínua para {len(symbols_to_analyze)} símbolos com lógica SNIPER.")
        while True:
            try:
                for symbol in symbols_to_analyze:
                    self.analyze_symbol_all_timeframes(symbol)
                    time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("Análise contínua interrompida pelo usuário.")
                break
            except Exception as e:
                self.logger.error(f"Erro no ciclo de análise contínua: {e}", exc_info=True)
            self.logger.info(f"Ciclo concluído. Aguardando {base_interval} segundos...")
            time.sleep(base_interval)

# Alias para manter compatibilidade com o `main.py`
TradingAnalyzer = MultiTimeframeAnalyzer
# Alias para manter compatibilidade com o `main.py`
TradingAnalyzer = MultiTimeframeAnalyzer