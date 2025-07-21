"""
Script para Criar a Tabela trading_signals_v2
Sistema de Trading Analyzer - Tabela Unificada de Sinais
"""

import sqlite3
import os
import sys
from datetime import datetime
from config.settings import settings

def create_trading_signals_table():
    """Cria a tabela trading_signals_v2 com estrutura completa"""
    
    # Caminho do banco de dados
    db_path = settings.database.signals_db_path
    
    print(f"🔧 Criando tabela trading_signals_v2...")
    print(f"📁 Banco: {db_path}")
    
    # Verifica se o diretório existe
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        print(f"📁 Diretório criado: {db_dir}")
    
    try:
        # Conecta ao banco
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # SQL de criação da tabela
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS trading_signals_v2 (
            -- Identificação
            id TEXT PRIMARY KEY NOT NULL,
            symbol TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            
            -- Preços e Targets
            entry_price REAL NOT NULL,
            targets TEXT,  -- JSON array de targets
            stop_loss REAL,
            current_price REAL,
            
            -- Confiança e Scoring
            confidence REAL NOT NULL,
            confluence_score INTEGER DEFAULT 95,
            risk_reward_ratio REAL DEFAULT 1.0,
            
            -- Status e Controle
            status TEXT DEFAULT 'ACTIVE',
            volume_confirmed INTEGER DEFAULT 0,
            
            -- Timestamps
            created_at DATETIME NOT NULL,
            entry_time DATETIME,
            exit_time DATETIME,
            updated_at DATETIME,
            
            -- Performance Tracking
            pnl_percentage REAL DEFAULT 0.0,
            pnl_absolute REAL DEFAULT 0.0,
            duration_hours REAL DEFAULT 0.0,
            max_profit REAL DEFAULT 0.0,
            max_drawdown REAL DEFAULT 0.0,
            
            -- Targets e Indicadores
            targets_hit TEXT,  -- JSON array de booleans
            indicators_used TEXT  -- JSON array de indicadores
        );
        """
        
        cursor.execute(create_table_sql)
        
        # Cria índices para performance
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_symbol ON trading_signals_v2(symbol);",
            "CREATE INDEX IF NOT EXISTS idx_status ON trading_signals_v2(status);",
            "CREATE INDEX IF NOT EXISTS idx_created_at ON trading_signals_v2(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_symbol_status ON trading_signals_v2(symbol, status);",
            "CREATE INDEX IF NOT EXISTS idx_signal_type ON trading_signals_v2(signal_type);",
            "CREATE INDEX IF NOT EXISTS idx_confidence ON trading_signals_v2(confidence);"
        ]
        
        for index_sql in indices:
            cursor.execute(index_sql)
        
        # Commit das alterações
        conn.commit()
        
        # Verifica se foi criada corretamente
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trading_signals_v2';")
        table_exists = cursor.fetchone()
        
        if table_exists:
            # Verifica estrutura
            cursor.execute("PRAGMA table_info(trading_signals_v2);")
            columns = cursor.fetchall()
            
            print("✅ Tabela trading_signals_v2 criada com sucesso!")
            print(f"📊 Estrutura da tabela ({len(columns)} colunas):")
            
            for col in columns:
                col_id, col_name, col_type, not_null, default, primary_key = col
                nullable = "NOT NULL" if not_null else "NULL"
                pk = " (PK)" if primary_key else ""
                default_val = f" DEFAULT {default}" if default else ""
                print(f"   {col_name}: {col_type} {nullable}{default_val}{pk}")
            
            # Verifica índices
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='trading_signals_v2';")
            indexes = cursor.fetchall()
            print(f"🔍 Índices criados: {len(indexes)}")
            for idx in indexes:
                if not idx[0].startswith('sqlite_'):  # Pula índices automáticos
                    print(f"   - {idx[0]}")
            
        else:
            print("❌ Erro: Tabela não foi criada")
            return False
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Erro no banco de dados: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return False

def verify_table_structure():
    """Verifica se a tabela está correta e funcionando"""
    
    db_path = settings.database.signals_db_path
    
    if not os.path.exists(db_path):
        print("❌ Banco de dados não encontrado")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Testa inserção de um sinal de exemplo
        test_signal = {
            'id': f"TEST_BTCUSDT_BUY_LONG_{int(datetime.now().timestamp() * 100)}",
            'symbol': 'BTCUSDT',
            'signal_type': 'BUY_LONG',
            'entry_price': 50000.0,
            'targets': '["51500.0", "52000.0", "53000.0"]',
            'stop_loss': 48500.0,
            'confidence': 0.85,
            'confluence_score': 95,
            'status': 'ACTIVE',
            'created_at': datetime.now().isoformat(),
            'entry_time': datetime.now().isoformat(),
            'exit_time': None,
            'current_price': 50000.0,
            'pnl_percentage': 0.0,
            'pnl_absolute': 0.0,
            'duration_hours': 0.0,
            'targets_hit': '[false, false, false]',
            'indicators_used': '["rsi_analize", "macd_analize"]',
            'volume_confirmed': 1,
            'risk_reward_ratio': 2.5,
            'max_profit': 0.0,
            'max_drawdown': 0.0,
            'updated_at': datetime.now().isoformat()
        }
        
        # Monta query de inserção
        columns = ', '.join(test_signal.keys())
        placeholders = ', '.join(['?' for _ in test_signal])
        
        insert_sql = f"INSERT INTO trading_signals_v2 ({columns}) VALUES ({placeholders})"
        cursor.execute(insert_sql, list(test_signal.values()))
        
        # Verifica se foi inserido
        cursor.execute("SELECT COUNT(*) FROM trading_signals_v2 WHERE id = ?", (test_signal['id'],))
        count = cursor.fetchone()[0]
        
        if count == 1:
            print("✅ Teste de inserção: OK")
            
            # Remove o registro de teste
            cursor.execute("DELETE FROM trading_signals_v2 WHERE id = ?", (test_signal['id'],))
            conn.commit()
            print("🧹 Registro de teste removido")
        else:
            print("❌ Teste de inserção: FALHOU")
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def show_current_signals():
    """Mostra sinais ativos atuais (se houver)"""
    
    db_path = settings.database.signals_db_path
    
    if not os.path.exists(db_path):
        print("📋 Nenhum sinal encontrado (banco não existe)")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Conta sinais ativos
        cursor.execute("SELECT COUNT(*) FROM trading_signals_v2 WHERE status = 'ACTIVE'")
        active_count = cursor.fetchone()[0]
        
        # Conta sinais totais
        cursor.execute("SELECT COUNT(*) FROM trading_signals_v2")
        total_count = cursor.fetchone()[0]
        
        print(f"📋 Sinais atuais: {active_count} ativos de {total_count} totais")
        
        if active_count > 0:
            # Mostra os 5 mais recentes
            cursor.execute("""
                SELECT symbol, signal_type, entry_price, confidence, created_at 
                FROM trading_signals_v2 
                WHERE status = 'ACTIVE' 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            
            recent_signals = cursor.fetchall()
            
            print("🔝 Últimos 5 sinais ativos:")
            for signal in recent_signals:
                symbol, signal_type, entry_price, confidence, created_at = signal
                print(f"   {symbol}: {signal_type} @ ${entry_price:.2f} (conf: {confidence:.2f}) - {created_at[:16]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao consultar sinais: {e}")

def main():
    """Função principal"""
    
    print("=" * 70)
    print("🚀 CRIAÇÃO DA TABELA TRADING_SIGNALS_V2")
    print("=" * 70)
    
    # 1. Cria a tabela
    if create_trading_signals_table():
        print("\n" + "=" * 50)
        
        # 2. Verifica funcionamento
        print("🧪 Testando funcionalidade...")
        if verify_table_structure():
            print("✅ Tabela está funcionando corretamente")
        else:
            print("❌ Problema na verificação da tabela")
        
        print("\n" + "=" * 50)
        
        # 3. Mostra sinais atuais
        show_current_signals()
        
        print("\n" + "=" * 50)
        print("🎯 PRÓXIMOS PASSOS:")
        print("1. Execute: python main.py --status")
        print("2. Teste com: python main.py --analyze BTCUSDT")
        print("3. Para análise completa: python main.py --analyze-all")
        print("=" * 50)
        
    else:
        print("❌ Falha na criação da tabela")
        sys.exit(1)

if __name__ == "__main__":
    main()