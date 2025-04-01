import streamlit as st
import sqlite3
import pandas as pd
import time
from supabase import create_client
import json
import os
import traceback
import base64

def init_supabase():
    """Inicializa o cliente Supabase usando as credenciais do Streamlit secrets"""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao conectar com Supabase: {str(e)}")
        return None

def extract_sqlite_data(db_path="financas.db"):
    """Extrai todos os dados do SQLite em um formato adequado para transformação"""
    data = {}
    try:
        conn = sqlite3.connect(db_path)
        # Habilitar nomes de colunas em vez de índices
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Obter lista de tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall() if row[0] != 'sqlite_sequence']
        
        # Extrair dados de cada tabela
        for table in tables:
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            
            # Converter para lista de dicionários
            table_data = []
            for row in rows:
                row_dict = dict(row)
                table_data.append(row_dict)
            
            data[table] = table_data
        
        conn.close()
        return data
    except Exception as e:
        st.error(f"Erro ao extrair dados do SQLite: {str(e)}")
        st.error(traceback.format_exc())
        return None

def is_json_serializable(obj):
    """Verifica se um objeto pode ser serializado em JSON"""
    try:
        json.dumps(obj)
        return True
    except (TypeError, OverflowError):
        return False

def convert_to_serializable(obj):
    """Converte objetos não serializáveis para formatos serializáveis"""
    if isinstance(obj, bytes):
        return base64.b64encode(obj).decode('utf-8')
    elif isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(i) for i in obj]
    elif not is_json_serializable(obj):
        return str(obj)
    return obj

def transform_data(data):
    """Transforma os dados extraídos do SQLite para o formato adequado para o Supabase"""
    transformed = {}
    
    # Processar cada tabela
    for table, rows in data.items():
        transformed[table] = []
        
        for row in rows:
            # Copiar o registro
            new_row = row.copy()
            
            # Transformações específicas por tabela
            if table == 'transactions':
                # Converter booleanos (SQLite armazena como 0/1 ou True/False)
                for bool_field in ['recurring', 'fixed_expense']:
                    if bool_field in new_row and new_row[bool_field] is not None:
                        new_row[bool_field] = bool(new_row[bool_field])
            
            elif table == 'categories':
                # Converter booleanos
                if 'active' in new_row and new_row['active'] is not None:
                    new_row['active'] = bool(new_row['active'])
            
            # Validações gerais para todos os registros
            for key, value in list(new_row.items()):
                # Remover campos que podem causar problemas
                if key in ['updated_at'] and value is None:
                    new_row[key] = time.strftime('%Y-%m-%d %H:%M:%S')
                
                # Converter tipos não serializáveis
                if not is_json_serializable(value):
                    new_row[key] = convert_to_serializable(value)
            
            transformed[table].append(new_row)
    
    return transformed

def load_to_supabase(supabase, transformed_data):
    """Carrega os dados transformados no Supabase, tabela por tabela"""
    results = {}
    migration_order = [
        'settings',    # Começar com configurações
        'users',       # Usuários antes de conteúdo relacionado a usuários
        'categories',  # Categorias antes de transações
        'transactions', # Transações
        'goals',       # Metas
        'reminders',   # Tabelas relacionadas
        'user_settings'
    ]
    
    # Reordenar as tabelas na ordem de migração
    ordered_tables = []
    for table in migration_order:
        if table in transformed_data:
            ordered_tables.append(table)
    
    # Adicionar qualquer tabela restante que não esteja na ordem de migração
    for table in transformed_data:
        if table not in ordered_tables:
            ordered_tables.append(table)
    
    # Migrar cada tabela
    progress = st.progress(0)
    status = st.empty()
    
    for idx, table in enumerate(ordered_tables):
        rows = transformed_data[table]
        if not rows:
            status.info(f"Tabela {table} vazia, pulando...")
            results[table] = {"success": True, "message": "Tabela vazia"}
            continue
        
        status.info(f"Migrando tabela {table} ({len(rows)} registros)...")
        
        try:
            # Limpar tabela existente
            try:
                supabase.table(table).delete().neq("id", 0).execute()
            except Exception as e:
                status.warning(f"Aviso ao limpar tabela {table}: {str(e)}")
            
            # Dividir em lotes para evitar problemas com muitos registros
            batch_size = 20
            success = True
            error_msg = None
            
            for i in range(0, len(rows), batch_size):
                batch = rows[i:min(i+batch_size, len(rows))]
                
                try:
                    # Inserir os dados
                    response = supabase.table(table).insert(batch).execute()
                    
                    if hasattr(response, 'error') and response.error:
                        raise Exception(f"Erro na resposta: {response.error}")
                    
                except Exception as e:
                    status.error(f"Erro ao inserir lote na tabela {table}: {str(e)}")
                    # Tentar inserir um por um para identificar registros problemáticos
                    for item in batch:
                        try:
                            supabase.table(table).insert(item).execute()
                        except Exception as item_e:
                            status.error(f"Erro no registro {item.get('id', 'desconhecido')}: {str(item_e)}")
                            success = False
                            error_msg = str(item_e)
            
            if success:
                status.success(f"✅ Tabela {table} migrada com sucesso")
            else:
                status.warning(f"⚠️ Tabela {table} migrada com alguns erros: {error_msg}")
                
            results[table] = {"success": success, "message": error_msg or "Sucesso"}
        
        except Exception as e:
            status.error(f"❌ Erro ao migrar tabela {table}: {str(e)}")
            st.error(traceback.format_exc())
            results[table] = {"success": False, "message": str(e)}
        
        # Atualizar barra de progresso
        progress.progress((idx + 1) / len(ordered_tables))
    
    return results

