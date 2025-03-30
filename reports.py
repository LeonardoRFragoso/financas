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

def show_reports():
    """Mostra os relatórios financeiros"""
    st.title("📊 Relatórios")
    
    # Obter transações
    transactions = view_transactions()
    
    if not transactions:
        st.warning("Nenhuma transação encontrada para gerar relatórios.")
        return
    
    # Converter para DataFrame
    df = pd.DataFrame(transactions)
    df['date'] = pd.to_datetime(df['date'])
    
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
    balance = get_balance()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Saldo em Conta", f"R$ {balance['saldo_conta']:,.2f}")
    
    with col2:
        st.metric("Total Investido", f"R$ {balance['total_investido']:,.2f}")
    
    with col3:
        st.metric("Patrimônio Total", f"R$ {balance['patrimonio_total']:,.2f}")
    
    # Gráfico de pizza por tipo de transação
    st.subheader("Distribuição por Tipo")
    df_type = df.groupby('type')['amount'].sum()
    
    fig = px.pie(
        values=df_type.values,
        names=df_type.index,
        title='Distribuição por Tipo de Transação'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabela com resumo
    st.subheader("Resumo por Tipo")
    summary_df = pd.DataFrame({
        'Tipo': df_type.index,
        'Valor Total': df_type.values,
        'Quantidade': df.groupby('type').size(),
        'Média': df.groupby('type')['amount'].mean()
    })
    summary_df['Valor Total'] = summary_df['Valor Total'].apply(lambda x: f"R$ {x:,.2f}")
    summary_df['Média'] = summary_df['Média'].apply(lambda x: f"R$ {x:,.2f}")
    st.dataframe(summary_df)

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
    if period == "Últimos 30 dias":
        df = df[df['date'] >= (today - pd.Timedelta(days=30))]
    elif period == "Este mês":
        df = df[df['date'].dt.month == today.month]
    elif period == "Mês anterior":
        last_month = today.month - 1 if today.month > 1 else 12
        df = df[df['date'].dt.month == last_month]
    elif period == "Últimos 3 meses":
        df = df[df['date'] >= (today - pd.Timedelta(days=90))]
    
    # Gráfico de linha temporal
    df_daily = df.groupby(['date', 'type'])['amount'].sum().reset_index()
    
    fig = px.line(
        df_daily,
        x='date',
        y='amount',
        color='type',
        title=f'Fluxo de Caixa - {period}'
    )
    fig.update_layout(
        xaxis_title='Data',
        yaxis_title='Valor (R$)'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Resumo do período
    col1, col2, col3 = st.columns(3)
    
    with col1:
        receitas = df[df['type'] == 'Receita']['amount'].sum()
        st.metric("Total Receitas", f"R$ {receitas:,.2f}")
    
    with col2:
        despesas = df[df['type'] == 'Despesa']['amount'].sum()
        st.metric("Total Despesas", f"R$ {despesas:,.2f}")
    
    with col3:
        investimentos = df[df['type'] == 'Investimento']['amount'].sum()
        st.metric("Total Investimentos", f"R$ {investimentos:,.2f}")

def show_category_analysis(df):
    """Mostra análise por categorias"""
    st.subheader("Análise por Categorias")
    
    # Filtro por tipo
    type_filter = st.selectbox(
        "Tipo de Transação",
        ["Despesa", "Receita", "Investimento"]
    )
    
    # Filtrar dados
    df_filtered = df[df['type'] == type_filter]
    
    # Gráfico de barras por categoria
    df_cat = df_filtered.groupby('category')['amount'].agg(['sum', 'count']).reset_index()
    df_cat.columns = ['Categoria', 'Total', 'Quantidade']
    df_cat = df_cat.sort_values('Total', ascending=True)
    
    fig = go.Figure(data=[
        go.Bar(
            x=df_cat['Total'],
            y=df_cat['Categoria'],
            orientation='h'
        )
    ])
    
    fig.update_layout(
        title=f'Total por Categoria - {type_filter}s',
        xaxis_title='Valor (R$)',
        yaxis_title='Categoria'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabela detalhada
    st.subheader(f"Detalhamento por Categoria - {type_filter}s")
    df_cat['Média'] = df_cat['Total'] / df_cat['Quantidade']
    df_cat['Total'] = df_cat['Total'].apply(lambda x: f"R$ {x:,.2f}")
    df_cat['Média'] = df_cat['Média'].apply(lambda x: f"R$ {x:,.2f}")
    st.dataframe(df_cat)
