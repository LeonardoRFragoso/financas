import streamlit as st
from transactions_db import add_transaction, view_transactions, delete_transaction, update_transaction
from goals import add_goal, view_goals, delete_goal
from categories import get_categories
import pandas as pd
from datetime import datetime

def create_transaction_form():
    """Cria o formulário para adicionar uma nova transação"""
    # Inicializa o tipo de transação no session state se não existir
    if 'transaction_type' not in st.session_state:
        st.session_state.transaction_type = "Despesa"
    
    # Seleciona o tipo fora do formulário
    type_trans = st.selectbox(
        "Tipo",
        ["Despesa", "Receita", "Investimento"],
        key="type_select"
    )
    st.session_state.transaction_type = type_trans
    
    with st.form(key='transaction_form'):
        st.subheader("Nova Transação")
        
        col1, col2 = st.columns(2)
        with col1:
            description = st.text_input("Descrição")
            amount = st.number_input("Valor", min_value=0.0, format="%.2f")
            
            # Busca categorias filtradas pelo tipo atual
            categoria_tipo = "outros"  # valor padrão inicial
            categoria_tipo_map = {}
            
            if st.session_state.transaction_type == "Despesa":
                categories = get_categories(type_filter="Despesa")
                if not categories:
                    category_names = ["Alimentação", "Moradia", "Transporte", "Outros"]
                    categoria_tipo = "necessidade"
                else:
                    category_names = [cat[1] for cat in categories]
                    categoria_tipo_map = {cat[1]: cat[3] for cat in categories}
            elif st.session_state.transaction_type == "Receita":
                categories = get_categories(type_filter="Receita")
                if not categories:
                    category_names = ["Salário", "Freelancer", "Investimentos", "Outros"]
                    categoria_tipo = "receita"
                else:
                    category_names = [cat[1] for cat in categories]
                    categoria_tipo_map = {cat[1]: cat[3] for cat in categories}
            else:  # Investimento
                category_names = ["Poupança", "Renda Fixa", "Fundos Imobiliários", "Ações", "Tesouro Direto", "CDB", "Fundos", "Outros"]
                categoria_tipo = "investimento"
                categoria_tipo_map = {name: "investimento" for name in category_names}
            
            category = st.selectbox("Categoria", category_names)
            # Pegar o tipo da categoria do mapa ou usar o valor padrão
            categoria_tipo = categoria_tipo_map.get(category, categoria_tipo)
        
        with col2:
            date = st.date_input("Data")
            due_date = st.date_input("Data de Vencimento")
            status = st.selectbox("Status", ["pendente", "pago", "atrasado"])
        
        st.markdown("### Opções Avançadas")
        col1, col2 = st.columns(2)
        with col1:
            # Mostrar opções avançadas apenas para despesas
            if st.session_state.transaction_type == "Despesa":
                recurring = st.checkbox("Transação Recorrente")
                fixed_expense = st.checkbox("Despesa Fixa")
            else:
                recurring = False
                fixed_expense = False
        
        with col2:
            if st.session_state.transaction_type == "Despesa":
                priority = st.select_slider("Prioridade", options=[1, 2, 3], value=2,
                                      format_func=lambda x: {1: "Baixa", 2: "Média", 3: "Alta"}[x])
                installments = st.number_input("Número de Parcelas", min_value=1, value=1)
            else:
                priority = 1
                installments = 1
        
        col1, col2 = st.columns(2)
        with col1:
            submit_button = st.form_submit_button(label='Adicionar')
        with col2:
            pass
        
        if submit_button:
            add_transaction(
                description=description, 
                amount=amount,
                category=category,
                date=date.strftime("%Y-%m-%d"),
                type_trans=type_trans,
                due_date=due_date.strftime("%Y-%m-%d"),
                status=status,
                recurring=recurring,
                priority=priority,
                fixed_expense=fixed_expense,
                installments=installments,
                categoria_tipo=categoria_tipo
            )
            st.success("Transação adicionada com sucesso!")
            st.rerun()

def create_goal_form():
    """Formulário para adicionar uma nova meta"""
    with st.form(key='goal_form'):
        description = st.text_input("Descrição da Meta")
        target_amount = st.number_input("Valor Alvo", min_value=0.0, format="%.2f")
        current_amount = st.number_input("Valor Atual", min_value=0.0, format="%.2f")
        deadline = st.date_input("Prazo")
        category = st.text_input("Categoria")
        submit_button = st.form_submit_button(label='Adicionar Meta')
        if submit_button:
            add_goal(description, target_amount, deadline.strftime("%Y-%m-%d"), category)
            st.success("Meta adicionada com sucesso!")

