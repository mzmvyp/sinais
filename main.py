"""
Trading Analyzer - SISTEMA ANTI-SPAM COMPLETO
Máximo 1 sinal ativo por symbol+timeframe + Ferramentas de gerenciamento
"""
import argparse
import sys
import json
import os
from datetime import datetime
from typing import Optional
import logging

from core.data_reader import DataReader

# Configuração de encoding para Windows
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Imports do sistema UNIFICADO
from core.analyzer import TradingAnalyzer
from config.settings import settings

# 🚨 NOVO IMPORT: Gerenciador de sinais
try:
    from core.signal_manager import SignalManager, print_active_signals_table, clear_symbol_signals
    SIGNAL_MANAGER_AVAILABLE = True
except ImportError:
    SIGNAL_MANAGER_AVAILABLE = False
    print("⚠️ Signal Manager não disponível")

# 🚨 NOVO IMPORT: Analisador de qualidade de stop loss
try:
    from core.stop_loss_analyzer import StopLossQualityAnalyzer, print_stop_loss_quality_report
    STOP_ANALYZER_AVAILABLE = True
except ImportError:
    STOP_ANALYZER_AVAILABLE = False
    print("⚠️ Stop Loss Analyzer não disponível")

# 🚨 NOVO IMPORT: Monitor de sinais
try:
    from core.signal_monitor import SignalStatusMonitor, print_signal_monitoring_report
    SIGNAL_MONITOR_AVAILABLE = True
except ImportError:
    SIGNAL_MONITOR_AVAILABLE = False
    print("⚠️ Signal Monitor não disponível")

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
        """Exibe banner do sistema OTIMIZADO"""
        banner = """
    +=================================================================+
    |                    TRADING ANALYZER v2.0                       |
    |              Sistema OTIMIZADO - Sinal Único                   |
    |                                                                 |
    |  🎯 SINAL ÚNICO: Máx 1 sinal ativo por crypto                  |
    |  ⚡ TIMEFRAMES: 5m (prioritário) + 15m                         |
    |  🛑 STOP TÉCNICO: ATR calculado automaticamente                |
    |  📊 INDICADORES: RSI + MACD (5m/15m)                           |
    |  📈 PADRÕES: Apenas Double Top/Bottom                          |
    |  🕯️ CANDLESTICKS: 43 padrões (alta confiança)                 |
    |  🧹 LIMPEZA AUTO: Move sinais inativos diariamente             |
    |  ⚖️ VALIDAÇÃO: Volume + Momentum + Microestrutura             |
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
    output.append(f"Total de sinais ativos: {general.get('total_active_signals', 0)}")
    output.append(f"Symbols com sinais: {general.get('symbols_with_signals', 0)}")
    output.append(f"Confiança média: {general.get('avg_confidence', 0):.3f}")
    output.append(f"Sinais criados hoje: {general.get('signals_today', 0)}")
    output.append(f"Sinais bloqueados hoje: {general.get('signals_blocked_today', 0)}")  # NOVO
    
    # Por timeframe
    by_timeframe = general.get('by_timeframe', {})
    if by_timeframe:
        output.append(f"\nPOR TIMEFRAME:")
        for timeframe, count in by_timeframe.items():
            output.append(f"  {timeframe}: {count} sinais ativos")
    
    # 🚨 NOVO: Estatísticas anti-spam
    anti_spam = data.get('anti_spam_stats', {})
    if anti_spam:
        output.append(f"\nSISTEMA ANTI-SPAM:")
        output.append(f"  Status: {anti_spam.get('system_status', 'UNKNOWN')}")
        output.append(f"  Máximo por symbol+timeframe: {anti_spam.get('max_allowed_per_symbol_timeframe', 1)}")
        output.append(f"  Maior concentração atual: {anti_spam.get('current_max_per_symbol', 0)}")
    
    return '\n'.join(output)

def format_output(data: dict, output_format: str) -> str:
    """Formata saída conforme solicitado - MELHORADO COM ANTI-SPAM"""
    if output_format == 'json':
        return json.dumps(data, indent=2, default=str, ensure_ascii=False)
    
    elif output_format == 'table':
        # Formato tabular para sistema anti-spam
        if 'symbol' in data and data.get('status') != 'error':
            # Resultado individual
            status = data['status']
            symbol = data['symbol']
            
            if status == 'blocked':
                # Symbol totalmente bloqueado
                blocked_tf = data.get('blocked_timeframes', [])
                active_count = data.get('active_signals_before', {})
                
                table = f"""
+================================================================+
|                    ANÁLISE BLOQUEADA                           |
+================================================================+

