import os
import json
import datetime
import streamlit as st

def backup_transactions(transactions, user_id=1):
    """
    Cria um backup das transações
    
    Esta é uma versão simplificada que mantém compatibilidade com o código existente.
    """
    os.makedirs('backup', exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup/transactions_backup_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(transactions, f, ensure_ascii=False, indent=4)
    
    return filename

def restore_transactions(filename):
    """
    Restaura transações de um arquivo de backup
    
    Esta é uma versão simplificada que mantém compatibilidade com o código existente.
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            transactions = json.load(f)
        return transactions
    except Exception as e:
        st.error(f"Erro ao restaurar backup: {e}")
        return None

def list_backups():
    """
    Lista todos os arquivos de backup disponíveis
    
    Esta é uma versão simplificada que mantém compatibilidade com o código existente.
    """
    os.makedirs('backup', exist_ok=True)
    backup_dir = 'backup'
    backup_files = [f for f in os.listdir(backup_dir) if f.startswith('transactions_backup_') and f.endswith('.json')]
    backup_files.sort(reverse=True)  # Ordenar do mais recente para o mais antigo
    return backup_files
