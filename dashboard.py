import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from transactions_db import view_transactions
from categories import get_categories
import plotly.graph_objects as go
import sqlite3
from datetime import datetime

def calculate_summary(transactions):
    """Calcula o resumo financeiro a partir das transações"""
    if not transactions:
        return {"receitas": 0, "despesas": 0, "saldo": 0, "por_categoria": {}, "regra_50_30_20": {}}
    
    # Definir todas as colunas da tabela transactions
    columns = ['id', 'user_id', 'description', 'amount', 'category', 'date', 
               'due_date', 'type', 'status', 'recurring', 'priority', 
               'quinzena', 'installments', 'current_installment', 
               'fixed_expense', 'categoria_tipo', 'created_at']
    
    df = pd.DataFrame(transactions, columns=columns)
    
    # Converter para minúsculas para garantir consistência
    df['type'] = df['type'].str.lower()
    
    receitas = df[df['type'] == 'receita']['amount'].sum()
    despesas = df[df['type'] == 'despesa']['amount'].sum()
    saldo = receitas - despesas
    
    # Agregação por categoria
    por_categoria = {}
    df_despesas = df[df['type'] == 'despesa']
    
    if not df_despesas.empty:
        categorias = df_despesas.groupby('category')['amount'].sum().to_dict()
        for cat, valor in categorias.items():
            por_categoria[cat] = valor
    
    # Cálculo de investimentos
    investimentos = 0
    if 'categoria_tipo' in df.columns:
        df_investimentos = df[(df['type'] == 'despesa') & (df['categoria_tipo'] == 'Investimento')]
        if not df_investimentos.empty:
            investimentos = df_investimentos['amount'].sum()
    
    # Regra 50/30/20
    # 50% Necessidades, 30% Desejos, 20% Investimentos/Poupança
    regra_50_30_20 = {
        "Necessidades": 0,
        "Desejos": 0,
        "Investimentos": investimentos
    }
    
    if 'categoria_tipo' in df.columns:
        df_necessidades = df[(df['type'] == 'despesa') & (df['categoria_tipo'] == 'Necessidade')]
        if not df_necessidades.empty:
            regra_50_30_20["Necessidades"] = df_necessidades['amount'].sum()
        
        df_desejos = df[(df['type'] == 'despesa') & (df['categoria_tipo'] == 'Desejo')]
        if not df_desejos.empty:
            regra_50_30_20["Desejos"] = df_desejos['amount'].sum()
    
    return {
        "receitas": receitas,
        "despesas": despesas,
        "saldo_mes": saldo,
        "investimentos": investimentos,
        "por_categoria": por_categoria,
        "regra_50_30_20": regra_50_30_20
    }

# Função para obter cores baseadas na configuração do tema
def get_theme_colors(use_dark_theme=None):
    """Retorna um conjunto de cores baseado no tema definido."""
    # Se o tema não for especificado, verificar a configuração
    if use_dark_theme is None:
        # Inicializar a configuração se não existir
        if 'use_dark_theme' not in st.session_state:
            st.session_state.use_dark_theme = False
        use_dark_theme = st.session_state.use_dark_theme
        
    if use_dark_theme:
        return {
            'background': '#1e2126',
            'paper_bgcolor': '#1e2126',
            'font_color': '#fafafa',
            'grid_color': 'rgba(255, 255, 255, 0.1)',
            'revenue_color': '#4CAF50',
            'expense_color': '#EF5350',
            'investment_color': '#42A5F5',
            'colorscale': 'Plasma'
        }
    else:
        return {
            'background': 'white',
            'paper_bgcolor': 'white',
            'font_color': '#262730',
            'grid_color': 'rgba(0, 0, 0, 0.1)',
            'revenue_color': '#4CAF50',
            'expense_color': '#EF5350',
            'investment_color': '#42A5F5',
            'colorscale': 'Viridis'
        }

def create_pie_chart(data, column, title):
    """Cria um gráfico de pizza a partir dos dados com compatibilidade de tema."""
    theme_colors = get_theme_colors()
    fig = px.pie(data, names=column, title=title)
    
    # Atualizar layout com cores do tema
    fig.update_layout(
        title_font_color=theme_colors['font_color'],
        font_color=theme_colors['font_color'],
        paper_bgcolor=theme_colors['paper_bgcolor'],
        plot_bgcolor=theme_colors['background'],
        legend_font_color=theme_colors['font_color']
    )
    
    return fig

def create_bar_chart(data, x, y, title):
    """Cria um gráfico de barras a partir dos dados com compatibilidade de tema."""
    theme_colors = get_theme_colors()
    fig = px.bar(data, x=x, y=y, title=title)
    
    # Atualizar layout com cores do tema
    fig.update_layout(
        title_font_color=theme_colors['font_color'],
        font_color=theme_colors['font_color'],
        paper_bgcolor=theme_colors['paper_bgcolor'],
        plot_bgcolor=theme_colors['background'],
        xaxis=dict(
            gridcolor=theme_colors['grid_color'],
            tickfont=dict(color=theme_colors['font_color'])
        ),
        yaxis=dict(
            gridcolor=theme_colors['grid_color'],
            tickfont=dict(color=theme_colors['font_color'])
        )
    )
    
    return fig

