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
from categories import get_categories
from theme_manager import init_theme_manager, get_theme_colors, theme_config_section, apply_theme_to_plotly_chart
import calendar
import io
import base64
import numpy as np
from supabase_db import init_supabase
import random

def connect_to_database():
    """
    Estabelece conexão com o banco de dados.
    
    Returns:
        sqlite3.Connection ou supabase.Client: Conexão com o banco de dados.
    """
    try:
        # Retornar cliente do Supabase
        return init_supabase()
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        raise

def calculate_summary(transactions):
    """
    Calcula o resumo financeiro a partir das transações
    
    Args:
        transactions: Lista de transações a serem analisadas
        
    Returns:
        dict: Resumo financeiro contendo receitas, despesas, saldo e análises
    """
    if not transactions:
        # Retornar dados vazios quando não há transações
        return {
            "receitas": 0, 
            "despesas": 0, 
            "saldo_mes": 0, 
            "investimentos": 0, 
            "por_categoria": {}, 
            "regra_50_30_20": {
                "Necessidades": 0,
                "Desejos": 0,
                "Investimentos": 0
            }, 
            "kpis": {
                "saude_financeira": "Sem dados", 
                "taxa_poupanca": 0, 
                "relacao_despesa_receita": 0
            }
        }
    
    # Log para depuração - Verificar dados recebidos
    print(f"Analisando {len(transactions)} transações")
    tipos_unicos = set(str(t.get('type', '')).lower() for t in transactions)
    print(f"Tipos únicos encontrados: {tipos_unicos}")
    
    # Imprimir detalhes de cada transação para debug
    for t in transactions:
        print(f"ID: {t.get('id')} | Desc: {t.get('description')} | Tipo: {t.get('type')} | Status: {t.get('status')} | Valor: {t.get('amount')} | Categoria Tipo: {t.get('categoria_tipo')}")
    
    # Inicializar contadores
    receitas = 0
    despesas = 0
    investimentos = 0
    
    # Primeiro passo: Processar cada transação individualmente
    for transaction in transactions:
        try:
            # Converter todos os campos para formatos consistentes
            tipo = str(transaction.get('type', '')).lower()
            valor = float(transaction.get('amount', 0))
            categoria_tipo = str(transaction.get('categoria_tipo', '')).lower()
            status = str(transaction.get('status', '')).lower()
            
            # Verificar o status da transação - aceitar 'pago' ou 'paid'
            if status not in ['pago', 'paid']:
                print(f"Transação não considerada - status: {status}: {transaction.get('description')}")
                continue
                
            # Classificar a transação - verificar todas as variações possíveis
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
    
    # Calcular saldo
    saldo = receitas - despesas - investimentos
    
    # Agregação por categoria
    por_categoria = {}
    for transaction in transactions:
        try:
            tipo = str(transaction.get('type', '')).lower()
            if tipo not in ['despesa', 'expense', 'expenses']:
                continue
                
            # Verificar status da transação
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
            
            if categoria in por_categoria:
                por_categoria[categoria] += valor
            else:
                por_categoria[categoria] = valor
        except Exception as e:
            print(f"Erro ao processar categoria: {e}")
            continue
    
    # Calcular regra 50/30/20
    regra_50_30_20 = {
        "Necessidades": 0,
        "Desejos": 0,
        "Investimentos": investimentos
    }
    
    for transaction in transactions:
        try:
            tipo = str(transaction.get('type', '')).lower()
            if tipo not in ['despesa', 'expense', 'expenses']:
                continue
                
            # Verificar status da transação
            status = str(transaction.get('status', '')).lower()
            if status not in ['pago', 'paid']:
                continue
                
            categoria_tipo = str(transaction.get('categoria_tipo', '')).lower()
            valor = float(transaction.get('amount', 0))
            
            # Normalizar categoria_tipo para comparação
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
    
    # Calcular KPIs
    taxa_poupanca = (investimentos / receitas * 100) if receitas > 0 else 0
    relacao_despesa_receita = ((despesas + investimentos) / receitas * 100) if receitas > 0 else 0
    
    # Status de saúde financeira
    if saldo > 0 and taxa_poupanca >= 10:
        saude_financeira = "Ótima"
    elif saldo > 0:
        saude_financeira = "Boa"
    elif saldo == 0:
        saude_financeira = "Atenção"
    else:
        saude_financeira = "Crítica"
    
    # Log para depuração
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
    """
    Cria um gráfico de pizza a partir dos dados com compatibilidade de tema.
    
    Args:
        data: DataFrame com os dados
        column: Nome da coluna a ser usada para as fatias
        title: Título do gráfico
        
    Returns:
        Figura Plotly configurada com o tema adequado
    """
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
    """
    Cria um gráfico de barras a partir dos dados com compatibilidade de tema.
    
    Args:
        data: DataFrame com os dados
        x: Nome da coluna para o eixo X
        y: Nome da coluna para o eixo Y
        title: Título do gráfico
        
    Returns:
        Figura Plotly configurada com o tema adequado
    """
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
    """
    Cria um gráfico comparando orçamento real vs ideal com compatibilidade de tema.
    
    Args:
        actual: Lista com valores reais
        ideal: Lista com valores ideais
        labels: Lista com rótulos
        
    Returns:
        Figura Plotly configurada com o tema adequado
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

def create_trend_chart(titulo, dados_mensais, y_label="Valor (R$)"):
    """
    Cria um gráfico de linha mostrando a tendência ao longo do tempo.
    
    Args:
        titulo: Título do gráfico
        dados_mensais: Dicionário com séries temporais no formato {série: {período: valor}}
        y_label: Rótulo do eixo Y
        
    Returns:
        Figura Plotly configurada com o tema adequado
    """
    theme_colors = get_theme_colors()
    
    fig = go.Figure()
    
    # Adicionar linhas para cada série temporal
    for serie, valores in dados_mensais.items():
        cor = theme_colors['revenue_color'] if 'receita' in serie.lower() else theme_colors['expense_color']
        if 'investimento' in serie.lower():
            cor = theme_colors['investment_color']
            
        periodos = list(valores.keys())
        # Converter para formato legível (mês/ano)
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
    
    # Aplicar estilo do tema
    fig = apply_theme_to_plotly_chart(fig)
    fig.update_layout(
        title=titulo,
        xaxis_title="Período",
        yaxis_title=y_label
    )
    
    return fig

def projetar_valores_futuros(dados_historicos, meses_futuros=3, metodo="media_movel"):
    """
    Projeta valores futuros com base em métodos de previsão simples.
    
    Args:
        dados_historicos: Dicionário com histórico no formato {período: valor}
        meses_futuros: Quantidade de meses futuros para projetar
        metodo: Método de previsão ("media_movel" ou "tendencia")
        
    Returns:
        Dicionário com projeções no formato {período: valor}
    """
    if not dados_historicos or len(dados_historicos) < 2:
        return {}
    
    # Ordenar dados históricos por período
    periodos = sorted(list(dados_historicos.keys()))
    valores = [dados_historicos[p] for p in periodos]
    
    if metodo == "media_movel":
        # Média simples dos últimos 3 meses ou menos se não houver 3 meses
        n_meses = min(3, len(valores))
        media = sum(valores[-n_meses:]) / n_meses
        previsao = [media] * meses_futuros
    elif metodo == "tendencia":
        # Tendência linear simples
        if len(valores) >= 2:
            tendencia = (valores[-1] - valores[-2])
            # Limitar a tendência para evitar projeções extremas
            tendencia = max(min(tendencia, valores[-1] * 0.2), -valores[-1] * 0.2)
            previsao = [valores[-1] + tendencia * (i+1) for i in range(meses_futuros)]
        else:
            # Fallback para média se não houver dados suficientes
            previsao = [valores[-1]] * meses_futuros
    else:
        # Método padrão: último valor
        previsao = [valores[-1]] * meses_futuros
    
    # Gerar períodos futuros
    ultimo_periodo = periodos[-1]
    if '-' in ultimo_periodo:
        ano, mes = map(int, ultimo_periodo.split('-'))
        periodos_futuros = []
        for i in range(1, meses_futuros + 1):
            mes_futuro = mes + i
            ano_futuro = ano
            if mes_futuro > 12:
                ano_futuro += (mes_futuro - 1) // 12
                mes_futuro = ((mes_futuro - 1) % 12) + 1
            periodos_futuros.append(f"{ano_futuro}-{mes_futuro:02d}")
    else:
        # Formato alternativo de período
        periodos_futuros = [f"P{i+1}" for i in range(meses_futuros)]
    
    # Montar resultado
    projecoes = {}
    for i, periodo in enumerate(periodos_futuros):
        projecoes[periodo] = previsao[i]
    
    return projecoes

def get_monthly_summary(month=None, year=None, start_date=None, end_date=None, category_filter=None, transaction_types=None):
    """
    Obtém o resumo mensal de transações.
    
    Args:
        month (int, opcional): Mês específico para filtrar.
        year (int, opcional): Ano específico para filtrar.
        start_date (str, opcional): Data inicial para filtro personalizado.
        end_date (str, opcional): Data final para filtro personalizado.
        category_filter (list, opcional): Lista de categorias para filtrar.
        transaction_types (list, opcional): Lista de tipos de transação para filtrar.
        
    Returns:
        dict: Resumo financeiro do período.
    """
    try:
        # Obter todas as transações
        transactions = view_transactions()
        
        if not transactions:
            st.warning("Nenhuma transação encontrada no banco de dados.")
            return {"receitas": 0, "despesas": 0, "saldo_mes": 0, "investimentos": 0, "por_categoria": {}, "regra_50_30_20": {}, "kpis": {"saude_financeira": "Sem dados", "taxa_poupanca": 0, "relacao_despesa_receita": 0}}
            
        # Filtrar por data
        filtered_transactions = []
        
        for transaction in transactions:
            # Extrair data da transação ou usar data atual
            date_str = transaction.get('date', None)
            if not date_str:
                continue
                
            try:
                transaction_date = datetime.strptime(date_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                # Se falhar, tentar outros formatos comuns
                try:
                    transaction_date = datetime.strptime(date_str, "%d/%m/%Y")
                except (ValueError, TypeError):
                    # Se ainda falhar, pular esta transação
                    continue
            
            # Aplicar filtro de data
            if start_date and end_date:
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")
                if not (start <= transaction_date <= end):
                    continue
            elif month and year:
                if not (transaction_date.month == month and transaction_date.year == year):
                    continue
            else:
                # Se nenhum filtro for fornecido, usar mês atual
                current_date = datetime.now()
                if not (transaction_date.month == current_date.month and transaction_date.year == current_date.year):
                    continue
        
        # Apply category filter
        if category_filter and len(category_filter) > 0:
            filtered_transactions = [t for t in transactions if t.get('category') in category_filter]
        
        # Apply transaction type filter - case insensitive
        if transaction_types and len(transaction_types) > 0:
            filtered_by_type = []
            for transaction in filtered_transactions:
                transaction_type = transaction.get('type', '').lower()
                type_matches = False
                
                for t_type in transaction_types:
                    # Check both Portuguese and English versions
                    if (t_type.lower() == transaction_type or 
                        (t_type.lower() == 'receita' and transaction_type in ['receita', 'income']) or
                        (t_type.lower() == 'despesa' and transaction_type in ['despesa', 'expense']) or
                        (t_type.lower() == 'investimento' and transaction_type in ['investimento', 'investment'])):
                        type_matches = True
                        break
                        
                if type_matches:
                    filtered_by_type.append(transaction)
            
            filtered_transactions = filtered_by_type
        
        # Debug para mostrar os tipos de transações encontrados
        print(f"Após filtragem, restaram {len(filtered_transactions)} transações")
        tipos_encontrados = set(t.get('type', '').lower() for t in filtered_transactions)
        print(f"Tipos encontrados após filtragem: {tipos_encontrados}")
        
        # Calculate summary from filtered transactions
        summary = calculate_summary(filtered_transactions)
        
        # Debug para ver os valores calculados
        print(f"DEBUG - Resumo calculado: Receitas={summary['receitas']}, Despesas={summary['despesas']}, Investimentos={summary['investimentos']}")
        
        return summary
    
    except Exception as e:
        st.error(f"Erro ao obter resumo mensal: {e}")
        import traceback
        st.error(traceback.format_exc())
        return {"receitas": 0, "despesas": 0, "saldo_mes": 0, "investimentos": 0, "por_categoria": {}, "regra_50_30_20": {}, "kpis": {"saude_financeira": "Sem dados", "taxa_poupanca": 0, "relacao_despesa_receita": 0}}

def get_historical_data(n_meses=6):
    """
    Obtém dados históricos dos últimos n meses
    
    Args:
        n_meses: Número de meses no histórico
        
    Returns:
        dict: Dados históricos organizados para análise de tendências
    """
    try:
        dados_historicos = {"Receitas": {}, "Despesas": {}, "Investimentos": {}, "Saldo": {}}
        
        date_atual = datetime.now()
        
        for i in range(n_meses-1, -1, -1):
            # Calcular mês e ano
            data_ref = date_atual.replace(day=1) - relativedelta(months=i)
            mes = data_ref.month
            ano = data_ref.year
            
            # Chave para o período
            periodo = f"{ano}-{mes:02d}"
            
            # Obter resumo do mês
            resumo = get_monthly_summary(month=mes, year=ano)
            
            # Armazenar dados
            dados_historicos["Receitas"][periodo] = resumo["receitas"]
            dados_historicos["Despesas"][periodo] = resumo["despesas"]
            dados_historicos["Investimentos"][periodo] = resumo["investimentos"]
            dados_historicos["Saldo"][periodo] = resumo["saldo_mes"]
        
        return dados_historicos
    except Exception as e:
        st.error(f"Erro ao obter dados históricos: {e}")
        return {"Receitas": {}, "Despesas": {}, "Investimentos": {}, "Saldo": {}}

def get_balance():
    """
    Calcula o saldo atual
    
    Returns:
        dict: Informações de saldo, investimentos e patrimônio total
    """
    try:
        # Obter todas as transações e processar em memória
        # (mais flexível com diferentes formatos de dados)
        transactions = view_transactions()
        
        # Inicializar valores
        saldo_conta = 0
        total_investido = 0
        
        # Processar cada transação
        for transaction in transactions:
            # Verificar se a transação está paga
            status = str(transaction.get('status', '')).lower()
            if status not in ['pago', 'paid']:
                continue
                
            # Obter o tipo e valor da transação
            tipo = str(transaction.get('type', '')).lower()
            valor = float(transaction.get('amount', 0))
            categoria_tipo = str(transaction.get('categoria_tipo', '')).lower()
            
            # Calcular saldo em conta
            if tipo in ['receita', 'income', 'revenue']:
                saldo_conta += valor
            elif tipo in ['despesa', 'expense', 'expenses']:
                saldo_conta -= valor
            elif tipo in ['investimento', 'investment']:
                saldo_conta -= valor
                total_investido += valor
            
            # Não precisamos mais desta lógica que mistura os tipos de transações
            # if tipo in ['investimento', 'investment'] or categoria_tipo == 'investimento':
            #     total_investido += valor
        
        # Calcular patrimônio total
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
        dict: Dicionário com {categoria: valor} para cada categoria de despesa.
    """
    try:
        # Obter todas as transações diretamente do Supabase
        from transactions_db import view_transactions
        
        print("Buscando transações para distribuição de despesas...")
        
        # Se não recebemos transações, buscar todas do banco
        if transactions_data is None:
            from supabase_db import init_supabase
            supabase = init_supabase()
            if not supabase:
                print("Erro ao conectar ao Supabase")
                return {}
                
            # Buscar TODAS as transações diretamente do Supabase
            response = supabase.table("transactions").select("*").execute()
            transactions = response.data
            print(f"Buscando diretamente do Supabase: {len(transactions)} transações encontradas")
        else:
            transactions = transactions_data
            print(f"Usando transações fornecidas: {len(transactions)} transações")
        
        # Filtrar apenas despesas
        despesas = {}
        
        # Variável para contar despesas encontradas
        despesas_encontradas = 0
        
        print(f"Processando {len(transactions)} transações para análise de categorias")
        
        # Processar cada transação
        for transaction in transactions:
            # Verificar se é uma despesa
            tipo = str(transaction.get('type', '')).lower()
            
            # Debug para identificar o tipo e categoria
            categoria_tipo = str(transaction.get('categoria_tipo', '')).lower()
            status = str(transaction.get('status', '')).lower()
            
            print(f"Analisando: {transaction.get('description')}, Tipo: {tipo}, Categoria: {categoria_tipo}, Status: {status}, Valor: {transaction.get('amount')}")
            
            if tipo not in ['despesa', 'expense', 'expenses']:
                print(f"Ignorando (não é despesa): {transaction.get('description')} - Tipo: {tipo}")
                continue
            
            # Incluir todas as despesas, independente do status (pago ou pendente)
            # Usar categoria_tipo como categoria principal
            categoria = categoria_tipo if categoria_tipo else 'Outros'
            if categoria in ['necessidade', 'necessidades']:
                categoria = 'Necessidades'
            elif categoria in ['desejo', 'desejos']:
                categoria = 'Lazer'
            elif categoria == 'investimento':
                categoria = 'Investimentos'
            else:
                categoria = 'Outros'
                
            # Aplicar filtro de categoria se necessário
            if category_filter and categoria not in category_filter:
                print(f"Ignorando (filtro de categoria): {transaction.get('description')}")
                continue
                
            # Adicionar ao dicionário de despesas
            valor = float(transaction.get('amount', 0))
            if categoria in despesas:
                despesas[categoria] += valor
                print(f"Adicionando à categoria {categoria}: +R${valor:.2f} = R${despesas[categoria]:.2f}")
            else:
                despesas[categoria] = valor
                print(f"Nova categoria {categoria}: R${valor:.2f}")
            
            despesas_encontradas += 1
        
        print(f"Total de despesas encontradas: {despesas_encontradas}")
        print(f"Distribuição de despesas final: {despesas}")
        
        # Ordenar categorias por valor
        return dict(sorted(despesas.items(), key=lambda x: x[1], reverse=True)) if despesas else {}
    except Exception as e:
        print(f"ERRO na distribuição de despesas: {e}")
        st.error(f"Erro ao obter distribuição de despesas: {e}")
        import traceback
        print(traceback.format_exc())
        
        # Retornar vazio em caso de erro
        return {}

