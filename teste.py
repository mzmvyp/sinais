#!/usr/bin/env python3
# momentum_validation_example.py - EXEMPLO PRÁTICO DA VALIDAÇÃO 1m

"""
Demonstra como o sistema usa 1m para validar sinais de 5m/15m
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def simulate_momentum_validation():
    """Simula como funciona a validação de momentum 1m"""
    
    print("🔍 SIMULAÇÃO DA VALIDAÇÃO DE MOMENTUM 1m")
    print("=" * 60)
    
    # 1. SINAL GERADO EM 5m
    print("\n1️⃣ SINAL GERADO EM 5m:")
    signal_time = datetime(2025, 7, 22, 22, 55, 0)  # 22:55
    signal_data = {
        'symbol': 'BNBUSDT',
        'timeframe': '5m',
        'signal_type': 'BUY_LONG',
        'detector': 'RSI',
        'entry_price': 797.13,
        'confidence': 0.75,
        'timestamp': signal_time
    }
    
    print(f"   📊 Detector: {signal_data['detector']} {signal_data['timeframe']}")
    print(f"   📈 Direção: {signal_data['signal_type']}")
    print(f"   💰 Entry: ${signal_data['entry_price']}")
    print(f"   ⏰ Hora: {signal_data['timestamp']}")
    
    # 2. BUSCA DADOS 1m PARA VALIDAÇÃO
    print("\n2️⃣ BUSCA DADOS 1m PARA VALIDAÇÃO:")
    
    # Simula busca de dados 1m (30min antes até 5min depois)
    search_start = signal_time - timedelta(minutes=30)  # 22:25
    search_end = signal_time + timedelta(minutes=5)     # 23:00
    
    print(f"   🔍 Período de busca: {search_start.strftime('%H:%M')} - {search_end.strftime('%H:%M')}")
    
    # Simula dados de 1m encontrados
    minutes_1m = []
    prices_1m = []
    base_price = 797.13
    
    # Gera 35 candles de 1m (22:25 - 23:00)
    for i in range(35):
        minute_time = search_start + timedelta(minutes=i)
        # Simula movimento de preço
        if i < 25:  # Antes do sinal (movimento para baixo)
            price_change = np.random.normal(-0.001, 0.002)
        else:  # Depois do sinal (movimento para cima - momentum)
            price_change = np.random.normal(0.001, 0.002)
        
        price = base_price * (1 + price_change)
        base_price = price
        
        minutes_1m.append(minute_time)
        prices_1m.append(price)
    
    df_1m = pd.DataFrame({
        'timestamp': minutes_1m,
        'close_price': prices_1m
    })
    
    print(f"   ✅ Encontrados: {len(df_1m)} candles de 1m")
    print(f"   📊 Preço inicial: ${df_1m['close_price'].iloc[0]:.4f}")
    print(f"   📊 Preço final: ${df_1m['close_price'].iloc[-1]:.4f}")
    
    # 3. CALCULA RSI DE 1m
    print("\n3️⃣ CALCULA RSI DE 1m:")
    
    def calculate_rsi_simple(prices, period=14):
        """Calcula RSI simples"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50.0)
    
    rsi_1m = calculate_rsi_simple(df_1m['close_price'])
    current_rsi_1m = rsi_1m.iloc[-1]
    
    print(f"   🔢 RSI 1m atual: {current_rsi_1m:.2f}")
    print(f"   📈 Últimos 5 valores RSI 1m: {rsi_1m.tail(5).round(2).tolist()}")
    
    # 4. VALIDAÇÃO DO MOMENTUM
    print("\n4️⃣ VALIDAÇÃO DO MOMENTUM:")
    
    # Configurações de validação
    buy_threshold = 50.0   # Para BUY: RSI deve estar > 50
    sell_threshold = 50.0  # Para SELL: RSI deve estar < 50
    
    print(f"   ⚙️ Configuração:")
    print(f"      • BUY precisa RSI > {buy_threshold}")
    print(f"      • SELL precisa RSI < {sell_threshold}")
    
    # Aplica validação
    if signal_data['signal_type'] == 'BUY_LONG':
        momentum_valid = current_rsi_1m > buy_threshold
        direction_icon = "📈"
        condition = f"RSI 1m ({current_rsi_1m:.2f}) > {buy_threshold}"
    else:  # SELL_SHORT
        momentum_valid = current_rsi_1m < sell_threshold
        direction_icon = "📉"
        condition = f"RSI 1m ({current_rsi_1m:.2f}) < {sell_threshold}"
    
    # 5. RESULTADO DA VALIDAÇÃO
    print("\n5️⃣ RESULTADO DA VALIDAÇÃO:")
    
    if momentum_valid:
        result_icon = "✅"
        result_text = "APROVADO"
        action = "Sinal será salvo no banco"
    else:
        result_icon = "❌"
        result_text = "REJEITADO"
        action = "Sinal será descartado"
    
    print(f"   {direction_icon} Sinal: {signal_data['signal_type']}")
    print(f"   🔍 Condição: {condition}")
    print(f"   {result_icon} Resultado: {result_text}")
    print(f"   🎯 Ação: {action}")
    
    # 6. PONTUAÇÃO DE VALIDAÇÃO
    print("\n6️⃣ PONTUAÇÃO DE VALIDAÇÃO:")
    
    validation_score = 0
    max_score = 6
    
    # Microestrutura (3 pontos)
    if momentum_valid:
        validation_score += 3
        print(f"   ✅ Momentum 1m: +3 pontos")
    else:
        print(f"   ❌ Momentum 1m: +0 pontos")
    
    # Volume (simulado - 2 pontos)
    volume_valid = np.random.choice([True, False], p=[0.7, 0.3])
    if volume_valid:
        validation_score += 2
        print(f"   ✅ Volume adequado: +2 pontos")
    else:
        print(f"   ❌ Volume baixo: +0 pontos")
    
    # Confidence (1 ponto)
    if signal_data['confidence'] >= 0.70:
        validation_score += 1
        print(f"   ✅ Confidence alta: +1 ponto")
    else:
        print(f"   ❌ Confidence baixa: +0 pontos")
    
    success_rate = validation_score / max_score
    required_rate = 0.40 if signal_data['timeframe'] == '5m' else 0.45
    
    print(f"\n   📊 Pontuação final: {validation_score}/{max_score} ({success_rate:.1%})")
    print(f"   🎯 Necessário: {required_rate:.1%}")
    
    final_approved = success_rate >= required_rate
    
    if final_approved:
        print(f"   🎉 SINAL FINAL: ✅ APROVADO")
        print(f"      • Sistema calculará stop/targets")
        print(f"      • Sinal será salvo e executado")
    else:
        print(f"   🚫 SINAL FINAL: ❌ REJEITADO")
        print(f"      • Sinal será descartado")
        print(f"      • Nenhuma ação será tomada")
    
    return {
        'signal': signal_data,
        'momentum_valid': momentum_valid,
        'final_approved': final_approved,
        'rsi_1m': current_rsi_1m,
        'validation_score': validation_score,
        'success_rate': success_rate
    }

