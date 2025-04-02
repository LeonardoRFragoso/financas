"""
Script para inicialização do banco de dados.
Cria todas as tabelas necessárias se elas não existirem.
"""
import sqlite3
from db import DB_PATH

def init_database():
    """Inicializa o banco de dados com todas as tabelas necessárias"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Criar tabela de transações se não existir
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL DEFAULT 1,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        date TEXT NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('Income', 'Expense', 'Investment')),
        due_date TEXT,
        status TEXT DEFAULT 'pendente',
        recurring BOOLEAN DEFAULT FALSE,
        priority INTEGER DEFAULT 2,
        quinzena INTEGER,
        installments INTEGER DEFAULT 1,
        current_installment INTEGER DEFAULT 1,
        fixed_expense BOOLEAN DEFAULT FALSE,
        categoria_tipo TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Criar tabela de metas se não existir
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        name TEXT NOT NULL,
        target_value REAL NOT NULL,
        current_value REAL DEFAULT 0,
        created_date TEXT DEFAULT CURRENT_TIMESTAMP,
        target_date TEXT,
        notes TEXT
    )
    """)
    
    # Criar tabela de categorias se não existir
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        type TEXT NOT NULL CHECK(type IN ('necessidade', 'desejo', 'investimento', 'outros')),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Inserir algumas categorias padrão se a tabela estiver vazia
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        default_categories = [
            ('Alimentação', 'Gastos com alimentação', 'necessidade'),
            ('Moradia', 'Aluguel, contas, etc', 'necessidade'),
            ('Transporte', 'Combustível, transporte público', 'necessidade'),
            ('Saúde', 'Plano de saúde, medicamentos', 'necessidade'),
            ('Lazer', 'Entretenimento, hobbies', 'desejo'),
            ('Educação', 'Cursos, material escolar', 'investimento'),
            ('Investimentos', 'Aplicações financeiras', 'investimento'),
            ('Outros', 'Despesas diversas', 'outros')
        ]
        cursor.executemany(
            "INSERT INTO categories (name, description, type) VALUES (?, ?, ?)",
            default_categories
        )
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("Inicializando banco de dados...")
    init_database()
    print("Banco de dados inicializado com sucesso!")
