"""
Trading Analyzer - CORRIGIDO para Sistema Unificado
Todas as funcionalidades integradas e funcionando
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
    """Exibe banner do sistema UNIFICADO"""
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
|  * Sistema de Validação Completo                               |
+=================================================================+
    """
    print(banner)

def format_signals_comparison(data: dict) -> str:
    """Formata comparação de sinais - CORRIGIDO"""
    if 'error' in data:
        return f"ERRO: {data['error']}"
    
    output = []
    output.append("=" * 80)
    output.append("COMPARAÇÃO DE EFETIVIDADE DOS SINAIS")
    output.append("=" * 80)
    
    # Estatísticas gerais
    general = data.get('general_stats', {})
    output.append(f"\nPeríodo analisado: {data.get('comparison_period_days', 0)} dias")
    output.append(f"Total de sinais: {general.get('total_signals', 0)}")
    output.append(f"Sinais ativos: {general.get('active_signals', 0)}")
    output.append(f"Symbols únicos: {general.get('symbols_count', 0)}")
    output.append(f"Confiança média: {general.get('avg_confidence', 0):.3f}")
    
    # Por tipo
    by_type = general.get('by_type', {})
    if by_type:
        output.append(f"\nPOR TIPO DE SINAL:")
        for signal_type, count in by_type.items():
            output.append(f"  {signal_type}: {count} sinais")
    
    # Se não há detalhamento, mostra informação disponível
    output.append(f"\nNOTA: Esta é uma implementação básica do relatório de comparação.")
    output.append(f"Para análises mais detalhadas, implementar histórico de performance.")
    
    return '\n'.join(output)

def format_output(data: dict, output_format: str) -> str:
    """Formata saída conforme solicitado - MELHORADO"""
    if output_format == 'json':
        return json.dumps(data, indent=2, default=str, ensure_ascii=False)
    
    elif output_format == 'table':
        # Formato tabular para sistema unificado
        if 'symbol' in data and data.get('status') != 'error':
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

SCORING UNIFICADO:
  * Score Total: {data.get('total_score', 0):.3f}
  * Recomendação: {data.get('recommendation', 'N/A')}
  * Nível: {data.get('confidence_level', 'N/A')}
  * Válido: {'SIM' if data.get('is_valid') else 'NÃO'}

SINAIS DETECTADOS:
  * Técnicos: {data.get('technical_signals', 0)}
  * Padrões Gráficos: {data.get('pattern_signals', 0)}
  * Candlestick: {data.get('candlestick_signals', 0)}

COMPONENTES DO SCORE:
  * Técnico: {components.get('technical', 0):.3f}
  * Padrões: {components.get('patterns', 0):.3f}
  * Candlestick: {components.get('candlestick', 0):.3f}
  * Volume: {components.get('volume', 0):.3f}
  * Tendência: {components.get('trend', 0):.3f}

VALIDAÇÕES:
  * Confidence Min: {'✅' if validations.get('min_confidence') else '❌'}
  * Volume Min: {'✅' if validations.get('min_volume') else '❌'}
  * Dados Sufic.: {'✅' if validations.get('sufficient_data') else '❌'}
  * Preço Válido: {'✅' if validations.get('valid_price') else '❌'}
  * Confirmação: {'✅' if validations.get('multiple_confirmation') else '❌'}

