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
    
    # Aplicar apenas CSS que complementa o tema, sem sobreescrever as cores de tema do Streamlit
    st.markdown("""
        <style>
        /* Elementos de layout e animações que não interferem com o tema */
        .stButton>button {
            border-radius: 8px;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            transform: translateY(-2px);
        }
        
        /* Cards de métricas */
        .metric-card {
            padding: 1.5rem;
            border-radius: 10px;
            transition: all 0.3s ease;
        }
        .metric-card:hover {
            transform: translateY(-2px);
        }
        
        /* Links de navegação */
        .nav-link {
            padding: 0.5rem 1rem;
            margin: 0.2rem 0;
            border-radius: 8px;
            transition: all 0.3s ease;
            text-decoration: none;
        }
        .nav-link:hover {
            opacity: 0.8;
        }
        
        /* Estilos para plots e gráficos */
        .plot-container {
            border-radius: 10px;
            padding: 1rem;
            margin: 1rem 0;
        }
        
        /* Conteúdo principal */
        .main .block-container {
            padding: 1rem;
        }
        
        /* Classes utilitárias */
        .card {
            border-radius: 10px;
            padding: 1rem;
            margin: 1rem 0;
        }
        
        /* Suporte para widgets personalizados */
        .custom-widget {
            border-radius: 8px;
            padding: 10px;
        }
        
        /* Estilos para as abas */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 4px 4px 0px 0px;
            padding: 8px 16px;
            transition: all 0.3s ease;
        }
        
        /* Animações suaves */
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        .st-emotion-cache-16txtl3 h1,
        .st-emotion-cache-16txtl3 h2,
        .st-emotion-cache-16txtl3 h3 {
            animation: fadeIn 0.5s ease-in-out;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Inicializar banco de dados
    init_db()
    
    # Sidebar para navegação
    with st.sidebar:
        st.title("💰 Controle Financeiro")
        st.markdown("---")
        
        # Menu de navegação
        menu = st.radio(
            "Navegação",
            ["📊 Dashboard", "💸 Transações", "📈 Orçamento", "📑 Relatórios", "🎯 Metas", "🤖 Assistente"]
        )
    
    # Conteúdo baseado na seleção do menu
    if "Dashboard" in menu:
        show_dashboard()
    elif "Transações" in menu:
        from ui import show_transactions_page
        show_transactions_page()
    elif "Orçamento" in menu:
        show_budget_tool()
    elif "Relatórios" in menu:
        show_reports()
    elif "Metas" in menu:
        show_goals()
    elif "Assistente" in menu:
        show_finance_assistant()
    
    # Rodapé
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center;">
            <p>Controle Financeiro 2025 - Desenvolvido com ❤️ usando Streamlit</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
