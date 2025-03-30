"""
Módulo responsável pelas análises financeiras das transações.
"""
from datetime import datetime
from transactions_db import view_transactions

def get_balance():
    """Calcula o saldo atual considerando receitas, despesas e investimentos"""
    transactions = view_transactions()
    
    # Calcular saldo
    saldo = 0
    investimentos = 0
    
    for t in transactions:
        if t['status'].lower() != 'pago':
            continue
            
        if t['type'] == 'Receita':
            saldo += t['amount']
        elif t['type'] == 'Despesa':
            saldo -= t['amount']
        elif t['type'] == 'Investimento':
            investimentos += t['amount']
            saldo -= t['amount']  # O valor sai da conta corrente
    
    return {
        'saldo_conta': saldo,
        'total_investido': investimentos,
        'patrimonio_total': saldo + investimentos
    }

def get_monthly_summary(month=None, year=None):
    """Obtém um resumo das transações do mês, incluindo investimentos"""
    if month is None: 
        month = datetime.now().month
    if year is None:
        year = datetime.now().year
    
    transactions = view_transactions()
    
    # Filtrar transações do mês
    month_transactions = [
        t for t in transactions 
        if t['status'].lower() == 'pago' 
        and datetime.strptime(t['date'], '%Y-%m-%d').month == month
        and datetime.strptime(t['date'], '%Y-%m-%d').year == year
    ]
    
    # Calcular totais
    receitas = 0
    despesas = 0
    investimentos = 0
    
    for t in month_transactions:
        if t['type'] == 'Receita':
            receitas += t['amount']
        elif t['type'] == 'Despesa':
            despesas += t['amount']
        elif t['type'] == 'Investimento':
            investimentos += t['amount']
    
    return {
        'receitas': receitas,
        'despesas': despesas + investimentos,  # Considera investimentos como saída de caixa
        'investimentos': investimentos,
        'saldo_mes': receitas - despesas - investimentos
    }

def get_category_distribution(transactions=None, tipo='Despesa'):
    """Calcula a distribuição de valores por categoria para um tipo específico de transação"""
    import pandas as pd
    
    if transactions is None:
        transactions = view_transactions()
    
    # Filtrar transações por tipo e status
    filtered_transactions = [
        {'category': t['category'], 'amount': t['amount']}
        for t in transactions
        if t['type'] == tipo and t['status'].lower() == 'pago'
    ]
    
    if not filtered_transactions:
        return pd.Series()
    
    df = pd.DataFrame(filtered_transactions)
    return df.groupby('category')['amount'].sum()
