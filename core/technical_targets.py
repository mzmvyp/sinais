# technical_targets.py - SISTEMA INTELIGENTE DE TARGETS TÉCNICOS

"""
Sistema Inteligente de Targets baseado em Análise Técnica
Considera Resistências, Suportes, Fibonacci, Estrutura de Mercado e Risco/Recompensa
Complementa o sistema de Stop Loss Inteligente (technical_stop_loss.py)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass

from core.data_reader import MarketData
from config.settings import settings

@dataclass
class TargetsAnalysis:
    """Resultado da análise de targets técnicos (similar ao StopLossAnalysis)"""
    targets: List[float]
    method_used: str
    confidence: float
    analysis_details: Dict
    target_levels: List[Dict]  # Informações detalhadas de cada target
    resistance_levels: Optional[List[float]] = None
    support_levels: Optional[List[float]] = None
    risk_reward_ratios: Optional[List[float]] = None

class TechnicalTargetsCalculator:
    """Calculadora inteligente de targets baseada em análise técnica"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 🚨 INTEGRA COM CONFIGURAÇÕES AVANÇADAS (se disponíveis)
        try:
            from config.stop_loss_config import stop_loss_config, get_stop_config_for_symbol
            self.advanced_config = stop_loss_config
            self.get_config_func = get_stop_config_for_symbol
            self.use_advanced_config = True
            self.logger.info("🎯 Targets Inteligentes usando configurações avançadas")
        except ImportError:
            self.use_advanced_config = False
            self.logger.warning("⚠️ Configurações avançadas não disponíveis para targets")
            
            # Configurações básicas como fallback
            self.config = {
                '5m': {
                    'fibonacci_levels': [0.382, 0.618, 1.0, 1.618],
                    'max_target_distance_pct': 6.0,
                    'min_risk_reward': 1.5,
                    'max_risk_reward': 4.0,
                    'resistance_lookback': 20,
                    'support_lookback': 20,
                    'structure_lookback': 15
                },
                '15m': {
                    'fibonacci_levels': [0.382, 0.618, 1.0, 1.618],
                    'max_target_distance_pct': 8.0,
                    'min_risk_reward': 1.8,
                    'max_risk_reward': 5.0,
                    'resistance_lookback': 30,
                    'support_lookback': 30,
                    'structure_lookback': 20
                },
                '1h': {
                    'fibonacci_levels': [0.382, 0.618, 1.0, 1.618],
                    'max_target_distance_pct': 10.0,
                    'min_risk_reward': 2.0,
                    'max_risk_reward': 6.0,
                    'resistance_lookback': 50,
                    'support_lookback': 50,
                    'structure_lookback': 30
                }
            }
    
    def calculate_intelligent_targets(self, market_data: MarketData, signal_type: str, 
                                     entry_price: float, stop_loss: float, timeframe: str) -> TargetsAnalysis:
        """
        🎯 FUNÇÃO PRINCIPAL: Calcula targets inteligentes baseados em análise técnica
        """
        try:
            # 🚨 OBTÉM CONFIGURAÇÃO PERSONALIZADA - CORRIGIDO
            if self.use_advanced_config:
                try:
                    config = self.get_config_func(market_data.symbol, timeframe)
                    # Adiciona configurações específicas de targets do fallback
                    fallback_targets_config = self._get_fallback_targets_config(timeframe)
                    # Mescla as configurações, dando prioridade às avançadas
                    for key, value in fallback_targets_config.items():
                        if key not in config:
                            config[key] = value
                    self.logger.debug(f"🎯 Usando config avançada para targets {market_data.symbol} {timeframe}")
                except Exception as e:
                    self.logger.warning(f"Erro ao obter config avançada: {e}, usando fallback")
                    config = self.config.get(timeframe, self.config['15m'])
            else:
                config = self.config.get(timeframe, self.config['15m'])
            
            df = market_data.data.copy()
            
            if len(df) < 20:
                # Fallback para dados insuficientes
                return self._fallback_targets(entry_price, stop_loss, signal_type, timeframe, market_data.symbol)
            
            # Calcula risco do trade
            risk = abs(entry_price - stop_loss)
            
            # 1. IDENTIFICA RESISTÊNCIAS E SUPORTES
            resistance_levels, support_levels = self._find_resistance_support_levels(
                df, config
            )
            
            # 2. CALCULA NÍVEIS DE FIBONACCI
            fibonacci_targets = self._calculate_fibonacci_targets(
                df, entry_price, signal_type, risk, config
            )
            
            # 3. IDENTIFICA ESTRUTURA DE MERCADO
            structure_targets = self._find_market_structure_targets(
                df, entry_price, signal_type, config
            )
            
            # 4. CALCULA TARGETS BASEADOS EM ATR
            atr_targets = self._calculate_atr_targets(df, entry_price, signal_type, risk)
            
            # 5. ESCOLHE MÉTODO MAIS APROPRIADO
            targets_analysis = self._determine_best_targets_method(
                signal_type, entry_price, risk, resistance_levels, support_levels,
                fibonacci_targets, structure_targets, atr_targets, config, market_data.symbol
            )
            
            # 6. VALIDAÇÃO FINAL
            validated_targets = self._validate_targets(
                targets_analysis, entry_price, stop_loss, signal_type, config
            )
            
            self.logger.debug(
                f"Targets Inteligentes: {market_data.symbol} {timeframe} | "
                f"Método: {validated_targets.method_used} | "
                f"Entry: {entry_price:.4f} | Targets: {[f'{t:.4f}' for t in validated_targets.targets]}"
            ) 
            
            return validated_targets
            
        except Exception as e:
            self.logger.error(f"Erro no cálculo de targets inteligentes: {e}")
            return self._fallback_targets(entry_price, stop_loss, signal_type, timeframe, market_data.symbol)
    
    def _find_resistance_support_levels(self, df: pd.DataFrame, config: Dict) -> Tuple[List[float], List[float]]:
        """Identifica níveis de suporte e resistência"""
        try:
            lookback = config.get('resistance_lookback', 30)
            recent_data = df.tail(lookback)
            
            # Encontra picos (resistência) e vales (suporte)
            highs = recent_data['high_price']
            lows = recent_data['low_price']
            
            # Resistências (máximos locais)
            resistance_levels = []
            for i in range(2, len(highs) - 2):
                if (highs.iloc[i] > highs.iloc[i-1] and highs.iloc[i] > highs.iloc[i-2] and
                    highs.iloc[i] > highs.iloc[i+1] and highs.iloc[i] > highs.iloc[i+2]):
                    resistance_levels.append(highs.iloc[i])
            
            # Suportes (mínimos locais)
            support_levels = []
            for i in range(2, len(lows) - 2):
                if (lows.iloc[i] < lows.iloc[i-1] and lows.iloc[i] < lows.iloc[i-2] and
                    lows.iloc[i] < lows.iloc[i+1] and lows.iloc[i] < lows.iloc[i+2]):
                    support_levels.append(lows.iloc[i])
            
            # Ordena e pega os mais relevantes
            resistance_levels = sorted(resistance_levels, reverse=True)[:5]
            support_levels = sorted(support_levels)[-5:]
            
            return resistance_levels, support_levels
            
        except Exception as e:
            self.logger.warning(f"Erro na identificação de S/R para targets: {e}")
            return [], []
    
    def _calculate_fibonacci_targets(self, df: pd.DataFrame, entry_price: float, 
                                   signal_type: str, risk: float, config: Dict) -> List[float]:
        """Calcula targets baseados em níveis de Fibonacci"""
        try:
            fibonacci_levels = config.get('fibonacci_levels', [0.618, 1.0, 1.618])
            targets = []
            
            # Encontra swing high/low recente para Fibonacci
            recent_data = df.tail(50)
            swing_high = recent_data['high_price'].max()
            swing_low = recent_data['low_price'].min()
            
            if 'BUY' in signal_type:
                # Para LONG: projeta Fibonacci acima do entry
                for level in fibonacci_levels:
                    fib_target = entry_price + (risk * level)
                    targets.append(fib_target)
            else:
                # Para SHORT: projeta Fibonacci abaixo do entry
                for level in fibonacci_levels:
                    fib_target = entry_price - (risk * level)
                    targets.append(fib_target)
            
            return targets[:2]  # Retorna apenas primeiros 2 targets
            
        except Exception as e:
            self.logger.warning(f"Erro no cálculo de Fibonacci targets: {e}")
            return []
    
    def _find_market_structure_targets(self, df: pd.DataFrame, entry_price: float,
                                     signal_type: str, config: Dict) -> List[float]:
        """Encontra targets baseados na estrutura de mercado"""
        try:
            lookback = config.get('structure_lookback', 20)
            recent_data = df.tail(lookback)
            
            targets = []
            
            if 'BUY' in signal_type:
                # Para LONG: busca resistências como targets
                highs = recent_data['high_price']
                potential_targets = [h for h in highs if h > entry_price]
                if potential_targets:
                    # Ordena e pega os mais próximos
                    potential_targets.sort()
                    targets = potential_targets[:2]
            else:
                # Para SHORT: busca suportes como targets
                lows = recent_data['low_price']
                potential_targets = [l for l in lows if l < entry_price]
                if potential_targets:
                    # Ordena e pega os mais próximos
                    potential_targets.sort(reverse=True)
                    targets = potential_targets[:2]
            
            return targets
            
        except Exception as e:
            self.logger.warning(f"Erro na estrutura de mercado para targets: {e}")
            return []
    
    def _calculate_atr_targets(self, df: pd.DataFrame, entry_price: float, 
                             signal_type: str, risk: float) -> List[float]:
        """Calcula targets baseados em ATR"""
        try:
            atr = self._calculate_atr(df, 14)
            targets = []
            
            # Targets baseados em múltiplos do ATR
            atr_multipliers = [2.0, 4.0]  # 2x e 4x ATR
            
            for multiplier in atr_multipliers:
                if 'BUY' in signal_type:
                    target = entry_price + (atr * multiplier)
                else:
                    target = entry_price - (atr * multiplier)
                targets.append(target)
            
            return targets
            
        except Exception as e:
            self.logger.warning(f"Erro no cálculo de ATR targets: {e}")
            return []
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calcula ATR (Average True Range)"""
        try:
            if len(df) < period + 2:
                return df['close_price'].iloc[-1] * 0.02
            
            data = df.iloc[:-1].copy() if len(df) > 1 else df.copy()
            
            # Calcula True Range
            data['prev_close'] = data['close_price'].shift(1)
            data['tr1'] = data['high_price'] - data['low_price']
            data['tr2'] = abs(data['high_price'] - data['prev_close'])
            data['tr3'] = abs(data['low_price'] - data['prev_close'])
            
            data['true_range'] = data[['tr1', 'tr2', 'tr3']].max(axis=1)
            atr = data['true_range'].ewm(span=period, adjust=False).mean().iloc[-1]
            
            return atr if pd.notna(atr) and atr > 0 else df['close_price'].iloc[-1] * 0.02
            
        except Exception as e:
            return df['close_price'].iloc[-1] * 0.02
    
    def _determine_best_targets_method(self, signal_type: str, entry_price: float, risk: float,
                                     resistance_levels: List[float], support_levels: List[float],
                                     fibonacci_targets: List[float], structure_targets: List[float],
                                     atr_targets: List[float], config: Dict, symbol: str = None) -> TargetsAnalysis:
        """
        🎯 ESCOLHE O MELHOR MÉTODO DE TARGETS
        """
        methods = []
        
        # MÉTODO 1: Resistência/Suporte targets
        if 'BUY' in signal_type and resistance_levels:
            valid_resistances = [r for r in resistance_levels if r > entry_price]
            if len(valid_resistances) >= 2:
                targets = valid_resistances[:2]
                methods.append(TargetsAnalysis(
                    targets=targets,
                    method_used="Resistance_Levels",
                    confidence=0.9,
                    analysis_details={
                        'resistance_levels': resistance_levels,
                        'selected_targets': targets
                    },
                    target_levels=[
                        {'level': targets[0], 'type': 'resistance', 'confidence': 0.9},
                        {'level': targets[1], 'type': 'resistance', 'confidence': 0.8}
                    ],
                    resistance_levels=resistance_levels
                ))
        
        elif 'SELL' in signal_type and support_levels:
            valid_supports = [s for s in support_levels if s < entry_price]
            if len(valid_supports) >= 2:
                targets = sorted(valid_supports, reverse=True)[:2]
                methods.append(TargetsAnalysis(
                    targets=targets,
                    method_used="Support_Levels",
                    confidence=0.9,
                    analysis_details={
                        'support_levels': support_levels,
                        'selected_targets': targets
                    },
                    target_levels=[
                        {'level': targets[0], 'type': 'support', 'confidence': 0.9},
                        {'level': targets[1], 'type': 'support', 'confidence': 0.8}
                    ],
                    support_levels=support_levels
                ))
        
        # MÉTODO 2: Estrutura de mercado
        if len(structure_targets) >= 2:
            methods.append(TargetsAnalysis(
                targets=structure_targets[:2],
                method_used="Market_Structure",
                confidence=0.8,
                analysis_details={
                    'structure_targets': structure_targets
                },
                target_levels=[
                    {'level': structure_targets[0], 'type': 'structure', 'confidence': 0.8},
                    {'level': structure_targets[1], 'type': 'structure', 'confidence': 0.7}
                ]
            ))
        
        # MÉTODO 3: Fibonacci
        if len(fibonacci_targets) >= 2:
            risk_reward_ratios = [abs(t - entry_price) / risk for t in fibonacci_targets]
            methods.append(TargetsAnalysis(
                targets=fibonacci_targets[:2],
                method_used="Fibonacci_Projection",
                confidence=0.75,
                analysis_details={
                    'fibonacci_levels': fibonacci_targets,
                    'risk_used': risk
                },
                target_levels=[
                    {'level': fibonacci_targets[0], 'type': 'fibonacci', 'confidence': 0.75},
                    {'level': fibonacci_targets[1], 'type': 'fibonacci', 'confidence': 0.7}
                ],
                risk_reward_ratios=risk_reward_ratios
            ))
        
        # MÉTODO 4: ATR dinâmico
        if len(atr_targets) >= 2:
            risk_reward_ratios = [abs(t - entry_price) / risk for t in atr_targets]
            methods.append(TargetsAnalysis(
                targets=atr_targets[:2],
                method_used="ATR_Dynamic",
                confidence=0.7,
                analysis_details={
                    'atr_targets': atr_targets,
                    'risk_used': risk
                },
                target_levels=[
                    {'level': atr_targets[0], 'type': 'atr', 'confidence': 0.7},
                    {'level': atr_targets[1], 'type': 'atr', 'confidence': 0.6}
                ],
                risk_reward_ratios=risk_reward_ratios
            ))
        
        # ESCOLHE O MELHOR MÉTODO
        if self.use_advanced_config and symbol:
            best_method = self._select_best_method_advanced(methods, entry_price, signal_type, symbol, config)
        else:
            best_method = self._select_best_method(methods, entry_price, signal_type, config)
        
        return best_method
    
    def _select_best_method_advanced(self, methods: List[TargetsAnalysis], entry_price: float,
                                   signal_type: str, symbol: str, config: Dict) -> TargetsAnalysis:
        """Seleção avançada com configurações personalizadas"""
        
        if not methods:
            return self._fallback_targets_analysis(entry_price, signal_type, symbol)
        
        # Filtra métodos válidos por risco/recompensa
        valid_methods = []
        min_rr = config.get('min_risk_reward', 1.5)
        max_rr = config.get('max_risk_reward', 5.0)
        
        for method in methods:
            if method.risk_reward_ratios:
                avg_rr = sum(method.risk_reward_ratios) / len(method.risk_reward_ratios)
                if min_rr <= avg_rr <= max_rr:
                    valid_methods.append(method)
            else:
                valid_methods.append(method)  # Aceita se não tem RR calculado
        
        if not valid_methods:
            return methods[0]  # Usa o primeiro se nenhum é válido
        
        # Ordena por confiança
        valid_methods.sort(key=lambda x: x.confidence, reverse=True)
        best_method = valid_methods[0]
        
        self.logger.debug(f"🎯 Método de targets selecionado: {best_method.method_used} para {symbol}")
        
        return best_method
    
    def _select_best_method(self, methods: List[TargetsAnalysis], entry_price: float,
                           signal_type: str, config: Dict) -> TargetsAnalysis:
        """Seleção básica de método"""
        
        if not methods:
            return self._fallback_targets_analysis(entry_price, signal_type)
        
        # Ordena por confiança
        methods.sort(key=lambda x: x.confidence, reverse=True)
        return methods[0]
    
    def _validate_targets(self, targets_analysis: TargetsAnalysis, entry_price: float,
                         stop_loss: float, signal_type: str, config: Dict) -> TargetsAnalysis:
        """Validação final dos targets"""
        
        # Validação 1: Direção correta
        for i, target in enumerate(targets_analysis.targets):
            if 'BUY' in signal_type and target <= entry_price:
                targets_analysis.targets[i] = entry_price * (1.02 + i * 0.02)
                targets_analysis.method_used += "_CORRECTED"
                targets_analysis.confidence *= 0.8
            
            elif 'SELL' in signal_type and target >= entry_price:
                targets_analysis.targets[i] = entry_price * (0.98 - i * 0.02)
                targets_analysis.method_used += "_CORRECTED"
                targets_analysis.confidence *= 0.8
        
        # Validação 2: Distância máxima
        max_distance_pct = config.get('max_target_distance_pct', 8.0) / 100
        
        for i, target in enumerate(targets_analysis.targets):
            distance_pct = abs(target - entry_price) / entry_price
            
            if distance_pct > max_distance_pct:
                if 'BUY' in signal_type:
                    targets_analysis.targets[i] = entry_price * (1 + max_distance_pct * (0.5 + i * 0.5))
                else:
                    targets_analysis.targets[i] = entry_price * (1 - max_distance_pct * (0.5 + i * 0.5))
                
                targets_analysis.method_used += "_DISTANCE_LIMITED"
                targets_analysis.confidence *= 0.9
        
        # Validação 3: Ordem correta dos targets
        if 'BUY' in signal_type:
            targets_analysis.targets.sort()  # Crescente para LONG
        else:
            targets_analysis.targets.sort(reverse=True)  # Decrescente para SHORT
        
        # Recalcula risk/reward ratios se necessário
        risk = abs(entry_price - stop_loss)
        targets_analysis.risk_reward_ratios = [
            abs(t - entry_price) / risk for t in targets_analysis.targets
        ]
        
        return targets_analysis
    
    def _fallback_targets(self, entry_price: float, stop_loss: float, signal_type: str, 
                         timeframe: str, symbol: str = None) -> TargetsAnalysis:
        """Targets de emergência quando há falha na análise"""
        
        risk = abs(entry_price - stop_loss)
        
        # Targets baseados em risco/recompensa simples
        if 'BUY' in signal_type:
            targets = [
                entry_price + risk * 2.0,  # 2:1 RR
                entry_price + risk * 3.0   # 3:1 RR
            ]
        else:
            targets = [
                entry_price - risk * 2.0,  # 2:1 RR
                entry_price - risk * 3.0   # 3:1 RR
            ]
        
        return TargetsAnalysis(
            targets=targets,
            method_used="Emergency_Fallback",
            confidence=0.4,
            analysis_details={
                'reason': 'insufficient_data_or_error',
                'symbol': symbol,
                'timeframe': timeframe,
                'risk_used': risk
            },
            target_levels=[
                {'level': targets[0], 'type': 'fallback', 'confidence': 0.4},
                {'level': targets[1], 'type': 'fallback', 'confidence': 0.3}
            ],
            risk_reward_ratios=[2.0, 3.0]
        )
    
    def _fallback_targets_analysis(self, entry_price: float, signal_type: str, symbol: str = None) -> TargetsAnalysis:
        """Fallback quando não há métodos válidos"""
        
        if 'BUY' in signal_type:
            targets = [entry_price * 1.03, entry_price * 1.05]
        else:
            targets = [entry_price * 0.97, entry_price * 0.95]
        
        return TargetsAnalysis(
            targets=targets,
            method_used="Simple_Fallback",
            confidence=0.3,
            analysis_details={
                'reason': 'no_valid_methods',
                'symbol': symbol
            },
            target_levels=[
                {'level': targets[0], 'type': 'simple', 'confidence': 0.3},
                {'level': targets[1], 'type': 'simple', 'confidence': 0.2}
            ]
        )
    
    def _get_fallback_targets_config(self, timeframe: str) -> Dict:
        """🚨 CORREÇÃO: Retorna configuração de targets específica para fallback"""
        return {
            'fibonacci_levels': [0.618, 1.0, 1.618, 2.618],
            'max_target_distance_pct': 8.0 if timeframe == '15m' else 6.0,
            'min_risk_reward': 1.5 if timeframe == '5m' else 1.8,
            'max_risk_reward': 4.0 if timeframe == '5m' else 5.0,
            'preferred_risk_reward': 2.5 if timeframe == '5m' else 3.0,
            'resistance_lookback': 20 if timeframe == '5m' else 30,
            'support_lookback': 20 if timeframe == '5m' else 30,
            'structure_lookback': 15 if timeframe == '5m' else 20,
            'atr_multipliers': [2.0, 3.5] if timeframe == '5m' else [2.5, 4.0],
            'preferred_methods': ['Resistance_Levels', 'Support_Levels', 'Market_Structure', 'Fibonacci_Projection'],
            'enable_fibonacci': True,
            'enable_structure_analysis': True
        }