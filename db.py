import sqlite3
from goals_db import init_goals_table
from db_backup import backup_transactions, restore_transactions, list_backups
import os

DB_PATH = 'financas.db'

# Função para inicializar o banco de dados
def init_db():
    # Verificar se o banco já existe e está inicializado
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Verificar se as tabelas existem
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {table[0] for table in c.fetchall()}
        
        if all(table in tables for table in ['transactions', 'categories', 'users', 'settings', 'goals']):
            conn.close()
            return  # Banco já está inicializado, não precisa fazer nada
        
        conn.close()

    # Se chegou aqui, precisa inicializar o banco
    # Fazer backup das transações existentes apenas se o arquivo existir
    if os.path.exists(DB_PATH):
        try:
            backup_file = backup_transactions()
            print(f"Backup criado em: {backup_file}")
        except Exception as e:
            print(f"Não foi possível fazer backup: {str(e)}")
            backup_file = None

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Inicializar tabela de metas primeiro
    init_goals_table()

    # Remover tabela categories se existir para recriar com a estrutura correta
    c.execute('DROP TABLE IF EXISTS categories')
    conn.commit()
    
    # Tabela de categorias
    c.execute('''CREATE TABLE IF NOT EXISTS categories
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  type TEXT NOT NULL,
                  categoria_tipo TEXT NOT NULL,
                  active BOOLEAN DEFAULT 1)''')
    conn.commit()
    
    # Adicionar colunas se não existirem
    try:
        c.execute('''ALTER TABLE transactions 
                     ADD COLUMN categoria_tipo TEXT DEFAULT 'outros' ''')
        conn.commit()
    except:
        pass  # Coluna já existe ou tabela não existe ainda
        
    try:
        c.execute('''ALTER TABLE transactions 
                     ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP''')
        conn.commit()
    except:
        pass  # Coluna já existe ou tabela não existe ainda
    
    # Tabela de usuários (opcional por enquanto)
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Tabela de transações completa
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER DEFAULT 1,
                  description TEXT NOT NULL,
                  amount REAL NOT NULL,
                  category TEXT NOT NULL,
                  date TEXT NOT NULL,
                  due_date TEXT,
                  type TEXT NOT NULL,
                  status TEXT DEFAULT 'pendente',
                  recurring BOOLEAN DEFAULT 0,
                  priority INTEGER DEFAULT 2,
                  quinzena INTEGER,
                  installments INTEGER DEFAULT 1,
                  current_installment INTEGER DEFAULT 1,
                  fixed_expense BOOLEAN DEFAULT 0,
                  categoria_tipo TEXT DEFAULT 'outros',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    
    # Tabela de metas completa
    c.execute('''CREATE TABLE IF NOT EXISTS goals
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER DEFAULT 1,
                  description TEXT NOT NULL,
                  target_amount REAL NOT NULL,
                  current_amount REAL DEFAULT 0,
                  deadline TEXT NOT NULL,
                  category TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Tabela de configurações
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  value TEXT NOT NULL)''')
    
    conn.commit()
    
    # Inicializar configurações depois das tabelas estarem criadas
    from settings import init_settings
    from categories import initialize_categories
    initialize_categories()
    init_settings()
    
    # Se tiver feito backup, restaura as transações
    if os.path.exists(DB_PATH) and 'backup_file' in locals() and backup_file:
        try:
            restore_transactions(backup_file)
        except Exception as e:
            print(f"Erro ao restaurar transações: {str(e)}")
    
    conn.close()
    
def get_transactions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT id, user_id, description, amount, category, date,
                       due_date, type, status, recurring, priority,
                       quinzena, installments, current_installment, fixed_expense,
                       categoria_tipo, created_at
                FROM transactions 
                ORDER BY date DESC''')
    transactions = c.fetchall()
    conn.close()
    return transactions
