import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlite3
from dateutil.relativedelta import relativedelta
import json
from transactions_db import view_goals as get_goals
from transactions_db import view_transactions
from categories import get_categories  # função original para obter categorias
from theme_manager import init_theme_manager, get_theme_colors, theme_config_section, apply_theme_to_plotly_chart
import calendar
import io
import base64
import numpy as np
from supabase_db import init_supabase
import random

# ---------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------

def parse_date(date_str):
    """
    Converte uma string em objeto datetime usando formatos comuns.
    Retorna None se a conversão não for possível.
    """
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    return None

def filter_transactions(transactions, start_date=None, end_date=None, category_filter=None, transaction_types=None):
    """
    Filtra a lista de transações com base em data, categorias e tipos.
    Se nenhum filtro de data for fornecido, mantém apenas as transações do mês atual.
    """
    filtered = []
    for transaction in transactions:
        date_str = transaction.get('date')
        trans_date = parse_date(date_str)
        if not trans_date:
            continue

        # Filtro por data
        if start_date and end_date:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            if not (start <= trans_date <= end):
                continue
        elif not (start_date or end_date):
            # Se não foi passado filtro, manter apenas transações do mês atual
            today = datetime.now()
            if not (trans_date.month == today.month and trans_date.year == today.year):
                continue

        filtered.append(transaction)

    # Filtro por categoria (se informado)
    if category_filter and len(category_filter) > 0:
        filtered = [t for t in filtered if t.get('category') in category_filter]

    # Filtro por tipo de transação (case insensitive e considerando variações)
    if transaction_types and len(transaction_types) > 0:
        filtered_by_type = []
        for transaction in filtered:
            t_type = transaction.get('type', '').lower()
            for tipo in transaction_types:
                tipo_lower = tipo.lower()
                if (tipo_lower == t_type or
                    (tipo_lower == 'receita' and t_type in ['receita', 'income', 'revenue']) or
                    (tipo_lower == 'despesa' and t_type in ['despesa', 'expense', 'expenses']) or
                    (tipo_lower == 'investimento' and t_type in ['investimento', 'investment'])):
                    filtered_by_type.append(transaction)
                    break
        filtered = filtered_by_type

    return filtered

# ---------------------------------------------------------------------
# Funções de Conexão e Acesso ao Banco de Dados
# ---------------------------------------------------------------------

def connect_to_database():
    """
    Estabelece conexão com o banco de dados.
    
    Returns:
        sqlite3.Connection ou supabase.Client: Conexão com o banco de dados.
    """
    try:
        return init_supabase()
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        raise

# ---------------------------------------------------------------------
# Funções de Processamento dos Dados
# ---------------------------------------------------------------------

def calculate_summary(transactions):
    """
    Calcula o resumo financeiro a partir das transações.
    
    Args:
        transactions (list): Lista de transações a serem analisadas.
        
    Returns:
        dict: Resumo financeiro contendo receitas, despesas, saldo, investimentos,
              distribuição por categoria, regra 50/30/20 e KPIs.
    """
    if not transactions:
        return {
            "receitas": 0, 
            "despesas": 0, 
            "saldo_mes": 0, 
            "investimentos": 0, 
            "por_categoria": {}, 
            "regra_50_30_20": {"Necessidades": 0, "Desejos": 0, "Investimentos": 0}, 
            "kpis": {"saude_financeira": "Sem dados", "taxa_poupanca": 0, "relacao_despesa_receita": 0}
        }
    
    print(f"Analisando {len(transactions)} transações")
    tipos_unicos = set(str(t.get('type', '')).lower() for t in transactions)
    print(f"Tipos únicos encontrados: {tipos_unicos}")
    
    for t in transactions:
        print(f"ID: {t.get('id')} | Desc: {t.get('description')} | Tipo: {t.get('type')} | Status: {t.get('status')} | Valor: {t.get('amount')} | Categoria Tipo: {t.get('categoria_tipo')}")
    
    receitas = 0
    despesas = 0
    investimentos = 0

    for transaction in transactions:
        try:
            tipo = str(transaction.get('type', '')).lower()
            valor = float(transaction.get('amount', 0))
            status = str(transaction.get('status', '')).lower()
            
            if status not in ['pago', 'paid']:
                print(f"Transação não considerada - status: {status}: {transaction.get('description')}")
                continue
                
            if tipo in ['receita', 'income', 'revenue']:
                receitas += valor
                print(f"Receita encontrada: {transaction.get('description')} - R${valor} (Tipo: {tipo})")
            elif tipo in ['despesa', 'expense', 'expenses']:
                despesas += valor
                print(f"Despesa encontrada: {transaction.get('description')} - R${valor} (Tipo: {tipo})")
            elif tipo in ['investimento', 'investment']:
                investimentos += valor
                print(f"Investimento encontrado: {transaction.get('description')} - R${valor} (Tipo: {tipo})")
            else:
                print(f"Tipo desconhecido: {tipo} para transação: {transaction.get('description')}")
        except Exception as e:
            print(f"Erro ao processar transação: {e}")
            continue

    saldo = receitas - despesas - investimentos

    por_categoria = {}
    for transaction in transactions:
        try:
            tipo = str(transaction.get('type', '')).lower()
            if tipo not in ['despesa', 'expense', 'expenses']:
                continue
            status = str(transaction.get('status', '')).lower()
            if status not in ['pago', 'paid']:
                continue
            categoria_tipo = str(transaction.get('categoria_tipo', '')).lower()
            valor = float(transaction.get('amount', 0))
            
            if categoria_tipo in ['necessidade', 'necessidades']:
                categoria = 'Necessidades'
            elif categoria_tipo in ['desejo', 'desejos']:
                categoria = 'Lazer'
            elif categoria_tipo == 'investimento':
                categoria = 'Investimentos'
            else:
                categoria = 'Outros'
            
            por_categoria[categoria] = por_categoria.get(categoria, 0) + valor
        except Exception as e:
            print(f"Erro ao processar categoria: {e}")
            continue

    regra_50_30_20 = {"Necessidades": 0, "Desejos": 0, "Investimentos": investimentos}
    for transaction in transactions:
        try:
            tipo = str(transaction.get('type', '')).lower()
            if tipo not in ['despesa', 'expense', 'expenses']:
                continue
            status = str(transaction.get('status', '')).lower()
            if status not in ['pago', 'paid']:
                continue
            categoria_tipo = str(transaction.get('categoria_tipo', '')).lower()
            valor = float(transaction.get('amount', 0))
            if categoria_tipo in ['necessidade', 'necessidades']:
                regra_50_30_20["Necessidades"] += valor
                print(f"Adicionando à Necessidades: {transaction.get('description')} - R${valor}")
            elif categoria_tipo in ['desejo', 'desejos']:
                regra_50_30_20["Desejos"] += valor
                print(f"Adicionando à Desejos: {transaction.get('description')} - R${valor}")
            else:
                print(f"Categoria tipo não mapeada: {categoria_tipo} para transação: {transaction.get('description')}")
        except Exception as e:
            print(f"Erro ao processar regra 50/30/20: {e}")
            continue

    taxa_poupanca = (investimentos / receitas * 100) if receitas > 0 else 0
    relacao_despesa_receita = ((despesas + investimentos) / receitas * 100) if receitas > 0 else 0

    if saldo > 0 and taxa_poupanca >= 10:
        saude_financeira = "Ótima"
    elif saldo > 0:
        saude_financeira = "Boa"
    elif saldo == 0:
        saude_financeira = "Atenção"
    else:
        saude_financeira = "Crítica"

    print(f"Resumo calculado: Receitas={receitas}, Despesas={despesas}, Investimentos={investimentos}")
    print(f"Regra 50/30/20: {regra_50_30_20}")
    
    return {
        "receitas": receitas,
        "despesas": despesas,
        "saldo_mes": saldo,
        "investimentos": investimentos,
        "por_categoria": por_categoria,
        "regra_50_30_20": regra_50_30_20,
        "kpis": {
            "saude_financeira": saude_financeira,
            "taxa_poupanca": taxa_poupanca,
            "relacao_despesa_receita": relacao_despesa_receita
        }
    }