RESULTADO:
  * Sinais Gerados: {data.get('signals_generated', 0)}
  * Sinais Salvos: {data.get('signals_saved', 0)}
  * Tempo: {data.get('execution_time', 0):.3f}s
  * Dados: {data.get('data_points', 0)} pontos
            """.strip()
            return table
        
        elif '_summary' in data:
            # Múltiplos resultados
            output = []
            output.append("+" + "="*70 + "+")
            output.append("|" + " "*25 + "RESUMO GERAL" + " "*25 + "|")
            output.append("+" + "="*70 + "+")
            
            for symbol, result in data.items():
                if symbol == '_summary':
                    continue
                    
                if isinstance(result, dict) and result.get('status') != 'error':
                    status_icon = "✅" if result.get('status') == 'success' else "❌"
                    score = result.get('total_score', 0)
                    signals = result.get('signals_saved', 0)
                    rec = result.get('recommendation', 'HOLD')
                    valid = "V" if result.get('is_valid') else "X"
                    
                    line = f"{status_icon} {symbol:8} | Score: {score:5.2f} | {rec:10} | {valid} | {signals} sinais"
                    output.append(line)
                else:
                    output.append(f"❌ {symbol:8} | ERRO")
            
            # Resumo final
            summary = data.get('_summary', {})
            output.append("+" + "="*70 + "+")
            output.append(f"Total: {summary.get('successful_analyses', 0)}/{summary.get('symbols_analyzed', 0)} OK | {summary.get('total_signals_generated', 0)} sinais | {summary.get('total_execution_time', 0):.1f}s")
            
            return '\n'.join(output)
        else:
            # Resultado de erro
            return f"ERRO: {data.get('message', 'Erro desconhecido')}"
    
    else:  # summary
        if 'symbol' in data and data.get('status') != 'error':
            # Resultado individual
            status_icon = "✅" if data.get('status') == 'success' else "❌"
            score = data.get('total_score', 0)
            recommendation = data.get('recommendation', 'HOLD')
            signals = data.get('signals_saved', 0)
            valid = "V" if data.get('is_valid') else "X"
            
            return (
                f"{status_icon} {data['symbol']}: Score {score:.3f} | {recommendation} | "
                f"{signals} sinais | {valid} | ${data.get('latest_price', 0):,.2f}"
            )
        elif '_summary' in data:
            # Múltiplos resultados
            summary = data.get('_summary', {})
            successful = summary.get('successful_analyses', 0)
            total = summary.get('symbols_analyzed', 0)
            total_signals = summary.get('total_signals_generated', 0)
            exec_time = summary.get('total_execution_time', 0)
            
            # Calcula score médio dos sucessos
            successful_results = [r for r in data.values() 
                                if isinstance(r, dict) and r.get('status') == 'success']
            avg_score = (sum(r.get('total_score', 0) for r in successful_results) / len(successful_results)) if successful_results else 0
            
            return (
                f"Análise Unificada: {successful}/{total} symbols OK | "
                f"Score médio: {avg_score:.3f} | {total_signals} sinais | {exec_time:.1f}s"
            )
        else:
            # Erro
            return f"ERRO: {data.get('message', 'Erro desconhecido')}"

def format_system_status(status: dict, output_format: str) -> str:
    """Formata status do sistema - NOVO"""
    if output_format == 'json':
        return json.dumps(status, indent=2, default=str, ensure_ascii=False)
    
    elif output_format == 'table':
        output = []
        output.append("+" + "="*60 + "+")
        output.append("|" + " "*20 + "STATUS DO SISTEMA" + " "*20 + "|")
        output.append("+" + "="*60 + "+")
        
        output.append(f"Status Geral: {status.get('status', 'unknown')}")
        output.append(f"Tipo: {status.get('system_type', 'unknown')}")
        output.append(f"Timestamp: {status.get('timestamp', 'N/A')}")
        
        output.append("\nCOMPONENTES:")
        components = status.get('components', {})
        for comp, stat in components.items():
            icon = "✅" if stat == 'OK' else "❌" if stat == 'ERROR' else "⚠️"
            output.append(f"  {icon} {comp}: {stat}")
        
        output.append(f"\nESTATÍSTICAS:")
        output.append(f"  Symbols disponíveis: {status.get('symbols_available', 0)}")
        output.append(f"  Sinais ativos: {status.get('active_signals', 0)}")
        output.append(f"  Sinais hoje: {status.get('signals_today', 0)}")
        output.append(f"  Tempo último teste: {status.get('last_analysis_time', 0):.3f}s")
        
        if status.get('test_symbol'):
            output.append(f"  Symbol teste: {status['test_symbol']}")
            output.append(f"  Resultado teste: {status.get('test_result', 'N/A')}")
            output.append(f"  Score teste: {status.get('test_score', 0):.3f}")
        
        output.append(f"\nCONFIGURAÇÃO:")
        config = status.get('configuration', {})
        for key, value in config.items():
            output.append(f"  {key}: {value}")
        
        return '\n'.join(output)
    
    else:  # summary
        components_ok = sum(1 for stat in status.get('components', {}).values() if stat == 'OK')
        total_components = len(status.get('components', {}))
        
        return (
            f"Sistema {status.get('system_type', 'unknown')}: {status.get('status', 'unknown')} | "
            f"Componentes: {components_ok}/{total_components} OK | "
            f"Symbols: {status.get('symbols_available', 0)} | "
            f"Sinais ativos: {status.get('active_signals', 0)}"
        )

def main():
    """Função principal CORRIGIDA"""
    parser = argparse.ArgumentParser(
        description="Trading Analyzer v2.0 - Sistema Unificado COMPLETO",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python main.py --status                    # Status do sistema unificado
  python main.py --analyze BTCUSDT           # Análise unificada de um symbol
  python main.py --analyze-all               # Análise unificada de todos os symbols
  python main.py --compare-signals           # Compara efetividade dos tipos de sinais
  python main.py --continuous                # Execução contínua unificada
  python main.py --cleanup 7                 # Remove sinais antigos
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
                       help='Timeframe para análise (padrão: configurado)')
    
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
    
    args = parser.parse_args()
    
    # Configura nível de log
    log_level = 'ERROR' if args.quiet else args.log_level
    setup_logging(log_level)
    
    # Exibe banner se não estiver em modo silencioso
    if not args.quiet:
        print_banner()
    
    try:
        # Inicializa o analisador UNIFICADO
        if not args.quiet:
            print("Inicializando Trading Analyzer Unificado...")
        
        analyzer = TradingAnalyzer()
        
        # Executa comando solicitado
        if args.status:
            # Mostra status do sistema unificado
            if not args.quiet:
                print("Verificando status do sistema unificado...")
            
            status = analyzer.get_system_status()
            print(format_system_status(status, args.output))
        
        elif args.analyze:
            # Analisa symbol específico com sistema unificado
            symbol = args.analyze.upper()
            if not args.quiet:
                print(f"Iniciando análise unificada: {symbol}...")
            
            result = analyzer.analyze_symbol(symbol, args.timeframe)
            print(format_output(result, args.output))
        
        elif args.analyze_all:
            # Analisa todos os symbols com sistema unificado
            symbols = args.symbols if args.symbols else None
            if not args.quiet:
                symbols_desc = f"{len(args.symbols)} symbols especificados" if symbols else "todos os symbols configurados"
                print(f"Iniciando análise unificada: {symbols_desc}...")
            
            results = analyzer.analyze_multiple_symbols(symbols, args.timeframe)
            print(format_output(results, args.output))
        
        elif args.compare_signals:
            # Compara efetividade dos diferentes tipos de sinais
            if not args.quiet:
                print(f"Comparando sinais dos últimos {args.days} dias...")
            
            comparison = analyzer.get_signals_comparison(args.days)
            
            if args.output == 'json':
                print(json.dumps(comparison, indent=2, default=str, ensure_ascii=False))
            else:
                print(format_signals_comparison(comparison))
        
        elif args.continuous:
            # Modo contínuo unificado
            interval = args.interval if args.interval else settings.system.analysis_interval
            
            if not args.quiet:
                print(f"Iniciando análise contínua unificada (intervalo: {interval}s)")
                print("Pressione Ctrl+C para parar\n")
            
            analyzer.run_continuous_analysis(interval)
        
        elif args.cleanup is not None:
            # Limpeza de dados antigos
            if not args.quiet:
                print(f"Removendo sinais mais antigos que {args.cleanup} dias...")
            
            result = analyzer.cleanup_old_data(args.cleanup)
            
            if args.output == 'json':
                print(json.dumps(result, indent=2, default=str))
            else:
                if result.get('status') == 'success':
                    print(f"✅ Limpeza concluída: {result['removed_signals']} sinais removidos")
                else:
                    print(f"❌ Erro na limpeza: {result.get('message', 'Erro desconhecido')}")
        
        else:
            # Nenhum comando especificado
            print("ERRO: Nenhum comando especificado. Use --help para ver opções disponíveis.")
            parser.print_help()
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nOperação interrompida pelo usuário")
        sys.exit(0)
    
    except ImportError as e:
        print(f"ERRO de Importação: {e}")
        print("Verifique se todos os módulos estão instalados corretamente.")
        if not args.quiet:
            print("Execute: pip install -r requirements.txt")
        sys.exit(1)
    
    except Exception as e:
        print(f"ERRO: {e}")
        if not args.quiet:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()