def get_historical_data(months=12):
    """
    Obtém dados históricos de receitas e despesas para análise de tendências.
    
    Args:
        months (int): Número de meses para obter dados históricos.
        
    Returns:
        dict: Dicionário com chaves 'Receitas', 'Despesas' e 'Investimentos', cada uma
              contendo um dicionário de {período: valor}.
    """
    try:
        # Importar para evitar importação circular
        from transactions_db import view_transactions
        
        # Obter todas as transações
        transactions = view_transactions()
        
        # Calcular data inicial com base no número de meses
        hoje = datetime.now()
        data_inicial = hoje.replace(day=1) - timedelta(days=30 * months)
        data_inicial_str = data_inicial.strftime("%Y-%m-%d")
        
        # Estruturas para armazenar os resultados
        receitas_por_mes = {}
        despesas_por_mes = {}
        investimentos_por_mes = {}
        saldo_por_mes = {}
        
        # Processar cada transação
        for transaction in transactions:
            # Obter data e converter para objeto datetime
            data_str = transaction.get('date')
            if not data_str:
                continue
                
            try:
                data = datetime.strptime(data_str, "%Y-%m-%d")
                periodo = data.strftime("%Y-%m")
                
                # Verificar se está dentro do período de interesse
                if data < data_inicial:
                    continue
                    
                # Obter valores
                tipo = str(transaction.get('type', '')).lower()
                valor = float(transaction.get('amount', 0))
                status = str(transaction.get('status', '')).lower()
                
                # Se não estiver pago, não considerar
                if status not in ['pago', 'paid']:
                    continue
                    
                # Classificar por tipo usando as mesmas variações de tipos
                if tipo in ['receita', 'income', 'revenue']:
                    receitas_por_mes[periodo] = receitas_por_mes.get(periodo, 0) + valor
                    
                    # Atualizar saldo
                    saldo_por_mes[periodo] = saldo_por_mes.get(periodo, 0) + valor
                    
                elif tipo in ['despesa', 'expense', 'expenses']:
                    despesas_por_mes[periodo] = despesas_por_mes.get(periodo, 0) + valor
                    
                    # Atualizar saldo (negativo para despesas)
                    saldo_por_mes[periodo] = saldo_por_mes.get(periodo, 0) - valor
                    
                elif tipo in ['investimento', 'investment']:
                    investimentos_por_mes[periodo] = investimentos_por_mes.get(periodo, 0) + valor
                    
                    # Atualizar saldo (negativo para investimentos)
                    saldo_por_mes[periodo] = saldo_por_mes.get(periodo, 0) - valor
            except Exception as e:
                print(f"Erro ao processar data da transação: {e}")
                continue
        
        # Garantir que todos os períodos estejam presentes
        todos_os_periodos = set(receitas_por_mes.keys()) | set(despesas_por_mes.keys()) | set(investimentos_por_mes.keys())
        
        for periodo in todos_os_periodos:
            if periodo not in receitas_por_mes:
                receitas_por_mes[periodo] = 0
            if periodo not in despesas_por_mes:
                despesas_por_mes[periodo] = 0
            if periodo not in investimentos_por_mes:
                investimentos_por_mes[periodo] = 0
            if periodo not in saldo_por_mes:
                saldo_por_mes[periodo] = 0
        
        # Ordenar os dicionários por período
        receitas_ordenadas = {k: receitas_por_mes[k] for k in sorted(receitas_por_mes.keys())}
        despesas_ordenadas = {k: despesas_por_mes[k] for k in sorted(despesas_por_mes.keys())}
        investimentos_ordenados = {k: investimentos_por_mes[k] for k in sorted(investimentos_por_mes.keys())}
        saldo_ordenado = {k: saldo_por_mes[k] for k in sorted(saldo_por_mes.keys())}
        
        dados = {
            "Receitas": receitas_ordenadas,
            "Despesas": despesas_ordenadas,
            "Investimentos": investimentos_ordenados,
            "Saldo": saldo_ordenado
        }
        
        return dados
    except Exception as e:
        st.error(f"Erro ao obter dados históricos: {e}")
        return {"Receitas": {}, "Despesas": {}, "Investimentos": {}, "Saldo": {}}

