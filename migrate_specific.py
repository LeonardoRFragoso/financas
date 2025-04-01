import streamlit as st
import sqlite3
import pandas as pd
import time
from supabase import create_client, Client
import json
import os

# Função para inicializar o cliente Supabase
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao conectar com Supabase: {str(e)}")
        return None

# Função para conectar ao SQLite
def connect_sqlite(db_path="financas.db"):
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar ao banco SQLite: {str(e)}")
        return None

# Função para migrar tabela por tabela
def migrate_table(supabase, sqlite_conn, table_name, primary_key="id"):
    try:
        # Obter os dados do SQLite
        cursor = sqlite_conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        if not rows:
            st.info(f"Nenhum dado encontrado na tabela {table_name}.")
            return True
        
        # Converter para lista de dicionários
        data = []
        for row in rows:
            item = dict(row)
            
            # Converter booleanos (SQLite armazena como 0/1)
            for key, value in item.items():
                if isinstance(value, (bool, int)) and key in ["recurring", "fixed_expense", "active"]:
                    item[key] = bool(value)
            
            data.append(item)
        
        # Migrar em lotes para evitar problemas
        batch_size = 50
        for i in range(0, len(data), batch_size):
            batch = data[i:i+batch_size]
            
            # Inserir ou atualizar no Supabase (upsert)
            response = supabase.table(table_name).upsert(
                batch, 
                on_conflict=primary_key  # Especificar a coluna de chave primária
            ).execute()
            
            if response.error:
                st.error(f"Erro ao inserir dados na tabela {table_name}: {response.error}")
                return False
        
        st.success(f"✅ Tabela {table_name} migrada com sucesso ({len(data)} registros)")
        return True
        
    except Exception as e:
        st.error(f"Erro ao migrar tabela {table_name}: {str(e)}")
        return False

# Interface principal
def show_specific_migration():
    st.title("Migração Específica SQLite → Supabase")
    
    # Verificar se o Supabase está configurado
    supabase = init_supabase()
    if not supabase:
        st.error("Supabase não configurado corretamente")
        return
    
    # Conectar ao SQLite
    sqlite_conn = connect_sqlite()
    if not sqlite_conn:
        st.error("Não foi possível conectar ao banco SQLite")
        return
    
    st.info("""
    ### Migração Tabela por Tabela
    
    Esta ferramenta migrará cada tabela individualmente, preservando os IDs e
    evitando duplicações. Por favor, escolha as tabelas que deseja migrar.
    """)
    
    # Mapear tabelas disponíveis
    tables = {
        "categories": "Categorias",
        "transactions": "Transações",
        "goals": "Metas",
        "settings": "Configurações",
        "users": "Usuários",
        "reminders": "Lembretes",
        "user_settings": "Configurações de Usuário"
    }
    
    # Selecionar tabelas para migrar
    selected_tables = []
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Selecione as tabelas:")
        for table, label in tables.items():
            if st.checkbox(f"{label} ({table})", value=True):
                selected_tables.append(table)
    
    with col2:
        st.subheader("Opções avançadas:")
        truncate_first = st.checkbox("Limpar tabelas antes de migrar", value=False,
                                     help="CUIDADO: Isso apagará todos os dados existentes no Supabase antes da migração")
    
    # Botão para iniciar migração
    if st.button("Iniciar Migração Específica", type="primary"):
        if not selected_tables:
            st.warning("Selecione pelo menos uma tabela para migrar")
            return
        
        # Limpar tabelas se solicitado
        if truncate_first:
            with st.spinner("Limpando tabelas no Supabase..."):
                for table in selected_tables:
                    try:
                        supabase.table(table).delete().neq("id", 0).execute()
                        st.info(f"Tabela {table} limpa com sucesso")
                    except Exception as e:
                        st.error(f"Erro ao limpar tabela {table}: {str(e)}")
        
        # Migrar tabelas selecionadas
        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        
        for i, table in enumerate(selected_tables):
            status_placeholder.info(f"Migrando tabela: {table}...")
            success = migrate_table(supabase, sqlite_conn, table)
            progress = (i + 1) / len(selected_tables)
            progress_bar.progress(progress)
            
            if not success:
                status_placeholder.error(f"Erro ao migrar tabela {table}")
        
        # Fechar conexão SQLite
        sqlite_conn.close()
        
        status_placeholder.success("✅ Migração específica concluída!")
        
        # Orientações finais
        st.info("""
        ### Próximos passos
        
        1. Verifique se todos os dados foram migrados corretamente.
        2. Caso necessário, refaça a migração de tabelas específicas.
        3. Atualize seu app no Streamlit Cloud.
        """)

if __name__ == "__main__":
    show_specific_migration()
