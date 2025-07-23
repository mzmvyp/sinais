# technical_stop_loss.py - SISTEMA INTELIGENTE DE STOP LOSS

"""
Sistema Inteligente de Stop Loss baseado em Análise Técnica
Considera ATR, Suporte/Resistência, Volatilidade e Estrutura de Mercado
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass

from core.data_reader import MarketData
from config.settings import settings

@dataclass
class StopLossAnalysis:
    """Resultado da análise de stop loss"""
    recommended_stop: float
    confidence: float
    method_used: str
    analysis_details: Dict
    risk_percentage: float
    atr_value: float
    nearest_support_resistance: Optional[float] = None

class TechnicalStopLossCalculator:
    """Calculadora inteligente de stop loss baseada em análise técnica"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 🚨 NOVO: Usa configurações avançadas se disponíveis
        try:
            from config.stop_loss_config import stop_loss_config, get_stop_config_for_symbol
            self.advanced_config = stop_loss_config
            self.get_config_func = get_stop_config_for_symbol
            self.use_advanced_config = True
            self.logger.info("🔧 Stop Loss Inteligente usando configurações avançadas")
        except ImportError:
            self.use_advanced_config = False
            self.logger.warning("⚠️ Configurações avançadas não disponíveis, usando configuração básica")
            
            # Configurações básicas como fallback
            self.config = {
                '5m': {
                    'atr_period': 14,
                    'atr_multiplier': 1.5,
                    'max_risk_pct': 2.0,
                    'min_risk_pct': 0.8,
                    'support_resistance_lookback': 20,
                    'swing_lookback': 10
                },
                '15m': {
                    'atr_period': 14,
                    'atr_multiplier': 2.0,
                    'max_risk_pct': 3.0,
                    'min_risk_pct': 1.0,
                    'support_resistance_lookback': 30,
                    'swing_lookback': 15
                },
                '1h': {
                    'atr_period': 14,
                    'atr_multiplier': 2.5,
                    'max_risk_pct': 4.0,
                    'min_risk_pct': 1.5,
                    'support_resistance_lookback': 50,
                    'swing_lookback': 20
                }
            }
    
    def calculate_intelligent_stop_loss(self, market_data: MarketData, signal_type: str, 
                                       entry_price: float, timeframe: str) -> StopLossAnalysis:
        """
        🧠 FUNÇÃO PRINCIPAL: Calcula stop loss inteligente COM CONFIGURAÇÕES AVANÇADAS
        """
        try:
            # 🚨 NOVO: Obtém configuração personalizada para o symbol
            if self.use_advanced_config:
                config = self.get_config_func(market_data.symbol, timeframe)
                self.logger.debug(f"🔧 Usando config avançada para {market_data.symbol} {timeframe}")
            else:
                config = self.config.get(timeframe, self.config['15m'])
            
            df = market_data.data.copy()
            
            if len(df) < config['atr_period'] + 5:
                # Fallback para dados insuficientes
                return self._fallback_stop_loss(entry_price, signal_type, timeframe, market_data.symbol)
            
            # 1. CALCULA ATR (Average True Range)
            atr_value = self._calculate_atr(df, config['atr_period'])
            
            # 2. IDENTIFICA SUPORTE E RESISTÊNCIA
            support_resistance = self._find_support_resistance_levels(
                df, config['support_resistance_lookback']
            )
            
            # 3. IDENTIFICA SWING HIGHS/LOWS
            swing_levels = self._find_swing_levels(df, config['swing_lookback'])
            
            # 4. CALCULA VOLATILIDADE RECENTE
            volatility_factor = self._calculate_volatility_factor(df)
            
            # 5. ESCOLHE MÉTODO MAIS APROPRIADO
            stop_analysis = self._determine_best_stop_method(
                df, signal_type, entry_price, atr_value, 
                support_resistance, swing_levels, volatility_factor, config, market_data.symbol
            )
            
            # 6. VALIDAÇÃO FINAL
            validated_stop = self._validate_stop_loss(
                stop_analysis, entry_price, signal_type, config
            )
            
            self.logger.debug(
                f"Stop Loss Inteligente: {market_data.symbol} {timeframe} | "
                f"Método: {validated_stop.method_used} | "
                f"Entry: {entry_price:.4f} | Stop: {validated_stop.recommended_stop:.4f} | "
                f"Risco: {validated_stop.risk_percentage:.2f}%"
            )
            
            return validated_stop
            
        except Exception as e:
            self.logger.error(f"Erro no cálculo de stop loss inteligente: {e}")
            return self._fallback_stop_loss(entry_price, signal_type, timeframe, market_data.symbol)
    
    def _calculate_atr(self, df: pd.DataFrame, period: int) -> float:
        """Calcula Average True Range (ATR)"""
        try:
            high = df['high_price']
            low = df['low_price']
            close = df['close_price']
            
            # True Range
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.rolling(window=period).mean().iloc[-1]
            
            return atr if pd.notna(atr) and atr > 0 else df['close_price'].iloc[-1] * 0.02
            
        except Exception as e:
            self.logger.warning(f"Erro no cálculo de ATR: {e}")
            return df['close_price'].iloc[-1] * 0.02
    
    def _find_support_resistance_levels(self, df: pd.DataFrame, lookback: int) -> Dict[str, List[float]]:
        """Identifica níveis de suporte e resistência"""
        try:
            recent_data = df.tail(lookback)
            
            # Identifica picos (resistência) e vales (suporte)
            highs = recent_data['high_price']
            lows = recent_data['low_price']
            
            # Encontra máximos locais (resistência)
            resistance_levels = []
            for i in range(2, len(highs) - 2):
                if (highs.iloc[i] > highs.iloc[i-1] and highs.iloc[i] > highs.iloc[i-2] and
                    highs.iloc[i] > highs.iloc[i+1] and highs.iloc[i] > highs.iloc[i+2]):
                    resistance_levels.append(highs.iloc[i])
            
            # Encontra mínimos locais (suporte)
            support_levels = []
            for i in range(2, len(lows) - 2):
                if (lows.iloc[i] < lows.iloc[i-1] and lows.iloc[i] < lows.iloc[i-2] and
                    lows.iloc[i] < lows.iloc[i+1] and lows.iloc[i] < lows.iloc[i+2]):
                    support_levels.append(lows.iloc[i])
            
            return {
                'resistance': sorted(resistance_levels, reverse=True)[:5],  # Top 5
                'support': sorted(support_levels)[-5:]  # Bottom 5
            }
            
        except Exception as e:
            self.logger.warning(f"Erro na identificação de S/R: {e}")
            return {'resistance': [], 'support': []}
    
    def _find_swing_levels(self, df: pd.DataFrame, lookback: int) -> Dict[str, float]:
        """Encontra swing highs e swing lows recentes"""
        try:
            recent_data = df.tail(lookback)
            
            swing_high = recent_data['high_price'].max()
            swing_low = recent_data['low_price'].min()
            
            # Encontra o swing high/low mais significativo
            range_size = swing_high - swing_low
            
            return {
                'swing_high': swing_high,
                'swing_low': swing_low,
                'range_size': range_size
            }
            
        except Exception as e:
            self.logger.warning(f"Erro na identificação de swings: {e}")
            current_price = df['close_price'].iloc[-1]
            return {
                'swing_high': current_price * 1.02,
                'swing_low': current_price * 0.98,
                'range_size': current_price * 0.04
            }
    
    def _calculate_volatility_factor(self, df: pd.DataFrame) -> float:
        """Calcula fator de volatilidade recente"""
        try:
            # Calcula volatilidade baseada no retorno dos últimos 20 períodos
            returns = df['close_price'].pct_change().tail(20)
            volatility = returns.std()
            
            # Normaliza a volatilidade
            if pd.isna(volatility) or volatility == 0:
                return 1.0
            
            # Fator de 0.5 (baixa vol) a 2.0 (alta vol)
            normalized_vol = min(2.0, max(0.5, volatility * 100))
            return normalized_vol
            
        except Exception as e:
            self.logger.warning(f"Erro no cálculo de volatilidade: {e}")
            return 1.0
    
    def _determine_best_stop_method(self, df: pd.DataFrame, signal_type: str, entry_price: float,
                                   atr_value: float, support_resistance: Dict, swing_levels: Dict,
                                   volatility_factor: float, config: Dict, symbol: str = None) -> StopLossAnalysis:
        """
        🎯 ESCOLHE O MELHOR MÉTODO DE STOP LOSS COM CONFIGURAÇÕES AVANÇADAS
        """
        methods = []
        
        # MÉTODO 1: ATR-based Stop
        atr_stop = self._calculate_atr_stop(
            entry_price, atr_value, signal_type, config, volatility_factor
        )
        methods.append(atr_stop)
        
        # MÉTODO 2: Support/Resistance Stop
        if support_resistance['support'] or support_resistance['resistance']:
            sr_stop = self._calculate_support_resistance_stop(
                entry_price, signal_type, support_resistance
            )
            if sr_stop:
                methods.append(sr_stop)
        
        # MÉTODO 3: Swing-based Stop
        swing_stop = self._calculate_swing_stop(
            entry_price, signal_type, swing_levels, config
        )
        methods.append(swing_stop)
        
        # MÉTODO 4: Structure-based Stop (baseado na estrutura de mercado)
        structure_stop = self._calculate_structure_stop(
            df, entry_price, signal_type, config
        )
        methods.append(structure_stop)
        
        # ESCOLHE O MELHOR MÉTODO COM CONFIGURAÇÕES AVANÇADAS
        if self.use_advanced_config and symbol:
            best_method = self._select_best_method_advanced(methods, entry_price, signal_type, symbol, config)
        else:
            best_method = self._select_best_method(methods, entry_price, signal_type)
        
        return best_method
    
    def _select_best_method_advanced(self, methods: List[StopLossAnalysis], entry_price: float,
                                   signal_type: str, symbol: str, config: Dict) -> StopLossAnalysis:
        """🚨 NOVO: Seleção avançada com configurações personalizadas"""
        
        # Remove métodos com risco excessivo ou muito baixo
        valid_methods = []
        for method in methods:
            if config['min_risk_pct'] <= method.risk_percentage <= config['max_risk_pct']:
                valid_methods.append(method)
        
        if not valid_methods:
            # Se todos são inválidos, usa o ATR como fallback
            return methods[0]  # Primeiro sempre é ATR
        
        # 🚨 NOVO: Usa prioridades das configurações avançadas
        for method in valid_methods:
            # Adiciona prioridade baseada nas configurações
            priority = self.advanced_config.get_method_priority(method.method_used, symbol, config.get('timeframe', '15m'))
            method.analysis_details['config_priority'] = priority
            
            # Bonus para métodos preferidos
            if self.advanced_config.is_method_preferred(method.method_used, symbol, config.get('timeframe', '15m')):
                method.confidence += 0.1  # Bonus de confiança
                method.analysis_details['preferred_method'] = True
        
        # Ordena por prioridade de configuração + confiança
        def sort_key(m):
            priority = m.analysis_details.get('config_priority', 0)
            confidence = m.confidence
            return (priority, confidence)
        
        valid_methods.sort(key=sort_key, reverse=True)
        best_method = valid_methods[0]
        
        self.logger.debug(f"🔧 Método selecionado com config avançada: {best_method.method_used} (Prioridade: {best_method.analysis_details.get('config_priority', 0)})")
        
        return best_method
    
    def _calculate_atr_stop(self, entry_price: float, atr_value: float, signal_type: str,
                           config: Dict, volatility_factor: float) -> StopLossAnalysis:
        """Stop loss baseado em ATR"""
        # Ajusta multiplicador pela volatilidade
        adjusted_multiplier = config['atr_multiplier'] * volatility_factor
        
        if 'BUY' in signal_type:
            stop_price = entry_price - (atr_value * adjusted_multiplier)
        else:  # SELL/SHORT
            stop_price = entry_price + (atr_value * adjusted_multiplier)
        
        risk_pct = abs(entry_price - stop_price) / entry_price * 100
        
        return StopLossAnalysis(
            recommended_stop=stop_price,
            confidence=0.7,
            method_used="ATR_Dynamic",
            analysis_details={
                'atr_value': atr_value,
                'multiplier_used': adjusted_multiplier,
                'volatility_factor': volatility_factor
            },
            risk_percentage=risk_pct,
            atr_value=atr_value
        )
    
    def _calculate_support_resistance_stop(self, entry_price: float, signal_type: str,
                                          support_resistance: Dict) -> Optional[StopLossAnalysis]:
        """Stop loss baseado em suporte/resistência"""
        try:
            if 'BUY' in signal_type and support_resistance['support']:
                # Para BUY, usa suporte mais próximo abaixo do entry
                relevant_supports = [s for s in support_resistance['support'] if s < entry_price]
                if relevant_supports:
                    nearest_support = max(relevant_supports)
                    # Stop um pouco abaixo do suporte
                    stop_price = nearest_support * 0.998
                    
                    risk_pct = abs(entry_price - stop_price) / entry_price * 100
                    
                    return StopLossAnalysis(
                        recommended_stop=stop_price,
                        confidence=0.9,  # Alta confiança em S/R
                        method_used="Support_Level",
                        analysis_details={
                            'nearest_support': nearest_support,
                            'buffer_pct': 0.2
                        },
                        risk_percentage=risk_pct,
                        atr_value=0,
                        nearest_support_resistance=nearest_support
                    )
            
            elif 'SELL' in signal_type and support_resistance['resistance']:
                # Para SELL, usa resistência mais próxima acima do entry
                relevant_resistance = [r for r in support_resistance['resistance'] if r > entry_price]
                if relevant_resistance:
                    nearest_resistance = min(relevant_resistance)
                    # Stop um pouco acima da resistência
                    stop_price = nearest_resistance * 1.002
                    
                    risk_pct = abs(stop_price - entry_price) / entry_price * 100
                    
                    return StopLossAnalysis(
                        recommended_stop=stop_price,
                        confidence=0.9,
                        method_used="Resistance_Level",
                        analysis_details={
                            'nearest_resistance': nearest_resistance,
                            'buffer_pct': 0.2
                        },
                        risk_percentage=risk_pct,
                        atr_value=0,
                        nearest_support_resistance=nearest_resistance
                    )
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Erro no cálculo S/R stop: {e}")
            return None
    
    def _calculate_swing_stop(self, entry_price: float, signal_type: str,
                             swing_levels: Dict, config: Dict) -> StopLossAnalysis:
        """Stop loss baseado em swing highs/lows"""
        if 'BUY' in signal_type:
            # Para BUY, stop abaixo do swing low recente
            buffer = swing_levels['range_size'] * 0.1  # 10% do range como buffer
            stop_price = swing_levels['swing_low'] - buffer
        else:  # SELL/SHORT
            # Para SELL, stop acima do swing high recente
            buffer = swing_levels['range_size'] * 0.1
            stop_price = swing_levels['swing_high'] + buffer
        
        risk_pct = abs(entry_price - stop_price) / entry_price * 100
        
        return StopLossAnalysis(
            recommended_stop=stop_price,
            confidence=0.8,
            method_used="Swing_Level",
            analysis_details={
                'swing_high': swing_levels['swing_high'],
                'swing_low': swing_levels['swing_low'],
                'buffer_used': buffer
            },
            risk_percentage=risk_pct,
            atr_value=0
        )
    
    def _calculate_structure_stop(self, df: pd.DataFrame, entry_price: float,
                                 signal_type: str, config: Dict) -> StopLossAnalysis:
        """Stop loss baseado na estrutura de mercado"""
        try:
            # Analisa a tendência recente
            lookback = min(config['swing_lookback'], len(df) - 1)
            recent_data = df.tail(lookback)
            
            # Calcula EMA rápida para estrutura
            ema_fast = recent_data['close_price'].ewm(span=5).mean().iloc[-1]
            
            # Encontra a estrutura mais próxima
            if 'BUY' in signal_type:
                # Para BUY, procura último low significativo
                recent_lows = recent_data['low_price']
                structure_level = recent_lows.min()
                # Stop abaixo da estrutura
                stop_price = structure_level * 0.995
            else:  # SELL/SHORT
                # Para SELL, procura último high significativo
                recent_highs = recent_data['high_price']
                structure_level = recent_highs.max()
                # Stop acima da estrutura
                stop_price = structure_level * 1.005
            
            risk_pct = abs(entry_price - stop_price) / entry_price * 100
            
            return StopLossAnalysis(
                recommended_stop=stop_price,
                confidence=0.75,
                method_used="Market_Structure",
                analysis_details={
                    'structure_level': structure_level,
                    'ema_fast': ema_fast,
                    'lookback_periods': lookback
                },
                risk_percentage=risk_pct,
                atr_value=0
            )
            
        except Exception as e:
            self.logger.warning(f"Erro no cálculo structure stop: {e}")
            # Fallback simples
            if 'BUY' in signal_type:
                stop_price = entry_price * 0.98
            else:
                stop_price = entry_price * 1.02
            
            return StopLossAnalysis(
                recommended_stop=stop_price,
                confidence=0.5,
                method_used="Structure_Fallback",
                analysis_details={'error': str(e)},
                risk_percentage=2.0,
                atr_value=0
            )
    
    def _select_best_method(self, methods: List[StopLossAnalysis], entry_price: float,
                           signal_type: str) -> StopLossAnalysis:
        """Seleciona o melhor método baseado em prioridades e validação"""
        
        # Remove métodos com risco excessivo (>8%) ou muito baixo (<0.5%)
        valid_methods = []
        for method in methods:
            if 0.5 <= method.risk_percentage <= 8.0:
                valid_methods.append(method)
        
        if not valid_methods:
            # Se todos são inválidos, usa o ATR como fallback
            return methods[0]  # Primeiro sempre é ATR
        
        # Prioridades:
        # 1. Support/Resistance (confidence 0.9)
        # 2. Market Structure (confidence 0.75-0.8) 
        # 3. Swing Level (confidence 0.8)
        # 4. ATR (confidence 0.7)
        
        # Ordena por confiança e escolhe o melhor
        valid_methods.sort(key=lambda x: x.confidence, reverse=True)
        best_method = valid_methods[0]
        
        # Se o melhor método tem risco muito baixo, tenta ajustar
        if best_method.risk_percentage < 1.0:
            self.logger.debug(f"Ajustando stop por risco muito baixo: {best_method.risk_percentage:.2f}%")
            # Usa o segundo melhor ou ajusta o atual
            if len(valid_methods) > 1 and valid_methods[1].risk_percentage >= 1.0:
                best_method = valid_methods[1]
        
        return best_method
    
    def _validate_stop_loss(self, stop_analysis: StopLossAnalysis, entry_price: float,
                           signal_type: str, config: Dict) -> StopLossAnalysis:
        """Validação final do stop loss"""
        
        # VALIDAÇÃO 1: Direção correta
        if 'BUY' in signal_type and stop_analysis.recommended_stop >= entry_price:
            self.logger.warning(f"Stop inválido para BUY: {stop_analysis.recommended_stop} >= {entry_price}")
            stop_analysis.recommended_stop = entry_price * 0.985  # 1.5% de emergência
            stop_analysis.method_used += "_CORRECTED"
            stop_analysis.confidence *= 0.5
        
        elif 'SELL' in signal_type and stop_analysis.recommended_stop <= entry_price:
            self.logger.warning(f"Stop inválido para SELL: {stop_analysis.recommended_stop} <= {entry_price}")
            stop_analysis.recommended_stop = entry_price * 1.015  # 1.5% de emergência
            stop_analysis.method_used += "_CORRECTED"
            stop_analysis.confidence *= 0.5
        
        # VALIDAÇÃO 2: Risco dentro dos limites
        risk_pct = abs(entry_price - stop_analysis.recommended_stop) / entry_price * 100
        
        if risk_pct > config['max_risk_pct']:
            # Risco muito alto - ajusta
            if 'BUY' in signal_type:
                stop_analysis.recommended_stop = entry_price * (1 - config['max_risk_pct'] / 100)
            else:
                stop_analysis.recommended_stop = entry_price * (1 + config['max_risk_pct'] / 100)
            
            stop_analysis.method_used += "_RISK_LIMITED"
            stop_analysis.confidence *= 0.8
            risk_pct = config['max_risk_pct']
        
        elif risk_pct < config['min_risk_pct']:
            # Risco muito baixo - ajusta
            if 'BUY' in signal_type:
                stop_analysis.recommended_stop = entry_price * (1 - config['min_risk_pct'] / 100)
            else:
                stop_analysis.recommended_stop = entry_price * (1 + config['min_risk_pct'] / 100)
            
            stop_analysis.method_used += "_RISK_INCREASED"
            stop_analysis.confidence *= 0.9
            risk_pct = config['min_risk_pct']
        
        # Atualiza o risco final
        stop_analysis.risk_percentage = risk_pct
        
        return stop_analysis
    
    def _fallback_stop_loss(self, entry_price: float, signal_type: str, timeframe: str, symbol: str = None) -> StopLossAnalysis:
        """Stop loss de emergência quando há falha na análise COM CONFIGURAÇÕES AVANÇADAS"""
        
        # 🚨 NOVO: Usa configurações avançadas se disponíveis
        if self.use_advanced_config and symbol:
            try:
                config = self.get_config_func(symbol, timeframe)
                risk_pct = (config['min_risk_pct'] + config['max_risk_pct']) / 2  # Média do range
                method_suffix = "_Advanced_Fallback"
                self.logger.debug(f"🔧 Fallback avançado para {symbol}: {risk_pct:.1f}%")
            except Exception as e:
                risk_pct = {'5m': 1.5, '15m': 2.0, '1h': 2.5}.get(timeframe, 2.0)
                method_suffix = "_Basic_Fallback"
                self.logger.warning(f"⚠️ Erro no fallback avançado para {symbol}: {e}")
        else:
            fallback_risk = {'5m': 1.5, '15m': 2.0, '1h': 2.5}
            risk_pct = fallback_risk.get(timeframe, 2.0)
            method_suffix = "_Basic_Fallback"
        
        if 'BUY' in signal_type:
            stop_price = entry_price * (1 - risk_pct / 100)
        else:
            stop_price = entry_price * (1 + risk_pct / 100)
        
        return StopLossAnalysis(
            recommended_stop=stop_price,
            confidence=0.4,  # Baixa confiança para fallback
            method_used=f"Emergency{method_suffix}",
            analysis_details={
                'reason': 'insufficient_data_or_error',
                'symbol': symbol,
                'config_type': 'advanced' if self.use_advanced_config else 'basic'
            },
            risk_percentage=risk_pct,
            atr_value=entry_price * 0.02
        )