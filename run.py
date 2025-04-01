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
    
    # Aplicar tema personalizado
    st.markdown("""
        <style>
        /* Estilo responsivo para modo claro e escuro */
        .stApp {
            background-color: var(--background-color);
        }
        
        /* Sidebar com adaptação para tema */
        .stSidebar {
            background-color: var(--secondary-background-color);
            border-right: 1px solid var(--border-color);
        }
        
        /* Botões estilizados */
        .stButton>button {
            border-radius: 8px;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        /* Cards de métricas adaptáveis ao tema */
        .metric-card {
            background-color: var(--secondary-background-color);
            color: var(--text-color);
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px var(--shadow-color);
            transition: all 0.3s ease;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px var(--shadow-color);
        }
        
        /* Links de navegação */
        .nav-link {
            padding: 0.5rem 1rem;
            margin: 0.2rem 0;
            border-radius: 8px;
            transition: all 0.3s ease;
            text-decoration: none;
            color: var(--text-color);
        }
        .nav-link:hover {
            background-color: var(--hover-color);
        }
        
        /* Contêiner de gráficos */
        .chart-container {
            background-color: var(--secondary-background-color);
            color: var(--text-color);
            padding: 1rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px var(--shadow-color);
            margin: 1rem 0;
        }
        
        /* Definição de variáveis CSS baseadas no tema */
        :root {
            --background-color: #f5f7fa;
            --secondary-background-color: #ffffff;
            --text-color: #262730;
            --border-color: #eee;
            --shadow-color: rgba(0,0,0,0.05);
            --hover-color: #f8f9fa;
        }
        
        /* Adaptação para o tema escuro */
        [data-theme="dark"] {
            --background-color: #0e1117;
            --secondary-background-color: #1e2126;
            --text-color: #fafafa;
            --border-color: #333;
            --shadow-color: rgba(0,0,0,0.3);
            --hover-color: #2e3136;
        }
        
        /* Garantir contraste adequado para textos */
        p, h1, h2, h3, h4, h5, h6, span, div {
            color: var(--text-color);
        }
        
        /* Estilos para plots e gráficos */
        .plot-container {
            background-color: var(--secondary-background-color);
            border-radius: 10px;
            padding: 1rem;
            margin: 1rem 0;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Inicializar banco de dados
    init_db()
    
    # Sidebar para navegação
    with st.sidebar:
        st.title("💰 Controle Financeiro")
        st.markdown("---")
        
        # Navegação
        pages = {
            "Dashboard": {"icon": "📊", "desc": "Visão geral das suas finanças"},
            "Transações": {"icon": "💸", "desc": "Gerenciar receitas e despesas"},
            "Orçamento 50/30/20": {"icon": "📈", "desc": "Análise do seu orçamento"},
            "Relatórios": {"icon": "📑", "desc": "Relatórios detalhados"},
            "Assistente Financeiro": {"icon": "🤖", "desc": "Dicas e recomendações"},
            "Metas": {"icon": "🎯", "desc": "Suas metas financeiras"},
            "Configurações": {"icon": "⚙️", "desc": "Personalizar o sistema"}
        }
        
        selected_page = None
        for page, info in pages.items():
            col1, col2 = st.columns([1, 4])
            with col1:
                st.markdown(f"### {info['icon']}")
            with col2:
                if st.button(page, key=f"nav_{page}", use_container_width=True):
                    selected_page = page
                st.caption(info['desc'])
            
        st.markdown("---")
        st.caption("© 2025 Controle Financeiro")
    
    # Renderizar página selecionada
    if selected_page is None:
        selected_page = "Dashboard"  # Página padrão
    
    # Cabeçalho da página
    st.markdown(f"# {pages[selected_page]['icon']} {selected_page}")
    st.markdown("---")
    
    if selected_page == "Dashboard":
        show_dashboard()
    
    elif selected_page == "Transações":
        st.subheader("💸 Gerenciar Transações")
        
        # Formulário para adicionar transação
        with st.expander("➕ Adicionar Nova Transação", expanded=False):
            from ui import create_transaction_form
            create_transaction_form()
        
        # Visualizar transações
        transactions = get_transactions()
        if transactions:
            from ui import display_transactions
            display_transactions(transactions)
        else:
            st.info("🔍 Nenhuma transação registrada ainda.")
    
    elif selected_page == "Orçamento 50/30/20":
        show_budget_tool()
    
    elif selected_page == "Relatórios":
        show_reports()
    
    elif selected_page == "Assistente Financeiro":
        show_finance_assistant()
    
    elif selected_page == "Metas":
        show_goals()
    
    elif selected_page == "Configurações":
        from settings import show_settings_page
        show_settings_page()

if __name__ == "__main__":
    main()