def create_pie_chart(data, column, title):
    theme_colors = get_theme_colors()

    values = data["Valor"]
    labels = data[column]

    fig = go.Figure()

    fig.add_trace(go.Pie(
        labels=labels,
        values=values,
        hole=0.5,
        textinfo='percent+label',
        textfont=dict(color=theme_colors['font_color']),
        insidetextfont=dict(color=theme_colors['font_color']),
        outsidetextfont=dict(color=theme_colors['font_color']),
        insidetextorientation='radial',
        marker=dict(
            line=dict(color=theme_colors['plot_bgcolor'], width=2)
        ),
        hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>"
    ))

    fig.update_layout(
        title=dict(
            text=title,
            font=dict(color=theme_colors['font_color'])
        ),
        showlegend=True,
        paper_bgcolor=theme_colors['paper_bgcolor'],
        plot_bgcolor=theme_colors['plot_bgcolor'],
        font=dict(color=theme_colors['font_color']),
        legend=dict(
            font=dict(color=theme_colors['font_color']),
            bgcolor=theme_colors['paper_bgcolor'],
            bordercolor=theme_colors['grid_color']
        ),
        margin=dict(t=40, b=20, l=20, r=20)
    )

    return fig

def create_bar_chart(data, x, y, title):
    """
    Cria um gráfico de barras com tema.
    
    Args:
        data (DataFrame): Dados para o gráfico.
        x (str): Coluna para eixo X.
        y (str): Coluna para eixo Y.
        title (str): Título do gráfico.
        
    Returns:
        Figura Plotly com tema aplicado.
    """
    theme_colors = get_theme_colors()
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=data[x],
        y=data[y],
        marker_color=theme_colors['accent_color'],
        text=data[y],
        textposition='auto',
        textfont=dict(color=theme_colors['font_color'])
    ))
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(color=theme_colors['font_color'])
        ),
        paper_bgcolor=theme_colors['paper_bgcolor'],
        plot_bgcolor=theme_colors['plot_bgcolor'],
        font=dict(color=theme_colors['font_color']),
        legend=dict(
            font=dict(color=theme_colors['font_color']),
            bgcolor=theme_colors['paper_bgcolor'],
            bordercolor=theme_colors['grid_color']
        ),
        xaxis=dict(
            gridcolor=theme_colors['grid_color'],
            tickfont=dict(color=theme_colors['font_color']),
            title_font=dict(color=theme_colors['font_color'])
        ),
        yaxis=dict(
            gridcolor=theme_colors['grid_color'],
            tickfont=dict(color=theme_colors['font_color']),
            title_font=dict(color=theme_colors['font_color'])
        ),
        margin=dict(t=40, b=20, l=20, r=20)
    )
    return fig

def create_budget_comparison_chart(actual, ideal, labels):
    """
    Compara o orçamento real versus ideal com um gráfico de barras.
    
    Args:
        actual (list): Valores reais.
        ideal (list): Valores ideais.
        labels (list): Rótulos das categorias.
        
    Returns:
        Figura Plotly com tema aplicado.
    """
    theme_colors = get_theme_colors()
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Ideal',
        x=labels,
        y=ideal,
        marker_color=theme_colors['success_color']
    ))
    fig.add_trace(go.Bar(
        name='Real',
        x=labels,
        y=actual,
        marker_color=theme_colors['accent_color']
    ))
    fig.update_layout(
        title='Comparação de Orçamento',
        barmode='group'
    )
    return apply_theme_to_plotly_chart(fig)

