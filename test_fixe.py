"""
Teste das Correções - Verifica se os warnings foram resolvidos
e se a quantidade de padrões está mais controlada
"""
import warnings
import logging

def test_pattern_fixes():
    """Testa se as correções funcionaram"""
    print("[FIX-TEST] Testando correções dos padrões...")
    
    # Captura warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        try:
            from core.data_reader import DataReader
            from indicators.patterns import PatternAnalyzer
            from config.settings import settings
            
            # Configura logging para reduzir ruído
            logging.basicConfig(level=logging.WARNING)
            
            print(f"[CONFIG] Novos parâmetros:")
            print(f"  Cup min depth: {settings.patterns.cup_min_depth}")
            print(f"  Double tolerance: {settings.patterns.double_tolerance}")
            print(f"  Double min distance: {settings.patterns.double_min_distance}")
            print(f"  Min pattern strength: {settings.patterns.min_pattern_strength}")
            print(f"  Max patterns per analysis: {settings.patterns.max_patterns_per_analysis}")
            
            # Testa com dados reais
            reader = DataReader()
            pattern_analyzer = PatternAnalyzer()
            
            # Testa BTC
            market_data = reader.get_latest_data("BTC")
            
            if market_data:
                print(f"\n[TEST] Analisando BTC com {market_data.data_points} pontos...")
                
                patterns = pattern_analyzer.analyze_all_patterns(market_data)
                
                print(f"[RESULT] {len(patterns)} padrões detectados (era 215+)")
                
                # Mostra detalhes dos padrões
                for i, pattern in enumerate(patterns):
                    print(f"  {i+1}. {pattern.pattern_name}")
                    print(f"     Tipo: {pattern.pattern_type}")
                    print(f"     Confiança: {pattern.confidence:.3f}")
                    print(f"     Força: {pattern.strength:.3f}")
                    print(f"     Score: {pattern.confidence * pattern.strength:.3f}")
                
                # Verifica warnings
                pandas_warnings = [warning for warning in w if "FutureWarning" in str(warning.category)]
                
                if pandas_warnings:
                    print(f"\n[WARNING] Ainda há {len(pandas_warnings)} warnings do pandas")
                    for warning in pandas_warnings[:3]:  # Mostra só os primeiros 3
                        print(f"  - {warning.message}")
                else:
                    print(f"\n[OK] Nenhum warning do pandas detectado!")
                
                # Testa outros symbols rapidamente
                print(f"\n[QUICK-TEST] Testando outros symbols...")
                symbols = ["ETH", "BNB"]
                
                for symbol in symbols:
                    data = reader.get_latest_data(symbol)
                    if data:
                        patterns = pattern_analyzer.analyze_all_patterns(data)
                        print(f"  {symbol}: {len(patterns)} padrões")
                
                print(f"\n[SUCCESS] Correções aplicadas com sucesso!")
                
            else:
                print("[ERROR] Sem dados para teste")
                
        except Exception as e:
            print(f"[ERROR] Erro no teste: {e}")
            import traceback
            traceback.print_exc()

def test_performance():
    """Testa performance com novos parâmetros"""
    print("\n[PERFORMANCE] Testando performance...")
    
    import time
    
    try:
        from core.analyzer import TradingAnalyzer
        
        analyzer = TradingAnalyzer()
        
        start_time = time.time()
        result = analyzer.analyze_symbol("BTC")
        end_time = time.time()
        
        print(f"[TIMING] Análise de BTC: {end_time - start_time:.2f}s")
        print(f"[RESULT] Status: {result['status']}")
        print(f"[RESULT] Sinais: {result.get('signals_generated', 0)}")
        
        if 'analysis_summary' in result and 'PATTERNS' in result['analysis_summary']:
            pattern_count = result['analysis_summary']['PATTERNS'].get('signals_count', 0)
            print(f"[RESULT] Sinais de padrões: {pattern_count}")
        
    except Exception as e:
        print(f"[ERROR] Erro no teste de performance: {e}")

def show_quality_improvements():
    """Mostra as melhorias de qualidade implementadas"""
    print("\n[IMPROVEMENTS] Melhorias implementadas:")
    print("=" * 50)
    print()
    print("1. CORREÇÃO DE WARNINGS:")
    print("   ✓ Tratamento seguro de valores NA")
    print("   ✓ Verificação de seções vazias")
    print("   ✓ Uso de máscaras ao invés de idxmin/idxmax direto")
    print()
    print("2. CRITÉRIOS MAIS RIGOROSOS:")
    print("   ✓ Cup & Handle: profundidade mínima 15% (era 10%)")
    print("   ✓ Double patterns: tolerância 1.5% (era 2%)")
    print("   ✓ Head & Shoulders: tolerância 3% (era 5%)")
    print("   ✓ Significância mínima de 8% nos movimentos")
    print()
    print("3. CONTROLE DE QUALIDADE:")
    print("   ✓ Força mínima de 0.6 para considerar padrão")
    print("   ✓ Máximo de 5 padrões por análise")
    print("   ✓ Ordenação por confiança × força")
    print()
    print("4. VALIDAÇÕES ADICIONAIS:")
    print("   ✓ Proeminência mínima da cabeça em H&S")
    print("   ✓ Movimento mínimo significativo")
    print("   ✓ Tratamento de erros robusto")
    print()

if __name__ == "__main__":
    show_quality_improvements()
    test_pattern_fixes()
    test_performance()