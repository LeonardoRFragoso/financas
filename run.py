import streamlit as st

# Configuração da página - DEVE ser a primeira chamada Streamlit
st.set_page_config(
    page_title="Finanças Pessoais",
    page_icon="💰",
    layout="wide"
)

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import bcrypt
import extra_streamlit_components as stx
from pathlib import Path
import calendar
from datetime import date
from io import BytesIO
import plotly.express as px
from dateutil.relativedelta import relativedelta
import json
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors

def get_cookie_manager():
    """Retorna o gerenciador de cookies"""
    if 'cookie_manager' not in st.session_state:
        st.session_state.cookie_manager = stx.CookieManager(key="unique_cookie_manager")
    return st.session_state.cookie_manager

def init_session_state():
    """Inicializa variáveis de estado da sessão"""
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'page' not in st.session_state:
        st.session_state.page = "login"
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

def check_cookie_auth():
    """Verifica autenticação via cookie"""
    cookie_manager = get_cookie_manager()
    user_id = cookie_manager.get("user_id")
    username = cookie_manager.get("username")
    
    if user_id and username:
        # Verifica se o usuário existe no banco
        conn = sqlite3.connect('financas.db')
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE id = ? AND username = ?", 
                 (user_id, username))
        result = c.fetchone()
        conn.close()
        
        if result:
            st.session_state.user_id = user_id
            st.session_state.username = username
            st.session_state.authenticated = True
            return True
    
    return False

def set_auth_cookie(user_id, username):
    """Define cookies de autenticação"""
    cookie_manager = get_cookie_manager()
    cookie_manager.set('user_id', str(user_id), expires_at=datetime.now() + timedelta(days=30))
    cookie_manager.set('username', username, expires_at=datetime.now() + timedelta(days=30))

def clear_auth_cookie():
    """Limpa cookies de autenticação"""
    cookie_manager = get_cookie_manager()
    cookie_manager.delete('user_id')
    cookie_manager.delete('username')