Symbol: {symbol}
Status: {status.upper()}
Motivo: {data.get('message', 'Todos os timeframes têm sinais ativos')}

SINAIS ATIVOS EXISTENTES:
"""
                for tf, count in active_count.items():
                    table += f"  • {tf}: {count} sinal(s) ativo(s)\n"
                
                table += f"""
TIMEFRAMES BLOQUEADOS: {blocked_tf}
TIMEFRAMES DISPONÍVEIS: {data.get('available_timeframes', [])}

RESULTADO:
  * Sinais Detectados: {data.get('signals_detected', 0)}
  * Sinais Validados: {data.get('signals_validated', 0)}
  * Sinais Salvos: {data.get('signals_saved', 0)}
  * Sinais Bloqueados: {data.get('signals_blocked', 0)}
                """.strip()
                return table
            
            else:
                # Análise normal
                table = f"""
+================================================================+
|                    ANÁLISE ANTI-SPAM                          |
+================================================================+

Symbol: {symbol}
Status: {status.upper()}

CONTROLE ANTI-SPAM:
  * Timeframes Disponíveis: {data.get('available_timeframes', [])}
  * Timeframes Bloqueados: {data.get('blocked_timeframes', [])}
  * Sinais Ativos Antes: {data.get('active_signals_before', {})}

