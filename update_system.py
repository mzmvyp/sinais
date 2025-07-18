"""
INTEGRAÇÃO DOS PADRÕES DE CANDLESTICK
Conecta detector de patterns com sistema de trading existente
"""

import sys
import os
from datetime import datetime
from typing import Dict, List
from indicators.candlestick_patter import CandlestickDetector
from simple_analyzer import SimpleEnhancedAnalyzer

# Adiciona path
sys.path.insert(0, os.getcwd())

def test_candlestick_integration():
    """Testa integração dos padrões de candlestick"""
    print("🕯️  TESTE DE INTEGRAÇÃO - PADRÕES DE CANDLESTICK")
    print("=" * 60)
    
    try:
        # 1. Carrega sistema existente
        from core.data_reader import DataReader
        
        data_reader = DataReader()
        symbols = data_reader.get_available_symbols()
        
        print(f"✅ Sistema original conectado")
        print(f"   Symbols disponíveis: {len(symbols)}")
        print()
        
        # 2. Carrega detector de candlestick
        exec(open("candlestick_patterns_detector.py", encoding='utf-8').read())
        
        detector = CandlestickDetector()
        print(f"✅ Detector de candlestick carregado")
        print(f"   Padrões implementados: 43")
        print()
        
        return True, symbols, data_reader, detector
        
    except Exception as e:
        print(f"❌ Erro na integração: {e}")
        return False, [], None, None

def analyze_symbol_with_patterns(symbol: str, data_reader, detector):
    """Analisa symbol com padrões de candlestick"""
    print(f"🔍 ANÁLISE COM PADRÕES: {symbol}")
    print("-" * 40)
    
    try:
        # Busca dados
        market_data = data_reader.get_latest_data(symbol, "5m")
        
        if not market_data or market_data.data_points < 50:
            print(f"❌ Dados insuficientes para {symbol}")
            return None
        
        print(f"📊 Dados carregados:")
        print(f"   Períodos: {market_data.data_points}")
        print(f"   Preço atual: ${market_data.latest_price:,.2f}")
        
        # Detecta padrões
        patterns = detector.detect_all_patterns(market_data.data)
        
        print(f"\n🕯️  PADRÕES DETECTADOS: {len(patterns)}")
        
        if not patterns:
            print("   Nenhum padrão encontrado")
            return None
        
        # Mostra padrões encontrados
        valid_patterns = 0
        for i, pattern in enumerate(patterns[:8]):  # Mostra até 8 padrões
            confidence_emoji = "🟢" if pattern.confidence_level == "high" else "🟡" if pattern.confidence_level == "medium" else "🔴"
            type_emoji = "📈" if pattern.pattern_type == "bullish" else "📉" if pattern.pattern_type == "bearish" else "➖"
            
            print(f"   {i+1}. {confidence_emoji} {type_emoji} {pattern.name}")
            print(f"      Tipo: {pattern.pattern_type} | Confiança: {pattern.confidence_level}")
            print(f"      Score: {pattern.reliability_score:.2f} | Força: {pattern.signal_strength:.2f}")
            print(f"      Entry: ${pattern.entry_price:.2f} | Target: ${pattern.target_price:.2f}")
            print(f"      Stop: ${pattern.stop_loss:.2f}")
            print()
            
            if pattern.confidence_level in ['medium', 'high'] and pattern.reliability_score >= 0.6:
                valid_patterns += 1
        
        print(f"📊 RESUMO:")
        print(f"   Total encontrados: {len(patterns)}")
        print(f"   Padrões válidos: {valid_patterns}")
        print(f"   Taxa de qualidade: {valid_patterns/len(patterns)*100:.1f}%")
        
        return patterns
        
    except Exception as e:
        print(f"❌ Erro na análise de {symbol}: {e}")
        return None

def generate_candlestick_trading_signals(patterns: List, symbol: str):
    """Gera sinais de trading baseados nos padrões"""
    
    if not patterns:
        return []
    
    signals = []
    
    for pattern in patterns:
        # Só gera sinais para padrões de qualidade
        if (pattern.pattern_type in ['bullish', 'bearish'] and 
            pattern.confidence_level in ['medium', 'high'] and
            pattern.reliability_score >= 0.6):
            
            # Cria sinal no formato do sistema
            signal = {
                'symbol': symbol,
                'pattern_name': pattern.name,
                'signal_type': 'BUY' if pattern.pattern_type == 'bullish' else 'SELL',
                'confidence': pattern.reliability_score,
                'strength': pattern.signal_strength,
                'entry_price': pattern.entry_price,
                'stop_loss': pattern.stop_loss,
                'target_price': pattern.target_price,
                'pattern_description': pattern.description,
                'confidence_level': pattern.confidence_level,
                'source': 'candlestick_patterns',
                'timestamp': datetime.now()
            }
            
            signals.append(signal)
    
    return signals