# Configuração do banco de dados
def init_db():
    """Inicializa o banco de dados"""
    conn = sqlite3.connect('financas.db')
    c = conn.cursor()
    
    # Criar tabela de usuários
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Criar tabela de transações
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  description TEXT NOT NULL,
                  amount REAL NOT NULL,
                  category TEXT NOT NULL,
                  date TEXT NOT NULL,
                  due_date TEXT,
                  type TEXT NOT NULL,
                  status TEXT NOT NULL,
                  recurring BOOLEAN DEFAULT 0,
                  priority INTEGER DEFAULT 2,
                  quinzena INTEGER,
                  installments INTEGER DEFAULT 1,
                  current_installment INTEGER DEFAULT 1,
                  fixed_expense BOOLEAN DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users(id))''')
    
    # Criar tabela de metas
    c.execute('''CREATE TABLE IF NOT EXISTS goals
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  description TEXT NOT NULL,
                  target_amount REAL NOT NULL,
                  current_amount REAL DEFAULT 0,
                  deadline TEXT NOT NULL,
                  category TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users(id))''')
    
    # Criar tabela de lembretes
    c.execute('''CREATE TABLE IF NOT EXISTS reminders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  transaction_id INTEGER,
                  reminder_date TEXT NOT NULL,
                  status TEXT DEFAULT 'pendente',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (transaction_id) REFERENCES transactions(id))''')
    
    # Criar tabela de configurações do usuário
    c.execute('''CREATE TABLE IF NOT EXISTS user_settings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER UNIQUE,
                  settings TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users(id))''')
    
    conn.commit()
    conn.close()

# Inicialização do banco de dados
init_db()

# Funções de autenticação
def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt)

def check_password(password, hashed):
    """Verifica se a senha corresponde ao hash armazenado"""
    try:
        # `hashed` já está no formato bytes, então não precisa de `.encode()`
        return bcrypt.checkpw(password.encode(), hashed)
    except Exception as e:
        print(f"Erro ao verificar senha: {str(e)}")
        return False


def create_user(username, password):
    if not username or not password:
        st.error("Usuário e senha são obrigatórios")
        return False
        
    try:
        conn = sqlite3.connect('financas.db')
        c = conn.cursor()
        
        # Verifica se o usuário já existe
        c.execute("SELECT username FROM users WHERE username=?", (username,))
        if c.fetchone():
            st.error("Nome de usuário já existe")
            return False
        
        print(f"Criando usuário: {username}")
            
        # Cria o hash da senha e salva o usuário
        hashed = hash_password(password)
        print(f"Hash gerado: {hashed[:20]}...")
        
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                 (username, hashed))
        conn.commit()
        
        # Verifica se o usuário foi criado
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        result = c.fetchone()
        print(f"Usuário criado: {result}")
        
        st.success("Usuário criado com sucesso! Faça login para continuar.")
        return True
        
    except Exception as e:
        print(f"Erro ao criar usuário: {str(e)}")
        st.error(f"Erro ao criar usuário: {str(e)}")
        return False
    finally:
        conn.close()

def login(username, password):
    """Função para realizar login"""
    try:
        conn = sqlite3.connect('financas.db')
        c = conn.cursor()
        c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        result = c.fetchone()
        
        if result and check_password(password, result[1]):
            user_id = result[0]
            st.session_state.user_id = user_id
            st.session_state.username = username
            st.session_state.authenticated = True
            
            # Define cookies de autenticação
            set_auth_cookie(user_id, username)
            return True
        else:
            st.session_state.authenticated = False
            return False
    except Exception as e:
        print(f"Erro ao fazer login: {str(e)}")
        return False
    finally:
        conn.close()


def logout():
    """Função para realizar logout"""
    # Limpa o estado da sessão
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.authenticated = False
    st.session_state.page = "login"
    
    # Limpa cookies
    clear_auth_cookie()
    
    st.rerun()

def login_page():
    """Página de login"""
    st.title("Login")
    
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("Entrar"):  # Removido o argumento `key`
                if login(username, password):
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos")
        
        with col2:
            if st.form_submit_button("Criar Conta"):  # Removido o argumento `key`
                st.session_state.page = "register"
                st.rerun()


def register_page():
    """Página de cadastro"""
    st.title("Criar Conta")
    
    with st.form("register_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        confirm_password = st.text_input("Confirmar Senha", type="password")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("Cadastrar"):  # Removido o argumento `key`
                if password != confirm_password:
                    st.error("As senhas não conferem")
                elif len(password) < 6:
                    st.error("A senha deve ter pelo menos 6 caracteres")
                else:
                    if create_user(username, password):
                        st.success("Usuário criado com sucesso!")
                        st.session_state.page = "login"
                        st.rerun()
                    else:
                        st.error("Erro ao criar usuário. Talvez o nome já esteja em uso.")
        
        with col2:
            if st.form_submit_button("Voltar"):  # Removido o argumento `key`
                st.session_state.page = "login"
                st.rerun()

# Funções de transações
def add_transaction(user_id, description, amount, category, date, due_date=None, type_trans="despesa", 
                  status="pendente", recurring=False, priority=2, quinzena=None, 
                  installments=1, current_installment=1, fixed_expense=False, create_reminder=True):
    """Adiciona uma nova transação"""
    try:
        conn = sqlite3.connect('financas.db')
        c = conn.cursor()
        
        # Se não foi fornecida uma data de vencimento, usa a data da transação
        if not due_date:
            due_date = date
            
        # Se não foi fornecida uma quinzena, calcula automaticamente
        if quinzena is None:
            quinzena = calcular_quinzena(datetime.strptime(date, '%Y-%m-%d'))
        
        # Insere a transação
        c.execute("""INSERT INTO transactions 
                  (user_id, description, amount, category, date, due_date, type, status,
                   recurring, priority, quinzena, installments, current_installment, fixed_expense)
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
               (user_id, description, amount, category, date, due_date, type_trans, status,
                recurring, priority, quinzena, installments, current_installment,
                fixed_expense))
        
        transaction_id = c.lastrowid
        
        # Se for parcelado, criar as parcelas futuras
        if installments > 1:
            base_date = datetime.strptime(date, '%Y-%m-%d')
            base_due_date = datetime.strptime(due_date, '%Y-%m-%d')
            
            for i in range(2, installments + 1):
                # Adiciona um mês para cada parcela
                next_date = base_date + relativedelta(months=i-1)
                next_due_date = base_due_date + relativedelta(months=i-1)
                
                # Calcula a quinzena da próxima parcela
                next_quinzena = calcular_quinzena(next_date)
                
                c.execute("""INSERT INTO transactions 
                          (user_id, description, amount, category, date, due_date, type, status,
                           recurring, priority, quinzena, installments, current_installment, fixed_expense)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                       (user_id, description, amount, category, 
                        next_date.strftime('%Y-%m-%d'),
                        next_due_date.strftime('%Y-%m-%d'),
                        type_trans, status, recurring, priority, next_quinzena,
                        installments, i, fixed_expense))
        
        conn.commit()
        
        # Cria lembrete se solicitado
        if create_reminder and status != 'pago':
            manage_reminders(transaction_id, due_date)
        
        return True
    except Exception as e:
        print(f"Erro ao adicionar transação: {str(e)}")
        return False
    finally:
        conn.close()

def calcular_quinzena(data):
    """Calcula a quinzena com base na data"""
    dia = data.day
    if dia <= 15:
        return 1
    return 2

def get_transactions(user_id, quinzena=None, mes=None, ano=None, tipo=None, status=None):
    """Retorna as transações do usuário com filtros opcionais"""
    try:
        conn = sqlite3.connect('financas.db')
        c = conn.cursor()
        
        query = "SELECT * FROM transactions WHERE user_id = ?"
        params = [user_id]
        
        if quinzena:
            query += " AND quinzena = ?"
            params.append(quinzena)
        
        if mes:
            query += " AND strftime('%m', date) = ?"
            params.append(f"{mes:02d}")
        
        if ano:
            query += " AND strftime('%Y', date) = ?"
            params.append(str(ano))
            
        if tipo:
            query += " AND type = ?"
            params.append(tipo)
            
        if status:
            query += " AND status = ?"
            params.append(status)
        
        c.execute(query, params)
        transactions = c.fetchall()
        
        # Converte para DataFrame
        columns = ['id', 'user_id', 'description', 'amount', 'category', 'date', 
                  'due_date', 'type', 'status', 'recurring', 'priority', 'quinzena',
                  'installments', 'current_installment', 'fixed_expense']
        df = pd.DataFrame(transactions, columns=columns)
        
        return df
    except Exception as e:
        print(f"Erro ao buscar transações: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()

def update_transaction_status(transaction_id, new_status):
    """Atualiza o status de uma transação"""
    try:
        conn = sqlite3.connect('financas.db')
        c = conn.cursor()
        
        c.execute("UPDATE transactions SET status = ? WHERE id = ?",
                 (new_status, transaction_id))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao atualizar status: {str(e)}")
        return False
    finally:
        conn.close()

def delete_transaction(transaction_id):
    """Deleta uma transação"""
    try:
        conn = sqlite3.connect('financas.db')
        c = conn.cursor()
        
        # Primeiro deleta os lembretes associados
        c.execute("DELETE FROM reminders WHERE transaction_id = ?", (transaction_id,))
        
        # Depois deleta a transação
        c.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao deletar transação: {str(e)}")
        return False
    finally:
        conn.close()

def manage_reminders(transaction_id, due_date):
    """Gerencia os lembretes para uma transação"""
    try:
        conn = sqlite3.connect('financas.db')
        c = conn.cursor()
        
        # Primeiro remove lembretes existentes
        c.execute("DELETE FROM reminders WHERE transaction_id = ?", (transaction_id,))
        
        # Cria novo lembrete
        c.execute("""INSERT INTO reminders 
                  (transaction_id, reminder_date, status)
                  VALUES (?, ?, ?)""",
                 (transaction_id, due_date, 'pendente'))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao gerenciar lembretes: {str(e)}")
        return False
    finally:
        conn.close()

def get_reminders(user_id, days_ahead=7):
    """Retorna lembretes próximos ao vencimento"""
    try:
        conn = sqlite3.connect('financas.db')
        c = conn.cursor()
        
        today = datetime.now().date()
        future = today + timedelta(days=days_ahead)
        
        c.execute("""
            SELECT r.*, t.description, t.amount, t.due_date
            FROM reminders r
            JOIN transactions t ON r.transaction_id = t.id
            WHERE t.user_id = ? 
            AND t.status != 'pago'
            AND date(t.due_date) BETWEEN date(?) AND date(?)
            ORDER BY t.due_date
        """, (user_id, today, future))
        
        reminders = c.fetchall()
        return reminders
    except Exception as e:
        print(f"Erro ao buscar lembretes: {str(e)}")
        return []
    finally:
        conn.close()

def load_settings(user_id):
    """Carrega configurações do usuário"""
    try:
        conn = sqlite3.connect('financas.db')
        c = conn.cursor()
        
        c.execute("SELECT settings FROM user_settings WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        
        if result:
            return json.loads(result[0])
        
        # Configurações padrão
        return {
            "dias_antecedencia": 3,
            "notificar_vencimentos": True,
            "notificar_metas": True,
            "mostrar_valores": True,
            "categorias": ["Alimentação", "Transporte", "Moradia", "Lazer", "Saúde"],
            "dia_corte": 15,
            "dia_pagamento_q1": 5,
            "dia_pagamento_q2": 20
        }
    except Exception as e:
        print(f"Erro ao carregar configurações: {str(e)}")
        return {}
    finally:
        conn.close()

def save_settings(user_id, settings):
    """Salva configurações do usuário"""
    try:
        conn = sqlite3.connect('financas.db')
        c = conn.cursor()
        
        settings_json = json.dumps(settings)
        
        # Tenta atualizar, se não existir, insere
        c.execute("""INSERT OR REPLACE INTO user_settings 
                  (user_id, settings) VALUES (?, ?)""",
                 (user_id, settings_json))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao salvar configurações: {str(e)}")
        return False
    finally:
        conn.close()

def add_goal(user_id, description, target_amount, deadline, category):
    """Adiciona uma nova meta"""
    try:
        conn = sqlite3.connect('financas.db')
        c = conn.cursor()
        
        c.execute("""INSERT INTO goals 
                  (user_id, description, target_amount, deadline, category)
                  VALUES (?, ?, ?, ?, ?)""",
                 (user_id, description, target_amount, deadline, category))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao adicionar meta: {str(e)}")
        return False
    finally:
        conn.close()

def get_goals(user_id):
    """Retorna as metas do usuário"""
    try:
        conn = sqlite3.connect('financas.db')
        c = conn.cursor()
        
        c.execute("SELECT * FROM goals WHERE user_id = ?", (user_id,))
        goals = c.fetchall()
        
        # Converte para DataFrame
        columns = ['id', 'user_id', 'description', 'target_amount', 
                  'current_amount', 'deadline', 'category', 'created_at']
        df = pd.DataFrame(goals, columns=columns)
        
        return df
    except Exception as e:
        print(f"Erro ao buscar metas: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()

def update_goal_progress(goal_id, current_amount):
    """Atualiza o progresso de uma meta"""
    try:
        conn = sqlite3.connect('financas.db')
        c = conn.cursor()
        
        c.execute("UPDATE goals SET current_amount = ? WHERE id = ?",
                 (current_amount, goal_id))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao atualizar meta: {str(e)}")
        return False
    finally:
        conn.close()

def delete_goal(goal_id):
    """Deleta uma meta"""
    try:
        conn = sqlite3.connect('financas.db')
        c = conn.cursor()
        
        c.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao deletar meta: {str(e)}")
        return False
    finally:
        conn.close()

def update_transaction(transaction_id, description=None, amount=None, category=None, 
                      date=None, due_date=None, type_trans=None, status=None,
                      recurring=None, priority=None, quinzena=None):
    """Atualiza uma transação existente"""
    try:
        conn = sqlite3.connect('financas.db')
        c = conn.cursor()
        
        # Constrói a query de atualização dinamicamente
        updates = []
        params = []
        
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if amount is not None:
            updates.append("amount = ?")
            params.append(amount)
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if date is not None:
            updates.append("date = ?")
            params.append(date)
        if due_date is not None:
            updates.append("due_date = ?")
            params.append(due_date)
        if type_trans is not None:
            updates.append("type = ?")
            params.append(type_trans)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if recurring is not None:
            updates.append("recurring = ?")
            params.append(recurring)
        if priority is not None:
            updates.append("priority = ?")
            params.append(priority)
        if quinzena is not None:
            updates.append("quinzena = ?")
            params.append(quinzena)
        
        if not updates:
            return True
        
        # Adiciona o ID da transação aos parâmetros
        params.append(transaction_id)
        
        # Executa a atualização
        query = f"UPDATE transactions SET {', '.join(updates)} WHERE id = ?"
        c.execute(query, params)
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao atualizar transação: {str(e)}")
        return False
    finally:
        conn.close()

def export_data(user_id, start_date=None, end_date=None):
    """Exporta dados para CSV"""
    try:
        conn = sqlite3.connect('financas.db')
        
        # Query base
        query = """
            SELECT t.*, g.description as goal_description, g.target_amount, g.current_amount
            FROM transactions t
            LEFT JOIN goals g ON t.category = g.category AND t.user_id = g.user_id
            WHERE t.user_id = ?
        """
        params = [user_id]
        
        # Adiciona filtros de data se fornecidos
        if start_date:
            query += " AND date(t.date) >= date(?)"
            params.append(start_date)
        if end_date:
            query += " AND date(t.date) <= date(?)"
            params.append(end_date)
            
        # Executa query
        df = pd.read_sql_query(query, conn, params=params)
        
        # Formata datas
        for col in ['date', 'due_date', 'created_at']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col]).dt.strftime('%d/%m/%Y')
                
        # Formata valores monetários
        for col in ['amount', 'target_amount', 'current_amount']:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: f"R$ {x:.2f}" if pd.notnull(x) else "")
                
        return df
        
    except Exception as e:
        print(f"Erro ao exportar dados: {str(e)}")
        return None
    finally:
        conn.close()

def generate_report(user_id, start_date=None, end_date=None):
    """Gera relatório em PDF"""
    try:
        # Busca dados
        df = export_data(user_id, start_date, end_date)
        if df is None:
            return None
            
        # Cria buffer para o PDF
        buffer = io.BytesIO()
        
        # Configura o documento PDF
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        # Título
        elements.append(Paragraph("Relatório Financeiro", getSampleStyleSheet()['Title']))
        elements.append(Spacer(1, 12))
        
        # Período do relatório
        if start_date and end_date:
            period = f"Período: {start_date} a {end_date}"
        else:
            period = "Período: Todo o histórico"
        elements.append(Paragraph(period, getSampleStyleSheet()['Normal']))
        elements.append(Spacer(1, 12))
        
        # Resumo financeiro
        receitas = df[df['type'] == 'receita']['amount'].sum()
        despesas = df[df['type'] == 'despesa']['amount'].sum()
        saldo = receitas - despesas
        
        elements.append(Paragraph("Resumo Financeiro", getSampleStyleSheet()['Heading2']))
        elements.append(Paragraph(f"Receitas: R$ {receitas:.2f}", getSampleStyleSheet()['Normal']))
        elements.append(Paragraph(f"Despesas: R$ {despesas:.2f}", getSampleStyleSheet()['Normal']))
        elements.append(Paragraph(f"Saldo: R$ {saldo:.2f}", getSampleStyleSheet()['Normal']))
        elements.append(Spacer(1, 12))
        
        # Transações
        elements.append(Paragraph("Transações", getSampleStyleSheet()['Heading2']))
        
        # Cria tabela de transações
        data = [['Data', 'Descrição', 'Categoria', 'Valor', 'Status']]
        for _, row in df.iterrows():
            data.append([
                row['date'],
                row['description'],
                row['category'],
                f"R$ {row['amount']:.2f}",
                row['status']
            ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)
        
        # Gera o PDF
        doc.build(elements)
        
        # Retorna o buffer
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        print(f"Erro ao gerar relatório: {str(e)}")
        return None

def main_interface():
    """Interface principal do aplicativo"""
    st.title("Finanças Pessoais")
    
    # Atualiza transações vencidas
    update_overdue_transactions()
    
    # Verifica pagamentos próximos
    check_upcoming_payments(st.session_state.user_id)
    
    # Sidebar melhorada
    st.sidebar.title("💰 Finanças Pessoais")

    # Perfil do usuário
    st.sidebar.markdown("### Perfil")
    st.sidebar.write(f"**Usuário:** {st.session_state.username}")
    st.sidebar.write(f"**Desde:** {datetime.now().strftime('%d/%m/%Y')}")  # Data simulada
    st.sidebar.markdown("---")

    # Menus com ícones
    menu_icons = {
        "Dashboard": "📊",
        "Transações": "💳",
        "Metas": "🎯",
        "Configurações": "⚙️"
    }
    menu = st.sidebar.radio("Menu", list(menu_icons.keys()), 
                            format_func=lambda x: f"{menu_icons[x]} {x}")

    # Atalhos rápidos na barra lateral
    st.sidebar.markdown("### Atalhos")
    if st.sidebar.button("➕ Nova Transação", key="sidebar_nova_transacao"):
        st.session_state.page = "Transações"
        st.rerun()

    if st.sidebar.button("🎯 Nova Meta", key="sidebar_nova_meta"):
        st.session_state.page = "Metas"
        st.rerun()

    if st.sidebar.button("Sair", key="sidebar_sair"):
        logout()
        st.rerun()



    # Progresso das metas
    st.sidebar.markdown("### Progresso das Metas")
    df_metas = get_goals(st.session_state.user_id)
    if not df_metas.empty:
        for _, meta in df_metas.iterrows():
            progresso = (meta['current_amount'] / meta['target_amount']) * 100
            st.sidebar.progress(progresso / 100, text=meta['description'])
    else:
        st.sidebar.write("Nenhuma meta cadastrada.")

    # Controle de exibição de menu
    if menu == "Dashboard":
        show_dashboard()
    elif menu == "Transações":
        show_transactions()
    elif menu == "Metas":
        show_goals()
    elif menu == "Configurações":
        show_settings()

def show_dashboard():
    """Mostra o dashboard principal"""
    st.header("Dashboard")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        mes = st.selectbox("Mês", range(1, 13), 
                          format_func=lambda x: calendar.month_name[x])
    
    with col2:
        ano = st.selectbox("Ano", range(2020, 2026))
    
    with col3:
        quinzena = st.selectbox("Quinzena", [None, 1, 2], 
                              format_func=lambda x: "Todas" if x is None else f"{x}ª")
    
    # Busca transações
    df = get_transactions(st.session_state.user_id, quinzena, mes, ano)
    
    if df.empty:
        st.warning("Nenhuma transação encontrada para o período selecionado.")
        return
    
    # Resumo financeiro
    st.subheader("Resumo Financeiro")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        receitas = df[df['type'] == 'receita']['amount'].sum()
        st.metric("Receitas", f"R$ {receitas:.2f}")
    
    with col2:
        despesas = df[df['type'] == 'despesa']['amount'].sum()
        st.metric("Despesas", f"R$ {despesas:.2f}")
    
    with col3:
        saldo = receitas - despesas
        delta = saldo - despesas  # Variação em relação às despesas
        st.metric("Saldo", f"R$ {saldo:.2f}", 
                 delta=f"R$ {delta:.2f}",
                 delta_color="normal")
    
    with col4:
        despesas_fixas = df[(df['type'] == 'despesa') & (df['fixed_expense'])]['amount'].sum()
        percentual_fixas = (despesas_fixas / despesas * 100) if despesas > 0 else 0
        st.metric("Despesas Fixas", f"R$ {despesas_fixas:.2f}",
                 delta=f"{percentual_fixas:.1f}% das despesas")
    
    # Gráficos
    st.subheader("Análise Visual")
    
    tab1, tab2, tab3 = st.tabs(["Categorias", "Status", "Tendências"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de pizza por categoria (despesas)
            df_despesas = df[df['type'] == 'despesa']
            fig = px.pie(df_despesas, values='amount', names='category',
                        title='Despesas por Categoria')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Gráfico de pizza por categoria (receitas)
            df_receitas = df[df['type'] == 'receita']
            fig = px.pie(df_receitas, values='amount', names='category',
                        title='Receitas por Categoria')
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de barras por status
            df_status = df.groupby(['status', 'type'])['amount'].sum().reset_index()
            fig = px.bar(df_status, x='status', y='amount', color='type',
                        title='Transações por Status',
                        barmode='group')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Tabela de resumo por status
            st.write("Resumo por Status")
            df_status_summary = df.pivot_table(
                values='amount',
                index='status',
                columns='type',
                aggfunc='sum',
                fill_value=0
            ).reset_index()
            
            # Formata os valores monetários
            for col in df_status_summary.columns:
                if col != 'status':
                    df_status_summary[col] = df_status_summary[col].apply(
                        lambda x: f"R$ {x:.2f}"
                    )
            
            st.dataframe(df_status_summary, use_container_width=True)
    
    with tab3:
        # Gráfico de linha mostrando tendência ao longo do tempo
        df['date'] = pd.to_datetime(df['date'])
        df_trend = df.groupby(['date', 'type'])['amount'].sum().reset_index()
        
        fig = px.line(df_trend, x='date', y='amount', color='type',
                     title='Tendência de Receitas e Despesas')
        st.plotly_chart(fig, use_container_width=True)
    
    # Próximos vencimentos
    st.subheader("Próximos Vencimentos")
    
    df_vencimentos = df[
        (df['status'] == 'pendente') & 
        (df['type'] == 'despesa')
    ].sort_values('due_date')
    
    if not df_vencimentos.empty:
        for _, row in df_vencimentos.head(5).iterrows():
            with st.expander(f"{row['description']} - R$ {row['amount']:.2f}"):
                st.write(f"**Categoria:** {row['category']}")
                st.write(f"**Vencimento:** {row['due_date']}")
                st.write(f"**Prioridade:** {row['priority']}")
                if st.button("Marcar como Pago", key=f"pagar_{row['id']}"):
                    if update_transaction_status(row['id'], 'pago'):
                        st.success("Status atualizado!")
                        st.rerun()
    else:
        st.info("Não há vencimentos próximos.")
    
    # Metas
    st.subheader("Progresso das Metas")
    
    df_metas = get_goals(st.session_state.user_id)
    
    if not df_metas.empty:
        for _, row in df_metas.iterrows():
            progresso = (row['current_amount'] / row['target_amount']) * 100
            st.progress(progresso / 100, text=row['description'])
            st.write(f"R$ {row['current_amount']:.2f} de R$ {row['target_amount']:.2f} ({progresso:.1f}%)")
    else:
        st.info("Nenhuma meta cadastrada.")


def show_transactions():
    """Mostra a página de transações"""
    st.header("Transações")
    
    # Tabs para diferentes visualizações
    tab1, tab2 = st.tabs(["Nova Transação", "Listar Transações"])
    
    with tab1:
        # Formulário para adicionar transação
        with st.form("nova_transacao"):
            st.subheader("Nova Transação")
            
            col1, col2 = st.columns(2)
            
            with col1:
                description = st.text_input("Descrição")
                amount = st.number_input("Valor", min_value=0.0, step=0.01)
                category = st.selectbox(
                    "Categoria", 
                    load_settings(st.session_state.user_id)['categorias']
                )
            
            with col2:
                type_trans = st.selectbox("Tipo", ["despesa", "receita"])
                date = st.date_input("Data")
                due_date = st.date_input("Data de Vencimento")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                status = st.selectbox("Status", ["pendente", "pago", "atrasado"])
            
            with col2:
                recurring = st.checkbox("Recorrente")
            
            with col3:
                fixed_expense = st.checkbox("Despesa Fixa")
            
            if recurring:
                col1, col2 = st.columns(2)
                with col1:
                    installments = st.number_input(
                        "Número de Parcelas", 
                        min_value=2, max_value=12, step=1
                    )
                with col2:
                    priority = st.slider("Prioridade", 1, 5, 2)
            else:
                installments = 1
                priority = 2
            
            if st.form_submit_button("Adicionar"):
                if add_transaction(
                    st.session_state.user_id,
                    description,
                    amount,
                    category,
                    date.strftime('%Y-%m-%d'),
                    due_date.strftime('%Y-%m-%d'),
                    type_trans,
                    status,
                    recurring,
                    priority,
                    None,  # quinzena será calculada
                    installments,
                    1,  # current_installment
                    fixed_expense
                ):
                    st.success("Transação adicionada com sucesso!")
                    st.rerun()
                else:
                    st.error("Erro ao adicionar transação")
    
    with tab2:
        # Filtros
        st.subheader("Filtros")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            mes = st.selectbox(
                "Mês", range(1, 13), 
                format_func=lambda x: calendar.month_name[x]
            )
        
        with col2:
            ano = st.selectbox("Ano", range(2020, 2026))
        
        with col3:
            quinzena = st.selectbox(
                "Quinzena", [None, 1, 2], 
                format_func=lambda x: "Todas" if x is None else f"{x}ª"
            )
        
        col1, col2 = st.columns(2)
        
        with col1:
            tipo = st.selectbox(
                "Tipo", [None, "despesa", "receita"],
                format_func=lambda x: "Todos" if x is None else x.title()
            )
        
        with col2:
            status_filter = st.selectbox(
                "Status", [None, "pendente", "pago", "atrasado"],
                format_func=lambda x: "Todos" if x is None else x.title()
            )
        
        # Lista de transações
        st.subheader("Suas Transações")
        
        df = get_transactions(
            st.session_state.user_id, quinzena, mes, ano, tipo, status_filter
        )
        
        if df.empty:
            st.info("Nenhuma transação encontrada")
            return
        
        # Converter colunas relevantes para datetime
        df['date'] = pd.to_datetime(df['date'], errors='coerce')  # Converte 'date' para datetime
        df['due_date'] = pd.to_datetime(df['due_date'], errors='coerce')  # Converte 'due_date' para datetime
        
        # Exibe transações em uma tabela editável
        edited_df = st.data_editor(
            df,
            hide_index=True,
            column_config={
                "id": None,  # Esconde coluna ID
                "user_id": None,  # Esconde coluna user_id
                "amount": st.column_config.NumberColumn(
                    "Valor",
                    format="R$ %.2f"
                ),
                "date": st.column_config.DateColumn(
                    "Data"
                ),
                "due_date": st.column_config.DateColumn(
                    "Vencimento"
                ),
                "status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["pendente", "pago", "atrasado"]
                ),
                "type": st.column_config.SelectboxColumn(
                    "Tipo",
                    options=["despesa", "receita"]
                ),
                "category": st.column_config.SelectboxColumn(
                    "Categoria",
                    options=load_settings(st.session_state.user_id)['categorias']
                )
            }
        )
        
        # Verifica mudanças e atualiza
        if not df.equals(edited_df):
            for index, row in edited_df.iterrows():
                original_row = df.loc[df['id'] == row['id']].iloc[0]
                
                # Verifica quais campos foram alterados
                updates = {}
                for col in ['description', 'amount', 'category', 'date', 'due_date', 
                           'type', 'status', 'recurring', 'priority', 'quinzena']:
                    if row[col] != original_row[col]:
                        updates[col] = row[col]
                
                if updates:
                    if update_transaction(row['id'], **updates):
                        st.success(f"Transação '{row['description']}' atualizada!")
                    else:
                        st.error(f"Erro ao atualizar transação '{row['description']}'")
        
        # Botão para atualizar status em massa
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Marcar Selecionadas como Pagas"):
                selected_rows = edited_df[edited_df['status'] == 'pendente']
                for _, row in selected_rows.iterrows():
                    update_transaction_status(row['id'], 'pago')
                st.rerun()
        
        with col2:
            if st.button("Excluir Selecionadas"):
                selected_rows = edited_df[edited_df['status'] == 'pendente']
                for _, row in selected_rows.iterrows():
                    delete_transaction(row['id'])
                st.rerun()


def update_overdue_transactions():
    """Atualiza transações vencidas"""
    try:
        conn = sqlite3.connect('financas.db')
        c = conn.cursor()
        
        today = datetime.now().date()
        
        # Atualiza status de transações vencidas
        c.execute("""UPDATE transactions 
                  SET status = 'atrasado'
                  WHERE status = 'pendente'
                  AND date(due_date) < date(?)
                  AND type = 'despesa'""",
                 (today.strftime('%Y-%m-%d'),))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao atualizar transações vencidas: {str(e)}")
        return False
    finally:
        conn.close()

def check_upcoming_payments(user_id):
    """Verifica pagamentos próximos"""
    settings = load_settings(user_id)
    days_ahead = settings['dias_antecedencia']
    
    reminders = get_reminders(user_id, days_ahead)
    
    if reminders:
        st.warning(f"Você tem {len(reminders)} pagamentos próximos!")
        
        # Mostra detalhes em um expander
        with st.expander("Ver Detalhes"):
            for reminder in reminders:
                due_date = datetime.strptime(reminder[3], '%Y-%m-%d').date()
                days_left = (due_date - datetime.now().date()).days
                
                st.write(f"**{reminder[1]}** - R$ {reminder[2]:.2f}")
                st.write(f"Vencimento: {due_date.strftime('%d/%m/%Y')} ({days_left} dias)")
                st.divider()

def show_goals():
    """Mostra a página de metas"""
    st.header("Metas de Economia")
    
    # Formulário para adicionar meta
    with st.form("nova_meta"):
        st.subheader("Nova Meta")
        
        col1, col2 = st.columns(2)
        
        with col1:
            description = st.text_input("Descrição")
            target_amount = st.number_input("Valor Alvo", min_value=0.0, step=0.01)
        
        with col2:
            deadline = st.date_input("Data Limite")
            category = st.selectbox("Categoria", 
                                  load_settings(st.session_state.user_id)['categorias'])
        
        if st.form_submit_button("Adicionar"):
            if add_goal(
                st.session_state.user_id,
                description,
                target_amount,
                deadline.strftime('%Y-%m-%d'),
                category
            ):
                st.success("Meta adicionada com sucesso!")
                st.rerun()
            else:
                st.error("Erro ao adicionar meta")
    
    # Lista de metas
    st.subheader("Suas Metas")
    
    df = get_goals(st.session_state.user_id)
    
    if df.empty:
        st.info("Nenhuma meta encontrada")
        return
    
    # Exibe metas em uma tabela editável
    edited_df = st.data_editor(
        df,
        hide_index=True,
        column_config={
            "id": None,  # Esconde coluna ID
            "user_id": None,  # Esconde coluna user_id
            "target_amount": st.column_config.NumberColumn(
                "Valor Alvo",
                format="R$ %.2f"
            ),
            "current_amount": st.column_config.NumberColumn(
                "Valor Atual",
                format="R$ %.2f"
            ),
            "deadline": st.column_config.DateColumn(
                "Data Limite"
            )
        }
    )
    
    # Verifica mudanças e atualiza
    if not df.equals(edited_df):
        for index, row in edited_df.iterrows():
            original_row = df.loc[df['id'] == row['id']].iloc[0]
            if row['current_amount'] != original_row['current_amount']:
                if update_goal_progress(row['id'], row['current_amount']):
                    st.success(f"Meta '{row['description']}' atualizada!")
                else:
                    st.error(f"Erro ao atualizar meta '{row['description']}'")

def show_settings():
    st.header("Configurações")
    
    # Tabs para diferentes seções
    tab1, tab2, tab3 = st.tabs(["Geral", "Notificações", "Exportar"])
    
    with tab1:
        # Carregar configurações atuais
        settings = load_settings(st.session_state.user_id)
        
        # Configurações de Visualização
        st.subheader("Visualização")
        
        mostrar_valores = st.checkbox(
            "Mostrar valores monetários no dashboard",
            value=settings['mostrar_valores'],
            key="mostrar_valores"
        )
        
        categorias_customizadas = st.text_area(
            "Categorias personalizadas (uma por linha)",
            value="\n".join(settings['categorias']),
            key="categorias_customizadas"
        )
        
        # Configurações de Quinzena
        st.subheader("Configurações de Quinzena")
        
        dia_corte = st.number_input(
            "Dia de corte entre quinzenas",
            min_value=1,
            max_value=31,
            value=settings['dia_corte'],
            key="dia_corte"
        )
        
        dia_pagamento_q1 = st.number_input(
            "Dia de pagamento (1ª quinzena)",
            min_value=1,
            max_value=15,
            value=settings['dia_pagamento_q1'],
            key="dia_pagamento_q1"
        )
        
        dia_pagamento_q2 = st.number_input(
            "Dia de pagamento (2ª quinzena)",
            min_value=16,
            max_value=31,
            value=settings['dia_pagamento_q2'],
            key="dia_pagamento_q2"
        )
    
    with tab2:
        # Configurações de Notificações
        st.subheader("Notificações")
        
        dias_antecedencia = st.number_input(
            "Dias de antecedência para lembretes",
            min_value=1,
            max_value=10,
            value=settings['dias_antecedencia'],
            key="dias_antecedencia"
        )
        
        notificar_vencimentos = st.checkbox(
            "Notificar contas próximas ao vencimento",
            value=settings['notificar_vencimentos'],
            key="notificar_vencimentos"
        )
        
        notificar_metas = st.checkbox(
            "Notificar progresso das metas",
            value=settings['notificar_metas'],
            key="notificar_metas"
        )
    
    with tab3:
        # Exportação de dados
        st.subheader("Exportar Dados")
        
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input("Data Inicial")
        
        with col2:
            end_date = st.date_input("Data Final")
        
        if st.button("Exportar para CSV"):
            df = export_data(
                st.session_state.user_id,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            if df is not None:
                # Converte DataFrame para CSV
                csv = df.to_csv(index=False)
                
                # Cria botão de download
                st.download_button(
                    label="Baixar CSV",
                    data=csv,
                    file_name=f"financas_{start_date}_{end_date}.csv",
                    mime="text/csv"
                )
            else:
                st.error("Erro ao exportar dados")
        
        if st.button("Gerar Relatório em PDF"):
            pdf = generate_report(
                st.session_state.user_id,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            if pdf is not None:
                # Cria botão de download
                st.download_button(
                    label="Baixar PDF",
                    data=pdf,
                    file_name=f"relatorio_{start_date}_{end_date}.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("Erro ao gerar relatório")

# Execução principal
def main():
    """Função principal do aplicativo"""
    # Inicializa estado da sessão
    init_session_state()
    
    # Verifica autenticação via cookie
    if not st.session_state.authenticated:
        check_cookie_auth()
    
    # Se não estiver autenticado, mostra página de login/registro
    if not st.session_state.authenticated:
        if st.session_state.page == "register":
            register_page()
        else:
            login_page()
        return
    
    # Se estiver autenticado, mostra interface principal
    main_interface()
    
    # Botão de logout no sidebar
    if st.sidebar.button("Sair"):
        logout()
        st.rerun()

if __name__ == "__main__":
    main()