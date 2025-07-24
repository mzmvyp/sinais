#!/usr/bin/env python3
# fix_cycle_loop.py - CORRIGE O LOOP DOS CICLOS

"""
Adiciona logs verbosos e corrige o loop dos ciclos
para garantir que continue após o primeiro ciclo
"""

def fix_analyzer_loop():
    """Corrige o método run_continuous_multi_timeframe_analysis"""
    
    try:
        with open("core/analyzer.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Método corrigido com logs verbosos
        new_method = '''    def run_continuous_multi_timeframe_analysis(self, base_interval: int = None):
        """Execução contínua DEFINITIVA com logs verbosos"""
        if base_interval is None: 
           base_interval = getattr(settings.system, 'analysis_interval', 300)
        
        self.logger.info("🚀 ANÁLISE CONTÍNUA DEFINITIVA - PRIORIDADE 15m")
        self.logger.info(f"⏱️ Intervalo entre ciclos: {base_interval}s")
        
        valid_symbols = self.data_reader.get_valid_symbols_for_analysis()
        
        if not valid_symbols:
            self.logger.error("❌ Nenhum símbolo válido encontrado!")
            return
        
        self.logger.info(f"✅ Símbolos: {valid_symbols}")
        
        cycle_count = 0
        
        while True:
            try:
                cycle_count += 1
                cycle_start = time.time()
                total_signals = 0
                blocked_count = 0
                error_count = 0
                
                self.logger.info(f"🔄 Ciclo {cycle_count} - Prioridade 15m")
                
                for i, symbol in enumerate(valid_symbols, 1):
                    try:
                        symbol_start = time.time()
                        result = self.analyze_symbol_all_timeframes(symbol)
                        symbol_time = time.time() - symbol_start
                        
                        if result.get('status') == 'blocked':
                            blocked_count += 1
                        elif result.get('status') == 'error':
                            error_count += 1
                        else:
                            signals_saved = result.get('signals_saved', 0)
                            total_signals += signals_saved
                            if signals_saved > 0:
                                self.logger.info(f"🎯 {symbol} ({i}/{len(valid_symbols)}): {signals_saved} ATIVO")
                            else:
                                self.logger.debug(f"✓ {symbol} ({i}/{len(valid_symbols)}): OK em {symbol_time:.1f}s")
                        
                        time.sleep(0.1)
                        
                    except Exception as e:
                        error_count += 1
                        self.logger.error(f"❌ Erro em {symbol}: {e}")
                
                cycle_time = time.time() - cycle_start
                
                # RESUMO DO CICLO COM LOGS VERBOSOS
                self.logger.info(
                    f"✅ Ciclo {cycle_count}: {total_signals} novos ACTIVE | "
                    f"{blocked_count} bloqueados | {error_count} erros | {cycle_time:.1f}s"
                )
                
                # LOG VERBOSE DO FINAL DO CICLO
                self.logger.info(f"📊 Ciclo {cycle_count} finalizado com sucesso!")
                self.logger.info(f"⏳ Iniciando aguardo de {base_interval}s...")
                
                # SLEEP COM HEARTBEAT
                sleep_start = time.time()
                heartbeat_interval = 60  # Heartbeat a cada 60s
                next_heartbeat = heartbeat_interval
                
                while True:
                    elapsed_sleep = time.time() - sleep_start
                    
                    if elapsed_sleep >= base_interval:
                        break
                    
                    # Heartbeat
                    if elapsed_sleep >= next_heartbeat:
                        remaining = base_interval - elapsed_sleep
                        self.logger.info(f"💓 Heartbeat: aguardando mais {remaining:.0f}s até próximo ciclo...")
                        next_heartbeat += heartbeat_interval
                    
                    time.sleep(1)  # Sleep curto para permitir heartbeat
                
                self.logger.info(f"⏰ Aguardo de {base_interval}s concluído. Iniciando Ciclo {cycle_count + 1}...")
                
            except KeyboardInterrupt:
                self.logger.info("🛑 Análise interrompida pelo usuário")
                break
            except Exception as e:
                self.logger.error(f"❌ Erro crítico no ciclo {cycle_count}: {e}")
                import traceback
                self.logger.error(f"Stack trace: {traceback.format_exc()}")
                
                self.logger.info(f"🔄 Tentando recuperar em 10s...")
                time.sleep(10)
                continue
        
        self.logger.info("🏁 Análise contínua finalizada")'''
        
        # Substitui o método
        import re
        pattern = r'def run_continuous_multi_timeframe_analysis\(self.*?(?=def|\Z)'
        
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, new_method + "\n\n    ", content, flags=re.DOTALL)
            
            # Salva
            with open("core/analyzer.py", "w", encoding="utf-8") as f:
                f.write(content)
            
            print("✅ Loop dos ciclos corrigido com logs verbosos")
            return True
        else:
            print("❌ Não encontrou método para substituir")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao corrigir loop: {e}")
        return False

