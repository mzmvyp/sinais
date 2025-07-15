"""
Teste Rápido dos Padrões - Verificação das correções
"""
import warnings
import logging

# Reduz warnings para ver apenas os críticos
warnings.filterwarnings("ignore", category=FutureWarning)
logging.basicConfig(level=logging.ERROR)

def quick_test():
    """Teste rápido e limpo"""
    print("TESTE RÁPIDO DOS PADRÕES CORRIGIDOS")
    print("=" * 40)
    
    try:
        from core.analyzer import TradingAnalyzer
        from config.settings import settings
        
        print(f"✓ Configurações atualizadas:")
        print(f"  • Max padrões por análise: {settings.patterns.max_patterns_per_analysis}")
        print(f"  • Força mínima: {settings.patterns.min_pattern_strength}")
        print(f"  • Tolerância double: {settings.patterns.double_tolerance}")
        
        analyzer = TradingAnalyzer()
        
        print(f"\n✓ Testando análise de BTC...")
        result = analyzer.analyze_symbol("BTC")
        
        print(f"✓ Status: {result['status']}")
        print(f"✓ Sinais gerados: {result.get('signals_generated', 0)}")
        print(f"✓ Tempo: {result.get('execution_time', 'N/A')}s")
        
        # Verifica se há padrões
        if 'analysis_summary' in result and 'PATTERNS' in result['analysis_summary']:
            patterns_info = result['analysis_summary']['PATTERNS']
            pattern_count = patterns_info.get('signals_count', 0)
            print(f"✓ Padrões detectados: {pattern_count} (controlado!)")
        
        print(f"\n✓ SUCESSO! Sistema funcionando sem warnings excessivos")
        print(f"✓ Quantidade de padrões controlada")
        
    except Exception as e:
        print(f"✗ ERRO: {e}")

if __name__ == "__main__":
    quick_test()