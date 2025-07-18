"""
Trading Analyzer - Sistema de Análise Técnica para Criptomoedas
Ponto de entrada principal do sistema
"""
import argparse
import sys
import json
from datetime import datetime
from typing import Optional

# Imports do sistema
from core.analyzer import TradingAnalyzer, EnhancedFilters, EnhancedTradingAnalyzer
from config.settings import settings
import logging

def print_banner():
    """Exibe banner do sistema"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    TRADING ANALYZER v1.0                    ║
║              Sistema de Análise Técnica Modular             ║
║                                                              ║
║  ● RSI com Detecção de Divergências                         ║
║  ● MACD com Cruzamentos                                      ║
║  ● Sistema Modular e Extensível                             ║
║  ● Análise Paralela                                         ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def setup_arguments():
    """Configura argumentos da linha de comando"""
    parser = argparse.ArgumentParser(
        description="Trading Analyzer - Sistema de Análise Técnica",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python main.py --status                    # Mostra status do sistema
  python main.py --analyze BTCUSDT           # Analisa um symbol específico
  python main.py --analyze-all               # Analisa todos os symbols configurados
  python main.py --continuous                # Execução contínua
  python main.py --continuous --interval 300 # Contínuo com intervalo personalizado
  python main.py --cleanup 7                 # Remove sinais mais antigos que 7 dias
        """
    )
    
    # Comandos principais
    parser.add_argument('--status', action='store_true',
                       help='Mostra status do sistema')
    
    parser.add_argument('--analyze', type=str, metavar='SYMBOL',
                       help='Analisa um symbol específico (ex: BTCUSDT)')
    
    parser.add_argument('--analyze-all', action='store_true',
                       help='Analisa todos os symbols configurados')
    
    parser.add_argument('--continuous', action='store_true',
                       help='Execução contínua')
    
    parser.add_argument('--cleanup', type=int, metavar='DAYS',
                       help='Remove sinais mais antigos que N dias')
    
    # Opções adicionais
    parser.add_argument('--timeframe', type=str, default=None,
                       help='Timeframe para análise (padrão: 5m)')
    
    parser.add_argument('--interval', type=int, default=None,
                       help='Intervalo em segundos para modo contínuo')
    
    parser.add_argument('--symbols', type=str, nargs='+',
                       help='Lista específica de symbols para analisar')
    
    parser.add_argument('--output', type=str, choices=['json', 'table', 'summary'],
                       default='summary', help='Formato de saída')
    
    parser.add_argument('--log-level', type=str, 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Nível de log')
    
    parser.add_argument('--quiet', action='store_true',
                       help='Modo silencioso (apenas erros)')
    
    return parser

def format_output(data: dict, output_format: str) -> str:
    """Formata saída conforme solicitado"""
    if output_format == 'json':
        return json.dumps(data, indent=2, default=str)
    
    elif output_format == 'table':
        # Formato tabular simples
        if 'symbol' in data:
            # Resultado individual
            return f"""
Symbol: {data['symbol']}
Status: {data['status']}
Preço Atual: {data.get('latest_price', 'N/A')}
Sinais Gerados: {data.get('signals_generated', 0)}
Sinais Salvos: {data.get('signals_saved', 0)}
Tempo de Execução: {data.get('execution_time', 'N/A')}s
            """.strip()
        else:
            # Múltiplos resultados
            output = []
            for symbol, result in data.items():
                status_emoji = "✅" if result['status'] == 'success' else "❌"
                output.append(
                    f"{status_emoji} {symbol}: {result.get('signals_generated', 0)} sinais "
                    f"({result.get('execution_time', 'N/A')}s)"
                )
            return '\n'.join(output)
    
    else:  # summary
        if 'symbol' in data:
            # Resultado individual
            status_emoji = "✅" if data['status'] == 'success' else "❌"
            return (
                f"{status_emoji} {data['symbol']}: {data.get('signals_generated', 0)} sinais gerados, "
                f"preço atual: {data.get('latest_price', 'N/A')}"
            )
        else:
            # Múltiplos resultados
            successful = sum(1 for r in data.values() if r['status'] == 'success')
            total_signals = sum(r.get('signals_generated', 0) for r in data.values())
            return f"📊 {successful}/{len(data)} symbols analisados, {total_signals} sinais gerados"

def main():
    """Função principal"""
    parser = setup_arguments()
    args = parser.parse_args()
    
    # Configura nível de log
    if args.quiet:
        log_level = 'ERROR'
    else:
        log_level = args.log_level
    
    # Atualiza configurações
    settings.system.log_level = log_level
    
    # Exibe banner se não estiver em modo silencioso
    if not args.quiet:
        print_banner()
    
    try:
        # Inicializa o analisador
        analyzer = EnhancedTradingAnalyzer()
        
        # Executa comando solicitado
        if args.status:
            # Mostra status do sistema
            status = analyzer.get_system_status()
            print("📊 STATUS DO SISTEMA:")
            print(format_output(status, args.output))
        
        elif args.analyze:
            # Analisa symbol específico
            symbol = args.analyze.upper()
            print(f"🔍 Analisando {symbol}...")
            
            result = analyzer.analyze_symbol(symbol, args.timeframe)
            print(format_output(result, args.output))
        
        elif args.analyze_all:
            # Analisa todos os symbols
            symbols = args.symbols if args.symbols else None
            print(f"🚀 Analisando {'symbols especificados' if symbols else 'todos os symbols configurados'}...")
            
            results = analyzer.analyze_multiple_symbols(symbols, args.timeframe)
            print(format_output(results, args.output))
        
        elif args.continuous:
            # Modo contínuo
            interval = args.interval if args.interval else settings.system.analysis_interval
            
            print(f"🔄 Iniciando análise contínua (intervalo: {interval}s)")
            print("Pressione Ctrl+C para parar\n")
            
            analyzer.run_continuous_analysis(interval)
        
        elif args.cleanup is not None:
            # Limpeza de dados antigos
            print(f"🧹 Removendo sinais mais antigos que {args.cleanup} dias...")
            
            result = analyzer.cleanup_old_data(args.cleanup)
            print(format_output(result, args.output))
        
        else:
            # Nenhum comando especificado
            print("❌ Nenhum comando especificado. Use --help para ver opções disponíveis.")
            parser.print_help()
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n🛑 Operação interrompida pelo usuário")
        sys.exit(0)
    
    except Exception as e:
        print(f"❌ Erro: {e}")
        if not args.quiet:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()