def compare_technical_vs_candlestick(symbol: str, data_reader, detector):
    """Compara sinais técnicos vs padrões de candlestick"""
    print(f"\n⚔️  COMPARAÇÃO: TÉCNICO vs CANDLESTICK ({symbol})")
    print("=" * 55)
    
    try:
        # Dados
        market_data = data_reader.get_latest_data(symbol, "5m")
        if not market_data:
            print(f"❌ Dados não disponíveis")
            return
        
        print(f"📊 Analisando {market_data.data_points} períodos de {symbol}")
        
        # 1. Análise técnica tradicional
        print(f"\n🔸 SINAIS TÉCNICOS (RSI + MACD):")
        
        # Carrega enhanced analyzer
        exec(open("simple_analyzer.py", encoding='utf-8').read())
        tech_analyzer = SimpleEnhancedAnalyzer()
        
        tech_result = tech_analyzer.analyze_dataframe(market_data.data, symbol)
        
        print(f"   RSI: {tech_result.get('rsi_value', 0):.1f}")
        print(f"   Sinal técnico: {tech_result.get('signal_type', 'NONE')}")
        print(f"   Score técnico: {tech_result.get('total_score', 0):.3f}")
        print(f"   Recomendação: {tech_result.get('recommendation', 'NONE')}")
        
        # 2. Padrões de candlestick
        print(f"\n🔹 PADRÕES DE CANDLESTICK:")
        
        patterns = detector.detect_all_patterns(market_data.data)
        candlestick_signals = generate_candlestick_trading_signals(patterns, symbol)
        
        if candlestick_signals:
            best_pattern = max(candlestick_signals, key=lambda x: x['confidence'] * x['strength'])
            
            print(f"   Melhor padrão: {best_pattern['pattern_name']}")
            print(f"   Sinal candlestick: {best_pattern['signal_type']}")
            print(f"   Confiança: {best_pattern['confidence']:.2f}")
            print(f"   Força: {best_pattern['strength']:.2f}")
            print(f"   Entry: ${best_pattern['entry_price']:.2f}")
        else:
            print(f"   Nenhum padrão válido encontrado")
            best_pattern = None
        
        # 3. Análise comparativa
        print(f"\n📋 ANÁLISE COMPARATIVA:")
        
        tech_signal = tech_result.get('signal_type', 'NONE')
        tech_valid = tech_result.get('is_valid', False)
        
        candlestick_signal = best_pattern['signal_type'] if best_pattern else 'NONE'
        
        if tech_signal != 'NONE' and candlestick_signal != 'NONE':
            if tech_signal == candlestick_signal:
                print(f"   🎯 CONFLUÊNCIA PERFEITA: Ambos indicam {tech_signal}")
                print(f"   ✅ Sinal muito forte - dupla confirmação")
                confluence_score = 0.9
            else:
                print(f"   ⚠️  SINAIS CONFLITANTES:")
                print(f"      Técnico: {tech_signal} | Candlestick: {candlestick_signal}")
                print(f"   🤔 Aguardar confirmação adicional")
                confluence_score = 0.3
        elif tech_signal != 'NONE' and candlestick_signal == 'NONE':
            print(f"   📊 APENAS SINAL TÉCNICO: {tech_signal}")
            print(f"   ⚠️  Sem confirmação por padrões de candlestick")
            confluence_score = 0.6
        elif tech_signal == 'NONE' and candlestick_signal != 'NONE':
            print(f"   🕯️  APENAS PADRÃO CANDLESTICK: {candlestick_signal}")
            print(f"   ⚠️  Sem confirmação por indicadores técnicos")
            confluence_score = 0.5
        else:
            print(f"   ➖ NENHUM SINAL DETECTADO")
            print(f"   🔍 Aguardar formação de setup")
            confluence_score = 0.0
        
        # 4. Recomendação final
        print(f"\n🎯 RECOMENDAÇÃO FINAL:")
        print(f"   Score de confluência: {confluence_score:.1f}")
        
        if confluence_score >= 0.8:
            print(f"   🟢 OPERAR: Sinal muito forte com dupla confirmação")
        elif confluence_score >= 0.6:
            print(f"   🟡 CONSIDERAR: Sinal presente mas sem confluência")
        elif confluence_score >= 0.4:
            print(f"   🔴 AGUARDAR: Sinais conflitantes")
        else:
            print(f"   ⚫ FICAR FORA: Sem setups claros")
        
        return {
            'technical_signal': tech_signal,
            'technical_score': tech_result.get('total_score', 0),
            'candlestick_signal': candlestick_signal,
            'candlestick_patterns': len(patterns),
            'confluence_score': confluence_score,
            'recommendation': 'STRONG' if confluence_score >= 0.8 else 'WEAK' if confluence_score >= 0.4 else 'NONE'
        }
        
    except Exception as e:
        print(f"❌ Erro na comparação: {e}")
        return None

