import streamlit as st
from datetime import datetime
from db import init_db, get_transactions
from dashboard import show_dashboard
from finance_assistant import show_finance_assistant
from budget_tool import show_budget_tool
from reports import show_reports
from goals import show_goals

def main():
    # Configuração inicial da página
    st.set_page_config(
        page_title="Controle Financeiro",
        page_icon="💰",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Inicializar banco de dados
    init_db()
    
    # Sidebar para navegação
    st.sidebar.title("Controle Financeiro")
    
    # Navegação
    pages = {
        "Dashboard": "📊",
        "Transações": "💸",
        "Orçamento 50/30/20": "📈",
        "Relatórios": "📑",
        "Assistente Financeiro": "🤖",
        "Metas": "🎯",
        "Configurações": "⚙️"
    }
    
    page = st.sidebar.selectbox(
        "Navegação",
        pages.keys(),
        format_func=lambda x: f"{pages[x]} {x}"
    )
    
    # Renderizar página selecionada
    if page == "Dashboard":
        show_dashboard()
    
    elif page == "Transações":
        st.title("Gerenciar Transações")
        
        # Formulário para adicionar transação
        with st.expander("Adicionar Nova Transação", expanded=False):
            from ui import create_transaction_form
            create_transaction_form()
        
        # Visualizar transações
        st.subheader("Transações Existentes")
        transactions = get_transactions()
        if transactions:
            from ui import display_transactions
            display_transactions(transactions)
        else:
            st.info("Nenhuma transação registrada ainda.")
    
    elif page == "Orçamento 50/30/20":
        show_budget_tool()
    
    elif page == "Relatórios":
        show_reports()
    
    elif page == "Assistente Financeiro":
        show_finance_assistant()
    
    elif page == "Metas":
        show_goals()
    
    elif page == "Configurações":
        from settings import show_settings_page
        show_settings_page()

if __name__ == "__main__":
    main()
