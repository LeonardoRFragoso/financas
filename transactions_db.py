"""
Módulo responsável pelas operações de banco de dados relacionadas a transações.
"""
import sqlite3
from datetime import datetime
from categories import get_categories
from db import DB_PATH

def add_transaction(description, amount, category, date, type_trans, 
                   due_date=None, status="pendente", recurring=False, 
                   priority=2, fixed_expense=False, installments=1, 
                   current_installment=1, user_id=1, categoria_tipo=None):
    """Adiciona uma nova transação ao banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Validar o tipo de transação
    valid_types = ["Despesa", "Receita", "Investimento"]
    if type_trans not in valid_types:
        raise ValueError(f"Tipo de transação inválido. Deve ser um dos seguintes: {', '.join(valid_types)}")
    
    # Calcular quinzena se aplicável
    quinzena = None
    if date:
        try:
            data_obj = datetime.strptime(date, "%Y-%m-%d")
            dia = data_obj.day
            quinzena = 1 if dia <= 15 else 2
        except:
            pass
    
    # Se categoria_tipo não foi fornecido, determinar com base na categoria
    if not categoria_tipo:
        # Buscar categorias
        categories = get_categories()
        categoria_map = {cat[1]: cat[3] for cat in categories if len(cat) > 3}
        # Usar o tipo da categoria ou "outros" se não encontrado
        categoria_tipo = categoria_map.get(category, "outros")
    
    c.execute('''INSERT INTO transactions 
                (description, amount, category, date, type, due_date, 
                 status, recurring, priority, quinzena, installments, 
                 current_installment, fixed_expense, user_id, categoria_tipo) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (description, amount, category, date, type_trans, due_date, 
               status, recurring, priority, quinzena, installments, 
               current_installment, fixed_expense, user_id, categoria_tipo))
    conn.commit()
    conn.close()

def view_transactions():
    """Retorna todas as transações do banco de dados como uma lista de dicionários"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Obter os nomes das colunas
    c.execute('PRAGMA table_info(transactions)')
    columns = [col[1] for col in c.fetchall()]
    
    # Buscar as transações
    c.execute('''SELECT id, user_id, description, amount, category, date, 
                 due_date, type, status, recurring, priority, quinzena, 
                 installments, current_installment, fixed_expense, 
                 COALESCE(categoria_tipo, 'outros') as categoria_tipo,
                 date as created_at
                 FROM transactions''')
    
    # Converter para lista de dicionários
    transactions = []
    for row in c.fetchall():
        transaction = {}
        for i, value in enumerate(row):
            transaction[columns[i]] = value
        transactions.append(transaction)
    
    conn.close()
    return transactions

def delete_transaction(transaction_id):
    """Deleta uma transação do banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
    conn.commit()
    conn.close()

def update_transaction(transaction_id, description=None, amount=None, category=None, 
                      date=None, type_trans=None, due_date=None, status=None, 
                      recurring=None, priority=None, fixed_expense=None, 
                      installments=None, current_installment=None, categoria_tipo=None):
    """Atualiza uma transação existente no banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Buscar dados atuais da transação
    c.execute('SELECT * FROM transactions WHERE id = ?', (transaction_id,))
    current_data = c.fetchone()
    
    if not current_data:
        conn.close()
        raise ValueError(f"Transação com ID {transaction_id} não encontrada")
    
    # Preparar os campos para atualização
    updates = []
    values = []
    
    if description is not None:
        updates.append("description = ?")
        values.append(description)
    if amount is not None:
        updates.append("amount = ?")
        values.append(amount)
    if category is not None:
        updates.append("category = ?")
        values.append(category)
    if date is not None:
        updates.append("date = ?")
        values.append(date)
        # Atualizar quinzena
        try:
            data_obj = datetime.strptime(date, "%Y-%m-%d")
            quinzena = 1 if data_obj.day <= 15 else 2
            updates.append("quinzena = ?")
            values.append(quinzena)
        except:
            pass
    if type_trans is not None:
        updates.append("type = ?")
        values.append(type_trans)
    if due_date is not None:
        updates.append("due_date = ?")
        values.append(due_date)
    if status is not None:
        updates.append("status = ?")
        values.append(status)
    if recurring is not None:
        updates.append("recurring = ?")
        values.append(recurring)
    if priority is not None:
        updates.append("priority = ?")
        values.append(priority)
    if fixed_expense is not None:
        updates.append("fixed_expense = ?")
        values.append(fixed_expense)
    if installments is not None:
        updates.append("installments = ?")
        values.append(installments)
    if current_installment is not None:
        updates.append("current_installment = ?")
        values.append(current_installment)
    if categoria_tipo is not None:
        updates.append("categoria_tipo = ?")
        values.append(categoria_tipo)
    
    if updates:
        # Construir e executar a query de atualização
        query = f"UPDATE transactions SET {', '.join(updates)} WHERE id = ?"
        values.append(transaction_id)
        c.execute(query, values)
        conn.commit()
    
    conn.close()
