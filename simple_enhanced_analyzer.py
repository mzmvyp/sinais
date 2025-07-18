"""
Enhanced Analyzer - Versão Standalone
Funciona independente de importações complexas
"""
import logging
import time
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class SimpleEnhancedAnalyzer:
    """Analyzer melhorado simplificado"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Configurações hardcoded para evitar problemas de import
        self.config = {
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'confidence_threshold': 0.65,
            'min_volume_ratio': 1.5,
            'max_volatility_ratio': 1.3
        }
        
        self.logger.info("Simple Enhanced Analyzer inicializado")
    
    def validate_volume(self, df: pd.DataFrame) -> Tuple[bool, float]:
        """Valida volume"""
        try:
            if len(df) < 20:
                return False, 0.0
            
            recent_volume = df['volume'].tail(5).mean()
            volume_ma = df['volume'].rolling(20, min_periods=10).mean().iloc[-1]
            
            if volume_ma == 0:
                return False, 0.0
            
            volume_ratio = recent_volume / volume_ma
            is_valid = volume_ratio >= self.config['min_volume_ratio']
            
            return is_valid, volume_ratio
            
        except Exception:
            return False, 0.0
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcula ATR"""
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
    
    def validate_volatility(self, df: pd.DataFrame) -> Tuple[bool, float]:
        """Valida volatilidade"""
        try:
            if len(df) < 20:
                return True, 1.0
            
            atr = self.calculate_atr(df, period=14)
            atr_current = atr.iloc[-1]
            atr_ma = atr.rolling(20, min_periods=10).mean().iloc[-1]
            
            if atr_ma == 0:
                return True, 1.0
            
            volatility_ratio = atr_current / atr_ma
            is_valid = volatility_ratio <= self.config['max_volatility_ratio']
            
            return is_valid, volatility_ratio
            
        except Exception:
            return True, 1.0
    
    def get_trend_direction(self, df: pd.DataFrame) -> str:
        """Identifica tendência"""
        try:
            if len(df) < 50:
                return 'sideways'
            
            ema_fast = df['close_price'].ewm(span=20, min_periods=10).mean()
            ema_slow = df['close_price'].ewm(span=50, min_periods=25).mean()
            
            fast_value = ema_fast.iloc[-1]
            slow_value = ema_slow.iloc[-1]
            
            if fast_value > slow_value * 1.002:
                return 'bullish'
            elif fast_value < slow_value * 0.998:
                return 'bearish'
            else:
                return 'sideways'
                
        except Exception:
            return 'sideways'
    
    def calculate_enhanced_score(self, df: pd.DataFrame, rsi_value: float, 
                                signal_type: str) -> Dict:
        """Calcula score melhorado"""
        try:
            components = {}
            total_score = 0.0
            
            # 1. RSI Score (40%)
            if signal_type == 'BUY':
                if rsi_value <= self.config['rsi_oversold']:
                    rsi_score = 1.0
                elif rsi_value <= 50:
                    rsi_score = 0.8
                else:
                    rsi_score = 0.3
            else:  # SELL
                if rsi_value >= self.config['rsi_overbought']:
                    rsi_score = 1.0
                elif rsi_value >= 50:
                    rsi_score = 0.8
                else:
                    rsi_score = 0.3
            
            components['rsi'] = rsi_score
            total_score += rsi_score * 0.40
            
            # 2. Volume Score (25%)
            volume_valid, volume_ratio = self.validate_volume(df)
            volume_score = min(1.0, volume_ratio / self.config['min_volume_ratio']) if volume_valid else 0.0
            components['volume'] = volume_score
            total_score += volume_score * 0.25
            
            # 3. Trend Score (20%)
            trend = self.get_trend_direction(df)
            signal_bullish = signal_type == 'BUY'
            
            if (signal_bullish and trend == 'bullish') or (not signal_bullish and trend == 'bearish'):
                trend_score = 0.8
            elif trend == 'sideways':
                trend_score = 0.5
            else:
                trend_score = 0.2
            
            components['trend'] = trend_score
            total_score += trend_score * 0.20
            
            # 4. Volatility Score (15%)
            volatility_valid, vol_ratio = self.validate_volatility(df)
            vol_score = 1.0 if volatility_valid else 0.0
            components['volatility'] = vol_score
            total_score += vol_score * 0.15
            
            # Determina se é válido
            is_valid = (
                total_score >= self.config['confidence_threshold'] and
                volume_valid and
                volatility_valid
            )
            
            # Recomendação
            if total_score >= 0.8:
                recommendation = "STRONG"
            elif total_score >= 0.65:
                recommendation = "MODERATE"
            elif total_score >= 0.5:
                recommendation = "WEAK"
            else:
                recommendation = "REJECT"
            
            return {
                'total_score': total_score,
                'is_valid': is_valid,
                'recommendation': recommendation,
                'components': components,
                'validations': {
                    'volume': {'valid': volume_valid, 'ratio': volume_ratio},
                    'volatility': {'valid': volatility_valid, 'ratio': vol_ratio},
                    'trend': trend
                }
            }
            
        except Exception as e:
            self.logger.error(f"Erro no score: {e}")
            return {
                'total_score': 0.0,
                'is_valid': False,
                'recommendation': 'ERROR',
                'components': {}
            }
    
    def get_recommendation(self, score: float) -> str:
        """Converte score em recomendação"""
        if score >= 0.8:
            return "STRONG"
        elif score >= 0.65:
            return "MODERATE"
        elif score >= 0.5:
            return "WEAK"
        else:
            return "REJECT"
    
    def analyze_dataframe(self, df: pd.DataFrame, symbol: str = "TEST") -> Dict:
        """Analisa DataFrame diretamente"""
        try:
            if len(df) < 20:
                return {
                    'symbol': symbol,
                    'status': 'insufficient_data',
                    'message': f'Apenas {len(df)} períodos disponíveis'
                }
            
            # Calcula RSI simples
            delta = df['close_price'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
            loss = loss.replace(0, 0.0001)
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # Determina tipo de sinal baseado no RSI
            if current_rsi <= self.config['rsi_oversold']:
                signal_type = 'BUY'
                base_confidence = 0.8
            elif current_rsi >= self.config['rsi_overbought']:
                signal_type = 'SELL'
                base_confidence = 0.8
            elif current_rsi < 50:
                signal_type = 'BUY'
                base_confidence = 0.6
            else:
                signal_type = 'SELL'
                base_confidence = 0.6
            
            # Calcula score melhorado
            score_result = self.calculate_enhanced_score(df, current_rsi, signal_type)
            
            result = {
                'symbol': symbol,
                'status': 'success',
                'enhanced': True,
                'latest_price': df['close_price'].iloc[-1],
                'rsi_value': current_rsi,
                'signal_type': signal_type,
                'base_confidence': base_confidence,
                'total_score': score_result['total_score'],
                'is_valid': score_result['is_valid'],
                'recommendation': score_result['recommendation'],
                'components': score_result['components'],
                'validations': score_result['validations'],
                'timestamp': datetime.now()
            }
            
            # Log resultado
            score = result['total_score']
            rec = result['recommendation']
            
            if score >= 0.65:
                self.logger.info(f"✅ {symbol}: Score {score:.3f} | {rec} | RSI {current_rsi:.1f}")
            else:
                self.logger.info(f"⚠️  {symbol}: Score {score:.3f} | {rec} | Filtrado")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro na análise: {e}")
            return {
                'symbol': symbol,
                'status': 'error',
                'message': str(e),
                'enhanced': True
            }

def create_simple_test():
    """Cria teste simples com dados sintéticos"""
    
    # Gera dados sintéticos para teste
    periods = 100
    dates = pd.date_range(start='2024-01-01', periods=periods, freq='5min')
    
    # Preços com tendência e ruído
    base_price = 50000
    trend = np.linspace(0, 1000, periods)
    noise = np.random.normal(0, 200, periods)
    close_prices = base_price + trend + noise
    
    # OHLC
    opens = close_prices + np.random.normal(0, 50, periods)
    highs = np.maximum(opens, close_prices) + np.abs(np.random.normal(0, 100, periods))
    lows = np.minimum(opens, close_prices) - np.abs(np.random.normal(0, 100, periods))
    
    # Volume
    volumes = np.abs(np.random.normal(1000000, 200000, periods))
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open_price': opens,
        'high_price': highs,
        'low_price': lows,
        'close_price': close_prices,
        'volume': volumes
    })
    
    return df