def get_categories():
    """
    Obtém todas as categorias disponíveis para filtros.
    
    Returns:
        list: Lista de categorias disponíveis.
    """
    # Importar para evitar importação circular
    from categories import get_categories as get_all_categories
    
    # Usar a função de categories.py que já está adaptada para Supabase
    all_categories = get_all_categories()
    
    # Extrair apenas os nomes das categorias
    category_names = [cat.get("name", "") for cat in all_categories if cat.get("name")]
    
    return sorted(category_names)

def view_goals():
    """
    Recupera as metas financeiras do usuário, utilizando a função do módulo transactions_db.
    
    Returns:
        list: Lista de metas com estrutura (id, tipo, nome, valor_objetivo, valor_atual).
    """
    return get_goals()

def get_monthly_summary(month=None, year=None, start_date=None, end_date=None, category_filter=None, transaction_types=None):
    """
    Obtém o resumo mensal de transações.
    
    Args:
        month (int, opcional): Mês específico para filtrar.
        year (int, opcional): Ano específico para filtrar.
        start_date (str, opcional): Data inicial para filtro personalizado.
        end_date (str, opcional): Data final para filtro personalizado.
        category_filter (list, opcional): Lista de categorias para filtrar.
        transaction_types (list, opcional): Lista de tipos de transação para filtrar.
        
    Returns:
        dict: Resumo financeiro do período.
    """
    # Option 1: Get all transactions and filter manually (more reliable)
    transactions = view_transactions()
    
    # Apply date filtering
    filtered_transactions = []
    
    for transaction in transactions:
        # Extrair data da transação ou usar data atual
        date_str = transaction.get('date')
        if not date_str:
            continue
            
        # Convert to datetime for comparison
        try:
            transaction_date = datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            # Se falhar, tentar outros formatos comuns
            try:
                transaction_date = datetime.strptime(date_str, "%d/%m/%Y")
            except (ValueError, TypeError):
                # Se ainda falhar, pular esta transação
                continue
            
        # Apply date filters
        if start_date and end_date:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            if not (start <= transaction_date <= end):
                continue
        elif month and year:
            if not (transaction_date.month == month and transaction_date.year == year):
                continue
        else:
            # Default to current month
            today = datetime.now()
            if not (transaction_date.month == today.month and transaction_date.year == today.year):
                continue
                
        # Se passou por todos os filtros de data, adiciona à lista filtrada    
        filtered_transactions.append(transaction)
    
    # Apply category filter
    if category_filter and len(category_filter) > 0:
        filtered_transactions = [t for t in transactions if t.get('category') in category_filter]
    
    # Apply transaction type filter - case insensitive
    if transaction_types and len(transaction_types) > 0:
        filtered_by_type = []
        for transaction in filtered_transactions:
            transaction_type = transaction.get('type', '').lower()
            type_matches = False
            
            for t_type in transaction_types:
                # Check both Portuguese and English versions
                if (t_type.lower() == transaction_type or 
                    (t_type.lower() == 'receita' and transaction_type in ['receita', 'income']) or
                    (t_type.lower() == 'despesa' and transaction_type in ['despesa', 'expense']) or
                    (t_type.lower() == 'investimento' and transaction_type in ['investimento', 'investment'])):
                    type_matches = True
                    break
                    
            if type_matches:
                filtered_by_type.append(transaction)
        
        filtered_transactions = filtered_by_type
        
    # Debug para mostrar os tipos de transações encontrados
    print(f"Após filtragem, restaram {len(filtered_transactions)} transações")
    tipos_encontrados = set(t.get('type', '').lower() for t in filtered_transactions)
    print(f"Tipos encontrados após filtragem: {tipos_encontrados}")
    
    # Calculate summary from filtered transactions
    summary = calculate_summary(filtered_transactions)
    return summary

