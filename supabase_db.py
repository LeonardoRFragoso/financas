import os
import streamlit as st
from supabase import create_client
from datetime import datetime
import pandas as pd
import json

# Inicializar cliente Supabase
def init_supabase():
    """Inicializa e retorna o cliente Supabase"""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao conectar com Supabase: {str(e)}")
        return None

# Inicializar tabelas no Supabase
def init_supabase_tables():
    """Cria as tabelas necessárias no Supabase, se não existirem"""
    supabase = init_supabase()
    if not supabase:
        return False
    
    # As tabelas são criadas através da interface do Supabase
    # Este método é apenas para verificar a conexão
    try:
        # Verificar se podemos acessar a tabela de transactions
        supabase.table("transactions").select("id").limit(1).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao verificar tabelas no Supabase: {str(e)}")
        return False

# Funções para transações
def get_transactions():
    """Obtém todas as transações do Supabase"""
    supabase = init_supabase()
    if not supabase:
        return []
    
    response = supabase.table("transactions").select("*").order("date", desc=True).execute()
    return response.data

def add_transaction(user_id, description, amount, category, date, due_date, 
                   trans_type, status, recurring, priority, quinzena, 
                   installments, current_installment, fixed_expense, categoria_tipo):
    """Adiciona uma nova transação ao Supabase"""
    supabase = init_supabase()
    if not supabase:
        return False
    
    transaction_data = {
        "user_id": user_id,
        "description": description,
        "amount": amount,
        "category": category,
        "date": date,
        "due_date": due_date,
        "type": trans_type,
        "status": status,
        "recurring": recurring,
        "priority": priority,
        "quinzena": quinzena,
        "installments": installments,
        "current_installment": current_installment,
        "fixed_expense": fixed_expense,
        "categoria_tipo": categoria_tipo,
        "created_at": datetime.now().isoformat()
    }
    
    response = supabase.table("transactions").insert(transaction_data).execute()
    return response.data

def update_transaction(transaction_id, data):
    """Atualiza uma transação existente no Supabase"""
    supabase = init_supabase()
    if not supabase:
        return False
    
    response = supabase.table("transactions").update(data).eq("id", transaction_id).execute()
    return response.data

def delete_transaction(transaction_id):
    """Remove uma transação do Supabase"""
    supabase = init_supabase()
    if not supabase:
        return False
    
    response = supabase.table("transactions").delete().eq("id", transaction_id).execute()
    return response.data

# Funções para categorias
def get_categories():
    """Obtém todas as categorias do Supabase"""
    supabase = init_supabase()
    if not supabase:
        return []
    
    response = supabase.table("categories").select("*").order("name").execute()
    return response.data

def add_category(name, category_type, categoria_tipo, active=True):
    """Adiciona uma nova categoria ao Supabase"""
    supabase = init_supabase()
    if not supabase:
        return False
    
    category_data = {
        "name": name,
        "type": category_type,
        "categoria_tipo": categoria_tipo,
        "active": active
    }
    
    response = supabase.table("categories").insert(category_data).execute()
    return response.data

# Funções para metas
def get_goals():
    """Obtém todas as metas do Supabase"""
    supabase = init_supabase()
    if not supabase:
        return []
    
    response = supabase.table("goals").select("*").execute()
    return response.data

def add_goal(user_id, description, target_amount, current_amount, deadline, category):
    """Adiciona uma nova meta ao Supabase"""
    supabase = init_supabase()
    if not supabase:
        return False
    
    goal_data = {
        "user_id": user_id,
        "description": description,
        "target_amount": target_amount,
        "current_amount": current_amount,
        "deadline": deadline,
        "category": category,
        "created_at": datetime.now().isoformat()
    }
    
    response = supabase.table("goals").insert(goal_data).execute()
    return response.data

# Funções para configurações
def get_settings():
    """Obtém todas as configurações do Supabase"""
    supabase = init_supabase()
    if not supabase:
        return {}
    
    response = supabase.table("settings").select("*").execute()
    
    # Converter para dicionário name:value
    settings = {}
    for item in response.data:
        settings[item["name"]] = item["value"]
    
    return settings

def update_setting(name, value):
    """Atualiza ou cria uma configuração no Supabase"""
    supabase = init_supabase()
    if not supabase:
        return False
    
    # Verificar se a configuração já existe
    response = supabase.table("settings").select("id").eq("name", name).execute()
    
    if response.data:
        # Atualizar configuração existente
        setting_id = response.data[0]["id"]
        supabase.table("settings").update({"value": value}).eq("id", setting_id).execute()
    else:
        # Criar nova configuração
        supabase.table("settings").insert({"name": name, "value": value}).execute()
    
    return True

# Função para migrar dados do SQLite para Supabase
def migrate_data_from_sqlite(sqlite_db_path="financas.db"):
    """Migra dados do SQLite local para o Supabase"""
    import sqlite3
    
    try:
        # Conectar ao SQLite
        conn = sqlite3.connect(sqlite_db_path)
        conn.row_factory = sqlite3.Row
        
        # Obter dados do SQLite
        transactions = []
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions")
        for row in cursor.fetchall():
            transactions.append(dict(row))
        
        categories = []
        cursor.execute("SELECT * FROM categories")
        for row in cursor.fetchall():
            categories.append(dict(row))
        
        goals = []
        cursor.execute("SELECT * FROM goals")
        for row in cursor.fetchall():
            goals.append(dict(row))
        
        settings = []
        cursor.execute("SELECT * FROM settings")
        for row in cursor.fetchall():
            settings.append(dict(row))
        
        conn.close()
        
        # Enviar dados para o Supabase
        supabase = init_supabase()
        if not supabase:
            return False
        
        # Inserir categorias
        if categories:
            supabase.table("categories").insert(categories).execute()
        
        # Inserir transações
        if transactions:
            # Ajustar formato dos dados se necessário
            for transaction in transactions:
                # Converter campos booleanos (SQLite armazena como 0/1)
                for field in ["recurring", "fixed_expense"]:
                    if field in transaction:
                        transaction[field] = bool(transaction[field])
            
            supabase.table("transactions").insert(transactions).execute()
        
        # Inserir metas
        if goals:
            supabase.table("goals").insert(goals).execute()
        
        # Inserir configurações
        if settings:
            supabase.table("settings").insert(settings).execute()
        
        return True
    
    except Exception as e:
        st.error(f"Erro durante a migração: {str(e)}")
        return False
