"""
Módulo responsável pela interface da página de metas financeiras.
"""
import streamlit as st
from datetime import datetime, date
import pandas as pd
import plotly.express as px
from goals_db import (
    init_goals_table, add_goal, update_goal, 
    delete_goal, view_goals, get_goal, update_goal_amount
)

def show_goals():
    """Mostra a página de metas financeiras."""
    st.title(" Metas Financeiras")
    
    # Inicializar tabela se necessário
    init_goals_table()
    
    # Inicializar estado da sessão se necessário
    if 'editing_goal' not in st.session_state:
        st.session_state.editing_goal = None
    
    if 'updating_goal_amount' not in st.session_state:
        st.session_state.updating_goal_amount = None
    
    # Tabs para organizar o conteúdo
    if st.session_state.editing_goal:
        show_goal_form()  # Mostrar formulário de edição primeiro
    elif st.session_state.updating_goal_amount:
        show_goal_amount_form()  # Mostrar formulário de atualização de valor
    else:
        tab1, tab2 = st.tabs([" Minhas Metas", " Nova Meta"])
        
        with tab1:
            show_goals_list()
        
        with tab2:
            show_goal_form()

def show_goals_list():
    """Mostra a lista de metas cadastradas."""
    goals = view_goals()
    
    if not goals:
        st.info("Nenhuma meta cadastrada ainda.")
        return
    
    # Converter para DataFrame para melhor manipulação
    df = pd.DataFrame(goals)
    
    # Converter campos de data
    df['deadline'] = pd.to_datetime(df['deadline'])
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['updated_at'] = pd.to_datetime(df['updated_at'])
    
    # Calcular progresso
    df['progress'] = (df['current_amount'] / df['target_amount'] * 100).round(2)
    
    # Visão geral em cards
    for _, goal in df.iterrows():
        with st.expander(f" {goal['title']}", expanded=True):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Descrição:** {goal['description'] or 'Sem descrição'}")
                st.markdown(f"**Categoria:** {goal['category'] or 'Não definida'}")
                st.markdown(f"**Status:** {goal['status']}")
                if not pd.isna(goal['deadline']):
                    st.markdown(f"**Prazo:** {goal['deadline'].strftime('%d/%m/%Y')}")
                
                # Barra de progresso
                progress = min(100, goal['progress'])
                st.progress(progress / 100)
                st.markdown(f"**Progresso:** R$ {goal['current_amount']:,.2f} de R$ {goal['target_amount']:,.2f} ({progress:.1f}%)")
            
            with col2:
                col2.markdown("### Ações")
                
                # Botão de atualizar valor
                if st.button("💰 Atualizar Valor", key=f"update_amount_{goal['id']}"):
                    st.session_state.updating_goal_amount = dict(goal)
                    st.rerun()
                
                # Botão de editar
                if st.button("✏️ Editar", key=f"edit_{goal['id']}"):
                    st.session_state.editing_goal = dict(goal)
                    st.rerun()
                
                # Botão de excluir
                if st.button("🗑️ Excluir", key=f"delete_{goal['id']}"):
                    if delete_goal(goal['id']):
                        st.success("Meta excluída com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro ao excluir meta.")

def show_goal_amount_form():
    """Mostra o formulário para atualizar o valor atual de uma meta."""
    if not st.session_state.updating_goal_amount:
        st.error("Nenhuma meta selecionada para atualização.")
        return
    
    goal = st.session_state.updating_goal_amount
    
    st.subheader(f"💰 Atualizar Valor da Meta: {goal['title']}")
    
    with st.form(key="goal_amount_form", clear_on_submit=True):
        # Informações atuais
        st.markdown(f"**Valor Alvo:** R$ {float(goal['target_amount']):,.2f}")
        st.markdown(f"**Valor Atual:** R$ {float(goal['current_amount']):,.2f}")
        
        # Calcular progresso
        progress = (float(goal['current_amount']) / float(goal['target_amount']) * 100) if float(goal['target_amount']) > 0 else 0
        st.progress(min(1.0, progress / 100))
        st.markdown(f"**Progresso Atual:** {progress:.1f}%")
        
        # Campo para novo valor
        new_amount = st.number_input(
            "Novo Valor Atual",
            min_value=0.0,
            max_value=float(goal['target_amount']),
            value=float(goal['current_amount']),
            step=100.0,
            format="%.2f"
        )
        
        # Calcular novo progresso
        new_progress = (new_amount / float(goal['target_amount']) * 100) if float(goal['target_amount']) > 0 else 0
        st.markdown(f"**Novo Progresso:** {new_progress:.1f}%")
        
        # Botões
        col1, col2 = st.columns(2)
        
        with col1:
            submit = st.form_submit_button("💾 Salvar", type="primary")
        
        with col2:
            cancel = st.form_submit_button("❌ Cancelar")
        
        if submit:
            if update_goal_amount(goal['id'], new_amount):
                st.success("Valor atualizado com sucesso!")
                st.session_state.updating_goal_amount = None
                st.rerun()
            else:
                st.error("Erro ao atualizar valor.")
        
        if cancel:
            st.session_state.updating_goal_amount = None
            st.rerun()

