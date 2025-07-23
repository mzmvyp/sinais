"""
Trading Analyzer - SISTEMA ANTI-SPAM COMPLETO - VERSÃO ROBUSTA
Máximo 1 sinal ativo por symbol+timeframe + Proteção anti-travamento
"""
import argparse
import sys
import json
import os
import signal
import time
from datetime import datetime
from typing import Optional
import logging

from core.data_reader import DataReader

# Configuração de encoding para Windows
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'

def timeout_handler(signum, frame):
    """Handler para timeout - apenas Unix"""
    raise TimeoutError("Operação excedeu tempo limite")

def run_with_timeout(func, args, timeout_seconds=30):
    """Executa função com timeout (Unix) ou fallback simples (Windows)"""
    if sys.platform.startswith('win'):
        # Windows: execução simples sem timeout por signal
        start_time = time.time()
        try:
            result = func(*args)
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                logging.warning(f"Operação demorou {elapsed:.1f}s (limite: {timeout_seconds}s)")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logging.error(f"Erro após {elapsed:.1f}s: {e}")
            raise
    else:
        # Unix: usa signal para timeout real
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)
        try:
            result = func(*args)
            signal.alarm(0)
            return result
        except TimeoutError:
            logging.error(f"Timeout de {timeout_seconds}s excedido")
            raise
        finally:
            signal.signal(signal.SIGALRM, old_handler)

# Imports do sistema UNIFICADO
try:
    from core.analyzer import TradingAnalyzer
    from config.settings import settings
    ANALYZER_AVAILABLE = True
except ImportError as e:
    print(f"❌ Erro crítico ao importar analyzer: {e}")
    ANALYZER_AVAILABLE = False

# 🚨 IMPORTS OPCIONAIS COM PROTEÇÃO
try:
    from core.signal_manager import SignalManager, print_active_signals_table, clear_symbol_signals
    SIGNAL_MANAGER_AVAILABLE = True
except ImportError:
    SIGNAL_MANAGER_AVAILABLE = False
    print("⚠️ Signal Manager não disponível")

try:
    from core.stop_loss_analyzer import StopLossQualityAnalyzer, print_stop_loss_quality_report
    STOP_ANALYZER_AVAILABLE = True
except ImportError:
    STOP_ANALYZER_AVAILABLE = False
    print("⚠️ Stop Loss Analyzer não disponível")

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
                logging.FileHandler("trading_analyzer_robust.log", encoding='utf-8')
            ]
        )
    else:
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("trading_analyzer_robust.log")
            ]
        )

def print_banner():
    """Exibe banner do sistema OTIMIZADO E ROBUSTO"""
    banner = """
+=================================================================+
|                    TRADING ANALYZER v2.0.1                     |
|              Sistema OTIMIZADO - Anti-Travamento               |
|                                                                 |
|  🎯 SINAL ÚNICO: Máx 1 sinal ativo por crypto                  |
|  ⚡ TIMEFRAMES: 5m (prioritário) + 15m APENAS                  |
|  🛑 STOP TÉCNICO: ATR calculado automaticamente                |
|  📊 INDICADORES: RSI + MACD (5m/15m)                           |
|  📈 PADRÕES: Apenas Double Top/Bottom                          |
|  🕯️ CANDLESTICKS: 43 padrões (alta confiança)                 |
|  🧹 LIMPEZA AUTO: Move sinais inativos diariamente             |
|  ⚖️ VALIDAÇÃO: Volume + Momentum + Microestrutura             |
|  🛡️ PROTEÇÃO: Timeout + Cache + Validação robusta             |
+=================================================================+
    """
    print(banner)

def safe_execute(func, args=(), kwargs=None, timeout=30, operation_name="Operação"):
    """Executa função de forma segura com timeout e error handling"""
    if kwargs is None:
        kwargs = {}
    
    start_time = time.time()
    logging.info(f"Iniciando {operation_name}...")
    
    try:
        if sys.platform.startswith('win'):
            # Windows: timeout simples
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            
            if elapsed > timeout:
                logging.warning(f"{operation_name} demorou {elapsed:.1f}s (limite: {timeout}s)")
            else:
                logging.info(f"{operation_name} concluída em {elapsed:.1f}s")
            
            return result
        else:
            # Unix: timeout com signal
            result = run_with_timeout(lambda: func(*args, **kwargs), (), timeout)
            elapsed = time.time() - start_time
            logging.info(f"{operation_name} concluída em {elapsed:.1f}s")
            return result
            
    except TimeoutError:
        elapsed = time.time() - start_time
        error_msg = f"{operation_name} TIMEOUT após {elapsed:.1f}s"
        logging.error(error_msg)
        return {'status': 'timeout', 'message': error_msg}
    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = f"{operation_name} ERRO após {elapsed:.1f}s: {e}"
        logging.error(error_msg)
        return {'status': 'error', 'message': str(e)}