def show_dashboard():
    """
    Mostra o dashboard financeiro completo
    """
    # Inicializar o gerenciador de tema
    init_theme_manager()
    
    # Configurar o tema para todos os componentes
    theme_colors = get_theme_colors()
    
    # Mostrar configuração de tema
    theme_config_section()
    
    # Título principal do dashboard
    col_title, col_refresh = st.columns([5, 1])
    with col_title:
        st.title("Dashboard Financeiro")
    with col_refresh:
        # Botão estilizado adaptativo ao tema
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
            # Limpar todos os caches para forçar recarregamento dos dados
            st.cache_data.clear()
            st.rerun()
    
    # Sidebar para filtros e seleções
    with st.sidebar:
        st.subheader("📆 Período de Análise")
        
        # Opções de período
        periodo_opcoes = ["Mês Atual", "Mês Anterior", "Últimos 3 Meses", "Ano Atual", "Personalizado"]
        periodo_selecionado = st.selectbox("Selecione o período", periodo_opcoes)
        
        # Variáveis para armazenar datas de início e fim
        data_inicio = None
        data_fim = None
        
        # Definir período com base na seleção
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
        
        # Formatar datas para consulta
        inicio_str = data_inicio.strftime("%Y-%m-%d") if data_inicio else None
        fim_str = data_fim.strftime("%Y-%m-%d") if data_fim else None
        
        # Separador para filtros adicionais
        st.markdown("---")
        st.subheader("🔍 Filtros")
        
        # Obter categorias disponíveis
        categorias_disponiveis = get_categories()
        
        # Filtro de categorias
        categorias_selecionadas = st.multiselect(
            "Filtrar por Categorias",
            options=categorias_disponiveis,
            default=None,
            help="Selecione as categorias para incluir na análise"
        )
        
        # Filtro de tipo de transação
        tipo_transacao = st.multiselect(
            "Tipo de Transação",
            options=["Receita", "Despesa", "Investimento"],
            default=["Receita", "Despesa", "Investimento"],
            help="Selecione os tipos de transação para incluir na análise"
        )
        
        # Botão para aplicar filtros
        aplicar_filtros = st.button("Aplicar Filtros", type="primary")
    
    # Obter dados do período selecionado
    summary = None
    # Variável para armazenar as transações filtradas
    filtered_transactions = view_transactions() 
    
    if aplicar_filtros:
        # Filtrar transações com base nos parâmetros selecionados
        if inicio_str or fim_str:
            filtered_transactions = [
                t for t in filtered_transactions 
                if (inicio_str is None or t.get('date', '') >= inicio_str) and
                   (fim_str is None or t.get('date', '') <= fim_str)
            ]
        
        # Aplicar filtros de categoria
        if categorias_selecionadas:
            filtered_transactions = [
                t for t in filtered_transactions 
                if t.get('category') in categorias_selecionadas
            ]
            
        # Aplicar filtros de tipo de transação
        if tipo_transacao:
            # Mapear nomes em português para inglês
            tipo_map = {
                "Receita": ["income", "receita", "revenue"],
                "Despesa": ["expense", "despesa", "expenses"],
                "Investimento": ["investment", "investimento"]
            }
            # Criar lista de tipos permitidos (considerando variações em inglês/português)
            tipos_permitidos = []
            for t in tipo_transacao:
                if t in tipo_map:
                    tipos_permitidos.extend(tipo_map[t])
            
            # Filtrar transações pelos tipos permitidos
            filtered_transactions = [
                t for t in filtered_transactions 
                if str(t.get('type', '')).lower() in tipos_permitidos
            ]
        
        # Calcular resumo com as transações filtradas
        summary = calculate_summary(filtered_transactions)
        st.success(f"Filtros aplicados: {periodo_selecionado}")
    else:
        # Obter dados do mês atual (padrão)
        # Filtrar para o mês atual
        data_atual = datetime.now()
        inicio_padrao = data_atual.replace(day=1)
        if data_atual.month == 12:
            fim_padrao = data_atual.replace(year=data_atual.year + 1, month=1, day=1)
        else:
            fim_padrao = data_atual.replace(month=data_atual.month + 1, day=1)
            
        inicio_str = inicio_padrao.strftime("%Y-%m-%d")
        fim_str = fim_padrao.strftime("%Y-%m-%d")
        
        # Aplicar o filtro de data padrão
        filtered_transactions = [
            t for t in filtered_transactions 
            if (t.get('date', '') >= inicio_str) and (t.get('date', '') < fim_str)
        ]
        
        # Calcular resumo com as transações filtradas
        summary = calculate_summary(filtered_transactions)
    
    # Obtém lista de todas as transações
    print("Buscando transações para o dashboard...")
    transactions = view_transactions()
    print(f"Total de transações encontradas: {len(transactions)}")
    for t in transactions:
        print(f"ID: {t.get('id')} | Desc: {t.get('description')} | Tipo: {t.get('type')} | Status: {t.get('status')}")
    
    # Calcular o resumo total diretamente aqui para evitar problemas de filtragem
    resumo_total = calculate_summary(transactions)
    print(f"Resumo total calculado: Receitas={resumo_total['receitas']}, Despesas={resumo_total['despesas']}, Investimentos={resumo_total['investimentos']}")
    
    # Obter saldo global
    balance = get_balance()
    
    # Obter cores do tema
    theme_colors = get_theme_colors()
    
    # Seção de KPIs e métricas principais
    st.subheader("📊 Visão Geral")
    
    # Exibir alertas importantes com base nos KPIs
    if resumo_total["kpis"]["saude_financeira"] == "Crítica":
        st.error("⚠️ Atenção: Sua saúde financeira está em estado crítico! Despesas estão superando as receitas.")
    elif resumo_total["kpis"]["saude_financeira"] == "Atenção":
        st.warning("⚠️ Atenção: Sua situação financeira requer cuidado. Procure equilibrar receitas e despesas.")
    elif resumo_total["kpis"]["saude_financeira"] == "Ótima":
        st.success("✅ Parabéns! Sua saúde financeira está ótima. Continue no caminho certo!")
    
    # Cards de métricas em expansores interativos
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        with st.container(border=True):
            st.metric("Saldo em Conta", f"R$ {balance['saldo_conta']:,.2f}")
            with st.expander("Detalhes"):
                st.write("**Saldo em Conta**: Diferença entre receitas e despesas pagas (exceto investimentos)")
                st.write(f"**Atualizado em**: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    with col2:
        with st.container(border=True):
            st.metric("Total Investido", f"R$ {balance['total_investido']:,.2f}")
            with st.expander("Detalhes"):
                st.write("**Total Investido**: Soma de todas as transações classificadas como investimento")
                st.write(f"**Taxa de Poupança**: {resumo_total['kpis']['taxa_poupanca']:.1f}% da renda")
    
    with col3:
        with st.container(border=True):
            st.metric("Patrimônio Total", f"R$ {balance['patrimonio_total']:,.2f}")
            with st.expander("Detalhes"):
                st.write("**Patrimônio Total**: Saldo em conta + Total investido")
                st.write("Este valor representa sua situação financeira geral.")
    
    with col4:
        with st.container(border=True):
            saldo_mes = resumo_total['saldo_mes']
            st.metric(
                "Saldo do Período", 
                f"R$ {saldo_mes:,.2f}", 
                delta=f"{'Positivo' if saldo_mes > 0 else 'Negativo'}",
                delta_color="normal" if saldo_mes > 0 else "inverse"
            )
            with st.expander("Detalhes"):
                st.write(f"**Receitas**: R$ {resumo_total['receitas']:,.2f}")
                st.write(f"**Despesas**: R$ {resumo_total['despesas']:,.2f}")
                st.write(f"**Relação Despesa/Receita**: {resumo_total['kpis']['relacao_despesa_receita']:.1f}%")
    
    # Indicadores Financeiros
    st.subheader("💹 Indicadores Financeiros")
    
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
    
    with kpi_col1:
        with st.container(border=True):
            st.metric(
                "Taxa de Poupança", 
                f"{resumo_total['kpis']['taxa_poupanca']:.1f}%",
                help="Percentual da renda destinada a investimentos"
            )
    
    with kpi_col2:
        with st.container(border=True):
            st.metric(
                "Relação Despesa/Receita", 
                f"{resumo_total['kpis']['relacao_despesa_receita']:.1f}%",
                delta=f"{100 - resumo_total['kpis']['relacao_despesa_receita']:.1f}% livre" if resumo_total['kpis']['relacao_despesa_receita'] < 100 else f"{resumo_total['kpis']['relacao_despesa_receita'] - 100:.1f}% negativo",
                delta_color="normal" if resumo_total['kpis']['relacao_despesa_receita'] < 100 else "inverse",
                help="Percentual da renda comprometida com despesas"
            )
    
    with kpi_col3:
        with st.container(border=True):
            st.metric(
                "Saúde Financeira", 
                resumo_total['kpis']['saude_financeira'],
                help="Avaliação geral da sua situação financeira"
            )
    
    # Organizar o restante do dashboard em abas
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
            
            # Usar o resumo_total calculado diretamente de todas as transações
            # Isso garantirá que os dados sejam exibidos mesmo que haja problemas nos filtros
            receitas = float(resumo_total['receitas'])
            despesas = float(resumo_total['despesas'])
            investimentos = float(resumo_total['investimentos'])
            
            # Criar gráfico com dados simplificados para melhor visualização
            categories = ['Receitas', 'Despesas', 'Investimentos']
            values = [receitas, despesas, investimentos]
            colors = [theme_colors['revenue_color'], theme_colors['expense_color'], theme_colors['investment_color']]
            
            # Criar dataframe para facilitar a visualização
            df_chart = pd.DataFrame({
                'Categoria': categories,
                'Valor': values
            })
            
            # Plotar com Plotly Express (mais simples e robusto)
            fig = px.bar(
                df_chart, 
                x='Categoria', 
                y='Valor',
                title="Visão Geral Financeira",
                color='Categoria',
                color_discrete_sequence=colors,
                text_auto='.2f'
            )
            
            # Ajustar layout para melhor visualização
            fig.update_layout(
                showlegend=False,
                yaxis=dict(
                    title="Valor (R$)",
                    range=[0, max(max(values) * 1.2, 10)]
                ),
                xaxis=dict(title=""),
                hovermode="x unified"
            )
            
            # Ajustar formato de texto dos valores
            fig.update_traces(texttemplate='R$%{y:.2f}', textposition='outside')
            
            # Aplicar tema ao gráfico
            fig = apply_theme_to_plotly_chart(fig)
            st.plotly_chart(fig, use_container_width=True, key="receitas_despesas_chart")
        
        with col2:
            st.subheader("Distribuição de Gastos")
            # Criar gráfico de pizza para categorias de despesas
            # Buscar todas as transações para garantir que todas as despesas sejam incluídas
            todas_transacoes = view_transactions()
            categorias_valores = get_expense_distribution(transactions_data=todas_transacoes)
            
            if categorias_valores:
                # Criar DataFrame para visualização
                df_categorias = pd.DataFrame([
                    {"Categoria": k, "Valor": v}
                    for k, v in categorias_valores.items()
                ])
                
                # Usar o Plotly Express para criar o gráfico de pizza
                fig_pizza = px.pie(
                    df_categorias,
                    names='Categoria',
                    values='Valor',
                    title='Distribuição de Despesas por Categoria',
                    color_discrete_sequence=px.colors.qualitative.Set3,  # Paleta de cores mais vibrante
                    hole=0.4  # Criar um gráfico de donut para melhor visualização
                )
                
                # Aplicar tema ao gráfico
                fig_pizza = apply_theme_to_plotly_chart(fig_pizza)
                
                # Configurar textos e layout
                fig_pizza.update_traces(
                    textposition='inside',
                    textinfo='percent+label',
                    hovertemplate='<b>%{label}</b><br>R$ %{value:.2f}<br>%{percent}'
                )
                
                fig_pizza.update_layout(
                    legend_title_text='Categorias',
                    margin=dict(t=50, b=20, l=20, r=20)
                )
                
                st.plotly_chart(fig_pizza, use_container_width=True, key="distribuicao_gastos_chart")
            else:
                st.info("Sem dados de categorias de despesas para exibir")
                st.write("Tente selecionar um período diferente ou adicione transações do tipo 'Despesa'.")
        
        # Opções de exportação
        with st.expander("Exportar Dados"):
            # Preparar dados para exportação
            dados_exportacao = {
                "Resumo Financeiro": pd.DataFrame({
                    "Métrica": ["Receitas", "Despesas", "Saldo", "Investimentos"],
                    "Valor": [
                        summary['receitas'],
                        summary['despesas'],
                        summary['saldo_mes'],
                        summary['investimentos']
                    ]
                })
            }
            
            if categorias_valores:
                dados_exportacao["Categorias"] = pd.DataFrame({
                    "Categoria": list(categorias_valores.keys()),
                    "Valor": list(categorias_valores.values())
                })
            
            # Botão para exportar em CSV
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
        
        # Obter todas as transações para análise de categorias
        todas_transacoes = view_transactions()
        categorias_valores = get_expense_distribution(transactions_data=todas_transacoes)
        
        if categorias_valores:
            # Criar dataframe para visualização em tabela
            df_categorias = pd.DataFrame([
                {"Categoria": k, "Valor": v}
                for k, v in categorias_valores.items()
            ])
            
            # Mostrar tabela de categorias
            st.dataframe(
                df_categorias,
                column_config={
                    "Categoria": st.column_config.TextColumn("Categoria"),
                    "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")
                },
                hide_index=True
            )
            
            # Gráfico de barras para despesas por categoria
            st.subheader("Despesas por Categoria")
            
            # Usar Plotly para um gráfico mais interativo
            fig = px.bar(
                df_categorias, 
                x='Categoria', 
                y='Valor',
                color='Categoria',
                color_discrete_sequence=px.colors.qualitative.Pastel,
                text_auto='.2f'
            )
            
            # Configurar layout
            fig.update_layout(
                xaxis_title="Categoria",
                yaxis_title="Valor (R$)",
                showlegend=False
            )
            
            # Mostrar o gráfico
            st.plotly_chart(fig, use_container_width=True)
            
            # Calcular distribuição percentual
            total = df_categorias['Valor'].sum()
            df_categorias['Percentual'] = df_categorias['Valor'] / total * 100
            
            # Mostrar distribuição percentual
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
            # Usando resumo_total em vez de summary para manter consistência com os indicadores
            receita_total = resumo_total['receitas']
            
            # Verificar se temos dados para exibir
            if receita_total == 0:
                st.info("Exibindo dados de demonstração.")
                # Usar valores fictícios para demonstração
                receita_total = 3000.0
            
            regra_ideal = {
                "Necessidades": receita_total * 0.5,
                "Desejos": receita_total * 0.3,
                "Investimentos": receita_total * 0.2
            }
            
            # Valores reais - se não tiver dados, usar valores fictícios
            if 'regra_50_30_20' not in resumo_total or sum(resumo_total['regra_50_30_20'].values()) == 0:
                # Calcular valores da regra 50/30/20 baseados nos dados atuais
                necessidades = 0
                desejos = 0
                investimentos = resumo_total['investimentos']
                
                # Para cada transação do tipo despesa, classificar por categoria_tipo
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
                
                # Se ainda estiver zerado, usar valores fictícios baseados na receita
                if necessidades == 0 and desejos == 0 and investimentos == 0:
                    regra_real = {
                        "Necessidades": receita_total * 0.45,  # Ligeiramente abaixo do ideal
                        "Desejos": receita_total * 0.35,       # Ligeiramente acima do ideal
                        "Investimentos": receita_total * 0.20  # No ideal
                    }
                else:
                    regra_real = {
                        "Necessidades": necessidades,
                        "Desejos": desejos,
                        "Investimentos": investimentos
                    }
            else:
                regra_real = resumo_total['regra_50_30_20']
            
            # Mostrar comparação visual
            st.markdown("### Comparação Ideal vs Real")
            
            # Tabela de comparação
            data = {
                "Categoria": list(regra_ideal.keys()),
                "Ideal (R$)": [f"R$ {v:,.2f}" for v in regra_ideal.values()],
                "Real (R$)": [f"R$ {regra_real.get(k, 0):,.2f}" for k in regra_ideal.keys()],
                "% da Receita": [f"{(regra_real.get(k, 0) / receita_total * 100 if receita_total > 0 else 0):,.1f}%" for k in regra_ideal.keys()],
                "Diferença": [f"{(regra_real.get(k, 0) - v):,.2f}" for k, v in regra_ideal.items()]
            }
            
            # Mostrar como DataFrame
            df_comparacao = pd.DataFrame(data)
            st.dataframe(df_comparacao, use_container_width=True)
            
            # Explicação da regra
            with st.expander("Como funciona a regra 50/30/20?"):
                st.markdown("""
                A regra 50/30/20 é uma diretriz simples para orçamento pessoal:
                
                - **50%** da sua renda deve ser destinada a necessidades básicas (aluguel, alimentação, contas, etc.)
                - **30%** para gastos pessoais e desejos (lazer, assinaturas, compras não essenciais)
                - **20%** para poupança e investimentos (reserva de emergência, aposentadoria, etc.)
                
                Esta distribuição ajuda a manter um equilíbrio saudável em suas finanças.
                """)
        
        with col2:
            # Gráfico de barras comparativo
            if receita_total > 0:
                fig = create_budget_comparison_chart(
                    [regra_real.get(k, 0) for k in regra_ideal.keys()],
                    list(regra_ideal.values()),
                    list(regra_ideal.keys())
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Recomendações baseadas na análise
                st.subheader("Recomendações")
                for categoria, valor_ideal in regra_ideal.items():
                    valor_real = regra_real.get(categoria, 0)
                    diferenca = valor_real - valor_ideal
                    if abs(diferenca) < valor_ideal * 0.1:  # Dentro de 10% do ideal
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
        
        # Obter dados históricos
        dados_historicos = get_historical_data()
        
        if dados_historicos["Receitas"]:
            # Gráfico de tendências
            fig_tendencia = create_trend_chart("Tendência de Receitas e Despesas", dados_historicos)
            st.plotly_chart(fig_tendencia, use_container_width=True)
            
            # Seletor de método de projeção
            metodo_projecao = st.selectbox(
                "Método de Projeção",
                options=["Média Móvel", "Tendência Linear"],
                index=0,
                help="Escolha o método para calcular as projeções futuras"
            )
            
            # Mapear seleção para os valores aceitos pela função
            metodo = "media_movel" if metodo_projecao == "Média Móvel" else "tendencia"
            
            # Seletor de meses para projeção
            meses_projecao = st.slider("Meses para projeção", 1, 12, 3)
            
            # Calcular projeções
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
            
            # Análise de saúde financeira futura
            st.subheader("Previsão de Saúde Financeira")
            
            # Calcular saldos projetados
            saldos_projetados = {}
            periodos_futuros = list(projecoes_receitas.keys())
            
            for periodo in periodos_futuros:
                receita_proj = projecoes_receitas.get(periodo, 0)
                despesa_proj = projecoes_despesas.get(periodo, 0)
                saldo_proj = receita_proj - despesa_proj
                saldos_projetados[periodo] = saldo_proj
            
            # Mostrar tabela de projeções
            df_projecoes = pd.DataFrame({
                "Período": periodos_futuros,
                "Receita Projetada": [f"R$ {projecoes_receitas.get(p, 0):,.2f}" for p in periodos_futuros],
                "Despesa Projetada": [f"R$ {projecoes_despesas.get(p, 0):,.2f}" for p in periodos_futuros],
                "Saldo Projetado": [f"R$ {saldos_projetados.get(p, 0):,.2f}" for p in periodos_futuros]
            })
            
            st.dataframe(df_projecoes, use_container_width=True)
            
            # Gráfico de saldos projetados
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
        
        # Carregar metas do usuário
        metas = view_goals()
        
        if metas:
            for meta in metas:
                # Extrair dados do dicionário no formato Supabase
                meta_valor = float(meta.get('target_amount', 0))
                meta_atual = float(meta.get('current_amount', 0))
                meta_nome = meta.get('description', 'Meta sem nome')
                
                # Evitar divisão por zero
                if meta_valor > 0:
                    progresso = (meta_atual / meta_valor) * 100
                else:
                    progresso = 0
                
                # Mostrar barra de progresso
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.progress(min(progresso / 100, 1.0), text=f"{meta_nome}: {progresso:.1f}%")
                with col2:
                    st.write(f"R$ {meta_atual:,.2f} / R$ {meta_valor:,.2f}")
            
            # Mostrar gráfico de progresso das metas
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

def get_historical_data(months=12):
    """
    Obtém dados históricos dos últimos meses para visualização de tendências
    
    Args:
        months: Número de meses no histórico
        
    Returns:
        dict: Dados históricos organizados para análise de tendências
    """
    try:
        # Inicializar dicionários para armazenar dados
        dados_historicos = {
            "Receitas": {},
            "Despesas": {},
            "Investimentos": {},
            "Saldo": {}
        }
        
        # Obter todas as transações
        transactions = view_transactions()
        
        # Data atual para referência
        current_date = datetime.now()
        
        # Para cada mês no intervalo
        for i in range(months-1, -1, -1):
            # Calcular mês e ano
            data_ref = current_date.replace(day=1) - relativedelta(months=i)
            periodo = f"{data_ref.year}-{data_ref.month:02d}"
            
            # Inicializar valores para o período
            dados_historicos["Receitas"][periodo] = 0
            dados_historicos["Despesas"][periodo] = 0
            dados_historicos["Investimentos"][periodo] = 0
            
            # Filtrar transações do mês
            month_start = data_ref.strftime("%Y-%m-%d")
            if data_ref.month == 12:
                month_end = data_ref.replace(year=data_ref.year + 1, month=1, day=1).strftime("%Y-%m-%d")
            else:
                month_end = data_ref.replace(month=data_ref.month + 1, day=1).strftime("%Y-%m-%d")
            
            # Processar cada transação do período
            for transaction in transactions:
                trans_date = transaction.get('date', '')
                if month_start <= trans_date < month_end:
                    valor = float(transaction.get('amount', 0))
                    tipo = str(transaction.get('type', '')).lower()
                    
                    if tipo in ['receita', 'income', 'revenue']:
                        dados_historicos["Receitas"][periodo] += valor
                    elif tipo in ['despesa', 'expense', 'expenses']:
                        dados_historicos["Despesas"][periodo] += valor
                    elif tipo in ['investimento', 'investment']:
                        dados_historicos["Investimentos"][periodo] += valor
            
            # Calcular saldo do período
            dados_historicos["Saldo"][periodo] = (
                dados_historicos["Receitas"][periodo] - 
                dados_historicos["Despesas"][periodo] - 
                dados_historicos["Investimentos"][periodo]
            )
            
            # Log para debug
            print(f"Dados do período {periodo}:")
            print(f"Receitas: R${dados_historicos['Receitas'][periodo]:.2f}")
            print(f"Despesas: R${dados_historicos['Despesas'][periodo]:.2f}")
            print(f"Investimentos: R${dados_historicos['Investimentos'][periodo]:.2f}")
            print(f"Saldo: R${dados_historicos['Saldo'][periodo]:.2f}")
            print("---")
        
        return dados_historicos
        
    except Exception as e:
        print(f"Erro ao obter dados históricos: {e}")
        st.error(f"Erro ao obter dados históricos: {e}")
        import traceback
        print(traceback.format_exc())
        return {"Receitas": {}, "Despesas": {}, "Investimentos": {}, "Saldo": {}}
