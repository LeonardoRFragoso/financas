import sqlite3

DB_PATH = 'financas.db'

# Função para inicializar o banco de dados
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

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
    
    # Inicializar categorias após criar as tabelas
    from categories import initialize_categories
    initialize_categories()
    
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
    conn.close()
    
    # Inicializar configurações depois das tabelas estarem criadas
    from settings import init_settings
    
    init_settings()

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