def create_budget_comparison_chart(actual, ideal, labels):
    """Cria um gráfico comparando orçamento real vs ideal com compatibilidade de tema."""
    theme_colors = get_theme_colors()
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Ideal',
        x=labels,
        y=ideal,
        marker_color='rgba(55, 83, 109, 0.7)'
    ))
    
    fig.add_trace(go.Bar(
        name='Real',
        x=labels,
        y=actual,
        marker_color='rgba(26, 118, 255, 0.7)'
    ))
    
    fig.update_layout(
        title='Comparação de Orçamento',
        barmode='group',
        title_font_color=theme_colors['font_color'],
        font_color=theme_colors['font_color'],
        paper_bgcolor=theme_colors['paper_bgcolor'],
        plot_bgcolor=theme_colors['background'],
        xaxis=dict(
            gridcolor=theme_colors['grid_color'],
            tickfont=dict(color=theme_colors['font_color'])
        ),
        yaxis=dict(
            gridcolor=theme_colors['grid_color'],
            tickfont=dict(color=theme_colors['font_color'])
        )
    )
    
    return fig

def get_monthly_summary(month=None, year=None):
    """Obtém um resumo das transações do mês"""
    # Se mês ou ano não forem fornecidos, usar o mês e ano atual
    if month is None:
        month = datetime.now().month
    if year is None:
        year = datetime.now().year
    
    # Formatar como strings para a consulta SQL
    month_str = str(month).zfill(2)
    year_str = str(year)
    
    # Data inicial e final para o período
    start_date = f"{year_str}-{month_str}-01"
    
    # Determinar a data final com base no mês
    if month == 12:
        end_date = f"{year_str + 1}-01-01"
    else:
        end_date = f"{year_str}-{str(month + 1).zfill(2)}-01"
    
    # Consultar as transações do período
    try:
        # Conectar ao banco de dados
        conn = sqlite3.connect('financas.db')
        cursor = conn.cursor()
        
        # Obter todas as transações do período
        cursor.execute("""
            SELECT * FROM transactions 
            WHERE date >= ? AND date < ?
        """, (start_date, end_date))
        
        transactions = cursor.fetchall()
        conn.close()
        
        # Calcular o resumo
        summary = calculate_summary(transactions)
        
        return summary
    except Exception as e:
        st.error(f"Erro ao obter resumo mensal: {e}")
        return {
            "receitas": 0,
            "despesas": 0,
            "saldo_mes": 0,
            "investimentos": 0,
            "por_categoria": {},
            "regra_50_30_20": {"Necessidades": 0, "Desejos": 0, "Investimentos": 0}
        }

def get_balance():
    """Calcula o saldo atual"""
    try:
        # Conectar ao banco de dados
        conn = sqlite3.connect('financas.db')
        cursor = conn.cursor()
        
        # Saldo em conta (receitas - despesas pago)
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN type = 'Receita' AND status = 'pago' THEN amount ELSE 0 END) - 
                SUM(CASE WHEN type = 'Despesa' AND status = 'pago' AND categoria_tipo != 'Investimento' THEN amount ELSE 0 END)
            FROM transactions
        """)
        
        saldo_conta = cursor.fetchone()[0] or 0
        
        # Total investido
        cursor.execute("""
            SELECT SUM(amount)
            FROM transactions
            WHERE type = 'Despesa' AND categoria_tipo = 'Investimento' AND status = 'pago'
        """)
        
        total_investido = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "saldo_conta": saldo_conta,
            "total_investido": total_investido,
            "patrimonio_total": saldo_conta + total_investido
        }
    except Exception as e:
        st.error(f"Erro ao calcular saldo: {e}")
        return {"saldo_conta": 0, "total_investido": 0, "patrimonio_total": 0}

def get_expense_distribution():
    """Retorna a distribuição de despesas por categoria"""
    try:
        conn = sqlite3.connect('financas.db')
        cursor = conn.cursor()
        
        # Obter categorias e valores
        cursor.execute("""
            SELECT category, SUM(amount)
            FROM transactions
            WHERE type = 'Despesa'
            GROUP BY category
            ORDER BY SUM(amount) DESC
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        # Convertendo para dicionário
        categorias = {}
        for cat, valor in results:
            categorias[cat] = valor
            
        return categorias
    except Exception as e:
        st.error(f"Erro ao obter distribuição de gastos: {e}")
        return {}

