"""
Trading Analyzer - Sistema de Análise Técnica para Criptomoedas
Ponto de entrada principal do sistema UNIFICADO
SEM EMOJIS para compatibilidade Windows
"""
import argparse
import sys
import json
import os
from datetime import datetime
from typing import Optional
import logging

# Configuração de encoding para Windows
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Imports do sistema UNIFICADO
from core.analyzer import TradingAnalyzer
from config.settings import settings

def setup_logging(log_level: str):
    """Configura sistema de logging SEM EMOJIS"""
    # Configuração específica para Windows
    if sys.platform.startswith('win'):
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(settings.system.log_file, encoding='utf-8')
            ]
        )
    else:
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(settings.system.log_file)
            ]
        )

def print_banner():
    """Exibe banner do sistema SEM EMOJIS"""
    banner = """
+=================================================================+
|                    TRADING ANALYZER v2.0                       |
|           Sistema Unificado de Análise Técnica                 |
|                                                                 |
|  * RSI + MACD com Detecção de Divergências                     |
|  * Padrões Gráficos (Head&Shoulders, Double Top/Bottom...)     |
|  * Padrões de Candlestick (43 implementados)                   |
|  * Filtros Avançados (Volume, Volatilidade, Tendência)         |
|  * Análise Paralela e Scoring Unificado                        |
|  * Sistema de Dupla Tabela para Comparação                     |
+=================================================================+
    """
    print(banner)