RESULTADO:
  * Sinais Detectados: {data.get('signals_detected', 0)}
  * Sinais Validados: {data.get('signals_validated', 0)}
  * Sinais Salvos: {data.get('signals_saved', 0)}
  * Sinais Bloqueados: {data.get('signals_blocked', 0)}
                """.strip()
                return table
        
        elif '_summary' in data:
            # Múltiplos resultados
            output = []
            output.append("+" + "="*70 + "+")
            output.append("|" + " "*20 + "RESUMO ANTI-SPAM" + " "*20 + "|")
            output.append("+" + "="*70 + "+")
            
            for symbol, result in data.items():
                if symbol == '_summary':
                    continue
                    
                if isinstance(result, dict):
                    if result.get('status') == 'blocked':
                        status_icon = "🚫"
                        info = "BLOQUEADO"
                    elif result.get('status') == 'success':
                        signals_saved = result.get('signals_saved', 0)
                        signals_blocked = result.get('signals_blocked', 0)
                        if signals_saved > 0:
                            status_icon = "✅"
                            info = f"{signals_saved} SALVOS"
                        elif signals_blocked > 0:
                            status_icon = "⚠️"
                            info = f"{signals_blocked} BLOQUEADOS"
                        else:
                            status_icon = "✓"
                            info = "OK"
                    else:
                        status_icon = "❌"
                        info = "ERRO"
                    
                    blocked_tf = len(result.get('blocked_timeframes', []))
                    available_tf = len(result.get('available_timeframes', []))
                    
                    line = f"{status_icon} {symbol:8} | {info:12} | Bloq: {blocked_tf} | Disp: {available_tf}"
                    output.append(line)
                else:
                    output.append(f"❌ {symbol:8} | ERRO")
            
            # Resumo final
            summary = data.get('_summary', {})
            output.append("+" + "="*70 + "+")
            output.append(f"Total: {summary.get('successful_analyses', 0)}/{summary.get('symbols_analyzed', 0)} OK | {summary.get('total_signals_generated', 0)} salvos | {summary.get('total_signals_blocked', 0)} bloqueados | {summary.get('total_execution_time', 0):.1f}s")
            
            return '\n'.join(output)
        else:
            # Resultado de erro
            return f"ERRO: {data.get('message', 'Erro desconhecido')}"
    
    else:  # summary
        if 'symbol' in data:
            # Resultado individual
            symbol = data['symbol']
            status = data['status']
            
            if status == 'blocked':
                blocked_count = len(data.get('blocked_timeframes', []))
                available_count = len(data.get('available_timeframes', []))
                return f"🚫 {symbol}: BLOQUEADO | {blocked_count} TF ocupados, {available_count} disponíveis"
            
            else:
                signals_saved = data.get('signals_saved', 0)
                signals_blocked = data.get('signals_blocked', 0)
                available_tf = data.get('available_timeframes', [])
                
                if signals_saved > 0:
                    return f"✅ {symbol}: {signals_saved} sinais salvos | TF disponíveis: {available_tf}"
                elif signals_blocked > 0:
                    return f"⚠️ {symbol}: {signals_blocked} sinais bloqueados | TF disponíveis: {available_tf}"
                else:
                    return f"✓ {symbol}: OK | TF disponíveis: {available_tf}"
        
        elif '_summary' in data:
            # Múltiplos resultados
            summary = data.get('_summary', {})
            successful = summary.get('successful_analyses', 0)
            total = summary.get('symbols_analyzed', 0)
            total_signals = summary.get('total_signals_generated', 0)
            total_blocked = summary.get('total_signals_blocked', 0)
            exec_time = summary.get('total_execution_time', 0)
            
            return (
                f"Anti-Spam: {successful}/{total} symbols | "
                f"{total_signals} salvos, {total_blocked} bloqueados | {exec_time:.1f}s"
            )
        else:
            # Erro
            return f"ERRO: {data.get('message', 'Erro desconhecido')}"

def format_system_status(status: dict, output_format: str) -> str:
    """Formata status do sistema - COM ANTI-SPAM"""
    if output_format == 'json':
        return json.dumps(status, indent=2, default=str, ensure_ascii=False)
    
    elif output_format == 'table':
        output = []
        output.append("+" + "="*60 + "+")
        output.append("|" + " "*15 + "STATUS DO SISTEMA ANTI-SPAM" + " "*15 + "|")
        output.append("+" + "="*60 + "+")
        
        output.append(f"Status Geral: {status.get('status', 'unknown')}")
        output.append(f"Tipo: {status.get('system_type', 'unknown')}")
        output.append(f"Timestamp: {status.get('timestamp', 'N/A')}")
        
        output.append("\nCOMPONENTES:")
        components = status.get('components', {})
        for comp, stat in components.items():
            icon = "✅" if stat == 'OK' else "❌" if stat == 'ERROR' else "⚠️"
            output.append(f"  {icon} {comp}: {stat}")
        
        # 🚨 NOVO: Estatísticas de sinais
        signal_stats = status.get('signal_statistics', {})
        if signal_stats and 'error' not in signal_stats:
            output.append(f"\nSINAIS ATIVOS:")
            output.append(f"  Total: {signal_stats.get('total_active_signals', 0)}")
            output.append(f"  Symbols com sinais: {signal_stats.get('symbols_with_active_signals', 0)}")
            output.append(f"  Confiança média: {signal_stats.get('average_confidence', 0):.3f}")
            output.append(f"  Criados hoje: {signal_stats.get('signals_created_today', 0)}")
            output.append(f"  Bloqueados hoje: {signal_stats.get('signals_backed_up_today', 0)}")
            
            # Por timeframe
            by_tf = signal_stats.get('active_by_timeframe', {})
            if by_tf:
                output.append(f"  Por timeframe: {by_tf}")
            
            output.append(f"  Máx por symbol: {signal_stats.get('max_signals_per_symbol', 0)}")
        
        output.append(f"\nCONFIGURAÇÃO:")
        config = status.get('configuration', {})
        for key, value in config.items():
            output.append(f"  {key}: {value}")
        
        return '\n'.join(output)
    
    else:  # summary
        components_ok = sum(1 for stat in status.get('components', {}).values() if stat == 'OK')
        total_components = len(status.get('components', {}))
        signal_stats = status.get('signal_statistics', {})
        active_signals = signal_stats.get('total_active_signals', 0) if 'error' not in signal_stats else 0
        
        return (
            f"Sistema Anti-Spam: {status.get('status', 'unknown')} | "
            f"Componentes: {components_ok}/{total_components} OK | "
            f"Sinais ativos: {active_signals}"
        )

def main():
    """Função principal COM GERENCIAMENTO DE SINAIS"""
    parser = argparse.ArgumentParser(
        description="Trading Analyzer v2.0 - Sistema Anti-Spam COMPLETO",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python main.py --status                    # Status do sistema anti-spam + stops
  python main.py --analyze BTCUSDT           # Análise anti-spam de um symbol
  python main.py --analyze-all               # Análise anti-spam de todos os symbols
  python main.py --compare-signals           # Compara efetividade com stats anti-spam
  python main.py --continuous                # Execução contínua anti-spam
  python main.py --cleanup 7                 # Remove sinais antigos
  
  Exemplos de uso (OTIMIZADO - apenas 5m e 15m):
  python main.py --status                    # Status do sistema otimizado
  python main.py --analyze BTCUSDT           # Análise (5m prioritário)
  python main.py --analyze-all               # Análise de todos (sinal único)
  python main.py --continuous                # Execução contínua otimizada
  python main.py --cleanup 7                 # Remove sinais inativos
  
  🚨 GERENCIAMENTO DE SINAIS:
  python main.py --check-signals             # Lista todos os sinais ativos
  python main.py --check-signals BTCUSDT     # Sinais ativos do BTC
  python main.py --clear-signals BTCUSDT     # Limpa sinais do BTC
  python main.py --clear-signals BTCUSDT 5m  # Limpa sinal BTC 5m específico
  python main.py --clear-old-signals 24      # Desativa sinais > 24h
  
  🧠 ANÁLISE DE STOP LOSS:
  python main.py --analyze-stops             # Relatório de qualidade dos stops (7 dias)
  python main.py --analyze-stops --days 14   # Relatório dos últimos 14 dias
  
  📊 MONITORAMENTO DE SINAIS:
  python main.py --monitor-signals           # Verifica status de sinais ativos
  python main.py --update-signals            # Atualiza status baseado no preço atual
        """
    )
    
    # Comandos principais
    parser.add_argument('--status', action='store_true',
                       help='Mostra status do sistema anti-spam')
    
    parser.add_argument('--analyze', type=str, metavar='SYMBOL',
                       help='Análise anti-spam de um symbol (ex: BTCUSDT)')
    
    parser.add_argument('--analyze-all', action='store_true',
                       help='Análise anti-spam de todos os symbols configurados')
    
    parser.add_argument('--compare-signals', action='store_true',
                       help='Compara efetividade com estatísticas anti-spam')
    
    parser.add_argument('--continuous', action='store_true',
                       help='Execução contínua anti-spam')
    
    parser.add_argument('--cleanup', type=int, metavar='DAYS',
                       help='Remove sinais mais antigos que N dias')
    
    parser.add_argument('--check-active', action='store_true',
                       help='Mostra sinais ativos por símbolo')
    
    parser.add_argument('--check-symbols', action='store_true',
                       help='Verifica quais símbolos têm dados suficientes')
    
    # 🚨 NOVOS COMANDOS: Gerenciamento de sinais
    parser.add_argument('--check-signals', nargs='?', const='ALL', metavar='SYMBOL',
                       help='Lista sinais ativos (todos ou de um symbol específico)')
    
    parser.add_argument('--clear-signals', nargs='+', metavar=('SYMBOL', 'TIMEFRAME'),
                       help='Limpa sinais de um symbol (opcionalmente específico por timeframe)')
    
    parser.add_argument('--clear-old-signals', type=int, metavar='HOURS',
                       help='Desativa sinais mais antigos que N horas')
    
    # 🧠 NOVO COMANDO: Análise de qualidade de stop loss
    parser.add_argument('--analyze-stops', action='store_true',
                       help='Relatório de qualidade dos stop losses')
    
    # 📊 NOVOS COMANDOS: Monitoramento de sinais
    parser.add_argument('--monitor-signals', action='store_true',
                       help='Monitora status dos sinais ativos (sem atualizar)')
    
    parser.add_argument('--update-signals', action='store_true',
                       help='Verifica e atualiza status dos sinais baseado no preço atual')
    
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
        # 🚨 NOVOS COMANDOS DE GERENCIAMENTO
        if args.check_signals is not None:
            if not SIGNAL_MANAGER_AVAILABLE:
                print("❌ Signal Manager não disponível")
                sys.exit(1)
            
            if args.check_signals == 'ALL':
                if not args.quiet:
                    print("Verificando todos os sinais ativos...")
                print_active_signals_table()
            else:
                symbol = args.check_signals.upper()
                if not args.quiet:
                    print(f"Verificando sinais ativos para {symbol}...")
                print_active_signals_table(symbol)
            return
        
        elif args.clear_signals:
            if not SIGNAL_MANAGER_AVAILABLE:
                print("❌ Signal Manager não disponível")
                sys.exit(1)
            
            symbol = args.clear_signals[0].upper()
            timeframe = args.clear_signals[1] if len(args.clear_signals) > 1 else None
            
            if not args.quiet:
                if timeframe:
                    print(f"Limpando sinais de {symbol} {timeframe}...")
                else:
                    print(f"Limpando todos os sinais de {symbol}...")
            
            clear_symbol_signals(symbol, timeframe)
            return
        
        elif args.clear_old_signals is not None:
            if not SIGNAL_MANAGER_AVAILABLE:
                print("❌ Signal Manager não disponível")
                sys.exit(1)
            
            hours = args.clear_old_signals
            if not args.quiet:
                print(f"Desativando sinais mais antigos que {hours} horas...")
            
            manager = SignalManager()
            cleared = manager.deactivate_old_signals(hours, "manual_cleanup_command")
            print(f"🔴 {cleared} sinais antigos desativados")
            return
        
        elif args.analyze_stops:
            # 🧠 NOVO: Análise de qualidade dos stop losses
            if not STOP_ANALYZER_AVAILABLE:
                print("❌ Stop Loss Analyzer não disponível")
                sys.exit(1)
            
            days = args.days
            if not args.quiet:
                print(f"Analisando qualidade dos stop losses dos últimos {days} dias...")
            
            if args.output == 'json':
                analyzer = StopLossQualityAnalyzer()
                report = analyzer.get_stop_loss_quality_report(days)
                print(json.dumps(report, indent=2, default=str, ensure_ascii=False))
            else:
                print_stop_loss_quality_report(days)
            return
        
        elif args.monitor_signals:
            # 📊 NOVO: Monitoramento de sinais (sem atualizar)
            if not SIGNAL_MONITOR_AVAILABLE:
                print("❌ Signal Monitor não disponível")
                sys.exit(1)
            
            if not args.quiet:
                print("Verificando status dos sinais ativos...")
            
            if args.output == 'json':
                monitor = SignalStatusMonitor()
                results = monitor.check_active_signals(update_status=False)
                print(json.dumps(results, indent=2, default=str, ensure_ascii=False))
            else:
                print_signal_monitoring_report()
            return
        
        elif args.update_signals:
            # 📊 NOVO: Atualização de status dos sinais
            if not SIGNAL_MONITOR_AVAILABLE:
                print("❌ Signal Monitor não disponível")
                sys.exit(1)
            
            if not args.quiet:
                print("Verificando e atualizando status dos sinais...")
            
            monitor = SignalStatusMonitor()
            results = monitor.check_active_signals(update_status=True)
            
            if 'error' in results:
                print(f"❌ Erro: {results['error']}")
            else:
                checked = results.get('signals_checked', 0)
                updated = results.get('signals_updated', 0)
                print(f"✅ {checked} sinais verificados | {updated} atualizados")
                
                if args.output == 'json':
                    print(json.dumps(results, indent=2, default=str, ensure_ascii=False))
            return
        
        # Inicializa o analisador ANTI-SPAM
        if not args.quiet:
            print("Inicializando Trading Analyzer Anti-Spam...")
        
        analyzer = TradingAnalyzer()
        
        # Executa comando solicitado
        if args.status:
            # Mostra status do sistema anti-spam
            if not args.quiet:
                print("Verificando status do sistema anti-spam...")
            
            status = analyzer.get_system_status()
            print(format_system_status(status, args.output))
        
        elif args.analyze:
            # Analisa symbol específico com sistema anti-spam
            symbol = args.analyze.upper()
            if not args.quiet:
                print(f"Iniciando análise anti-spam: {symbol}...")
            
            result = analyzer.analyze_symbol(symbol, args.timeframe)
            print(format_output(result, args.output))
        
        elif args.analyze_all:
            # Analisa todos os symbols com sistema anti-spam
            symbols = args.symbols if args.symbols else None
            if not args.quiet:
                symbols_desc = f"{len(args.symbols)} symbols especificados" if symbols else "todos os symbols configurados"
                print(f"Iniciando análise anti-spam: {symbols_desc}...")
            
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
            # Modo contínuo anti-spam
            interval = args.interval if args.interval else settings.system.analysis_interval
            
            if not args.quiet:
                print(f"Iniciando análise contínua anti-spam (intervalo: {interval}s)")
                print("Pressione Ctrl+C para parar\n")
            
            analyzer.run_continuous_multi_timeframe_analysis(interval)
        
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
        
        elif args.check_active:
            # Verifica sinais ativos
            symbols = settings.get_analysis_symbols()
            active_summary = {}
            
            for symbol in symbols:
                try:
                    count = analyzer.signal_writer.get_active_signals_count(symbol)
                    if count > 0:
                        active_summary[symbol] = count
                except Exception:
                    pass
            
            if active_summary:
                print("📊 SINAIS ATIVOS:")
                for symbol, count in active_summary.items():
                    print(f"  {symbol}: {count} sinal(s)")
                print(f"\nTotal: {sum(active_summary.values())} sinais ativos")
            else:
                print("✅ Nenhum sinal ativo encontrado")
        
        elif args.check_symbols:
            # Verifica disponibilidade de dados por símbolo
            print("🔍 Verificando disponibilidade de dados por símbolo...\n")
            
            all_symbols = settings.get_analysis_symbols()
            data_reader = DataReader()
            
            for symbol in all_symbols:
                result = data_reader.check_symbol_data_availability(symbol)
                status_icon = "✅" if result['has_sufficient_data'] else "❌"
                
                print(f"{status_icon} {symbol}:")
                for tf, data in result['timeframes'].items():
                    count = data['count']
                    sufficient = "✓" if data['sufficient'] else "✗"
                    print(f"    {tf}: {count} registros {sufficient}")
                print()
        
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