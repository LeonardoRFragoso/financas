"""
Módulo responsável pela ferramenta de orçamento 50/30/20.
"""
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
from transactions_db import view_transactions
from theme_manager import init_theme_manager, theme_config_section, get_theme_colors, apply_theme_to_plotly_chart

def calculate_budget_distribution(transactions):
    """Calcula a distribuição atual do orçamento seguindo a regra 50/30/20"""
    # Filtrar apenas transações pagas
    paid_transactions = [t for t in transactions if str(t.get('status', '')).lower() in ['pago', 'paid']]
    
    # Calcular receita total
    income = sum(float(t.get('amount', 0)) for t in paid_transactions if str(t.get('type', '')).lower() in ['receita', 'income', 'revenue'])
    
    if income == 0:
        return None
    
    # Calcular despesas por categoria
    expenses = {
        'Necessidades': 0,  # 50%
        'Desejos': 0,      # 30%
        'Poupança': 0      # 20%
    }
    
    for t in paid_transactions:
        tipo = str(t.get('type', '')).lower()
        categoria_tipo = str(t.get('categoria_tipo', '')).lower()
        amount = float(t.get('amount', 0))
        
        # Log para depuração
        print(f"Processando transação: {t.get('description')} | Tipo: {tipo} | Categoria: {categoria_tipo} | Valor: {amount}")
        
        if tipo in ['despesa', 'expense', 'expenses']:
            if categoria_tipo in ['necessidade', 'necessidades']:
                expenses['Necessidades'] += amount
                print(f"  → Adicionando à Necessidades: R${amount:.2f}")
            elif categoria_tipo in ['desejo', 'desejos']:
                expenses['Desejos'] += amount
                print(f"  → Adicionando à Desejos: R${amount:.2f}")
            else:
                # Se não tiver categoria específica, considerar como necessidade
                expenses['Necessidades'] += amount
                print(f"  → Categoria não especificada, adicionando à Necessidades: R${amount:.2f}")
        elif tipo in ['investimento', 'investment']:
            # Todos os investimentos vão para poupança
            expenses['Poupança'] += amount
            print(f"  → Adicionando à Poupança: R${amount:.2f}")
    
    # Calcular percentuais ideais
    ideal = {
        'Necessidades': income * 0.5,
        'Desejos': income * 0.3,
        'Poupança': income * 0.2
    }
    
    # Calcular percentuais reais
    real = {cat: (value / income * 100) if income > 0 else 0 
            for cat, value in expenses.items()}
    
    print(f"Resumo do orçamento:")
    print(f"  Renda total: R${income:.2f}")
    print(f"  Necessidades: R${expenses['Necessidades']:.2f} ({real['Necessidades']:.1f}%)")
    print(f"  Desejos: R${expenses['Desejos']:.2f} ({real['Desejos']:.1f}%)")
    print(f"  Poupança: R${expenses['Poupança']:.2f} ({real['Poupança']:.1f}%)")
    
    return {
        'income': income,
        'expenses': expenses,
        'ideal': ideal,
        'real': real
    }

def show_budget_tool():
    """Mostra a ferramenta de orçamento 50/30/20"""
    st.title("Orçamento 50/30/20")
    
    # Inicializar o gerenciador de tema
    init_theme_manager()
    
    # Mostrar configuração de tema
    theme_config_section()
    
    st.write("""
    ### Como funciona a regra 50/30/20?
    
    Esta regra sugere dividir sua renda mensal da seguinte forma:
    - **50%** para necessidades básicas
    - **30%** para desejos/gastos pessoais
    - **20%** para poupança e investimentos
    """)
    
    # Obter transações diretamente do Supabase
    try:
        from supabase_db import init_supabase
        
        # Inicializar conexão com Supabase
        supabase = init_supabase()
        if not supabase:
            st.error("Erro ao conectar ao banco de dados Supabase.")
            return
            
        # Buscar todas as transações
        print("Buscando transações para o orçamento 50/30/20...")
        response = supabase.table("transactions").select("*").limit(100).execute()
        transactions = response.data
        print(f"Total de transações encontradas: {len(transactions)}")
        
        if not transactions:
            st.warning("Nenhuma transação registrada ainda.")
            return
            
        # Exibir IDs das transações para debug
        print(f"IDs das transações: {[t.get('id') for t in transactions]}")
    except Exception as e:
        st.error(f"Erro ao buscar transações: {e}")
        import traceback
        print(traceback.format_exc())
        return
    
    # Calcular distribuição do orçamento
    distribution = calculate_budget_distribution(transactions)
    if not distribution:
        st.warning("Nenhuma receita registrada ainda.")
        return
    
    # Mostrar resumo
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Renda Total", f"R$ {distribution['income']:,.2f}")
    
    with col2:
        st.metric("Total Despesas", 
                 f"R$ {sum(distribution['expenses'].values()):,.2f}")
    
    with col3:
        st.metric("Disponível", 
                 f"R$ {distribution['income'] - sum(distribution['expenses'].values()):,.2f}")
    
    # Obter cores do tema
    theme_colors = get_theme_colors()
    
    # Criar gráfico comparativo
    categories = list(distribution['expenses'].keys())
    values_real = [distribution['expenses'][cat] for cat in categories]
    values_ideal = [distribution['ideal'][cat] for cat in categories]
    
    fig = go.Figure(data=[
        go.Bar(
            name='Real', 
            x=categories, 
            y=values_real,
            marker_color=theme_colors['accent_color']
        ),
        go.Bar(
            name='Ideal', 
            x=categories, 
            y=values_ideal,
            marker_color=theme_colors['success_color']
        )
    ])
    
    # Aplicar estilo baseado no tema
    fig = apply_theme_to_plotly_chart(fig)
    fig.update_layout(
        title='Distribuição Real vs Ideal',
        yaxis_title='Valor (R$)',
        barmode='group'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Mostrar percentuais
    st.subheader("Distribuição Percentual")
    cols = st.columns(3)
    
    for i, (category, percentage) in enumerate(distribution['real'].items()):
        with cols[i]:
            ideal_pct = 50 if category == 'Necessidades' else 30 if category == 'Desejos' else 20
            st.metric(
                category,
                f"{percentage:.1f}%",
                f"{ideal_pct - percentage:.1f}%",
                delta_color="normal" if category == "Poupança" else "inverse"
            )
    
    # Recomendações
    st.subheader("Análise e Recomendações")
    
    for category, percentage in distribution['real'].items():
        ideal_pct = 50 if category == 'Necessidades' else 30 if category == 'Desejos' else 20
        diff = percentage - ideal_pct
        
        if abs(diff) <= 5:
            st.success(f"✅ Seus gastos com {category.lower()} estão próximos do ideal!")
        else:
            if diff > 0:
                st.warning(f"⚠️ Seus gastos com {category.lower()} estão {diff:.1f}% acima do recomendado.")
            else:
                msg = "aumentar" if category == "Poupança" else "reduzir"
                st.info(f"💡 Você pode {msg} seus gastos com {category.lower()} em {abs(diff):.1f}%.")
    
    # Mostrar detalhes
    st.subheader("Detalhamento")
    for category in categories:  
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**{category}**")
        with col2:
            st.write(f"Ideal: R$ {distribution['ideal'][category]:,.2f}")
        with col3:
            st.write(f"Real: R$ {distribution['expenses'][category]:,.2f}")