def format_output_safe(data: dict, output_format: str) -> str:
    """Formata saída de forma segura"""
    try:
        if output_format == 'json':
            return json.dumps(data, indent=2, default=str, ensure_ascii=False)
        
        elif output_format == 'table':
            # Formato simplificado para evitar problemas
            if 'error' in data or 'status' in data and data['status'] in ['error', 'timeout']:
                return f"ERRO: {data.get('message', 'Erro desconhecido')}"
            
            # Resultado básico
            if 'symbol' in data:
                symbol = data['symbol']
                status = data.get('status', 'unknown')
                signals_saved = data.get('signals_saved', 0)
                return f"{symbol}: {status} - {signals_saved} sinais salvos"
            
            return str(data)
        
        else:  # summary
            if 'error' in data or 'status' in data and data['status'] in ['error', 'timeout']:
                return f"ERRO: {data.get('message', 'Erro desconhecido')}"
            
            if 'symbol' in data:
                symbol = data['symbol']
                signals_saved = data.get('signals_saved', 0)
                return f"{symbol}: {signals_saved} sinais"
            
            return "Operação concluída"
            
    except Exception as e:
        return f"Erro na formatação: {e}"

def initialize_analyzer_safe():
    """Inicializa analyzer de forma segura"""
    if not ANALYZER_AVAILABLE:
        return None
    
    try:
        logging.info("Inicializando Trading Analyzer...")
        analyzer = TradingAnalyzer()
        logging.info("Trading Analyzer inicializado com sucesso")
        return analyzer
    except Exception as e:
        logging.error(f"Erro ao inicializar analyzer: {e}")
        return None

