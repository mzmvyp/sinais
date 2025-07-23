import sqlite3
from config.settings import settings

def check_signals_table():
    """Verifica status da tabela de sinais"""
    db_path = settings.database.signals_db_path
    table = settings.database.signals_table
    
    try:
        with sqlite3.connect(db_path, timeout=10) as conn:
            cursor = conn.cursor()
            
            # Verifica se tabela existe
            cursor.execute(f"""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='{table}'
            """)
            table_exists = cursor.fetchone() is not None
            print(f"Tabela {table} existe: {table_exists}")
            
            if table_exists:
                # Conta sinais por status
                cursor.execute(f"""
                    SELECT status, COUNT(*) 
                    FROM {table} 
                    GROUP BY status
                """)
                status_counts = cursor.fetchall()
                print("Sinais por status:")
                for status, count in status_counts:
                    print(f"  {status}: {count}")
                
                # Últimos 5 sinais
                cursor.execute(f"""
                    SELECT symbol, status, created_at, detector_name, confidence
                    FROM {table} 
                    ORDER BY created_at DESC 
                    LIMIT 5
                """)
                recent = cursor.fetchall()
                print("\nÚltimos 5 sinais:")
                for row in recent:
                    print(f"  {row}")
    
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    check_signals_table()