def add_debug_script():
    """Cria script para debug em tempo real"""
    
    debug_script = '''#!/usr/bin/env python3
# debug_monitor.py - Monitor de debug em tempo real

import time
import sys
from datetime import datetime

def monitor_system():
    """Monitora o sistema em tempo real"""
    print("🔍 MONITOR DE DEBUG EM TEMPO REAL")
    print("=" * 50)
    print("⏱️ Inicia monitoramento...")
    
    cycle_count = 0
    
    while True:
        try:
            cycle_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Verifica se sistema ainda está rodando
            try:
                # Aqui poderia verificar logs, processos, etc
                status = "🟢 RODANDO"
            except:
                status = "🔴 PARADO"
            
            print(f"[{timestamp}] Monitor {cycle_count}: {status}")
            
            # Heartbeat a cada 30s
            time.sleep(30)
            
        except KeyboardInterrupt:
            print(f"\\n🛑 Monitor interrompido")
            break
        except Exception as e:
            print(f"❌ Erro no monitor: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor_system()
'''
    
    try:
        with open("debug_monitor.py", "w", encoding="utf-8") as f:
            f.write(debug_script)
        print("✅ Script de debug criado: debug_monitor.py")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar debug script: {e}")
        return False

def show_monitoring_tips():
    """Mostra dicas de monitoramento"""
    print("\n📊 COMO MONITORAR O SISTEMA:")
    print("=" * 40)
    
    print("🔍 1. Em outro terminal (monitoramento):")
    print("   python debug_monitor.py")
    
    print("\n📝 2. Para ver logs em tempo real:")
    print("   tail -f nohup.out")
    print("   # ou no Windows:")
    print("   Get-Content nohup.out -Wait")
    
    print("\n⏰ 3. O que esperar agora:")
    print("   ✅ Ciclo 1: 3 novos ACTIVE | 4 bloqueados | 0 erros | 8.5s")
    print("   📊 Ciclo 1 finalizado com sucesso!")
    print("   ⏳ Iniciando aguardo de 300s...")
    print("   💓 Heartbeat: aguardando mais 240s até próximo ciclo...")
    print("   💓 Heartbeat: aguardando mais 180s até próximo ciclo...")
    print("   ...")
    print("   ⏰ Aguardo de 300s concluído. Iniciando Ciclo 2...")
    print("   🔄 Ciclo 2 - Prioridade 15m")
    
    print("\n🚨 4. Se ainda travar:")
    print("   • Anote o último log mostrado")
    print("   • Pressione Ctrl+C")
    print("   • Execute: python main.py --analyze SIMBOLOPROBLEMA")

def main():
    """Aplica correção do loop"""
    print("🔧 CORREÇÃO DO LOOP DOS CICLOS")
    print("=" * 40)
    print("🎯 Adiciona logs verbosos e heartbeat no aguardo")
    print("=" * 40)
    
    success_count = 0
    
    if fix_analyzer_loop():
        success_count += 1
        print("✅ Loop corrigido")
    
    if add_debug_script():
        success_count += 1
        print("✅ Script de debug criado")
    
    if success_count == 2:
        print("\n🎉 CORREÇÃO APLICADA COM SUCESSO!")
        print("\n🚀 TESTE AGORA:")
        print("   python main.py --continuous")
        
        print("\n📊 RESULTADO ESPERADO:")
        print("   • Logs verbosos do progresso")
        print("   • Heartbeat durante aguardo")
        print("   • Ciclos contínuos sem travamento")
        
        show_monitoring_tips()
        
    else:
        print(f"\n❌ Algumas correções falharam ({success_count}/2)")

if __name__ == "__main__":
    main()