def display_transactions(transactions):
    """Exibe a lista de transações em uma tabela formatada"""
    if not transactions:
        st.info("Nenhuma transação registrada ainda.")
        return

    df = pd.DataFrame(transactions, columns=[
        'id', 'user_id', 'description', 'amount', 'category', 'date',
        'due_date', 'type', 'status', 'recurring', 'priority',
        'quinzena', 'installments', 'current_installment',
        'fixed_expense', 'categoria_tipo', 'created_at'
    ])

    # Converter datas para formato mais amigável
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%d/%m/%Y')
    df['due_date'] = pd.to_datetime(df['due_date']).dt.strftime('%d/%m/%Y')

    # Formatar valores monetários
    df['amount'] = df['amount'].apply(lambda x: f"R$ {x:.2f}")

    # Mostrar transações em uma tabela
    st.write("### Transações Existentes")
    
    # Criar colunas para cada transação
    for index, transaction in df.iterrows():
        with st.expander(f"{transaction['description']} - {transaction['amount']} ({transaction['date']})"):
            if st.button("Editar", key=f"edit_{transaction['id']}"):
                st.session_state['show_edit_form'] = True
                st.session_state['editing_transaction'] = transaction
            
            if st.button("Excluir", key=f"delete_{transaction['id']}"):
                delete_transaction(transaction['id'])
                st.success("Transação excluída com sucesso!")
                st.rerun()

    # Formulário de edição
    if st.session_state.get('show_edit_form', False):
        transaction = st.session_state['editing_transaction']
        
        with st.form(key=f"edit_form_{transaction['id']}"):
            st.subheader("Editar Transação")
            
            col1, col2 = st.columns(2)
            with col1:
                description = st.text_input("Descrição", value=transaction['description'])
                amount = st.number_input("Valor", value=float(transaction['amount'].replace('R$ ', '')), format="%.2f")
                
                # Busca categorias filtradas pelo tipo atual
                categoria_tipo = "outros"  # valor padrão inicial
                categoria_tipo_map = {}
                
                if transaction['type'] == "Despesa":
                    categories = get_categories(type_filter="Despesa")
                    if not categories:
                        category_names = ["Alimentação", "Moradia", "Transporte", "Outros"]
                        categoria_tipo = "necessidade"
                    else:
                        category_names = [cat[1] for cat in categories]
                        categoria_tipo_map = {cat[1]: cat[3] for cat in categories}
                elif transaction['type'] == "Receita":
                    categories = get_categories(type_filter="Receita")
                    if not categories:
                        category_names = ["Salário", "Freelancer", "Investimentos", "Outros"]
                        categoria_tipo = "receita"
                    else:
                        category_names = [cat[1] for cat in categories]
                        categoria_tipo_map = {cat[1]: cat[3] for cat in categories}
                else:  # Investimento
                    category_names = ["Poupança", "Renda Fixa", "Fundos Imobiliários", "Ações", "Tesouro Direto", "CDB", "Fundos", "Outros"]
                    categoria_tipo = "investimento"
                    categoria_tipo_map = {name: "investimento" for name in category_names}
                
                category = st.selectbox("Categoria", category_names, 
                                      index=category_names.index(transaction['category']) if transaction['category'] in category_names else 0)
                categoria_tipo = categoria_tipo_map.get(category, categoria_tipo)
            
            with col2:
                date = st.date_input("Data", value=pd.to_datetime(transaction['date'], format='%d/%m/%Y'))
                due_date = st.date_input("Data de Vencimento", value=pd.to_datetime(transaction['due_date'], format='%d/%m/%Y'))
                status = st.selectbox("Status", ["pendente", "pago", "atrasado"], 
                                    index=["pendente", "pago", "atrasado"].index(transaction['status']))
            
            st.markdown("### Opções Avançadas")
            col1, col2 = st.columns(2)
            with col1:
                recurring = st.checkbox("Transação Recorrente", value=transaction['recurring'])
                fixed_expense = st.checkbox("Despesa Fixa", value=transaction['fixed_expense'])
            
            with col2:
                priority = st.select_slider("Prioridade", options=[1, 2, 3], value=transaction['priority'],
                                      format_func=lambda x: {1: "Baixa", 2: "Média", 3: "Alta"}[x])
                installments = st.number_input("Número de Parcelas", min_value=1, value=transaction['installments'])
            
            submit = st.form_submit_button("Atualizar")
            
            if submit:
                update_transaction(
                    transaction_id=transaction['id'],
                    description=description,
                    amount=amount,
                    category=category,
                    date=date.strftime("%Y-%m-%d"),
                    type_trans=transaction['type'],
                    due_date=due_date.strftime("%Y-%m-%d"),
                    status=status,
                    recurring=recurring,
                    priority=priority,
                    fixed_expense=fixed_expense,
                    installments=installments,
                    categoria_tipo=categoria_tipo
                )
                st.success("Transação atualizada com sucesso!")
                st.session_state['show_edit_form'] = False
                st.rerun()

def display_goals(goals):
    """Exibe a lista de metas em uma tabela formatada"""
    if not goals:
        st.info("Nenhuma meta cadastrada ainda.")
        return

    # Criar DataFrame com as metas
    df = pd.DataFrame(
        goals,
        columns=['ID', 'User', 'Descrição', 'Valor Alvo', 'Valor Atual',
                'Prazo', 'Categoria', 'Data Criação']
    )

    st.dataframe(df, use_container_width=True)

    # Opção para deletar
    with st.expander("Gerenciar Metas"):
        col1, col2 = st.columns(2)
        with col1:
            goal_to_delete = st.number_input("ID da Meta para Excluir", min_value=1)
        with col2:
            if st.button("Excluir Meta"):
                from goals import delete_goal
                delete_goal(goal_to_delete)
                st.success(f"Meta ID {goal_to_delete} excluída!")
                st.rerun()

def show_transactions_page():
    st.subheader("Gerenciar Transações")
    create_transaction_form()
    transactions = view_transactions()
    display_transactions(transactions)

def show_goals_page():
    st.subheader("Gerenciar Metas")
    create_goal_form()
    goals = view_goals()
    display_goals(goals)
