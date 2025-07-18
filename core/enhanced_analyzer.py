"""
Enhanced Analyzer - Extensão do sistema existente
Adiciona filtros sem quebrar compatibilidade
"""
import logging
import time
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Imports do sistema existente
from core.analyzer import TradingAnalyzer as OriginalAnalyzer
from core.data_reader import MarketData
from core.signal_writer import TradingSignal
from config.settings import settings

class EnhancedFilters:
    """Filtros avançados para validação de sinais"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_volume(self, market_data: MarketData) -> Tuple[bool, float]:
        """Valida se há volume suficiente"""
        try:
            df = market_data.data
            if len(df) < 20:
                return False, 0.0
            
            recent_volume = df['volume'].tail(5).mean()
            volume_ma = df['volume'].rolling(20, min_periods=10).mean().iloc[-1]
            
            if volume_ma == 0:
                return False, 0.0
            
            volume_ratio = recent_volume / volume_ma
            min_ratio = getattr(settings.indicators, 'min_volume_ratio', 1.5)
            is_valid = volume_ratio >= min_ratio
            
            self.logger.debug(f"Volume: {volume_ratio:.2f}x (min: {min_ratio}x) = {'✅' if is_valid else '❌'}")
            return is_valid, volume_ratio
            
        except Exception as e:
            self.logger.error(f"Erro na validação de volume: {e}")
            return False, 0.0
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcula Average True Range"""
        try:
            high = df['high_price']
            low = df['low_price']
            close = df['close_price'].shift(1)
            
            tr1 = high - low
            tr2 = abs(high - close)
            tr3 = abs(low - close)
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(period, min_periods=1).mean()
            
            return atr.fillna(0)
            
        except Exception:
            return pd.Series([0] * len(df), index=df.index)
    
    def validate_volatility(self, market_data: MarketData) -> Tuple[bool, float]:
        """Valida se volatilidade não está excessiva"""
        try:
            df = market_data.data
            if len(df) < 20:
                return True, 1.0
            
            atr = self.calculate_atr(df, period=14)
            atr_current = atr.iloc[-1]
            atr_ma = atr.rolling(20, min_periods=10).mean().iloc[-1]
            
            if atr_ma == 0:
                return True, 1.0
            
            volatility_ratio = atr_current / atr_ma
            max_ratio = 1.3  # 30% acima da média
            is_valid = volatility_ratio <= max_ratio
            
            self.logger.debug(f"Volatilidade: {volatility_ratio:.2f}x (max: {max_ratio}x) = {'✅' if is_valid else '❌'}")
            return is_valid, volatility_ratio
            
        except Exception as e:
            self.logger.error(f"Erro na validação de volatilidade: {e}")
            return True, 1.0
    
    def get_trend_direction(self, market_data: MarketData) -> Tuple[str, float]:
        """Identifica direção da tendência"""
        try:
            df = market_data.data
            if len(df) < 50:
                return 'sideways', 0.0
            
            ema_fast = df['close_price'].ewm(span=20, min_periods=10).mean()
            ema_slow = df['close_price'].ewm(span=50, min_periods=25).mean()
            
            fast_value = ema_fast.iloc[-1]
            slow_value = ema_slow.iloc[-1]
            
            separation = abs(fast_value - slow_value) / slow_value
            
            if fast_value > slow_value * 1.002:
                return 'bullish', min(separation * 10, 1.0)
            elif fast_value < slow_value * 0.998:
                return 'bearish', min(separation * 10, 1.0)
            else:
                return 'sideways', separation
                
        except Exception:
            return 'sideways', 0.0
    
    def calculate_signal_score(self, market_data: MarketData, technical_signals: List) -> Dict:
        """Calcula score melhorado do sinal"""
        try:
            if not technical_signals:
                return {'total_score': 0.0, 'is_valid': False, 'components': {}}
            
            components = {}
            total_score = 0.0
            
            # 1. Confluência técnica (40%)
            tech_confidence = max(signal.get('confidence', 0) for signal in technical_signals)
            components['technical'] = tech_confidence
            total_score += tech_confidence * 0.40
            
            # 2. Volume (25%)
            volume_valid, volume_ratio = self.validate_volume(market_data)
            min_ratio = getattr(settings.indicators, 'min_volume_ratio', 1.5)
            volume_score = min(1.0, volume_ratio / min_ratio) if volume_valid else 0.0
            components['volume'] = volume_score
            total_score += volume_score * 0.25
            
            # 3. Tendência (20%)
            trend_direction, trend_strength = self.get_trend_direction(market_data)
            signal_type = technical_signals[0].get('signal_type', '')
            
            signal_bullish = 'BUY' in signal_type.upper()
            trend_bullish = trend_direction == 'bullish'
            
            if (signal_bullish and trend_bullish) or (not signal_bullish and not trend_bullish):
                trend_score = 0.5 + trend_strength * 0.5
            elif trend_direction == 'sideways':
                trend_score = 0.5
            else:
                trend_score = 0.2
            
            components['trend'] = trend_score
            total_score += trend_score * 0.20
            
            # 4. Volatilidade (15%)
            volatility_valid, vol_ratio = self.validate_volatility(market_data)
            vol_score = 1.0 if volatility_valid else 0.0
            components['volatility'] = vol_score
            total_score += vol_score * 0.15
            
            # Validação final
            is_valid = (
                total_score >= settings.analysis.confidence_threshold and
                volume_valid and
                volatility_valid
            )
            
            return {
                'total_score': total_score,
                'is_valid': is_valid,
                'components': components,
                'validations': {
                    'volume': {'valid': volume_valid, 'ratio': volume_ratio},
                    'volatility': {'valid': volatility_valid, 'ratio': vol_ratio},
                    'trend': {'direction': trend_direction, 'strength': trend_strength}
                }
            }
            
        except Exception as e:
            self.logger.error(f"Erro no cálculo de score: {e}")
            return {'total_score': 0.0, 'is_valid': False, 'components': {}}

