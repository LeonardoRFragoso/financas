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
    por_categoria = df.groupby(['category', 'type'])['amount'].sum().reset_index()
    
    # Cálculos para a regra 50/30/20
    regra_50_30_20 = {
        "necessidades": df[(df['type'] == 'despesa') & (df['categoria_tipo'] == 'necessidade')]['amount'].sum(),
        "desejos": df[(df['type'] == 'despesa') & (df['categoria_tipo'] == 'desejo')]['amount'].sum(),
        "poupanca": df[(df['type'] == 'despesa') & (df['categoria_tipo'] == 'poupanca')]['amount'].sum(),
        "outros": df[(df['type'] == 'despesa') & (df['categoria_tipo'] == 'outros')]['amount'].sum()
    }
    
    # Calcular percentuais em relação à renda
    if receitas > 0:
        regra_50_30_20["necessidades_ideal"] = receitas * 0.5
        regra_50_30_20["desejos_ideal"] = receitas * 0.3
        regra_50_30_20["poupanca_ideal"] = receitas * 0.2
        
        regra_50_30_20["necessidades_percentual"] = (regra_50_30_20["necessidades"] / receitas) * 100
        regra_50_30_20["desejos_percentual"] = (regra_50_30_20["desejos"] / receitas) * 100
        regra_50_30_20["poupanca_percentual"] = (regra_50_30_20["poupanca"] / receitas) * 100
        regra_50_30_20["outros_percentual"] = (regra_50_30_20["outros"] / receitas) * 100
    else:
        # Valores padrão caso não haja receita
        regra_50_30_20.update({
            "necessidades_ideal": 0,
            "desejos_ideal": 0,
            "poupanca_ideal": 0,
            "necessidades_percentual": 0,
            "desejos_percentual": 0,
            "poupanca_percentual": 0,
            "outros_percentual": 0
        })
    
    return {
        "receitas": receitas,
        "despesas": despesas,
        "saldo": saldo,
        "dataframe": df,
        "por_categoria": por_categoria,
        "regra_50_30_20": regra_50_30_20
    }

def create_pie_chart(data, column, title):
    """Cria um gráfico de pizza a partir dos dados"""
    fig = px.pie(data, values='amount', names=column, title=title)
    return fig

def create_bar_chart(data, x, y, title):
    """Cria um gráfico de barras a partir dos dados"""
    fig = px.bar(data, x=x, y=y, title=title, color=x)
    return fig

def create_budget_comparison_chart(actual, ideal, labels):
    """Cria um gráfico comparando orçamento real vs ideal"""
    df = pd.DataFrame({
        'Categoria': labels * 2,
        'Valor': actual + ideal,
        'Tipo': ['Atual'] * len(actual) + ['Ideal'] * len(ideal)
    })
    
    fig = px.bar(
        df, 
        x='Categoria', 
        y='Valor', 
        color='Tipo',
        barmode='group',
        title='Comparação de Orçamento: Atual vs. Ideal (50/30/20)',
        labels={'Valor': 'Valor (R$)', 'Categoria': ''}
    )
    
    return fig

def get_monthly_summary(month=None, year=None):
    """Obtém um resumo das transações do mês"""
    if month is None:
        month = datetime.now().month
    if year is None:
        year = datetime.now().year
    
    conn = sqlite3.connect('financas.db')
    c = conn.cursor()
    
    # Receitas pagas do mês
    c.execute('''SELECT COALESCE(SUM(amount), 0) 
                 FROM transactions 
                 WHERE LOWER(type) = 'receita' 
                 AND LOWER(status) = 'pago'
                 AND strftime('%Y-%m', date) = ?''',
              (f"{year:04d}-{month:02d}",))
    receitas = c.fetchone()[0] or 0
    
    # Todas as despesas pagas do mês
    c.execute('''SELECT COALESCE(SUM(amount), 0) 
                 FROM transactions 
                 WHERE LOWER(type) = 'despesa'
                 AND LOWER(status) = 'pago'
                 AND strftime('%Y-%m', date) = ?''',
              (f"{year:04d}-{month:02d}",))
    despesas = c.fetchone()[0] or 0
    
    # Investimentos pagos do mês
    c.execute('''SELECT COALESCE(SUM(amount), 0) 
                 FROM transactions 
                 WHERE LOWER(type) = 'investimento'
                 AND LOWER(status) = 'pago'
                 AND strftime('%Y-%m', date) = ?''',
              (f"{year:04d}-{month:02d}",))
    investimentos = c.fetchone()[0] or 0
    
    conn.close()
    
    return {
        'receitas': receitas,
        'despesas': despesas,
        'investimentos': investimentos or 0,
        'saldo_mes': receitas - despesas - investimentos
    }

def get_balance():
    """Calcula o saldo atual considerando todas as transações pagas"""
    conn = sqlite3.connect('financas.db')
    c = conn.cursor()
    
    # Receitas pagas
    c.execute('''SELECT COALESCE(SUM(amount), 0) 
                 FROM transactions 
                 WHERE LOWER(type) = 'receita' AND LOWER(status) = 'pago' ''')
    total_receitas = c.fetchone()[0] or 0
    
    # Todas as despesas pagas
    c.execute('''SELECT COALESCE(SUM(amount), 0) 
                 FROM transactions 
                 WHERE LOWER(type) = 'despesa' AND LOWER(status) = 'pago' ''')
    total_despesas = c.fetchone()[0] or 0
    
    # Investimentos pagos
    c.execute('''SELECT COALESCE(SUM(amount), 0) 
                 FROM transactions 
                 WHERE LOWER(type) = 'investimento' AND LOWER(status) = 'pago' ''')
    total_investimentos = c.fetchone()[0] or 0
    
    # Saldo em conta (receitas - despesas - investimentos)
    saldo_conta = total_receitas - total_despesas - total_investimentos
    
    conn.close()
    return {
        'saldo_conta': saldo_conta,
        'total_investido': total_investimentos,
        'patrimonio_total': saldo_conta + total_investimentos,
        'total_receitas': total_receitas,
        'total_despesas': total_despesas
    }

