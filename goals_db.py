"""
Módulo responsável pelas operações de banco de dados das metas financeiras.
"""
from datetime import datetime
from typing import Dict, List, Optional
import streamlit as st
from supabase_db import init_supabase

def init_goals_table():
    """Inicializa a tabela de metas no banco de dados."""
    # A tabela já é inicializada no Supabase
    pass

def add_goal(goal_data: Dict) -> int:
    """Adiciona uma nova meta ao banco de dados."""
    try:
        # Garantir que todos os campos obrigatórios estejam presentes
        if not all(key in goal_data for key in ['title', 'target_amount']):
            raise ValueError("Título e valor alvo são obrigatórios")
        
        # Inicializar Supabase
        supabase = init_supabase()
        if not supabase:
            st.error("Erro ao conectar ao banco de dados.")
            return None
        
        # Preparar dados para inserção
        goal_data_to_insert = {
            "title": goal_data['title'],
            "description": goal_data.get('description', ''),
            "target_amount": float(goal_data['target_amount']),
            "current_amount": float(goal_data.get('current_amount', 0)),
            "deadline": goal_data.get('deadline'),
            "category": goal_data.get('category'),
            "status": goal_data.get('status', 'Em Andamento'),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Inserir no Supabase
        response = supabase.table("goals").insert(goal_data_to_insert).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]['id']
        return None
        
    except Exception as e:
        print(f"Erro ao adicionar meta: {str(e)}")
        st.error(f"Erro ao adicionar meta: {str(e)}")
        return None

def update_goal(goal_id: int, goal_data: Dict) -> bool:
    """Atualiza uma meta existente."""
    try:
        # Inicializar Supabase
        supabase = init_supabase()
        if not supabase:
            st.error("Erro ao conectar ao banco de dados.")
            return False
        
        # Preparar dados para atualização
        goal_data_to_update = {}
        
        if 'title' in goal_data:
            goal_data_to_update['title'] = goal_data['title']
        
        if 'description' in goal_data:
            goal_data_to_update['description'] = goal_data['description']
        
        if 'target_amount' in goal_data:
            goal_data_to_update['target_amount'] = float(goal_data['target_amount'])
        
        if 'current_amount' in goal_data:
            goal_data_to_update['current_amount'] = float(goal_data['current_amount'])
        
        if 'deadline' in goal_data:
            goal_data_to_update['deadline'] = goal_data['deadline']
        
        if 'category' in goal_data:
            goal_data_to_update['category'] = goal_data['category']
        
        if 'status' in goal_data:
            goal_data_to_update['status'] = goal_data['status']
        
        goal_data_to_update['updated_at'] = datetime.now().isoformat()
        
        if not goal_data_to_update:
            return False
        
        # Atualizar no Supabase
        response = supabase.table("goals").update(goal_data_to_update).eq("id", goal_id).execute()
        
        return response.data is not None and len(response.data) > 0
        
    except Exception as e:
        print(f"Erro ao atualizar meta: {str(e)}")
        st.error(f"Erro ao atualizar meta: {str(e)}")
        return False

def delete_goal(goal_id: int) -> bool:
    """Exclui uma meta do banco de dados."""
    try:
        # Inicializar Supabase
        supabase = init_supabase()
        if not supabase:
            st.error("Erro ao conectar ao banco de dados.")
            return False
        
        # Excluir do Supabase
        response = supabase.table("goals").delete().eq("id", goal_id).execute()
        
        return response.data is not None
        
    except Exception as e:
        print(f"Erro ao excluir meta: {str(e)}")
        st.error(f"Erro ao excluir meta: {str(e)}")
        return False

def view_goals() -> List[Dict]:
    """Retorna todas as metas cadastradas."""
    try:
        # Inicializar Supabase
        supabase = init_supabase()
        if not supabase:
            st.error("Erro ao conectar ao banco de dados.")
            return []
        
        # Buscar todas as metas
        response = supabase.table("goals").select("*").order("created_at", desc=True).execute()
        
        goals = response.data
        
        # Converter valores numéricos para float
        for goal in goals:
            goal['target_amount'] = float(goal['target_amount'])
            goal['current_amount'] = float(goal['current_amount'])
        
        return goals
        
    except Exception as e:
        print(f"Erro ao buscar metas: {str(e)}")
        st.error(f"Erro ao buscar metas: {str(e)}")
        return []

def get_goal(goal_id: int) -> Optional[Dict]:
    """Retorna uma meta específica pelo ID."""
    try:
        # Inicializar Supabase
        supabase = init_supabase()
        if not supabase:
            st.error("Erro ao conectar ao banco de dados.")
            return None
        
        # Buscar meta pelo ID
        response = supabase.table("goals").select("*").eq("id", goal_id).execute()
        
        if response.data and len(response.data) > 0:
            goal = response.data[0]
            goal['target_amount'] = float(goal['target_amount'])
            goal['current_amount'] = float(goal['current_amount'])
            return goal
        
        return None
        
    except Exception as e:
        print(f"Erro ao buscar meta: {str(e)}")
        st.error(f"Erro ao buscar meta: {str(e)}")
        return None

def update_goal_amount(goal_id: int, new_amount: float) -> bool:
    """Atualiza apenas o valor atual de uma meta."""
    try:
        # Inicializar Supabase
        supabase = init_supabase()
        if not supabase:
            st.error("Erro ao conectar ao banco de dados.")
            return False
        
        # Buscar meta atual para verificar se o novo valor não excede o alvo
        goal = get_goal(goal_id)
        if not goal:
            return False
        
        # Garantir que o novo valor não exceda o alvo
        if new_amount > goal['target_amount']:
            new_amount = goal['target_amount']
        
        # Atualizar o valor atual e verificar se a meta foi concluída
        update_data = {
            'current_amount': new_amount,
            'updated_at': datetime.now().isoformat()
        }
        
        # Se o valor atual atingiu o alvo, atualizar o status para concluído
        if new_amount >= goal['target_amount']:
            update_data['status'] = 'Concluída'
        
        # Atualizar no Supabase
        response = supabase.table("goals").update(update_data).eq("id", goal_id).execute()
        
        return response.data is not None and len(response.data) > 0
        
    except Exception as e:
        print(f"Erro ao atualizar valor da meta: {str(e)}")
        st.error(f"Erro ao atualizar valor da meta: {str(e)}")
        return False