def analyze_multiple_symbols_with_patterns(symbols: List[str], data_reader, detector, max_symbols: int = 6):
    """Analisa múltiplos symbols com padrões"""
    print(f"\n🏆 ANÁLISE MULTI-SYMBOL COM PADRÕES")
    print("=" * 50)
    
    results = []
    
    for symbol in symbols[:max_symbols]:
        try:
            market_data = data_reader.get_latest_data(symbol, "5m")
            
            if market_data and market_data.data_points >= 50:
                # Análise técnica
                exec(open("simple_analyzer.py", encoding='utf-8').read())
                tech_analyzer = SimpleEnhancedAnalyzer()
                tech_result = tech_analyzer.analyze_dataframe(market_data.data, symbol)
                
                # Padrões de candlestick
                patterns = detector.detect_all_patterns(market_data.data)
                candlestick_signals = generate_candlestick_trading_signals(patterns, symbol)
                
                # Melhor padrão
                best_pattern = None
                if candlestick_signals:
                    best_pattern = max(candlestick_signals, key=lambda x: x['confidence'] * x['strength'])
                
                # Score combinado
                tech_score = tech_result.get('total_score', 0)
                pattern_score = best_pattern['confidence'] * best_pattern['strength'] if best_pattern else 0
                combined_score = (tech_score + pattern_score) / 2
                
                result = {
                    'symbol': symbol,
                    'price': market_data.latest_price,
                    'tech_score': tech_score,
                    'tech_signal': tech_result.get('signal_type', 'NONE'),
                    'patterns_found': len(patterns),
                    'best_pattern': best_pattern['pattern_name'] if best_pattern else 'None',
                    'pattern_signal': best_pattern['signal_type'] if best_pattern else 'NONE',
                    'pattern_score': pattern_score,
                    'combined_score': combined_score,
                    'confluence': tech_result.get('signal_type', 'NONE') == (best_pattern['signal_type'] if best_pattern else 'NONE')
                }
                
                results.append(result)
                
        except Exception as e:
            print(f"Erro ao analisar {symbol}: {e}")
            continue
    
    if not results:
        print("❌ Nenhum symbol pôde ser analisado")
        return
    
    # Ordena por score combinado
    results.sort(key=lambda x: x['combined_score'], reverse=True)
    
    print(f"📊 RANKING COMBINADO ({len(results)} symbols):")
    print()
    print("| Symbol | Preço     | T.Score | Padrão        | P.Score | Confluê | Final |")
    print("|--------|-----------|---------|---------------|---------|---------|-------|")
    
    for result in results:
        symbol = result['symbol']
        price = f"${result['price']:,.0f}"
        tech_score = f"{result['tech_score']:.2f}"
        pattern = result['best_pattern'][:12] if result['best_pattern'] != 'None' else 'None'
        pattern_score = f"{result['pattern_score']:.2f}"
        confluence = "✅" if result['confluence'] else "❌"
        final_score = f"{result['combined_score']:.2f}"
        
        print(f"| {symbol:6} | {price:>9} | {tech_score:>7} | {pattern:13} | {pattern_score:>7} | {confluence:>7} | {final_score:>5} |")
    
    # Top 3 oportunidades
    print(f"\n🏅 TOP 3 OPORTUNIDADES:")
    
    for i, result in enumerate(results[:3]):
        rank = i + 1
        symbol = result['symbol']
        combined = result['combined_score']
        confluence = result['confluence']
        
        status = "🟢 MUITO FORTE" if confluence and combined >= 0.7 else "🟡 MODERADA" if combined >= 0.5 else "🔴 FRACA"
        
        print(f"{rank}. {symbol}: Score {combined:.3f} | {status}")
        
        if result['best_pattern'] != 'None':
            print(f"   Padrão: {result['best_pattern']} ({result['pattern_signal']})")
        
        if confluence:
            print(f"   ✅ Confluência entre técnico e candlestick")
        else:
            print(f"   ⚠️ Sinais diferentes ou ausentes")
        print()
    
    return results

def main():
    """Função principal"""
    print("🕯️  SISTEMA INTEGRADO: TÉCNICO + CANDLESTICK")
    print("=" * 70)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. Testa integração
    success, symbols, data_reader, detector = test_candlestick_integration()
    if not success:
        return
    
    # 2. Análise individual detalhada
    if symbols:
        main_symbol = symbols[0] if "BTC" not in symbols else "BTC"
        patterns = analyze_symbol_with_patterns(main_symbol, data_reader, detector)
    
    # 3. Comparação técnico vs candlestick
    if symbols:
        test_symbol = symbols[0]
        comparison = compare_technical_vs_candlestick(test_symbol, data_reader, detector)
    
    # 4. Análise multi-symbol
    if len(symbols) > 1:
        results = analyze_multiple_symbols_with_patterns(symbols, data_reader, detector)
    
    print(f"\n🎉 ANÁLISE COMPLETA FINALIZADA!")
    print("=" * 40)
    print("✅ 43 padrões de candlestick implementados")
    print("✅ Integração com análise técnica")
    print("✅ Sistema de confluência ativo")
    print("✅ Ranking de oportunidades")
    print()
    print("🎯 PRÓXIMOS PASSOS:")
    print("1. Use o sistema para day trading em 5min")
    print("2. Procure confluência entre sinais")
    print("3. Priorize padrões de alta confiabilidade")
    print("4. Monitore taxa de acerto dos padrões")

if __name__ == "__main__":
    main()