def show_robust_migration():
    st.title("Migração Robusta SQLite → Supabase")
    
    # Configuração inicial
    st.info("""
    ### Migração Completa e Robusta
    
    Esta ferramenta realizará uma migração controlada e robusta dos seus dados do SQLite para o Supabase.
    O processo seguirá estas etapas:
    
    1. Extração de todos os dados do SQLite
    2. Transformação para resolver incompatibilidades
    3. Carregamento no Supabase tabela por tabela
    
    **Atenção**: Dados existentes no Supabase serão substituídos.
    """)
    
    # Verificar Supabase
    supabase = init_supabase()
    if not supabase:
        st.error("Não foi possível conectar ao Supabase. Verifique suas credenciais.")
        return
    
    # Formulário de configuração
    with st.form("migration_config"):
        st.subheader("Configurações da Migração")
        
        sqlite_path = st.text_input("Caminho do banco SQLite", value="financas.db")
        
        backup_data = st.checkbox("Fazer backup dos dados antes de migrar", value=True, 
                                help="Salva um arquivo JSON com todos os dados antes da migração")
        
        submitted = st.form_submit_button("Iniciar Migração Robusta")
    
    if submitted:
        # Contêiner para o processo
        with st.container():
            st.subheader("Processo de Migração")
            
            # Etapa 1: Extração
            with st.spinner("Extraindo dados do SQLite..."):
                extracted_data = extract_sqlite_data(sqlite_path)
                
                if extracted_data is None:
                    st.error("Falha na extração de dados. Verifique o caminho do banco SQLite.")
                    return
                
                tables_info = {table: len(rows) for table, rows in extracted_data.items()}
                st.success(f"✅ Extração concluída. Tabelas encontradas: {tables_info}")
                
                # Backup opcional
                if backup_data:
                    backup_file = f"backup_sqlite_{time.strftime('%Y%m%d_%H%M%S')}.json"
                    
                    # Converter para formato serializável
                    serializable_data = convert_to_serializable(extracted_data)
                    
                    with open(backup_file, "w") as f:
                        json.dump(serializable_data, f)
                    st.info(f"📁 Backup salvo em: {backup_file}")
            
            # Etapa 2: Transformação
            with st.spinner("Transformando dados..."):
                transformed_data = transform_data(extracted_data)
                st.success("✅ Transformação concluída.")
            
            # Etapa 3: Carregamento
            st.subheader("Carregando dados no Supabase")
            results = load_to_supabase(supabase, transformed_data)
            
            # Resumo
            success_count = sum(1 for result in results.values() if result["success"])
            total_tables = len(results)
            
            if success_count == total_tables:
                st.success(f"🎉 Migração concluída com sucesso! {success_count}/{total_tables} tabelas migradas.")
            else:
                st.warning(f"⚠️ Migração concluída com avisos. {success_count}/{total_tables} tabelas migradas com sucesso.")
            
            # Mostrar detalhes
            with st.expander("Ver detalhes da migração"):
                for table, result in results.items():
                    status = "✅" if result["success"] else "❌"
                    st.write(f"{status} **{table}**: {result['message']}")
            
            # Próximos passos
            st.info("""
            ### Próximos passos
            
            1. Verifique se os dados foram migrados corretamente no Supabase
            2. Execute seu aplicativo normalmente - ele agora usará o Supabase automaticamente
            3. Atualize suas configurações no Streamlit Cloud para usar o Supabase
            """)

if __name__ == "__main__":
    show_robust_migration()
