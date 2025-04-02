"""
Módulo responsável pelas operações de banco de dados relacionadas a transações.
Utiliza Supabase como fonte de dados primária.
"""
import sqlite3
from datetime import datetime
from categories import get_categories
from db import DB_PATH
from supabase_db import (
    init_supabase, 
    add_transaction as supabase_add_transaction,
    get_transactions as supabase_get_transactions,
    update_transaction as supabase_update_transaction,
    delete_transaction as supabase_delete_transaction,
    get_goals as supabase_get_goals,
    add_goal as supabase_add_goal,
    update_goal as supabase_update_goal,
    delete_goal as supabase_delete_goal
)

def add_transaction(description, amount, category, date, type_trans, 
                   due_date=None, status="pago", recurring=False, 
                   priority=2, fixed_expense=False, installments=1, 
                   current_installment=1, user_id=1, categoria_tipo=None):
    """Adiciona uma nova transação ao banco de dados"""
    # Mapear os tipos para formato em inglês
    type_map = {
        "Receita": "Income",
        "Despesa": "Expense",
        "Investimento": "Investment"
    }
    
    # Verificar se o tipo já está no formato em inglês
    if type_trans in type_map.values():
        type_to_use = type_trans
    else:
        # Usar o tipo mapeado ou o original se não estiver no mapa
        type_to_use = type_map.get(type_trans, type_trans)
    
    # Validar o tipo de transação
    valid_types = ["Expense", "Income", "Investment"]
    if type_to_use not in valid_types:
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
        categoria_map = {cat["name"]: cat["categoria_tipo"].lower() for cat in categories if "name" in cat and "categoria_tipo" in cat}
        # Usar o tipo da categoria ou "outros" se não encontrado
        categoria_tipo = categoria_map.get(category, "outros")
    else:
        # Normalizar categoria_tipo para minúsculas
        categoria_tipo = str(categoria_tipo).lower()
    
    print(f"Adicionando transação: {description} | Categoria: {category} | Tipo Categoria: {categoria_tipo}")
    
    # Adicionar transação ao Supabase
    result = supabase_add_transaction(
        user_id=user_id, 
        description=description, 
        amount=amount, 
        category=category, 
        date=date, 
        due_date=due_date, 
        trans_type=type_to_use, 
        status=status, 
        recurring=recurring, 
        priority=priority, 
        quinzena=quinzena, 
        installments=installments, 
        current_installment=current_installment, 
        fixed_expense=fixed_expense, 
        categoria_tipo=categoria_tipo
    )
    
    return result

def view_transactions():
    """Retorna todas as transações do banco de dados como uma lista de dicionários"""
    # Obter transações diretamente do Supabase
    transactions = supabase_get_transactions()
    return transactions

def delete_transaction(transaction_id):
    """Deleta uma transação do banco de dados"""
    return supabase_delete_transaction(transaction_id)

def update_transaction(transaction_id, description=None, amount=None, category=None, 
                      date=None, type_trans=None, due_date=None, status=None, 
                      recurring=None, priority=None, fixed_expense=None, 
                      installments=None, current_installment=None, categoria_tipo=None):
    """Atualiza uma transação existente no banco de dados"""
    # Preparar objeto de dados para atualização
    data = {}
    
    if description is not None:
        data["description"] = description
    if amount is not None:
        data["amount"] = amount
    if category is not None:
        data["category"] = category
    if date is not None:
        data["date"] = date
        # Atualizar quinzena
        try:
            data_obj = datetime.strptime(date, "%Y-%m-%d")
            quinzena = 1 if data_obj.day <= 15 else 2
            data["quinzena"] = quinzena
        except:
            pass
    if type_trans is not None:
        # Mapear os tipos em português para inglês para padronização
        type_map = {
            "Receita": "Income",
            "Despesa": "Expense",
            "Investimento": "Investment"
        }
        # Verificar se o tipo já está no formato em inglês
        if type_trans in type_map.values():
            data["type"] = type_trans
        else:
            # Converter para inglês se estiver em português
            updated_type = type_map.get(type_trans, type_trans)
            data["type"] = updated_type
    if due_date is not None:
        data["due_date"] = due_date
    if status is not None:
        data["status"] = status
    if recurring is not None:
        data["recurring"] = recurring
    if priority is not None:
        data["priority"] = priority
    if fixed_expense is not None:
        data["fixed_expense"] = fixed_expense
    if installments is not None:
        data["installments"] = installments
    if current_installment is not None:
        data["current_installment"] = current_installment
    if categoria_tipo is not None:
        data["categoria_tipo"] = categoria_tipo
    
    # Atualizar transação no Supabase apenas se houver dados para atualizar
    if data:
        return supabase_update_transaction(transaction_id, data)
    
    return None

# Funções para gerenciar metas financeiras

def create_goal(name, target_value, type_goal="Savings", current_value=0, target_date=None, notes=None):
    """
    Cria uma nova meta financeira
    
    Args:
        name (str): Nome da meta
        target_value (float): Valor objetivo da meta
        type_goal (str): Tipo da meta (Savings, Emergency, Investment, etc)
        current_value (float): Valor atual já acumulado
        target_date (str): Data alvo para atingir a meta
        notes (str): Observações sobre a meta
        
    Returns:
        bool: True se a meta foi criada com sucesso
    """
    # Converter para formato esperado pelo Supabase
    return supabase_add_goal(
        user_id=1,
        description=name,
        target_amount=target_value,
        current_amount=current_value,
        deadline=target_date or datetime.now().strftime("%Y-%m-%d"),
        category=type_goal
    )

def view_goals():
    """
    Recupera todas as metas financeiras
    
    Returns:
        list: Lista com todas as metas
    """
    return supabase_get_goals()

def update_goal_progress(goal_id, current_value=None, target_value=None, target_date=None, notes=None):
    """
    Atualiza o progresso de uma meta financeira
    
    Args:
        goal_id (int): ID da meta a ser atualizada
        current_value (float): Novo valor atual
        target_value (float): Novo valor objetivo
        target_date (str): Nova data alvo
        notes (str): Novas observações
        
    Returns:
        bool: True se a atualização foi bem-sucedida
    """
    # Preparar dados para atualização
    data = {}
    
    if current_value is not None:
        data["current_amount"] = current_value
    if target_value is not None:
        data["target_amount"] = target_value
    if target_date is not None:
        data["deadline"] = target_date
    if notes is not None:
        data["notes"] = notes
    
    # Atualizar meta no Supabase apenas se houver dados para atualizar
    if data:
        return supabase_update_goal(goal_id, data)
    
    return None

def delete_goal(goal_id):
    """
    Remove uma meta financeira
    
    Args:
        goal_id (int): ID da meta a ser removida
        
    Returns:
        bool: True se a remoção foi bem-sucedida
    """
    return supabase_delete_goal(goal_id)
