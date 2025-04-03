"""
Módulo responsável pelos relatórios financeiros.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from transactions_db import view_transactions
from transactions_analysis import get_balance, get_monthly_summary
from theme_manager import init_theme_manager, theme_config_section, get_theme_colors, apply_theme_to_plotly_chart
from supabase_db import init_supabase

def show_reports():
    """Mostra os relatórios financeiros"""
    st.title("📊 Relatórios")
    
    # Inicializar o gerenciador de tema
    init_theme_manager()
    
    # Mostrar configuração de tema
    theme_config_section()
    
    # Obter transações diretamente do Supabase
    supabase = init_supabase()
    if not supabase:
        st.error("Erro ao conectar ao banco de dados.")
        return
        
    response = supabase.table("transactions").select("*").execute()
    transactions = response.data
    
    if not transactions:
        st.warning("Nenhuma transação encontrada para gerar relatórios.")
        return
    
    # Converter para DataFrame
    df = pd.DataFrame(transactions)
    
    # Converter campos de data
    df['date'] = pd.to_datetime(df['date'])
    df['due_date'] = pd.to_datetime(df['due_date'])
    df['created_at'] = pd.to_datetime(df['created_at'])
    
    # Tabs para diferentes relatórios
    tab1, tab2, tab3 = st.tabs(["📈 Visão Geral", "💰 Fluxo de Caixa", "📊 Categorias"])
    
    with tab1:
        show_overview(df)
    
    with tab2:
        show_cash_flow(df)
    
    with tab3:
        show_category_analysis(df)

def show_overview(df):
    """Mostra visão geral das finanças"""
    st.subheader("Visão Geral")
    
    # Métricas principais
    theme_colors = get_theme_colors()
    
    # Calcular saldos usando a mesma lógica do dashboard
    # Filtrar apenas transações pagas
    df_paid = df[df['status'].str.lower().isin(['pago', 'paid'])]
    
    # Inicializar valores
    saldo_conta = 0
    total_investido = 0
    
    # Processar cada transação usando a mesma lógica do dashboard
    for _, transaction in df_paid.iterrows():
        # Obter o tipo e valor da transação
        tipo = str(transaction.get('type', '')).lower()
        valor = float(transaction.get('amount', 0))
        
        # Calcular saldo em conta
        if tipo in ['receita', 'income', 'revenue']:
            saldo_conta += valor
        elif tipo in ['despesa', 'expense', 'expenses']:
            saldo_conta -= valor
        elif tipo in ['investimento', 'investment']:
            saldo_conta -= valor
            total_investido += valor
    
    # Calcular patrimônio total
    patrimonio_total = saldo_conta + total_investido
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Saldo em Conta", f"R$ {saldo_conta:,.2f}")
    
    with col2:
        st.metric("Total Investido", f"R$ {total_investido:,.2f}")
    
    with col3:
        st.metric("Patrimônio Total", f"R$ {patrimonio_total:,.2f}")
    
    # Gráfico de pizza por tipo de transação
    st.subheader("Distribuição por Tipo")
    
    # Criar DataFrame para o gráfico
    df_type = pd.DataFrame([
        {"Tipo": "Receitas", "Valor": df[df['type'].str.lower().isin(['receita', 'income', 'revenue'])]['amount'].astype(float).sum()},
        {"Tipo": "Despesas", "Valor": df[df['type'].str.lower().isin(['despesa', 'expense', 'expenses'])]['amount'].astype(float).sum()},
        {"Tipo": "Investimentos", "Valor": df[df['type'].str.lower().isin(['investimento', 'investment'])]['amount'].astype(float).sum()}
    ])
    
    # Cores para cada tipo
    colors = [
        theme_colors.get('revenue_color', '#4CAF50'),  # Verde para receitas
        theme_colors.get('expense_color', '#F44336'),  # Vermelho para despesas
        theme_colors.get('investment_color', '#2196F3')  # Azul para investimentos
    ]
    
    fig = px.pie(
        df_type,
        values='Valor',
        names='Tipo',
        title='Distribuição por Tipo de Transação',
        color='Tipo',
        color_discrete_sequence=colors
    )
    
    # Aplicar tema e mostrar valores
    fig.update_traces(textinfo='percent+label+value', texttemplate='%{label}: R$%{value:.2f}<br>(%{percent})')
    apply_theme_to_plotly_chart(fig)
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabela com resumo
    st.subheader("Resumo por Tipo")
    
    # Contar transações por tipo
    receitas_count = df[df['type'].str.lower().isin(['receita', 'income', 'revenue'])].shape[0]
    despesas_count = df[df['type'].str.lower().isin(['despesa', 'expense', 'expenses'])].shape[0]
    investimentos_count = df[df['type'].str.lower().isin(['investimento', 'investment'])].shape[0]
    
    # Calcular médias
    receitas_mean = df[df['type'].str.lower().isin(['receita', 'income', 'revenue'])]['amount'].astype(float).sum() / receitas_count if receitas_count > 0 else 0
    despesas_mean = df[df['type'].str.lower().isin(['despesa', 'expense', 'expenses'])]['amount'].astype(float).sum() / despesas_count if despesas_count > 0 else 0
    investimentos_mean = df[df['type'].str.lower().isin(['investimento', 'investment'])]['amount'].astype(float).sum() / investimentos_count if investimentos_count > 0 else 0
    
    summary_df = pd.DataFrame({
        'Tipo': ['Receitas', 'Despesas', 'Investimentos'],
        'Valor Total': [f"R$ {df[df['type'].str.lower().isin(['receita', 'income', 'revenue'])]['amount'].astype(float).sum():,.2f}", f"R$ {df[df['type'].str.lower().isin(['despesa', 'expense', 'expenses'])]['amount'].astype(float).sum():,.2f}", f"R$ {df[df['type'].str.lower().isin(['investimento', 'investment'])]['amount'].astype(float).sum():,.2f}"],
        'Quantidade': [receitas_count, despesas_count, investimentos_count],
        'Média': [f"R$ {receitas_mean:,.2f}", f"R$ {despesas_mean:,.2f}", f"R$ {investimentos_mean:,.2f}"]
    })
    
    st.dataframe(summary_df, use_container_width=True)

def show_cash_flow(df):
    """Mostra análise do fluxo de caixa"""
    st.subheader("Fluxo de Caixa")
    
    # Seletor de período
    period = st.selectbox(
        "Período",
        ["Últimos 30 dias", "Este mês", "Mês anterior", "Últimos 3 meses", "Todo período"]
    )
    
    # Filtrar dados pelo período selecionado
    today = pd.Timestamp.now()
    df_filtered = df.copy()
    
    if period == "Últimos 30 dias":
        df_filtered = df[df['date'] >= (today - pd.Timedelta(days=30))]
    elif period == "Este mês":
        df_filtered = df[df['date'].dt.month == today.month]
        df_filtered = df_filtered[df_filtered['date'].dt.year == today.year]
    elif period == "Mês anterior":
        last_month = today.month - 1 if today.month > 1 else 12
        last_month_year = today.year if today.month > 1 else today.year - 1
        df_filtered = df[df['date'].dt.month == last_month]
        df_filtered = df_filtered[df_filtered['date'].dt.year == last_month_year]
    elif period == "Últimos 3 meses":
        df_filtered = df[df['date'] >= (today - pd.Timedelta(days=90))]
    
    # Preparar dados para o gráfico
    # Agrupar por data e tipo, considerando variações nos nomes dos tipos
    df_daily = pd.DataFrame()
    
    # Processar receitas
    receitas = df_filtered[df_filtered['type'].str.lower().isin(['receita', 'income', 'revenue'])]
    if not receitas.empty:
        receitas_daily = receitas.groupby('date')['amount'].sum().reset_index()
        receitas_daily['type'] = 'Receita'
        df_daily = pd.concat([df_daily, receitas_daily])
    
    # Processar despesas
    despesas = df_filtered[df_filtered['type'].str.lower().isin(['despesa', 'expense', 'expenses'])]
    if not despesas.empty:
        despesas_daily = despesas.groupby('date')['amount'].sum().reset_index()
        despesas_daily['type'] = 'Despesa'
        df_daily = pd.concat([df_daily, despesas_daily])
    
    # Processar investimentos
    investimentos = df_filtered[df_filtered['type'].str.lower().isin(['investimento', 'investment'])]
    if not investimentos.empty:
        investimentos_daily = investimentos.groupby('date')['amount'].sum().reset_index()
        investimentos_daily['type'] = 'Investimento'
        df_daily = pd.concat([df_daily, investimentos_daily])
    
    if df_daily.empty:
        st.info(f"Não há transações para o período selecionado: {period}")
        return
    
    # Obter cores do tema
    theme_colors = get_theme_colors()
    colors = {
        'Receita': theme_colors.get('revenue_color', '#4CAF50'),
        'Despesa': theme_colors.get('expense_color', '#F44336'),
        'Investimento': theme_colors.get('investment_color', '#2196F3')
    }
    
    # Criar gráfico de linha
    fig = px.line(
        df_daily,
        x='date',
        y='amount',
        color='type',
        title=f'Fluxo de Caixa - {period}',
        color_discrete_map=colors
    )
    
    apply_theme_to_plotly_chart(fig)
    fig.update_layout(
        xaxis_title='Data',
        yaxis_title='Valor (R$)',
        hovermode="x unified"
    )
    
    # Adicionar formatação para valores em reais
    fig.update_traces(hovertemplate='%{y:$.2f}')
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Resumo do período
    col1, col2, col3 = st.columns(3)
    
    # Calcular totais
    receitas_total = df_filtered[df_filtered['type'].str.lower().isin(['receita', 'income', 'revenue'])]['amount'].astype(float).sum()
    despesas_total = df_filtered[df_filtered['type'].str.lower().isin(['despesa', 'expense', 'expenses'])]['amount'].astype(float).sum()
    investimentos_total = df_filtered[df_filtered['type'].str.lower().isin(['investimento', 'investment'])]['amount'].astype(float).sum()
    
    with col1:
        st.metric("Total Receitas", f"R$ {receitas_total:,.2f}")
    
    with col2:
        st.metric("Total Despesas", f"R$ {despesas_total:,.2f}")
    
    with col3:
        st.metric("Total Investimentos", f"R$ {investimentos_total:,.2f}")

def show_category_analysis(df):
    """Mostra análise por categorias"""
    st.subheader("Análise por Categorias")
    
    # Filtro por tipo
    type_filter = st.selectbox(
        "Tipo de Transação",
        ["Despesa", "Receita", "Investimento"]
    )
    
    # Mapear seleção para possíveis variações nos dados
    type_map = {
        "Despesa": ['despesa', 'expense', 'expenses'],
        "Receita": ['receita', 'income', 'revenue'],
        "Investimento": ['investimento', 'investment']
    }
    
    # Filtrar dados
    df_filtered = df[df['type'].str.lower().isin(type_map[type_filter])]
    
    if df_filtered.empty:
        st.info(f"Não há transações do tipo {type_filter} para análise.")
        return
    
    # Agrupar por categoria
    df_cat = df_filtered.groupby('category')['amount'].agg(['sum', 'count']).reset_index()
    df_cat.columns = ['Categoria', 'Total', 'Quantidade']
    df_cat = df_cat.sort_values('Total', ascending=True)
    
    # Obter cores do tema
    theme_colors = get_theme_colors()
    
    # Criar gráfico de barras horizontais
    fig = go.Figure(data=[
        go.Bar(
            x=df_cat['Total'],
            y=df_cat['Categoria'],
            orientation='h',
            marker_color=theme_colors.get('primary_color', '#1E88E5')
        )
    ])
    
    apply_theme_to_plotly_chart(fig)
    fig.update_layout(
        title=f'Total por Categoria - {type_filter}s',
        xaxis_title='Valor (R$)',
        yaxis_title='Categoria',
        hovermode="y unified"
    )
    
    # Adicionar formatação para valores em reais
    fig.update_traces(hovertemplate='R$ %{x:.2f}')
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabela detalhada
    st.subheader(f"Detalhamento por Categoria - {type_filter}s")
    df_cat['Média'] = df_cat['Total'] / df_cat['Quantidade']
    df_cat['Total'] = df_cat['Total'].apply(lambda x: f"R$ {x:,.2f}")
    df_cat['Média'] = df_cat['Média'].apply(lambda x: f"R$ {x:,.2f}")
    st.dataframe(df_cat, use_container_width=True)