def create_trend_chart(titulo, dados_mensais, y_label="Valor (R$)"):
    """
    Cria um gráfico de linha para visualizar a tendência ao longo do tempo.
    
    Args:
        titulo (str): Título do gráfico.
        dados_mensais (dict): Dicionário no formato {série: {período: valor}}.
        y_label (str): Rótulo do eixo Y.
        
    Returns:
        Figura Plotly com tema aplicado.
    """
    theme_colors = get_theme_colors()
    fig = go.Figure()
    for serie, valores in dados_mensais.items():
        if 'receita' in serie.lower():
            cor = theme_colors['revenue_color']
        elif 'investimento' in serie.lower():
            cor = theme_colors['investment_color']
        else:
            cor = theme_colors['expense_color']
        periodos = list(valores.keys())
        periodos_formatados = []
        for periodo in periodos:
            if '-' in periodo:
                ano, mes = periodo.split('-')
                periodos_formatados.append(f"{mes}/{ano}")
            else:
                periodos_formatados.append(periodo)
        fig.add_trace(go.Scatter(
            x=periodos_formatados,
            y=list(valores.values()),
            mode='lines+markers',
            name=serie,
            line=dict(color=cor)
        ))
    fig.update_layout(
        title=titulo,
        xaxis_title="Período",
        yaxis_title=y_label
    )
    return apply_theme_to_plotly_chart(fig)

def projetar_valores_futuros(dados_historicos, meses_futuros=3, metodo="media_movel"):
    """
    Projeta valores futuros com base em dados históricos usando média móvel ou tendência linear.
    
    Args:
        dados_historicos (dict): Histórico no formato {período: valor}.
        meses_futuros (int): Número de meses para projeção.
        metodo (str): "media_movel" ou "tendencia".
        
    Returns:
        dict: Projeção no formato {período: valor}.
    """
    if not dados_historicos or len(dados_historicos) < 2:
        return {}
    periodos = sorted(list(dados_historicos.keys()))
    valores = [dados_historicos[p] for p in periodos]
    if metodo == "media_movel":
        n_meses = min(3, len(valores))
        media = sum(valores[-n_meses:]) / n_meses
        previsao = [media] * meses_futuros
    elif metodo == "tendencia":
        if len(valores) >= 2:
            tendencia = valores[-1] - valores[-2]
            tendencia = max(min(tendencia, valores[-1] * 0.2), -valores[-1] * 0.2)
            previsao = [valores[-1] + tendencia * (i+1) for i in range(meses_futuros)]
        else:
            previsao = [valores[-1]] * meses_futuros
    else:
        previsao = [valores[-1]] * meses_futuros

    ultimo_periodo = periodos[-1]
    if '-' in ultimo_periodo:
        ano, mes = ultimo_periodo.split('-')
        periodos_futuros = []
        for i in range(1, meses_futuros + 1):
            mes_futuro = int(mes) + i
            ano_futuro = int(ano)
            if mes_futuro > 12:
                ano_futuro += (mes_futuro - 1) // 12
                mes_futuro = ((mes_futuro - 1) % 12) + 1
            periodos_futuros.append(f"{ano_futuro}-{mes_futuro:02d}")
    else:
        periodos_futuros = [f"P{i+1}" for i in range(meses_futuros)]
    projecoes = {periodos_futuros[i]: previsao[i] for i in range(meses_futuros)}
    return projecoes

# ---------------------------------------------------------------------
# Funções de Resumo Mensal e Histórico
# ---------------------------------------------------------------------

def get_monthly_summary(month=None, year=None, start_date=None, end_date=None, category_filter=None, transaction_types=None):
    """
    Obtém o resumo mensal de transações aplicando os filtros de data, categoria e tipo.
    
    Args:
        month (int, opcional): Mês para filtrar.
        year (int, opcional): Ano para filtrar.
        start_date (str, opcional): Data inicial (YYYY-MM-DD).
        end_date (str, opcional): Data final (YYYY-MM-DD).
        category_filter (list, opcional): Lista de categorias.
        transaction_types (list, opcional): Lista de tipos de transação.
        
    Returns:
        dict: Resumo financeiro do período.
    """
    try:
        transactions = view_transactions()
        if not transactions:
            st.warning("Nenhuma transação encontrada no banco de dados.")
            return {
                "receitas": 0, "despesas": 0, "saldo_mes": 0, "investimentos": 0,
                "por_categoria": {}, "regra_50_30_20": {},
                "kpis": {"saude_financeira": "Sem dados", "taxa_poupanca": 0, "relacao_despesa_receita": 0}
            }
        filtered_transactions = filter_transactions(transactions, start_date, end_date, category_filter, transaction_types)
        print(f"Após filtragem, restaram {len(filtered_transactions)} transações")
        tipos_encontrados = set(t.get('type', '').lower() for t in filtered_transactions)
        print(f"Tipos encontrados após filtragem: {tipos_encontrados}")
        summary = calculate_summary(filtered_transactions)
        print(f"DEBUG - Resumo calculado: Receitas={summary['receitas']}, Despesas={summary['despesas']}, Investimentos={summary['investimentos']}")
        return summary
    except Exception as e:
        st.error(f"Erro ao obter resumo mensal: {e}")
        import traceback
        st.error(traceback.format_exc())
        return {
            "receitas": 0, "despesas": 0, "saldo_mes": 0, "investimentos": 0,
            "por_categoria": {}, "regra_50_30_20": {},
            "kpis": {"saude_financeira": "Sem dados", "taxa_poupanca": 0, "relacao_despesa_receita": 0}
        }

