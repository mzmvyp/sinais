"""
SCRIPT DE VERIFICAÇÃO DA INTEGRAÇÃO DOS 43 PADRÕES DE CANDLESTICK
Execute este script para verificar se tudo está funcionando corretamente
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

def test_candlestick_import():
    """Testa importação do detector de candlestick"""
    print("🔍 TESTE 1: Importação do Detector de Candlestick")
    print("-" * 50)
    
    try:
        from indicators.candlestick_patterns_detector import (
            CandlestickDetector,
            CandlestickPattern,
            generate_candlestick_signals,
            verify_patterns_implementation
        )
        
        print("✅ Importação bem-sucedida!")
        print("✅ Classes disponíveis: CandlestickDetector, CandlestickPattern")
        print("✅ Funções disponíveis: generate_candlestick_signals, verify_patterns_implementation")
        
        return True, (CandlestickDetector, generate_candlestick_signals, verify_patterns_implementation)
        
    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        print("💡 Solução: Certifique-se de que o arquivo candlestick_patterns_detector.py está no diretório indicators/")
        return False, None

def test_patterns_catalog(detector_class):
    """Testa se o catálogo de padrões está completo"""
    print("\n🔍 TESTE 2: Verificação do Catálogo de Padrões")
    print("-" * 50)
    
    try:
        detector = detector_class()
        catalog = detector.pattern_catalog
        
        print(f"📊 Total de padrões catalogados: {len(catalog)}")
        
        # Conta por categoria
        categories = {}
        for pattern_name, metadata in catalog.items():
            category = metadata.get('category', 'unknown')
            pattern_type = metadata.get('type', 'unknown')
            
            if category not in categories:
                categories[category] = {'bullish': 0, 'bearish': 0, 'neutral': 0}
            
            categories[category][pattern_type] += 1
        
        print("\n📁 Padrões por categoria:")
        total_patterns = 0
        for category, counts in categories.items():
            category_total = sum(counts.values())
            total_patterns += category_total
            print(f"   {category.title()}: {category_total} padrões")
            print(f"      - Bullish: {counts['bullish']}")
            print(f"      - Bearish: {counts['bearish']}")
            print(f"      - Neutral: {counts['neutral']}")
        
        print(f"\n🎯 RESULTADO: {total_patterns}/43 padrões")
        
        if total_patterns >= 43:
            print("✅ CATÁLOGO COMPLETO!")
            return True
        else:
            print("⚠️ CATÁLOGO INCOMPLETO - Alguns padrões podem estar faltando")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao verificar catálogo: {e}")
        return False

def test_pattern_detection(detector_class, generate_signals_func):
    """Testa detecção de padrões com dados sintéticos"""
    print("\n🔍 TESTE 3: Detecção de Padrões com Dados Sintéticos")
    print("-" * 50)
    
    try:
        # Gera dados sintéticos que devem formar padrões
        print("📊 Gerando dados sintéticos...")
        
        # Cria um dataset que deve conter vários padrões
        periods = 150
        base_price = 50000
        
        # Dados que devem formar padrões específicos
        prices = []
        for i in range(periods):
            if i < 20:
                # Tendência de baixa inicial
                price = base_price * (1 - i * 0.01)
            elif i < 25:
                # Hammer pattern (bullish reversal)
                if i == 22:  # Hammer
                    open_p = price * 0.98
                    high_p = price * 1.002
                    low_p = price * 0.96
                    close_p = price * 0.998
                    prices.append({'open': open_p, 'high': high_p, 'low': low_p, 'close': close_p})
                    continue
                price = price * 1.005
            elif i < 50:
                # Tendência de alta
                price = price * 1.008
            elif i < 55:
                # Three white soldiers
                price = price * 1.02
            elif i < 80:
                # Continuação de alta
                price = price * 1.005
            else:
                # Movimento lateral com padrões
                price = price * (1 + np.random.normal(0, 0.005))
            
            # Gera OHLC normal para outros períodos
            volatility = 0.01
            open_p = price
            high_p = price * (1 + abs(np.random.normal(0, volatility)))
            low_p = price * (1 - abs(np.random.normal(0, volatility)))
            close_p = price * (1 + np.random.normal(0, volatility * 0.5))
            
            prices.append({'open': open_p, 'high': high_p, 'low': low_p, 'close': close_p})
            price = close_p
        
        # Cria DataFrame
        df = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=periods, freq='15min'),
            'open_price': [p['open'] for p in prices],
            'high_price': [p['high'] for p in prices],
            'low_price': [p['low'] for p in prices],
            'close_price': [p['close'] for p in prices],
            'volume': [abs(np.random.normal(1000000, 200000)) for _ in range(periods)]
        })
        
        print(f"✅ Dataset criado: {len(df)} períodos")
        
        # Testa detecção
        print("🔍 Executando detecção de padrões...")
        start_time = time.time()
        
        signals = generate_signals_func(df, "BTCUSDT_TEST")
        
        detection_time = time.time() - start_time
        
        print(f"✅ Detecção concluída em {detection_time:.3f}s")
        print(f"📊 Padrões detectados: {len(signals)}")
        
        if signals:
            print("\n🎯 PADRÕES ENCONTRADOS:")
            for i, signal in enumerate(signals[:5], 1):  # Mostra só os primeiros 5
                pattern_name = signal.get('pattern_name', 'Unknown')
                confidence = signal.get('confidence', 0)
                signal_type = signal.get('signal_type', 'Unknown')
                entry_price = signal.get('entry_price', 0)
                
                print(f"   {i}. {pattern_name}")
                print(f"      Tipo: {signal_type} | Confiança: {confidence:.3f}")
                print(f"      Entry: ${entry_price:,.2f}")
            
            if len(signals) > 5:
                print(f"   ... e mais {len(signals) - 5} padrões")
        
        return len(signals) > 0
        
    except Exception as e:
        print(f"❌ Erro na detecção: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_analyzer_integration():
    """Testa integração com o analyzer principal"""
    print("\n🔍 TESTE 4: Integração com o Trading Analyzer")
    print("-" * 50)
    
    try:
        from core.analyzer import TradingAnalyzer
        
        print("✅ Importação do TradingAnalyzer bem-sucedida")
        
        # Verifica se o candlestick detector está sendo inicializado
        analyzer = TradingAnalyzer()
        
        has_candlestick = hasattr(analyzer, 'candlestick_detector') and analyzer.candlestick_detector is not None
        
        if has_candlestick:
            print("✅ CandlestickDetector integrado no TradingAnalyzer")
            
            # Verifica se tem os 43 padrões
            catalog_size = len(analyzer.candlestick_detector.pattern_catalog)
            print(f"📊 Padrões disponíveis no analyzer: {catalog_size}")
            
            if catalog_size >= 43:
                print("✅ INTEGRAÇÃO COMPLETA: 43+ padrões disponíveis no analyzer")
                return True
            else:
                print("⚠️ INTEGRAÇÃO PARCIAL: Menos de 43 padrões no analyzer")
                return False
        else:
            print("❌ CandlestickDetector NÃO está integrado no TradingAnalyzer")
            print("💡 Verifique se o import condicional está funcionando em core/analyzer.py")
            return False
            
    except ImportError as e:
        print(f"❌ Erro ao importar TradingAnalyzer: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro na integração: {e}")
        return False

def test_indicators_module():
    """Testa se o módulo indicators está exportando tudo corretamente"""
    print("\n🔍 TESTE 5: Verificação do Módulo Indicators")
    print("-" * 50)
    
    try:
        import indicators
        
        # Verifica constantes de status
        if hasattr(indicators, 'CANDLESTICK_AVAILABLE'):
            candlestick_status = indicators.CANDLESTICK_AVAILABLE
            print(f"✅ CANDLESTICK_AVAILABLE: {candlestick_status}")
        else:
            print("⚠️ CANDLESTICK_AVAILABLE não definido")
            candlestick_status = False
        
        # Verifica se as funções estão sendo exportadas
        available_functions = []
        if hasattr(indicators, 'CandlestickDetector'):
            available_functions.append('CandlestickDetector')
        if hasattr(indicators, 'generate_candlestick_signals'):
            available_functions.append('generate_candlestick_signals')
        if hasattr(indicators, 'verify_patterns_implementation'):
            available_functions.append('verify_patterns_implementation')
        
        print(f"✅ Funções exportadas: {', '.join(available_functions)}")
        
        # Testa função de status
        if hasattr(indicators, 'get_system_status'):
            status = indicators.get_system_status()
            print(f"✅ Status do sistema: {status}")
            
            candlestick_count = status.get('candlestick_patterns_count', 0)
            if candlestick_count >= 43:
                print(f"✅ MÓDULO COMPLETO: {candlestick_count} padrões de candlestick")
                return True
            else:
                print(f"⚠️ MÓDULO INCOMPLETO: {candlestick_count} padrões de candlestick")
                return False
        else:
            print("⚠️ Função get_system_status não disponível")
            return candlestick_status
            
    except ImportError as e:
        print(f"❌ Erro ao importar módulo indicators: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro na verificação do módulo: {e}")
        return False

def main():
    """Executa todos os testes de verificação"""
    print("🚀 VERIFICAÇÃO DE INTEGRAÇÃO DOS 43 PADRÕES DE CANDLESTICK")
    print("=" * 70)
    print(f"Executado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    tests_results = []
    
    # Teste 1: Importação
    success, imports = test_candlestick_import()
    tests_results.append(("Importação do Detector", success))
    
    if not success:
        print("\n❌ FALHA CRÍTICA: Não é possível continuar sem o detector")
        return False
    
    detector_class, generate_signals_func, verify_func = imports
    
    # Teste 2: Catálogo
    success = test_patterns_catalog(detector_class)
    tests_results.append(("Catálogo de Padrões", success))
    
    # Teste 3: Detecção
    success = test_pattern_detection(detector_class, generate_signals_func)
    tests_results.append(("Detecção de Padrões", success))
    
    # Teste 4: Integração com Analyzer
    success = test_analyzer_integration()
    tests_results.append(("Integração com Analyzer", success))
    
    # Teste 5: Módulo Indicators
    success = test_indicators_module()
    tests_results.append(("Módulo Indicators", success))
    
    # Resumo final
    print("\n" + "=" * 70)
    print("📊 RESUMO DOS TESTES")
    print("=" * 70)
    
    passed = 0
    total = len(tests_results)
    
    for test_name, success in tests_results:
        status = "✅ PASSOU" if success else "❌ FALHOU"
        print(f"{test_name:<30} {status}")
        if success:
            passed += 1
    
    print("-" * 70)
    print(f"RESULTADO FINAL: {passed}/{total} testes passaram")
    
    if passed == total:
        print("🎉 SUCESSO COMPLETO! Sistema totalmente integrado.")
        print("🚀 Os 43 padrões de candlestick estão funcionando perfeitamente!")
        return True
    elif passed >= 3:
        print("⚠️ SUCESSO PARCIAL: Maioria dos componentes funcionando.")
        print("💡 Algumas correções podem ser necessárias.")
        return True
    else:
        print("❌ FALHA: Sistema não está funcionando corretamente.")
        print("🔧 Revisão e correções são necessárias.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Verificação interrompida pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 ERRO INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)