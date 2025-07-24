import sqlite3
import pandas as pd
import json
from datetime import datetime
import sys
import logging

# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def create_connection(db_file):
    """ Cria uma conexão com o banco de dados SQLite. """
    conn = None
    try:
        # Conecta em modo de apenas leitura para segurança
        conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
        logging.info(f"Conexão com {db_file} (modo leitura) bem-sucedida.")
    except sqlite3.Error as e:
        logging.error(f"Erro ao conectar com o banco de dados {db_file}: {e}")
        logging.error("Verifique se o caminho e o nome do arquivo estão corretos.")
    return conn

def list_tables(conn):
    """ Lista todas as tabelas em uma conexão de banco de dados. """
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in cursor.fetchall()]
        return tables
    except Exception as e:
        logging.error(f"Erro ao listar tabelas: {e}")
        return []


def load_signals_data(conn, table_name):
    """ Carrega os dados dos sinais da tabela de backup. """
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        logging.info(f"Carregados {len(df)} sinais da tabela '{table_name}'.")
        # Converte a coluna de data para o formato datetime
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'])
        return df
    except Exception as e:
        logging.error(f"Erro ao carregar os sinais da tabela '{table_name}': {e}")
        return pd.DataFrame()

def get_price_stream(conn, symbol, start_time):
    """ Busca o stream de preços para um determinado símbolo a partir de um tempo inicial. """
    try:
        query = f"""
        SELECT * FROM {STREAM_TABLE_NAME}
        WHERE symbol = ? AND timestamp >= ?
        ORDER BY timestamp ASC
        """
        if isinstance(start_time, str):
            start_time = pd.to_datetime(start_time)
            
        df = pd.read_sql_query(query, conn, params=(symbol, start_time.strftime("%Y-%m-%d %H:%M:%S")))
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        logging.error(f"Erro ao buscar o stream de preços para {symbol}: {e}")
        return pd.DataFrame()

def analyze_signal(signal, price_stream):
    """
    Analisa um único sinal contra o seu stream de preços para determinar o resultado.
    A lógica verifica o stop loss antes do alvo para cada candle, simulando o "primeiro a chegar".
    """
    entry_price = signal.get('entry_price')
    stop_loss = signal.get('stop_loss')
    signal_type = signal.get('signal_type')
    targets_json = signal.get('targets')

    if any(v is None for v in [entry_price, stop_loss, signal_type, targets_json]):
        return "Dados do sinal incompletos", None

    try:
        targets = json.loads(targets_json)
        targets = [float(t) for t in targets]
    except (json.JSONDecodeError, TypeError, ValueError):
        return "Alvos inválidos", None

    # Ordena os alvos para verificação sequencial
    sorted_targets_buy = sorted(targets)
    sorted_targets_sell = sorted(targets, reverse=True)
    
    for _, row in price_stream.iterrows():
        high_price = row['high_price']
        low_price = row['low_price']

        if signal_type == 'BUY_LONG':
            # 1. Verifica se o stop foi atingido primeiro no candle
            if low_price <= stop_loss:
                return "Stop Loss Atingido", stop_loss
            
            # 2. Se não stopou, verifica se algum alvo foi atingido
            highest_target_hit = None
            for target in sorted_targets_buy:
                if high_price >= target:
                    highest_target_hit = target # Continua para encontrar o alvo mais alto atingido no mesmo candle
            if highest_target_hit is not None:
                return f"Alvo Atingido", highest_target_hit

        elif signal_type == 'SELL_SHORT':
            # 1. Verifica se o stop foi atingido primeiro no candle
            if high_price >= stop_loss:
                return "Stop Loss Atingido", stop_loss

            # 2. Se não stopou, verifica se algum alvo foi atingido
            lowest_target_hit = None
            for target in sorted_targets_sell:
                if low_price <= target:
                    lowest_target_hit = target # Continua para encontrar o alvo mais baixo atingido no mesmo candle
            if lowest_target_hit is not None:
                return f"Alvo Atingido", lowest_target_hit
    
    return "Nenhum resultado", None

