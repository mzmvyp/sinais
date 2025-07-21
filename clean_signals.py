"""Script para limpar sinais duplicados"""

def clean_duplicate_signals():
    from core.signal_writer import SignalWriter
    import sqlite3
    
    writer = SignalWriter()
    
    try:
        with writer._get_connection() as conn:
            # Encontra sinais duplicados
            duplicates_sql = """
            SELECT symbol, COUNT(*) as count
            FROM trading_signals_v2 
            WHERE status = 'ACTIVE'
            GROUP BY symbol
            HAVING COUNT(*) > 1
            """
            
            cursor = conn.execute(duplicates_sql)
            duplicates = cursor.fetchall()
            
            removed_count = 0
            
            for symbol, count in duplicates:
                print(f"🔄 {symbol}: {count} sinais ativos - removendo duplicatas...")
                
                # Mantém apenas o mais recente
                keep_sql = """
                SELECT id FROM trading_signals_v2 
                WHERE symbol = ? AND status = 'ACTIVE'
                ORDER BY created_at DESC
                LIMIT 1
                """
                
                cursor = conn.execute(keep_sql, (symbol,))
                keep_id = cursor.fetchone()[0]
                
                # Remove os outros
                remove_sql = """
                UPDATE trading_signals_v2 
                SET status = 'CANCELLED_DUPLICATE'
                WHERE symbol = ? AND status = 'ACTIVE' AND id != ?
                """
                
                cursor = conn.execute(remove_sql, (symbol, keep_id))
                removed_this_symbol = cursor.rowcount
                removed_count += removed_this_symbol
            
            conn.commit()
            print(f"✅ Total removido: {removed_count} duplicatas")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    clean_duplicate_signals()