def show_goal_form():
    """Mostra o formulário para adicionar/editar uma meta."""
    # Determinar se estamos editando ou criando
    editing = st.session_state.editing_goal is not None
    title = "✏️ Editar Meta" if editing else "➕ Nova Meta"
    
    if editing and not st.sidebar.checkbox("Continuar Editando", value=True):
        st.session_state.editing_goal = None
        st.rerun()
    
    # Formulário
    with st.form(key="goal_form", clear_on_submit=True):
        st.subheader(title)
        
        # Campos do formulário
        goal_data = {}
        
        goal_data['title'] = st.text_input(
            "Título*",
            value=st.session_state.editing_goal.get('title', '') if editing else ''
        )
        
        goal_data['description'] = st.text_area(
            "Descrição",
            value=st.session_state.editing_goal.get('description', '') if editing else ''
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            goal_data['target_amount'] = st.number_input(
                "Valor Alvo*",
                min_value=0.0,
                value=float(st.session_state.editing_goal.get('target_amount', 0)) if editing else 0.0,
                step=100.0,
                format="%.2f"
            )
        
        with col2:
            goal_data['current_amount'] = st.number_input(
                "Valor Atual",
                min_value=0.0,
                max_value=float(goal_data['target_amount']) if goal_data['target_amount'] > 0 else None,
                value=float(st.session_state.editing_goal.get('current_amount', 0)) if editing else 0.0,
                step=100.0,
                format="%.2f"
            )
        
        col3, col4 = st.columns(2)
        
        with col3:
            goal_data['category'] = st.selectbox(
                "Categoria",
                options=['Reserva', 'Viagem', 'Educação', 'Investimento', 'Compra', 'Outro'],
                index=['Reserva', 'Viagem', 'Educação', 'Investimento', 'Compra', 'Outro'].index(
                    st.session_state.editing_goal.get('category', 'Outro')
                ) if editing and st.session_state.editing_goal.get('category') else 0
            )
        
        with col4:
            goal_data['status'] = st.selectbox(
                "Status",
                options=['Em Andamento', 'Concluída', 'Cancelada'],
                index=['Em Andamento', 'Concluída', 'Cancelada'].index(
                    st.session_state.editing_goal.get('status', 'Em Andamento')
                ) if editing else 0
            )
        
        # Tratamento especial para a data limite
        try:
            default_date = None
            if editing and st.session_state.editing_goal.get('deadline'):
                default_date = datetime.strptime(
                    st.session_state.editing_goal['deadline'],
                    '%Y-%m-%d'
                ).date()
        except (ValueError, TypeError):
            default_date = None
        
        deadline = st.date_input(
            "Prazo",
            value=default_date,
            min_value=date.today()
        )
        if deadline:
            goal_data['deadline'] = deadline.strftime('%Y-%m-%d')
        
        # Botões
        col5, col6 = st.columns(2)
        
        with col5:
            submit = st.form_submit_button(
                "💾 Salvar" if editing else "➕ Adicionar",
                type="primary"
            )
        
        with col6:
            if editing and st.form_submit_button("❌ Cancelar"):
                st.session_state.editing_goal = None
                st.rerun()
        
        if submit:
            try:
                # Validar campos obrigatórios
                if not goal_data.get('title'):
                    st.error("O título é obrigatório.")
                    return
                
                if goal_data.get('target_amount', 0) <= 0:
                    st.error("O valor alvo deve ser maior que zero.")
                    return
                
                if editing:
                    # Atualizar meta existente
                    if update_goal(st.session_state.editing_goal['id'], goal_data):
                        st.success("Meta atualizada com sucesso!")
                        st.session_state.editing_goal = None
                        st.rerun()
                    else:
                        st.error("Erro ao atualizar meta.")
                else:
                    # Adicionar nova meta
                    goal_id = add_goal(goal_data)
                    if goal_id:
                        st.success("Meta adicionada com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro ao adicionar meta.")
            except ValueError as e:
                st.error(f"Erro de validação: {str(e)}")
            except Exception as e:
                st.error(f"Erro inesperado: {str(e)}")
                raise