def get_historical_data(months=12):
    """
    Obtém dados históricos de receitas, despesas, investimentos e saldo para os últimos 'months' meses.
    
    Args:
        months (int): Número de meses no histórico.
        
    Returns:
        dict: Dados organizados por período (YYYY-MM) para cada métrica.
    """
    try:
        transactions = view_transactions()
        current_date = datetime.now()
        dados_historicos = {"Receitas": {}, "Despesas": {}, "Investimentos": {}, "Saldo": {}}
        for i in range(months-1, -1, -1):
            data_ref = current_date.replace(day=1) - relativedelta(months=i)
            periodo = f"{data_ref.year}-{data_ref.month:02d}"
            dados_historicos["Receitas"][periodo] = 0
            dados_historicos["Despesas"][periodo] = 0
            dados_historicos["Investimentos"][periodo] = 0
            if data_ref.month == 12:
                month_end = data_ref.replace(year=data_ref.year+1, month=1, day=1).strftime("%Y-%m-%d")
            else:
                month_end = data_ref.replace(month=data_ref.month+1, day=1).strftime("%Y-%m-%d")
            month_start = data_ref.strftime("%Y-%m-%d")
            for transaction in transactions:
                trans_date = transaction.get('date', '')
                if month_start <= trans_date < month_end:
                    valor = float(transaction.get('amount', 0))
                    tipo = str(transaction.get('type', '')).lower()
                    status = str(transaction.get('status', '')).lower()
                    if status not in ['pago', 'paid']:
                        continue
                    if tipo in ['receita', 'income', 'revenue']:
                        dados_historicos["Receitas"][periodo] += valor
                        dados_historicos["Saldo"][periodo] = dados_historicos["Saldo"].get(periodo, 0) + valor
                    elif tipo in ['despesa', 'expense', 'expenses']:
                        dados_historicos["Despesas"][periodo] += valor
                        dados_historicos["Saldo"][periodo] = dados_historicos["Saldo"].get(periodo, 0) - valor
                    elif tipo in ['investimento', 'investment']:
                        dados_historicos["Investimentos"][periodo] += valor
                        dados_historicos["Saldo"][periodo] = dados_historicos["Saldo"].get(periodo, 0) - valor
            if periodo not in dados_historicos["Saldo"]:
                dados_historicos["Saldo"][periodo] = 0
            print(f"Dados do período {periodo}:")
            print(f"Receitas: R$ {dados_historicos['Receitas'][periodo]:.2f}")
            print(f"Despesas: R$ {dados_historicos['Despesas'][periodo]:.2f}")
            print(f"Investimentos: R$ {dados_historicos['Investimentos'][periodo]:.2f}")
            print(f"Saldo: R$ {dados_historicos['Saldo'][periodo]:.2f}")
            print("---")
        dados_historicos["Receitas"] = {k: dados_historicos["Receitas"][k] for k in sorted(dados_historicos["Receitas"].keys())}
        dados_historicos["Despesas"] = {k: dados_historicos["Despesas"][k] for k in sorted(dados_historicos["Despesas"].keys())}
        dados_historicos["Investimentos"] = {k: dados_historicos["Investimentos"][k] for k in sorted(dados_historicos["Investimentos"].keys())}
        dados_historicos["Saldo"] = {k: dados_historicos["Saldo"][k] for k in sorted(dados_historicos["Saldo"].keys())}
        return dados_historicos
    except Exception as e:
        st.error(f"Erro ao obter dados históricos: {e}")
        import traceback
        st.error(traceback.format_exc())
        return {"Receitas": {}, "Despesas": {}, "Investimentos": {}, "Saldo": {}}

def get_balance():
    """
    Calcula o saldo atual, total investido e patrimônio total.
    
    Returns:
        dict: {"saldo_conta": ..., "total_investido": ..., "patrimonio_total": ...}
    """
    try:
        transactions = view_transactions()
        saldo_conta = 0
        total_investido = 0
        for transaction in transactions:
            status = str(transaction.get('status', '')).lower()
            if status not in ['pago', 'paid']:
                continue
            tipo = str(transaction.get('type', '')).lower()
            valor = float(transaction.get('amount', 0))
            if tipo in ['receita', 'income', 'revenue']:
                saldo_conta += valor
            elif tipo in ['despesa', 'expense', 'expenses']:
                saldo_conta -= valor
            elif tipo in ['investimento', 'investment']:
                saldo_conta -= valor
                total_investido += valor
        patrimonio_total = saldo_conta + total_investido
        return {
            "saldo_conta": saldo_conta,
            "total_investido": total_investido,
            "patrimonio_total": patrimonio_total
        }
    except Exception as e:
        st.error(f"Erro ao calcular saldo: {e}")
        return {"saldo_conta": 0, "total_investido": 0, "patrimonio_total": 0}

def get_expense_distribution(category_filter=None, transactions_data=None):
    """
    Obtém a distribuição de despesas por categoria.
    
    Args:
        category_filter (list): Lista opcional de categorias para filtrar.
        transactions_data (list): Lista opcional de transações já filtradas.
        
    Returns:
        dict: {categoria: valor}
    """
    try:
        from transactions_db import view_transactions
        print("Buscando transações para distribuição de despesas...")
        if transactions_data is None:
            from supabase_db import init_supabase
            supabase = init_supabase()
            if not supabase:
                print("Erro ao conectar ao Supabase")
                return {}
            response = supabase.table("transactions").select("*").execute()
            transactions = response.data
            print(f"Buscando diretamente do Supabase: {len(transactions)} transações encontradas")
        else:
            transactions = transactions_data
            print(f"Usando transações fornecidas: {len(transactions)} transações")
        
        despesas = {}
        despesas_encontradas = 0
        print(f"Processando {len(transactions)} transações para análise de categorias")
        for transaction in transactions:
            tipo = str(transaction.get('type', '')).lower()
            categoria_tipo = str(transaction.get('categoria_tipo', '')).lower()
            status = str(transaction.get('status', '')).lower()
            print(f"Analisando: {transaction.get('description')}, Tipo: {tipo}, Categoria: {categoria_tipo}, Status: {status}, Valor: {transaction.get('amount')}")
            if tipo not in ['despesa', 'expense', 'expenses']:
                print(f"Ignorando (não é despesa): {transaction.get('description')} - Tipo: {tipo}")
                continue
                
            categoria = categoria_tipo if categoria_tipo else 'Outros'
            if categoria in ['necessidade', 'necessidades']:
                categoria = 'Necessidades'
            elif categoria in ['desejo', 'desejos']:
                categoria = 'Lazer'
            elif categoria == 'investimento':
                categoria = 'Investimentos'
            else:
                categoria = 'Outros'
            if category_filter and categoria not in category_filter:
                print(f"Ignorando (filtro de categoria): {transaction.get('description')}")
                continue
            valor = float(transaction.get('amount', 0))
            despesas[categoria] = despesas.get(categoria, 0) + valor
            print(f"Adicionando à categoria {categoria}: +R${valor:.2f} = R${despesas[categoria]:.2f}")
            despesas_encontradas += 1
        print(f"Total de despesas encontradas: {despesas_encontradas}")
        print(f"Distribuição de despesas final: {despesas}")
        return dict(sorted(despesas.items(), key=lambda x: x[1], reverse=True)) if despesas else {}
    except Exception as e:
        print(f"ERRO na distribuição de despesas: {e}")
        st.error(f"Erro ao obter distribuição de despesas: {e}")
        import traceback
        print(traceback.format_exc())
        return {}

