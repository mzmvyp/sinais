# core/timing_controller.py - SISTEMA DE CONTROLE DE TEMPO PARA SINAIS

"""
Timing Controller - Resolve o problema de sinais atrasados:
1. Só permite gerar sinais quando candles acabaram de fechar
2. Valida timing usando dados de 1m para precisão
3. Para 5m: máximo 1 minuto após fechamento
4. Para 15m: máximo 3 minutos após fechamento
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, Any
import pandas as pd
from dataclasses import dataclass

@dataclass
class TimingValidation:
    """Resultado da validação de timing"""
    is_valid: bool
    timeframe: str
    last_candle_close: datetime
    time_since_close: timedelta
    max_allowed_delay: timedelta
    current_time: datetime
    validation_details: Dict[str, Any]
    reason: str = ""

class SignalTimingController:
    """
    Controla QUANDO sinais podem ser gerados baseado no timing dos candles
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # CONFIGURAÇÕES DE TIMING RÍGIDAS
        self.MAX_DELAY_5M = timedelta(minutes=1)   # 5m: máximo 1 minuto de atraso
        self.MAX_DELAY_15M = timedelta(minutes=3)  # 15m: máximo 3 minutos de atraso
        self.MAX_DELAY_1M = timedelta(seconds=30)  # 1m: máximo 30 segundos
        
        # Cache para evitar recálculos
        self._timing_cache = {}
        self._cache_expiry = timedelta(seconds=30)
        
        self.logger.info("🕒 SignalTimingController inicializado:")
        self.logger.info(f"  • 5m: máximo {self.MAX_DELAY_5M.total_seconds():.0f}s após fechamento")
        self.logger.info(f"  • 15m: máximo {self.MAX_DELAY_15M.total_seconds():.0f}s após fechamento")
        self.logger.info(f"  • 1m: máximo {self.MAX_DELAY_1M.total_seconds():.0f}s após fechamento")
    
    def can_generate_signals(self, symbol: str, timeframe: str, market_data: pd.DataFrame) -> TimingValidation:
        """
        Verifica se PODE gerar sinais agora baseado no timing dos candles
        """
        current_time = datetime.now()
        
        # Verifica cache primeiro
        cache_key = f"{symbol}_{timeframe}"
        if cache_key in self._timing_cache:
            cached_result, cache_time = self._timing_cache[cache_key]
            if current_time - cache_time < self._cache_expiry:
                self.logger.debug(f"⚡ Cache hit para {cache_key}")
                return cached_result
        
        try:
            # Valida dados básicos
            if market_data is None or len(market_data) < 2:
                return TimingValidation(
                    is_valid=False,
                    timeframe=timeframe,
                    last_candle_close=current_time,
                    time_since_close=timedelta(0),
                    max_allowed_delay=self._get_max_delay(timeframe),
                    current_time=current_time,
                    validation_details={'error': 'Dados insuficientes'},
                    reason="Dados de mercado insuficientes"
                )
            
            # Pega o último candle FECHADO (penúltimo na série)
            last_closed_candle = market_data.iloc[-2]
            last_candle_time = pd.to_datetime(last_closed_candle['timestamp'])
            
            # Calcula quando esse candle deveria ter fechado
            expected_close_time = self._calculate_expected_close_time(last_candle_time, timeframe)
            time_since_close = current_time - expected_close_time
            max_allowed_delay = self._get_max_delay(timeframe)
            
            # Validação principal
            is_valid = time_since_close <= max_allowed_delay and time_since_close >= timedelta(0)
            
            validation_details = {
                'last_candle_timestamp': last_candle_time.isoformat(),
                'expected_close_time': expected_close_time.isoformat(),
                'actual_delay_seconds': time_since_close.total_seconds(),
                'max_allowed_seconds': max_allowed_delay.total_seconds(),
                'candle_price': float(last_closed_candle.get('close_price', 0))
            }
            
            if is_valid:
                reason = f"Timing OK - {time_since_close.total_seconds():.0f}s após fechamento"
                self.logger.debug(f"✅ {symbol} {timeframe}: {reason}")
            else:
                if time_since_close < timedelta(0):
                    reason = f"Candle ainda não fechou (futuro: {abs(time_since_close.total_seconds()):.0f}s)"
                else:
                    reason = f"Muito atrasado - {time_since_close.total_seconds():.0f}s > {max_allowed_delay.total_seconds():.0f}s"
                self.logger.warning(f"❌ {symbol} {timeframe}: {reason}")
            
            result = TimingValidation(
                is_valid=is_valid,
                timeframe=timeframe,
                last_candle_close=expected_close_time,
                time_since_close=time_since_close,
                max_allowed_delay=max_allowed_delay,
                current_time=current_time,
                validation_details=validation_details,
                reason=reason
            )
            
            # Atualiza cache
            self._timing_cache[cache_key] = (result, current_time)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Erro na validação de timing para {symbol} {timeframe}: {e}")
            return TimingValidation(
                is_valid=False,
                timeframe=timeframe,
                last_candle_close=current_time,
                time_since_close=timedelta(0),
                max_allowed_delay=self._get_max_delay(timeframe),
                current_time=current_time,
                validation_details={'error': str(e)},
                reason=f"Erro na validação: {e}"
            )
    
    def validate_signal_timing_with_1m_data(self, symbol: str, timeframe: str, 
                                           entry_price: float, signal_type: str,
                                           data_reader) -> Tuple[bool, Dict[str, Any]]:
        """
        Valida se um sinal ainda é válido usando dados de 1m para precisão máxima
        """
        try:
            # Busca dados de 1m para validação de preço atual
            current_1m_data = data_reader.get_latest_data(symbol, "1m", limit=5)
            
            if not current_1m_data or len(current_1m_data.data) == 0:
                return False, {
                    'reason': 'sem_dados_1m',
                    'details': 'Dados de 1m não disponíveis para validação'
                }
            
            # Pega preço mais atual
            current_price = float(current_1m_data.data.iloc[-1]['close_price'])
            current_1m_time = pd.to_datetime(current_1m_data.data.iloc[-1]['timestamp'])
            
            # Verifica se dados de 1m são frescos (últimos 2 minutos)
            time_diff = datetime.now() - current_1m_time
            if time_diff > timedelta(minutes=2):
                return False, {
                    'reason': 'dados_1m_antigos',
                    'details': f'Dados de 1m com {time_diff.total_seconds():.0f}s de atraso',
                    'current_price': current_price
                }
            
            # Calcula tolerância baseada no timeframe
            if timeframe == "5m":
                tolerance_pct = 0.3  # 0.3% para 5m
            elif timeframe == "15m":
                tolerance_pct = 0.5  # 0.5% para 15m
            else:
                tolerance_pct = 0.2  # 0.2% para outros
            
            tolerance = entry_price * (tolerance_pct / 100)
            
            # Validação por tipo de sinal
            if signal_type == "BUY_LONG":
                # Para compra: preço atual não pode estar muito acima do entry
                max_allowed_price = entry_price + tolerance
                is_valid = current_price <= max_allowed_price
                
                validation_details = {
                    'current_price': current_price,
                    'entry_price': entry_price,
                    'max_allowed_price': max_allowed_price,
                    'price_diff_pct': ((current_price - entry_price) / entry_price) * 100,
                    'tolerance_pct': tolerance_pct,
                    'signal_viable': is_valid
                }
                
                if not is_valid:
                    reason = f"Preço subiu muito - Atual: {current_price:.4f} > Máx: {max_allowed_price:.4f}"
                else:
                    reason = f"Sinal BUY viável - Preço OK"
                    
            else:  # SELL_SHORT
                # Para venda: preço atual não pode estar muito abaixo do entry
                min_allowed_price = entry_price - tolerance
                is_valid = current_price >= min_allowed_price
                
                validation_details = {
                    'current_price': current_price,
                    'entry_price': entry_price,
                    'min_allowed_price': min_allowed_price,
                    'price_diff_pct': ((entry_price - current_price) / entry_price) * 100,
                    'tolerance_pct': tolerance_pct,
                    'signal_viable': is_valid
                }
                
                if not is_valid:
                    reason = f"Preço caiu muito - Atual: {current_price:.4f} < Mín: {min_allowed_price:.4f}"
                else:
                    reason = f"Sinal SELL viável - Preço OK"
            
            validation_details.update({
                'reason': reason,
                'current_1m_timestamp': current_1m_time.isoformat(),
                'data_freshness_seconds': time_diff.total_seconds()
            })
            
            if is_valid:
                self.logger.debug(f"✅ {symbol} {timeframe}: Sinal {signal_type} validado com 1m data")
            else:
                self.logger.warning(f"❌ {symbol} {timeframe}: {reason}")
            
            return is_valid, validation_details
            
        except Exception as e:
            self.logger.error(f"❌ Erro na validação com dados 1m para {symbol}: {e}")
            return False, {
                'reason': 'erro_validacao_1m',
                'details': str(e)
            }
    
    def _get_max_delay(self, timeframe: str) -> timedelta:
        """Retorna o delay máximo permitido para um timeframe"""
        if timeframe == "5m":
            return self.MAX_DELAY_5M
        elif timeframe == "15m":
            return self.MAX_DELAY_15M
        elif timeframe == "1m":
            return self.MAX_DELAY_1M
        else:
            return timedelta(minutes=1)  # Default
    
    def _calculate_expected_close_time(self, candle_time: datetime, timeframe: str) -> datetime:
        """
        Calcula quando um candle deveria ter fechado baseado no seu timestamp
        """
        if timeframe == "5m":
            # Arredonda para o próximo múltiplo de 5 minutos
            minutes = candle_time.minute
            next_5min = ((minutes // 5) + 1) * 5
            
            if next_5min >= 60:
                expected_close = candle_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            else:
                expected_close = candle_time.replace(minute=next_5min, second=0, microsecond=0)
                
        elif timeframe == "15m":
            # Arredonda para o próximo múltiplo de 15 minutos
            minutes = candle_time.minute
            next_15min = ((minutes // 15) + 1) * 15
            
            if next_15min >= 60:
                expected_close = candle_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            else:
                expected_close = candle_time.replace(minute=next_15min, second=0, microsecond=0)
                
        elif timeframe == "1m":
            # Próximo minuto
            expected_close = candle_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
            
        else:
            # Para outros timeframes, assume o próximo minuto
            expected_close = candle_time + timedelta(minutes=1)
        
        return expected_close
    
    def get_next_signal_generation_window(self, timeframe: str) -> datetime:
        """
        Retorna o próximo momento em que sinais podem ser gerados para um timeframe
        """
        current_time = datetime.now()
        
        if timeframe == "5m":
            # Próxima janela de 5 minutos
            minutes = current_time.minute
            next_5min = ((minutes // 5) + 1) * 5
            
            if next_5min >= 60:
                next_window = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            else:
                next_window = current_time.replace(minute=next_5min, second=0, microsecond=0)
                
        elif timeframe == "15m":
            # Próxima janela de 15 minutos
            minutes = current_time.minute
            next_15min = ((minutes // 15) + 1) * 15
            
            if next_15min >= 60:
                next_window = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            else:
                next_window = current_time.replace(minute=next_15min, second=0, microsecond=0)
                
        else:
            # Para outros timeframes, próximo minuto
            next_window = current_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
        
        return next_window
    
    def get_timing_summary(self, symbols: list, timeframes: list, data_reader) -> Dict[str, Any]:
        """
        Retorna resumo de timing para múltiplos symbols e timeframes
        """
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_combinations': len(symbols) * len(timeframes),
            'valid_for_signals': 0,
            'invalid_combinations': 0,
            'details_by_symbol': {},
            'next_windows': {}
        }
        
        for symbol in symbols:
            summary['details_by_symbol'][symbol] = {}
            
            for timeframe in timeframes:
                try:
                    # Busca dados
                    market_data = data_reader.get_latest_data(symbol, timeframe)
                    
                    if market_data and market_data.data is not None:
                        validation = self.can_generate_signals(symbol, timeframe, market_data.data)
                        
                        summary['details_by_symbol'][symbol][timeframe] = {
                            'can_generate': validation.is_valid,
                            'reason': validation.reason,
                            'time_since_close_seconds': validation.time_since_close.total_seconds(),
                            'max_allowed_seconds': validation.max_allowed_delay.total_seconds()
                        }
                        
                        if validation.is_valid:
                            summary['valid_for_signals'] += 1
                        else:
                            summary['invalid_combinations'] += 1
                    else:
                        summary['details_by_symbol'][symbol][timeframe] = {
                            'can_generate': False,
                            'reason': 'Sem dados disponíveis'
                        }
                        summary['invalid_combinations'] += 1
                        
                except Exception as e:
                    summary['details_by_symbol'][symbol][timeframe] = {
                        'can_generate': False,
                        'reason': f'Erro: {e}'
                    }
                    summary['invalid_combinations'] += 1
        
        # Calcula próximas janelas
        for timeframe in timeframes:
            summary['next_windows'][timeframe] = self.get_next_signal_generation_window(timeframe).isoformat()
        
        return summary
    
    def clear_cache(self):
        """Limpa cache de timing"""
        self._timing_cache.clear()
        self.logger.debug("🧹 Cache de timing limpo")

# Função utilitária para usar no analyzer
def create_timing_controller() -> SignalTimingController:
    """Factory function para criar o timing controller"""
    return SignalTimingController()