def main():
    """Função principal COM PROTEÇÃO ANTI-TRAVAMENTO"""
    parser = argparse.ArgumentParser(
        description="Trading Analyzer v2.0.1 - Sistema Anti-Travamento COMPLETO",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso ROBUSTOS:
  python main.py --status                    # Status do sistema (timeout: 10s)
  python main.py --analyze BTCUSDT           # Análise de um symbol (timeout: 30s)
  python main.py --analyze-all               # Análise de todos (timeout: 300s)
  python main.py --continuous                # Execução contínua robusta
  python main.py --check-signals             # Lista sinais ativos
  python main.py --clear-signals BTCUSDT     # Limpa sinais
  python main.py --timeout 60 --analyze BTC  # Define timeout customizado
        """
    )
    
    # Comandos principais
    parser.add_argument('--status', action='store_true',
                       help='Status do sistema')
    
    parser.add_argument('--analyze', type=str, metavar='SYMBOL',
                       help='Análise de um symbol')
    
    parser.add_argument('--analyze-all', action='store_true',
                       help='Análise de todos os symbols')
    
    parser.add_argument('--continuous', action='store_true',
                       help='Execução contínua')
    
    parser.add_argument('--check-signals', nargs='?', const='ALL', metavar='SYMBOL',
                       help='Lista sinais ativos')
    
    parser.add_argument('--clear-signals', nargs='+', metavar=('SYMBOL', 'TIMEFRAME'),
                       help='Limpa sinais')
    
    parser.add_argument('--analyze-stops', action='store_true',
                       help='Análise de stop losses')
    
    parser.add_argument('--monitor-signals', action='store_true',
                       help='Monitora sinais')
    
    parser.add_argument('--update-signals', action='store_true',
                       help='Atualiza status dos sinais')
    
    # Opções de configuração
    parser.add_argument('--timeout', type=int, default=30,
                       help='Timeout em segundos (padrão: 30)')
    
    parser.add_argument('--output', type=str, choices=['json', 'table', 'summary'],
                       default='summary', help='Formato de saída')
    
    parser.add_argument('--log-level', type=str, 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Nível de log')
    
    parser.add_argument('--quiet', action='store_true',
                       help='Modo silencioso')
    
    parser.add_argument('--safe-mode', action='store_true',
                       help='Modo seguro com timeouts reduzidos')
    
    args = parser.parse_args()
    
    # Ajusta timeout para modo seguro
    if args.safe_mode:
        args.timeout = min(args.timeout, 15)
        print("Modo seguro ativado - timeouts reduzidos")
    
    # Configura nível de log
    log_level = 'ERROR' if args.quiet else args.log_level
    setup_logging(log_level)
    
    # Exibe banner se não estiver em modo silencioso
    if not args.quiet:
        print_banner()
    
    try:
        # COMANDOS DE GERENCIAMENTO (sem analyzer)
        if args.check_signals is not None:
            if not SIGNAL_MANAGER_AVAILABLE:
                print("❌ Signal Manager não disponível")
                sys.exit(1)
            
            def run_check_signals():
                if args.check_signals == 'ALL':
                    print_active_signals_table()
                else:
                    print_active_signals_table(args.check_signals.upper())
                return {'status': 'success'}
            
            result = safe_execute(run_check_signals, timeout=10, operation_name="Verificação de sinais")
            if 'status' in result and result['status'] != 'success':
                print(format_output_safe(result, args.output))
                sys.exit(1)
            return
        
        elif args.clear_signals:
            if not SIGNAL_MANAGER_AVAILABLE:
                print("❌ Signal Manager não disponível")
                sys.exit(1)
            
            symbol = args.clear_signals[0].upper()
            timeframe = args.clear_signals[1] if len(args.clear_signals) > 1 else None
            
            def run_clear_signals():
                clear_symbol_signals(symbol, timeframe)
                return {'status': 'success', 'message': f'Sinais limpos para {symbol}'}
            
            result = safe_execute(run_clear_signals, timeout=5, operation_name="Limpeza de sinais")
            print(format_output_safe(result, args.output))
            return
        
        elif args.analyze_stops:
            if not STOP_ANALYZER_AVAILABLE:
                print("❌ Stop Loss Analyzer não disponível")
                sys.exit(1)
            
            def run_analyze_stops():
                if args.output == 'json':
                    analyzer = StopLossQualityAnalyzer()
                    return analyzer.get_stop_loss_quality_report(7)
                else:
                    print_stop_loss_quality_report(7)
                    return {'status': 'success'}
            
            result = safe_execute(run_analyze_stops, timeout=20, operation_name="Análise de stops")
            if args.output == 'json':
                print(format_output_safe(result, args.output))
            return
        
        elif args.monitor_signals:
            if not SIGNAL_MONITOR_AVAILABLE:
                print("❌ Signal Monitor não disponível")
                sys.exit(1)
            
            def run_monitor_signals():
                if args.output == 'json':
                    monitor = SignalStatusMonitor()
                    return monitor.check_active_signals(update_status=False)
                else:
                    print_signal_monitoring_report()
                    return {'status': 'success'}
            
            result = safe_execute(run_monitor_signals, timeout=15, operation_name="Monitoramento de sinais")
            if args.output == 'json':
                print(format_output_safe(result, args.output))
            return
        
        elif args.update_signals:
            if not SIGNAL_MONITOR_AVAILABLE:
                print("❌ Signal Monitor não disponível")
                sys.exit(1)
            
            def run_update_signals():
                monitor = SignalStatusMonitor()
                return monitor.check_active_signals(update_status=True)
            
            result = safe_execute(run_update_signals, timeout=30, operation_name="Atualização de sinais")
            
            if 'error' in result:
                print(f"❌ Erro: {result['error']}")
            else:
                checked = result.get('signals_checked', 0)
                updated = result.get('signals_updated', 0)
                print(f"✅ {checked} sinais verificados | {updated} atualizados")
                
                if args.output == 'json':
                    print(format_output_safe(result, args.output))
            return
        
        # COMANDOS QUE PRECISAM DO ANALYZER
        if not ANALYZER_AVAILABLE:
            print("❌ Trading Analyzer não disponível - verifique as dependências")
            sys.exit(1)
        
        # Inicializa o analisador de forma segura
        analyzer = safe_execute(initialize_analyzer_safe, timeout=10, operation_name="Inicialização do analyzer")
        
        if analyzer is None or (isinstance(analyzer, dict) and 'status' in analyzer):
            print("❌ Falha ao inicializar Trading Analyzer")
            if isinstance(analyzer, dict):
                print(format_output_safe(analyzer, args.output))
            sys.exit(1)
        
        # Executa comando solicitado com proteção
        if args.status:
            result = safe_execute(analyzer.get_system_status, timeout=args.timeout, operation_name="Status do sistema")
            print(format_output_safe(result, args.output))
        
        elif args.analyze:
            symbol = args.analyze.upper()
            result = safe_execute(analyzer.analyze_symbol, (symbol,), timeout=args.timeout, operation_name=f"Análise de {symbol}")
            print(format_output_safe(result, args.output))
        
        elif args.analyze_all:
            result = safe_execute(analyzer.analyze_multiple_symbols, timeout=args.timeout*10, operation_name="Análise de todos os symbols")
            print(format_output_safe(result, args.output))
        
        elif args.continuous:
            if not args.quiet:
                print(f"Iniciando análise contínua ROBUSTA (timeout por ciclo: {args.timeout}s)")
                print("Pressione Ctrl+C para parar\n")
            
            try:
                # Análise contínua com proteção
                analyzer.run_continuous_multi_timeframe_analysis()
            except KeyboardInterrupt:
                print("\n🛑 Análise interrompida pelo usuário")
            except Exception as e:
                print(f"\n❌ Erro na análise contínua: {e}")
        
        else:
            print("ERRO: Nenhum comando especificado. Use --help para ver opções disponíveis.")
            parser.print_help()
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nOperação interrompida pelo usuário")
        sys.exit(0)
    
    except ImportError as e:
        print(f"ERRO de Importação: {e}")
        print("Verifique se todos os módulos estão instalados corretamente.")
        sys.exit(1)
    
    except Exception as e:
        print(f"ERRO CRÍTICO: {e}")
        if not args.quiet:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()