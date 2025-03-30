"""
Módulo responsável pela interface da página de metas financeiras.
"""
import streamlit as st
from datetime import datetime, date
import pandas as pd
import plotly.express as px
from goals_db import (
    init_goals_table, add_goal, update_goal, 
    delete_goal, view_goals, get_goal
)

def show_goals():
    """Mostra a página de metas financeiras."""
    st.title("🎯 Metas Financeiras")
    
    # Inicializar tabela se necessário
    init_goals_table()
    
    # Inicializar estado da sessão se necessário
    if 'editing_goal' not in st.session_state:
        st.session_state.editing_goal = None
    
    # Tabs para organizar o conteúdo
    if st.session_state.editing_goal:
        show_goal_form()  # Mostrar formulário de edição primeiro
    else:
        tab1, tab2 = st.tabs(["📋 Minhas Metas", "➕ Nova Meta"])
        
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
    df['deadline'] = pd.to_datetime(df['deadline'])
    df['progress'] = (df['current_amount'] / df['target_amount'] * 100).round(2)
    
    # Visão geral em cards
    for goal in goals:
        with st.expander(f"📌 {goal['title']}", expanded=True):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                st.write("**Descrição:**")
                st.write(goal['description'] if goal['description'] else "Sem descrição")
            
            with col2:
                st.metric(
                    "Meta",
                    f"R$ {goal['target_amount']:,.2f}",
                    f"R$ {goal['current_amount']:,.2f} atual"
                )
            
            with col3:
                progress = (goal['current_amount'] / goal['target_amount'] * 100)
                st.progress(min(progress / 100, 1.0))
                st.write(f"{progress:.1f}% concluído")
                st.write(f"**Prazo:** {goal['deadline']}")
            
            with col4:
                if st.button("✏️", key=f"edit_{goal['id']}", help="Editar meta"):
                    st.session_state.editing_goal = goal
                    st.rerun()
                
                if st.button("🗑️", key=f"delete_{goal['id']}", help="Excluir meta"):
                    if delete_goal(goal['id']):
                        st.success("Meta excluída com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro ao excluir meta.")
    
    # Gráfico de progresso
    st.subheader("Visão Geral do Progresso")
    fig = px.bar(
        df,
        x='title',
        y=['current_amount', 'target_amount'],
        title='Progresso das Metas',
        barmode='overlay',
        labels={
            'title': 'Meta',
            'value': 'Valor (R$)',
            'variable': 'Tipo'
        }
    )
    st.plotly_chart(fig, use_container_width=True)

def show_goal_form():
    """Mostra o formulário para adicionar/editar uma meta."""
    editing = st.session_state.editing_goal is not None
    goal = st.session_state.editing_goal if editing else {}
    
    # Botão para cancelar edição
    if editing:
        if st.button("← Voltar para lista"):
            st.session_state.editing_goal = None
            st.rerun()
    
    st.subheader("🎯 " + ("Editar Meta" if editing else "Nova Meta"))
    
    with st.form("goal_form", clear_on_submit=not editing):
        title = st.text_input(
            "Título da Meta *",
            value=goal.get('title', '')
        )
        
        description = st.text_area(
            "Descrição",
            value=goal.get('description', '')
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            target_amount = st.number_input(
                "Valor da Meta *",
                min_value=0.0,
                value=float(goal.get('target_amount', 0)),
                step=100.0,
                format="%.2f"
            )
            
            current_amount = st.number_input(
                "Valor Atual",
                min_value=0.0,
                max_value=float(target_amount),
                value=float(goal.get('current_amount', 0)),
                step=100.0,
                format="%.2f"
            )
        
        with col2:
            category = st.selectbox(
                "Categoria",
                ["Investimento", "Reserva", "Viagem", "Compra", "Outro"],
                index=0 if not goal.get('category') else ["Investimento", "Reserva", "Viagem", "Compra", "Outro"].index(goal['category'])
            )
            
            deadline = st.date_input(
                "Data Limite",
                min_value=date.today(),
                value=datetime.strptime(goal.get('deadline', date.today().strftime('%Y-%m-%d')), '%Y-%m-%d').date()
            )
        
        status = st.selectbox(
            "Status",
            ["Em Andamento", "Concluída", "Cancelada"],
            index=0 if not goal.get('status') else ["Em Andamento", "Concluída", "Cancelada"].index(goal['status'])
        )
        
        submitted = st.form_submit_button(
            "💾 Salvar" if editing else "➕ Adicionar"
        )
        
        if submitted:
            if not title or target_amount <= 0:
                st.error("Por favor, preencha todos os campos obrigatórios.")
                return
            
            goal_data = {
                'title': title,
                'description': description,
                'target_amount': target_amount,
                'current_amount': current_amount,
                'category': category,
                'deadline': deadline.strftime('%Y-%m-%d'),
                'status': status
            }
            
            if editing:
                if update_goal(goal['id'], goal_data):
                    st.success("Meta atualizada com sucesso!")
                    st.session_state.editing_goal = None
                    st.rerun()
                else:
                    st.error("Erro ao atualizar meta.")
            else:
                if add_goal(goal_data):
                    st.success("Meta adicionada com sucesso!")
                    st.rerun()
                else:
                    st.error("Erro ao adicionar meta.")
