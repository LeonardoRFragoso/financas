"""
Módulo para backup e restauração do banco de dados.
"""
import sqlite3
import json
from datetime import datetime
import os

def backup_transactions():
    """Faz backup das transações existentes."""
    conn = sqlite3.connect('financas.db')
    c = conn.cursor()
    
    # Backup de transações
    c.execute('''SELECT * FROM transactions''')
    transactions = c.fetchall()
    
    # Obtém os nomes das colunas
    c.execute('PRAGMA table_info(transactions)')
    columns = [col[1] for col in c.fetchall()]
    
    # Cria lista de dicionários com os dados
    transactions_data = []
    for transaction in transactions:
        transaction_dict = dict(zip(columns, transaction))
        transactions_data.append(transaction_dict)
    
    # Cria diretório de backup se não existir
    if not os.path.exists('backup'):
        os.makedirs('backup')
    
    # Salva em arquivo JSON com timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'backup/transactions_backup_{timestamp}.json'
    
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(transactions_data, f, ensure_ascii=False, indent=4, default=str)
    
    conn.close()
    return backup_file

def restore_transactions(backup_file):
    """Restaura transações de um arquivo de backup."""
    # Lê o arquivo de backup
    with open(backup_file, 'r', encoding='utf-8') as f:
        transactions_data = json.load(f)
    
    conn = sqlite3.connect('financas.db')
    c = conn.cursor()
    
    # Cria um índice das transações existentes usando uma tupla de campos únicos
    c.execute('''SELECT date, description, amount FROM transactions''')
    existing_transactions = {(str(date), str(desc), float(amount)) 
                           for date, desc, amount in c.fetchall()}
    
    # Insere as transações de volta no banco, ignorando duplicatas
    duplicates = 0
    inserted = 0
    for transaction in transactions_data:
        # Remove o ID para permitir auto-incremento
        if 'id' in transaction:
            del transaction['id']
        
        # Cria uma tupla de identificação única
        unique_key = (
            str(transaction.get('date', '')),
            str(transaction.get('description', '')),
            float(transaction.get('amount', 0))
        )
        
        # Pula se já existe
        if unique_key in existing_transactions:
            duplicates += 1
            continue
        
        columns = ', '.join(transaction.keys())
        placeholders = ', '.join(['?' for _ in transaction])
        query = f'INSERT INTO transactions ({columns}) VALUES ({placeholders})'
        
        try:
            c.execute(query, list(transaction.values()))
            existing_transactions.add(unique_key)
            inserted += 1
        except Exception as e:
            print(f"Erro ao inserir transação: {str(e)}")
            continue
    
    conn.commit()
    conn.close()
    
    print(f"Restauração concluída: {inserted} transações inseridas, {duplicates} duplicatas ignoradas")

def list_backups():
    """Lista todos os arquivos de backup disponíveis."""
    if not os.path.exists('backup'):
        return []
    
    backups = []
    for file in os.listdir('backup'):
        if file.startswith('transactions_backup_') and file.endswith('.json'):
            backup_path = os.path.join('backup', file)
            timestamp = os.path.getmtime(backup_path)
            backups.append({
                'file': file,
                'path': backup_path,
                'timestamp': datetime.fromtimestamp(timestamp)
            })
    
    return sorted(backups, key=lambda x: x['timestamp'], reverse=True)