def show_dashboard():
    st.title("Dashboard Financeiro")
    
    # Configuração de tema para gráficos
    col_theme1, col_theme2 = st.columns([2, 3])
    with col_theme1:
        if st.toggle("Usar tema escuro para gráficos", value=st.session_state.get('use_dark_theme', False)):
            st.session_state.use_dark_theme = True
        else:
            st.session_state.use_dark_theme = False
    
    # Obter dados do mês atual
    summary = get_monthly_summary()
    balance = get_balance()
    
    # Obter cores do tema
    theme_colors = get_theme_colors()
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Saldo em Conta", f"R$ {balance['saldo_conta']:,.2f}")
    
    with col2:
        st.metric("Total Investido", f"R$ {balance['total_investido']:,.2f}")
    
    with col3:
        st.metric("Patrimônio Total", f"R$ {balance['patrimonio_total']:,.2f}")
    
    with col4:
        saldo_mes = summary['saldo_mes']
        st.metric("Saldo do Mês", f"R$ {saldo_mes:,.2f}")
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Receitas vs Despesas do Mês")
        fig = go.Figure(data=[
            go.Bar(name='Receitas', x=[''], y=[summary['receitas']], marker_color=theme_colors['revenue_color']),
            go.Bar(name='Despesas', x=[''], y=[summary['despesas'] - summary['investimentos']], marker_color=theme_colors['expense_color']),
            go.Bar(name='Investimentos', x=[''], y=[summary['investimentos']], marker_color=theme_colors['investment_color'])
        ])
        fig.update_layout(
            barmode='group',
            paper_bgcolor=theme_colors['paper_bgcolor'],
            plot_bgcolor=theme_colors['background'],
            font_color=theme_colors['font_color'],
            xaxis=dict(gridcolor=theme_colors['grid_color']),
            yaxis=dict(gridcolor=theme_colors['grid_color'])
        )
        st.plotly_chart(fig, use_container_width=True, key="receitas_despesas_chart")
    
    with col2:
        st.subheader("Distribuição de Gastos")
        # Criar gráfico de pizza para categorias de despesas
        categorias_valores = get_expense_distribution()
        if categorias_valores:
            fig_pizza = go.Figure(data=[
                go.Pie(labels=list(categorias_valores.keys()),
                      values=list(categorias_valores.values()),
                      marker=dict(colors=px.colors.sequential[theme_colors['colorscale']]))
            ])
            fig_pizza.update_layout(
                showlegend=True,
                paper_bgcolor=theme_colors['paper_bgcolor'],
                plot_bgcolor=theme_colors['background'],
                font_color=theme_colors['font_color']
            )
            st.plotly_chart(fig_pizza, use_container_width=True, key="distribuicao_gastos_chart")
    
    # Regra 50/30/20
    st.subheader("Orçamento 50/30/20")
    col1, col2 = st.columns(2)
    
    with col1:
        # Cálculo da regra 50/30/20 ideal
        receita_total = summary['receitas']
        regra_ideal = {
            "Necessidades": receita_total * 0.5,
            "Desejos": receita_total * 0.3,
            "Investimentos": receita_total * 0.2
        }
        
        # Valores reais
        regra_real = summary['regra_50_30_20']
        
        # Mostrar comparação visual
        st.text("Comparação Ideal vs Real (R$)")
        
        # Tabela de comparação
        data = {
            "Categoria": list(regra_ideal.keys()),
            "Ideal (R$)": [f"R$ {v:,.2f}" for v in regra_ideal.values()],
            "Real (R$)": [f"R$ {regra_real.get(k, 0):,.2f}" for k in regra_ideal.keys()],
            "% da Receita": [f"{(regra_real.get(k, 0) / receita_total * 100 if receita_total > 0 else 0):,.1f}%" for k in regra_ideal.keys()]
        }
        
        # Mostrar como DataFrame
        df_comparacao = pd.DataFrame(data)
        st.dataframe(df_comparacao)
    
    with col2:
        # Gráfico de barras comparativo
        if receita_total > 0:
            fig = create_budget_comparison_chart(
                [regra_real.get(k, 0) for k in regra_ideal.keys()],
                list(regra_ideal.values()),
                list(regra_ideal.keys())
            )
            st.plotly_chart(fig, use_container_width=True, key="orcamento_chart")
        else:
            st.info("Sem receitas neste mês para comparar com o orçamento ideal.")
    
    # Resumo por categoria
    st.subheader("Despesas por Categoria")
    
    if summary['por_categoria']:
        # Criar DataFrame para visualização
        df_categorias = pd.DataFrame([
            {"Categoria": k, "Valor": v}
            for k, v in summary['por_categoria'].items()
        ])
        
        # Ordenar por valor
        df_categorias = df_categorias.sort_values("Valor", ascending=False)
        
        # Mostrar como DataFrame
        st.dataframe(df_categorias)
        
        # Gráfico de barras
        fig = create_bar_chart(df_categorias, "Categoria", "Valor", "Despesas por Categoria")
        st.plotly_chart(fig, use_container_width=True, key="categorias_chart")
    else:
        st.info("Sem despesas neste mês para mostrar as categorias.")