def get_categories():
    """
    Obtém todas as categorias disponíveis para filtros.
    
    Returns:
        list: Lista de nomes das categorias.
    """
    from categories import get_categories as get_all_categories
    all_categories = get_all_categories()
    category_names = [cat.get("name", "") for cat in all_categories if cat.get("name")]
    return sorted(category_names)

def view_goals():
    """
    Recupera as metas financeiras do usuário.
    
    Returns:
        list: Lista de metas.
    """
    return get_goals()

# ---------------------------------------------------------------------
# Função Principal de Exibição do Dashboard
# ---------------------------------------------------------------------

def show_dashboard():
    """
    Exibe o dashboard financeiro completo com filtros, gráficos e KPIs.
    """
    init_theme_manager()
    theme_colors = get_theme_colors()
    theme_config_section()
    
    # Título e botão de atualização
    col_title, col_refresh = st.columns([5, 1])
    with col_title:
        st.title("Dashboard Financeiro")
    with col_refresh:
        theme_colors = get_theme_colors()
        button_style = f"""
        <style>
        div[data-testid="stButton"] button {{
            background-color: {theme_colors['accent_color']};
            color: white;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            border: none;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
            transition: all 0.3s;
        }}
        div[data-testid="stButton"] button:hover {{
            background-color: {theme_colors['investment_color']};
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
            transform: translateY(-2px);
        }}
        </style>
        """
        st.markdown(button_style, unsafe_allow_html=True)
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Sidebar com filtros
    with st.sidebar:
        st.subheader("📆 Período de Análise")
        periodo_opcoes = ["Mês Atual", "Mês Anterior", "Últimos 3 Meses", "Ano Atual", "Personalizado"]
        periodo_selecionado = st.selectbox("Selecione o período", periodo_opcoes)
        data_inicio = None
        data_fim = None
        data_atual = datetime.now()
        if periodo_selecionado == "Mês Atual":
            data_inicio = data_atual.replace(day=1)
            if data_atual.month == 12:
                data_fim = data_atual.replace(year=data_atual.year + 1, month=1, day=1)
            else:
                data_fim = data_atual.replace(month=data_atual.month + 1, day=1)
        elif periodo_selecionado == "Mês Anterior":
            if data_atual.month == 1:
                data_inicio = data_atual.replace(year=data_atual.year - 1, month=12, day=1)
                data_fim = data_atual.replace(day=1)
            else:
                data_inicio = data_atual.replace(month=data_atual.month - 1, day=1)
                data_fim = data_atual.replace(day=1)
        elif periodo_selecionado == "Últimos 3 Meses":
            data_inicio = (data_atual - timedelta(days=90)).replace(day=1)
            data_fim = data_atual.replace(day=data_atual.day + 1)
        elif periodo_selecionado == "Ano Atual":
            data_inicio = data_atual.replace(month=1, day=1)
            data_fim = data_atual.replace(year=data_atual.year + 1, month=1, day=1)
        elif periodo_selecionado == "Personalizado":
            data_inicio = st.date_input("Data Inicial", value=data_atual.replace(day=1))
            data_fim = st.date_input("Data Final", value=data_atual)
            if data_inicio >= data_fim:
                st.warning("Data inicial deve ser anterior à data final")
                data_fim = data_inicio + timedelta(days=1)
        inicio_str = data_inicio.strftime("%Y-%m-%d") if data_inicio else None
        fim_str = data_fim.strftime("%Y-%m-%d") if data_fim else None
        st.markdown("---")
        st.subheader("🔍 Filtros")
        categorias_disponiveis = get_categories()
        categorias_selecionadas = st.multiselect(
            "Filtrar por Categorias",
            options=categorias_disponiveis,
            default=None,
            help="Selecione as categorias para incluir na análise"
        )
        tipo_transacao = st.multiselect(
            "Tipo de Transação",
            options=["Receita", "Despesa", "Investimento"],
            default=["Receita", "Despesa", "Investimento"],
            help="Selecione os tipos de transação para incluir na análise"
        )
        aplicar_filtros = st.button("Aplicar Filtros", type="primary")
    
    summary = None
    filtered_transactions = view_transactions()
    if aplicar_filtros:
        if inicio_str or fim_str:
            filtered_transactions = [
                t for t in filtered_transactions 
                if (inicio_str is None or t.get('date', '') >= inicio_str) and
                   (fim_str is None or t.get('date', '') <= fim_str)
            ]
        if categorias_selecionadas:
            filtered_transactions = [
                t for t in filtered_transactions 
                if t.get('category') in categorias_selecionadas
            ]
        if tipo_transacao:
            tipo_map = {
                "Receita": ["income", "receita", "revenue"],
                "Despesa": ["expense", "despesa", "expenses"],
                "Investimento": ["investment", "investimento"]
            }
            tipos_permitidos = []
            for t in tipo_transacao:
                if t in tipo_map:
                    tipos_permitidos.extend(tipo_map[t])
            filtered_transactions = [
                t for t in filtered_transactions 
                if str(t.get('type', '')).lower() in tipos_permitidos
            ]
        summary = calculate_summary(filtered_transactions)
        st.success(f"Filtros aplicados: {periodo_selecionado}")
    else:
        data_atual = datetime.now()
        inicio_padrao = data_atual.replace(day=1)
        if data_atual.month == 12:
            fim_padrao = data_atual.replace(year=data_atual.year + 1, month=1, day=1)
        else:
            fim_padrao = data_atual.replace(month=data_atual.month + 1, day=1)
        inicio_str = inicio_padrao.strftime("%Y-%m-%d")
        fim_str = fim_padrao.strftime("%Y-%m-%d")
        filtered_transactions = [
            t for t in filtered_transactions 
            if (t.get('date', '') >= inicio_str) and (t.get('date', '') < fim_str)
        ]
        summary = calculate_summary(filtered_transactions)
    
    print("Buscando transações para o dashboard...")
    transactions = view_transactions()
    print(f"Total de transações encontradas: {len(transactions)}")
    for t in transactions:
        print(f"ID: {t.get('id')} | Desc: {t.get('description')} | Tipo: {t.get('type')} | Status: {t.get('status')}")
    
    resumo_total = calculate_summary(transactions)
    print(f"Resumo total calculado: Receitas={resumo_total['receitas']}, Despesas={resumo_total['despesas']}, Investimentos={resumo_total['investimentos']}")
    
    balance = get_balance()
    theme_colors = get_theme_colors()
    
    st.subheader("📊 Visão Geral")
    if resumo_total["kpis"]["saude_financeira"] == "Crítica":
        st.error("⚠️ Atenção: Sua saúde financeira está em estado crítico! Despesas estão superando as receitas.")
    elif resumo_total["kpis"]["saude_financeira"] == "Atenção":
        st.warning("⚠️ Atenção: Sua situação financeira requer cuidado. Procure equilibrar receitas e despesas.")
    elif resumo_total["kpis"]["saude_financeira"] == "Ótima":
        st.success("✅ Parabéns! Sua saúde financeira está ótima. Continue no caminho certo!")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        with st.container():
            st.metric("Saldo em Conta", f"R$ {balance['saldo_conta']:,.2f}")
            with st.expander("Detalhes"):
                st.write("**Saldo em Conta**: Diferença entre receitas e despesas pagas (exceto investimentos)")
                st.write(f"**Atualizado em**: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    with col2:
        with st.container():
            st.metric("Total Investido", f"R$ {balance['total_investido']:,.2f}")
            with st.expander("Detalhes"):
                st.write("**Total Investido**: Soma de todas as transações classificadas como investimento")
                st.write(f"**Taxa de Poupança**: {resumo_total['kpis']['taxa_poupanca']:.1f}% da renda")
    with col3:
        with st.container():
            st.metric("Patrimônio Total", f"R$ {balance['patrimonio_total']:,.2f}")
            with st.expander("Detalhes"):
                st.write("**Patrimônio Total**: Saldo em conta + Total investido")
                st.write("Este valor representa sua situação financeira geral.")
    with col4:
        with st.container():
            saldo_mes = resumo_total['saldo_mes']
            st.metric("Saldo do Período", f"R$ {saldo_mes:,.2f}", delta=f"{'Positivo' if saldo_mes > 0 else 'Negativo'}",
                      delta_color="normal" if saldo_mes > 0 else "inverse")
            with st.expander("Detalhes"):
                st.write(f"**Receitas**: R$ {resumo_total['receitas']:,.2f}")
                st.write(f"**Despesas**: R$ {resumo_total['despesas']:,.2f}")
                st.write(f"**Relação Despesa/Receita**: {resumo_total['kpis']['relacao_despesa_receita']:.1f}%")
    
    st.subheader("💹 Indicadores Financeiros")
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
    with kpi_col1:
        with st.container():
            st.metric("Taxa de Poupança", f"{resumo_total['kpis']['taxa_poupanca']:.1f}%", help="Percentual da renda destinada a investimentos")
    with kpi_col2:
        with st.container():
            st.metric("Relação Despesa/Receita", f"{resumo_total['kpis']['relacao_despesa_receita']:.1f}%",
                      delta=f"{100 - resumo_total['kpis']['relacao_despesa_receita']:.1f}% livre" if resumo_total['kpis']['relacao_despesa_receita'] < 100 else f"{resumo_total['kpis']['relacao_despesa_receita'] - 100:.1f}% negativo",
                      delta_color="normal" if resumo_total['kpis']['relacao_despesa_receita'] < 100 else "inverse",
                      help="Percentual da renda comprometida com despesas")
    with kpi_col3:
        with st.container():
            st.metric("Saúde Financeira", resumo_total['kpis']['saude_financeira'], help="Avaliação geral da sua situação financeira")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Visão Geral", 
        "💰 Categorias", 
        "📊 Orçamento 50/30/20", 
        "📉 Tendências",
        "🎯 Metas"
    ])
    
    # Aba 1: Visão Geral
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Receitas vs Despesas")
            receitas = float(resumo_total['receitas'])
            despesas = float(resumo_total['despesas'])
            investimentos = float(resumo_total['investimentos'])
            categories = ['Receitas', 'Despesas', 'Investimentos']
            values = [receitas, despesas, investimentos]
            colors = [theme_colors['revenue_color'], theme_colors['expense_color'], theme_colors['investment_color']]
            
            # Implementação usando go.Figure para maior controle do layout (respeitando plot_bgcolor)
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=categories,
                y=values,
                marker_color=colors,
                text=[f"R$ {v:,.2f}" for v in values],
                textposition='outside'
            ))
            fig.update_layout(
                title="Visão Geral Financeira",
                yaxis=dict(title="Valor (R$)", range=[0, max(max(values) * 1.2, 10)]),
                xaxis=dict(title=""),
                showlegend=False
            )
            fig = apply_theme_to_plotly_chart(fig)
            st.plotly_chart(fig, use_container_width=True, key="receitas_despesas_chart")

        with col2:
            st.subheader("Distribuição de Gastos")
            todas_transacoes = view_transactions()
            categorias_valores = get_expense_distribution(transactions_data=todas_transacoes)
            if categorias_valores:
                df_categorias = pd.DataFrame([{"Categoria": k, "Valor": v} for k, v in categorias_valores.items()])
                fig_pizza = create_pie_chart(df_categorias, 'Categoria', title='Distribuição de Despesas por Categoria')
                st.plotly_chart(fig_pizza, use_container_width=True, key="distribuicao_gastos_chart")
            else:
                st.info("Sem dados de categorias de despesas para exibir")
                st.write("Tente selecionar um período diferente ou adicione transações do tipo 'Despesa'.")
        with st.expander("Exportar Dados"):
            dados_exportacao = {
                "Resumo Financeiro": pd.DataFrame({
                    "Métrica": ["Receitas", "Despesas", "Saldo", "Investimentos"],
                    "Valor": [summary['receitas'], summary['despesas'], summary['saldo_mes'], summary['investimentos']]
                })
            }
            if categorias_valores:
                dados_exportacao["Categorias"] = pd.DataFrame({
                    "Categoria": list(categorias_valores.keys()),
                    "Valor": list(categorias_valores.values())
                })
            if st.button("Exportar para CSV"):
                for nome, df in dados_exportacao.items():
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label=f"Download {nome}",
                        data=csv,
                        file_name=f"{nome.lower().replace(' ', '_')}.csv",
                        mime="text/csv"
                    )
    
    # Aba 2: Categorias
    with tab2:
        st.subheader("Análise de Categorias")
        todas_transacoes = view_transactions()
        categorias_valores = get_expense_distribution(transactions_data=todas_transacoes)

        if categorias_valores:
            df_categorias = pd.DataFrame([
                {"Categoria": k, "Valor": v}
                for k, v in categorias_valores.items()
            ])

            # Mostra a tabela
            st.dataframe(
                df_categorias,
                column_config={
                    "Categoria": st.column_config.TextColumn("Categoria"),
                    "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")
                },
                hide_index=True
            )

            st.subheader("Despesas por Categoria")

            # Cria o gráfico de barras
            fig = px.bar(
                df_categorias,
                x='Categoria',
                y='Valor',
                color='Categoria',
                color_discrete_sequence=px.colors.qualitative.Pastel,
                text_auto='.2f'
            )

            # Ajustes de layout
            fig.update_layout(
                xaxis_title="Categoria",
                yaxis_title="Valor (R$)",
                showlegend=False
            )

            # *** APLIQUE O TEMA AQUI ***
            fig = apply_theme_to_plotly_chart(fig)

            # Agora exiba o gráfico com o tema aplicado
            st.plotly_chart(fig, use_container_width=True)

            # Cálculo da distribuição percentual
            total = df_categorias['Valor'].sum()
            df_categorias['Percentual'] = df_categorias['Valor'] / total * 100

            st.subheader("Distribuição Percentual")
            st.dataframe(
                df_categorias,
                column_config={
                    "Categoria": st.column_config.TextColumn("Categoria"),
                    "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                    "Percentual": st.column_config.NumberColumn("Percentual", format="%.1f%%")
                },
                hide_index=True
            )
        else:
            st.info("Não há despesas registradas para o período selecionado.")


    
    # Aba 3: Orçamento 50/30/20
    with tab3:
        st.subheader("Orçamento 50/30/20")
        col1, col2 = st.columns(2)
        with col1:
            receita_total = resumo_total['receitas']
            if receita_total == 0:
                st.info("Exibindo dados de demonstração.")
                receita_total = 3000.0
            regra_ideal = {
                "Necessidades": receita_total * 0.5,
                "Desejos": receita_total * 0.3,
                "Investimentos": receita_total * 0.2
            }
            if 'regra_50_30_20' not in resumo_total or sum(resumo_total['regra_50_30_20'].values()) == 0:
                necessidades = 0
                desejos = 0
                investimentos = resumo_total['investimentos']
                for transaction in transactions:
                    tipo = str(transaction.get('type', '')).lower()
                    status = str(transaction.get('status', '')).lower()
                    if tipo in ['despesa', 'expense'] and status in ['pago', 'paid']:
                        valor = float(transaction.get('amount', 0))
                        categoria_tipo = str(transaction.get('categoria_tipo', '')).lower()
                        if categoria_tipo in ['necessidade', 'necessidades']:
                            necessidades += valor
                        elif categoria_tipo in ['desejo', 'desejos']:
                            desejos += valor
                if necessidades == 0 and desejos == 0 and investimentos == 0:
                    regra_real = {
                        "Necessidades": receita_total * 0.45,
                        "Desejos": receita_total * 0.35,
                        "Investimentos": receita_total * 0.20
                    }
                else:
                    regra_real = {"Necessidades": necessidades, "Desejos": desejos, "Investimentos": investimentos}
            else:
                regra_real = resumo_total['regra_50_30_20']
            st.markdown("### Comparação Ideal vs Real")
            data = {
                "Categoria": list(regra_ideal.keys()),
                "Ideal (R$)": [f"R$ {v:,.2f}" for v in regra_ideal.values()],
                "Real (R$)": [f"R$ {regra_real.get(k, 0):,.2f}" for k in regra_ideal.keys()],
                "% da Receita": [f"{(regra_real.get(k, 0) / receita_total * 100 if receita_total > 0 else 0):,.1f}%" for k in regra_ideal.keys()],
                "Diferença": [f"{(regra_real.get(k, 0) - v):,.2f}" for k, v in regra_ideal.items()]
            }
            df_comparacao = pd.DataFrame(data)
            st.dataframe(df_comparacao, use_container_width=True)
            with st.expander("Como funciona a regra 50/30/20?"):
                st.markdown("""
                A regra 50/30/20 é uma diretriz simples para orçamento pessoal:
                
                - **50%** da sua renda deve ser destinada a necessidades básicas (aluguel, alimentação, contas, etc.)
                - **30%** para gastos pessoais e desejos (lazer, assinaturas, compras não essenciais)
                - **20%** para poupança e investimentos (reserva de emergência, aposentadoria, etc.)
                
                Esta distribuição ajuda a manter um equilíbrio saudável em suas finanças.
                """)
        with col2:
            if receita_total > 0:
                fig = create_budget_comparison_chart(
                    [regra_real.get(k, 0) for k in regra_ideal.keys()],
                    list(regra_ideal.values()),
                    list(regra_ideal.keys())
                )
                st.plotly_chart(fig, use_container_width=True)
                st.subheader("Recomendações")
                for categoria, valor_ideal in regra_ideal.items():
                    valor_real = regra_real.get(categoria, 0)
                    diferenca = valor_real - valor_ideal
                    if abs(diferenca) < valor_ideal * 0.1:
                        st.success(f"✅ Seus gastos com {categoria} estão dentro do ideal")
                    elif diferenca > 0:
                        if categoria != "Investimentos":
                            st.warning(f"⚠️ Seus gastos com {categoria} estão R$ {diferenca:,.2f} acima do recomendado")
                        else:
                            st.success(f"✅ Ótimo! Você está investindo R$ {diferenca:,.2f} acima do recomendado")
                    else:
                        if categoria != "Investimentos":
                            st.info(f"ℹ️ Seus gastos com {categoria} estão R$ {abs(diferenca):,.2f} abaixo do recomendado")
                        else:
                            st.warning(f"⚠️ Você está investindo R$ {abs(diferenca):,.2f} abaixo do recomendado")
            else:
                st.info("Sem receitas neste período para analisar o orçamento ideal.")
    
    # Aba 4: Tendências
    with tab4:
        st.subheader("Análise de Tendências")
        dados_historicos = get_historical_data()
        if dados_historicos["Receitas"]:
            fig_tendencia = create_trend_chart("Tendência de Receitas e Despesas", dados_historicos)
            st.plotly_chart(fig_tendencia, use_container_width=True)
            
            metodo_projecao = st.selectbox(
                "Método de Projeção",
                options=["Média Móvel", "Tendência Linear"],
                index=0,
                help="Escolha o método para calcular as projeções futuras"
            )
            metodo = "media_movel" if metodo_projecao == "Média Móvel" else "tendencia"
            meses_projecao = st.slider("Meses para projeção", 1, 12, 3)
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Projeção de Receitas")
                projecoes_receitas = projetar_valores_futuros(dados_historicos["Receitas"], meses_futuros=meses_projecao, metodo=metodo)
                if projecoes_receitas:
                    fig_rec = create_trend_chart(
                        "Projeção de Receitas Futuras", 
                        {"Histórico": dados_historicos["Receitas"], "Projeção": projecoes_receitas}
                    )
                    st.plotly_chart(fig_rec, use_container_width=True)
            with col2:
                st.subheader("Projeção de Despesas")
                projecoes_despesas = projetar_valores_futuros(dados_historicos["Despesas"], meses_futuros=meses_projecao, metodo=metodo)
                if projecoes_despesas:
                    fig_desp = create_trend_chart(
                        "Projeção de Despesas Futuras",
                        {"Histórico": dados_historicos["Despesas"], "Projeção": projecoes_despesas}
                    )
                    st.plotly_chart(fig_desp, use_container_width=True)
            st.subheader("Previsão de Saúde Financeira")
            saldos_projetados = {}
            periodos_futuros = list(projecoes_receitas.keys())
            for periodo in periodos_futuros:
                receita_proj = projecoes_receitas.get(periodo, 0)
                despesa_proj = projecoes_despesas.get(periodo, 0)
                saldo_proj = receita_proj - despesa_proj
                saldos_projetados[periodo] = saldo_proj
            df_projecoes = pd.DataFrame({
                "Período": periodos_futuros,
                "Receita Projetada": [f"R$ {projecoes_receitas.get(p, 0):,.2f}" for p in periodos_futuros],
                "Despesa Projetada": [f"R$ {projecoes_despesas.get(p, 0):,.2f}" for p in periodos_futuros],
                "Saldo Projetado": [f"R$ {saldos_projetados.get(p, 0):,.2f}" for p in periodos_futuros]
            })
            st.dataframe(df_projecoes, use_container_width=True)
            fig_saldo = create_trend_chart(
                "Projeção de Saldo Futuro",
                {"Saldo Projetado": saldos_projetados}
            )
            st.plotly_chart(fig_saldo, use_container_width=True)
        else:
            st.info("Dados históricos insuficientes para análise de tendências")
    
    # Aba 5: Metas
    with tab5:
        st.subheader("🎯 Metas Financeiras")
        metas = view_goals()
        if metas:
            for meta in metas:
                meta_valor = float(meta.get('target_amount', 0))
                meta_atual = float(meta.get('current_amount', 0))
                meta_nome = meta.get('description', 'Meta sem nome')
                progresso = (meta_atual / meta_valor) * 100 if meta_valor > 0 else 0
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.progress(min(progresso / 100, 1.0), text=f"{meta_nome}: {progresso:.1f}%")
                with col2:
                    st.write(f"R$ {meta_atual:,.2f} / R$ {meta_valor:,.2f}")
            metas_df = pd.DataFrame([
                {
                    'Meta': meta.get('description', 'Meta sem nome'),
                    'Progresso (%)': 100 * float(meta.get('current_amount', 0)) / float(meta.get('target_amount', 0)),
                    'Valor Atual': float(meta.get('current_amount', 0)),
                    'Valor Objetivo': float(meta.get('target_amount', 0))
                }
                for meta in metas if float(meta.get('target_amount', 0)) > 0
            ])
            if not metas_df.empty:
                fig = go.Figure()
                for i, meta in metas_df.iterrows():
                    fig.add_trace(go.Bar(
                        name=meta["Meta"],
                        x=[meta["Meta"]],
                        y=[meta["Valor Atual"]],
                        marker_color=theme_colors['accent_color']
                    ))
                    fig.add_trace(go.Bar(
                        name=f"Faltando para {meta['Meta']}",
                        x=[meta["Meta"]],
                        y=[meta["Valor Objetivo"] - meta["Valor Atual"]],
                        marker_color='rgba(200, 200, 200, 0.5)'
                    ))
                fig = apply_theme_to_plotly_chart(fig)
                fig.update_layout(
                    title="Progresso das Metas",
                    barmode='stack'
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhuma meta financeira cadastrada.")
            st.markdown("""
            Para adicionar metas, acesse a página de Metas no menu lateral e defina seus objetivos financeiros.
            Suas metas aparecerão aqui para acompanhamento do progresso.
            """)

if __name__ == '__main__':
    show_dashboard()
