import sqlite3
from db import DB_PATH
import pandas as pd
from datetime import datetime
import json

def check_db_state():
    """Verifica o estado atual do banco de dados e exibe informações relevantes"""
    conn = sqlite3.connect(DB_PATH)
    
    # Verificar transações recentes
    print("=== 10 TRANSAÇÕES MAIS RECENTES ===")
    recent_trans = pd.read_sql_query(
        "SELECT id, date, description, amount, type, status, categoria_tipo FROM transactions ORDER BY id DESC LIMIT 10", 
        conn
    )
    print(recent_trans)
    
    # Estatísticas por status
    print("\n=== CONTAGEM POR STATUS ===")
    status_counts = pd.read_sql_query(
        "SELECT status, COUNT(*) as count FROM transactions GROUP BY status", 
        conn
    )
    print(status_counts)
    
    # Estatísticas por tipo
    print("\n=== CONTAGEM POR TIPO ===")
    type_counts = pd.read_sql_query(
        "SELECT type, COUNT(*) as count FROM transactions GROUP BY type", 
        conn
    )
    print(type_counts)
    
    # Verificar transações do mês atual
    current_month = datetime.now().strftime("%Y-%m")
    print(f"\n=== TRANSAÇÕES DO MÊS ATUAL ({current_month}) ===")
    current_month_trans = pd.read_sql_query(
        f"SELECT id, date, description, amount, type, status FROM transactions WHERE date LIKE '{current_month}%' ORDER BY date DESC", 
        conn
    )
    print(current_month_trans)
    
    # Estrutura da tabela
    print("\n=== ESTRUTURA DA TABELA DE TRANSAÇÕES ===")
    table_info = pd.read_sql_query("PRAGMA table_info(transactions)", conn)
    print(table_info)
    
    conn.close()

if __name__ == "__main__":
    check_db_state()
