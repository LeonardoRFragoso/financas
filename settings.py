import sqlite3
import json

def init_settings():
    """Inicializa a tabela de configurações no banco de dados"""
    from db import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Criar tabela de configurações se não existir
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  value TEXT NOT NULL)''')
    
    # Configurações padrão
    default_settings = {
        "dark_mode": True,
        "currency": "BRL",
        "date_format": "%d/%m/%Y",
        "show_notifications": True
    }
    
    # Verificar se já existem configurações
    c.execute('SELECT COUNT(*) FROM settings')
    count = c.fetchone()[0]
    
    # Se não existem configurações, adiciona as padrão
    if count == 0:
        for key, value in default_settings.items():
            c.execute('INSERT INTO settings (name, value) VALUES (?, ?)', 
                      (key, json.dumps(value)))
    
    conn.commit()
    conn.close()

def get_settings():
    """Retorna todas as configurações como um dicionário"""
    from db import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT name, value FROM settings')
    settings = {name: json.loads(value) for name, value in c.fetchall()}
    
    conn.close()
    return settings

def update_setting(name, value):
    """Atualiza uma configuração específica"""
    from db import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Verificar se a configuração existe
    c.execute('SELECT COUNT(*) FROM settings WHERE name = ?', (name,))
    count = c.fetchone()[0]
    
    if count > 0:
        # Atualizar configuração existente
        c.execute('UPDATE settings SET value = ? WHERE name = ?', 
                  (json.dumps(value), name))
    else:
        # Inserir nova configuração
        c.execute('INSERT INTO settings (name, value) VALUES (?, ?)', 
                  (name, json.dumps(value)))
    
    conn.commit()
    conn.close()

def show_settings_page():
    """Interface de usuário para configurações"""
    from db import DB_PATH
    import streamlit as st
    
    st.subheader("Configurações do Aplicativo")
    
    # Obter configurações atuais
    settings = get_settings()
    
    # Formulário de configurações
    with st.form(key="settings_form"):
        dark_mode = st.checkbox("Modo Escuro", 
                               value=settings.get("dark_mode", True))
        
        currency_options = ["BRL", "USD", "EUR", "GBP"]
        currency = st.selectbox("Moeda", 
                               options=currency_options,
                               index=currency_options.index(settings.get("currency", "BRL")))
        
        date_format_options = {
            "%d/%m/%Y": "DD/MM/AAAA",
            "%m/%d/%Y": "MM/DD/AAAA",
            "%Y-%m-%d": "AAAA-MM-DD"
        }
        date_format = st.selectbox("Formato de Data", 
                                  options=list(date_format_options.keys()),
                                  format_func=lambda x: date_format_options[x],
                                  index=list(date_format_options.keys()).index(
                                      settings.get("date_format", "%d/%m/%Y")
                                  ))
        
        show_notifications = st.checkbox("Mostrar Notificações", 
                                       value=settings.get("show_notifications", True))
        
        submit_button = st.form_submit_button(label="Salvar Configurações")
        
        if submit_button:
            # Atualizar configurações
            update_setting("dark_mode", dark_mode)
            update_setting("currency", currency)
            update_setting("date_format", date_format)
            update_setting("show_notifications", show_notifications)
            
            st.success("Configurações salvas com sucesso!")
