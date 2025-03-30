import sqlite3
from db import DB_PATH

def initialize_categories():
    """Inicializa as categorias padrão no banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Criar tabela de categorias se não existir
    c.execute('''CREATE TABLE IF NOT EXISTS categories
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  type TEXT NOT NULL,
                  categoria_tipo TEXT NOT NULL,
                  active BOOLEAN DEFAULT 1)''')
    
    # Verificar se já existem categorias
    c.execute("SELECT COUNT(*) FROM categories")
    count = c.fetchone()[0]
    
    if count == 0:
        # Despesas
        despesas_necessidades = [
            ("Moradia", "necessidade"),
            ("Alimentação", "necessidade"),
            ("Transporte", "necessidade"),
            ("Saúde", "necessidade"),
            ("Educação", "necessidade"),
            ("Contas", "necessidade"),
            ("Seguros", "necessidade")
        ]
        
        despesas_desejos = [
            ("Lazer", "desejo"),
            ("Restaurantes", "desejo"),
            ("Shopping", "desejo"),
            ("Entretenimento", "desejo"),
            ("Viagens", "desejo"),
            ("Presentes", "desejo"),
            ("Assinaturas", "desejo")
        ]
        
        despesas_poupanca = [
            ("Investimentos", "poupanca"),
            ("Previdência", "poupanca"),
            ("Reserva de Emergência", "poupanca"),
            ("Objetivos", "poupanca")
        ]
        
        despesas_outros = [
            ("Outros", "outros")
        ]
        
        # Inserir categorias de despesas
        for categoria, tipo in despesas_necessidades + despesas_desejos + despesas_poupanca + despesas_outros:
            c.execute("INSERT INTO categories (name, type, categoria_tipo) VALUES (?, ?, ?)",
                     (categoria, "Despesa", tipo))
        
        # Receitas
        receitas = [
            ("Salário", "necessidade"),
            ("Freelance", "necessidade"),
            ("Investimentos", "poupanca"),
            ("Reembolsos", "outros"),
            ("Presentes", "outros"),
            ("Outros", "outros")
        ]
        
        # Inserir categorias de receitas
        for categoria, tipo in receitas:
            c.execute("INSERT INTO categories (name, type, categoria_tipo) VALUES (?, ?, ?)",
                     (categoria, "Receita", tipo))
    
    conn.commit()
    conn.close()

def get_categories(type_filter=None, category_type_filter=None):
    """
    Retorna categorias do banco de dados
    
    Args:
        type_filter (str, optional): Filtrar por tipo (Despesa/Receita)
        category_type_filter (str, optional): Filtrar por categoria_tipo (necessidade/desejo/poupanca/outros)
    
    Returns:
        list: Lista de tuplas com as categorias
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if type_filter and category_type_filter:
        c.execute("SELECT * FROM categories WHERE type = ? AND categoria_tipo = ? AND active = 1 ORDER BY name", 
                 (type_filter, category_type_filter))
    elif type_filter:
        c.execute("SELECT * FROM categories WHERE type = ? AND active = 1 ORDER BY name", (type_filter,))
    elif category_type_filter:
        c.execute("SELECT * FROM categories WHERE categoria_tipo = ? AND active = 1 ORDER BY name", (category_type_filter,))
    else:
        c.execute("SELECT * FROM categories WHERE active = 1 ORDER BY name")
    
    categories = c.fetchall()
    conn.close()
    
    return categories

def add_category(name, type_trans, categoria_tipo="outros"):
    """
    Adiciona uma nova categoria
    
    Args:
        name (str): Nome da categoria
        type_trans (str): Tipo (Despesa/Receita)
        categoria_tipo (str): Tipo da categoria (necessidade/desejo/poupanca/outros)
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("INSERT INTO categories (name, type, categoria_tipo) VALUES (?, ?, ?)",
             (name, type_trans, categoria_tipo))
    
    conn.commit()
    conn.close()

def delete_category(category_id):
    """
    Marca uma categoria como inativa (não deleta realmente)
    
    Args:
        category_id (int): ID da categoria
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("UPDATE categories SET active = 0 WHERE id = ?", (category_id,))
    
    conn.commit()
    conn.close()

def recategorize_transactions(type_filter=None):
    """
    Atualiza a classificação 50/30/20 de todas as transações com base nas categorias atuais
    
    Args:
        type_filter (str, optional): Filtrar por tipo (Despesa/Receita)
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Obter o mapeamento de categorias para tipos
    c.execute("SELECT name, categoria_tipo FROM categories WHERE active = 1")
    categoria_map = {row[0]: row[1] for row in c.fetchall()}
    
    # Preparar a query para atualizar as transações
    if type_filter:
        c.execute("SELECT id, category FROM transactions WHERE type = ?", (type_filter,))
    else:
        c.execute("SELECT id, category FROM transactions")
    
    # Atualizar cada transação
    for row in c.fetchall():
        transaction_id, category = row
        categoria_tipo = categoria_map.get(category, "outros")
        
        c.execute("UPDATE transactions SET categoria_tipo = ? WHERE id = ?", 
                 (categoria_tipo, transaction_id))
    
    conn.commit()
    conn.close()

def update_category(category_id, name=None, type_trans=None, categoria_tipo=None, active=None):
    """
    Atualiza uma categoria existente
    
    Args:
        category_id (int): ID da categoria
        name (str, optional): Novo nome da categoria
        type_trans (str, optional): Novo tipo (Despesa/Receita)
        categoria_tipo (str, optional): Novo tipo da categoria (necessidade/desejo/poupanca/outros)
        active (bool, optional): Status de ativação da categoria
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Buscar dados atuais da categoria
    c.execute('SELECT * FROM categories WHERE id = ?', (category_id,))
    current_data = c.fetchone()
    
    if not current_data:
        conn.close()
        raise ValueError(f"Categoria com ID {category_id} não encontrada")
    
    # Preparar os campos para atualização
    updates = []
    values = []
    
    if name is not None:
        updates.append("name = ?")
        values.append(name)
    if type_trans is not None:
        updates.append("type = ?")
        values.append(type_trans)
    if categoria_tipo is not None:
        updates.append("categoria_tipo = ?")
        values.append(categoria_tipo)
    if active is not None:
        updates.append("active = ?")
        values.append(1 if active else 0)
    
    if updates:
        # Construir e executar a query de atualização
        query = f"UPDATE categories SET {', '.join(updates)} WHERE id = ?"
        values.append(category_id)
        c.execute(query, values)
        
        # Se a categoria foi atualizada, recategorizar transações
        if type_trans is not None or categoria_tipo is not None:
            recategorize_transactions()
        
        conn.commit()
    
    conn.close()

if __name__ == '__main__':
    initialize_categories()
