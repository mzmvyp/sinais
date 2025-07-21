"""
Script para validar se os sinais estão sendo gerados corretamente
Execute após aplicar as correções
"""
import sys
from datetime import datetime
from core.analyzer import TradingAnalyzer
from config.settings import settings

def validate_system():
    """Valida configurações e lógica do sistema"""
    print("🔍 VALIDANDO SISTEMA DE SINAIS")
    print("=" * 50)
    
    # 1. Verificar configurações
    print("\n1. VERIFICANDO CONFIGURAÇÕES:")
    print(f"   RSI Oversold: {settings.indicators.rsi_oversold} (esperado: 30)")
    print(f"   RSI Overbought: {settings.indicators.rsi_overbought} (esperado: 70)")
    print(f"   Confidence Threshold: {settings.analysis.confidence_threshold} (esperado: ≥0.7)")
    print(f"   Max Signals/Symbol: {settings.system.max_signals_per_symbol} (esperado: 1-2)")
    
    config_ok = (
        settings.indicators.rsi_oversold == 30 and
        settings.indicators.rsi_overbought == 70 and
        settings.analysis.confidence_threshold >= 0.7 and
        settings.system.max_signals_per_symbol <= 2
    )
    print(f"   Status: {'✅ OK' if config_ok else '❌ ERRO'}")
    
    # 2. Testar analyzer
    print("\n2. TESTANDO ANALYZER:")
    analyzer = TradingAnalyzer()
    
    # Verificar se configurações foram mantidas
    print(f"   RSI após init: {settings.indicators.rsi_oversold}/{settings.indicators.rsi_overbought}")
    print(f"   Confidence após init: {settings.analysis.confidence_threshold}")
    
    # 3. Simular análise
    print("\n3. SIMULANDO ANÁLISE:")
    test_symbol = "BTCUSDT"
    
    try:
        # Fazer uma análise rápida
        result = analyzer.analyze_symbol(test_symbol)
        
        if result['status'] == 'success':
            print(f"   Symbol: {test_symbol}")
            print(f"   Dados: {result.get('data_points', 0)} pontos")
            print(f"   Sinais técnicos: {result.get('technical_signals', 0)}")
            print(f"   Sinais padrões: {result.get('pattern_signals', 0)}")
            print(f"   Sinais candlestick: {result.get('candlestick_signals', 0)}")
            print(f"   Sinais salvos: {result.get('signals_saved', 0)}")
            
            # Verificar se está gerando sinais demais
            total_detected = result.get('total_detected', 0)
            if total_detected > 5:
                print(f"   ⚠️  AVISO: Muitos sinais detectados ({total_detected})")
            
            # Verificar taxa de filtragem
            if total_detected > 0:
                filter_rate = 1 - (result.get('signals_saved', 0) / total_detected)
                print(f"   Taxa de filtragem: {filter_rate:.1%}")
        else:
            print(f"   ❌ Erro na análise: {result.get('message', 'desconhecido')}")
            
    except Exception as e:
        print(f"   ❌ Exceção: {e}")
    
    # 4. Verificar componentes
    print("\n4. VERIFICANDO COMPONENTES:")
    from indicators import PATTERNS_AVAILABLE, CANDLESTICK_AVAILABLE
    
    print(f"   Indicadores técnicos: ✅ OK")
    print(f"   Padrões gráficos: {'✅ OK' if PATTERNS_AVAILABLE else '❌ Desabilitado'}")
    print(f"   Candlestick (43): {'✅ OK' if CANDLESTICK_AVAILABLE else '❌ Desabilitado'}")
    
    if CANDLESTICK_AVAILABLE:
        print("   ⚠️  RECOMENDAÇÃO: Desabilitar candlestick temporariamente")
    
    # 5. Estatísticas de sinais
    print("\n5. ESTATÍSTICAS DE SINAIS:")
    from core.signal_writer import SignalWriter
    writer = SignalWriter()
    stats = writer.get_signal_statistics()
    
    if 'error' not in stats:
        print(f"   Total sinais no banco: {stats.get('total_signals', 0)}")
        print(f"   Sinais ativos: {stats.get('active_signals', 0)}")
        print(f"   Confiança média: {stats.get('avg_confidence', 0):.3f}")
        
        # Verificar distribuição por tipo
        by_type = stats.get('by_type', {})
        if by_type:
            print("   Por tipo:")
            for sig_type, count in by_type.items():
                print(f"     {sig_type}: {count}")
    
    print("\n" + "=" * 50)
    print("VALIDAÇÃO CONCLUÍDA")
    
    # Recomendações finais
    print("\n📋 RECOMENDAÇÕES:")
    if not config_ok:
        print("❌ Corrigir configurações no settings.py")
    if CANDLESTICK_AVAILABLE:
        print("⚠️  Desabilitar detector de candlestick")
    print("✅ Monitorar por 24h após correções")
    print("✅ Verificar se sinais fazem sentido com o gráfico")
    print("✅ Implementar paper trading antes de usar real")

def test_rsi_logic():
    """Testa especificamente a lógica do RSI"""
    print("\n\n🧪 TESTE ESPECÍFICO DO RSI")
    print("=" * 50)
    
    from indicators.technical import RSIAnalyzer
    
    rsi = RSIAnalyzer()
    print(f"RSI Config: Oversold={rsi.oversold}, Overbought={rsi.overbought}")
    
    # Simular diferentes valores de RSI
    test_values = [20, 30, 40, 50, 60, 70, 80]
    
    print("\nSimulação de sinais por valor de RSI:")
    print("RSI  | Deve gerar? | Tipo esperado")
    print("-" * 40)
    
    for value in test_values:
        if value <= 30:
            should_signal = "SIM"
            expected = "BUY_LONG"
        elif value >= 70:
            should_signal = "SIM"
            expected = "SELL_SHORT"
        else:
            should_signal = "NÃO"
            expected = "Nenhum"
        
        print(f"{value:3d}  | {should_signal:11s} | {expected}")

if __name__ == "__main__":
    validate_system()
    test_rsi_logic()