class EnhancedTradingAnalyzer(OriginalAnalyzer):
    """Analyzer melhorado que estende o original"""
    
    def __init__(self):
        super().__init__()
        self.filters = EnhancedFilters()
        self.logger.info("Enhanced Trading Analyzer inicializado")
        
        # Integra patterns se disponível
        try:
            from indicators.patterns import PatternAnalyzer
            self.pattern_analyzer = PatternAnalyzer()
            self.patterns_enabled = True
            self.logger.info("✅ Pattern analyzer integrado")
        except ImportError:
            self.pattern_analyzer = None
            self.patterns_enabled = False
            self.logger.info("ℹ️  Pattern analyzer não disponível")
    
    def analyze_symbol_enhanced(self, symbol: str, timeframe: str = None) -> Dict:
        """Análise melhorada com filtros avançados"""
        if timeframe is None:
            timeframe = settings.analysis.default_timeframe
        
        start_time = time.time()
        self.logger.info(f"🔍 Análise melhorada: {symbol} {timeframe}")
        
        try:
            # 1. Buscar dados (usa método original)
            market_data = self.data_reader.get_latest_data(symbol, timeframe)
            
            if not market_data or not market_data.is_sufficient_data:
                return {
                    'symbol': symbol,
                    'status': 'insufficient_data',
                    'enhanced': True,
                    'message': f'Dados insuficientes: {market_data.data_points if market_data else 0}'
                }
            
            # 2. Análise técnica (usa método original)
            technical_results = self.technical_analyzer.analyze_all(market_data)
            technical_signals = []
            
            for indicator_name, result in technical_results.items():
                technical_signals.extend(result.signals)
            
            # 3. Análise de padrões (se disponível)
            pattern_signals = []
            patterns_found = 0
            if self.patterns_enabled and self.pattern_analyzer:
                try:
                    patterns = self.pattern_analyzer.analyze_all_patterns(market_data)
                    pattern_signals = self.pattern_analyzer.generate_pattern_signals(market_data, patterns)
                    patterns_found = len(patterns)
                    
                    self.logger.debug(f"Padrões {symbol}: {patterns_found} encontrados")
                except Exception as e:
                    self.logger.warning(f"Erro nos padrões {symbol}: {e}")
            
            # 4. Scoring melhorado
            if technical_signals:
                score_results = self.filters.calculate_signal_score(market_data, technical_signals)
            else:
                score_results = {'total_score': 0.0, 'is_valid': False, 'components': {}}
            
            # 5. Decisão de geração de sinal
            final_signals = []
            saved_signals = 0
            
            if score_results['is_valid']:
                # Verifica se já existe sinal ativo
                if not self.signal_writer._has_active_signal_for_symbol(symbol):
                    # Cria melhor sinal
                    best_signal = self._create_enhanced_signal(
                        market_data, technical_signals, score_results
                    )
                    
                    if best_signal:
                        final_signals = [best_signal]
                        saved_signals = self.signal_writer.write_multiple_signals(final_signals)
                else:
                    self.logger.info(f"Symbol {symbol} já possui sinal ativo")
            
            # 6. Resultado final
            execution_time = time.time() - start_time
            
            result = {
                'symbol': symbol,
                'status': 'success',
                'enhanced': True,
                'data_points': market_data.data_points,
                'latest_price': market_data.latest_price,
                
                # Sinais
                'technical_signals': len(technical_signals),
                'pattern_signals': len(pattern_signals),
                'patterns_found': patterns_found,
                'signals_generated': len(final_signals),
                'signals_saved': saved_signals,
                
                # Scoring
                'total_score': score_results['total_score'],
                'score_components': score_results.get('components', {}),
                'is_valid': score_results['is_valid'],
                
                # Validações
                'validations': score_results.get('validations', {}),
                
                # Metadata
                'execution_time': round(execution_time, 3),
                'timestamp': datetime.now(),
                'recommendation': self._get_recommendation(score_results['total_score'])
            }
            
            # Log resultado
            score = result['total_score']
            rec = result['recommendation']
            signals = result['signals_saved']
            
            if signals > 0:
                self.logger.info(f"✅ {symbol}: SINAL | Score: {score:.3f} | {rec}")
            elif score > 0.5:
                self.logger.info(f"⚠️  {symbol}: Score: {score:.3f} | {rec} | Filtrado")
            else:
                self.logger.debug(f"➖ {symbol}: Score baixo: {score:.3f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro na análise melhorada de {symbol}: {e}")
            return {
                'symbol': symbol,
                'status': 'error',
                'enhanced': True,
                'message': str(e),
                'timestamp': datetime.now()
            }
    
    def _create_enhanced_signal(self, market_data: MarketData, technical_signals: List, 
                               score_results: Dict) -> Optional[TradingSignal]:
        """Cria sinal melhorado"""
        try:
            if not technical_signals:
                return None
            
            # Escolhe melhor sinal técnico
            best_signal = max(technical_signals, key=lambda x: x.get('confidence', 0))
            
            # Usa score total como confidence
            enhanced_confidence = min(0.95, score_results['total_score'])
            
            trading_signal = TradingSignal(
                symbol=market_data.symbol,
                signal_type=best_signal['signal_type'],
                entry_price=market_data.latest_price,
                confidence=enhanced_confidence,
                indicators_used=[f"{best_signal.get('indicator', 'technical').lower()}_enhanced"]
            )
            
            return trading_signal
            
        except Exception as e:
            self.logger.error(f"Erro ao criar sinal melhorado: {e}")
            return None
    
    def _get_recommendation(self, score: float) -> str:
        """Converte score em recomendação"""
        if score >= 0.8:
            return "STRONG"
        elif score >= 0.65:
            return "MODERATE"
        elif score >= 0.5:
            return "WEAK"
        else:
            return "REJECT"
    
    # Métodos de compatibilidade
    def analyze_symbol(self, symbol: str, timeframe: str = None) -> Dict:
        """Compatibilidade - usa método melhorado"""
        return self.analyze_symbol_enhanced(symbol, timeframe)
    
    def analyze_multiple_symbols(self, symbols: List[str] = None, 
                                timeframe: str = None) -> Dict[str, Dict]:
        """Análise múltipla melhorada"""
        if symbols is None:
            symbols = settings.get_analysis_symbols()
        
        results = {}
        available_symbols = self.data_reader.get_available_symbols()
        valid_symbols = [s for s in symbols if s in available_symbols]
        
        self.logger.info(f"🚀 Análise melhorada de {len(valid_symbols)} symbols")
        
        for symbol in valid_symbols:
            results[symbol] = self.analyze_symbol_enhanced(symbol, timeframe)
        
        return results

# Função para criar analyzer melhorado
def create_enhanced_analyzer():
    """Cria analyzer melhorado"""
    return EnhancedTradingAnalyzer()
