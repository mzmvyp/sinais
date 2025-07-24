"""
Trading Analyzer - SISTEMA COMPLETO CORRIGIDO
Máximo 1 sinal ativo por symbol + Lógica de Status Corrigida
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

# 🚨 IMPORTS CORRIGIDOS DO SISTEMA
try:
    from core.analyzer import MultiTimeframeAnalyzer
    ANALYZER_AVAILABLE = True
    print("✅ MultiTimeframeAnalyzer importado com sucesso")
except ImportError as e:
    print(f"❌ Erro crítico ao importar analyzer: {e}")
    ANALYZER_AVAILABLE = False

try:
    from config.settings import settings
    SETTINGS_AVAILABLE = True
except ImportError as e:
    print(f"❌ Erro ao importar settings: {e}")
    SETTINGS_AVAILABLE = False

# 🚨 IMPORTS OPCIONAIS COM PROTEÇÃO
try:
    from core.signal_manager import SignalManager, print_active_signals_table, clear_symbol_signals
    SIGNAL_MANAGER_AVAILABLE = True
    print("✅ Signal Manager disponível")
except ImportError:
    SIGNAL_MANAGER_AVAILABLE = False
    print("⚠️ Signal Manager não disponível")

try:
    from core.signal_monitor import SignalStatusMonitor, print_signal_monitoring_report
    SIGNAL_MONITOR_AVAILABLE = True
    print("✅ Signal Monitor disponível")
except ImportError:
    SIGNAL_MONITOR_AVAILABLE = False
    print("⚠️ Signal Monitor não disponível")

# Outros imports opcionais
try:
    from core.stop_loss_analyzer import StopLossQualityAnalyzer, print_stop_loss_quality_report
    STOP_ANALYZER_AVAILABLE = True
except ImportError:
    STOP_ANALYZER_AVAILABLE = False

try:
    from core.targets_analyzer import TargetsQualityAnalyzer, print_targets_quality_report
    TARGETS_ANALYZER_AVAILABLE = True
except ImportError:
    TARGETS_ANALYZER_AVAILABLE = False

try:
    from config.stop_loss_config import print_current_config as print_stop_config
    from config.targets_config import print_targets_config
    ADVANCED_CONFIG_AVAILABLE = True
except ImportError:
    ADVANCED_CONFIG_AVAILABLE = False

def setup_logging(log_level: str):
    """Configura sistema de logging"""
    if sys.platform.startswith('win'):
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("trading_analyzer_complete.log", encoding='utf-8')
            ]
        )
    else:
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("trading_analyzer_complete.log")
            ]
        )

def print_banner():
    """Exibe banner do sistema CORRIGIDO"""
    banner = """
+=================================================================+
|                    TRADING ANALYZER v2.1.0                     |
|              Sistema COMPLETO - LÓGICA CORRIGIDA               |
|                                                                 |
|  🚨 CORREÇÕES APLICADAS:                                        |
|  ✅ Novos sinais → SEMPRE ACTIVE                               |
|  ✅ Estados bloqueadores → ACTIVE, TARGET_1_HIT                |
|  ✅ Estados finalizados → TARGET_2_HIT, STOP_HIT, EXPIRED      |
|  ✅ Fluxo → ACTIVE → TARGET_1_HIT → TARGET_2_HIT/STOP_HIT      |
|  ✅ Targets → Exatamente 2 targets por sinal                   |
|                                                                 |
|  🎯 CARACTERÍSTICAS:                                            |
|  • Máx 1 sinal ativo por crypto                                |
|  • Timeframes: 5m (prioritário) + 15m                          |
|  • Stop Loss e Targets técnicos                                |
|  • Validação robusta com proteção anti-travamento              |
|  • Monitoramento e gerenciamento de sinais                     |
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
            if 'error' in data or 'status' in data and data['status'] in ['error', 'timeout']:
                return f"ERRO: {data.get('message', 'Erro desconhecido')}"
            
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
    """🚨 CORRIGIDO: Inicializa MultiTimeframeAnalyzer"""
    if not ANALYZER_AVAILABLE:
        return None
    
    try:
        logging.info("Inicializando MultiTimeframeAnalyzer...")
        analyzer = MultiTimeframeAnalyzer()  # 🚨 CORRIGIDO
        logging.info("MultiTimeframeAnalyzer inicializado com sucesso")
        return analyzer
    except Exception as e:
        logging.error(f"Erro ao inicializar analyzer: {e}")
        return None

