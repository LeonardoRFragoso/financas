import sqlite3
from db import DB_PATH
from supabase_db import (
    init_supabase,
    get_categories as supabase_get_categories,
    add_category as supabase_add_category,
    update_category as supabase_update_category
)

def initialize_categories():
    """Inicializa as categorias padrão no banco de dados"""
    # Verificar se já existem categorias
    categories = get_categories()
    
    if not categories:
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
            add_category(categoria, "Despesa", tipo)
        
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
            add_category(categoria, "Receita", tipo)

def get_categories(type_filter=None, category_type_filter=None):
    """
    Retorna categorias do banco de dados
    
    Args:
        type_filter (str, optional): Filtrar por tipo (Despesa/Receita)
        category_type_filter (str, optional): Filtrar por categoria_tipo (necessidade/desejo/poupanca/outros)
    
    Returns:
        list: Lista de dicionários com as categorias
    """
    # Obter todas as categorias do Supabase
    categories = supabase_get_categories()
    
    # Aplicar filtros se necessário
    if categories:
        # Filtrar por tipo se especificado
        if type_filter:
            categories = [cat for cat in categories if cat.get("type") == type_filter]
            
        # Filtrar por categoria_tipo se especificado
        if category_type_filter:
            # Normalizar o filtro para minúsculas
            category_type_filter = str(category_type_filter).lower()
            categories = [cat for cat in categories if str(cat.get("categoria_tipo", "")).lower() == category_type_filter]
        
        # Filtrar apenas categorias ativas
        categories = [cat for cat in categories if cat.get("active") == True]
        
        # Normalizar categoria_tipo para minúsculas em todas as categorias
        for cat in categories:
            if "categoria_tipo" in cat:
                cat["categoria_tipo"] = str(cat["categoria_tipo"]).lower()
        
        # Ordenar por nome
        categories.sort(key=lambda x: x.get("name", ""))
    
    return categories

def add_category(name, type_trans, categoria_tipo="outros"):
    """
    Adiciona uma nova categoria
    
    Args:
        name (str): Nome da categoria
        type_trans (str): Tipo (Despesa/Receita)
        categoria_tipo (str): Tipo da categoria (necessidade/desejo/poupanca/outros)
    """
    return supabase_add_category(
        name=name,
        category_type=type_trans,
        categoria_tipo=categoria_tipo
    )

def delete_category(category_id):
    """
    Marca uma categoria como inativa (não deleta realmente)
    
    Args:
        category_id (int): ID da categoria
    """
    # No Supabase, usamos update para marcar como inativo
    return supabase_update_category(category_id, {"active": False})

def recategorize_transactions(type_filter=None):
    """
    Atualiza a classificação 50/30/20 de todas as transações com base nas categorias atuais
    
    Args:
        type_filter (str, optional): Filtrar por tipo (Despesa/Receita)
    """
    # Para evitar importação circular, importamos aqui
    from supabase_db import get_transactions, update_transaction
    
    # Obter todas as transações
    transactions = get_transactions()
    
    # Criar mapeamento de categorias para tipos
    all_categories = get_categories()
    cat_map = {cat.get("name"): cat.get("categoria_tipo") for cat in all_categories}
    
    # Filtrar por tipo se especificado
    if type_filter:
        transactions = [t for t in transactions if t.get("type") == type_filter]
    
    # Atualizar categoria_tipo de cada transação
    for transaction in transactions:
        transaction_id = transaction.get("id")
        if not transaction_id:
            continue
            
        category = transaction.get("category")
        if not category or category not in cat_map:
            continue
            
        new_categoria_tipo = cat_map.get(category)
        if new_categoria_tipo and new_categoria_tipo != transaction.get("categoria_tipo"):
            update_transaction(transaction_id, {"categoria_tipo": new_categoria_tipo})

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
    # Preparar dados para atualização
    data = {}
    
    if name is not None:
        data["name"] = name
    if type_trans is not None:
        data["type"] = type_trans
    if categoria_tipo is not None:
        data["categoria_tipo"] = categoria_tipo
    if active is not None:
        data["active"] = active
    
    # Atualizar categoria no Supabase
    if data:
        return supabase_update_category(category_id, data)
    
    return None

if __name__ == '__main__':
    initialize_categories()