def generate_report(results_df):
    """ Gera um relatório de performance a partir dos resultados da análise e retorna como string. """
    report_lines = []
    
    # Filtra apenas os sinais que tiveram um resultado conclusivo
    resolved_signals = results_df[results_df['resultado'] != 'Nenhum resultado'].copy()
    total_resolved = len(resolved_signals)

    if total_resolved == 0:
        return "Nenhum sinal com resultado conclusivo para gerar relatório."

    report_lines.append("\n" + "="*60)
    report_lines.append("RELATÓRIO DE PERFORMANCE DOS SINAIS")
    report_lines.append("="*60)

    # --- ESTATÍSTICAS GERAIS ---
    report_lines.append("\n--- ESTATÍSTICAS GERAIS ---")
    success_signals = resolved_signals[resolved_signals['resultado'] == "Alvo Atingido"]
    stopped_signals = resolved_signals[resolved_signals['resultado'] == "Stop Loss Atingido"]
    success_rate = (len(success_signals) / total_resolved) * 100 if total_resolved > 0 else 0

    report_lines.append(f"Total de Sinais com Resultado: {total_resolved}")
    report_lines.append(f"Sinais com Sucesso (Alvo): {len(success_signals)}")
    report_lines.append(f"Sinais com Falha (Stop): {len(stopped_signals)}")
    report_lines.append(f"Taxa de Sucesso Geral: {success_rate:.2f}%")

    # --- ANÁLISE DE RETORNO (PnL) ---
    report_lines.append("\n--- ANÁLISE DE RETORNO (PnL) ---")
    pnls = []
    for _, row in resolved_signals.iterrows():
        entry = row['entry_price']
        exit_price = row['exit_price']
        if entry > 0 and exit_price is not None:
            if row['signal_type'] == 'BUY_LONG':
                pnl = (exit_price - entry) / entry
            else: # SELL_SHORT
                pnl = (entry - exit_price) / entry
            pnls.append(pnl)

    if pnls:
        avg_pnl = (sum(pnls) / len(pnls)) * 100
        cumulative_pnl = sum(pnls) * 100
        best_trade = max(pnls) * 100
        worst_trade = min(pnls) * 100
        report_lines.append(f"Retorno Médio por Operação: {avg_pnl:.2f}%")
        report_lines.append(f"Retorno Acumulado: {cumulative_pnl:.2f}%")
        report_lines.append(f"Melhor Operação: {best_trade:.2f}%")
        report_lines.append(f"Pior Operação: {worst_trade:.2f}%")
    else:
        report_lines.append("Não foi possível calcular o retorno (PnL).")

    # --- PERFORMANCE POR CATEGORIA ---
    categories = ['detector_type', 'signal_source', 'detector_name']
    for category in categories:
        report_lines.append(f"\n--- PERFORMANCE POR '{category.upper()}' ---")
        
        # Agrupa para análise
        grouped = resolved_signals.groupby(category).agg(
            total_sinais=('resultado', 'count'),
            acertos=('resultado', lambda x: (x == 'Alvo Atingido').sum()),
            erros=('resultado', lambda x: (x == 'Stop Loss Atingido').sum())
        ).reset_index()

        grouped['taxa_sucesso_%'] = (grouped['acertos'] / grouped['total_sinais'] * 100).round(2)
        grouped = grouped.sort_values(by='total_sinais', ascending=False)
        
        if grouped.empty:
            report_lines.append("Nenhum dado para esta categoria.")
        else:
            # Converte o DataFrame para string para uma formatação bonita
            report_lines.append(grouped.to_string(index=False))

    report_lines.append("\n" + "="*60)
    report_lines.append("FIM DO RELATÓRIO")
    report_lines.append("="*60)
    
    return "\n".join(report_lines)

# =============================================================================
# SCRIPT PRINCIPAL
# =============================================================================

# Caminho para a pasta que contém os bancos de dados
DB_PATH = r"C:\Users\mzmvy\Documents\python\trading_system\data"

# Nomes dos arquivos de banco de dados
SIGNALS_DB_NAME = "trading_analyzer_v2.db"
STREAM_DB_NAME = "crypto_stream.db"

# Nomes das tabelas
SIGNALS_TABLE_NAME = "signal_backup_v2"
STREAM_TABLE_NAME = "crypto_ohlc"

def main():
    """ Função principal que orquestra a análise e geração do relatório. """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='analise_sinais.log',
        filemode='w'
    )
    
    logging.info("Iniciando a análise de sinais.")
    
    signals_conn = create_connection(f"{DB_PATH}\\{SIGNALS_DB_NAME}")
    stream_conn = create_connection(f"{DB_PATH}\\{STREAM_DB_NAME}")

    if not signals_conn or not stream_conn:
        logging.critical("Não foi possível conectar a um ou mais bancos de dados. Encerrando.")
        print("\nERRO: Não foi possível conectar a um ou mais bancos de dados. Verifique 'analise_sinais.log'.")
        sys.exit(1)
        
    signals_tables = list_tables(signals_conn)
    stream_tables = list_tables(stream_conn)

    print(f"\nTabelas encontradas em '{SIGNALS_DB_NAME}': {signals_tables}")
    print(f"Tabelas encontradas em '{STREAM_DB_NAME}': {stream_tables}")
    logging.info(f"Tabelas em '{SIGNALS_DB_NAME}': {signals_tables}")
    logging.info(f"Tabelas em '{STREAM_DB_NAME}': {stream_tables}")

    if SIGNALS_TABLE_NAME not in signals_tables:
        msg = f"ERRO CRÍTICO: Tabela '{SIGNALS_TABLE_NAME}' não encontrada em '{SIGNALS_DB_NAME}'. Disponíveis: {signals_tables}"
        print("\n" + "!"*60 + f"\n!! {msg}\n" + "!"*60)
        logging.critical(msg)
        sys.exit(1)

    signals_df = load_signals_data(signals_conn, SIGNALS_TABLE_NAME)
    if signals_df.empty:
        logging.warning("Nenhum sinal encontrado para análise. Encerrando.")
        print("\nNenhum sinal encontrado para análise.")
        signals_conn.close()
        stream_conn.close()
        return

    results = []
    exit_prices = []
    total_signals_count = len(signals_df)
    for index, signal in signals_df.iterrows():
        logging.info(f"Analisando sinal {index + 1}/{total_signals_count} (ID: {signal.get('original_id', 'N/A')})...")
        price_stream_df = get_price_stream(stream_conn, signal['symbol'], signal['created_at'])

        if not price_stream_df.empty:
            result, exit_price = analyze_signal(signal, price_stream_df)
            results.append(result)
            exit_prices.append(exit_price)
            logging.info(f"  -> Resultado para {signal.get('original_id', 'N/A')}: {result} no preço {exit_price}")
        else:
            results.append("Stream de preço não encontrado")
            exit_prices.append(None)
            logging.warning(f"  -> Stream de preço não encontrado para {signal['symbol']} após {signal['created_at']}")

    signals_df['resultado'] = results
    signals_df['exit_price'] = exit_prices
    
    report_string = generate_report(signals_df)
    print(report_string)
    logging.info("Relatório final gerado:\n" + report_string)

    signals_conn.close()
    stream_conn.close()
    logging.info("Conexões com os bancos de dados fechadas. Análise concluída.")

if __name__ == "__main__":
    main()