def setup_arguments():
    """Configura argumentos da linha de comando"""
    parser = argparse.ArgumentParser(
        description="Trading Analyzer v2.0 - Sistema Unificado de Análise Técnica",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python main.py --status                    # Status do sistema unificado
  python main.py --analyze BTCUSDT           # Análise unificada de um symbol
  python main.py --analyze-all               # Análise unificada de todos os symbols
  python main.py --compare-signals           # Compara efetividade dos tipos de sinais
  python main.py --compare-signals --days 14 # Compara sinais dos últimos 14 dias
  python main.py --continuous                # Execução contínua unificada
  python main.py --continuous --interval 300 # Contínuo com intervalo personalizado
  python main.py --cleanup 7                 # Remove sinais mais antigos que 7 dias
        """
    )
    
    # Comandos principais
    parser.add_argument('--status', action='store_true',
                       help='Mostra status do sistema unificado')
    
    parser.add_argument('--analyze', type=str, metavar='SYMBOL',
                       help='Análise unificada de um symbol (ex: BTCUSDT)')
    
    parser.add_argument('--analyze-all', action='store_true',
                       help='Análise unificada de todos os symbols configurados')
    
    parser.add_argument('--compare-signals', action='store_true',
                       help='Compara efetividade dos diferentes tipos de sinais')
    
    parser.add_argument('--continuous', action='store_true',
                       help='Execução contínua unificada')
    
    parser.add_argument('--cleanup', type=int, metavar='DAYS',
                       help='Remove sinais mais antigos que N dias')
    
    # Opções adicionais
    parser.add_argument('--timeframe', type=str, default=None,
                       help='Timeframe para análise (padrão: 5m)')
    
    parser.add_argument('--interval', type=int, default=None,
                       help='Intervalo em segundos para modo contínuo')
    
    parser.add_argument('--symbols', type=str, nargs='+',
                       help='Lista específica de symbols para analisar')
    
    parser.add_argument('--days', type=int, default=7,
                       help='Número de dias para comparação de sinais (padrão: 7)')
    
    parser.add_argument('--output', type=str, choices=['json', 'table', 'summary'],
                       default='summary', help='Formato de saída')
    
    parser.add_argument('--log-level', type=str, 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Nível de log')
    
    parser.add_argument('--quiet', action='store_true',
                       help='Modo silencioso (apenas erros)')
    
    return parser

def format_signals_comparison(data: dict) -> str:
    """Formata comparação de sinais"""
    if 'error' in data:
        return f"ERRO: {data['error']}"
    
    output = []
    output.append("=" * 80)
    output.append("COMPARAÇÃO DE EFETIVIDADE DOS SINAIS")
    output.append("=" * 80)
    
    # Estatísticas gerais
    general = data.get('general_stats', {})
    output.append(f"\nPeríodo analisado: {data.get('comparison_period_days', 0)} dias")
    output.append(f"Total de sinais: {general.get('total_unified_signals', 0)}")
    output.append(f"Symbols únicos: {general.get('symbols_count', 0)}")
    output.append(f"Confiança média: {general.get('avg_confidence', 0):.3f}")
    
    # Por origem
    by_source = general.get('by_source', {})
    output.append(f"\nPOR ORIGEM:")
    output.append(f"  Técnicos: {by_source.get('technical', 0)} sinais")
    output.append(f"  Padrões gráficos: {by_source.get('pattern', 0)} sinais")
    output.append(f"  Candlestick: {by_source.get('candlestick', 0)} sinais")
    
    # Detalhamento
    detailed = data.get('detailed_breakdown', [])
    if detailed:
        output.append(f"\nDETALHAMENTO POR PADRÃO:")
        output.append("-" * 80)
        output.append(f"{'ORIGEM':<12} {'PADRÃO':<20} {'TIPO':<10} {'QTD':<5} {'CONF':<6} {'FORÇA':<6}")
        output.append("-" * 80)
        
        for item in detailed[:15]:  # Top 15
            source = item.get('signal_source', '')[:11]
            pattern = item.get('pattern_name', '')[:19]
            ptype = item.get('pattern_type', '')[:9]
            total = item.get('total_signals', 0)
            conf = item.get('avg_confidence', 0)
            strength = item.get('avg_strength', 0)
            
            output.append(f"{source:<12} {pattern:<20} {ptype:<10} {total:<5} {conf:<6.3f} {strength:<6.3f}")
    
    return '\n'.join(output)

def format_output(data: dict, output_format: str) -> str:
    """Formata saída conforme solicitado"""
    if output_format == 'json':
        return json.dumps(data, indent=2, default=str)
    
    elif output_format == 'table':
        # Formato tabular para sistema unificado
        if 'symbol' in data:
            # Resultado individual
            components = data.get('score_components', {})
            validations = data.get('validations', {})
            
            table = f"""
+================================================================+
|                    ANÁLISE UNIFICADA                          |
+================================================================+

Symbol: {data['symbol']}
Status: {data['status']}
Preço Atual: ${data.get('latest_price', 0):,.2f}

SINAIS DETECTADOS:
  * Técnicos: {data.get('technical_signals', 0)}
  * Padrões Gráficos: {data.get('pattern_signals', 0)}
  * Candlestick: {data.get('candlestick_signals', 0)}

SCORING UNIFICADO:
  * Score Total: {data.get('total_score', 0):.3f}
  * Recomendação: {data.get('recommendation', 'N/A')}
  * Válido: {'SIM' if data.get('is_valid') else 'NÃO'}

COMPONENTES:
  * Técnico: {components.get('technical', 0):.3f}
  * Padrões: {components.get('patterns', 0):.3f}
  * Candlestick: {components.get('candlestick', 0):.3f}
  * Volume: {components.get('volume', 0):.3f}
  * Tendência: {components.get('trend', 0):.3f}

RESULTADO:
  * Sinais Gerados: {data.get('signals_generated', 0)}
  * Sinais Salvos: {data.get('signals_saved', 0)}
  * Tempo: {data.get('execution_time', 0):.3f}s
            """.strip()
            return table
        else:
            # Múltiplos resultados
            output = []
            for symbol, result in data.items():
                if isinstance(result, dict):
                    status_icon = "[OK]" if result.get('status') == 'success' else "[ERRO]"
                    score = result.get('total_score', 0)
                    signals = result.get('signals_saved', 0)
                    rec = result.get('recommendation', 'N/A')
                    
                    output.append(
                        f"{status_icon} {symbol}: Score {score:.3f} | {rec} | "
                        f"{signals} sinais ({result.get('execution_time', 0):.2f}s)"
                    )
                else:
                    output.append(f"[ERRO] {symbol}: Erro")
            return '\n'.join(output)
    
    else:  # summary
        if 'symbol' in data:
            # Resultado individual
            status_icon = "[OK]" if data.get('status') == 'success' else "[ERRO]"
            score = data.get('total_score', 0)
            recommendation = data.get('recommendation', 'N/A')
            signals = data.get('signals_saved', 0)
            
            return (
                f"{status_icon} {data['symbol']}: Score {score:.3f} | {recommendation} | "
                f"{signals} sinais | Preço: ${data.get('latest_price', 0):,.2f}"
            )
        else:
            # Múltiplos resultados
            successful = sum(1 for r in data.values() if isinstance(r, dict) and r.get('status') == 'success')
            total_signals = sum(r.get('signals_saved', 0) for r in data.values() if isinstance(r, dict))
            avg_score = sum(r.get('total_score', 0) for r in data.values() if isinstance(r, dict)) / len(data) if data else 0
            
            return (
                f"Análise Unificada: {successful}/{len(data)} symbols | "
                f"Score médio: {avg_score:.3f} | {total_signals} sinais gerados"
            )

def main():
    """Função principal"""
    parser = setup_arguments()
    args = parser.parse_args()
    
    # Configura nível de log
    log_level = 'ERROR' if args.quiet else args.log_level
    setup_logging(log_level)
    
    # Exibe banner se não estiver em modo silencioso
    if not args.quiet:
        print_banner()
    
    try:
        # Inicializa o analisador UNIFICADO
        analyzer = TradingAnalyzer()
        
        # Executa comando solicitado
        if args.status:
            # Mostra status do sistema unificado
            print("STATUS DO SISTEMA UNIFICADO:")
            status = analyzer.get_system_status()
            print(format_output(status, args.output))
        
        elif args.analyze:
            # Analisa symbol específico com sistema unificado
            symbol = args.analyze.upper()
            print(f"Análise Unificada: {symbol}...")
            
            result = analyzer.analyze_symbol(symbol, args.timeframe)
            print(format_output(result, args.output))
        
        elif args.analyze_all:
            # Analisa todos os symbols com sistema unificado
            symbols = args.symbols if args.symbols else None
            print(f"Análise Unificada: {'symbols especificados' if symbols else 'todos os symbols configurados'}...")
            
            results = analyzer.analyze_multiple_symbols(symbols, args.timeframe)
            print(format_output(results, args.output))
        
        elif args.compare_signals:
            # Compara efetividade dos diferentes tipos de sinais
            print(f"Comparando sinais dos últimos {args.days} dias...")
            
            comparison = analyzer.get_signals_comparison(args.days)
            
            if args.output == 'json':
                print(json.dumps(comparison, indent=2, default=str))
            else:
                print(format_signals_comparison(comparison))
        
        elif args.continuous:
            # Modo contínuo unificado
            interval = args.interval if args.interval else settings.system.analysis_interval
            
            print(f"Análise Contínua Unificada (intervalo: {interval}s)")
            print("Pressione Ctrl+C para parar\n")
            
            analyzer.run_continuous_analysis(interval)
        
        elif args.cleanup is not None:
            # Limpeza de dados antigos
            print(f"Removendo sinais mais antigos que {args.cleanup} dias...")
            
            result = analyzer.cleanup_old_data(args.cleanup)
            print(format_output(result, args.output))
        
        else:
            # Nenhum comando especificado
            print("ERRO: Nenhum comando especificado. Use --help para ver opções disponíveis.")
            parser.print_help()
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nOperação interrompida pelo usuário")
        sys.exit(0)
    
    except Exception as e:
        print(f"ERRO: {e}")
        if not args.quiet:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()