def test_simple_analyzer():
    """Testa analyzer simples"""
    print("🧪 TESTANDO ANALYZER SIMPLES")
    print("=" * 40)
    
    # Cria analyzer
    analyzer = SimpleEnhancedAnalyzer()
    
    # Gera dados de teste
    test_data = create_simple_test()
    print(f"📊 Dados sintéticos: {len(test_data)} períodos")
    
    # Executa análise
    result = analyzer.analyze_dataframe(test_data, "TEST_BTC")
    
    print(f"
📈 RESULTADO:")
    print(f"   Status: {result.get('status')}")
    print(f"   RSI: {result.get('rsi_value', 0):.1f}")
    print(f"   Signal: {result.get('signal_type')}")
    print(f"   Score: {result.get('total_score', 0):.3f}")
    print(f"   Recomendação: {result.get('recommendation')}")
    print(f"   Válido: {result.get('is_valid')}")
    
    if 'components' in result:
        print(f"
🧩 COMPONENTES:")
        for comp, score in result['components'].items():
            print(f"   {comp.upper()}: {score:.3f}")
    
    if 'validations' in result:
        print(f"
✅ VALIDAÇÕES:")
        validations = result['validations']
        
        if 'volume' in validations:
            vol_data = validations['volume']
            status = "✅" if vol_data['valid'] else "❌"
            print(f"   {status} Volume: {vol_data.get('ratio', 0):.2f}x")
        
        if 'volatility' in validations:
            vol_data = validations['volatility']
            status = "✅" if vol_data['valid'] else "❌"
            print(f"   {status} Volatilidade: {vol_data.get('ratio', 0):.2f}x")
        
        if 'trend' in validations:
            trend = validations['trend']
            print(f"   📈 Tendência: {trend}")
    
    return result

if __name__ == "__main__":
    test_simple_analyzer()