def get_expense_distribution():
    """Retorna a distribuição de despesas por categoria"""
    conn = sqlite3.connect('financas.db')
    c = conn.cursor()
    
    c.execute("""
        SELECT category, COALESCE(SUM(amount), 0) as total
        FROM transactions
        WHERE LOWER(type) = 'despesa'
        GROUP BY category
        ORDER BY total DESC
    """)
    
    results = c.fetchall()
    conn.close()
    
    if not results:
        return None
    
    return {category: amount for category, amount in results}

def show_dashboard():
    st.title("Dashboard Financeiro")
    
    # Obter dados do mês atual
    summary = get_monthly_summary()
    balance = get_balance()
    
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
            go.Bar(name='Receitas', x=[''], y=[summary['receitas']], marker_color='green'),
            go.Bar(name='Despesas', x=[''], y=[summary['despesas'] - summary['investimentos']], marker_color='red'),
            go.Bar(name='Investimentos', x=[''], y=[summary['investimentos']], marker_color='blue')
        ])
        fig.update_layout(barmode='group')
        st.plotly_chart(fig, use_container_width=True, key="receitas_despesas_chart")
    
    with col2:
        st.subheader("Distribuição de Gastos")
        # Criar gráfico de pizza para categorias de despesas
        categorias_valores = get_expense_distribution()
        if categorias_valores:
            fig_pizza = go.Figure(data=[
                go.Pie(labels=list(categorias_valores.keys()),
                      values=list(categorias_valores.values()))
            ])
            fig_pizza.update_layout(showlegend=True)
            st.plotly_chart(fig_pizza, use_container_width=True, key="distribuicao_gastos_chart")
        else:
            st.info("Sem dados suficientes para mostrar a distribuição de gastos")
    
    # Regra 50/30/20
    st.subheader("Orçamento 50/30/20")
    st.write("Como funciona a regra 50/30/20?")
    st.write("Esta regra sugere dividir sua renda mensal da seguinte forma:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("50% para necessidades básicas")
    with col2:
        st.info("30% para desejos/gastos pessoais")
    with col3:
        st.info("20% para poupança e investimentos")
    
    # Verificar se existem receitas
    if balance['total_receitas'] > 0:
        # Calcular valores ideais
        necessidades_ideal = balance['total_receitas'] * 0.5
        desejos_ideal = balance['total_receitas'] * 0.3
        poupanca_ideal = balance['total_receitas'] * 0.2
        
        # Obter valores reais
        c = sqlite3.connect('financas.db')
        cursor = c.cursor()
        
        # Necessidades (despesas com categoria_tipo = 'necessidade')
        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE LOWER(type) = 'despesa'
            AND LOWER(categoria_tipo) = 'necessidade'
            AND LOWER(status) = 'pago'
        ''')
        necessidades_real = cursor.fetchone()[0] or 0
        
        # Desejos (despesas com categoria_tipo = 'desejo')
        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE LOWER(type) = 'despesa'
            AND LOWER(categoria_tipo) = 'desejo'
            AND LOWER(status) = 'pago'
        ''')
        desejos_real = cursor.fetchone()[0] or 0
        
        # Poupança (investimentos + despesas com categoria_tipo = 'poupanca')
        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE (LOWER(type) = 'investimento' OR (LOWER(type) = 'despesa' AND LOWER(categoria_tipo) = 'poupanca'))
            AND LOWER(status) = 'pago'
        ''')
        poupanca_real = cursor.fetchone()[0] or 0
        
        c.close()
        
        # Criar gráfico de comparação
        fig = go.Figure(data=[
            go.Bar(name='Real', x=['Necessidades', 'Desejos', 'Poupança'],
                  y=[necessidades_real, desejos_real, poupanca_real]),
            go.Bar(name='Ideal', x=['Necessidades', 'Desejos', 'Poupança'],
                  y=[necessidades_ideal, desejos_ideal, poupanca_ideal])
        ])
        
        fig.update_layout(barmode='group',
                         title='Comparação Real vs Ideal',
                         yaxis_title='Valor (R$)')
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Mostrar percentuais
        col1, col2, col3 = st.columns(3)
        
        with col1:
            percentual = (necessidades_real / balance['total_receitas']) * 100 if balance['total_receitas'] > 0 else 0
            st.metric("Necessidades", f"{percentual:.1f}%", f"{50 - percentual:.1f}%")
        
        with col2:
            percentual = (desejos_real / balance['total_receitas']) * 100 if balance['total_receitas'] > 0 else 0
            st.metric("Desejos", f"{percentual:.1f}%", f"{30 - percentual:.1f}%")
        
        with col3:
            percentual = (poupanca_real / balance['total_receitas']) * 100 if balance['total_receitas'] > 0 else 0
            st.metric("Poupança", f"{percentual:.1f}%", f"{20 - percentual:.1f}%")
    else:
        st.warning("Nenhuma receita registrada ainda.")