def main():
    """Função principal CORRIGIDA"""
    parser = argparse.ArgumentParser(
        description="Trading Analyzer v2.1.0 - Sistema Completo CORRIGIDO",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso CORRIGIDOS:

🔍 ANÁLISE:
  python main.py --status                    # Status do sistema (timeout: 10s)
  python main.py --analyze BTCUSDT           # Análise de um symbol (timeout: 30s)
  python main.py --analyze-all               # Análise de todos (timeout: 300s)
  python main.py --continuous                # Execução contínua robusta

📊 GERENCIAMENTO DE SINAIS CORRIGIDO:
  python main.py --check-signals             # Lista sinais BLOQUEADORES
  python main.py --check-signals BTCUSDT     # Sinais bloqueadores de um symbol
  python main.py --clear-signals BTCUSDT     # Limpa sinais bloqueadores
  python main.py --clear-signals BTCUSDT 5m  # Limpa sinal específico

📈 MONITORAMENTO:
  python main.py --monitor-signals           # Monitora status dos sinais
  python main.py --update-signals            # Atualiza status automaticamente

🛑 ANÁLISE DE QUALIDADE:
  python main.py --analyze-stops             # Relatório de stop losses
  python main.py --analyze-targets           # Relatório de targets

⚙️ CONFIGURAÇÕES:
  python main.py --show-stop-config          # Mostra config de stop loss
  python main.py --show-targets-config       # Mostra config de targets

🔧 OPÇÕES:
  python main.py --timeout 60 --analyze BTC  # Define timeout customizado
  python main.py --output json --status      # Saída em JSON
  python main.py --safe-mode --analyze-all   # Modo seguro
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
                       help='Lista sinais bloqueadores')
    
    parser.add_argument('--clear-signals', nargs='+', metavar=('SYMBOL', 'TIMEFRAME'),
                       help='Limpa sinais bloqueadores')
    
    # Comandos de análise técnica
    parser.add_argument('--analyze-stops', action='store_true',
                       help='Análise de qualidade dos stop losses')
    
    parser.add_argument('--analyze-targets', action='store_true',
                       help='Análise de qualidade dos targets')
    
    parser.add_argument('--monitor-signals', action='store_true',
                       help='Monitora sinais')
    
    parser.add_argument('--update-signals', action='store_true',
                       help='Atualiza status dos sinais')
    
    # Comandos de configuração
    parser.add_argument('--show-stop-config', action='store_true',
                       help='Mostra configuração de stop loss')
    
    parser.add_argument('--show-targets-config', action='store_true',
                       help='Mostra configuração de targets')
    
    # Opções de configuração
    parser.add_argument('--days', type=int, default=7,
                       help='Número de dias para análise (padrão: 7)')
    
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
        # COMANDOS DE CONFIGURAÇÃO (sem analyzer)
        if args.show_stop_config:
            if not ADVANCED_CONFIG_AVAILABLE:
                print("❌ Configurações avançadas não disponíveis")
                sys.exit(1)
            
            def run_show_stop_config():
                print_stop_config()
                return {'status': 'success'}
            
            result = safe_execute(run_show_stop_config, timeout=5, operation_name="Configuração de stop loss")
            return
        
        elif args.show_targets_config:
            if not ADVANCED_CONFIG_AVAILABLE:
                print("❌ Configurações avançadas não disponíveis")
                sys.exit(1)
            
            def run_show_targets_config():
                print_targets_config()
                return {'status': 'success'}
            
            result = safe_execute(run_show_targets_config, timeout=5, operation_name="Configuração de targets")
            return
        
        # COMANDOS DE GERENCIAMENTO (sem analyzer)
        elif args.check_signals is not None:
            if not SIGNAL_MANAGER_AVAILABLE:
                print("❌ Signal Manager não disponível")
                sys.exit(1)
            
            def run_check_signals():
                if args.check_signals == 'ALL':
                    print_active_signals_table()
                else:
                    print_active_signals_table(args.check_signals.upper())
                return {'status': 'success'}
            
            result = safe_execute(run_check_signals, timeout=10, operation_name="Verificação de sinais bloqueadores")
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
                return {'status': 'success', 'message': f'Sinais bloqueadores limpos para {symbol}'}
            
            result = safe_execute(run_clear_signals, timeout=5, operation_name="Limpeza de sinais bloqueadores")
            print(format_output_safe(result, args.output))
            return
        
        # COMANDOS DE ANÁLISE TÉCNICA
        elif args.analyze_stops:
            if not STOP_ANALYZER_AVAILABLE:
                print("❌ Stop Loss Analyzer não disponível")
                sys.exit(1)
            
            def run_analyze_stops():
                if args.output == 'json':
                    analyzer = StopLossQualityAnalyzer()
                    return analyzer.get_stop_loss_quality_report(args.days)
                else:
                    print_stop_loss_quality_report(args.days)
                    return {'status': 'success'}
            
            result = safe_execute(run_analyze_stops, timeout=20, operation_name="Análise de stops")
            if args.output == 'json':
                print(format_output_safe(result, args.output))
            return
        
        elif args.analyze_targets:
            if not TARGETS_ANALYZER_AVAILABLE:
                print("❌ Targets Analyzer não disponível")
                sys.exit(1)
            
            def run_analyze_targets():
                if args.output == 'json':
                    analyzer = TargetsQualityAnalyzer()
                    return analyzer.get_targets_quality_report(args.days)
                else:
                    print_targets_quality_report(args.days)
                    return {'status': 'success'}
            
            result = safe_execute(run_analyze_targets, timeout=20, operation_name="Análise de targets")
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
            print("❌ MultiTimeframeAnalyzer não disponível - verifique as dependências")
            sys.exit(1)
        
        # Inicializa o analisador de forma segura
        analyzer = safe_execute(initialize_analyzer_safe, timeout=10, operation_name="Inicialização do analyzer")
        
        if analyzer is None or (isinstance(analyzer, dict) and 'status' in analyzer):
            print("❌ Falha ao inicializar MultiTimeframeAnalyzer")
            if isinstance(analyzer, dict):
                print(format_output_safe(analyzer, args.output))
            sys.exit(1)
        
        # Executa comando solicitado com proteção
        if args.status:
            result = safe_execute(analyzer.get_system_status, timeout=args.timeout, operation_name="Status do sistema")
            print(format_output_safe(result, args.output))
        
        elif args.analyze:
            symbol = args.analyze.upper()
            result = safe_execute(analyzer.analyze_symbol_all_timeframes, (symbol,), timeout=args.timeout, operation_name=f"Análise de {symbol}")
            print(format_output_safe(result, args.output))
        
        elif args.analyze_all:
            result = safe_execute(analyzer.analyze_multiple_symbols, timeout=args.timeout*10, operation_name="Análise de todos os symbols")
            print(format_output_safe(result, args.output))
        
        elif args.continuous:
            if not args.quiet:
                print(f"Iniciando análise contínua CORRIGIDA (timeout por ciclo: {args.timeout}s)")
                print("Estados: ACTIVE → TARGET_1_HIT → TARGET_2_HIT/STOP_HIT")
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