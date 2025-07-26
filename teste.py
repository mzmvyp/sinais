# signal_diagnostic_tool.py
"""
FERRAMENTA DE DIAGNÓSTICO DO SISTEMA DE SINAIS
Identifica exatamente onde estão os problemas na geração de sinais
"""

import sys
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import traceback

# Configura logging para capturar tudo
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("signal_diagnosis.log")
    ]
)

class SignalSystemDiagnostic:
    """Diagnóstica o sistema de sinais passo a passo"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.diagnosis_report = {
            'timestamp': datetime.now().isoformat(),
            'tests_performed': [],
            'issues_found': [],
            'recommendations': [],
            'detailed_results': {}
        }
    
    def run_complete_diagnosis(self, symbol: str = "BTCUSDT") -> Dict:
        """Executa diagnóstico completo do sistema"""
        
        print("🔍 INICIANDO DIAGNÓSTICO COMPLETO DO SISTEMA DE SINAIS")
        print("=" * 70)
        
        # Teste 1: Importações e dependências
        self._test_imports()
        
        # Teste 2: Configurações
        self._test_configurations()
        
        # Teste 3: Conexão com banco de dados
        self._test_database_connection()
        
        # Teste 4: Disponibilidade de dados
        self._test_data_availability(symbol)
        
        # Teste 5: Geração de sinais passo a passo
        self._test_signal_generation_pipeline(symbol)
        
        # Teste 6: Validações e filtros
        self._test_validation_pipeline(symbol)
        
        # Gera relatório final
        self._generate_final_report()
        
        return self.diagnosis_report
    
    def _test_imports(self):
        """Testa todas as importações necessárias"""
        print("\n📦 TESTE 1: IMPORTAÇÕES E DEPENDÊNCIAS")
        print("-" * 40)
        
        import_tests = {
            'core.analyzer': None,
            'core.data_reader': None,
            'core.signal_writer': None,
            'indicators.technical': None,
            'indicators.candlestick_patterns_detector': None,
            'config.settings': None
        }
        
        for module_name in import_tests.keys():
            try:
                __import__(module_name)
                import_tests[module_name] = "✅ OK"
                print(f"   {module_name}: ✅ OK")
            except ImportError as e:
                import_tests[module_name] = f"❌ ERRO: {e}"
                print(f"   {module_name}: ❌ ERRO - {e}")
                self.diagnosis_report['issues_found'].append(f"Import error: {module_name} - {e}")
        
        self.diagnosis_report['detailed_results']['imports'] = import_tests
        self.diagnosis_report['tests_performed'].append('imports')
    
    def _test_configurations(self):
        """Testa configurações do sistema"""
        print("\n⚙️ TESTE 2: CONFIGURAÇÕES")
        print("-" * 30)
        
        try:
            from config.settings import settings
            
            # Testa configurações críticas
            config_tests = {}
            
            # Timeframes habilitados
            try:
                timeframes = settings.get_enabled_timeframes()
                config_tests['enabled_timeframes'] = f"✅ {timeframes}"
                print(f"   Timeframes habilitados: ✅ {timeframes}")
            except Exception as e:
                config_tests['enabled_timeframes'] = f"❌ {e}"
                print(f"   Timeframes habilitados: ❌ {e}")
            
            # Símbolos de análise
            try:
                symbols = settings.get_analysis_symbols()
                config_tests['analysis_symbols'] = f"✅ {len(symbols)} símbolos"
                print(f"   Símbolos de análise: ✅ {len(symbols)} símbolos")
            except Exception as e:
                config_tests['analysis_symbols'] = f"❌ {e}"
                print(f"   Símbolos de análise: ❌ {e}")
            
            # Configurações de indicadores
            try:
                rsi_levels = settings.get_rsi_levels("5m")
                config_tests['rsi_config'] = f"✅ Overbought: {rsi_levels['overbought']}, Oversold: {rsi_levels['oversold']}"
                print(f"   RSI Config: ✅ OB: {rsi_levels['overbought']}, OS: {rsi_levels['oversold']}")
            except Exception as e:
                config_tests['rsi_config'] = f"❌ {e}"
                print(f"   RSI Config: ❌ {e}")
            
            self.diagnosis_report['detailed_results']['configurations'] = config_tests
            
        except ImportError as e:
            self.diagnosis_report['issues_found'].append(f"Configuration error: {e}")
            print(f"   ❌ Não foi possível importar settings: {e}")
        
        self.diagnosis_report['tests_performed'].append('configurations')
    
    def _test_database_connection(self):
        """Testa conexão com banco de dados"""
        print("\n🗄️ TESTE 3: CONEXÃO COM BANCO DE DADOS")
        print("-" * 40)
        
        try:
            from core.data_reader import DataReader
            
            data_reader = DataReader()
            connection_test = data_reader.test_connection()
            
            if connection_test.get('status') == 'success':
                print(f"   ✅ Conexão OK - {connection_test.get('sample_record_count', 0)} registros")
                print(f"   📁 Database: {connection_test.get('database_path')}")
                print(f"   📊 Tabela principal: {connection_test.get('main_table')}")
                print(f"   ⏱️ Tempo de conexão: {connection_test.get('connection_time', 0):.3f}s")
            else:
                print(f"   ❌ Erro na conexão: {connection_test.get('error')}")
                self.diagnosis_report['issues_found'].append(f"Database connection error: {connection_test.get('error')}")
            
            self.diagnosis_report['detailed_results']['database_connection'] = connection_test
            
        except Exception as e:
            print(f"   ❌ Erro ao testar banco: {e}")
            self.diagnosis_report['issues_found'].append(f"Database test error: {e}")
        
        self.diagnosis_report['tests_performed'].append('database_connection')
    
    def _test_data_availability(self, symbol: str):
        """Testa disponibilidade de dados para análise"""
        print(f"\n📊 TESTE 4: DISPONIBILIDADE DE DADOS ({symbol})")
        print("-" * 50)
        
        try:
            from core.data_reader import DataReader
            
            data_reader = DataReader()
            timeframes = ["5m", "15m"]
            
            data_availability = {}
            
            for tf in timeframes:
                try:
                    market_data = data_reader.get_latest_data(symbol, tf, limit=100)
                    
                    if market_data and market_data.is_sufficient_data:
                        last_timestamp = market_data.data.iloc[-1]['timestamp']
                        data_age_minutes = (datetime.now() - last_timestamp).total_seconds() / 60
                        
                        print(f"   {tf}: ✅ {len(market_data.data)} registros | Último: {last_timestamp} ({data_age_minutes:.1f}min atrás)")
                        
                        data_availability[tf] = {
                            'status': 'OK',
                            'records': len(market_data.data),
                            'last_timestamp': last_timestamp.isoformat(),
                            'age_minutes': data_age_minutes,
                            'latest_price': float(market_data.data.iloc[-1]['close_price'])
                        }
                    else:
                        print(f"   {tf}: ❌ Dados insuficientes")
                        data_availability[tf] = {'status': 'INSUFFICIENT'}
                        self.diagnosis_report['issues_found'].append(f"Insufficient data for {symbol} {tf}")
                        
                except Exception as e:
                    print(f"   {tf}: ❌ Erro - {e}")
                    data_availability[tf] = {'status': 'ERROR', 'error': str(e)}
                    self.diagnosis_report['issues_found'].append(f"Data error for {symbol} {tf}: {e}")
            
            self.diagnosis_report['detailed_results']['data_availability'] = {symbol: data_availability}
            
        except Exception as e:
            print(f"   ❌ Erro geral na verificação de dados: {e}")
            self.diagnosis_report['issues_found'].append(f"Data availability test error: {e}")
        
        self.diagnosis_report['tests_performed'].append('data_availability')
    
    def _test_signal_generation_pipeline(self, symbol: str):
        """Testa o pipeline de geração de sinais passo a passo"""
        print(f"\n🎯 TESTE 5: PIPELINE DE GERAÇÃO DE SINAIS ({symbol})")
        print("-" * 55)
        
        pipeline_results = {}
        
        try:
            from core.analyzer import MultiTimeframeAnalyzer
            from core.data_reader import DataReader
            
            # Inicializa componentes
            analyzer = MultiTimeframeAnalyzer()
            data_reader = DataReader()
            
            # Teste para cada timeframe
            for timeframe in ["5m", "15m"]:
                print(f"\n   📈 Testando {timeframe}:")
                tf_results = {}
                
                try:
                    # 1. Busca dados
                    market_data = data_reader.get_latest_data(symbol, timeframe, limit=100)
                    if not market_data or not market_data.is_sufficient_data:
                        print(f"      ❌ Dados insuficientes")
                        tf_results['data'] = 'INSUFFICIENT'
                        continue
                    
                    print(f"      ✅ Dados OK: {len(market_data.data)} registros")
                    tf_results['data'] = 'OK'
                    
                    # 2. Testa análise técnica
                    try:
                        from indicators.technical import TechnicalAnalyzer
                        
                        tech_analyzer = TechnicalAnalyzer()
                        analysis_results = tech_analyzer.analyze_all(market_data, timeframe)
                        
                        total_signals = 0
                        for indicator, result in analysis_results.items():
                            signals_count = len(result.signals) if hasattr(result, 'signals') else 0
                            total_signals += signals_count
                            print(f"         {indicator}: {signals_count} sinais detectados")
                        
                        tf_results['technical_analysis'] = {
                            'status': 'OK',
                            'total_signals': total_signals,
                            'by_indicator': {k: len(v.signals) if hasattr(v, 'signals') else 0 
                                           for k, v in analysis_results.items()}
                        }
                        
                    except Exception as e:
                        print(f"      ❌ Erro na análise técnica: {e}")
                        tf_results['technical_analysis'] = {'status': 'ERROR', 'error': str(e)}
                    
                    # 3. Testa candlestick patterns
                    try:
                        from indicators.candlestick_patterns_detector import generate_candlestick_signals
                        
                        cs_signals = generate_candlestick_signals(market_data.data, symbol)
                        print(f"         Candlestick: {len(cs_signals)} padrões detectados")
                        
                        tf_results['candlestick_analysis'] = {
                            'status': 'OK',
                            'patterns_detected': len(cs_signals),
                            'patterns': [s.get('detector_name') for s in cs_signals]
                        }
                        
                    except Exception as e:
                        print(f"      ❌ Erro nos candlesticks: {e}")
                        tf_results['candlestick_analysis'] = {'status': 'ERROR', 'error': str(e)}
                    
                    # 4. Testa verificação de sinais bloqueadores
                    try:
                        from core.signal_writer import EnhancedSignalWriter
                        
                        signal_writer = EnhancedSignalWriter()
                        is_blocked = signal_writer.check_existing_active_signals(symbol)
                        
                        print(f"         Sinais bloqueadores: {'SIM' if is_blocked else 'NÃO'}")
                        
                        tf_results['blocking_check'] = {
                            'status': 'OK',
                            'is_blocked': is_blocked
                        }
                        
                        if is_blocked:
                            self.diagnosis_report['issues_found'].append(f"{symbol} has blocking signals")
                        
                    except Exception as e:
                        print(f"      ❌ Erro na verificação de bloqueio: {e}")
                        tf_results['blocking_check'] = {'status': 'ERROR', 'error': str(e)}
                    
                except Exception as e:
                    print(f"      ❌ Erro geral no timeframe: {e}")
                    tf_results['general_error'] = str(e)
                
                pipeline_results[timeframe] = tf_results
            
            self.diagnosis_report['detailed_results']['signal_generation_pipeline'] = {symbol: pipeline_results}
            
        except Exception as e:
            print(f"   ❌ Erro geral no pipeline: {e}")
            self.diagnosis_report['issues_found'].append(f"Pipeline error: {e}")
            traceback.print_exc()
        
        self.diagnosis_report['tests_performed'].append('signal_generation_pipeline')
    
    def _test_validation_pipeline(self, symbol: str):
        """Testa o pipeline de validação"""
        print(f"\n✅ TESTE 6: PIPELINE DE VALIDAÇÃO")
        print("-" * 35)
        
        try:
            from core.analyzer import PrioritySignalResolver
            
            # Testa resolver de conflitos
            resolver = PrioritySignalResolver()
            
            print(f"   📊 Score mínimo 5m: {resolver.MIN_5M_SCORE}")
            print(f"   📈 Vantagem necessária: {resolver.SCORE_ADVANTAGE_REQUIRED}")
            
            validation_config = {
                'min_5m_score': resolver.MIN_5M_SCORE,
                'score_advantage_required': resolver.SCORE_ADVANTAGE_REQUIRED
            }
            
            # Identifica se os filtros são muito restritivos
            if resolver.MIN_5M_SCORE >= 85:
                self.diagnosis_report['issues_found'].append(f"Very restrictive 5m score filter: {resolver.MIN_5M_SCORE}")
                self.diagnosis_report['recommendations'].append("Consider reducing MIN_5M_SCORE from 90 to 75")
            
            if resolver.SCORE_ADVANTAGE_REQUIRED >= 8:
                self.diagnosis_report['issues_found'].append(f"Very restrictive score advantage: {resolver.SCORE_ADVANTAGE_REQUIRED}")
                self.diagnosis_report['recommendations'].append("Consider reducing SCORE_ADVANTAGE_REQUIRED from 10 to 5")
            
            self.diagnosis_report['detailed_results']['validation_config'] = validation_config
            
        except Exception as e:
            print(f"   ❌ Erro no teste de validação: {e}")
            self.diagnosis_report['issues_found'].append(f"Validation test error: {e}")
        
        self.diagnosis_report['tests_performed'].append('validation_pipeline')
    
    def _generate_final_report(self):
        """Gera relatório final com diagnóstico e recomendações"""
        print("\n" + "=" * 70)
        print("📋 RELATÓRIO FINAL DE DIAGNÓSTICO")
        print("=" * 70)
        
        # Sumário
        total_tests = len(self.diagnosis_report['tests_performed'])
        total_issues = len(self.diagnosis_report['issues_found'])
        
        print(f"\n📊 SUMÁRIO:")
        print(f"   • Testes executados: {total_tests}")
        print(f"   • Issues encontrados: {total_issues}")
        print(f"   • Recomendações: {len(self.diagnosis_report['recommendations'])}")
        
        # Issues críticos
        if self.diagnosis_report['issues_found']:
            print(f"\n🚨 ISSUES ENCONTRADOS:")
            for i, issue in enumerate(self.diagnosis_report['issues_found'], 1):
                print(f"   {i}. {issue}")
        
        # Recomendações
        if self.diagnosis_report['recommendations']:
            print(f"\n💡 RECOMENDAÇÕES:")
            for i, rec in enumerate(self.diagnosis_report['recommendations'], 1):
                print(f"   {i}. {rec}")
        
        # Recomendações automáticas baseadas nos issues
        auto_recommendations = self._generate_auto_recommendations()
        if auto_recommendations:
            print(f"\n🎯 RECOMENDAÇÕES AUTOMÁTICAS:")
            for i, rec in enumerate(auto_recommendations, 1):
                print(f"   {i}. {rec}")
                self.diagnosis_report['recommendations'].append(rec)
        
        # Status geral
        if total_issues == 0:
            print(f"\n✅ STATUS: Sistema aparenta estar funcionando corretamente")
        elif total_issues <= 3:
            print(f"\n⚠️ STATUS: Sistema com issues menores - correções simples necessárias")
        else:
            print(f"\n❌ STATUS: Sistema com issues significativos - intervenção necessária")
        
        print("\n" + "=" * 70)
    
    def _generate_auto_recommendations(self) -> List[str]:
        """Gera recomendações automáticas baseadas nos issues encontrados"""
        recommendations = []
        
        issues_text = ' '.join(self.diagnosis_report['issues_found']).lower()
        
        # Recomendações baseadas em patterns nos issues
        if 'insufficient data' in issues_text:
            recommendations.append("Verificar se o data collector está funcionando corretamente")
        
        if 'restrictive' in issues_text:
            recommendations.append("Relaxar filtros de score (MIN_5M_SCORE: 90→75, SCORE_ADVANTAGE: 10→5)")
        
        if 'blocking signals' in issues_text:
            recommendations.append("Limpar sinais bloqueadores antigos ou verificar lógica de status")
        
        if 'import error' in issues_text:
            recommendations.append("Verificar dependências Python e estrutura de arquivos")
        
        if 'database' in issues_text:
            recommendations.append("Verificar configuração e acessibilidade do banco de dados")
        
        # Recomendação geral se muitos issues
        if len(self.diagnosis_report['issues_found']) > 5:
            recommendations.append("Executar correções das issues críticas antes de prosseguir")
        
        return recommendations
    
    def save_report_to_file(self, filename: str = None):
        """Salva relatório detalhado em arquivo"""
        if filename is None:
            filename = f"signal_diagnosis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        import json
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.diagnosis_report, f, indent=2, default=str, ensure_ascii=False)
            print(f"\n📄 Relatório detalhado salvo em: {filename}")
        except Exception as e:
            print(f"\n❌ Erro ao salvar relatório: {e}")

def run_quick_diagnosis(symbol: str = "BTCUSDT"):
    """Executa diagnóstico rápido do sistema"""
    diagnostic = SignalSystemDiagnostic()
    report = diagnostic.run_complete_diagnosis(symbol)
    diagnostic.save_report_to_file()
    return report

def run_live_signal_test(symbol: str = "BTCUSDT", timeframe: str = "5m"):
    """Testa geração de sinal em tempo real"""
    print(f"\n🔴 TESTE LIVE: GERAÇÃO DE SINAL {symbol} {timeframe}")
    print("=" * 50)
    
    try:
        from core.analyzer import MultiTimeframeAnalyzer
        
        analyzer = MultiTimeframeAnalyzer()
        
        print(f"Executando análise completa...")
        result = analyzer.analyze_symbol_all_timeframes(symbol)
        
        print(f"\n📊 RESULTADO:")
        print(f"   Status: {result.get('status')}")
        print(f"   Sinais detectados: {result.get('signals_detected', 0)}")
        print(f"   Sinais validados: {result.get('signals_validated', 0)}")
        print(f"   Sinais salvos: {result.get('signals_saved', 0)}")
        print(f"   Tempo execução: {result.get('execution_time', 0):.2f}s")
        
        if result.get('reason'):
            print(f"   Razão: {result.get('reason')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Erro no teste live: {e}")
        traceback.print_exc()
        return {'status': 'error', 'error': str(e)}

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "quick":
            # Diagnóstico rápido
            symbol = sys.argv[2] if len(sys.argv) > 2 else "BTCUSDT"
            run_quick_diagnosis(symbol)
        elif sys.argv[1] == "live":
            # Teste live
            symbol = sys.argv[2] if len(sys.argv) > 2 else "BTCUSDT"
            timeframe = sys.argv[3] if len(sys.argv) > 3 else "5m"
            run_live_signal_test(symbol, timeframe)
    else:
        # Diagnóstico completo padrão
        run_quick_diagnosis()
        print(f"\n🔬 Para usar outras funções:")
        print(f"   python signal_diagnostic_tool.py quick BTCUSDT    # Diagnóstico rápido")
        print(f"   python signal_diagnostic_tool.py live BTCUSDT 5m  # Teste live")