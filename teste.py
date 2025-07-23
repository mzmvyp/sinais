import sqlite3
from config.settings import settings

def clear_test_signals():
    db_path = settings.database.signals_db_path
    table = settings.database.signals_table
    
    try:
        with sqlite3.connect(db_path, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {table} WHERE symbol IN ('SOL', 'IMX', 'ETH')")
            deleted = cursor.rowcount
            print(f"🧹 Removidos {deleted} sinais de teste")
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    clear_test_signals()