def demonstrate_different_scenarios():
    """Demonstra diferentes cenários de validação"""
    
    print("\n\n🎭 DEMONSTRAÇÃO DE DIFERENTES CENÁRIOS")
    print("=" * 60)
    
    scenarios = [
        {
            'name': 'BUY com momentum favorável',
            'signal_type': 'BUY_LONG',
            'rsi_1m': 55.2,
            'expected': 'APROVADO'
        },
        {
            'name': 'BUY com momentum desfavorável',
            'signal_type': 'BUY_LONG',
            'rsi_1m': 45.8,
            'expected': 'REJEITADO'
        },
        {
            'name': 'SELL com momentum favorável',
            'signal_type': 'SELL_SHORT',
            'rsi_1m': 44.1,
            'expected': 'APROVADO'
        },
        {
            'name': 'SELL com momentum desfavorável',
            'signal_type': 'SELL_SHORT',
            'rsi_1m': 56.7,
            'expected': 'REJEITADO'
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}️⃣ CENÁRIO: {scenario['name']}")
        print(f"   📊 Tipo: {scenario['signal_type']}")
        print(f"   🔢 RSI 1m: {scenario['rsi_1m']:.1f}")
        
        if scenario['signal_type'] == 'BUY_LONG':
            valid = scenario['rsi_1m'] > 50.0
            condition = f"RSI ({scenario['rsi_1m']:.1f}) > 50.0"
        else:
            valid = scenario['rsi_1m'] < 50.0
            condition = f"RSI ({scenario['rsi_1m']:.1f}) < 50.0"
        
        icon = "✅" if valid else "❌"
        result = "APROVADO" if valid else "REJEITADO"
        
        print(f"   🔍 Condição: {condition}")
        print(f"   {icon} Resultado: {result}")
        print(f"   🎯 Esperado: {scenario['expected']}")
        
        if result == scenario['expected']:
            print(f"   ✅ Cenário funcionou conforme esperado")
        else:
            print(f"   ❌ Cenário divergiu do esperado")

if __name__ == "__main__":
    print("🚀 DEMONSTRAÇÃO PRÁTICA - VALIDAÇÃO MOMENTUM 1m")
    print("Este script mostra como o sistema usa dados de 1m para validar sinais")
    
    # Executa simulação principal
    result = simulate_momentum_validation()
    
    # Mostra diferentes cenários
    demonstrate_different_scenarios()
    
    print("\n\n📝 RESUMO:")
    print("• 1m NÃO gera sinais, apenas VALIDA")
    print("• RSI de 1m confirma momentum do sinal")
    print("• Validação em múltiplas camadas")
    print("• Apenas sinais com momentum confirmado são aprovados")
    print("\n🎯 Sistema inteligente: patterns detectam, 1m valida, técnico executa!")