import streamlit as st
import sqlite3
import pandas as pd
from supabase import create_client

st.set_page_config(page_title="Migração Final - Tabelas Restantes", layout="wide")

def init_supabase():
    """Inicializa o cliente Supabase"""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao conectar com Supabase: {e}")
        return None

def get_sqlite_data(table_name, db_path="financas.db"):
    """Obtém os dados de uma tabela específica do SQLite"""
    try:
        conn = sqlite3.connect(db_path)
        # Usar pandas para facilitar a visualização
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro ao ler tabela {table_name}: {str(e)}")
        return None

def migrate_table(supabase, table_name, db_path="financas.db"):
    """Migra uma tabela específica do SQLite para o Supabase"""
    # Obter dados do SQLite
    df = get_sqlite_data(table_name, db_path)
    if df is None or df.empty:
        st.warning(f"Nenhum dado encontrado na tabela {table_name}")
        return False
    
    # Mostrar dados
    st.write(f"Dados da tabela {table_name}:")
    st.dataframe(df)
    
    # Converter para formato que o Supabase espera
    records = df.to_dict(orient='records')
    
    # Processar os dados
    processed_records = []
    for record in records:
        # Fazer uma cópia do registro
        new_record = {}
        
        # Processar cada campo
        for key, value in record.items():
            # Lidar com valores NULL
            if pd.isna(value):
                if key in ['title', 'description', 'category', 'status', 'settings']:
                    new_record[key] = ''
                elif key in ['current_amount', 'target_amount']:
                    new_record[key] = 0.0
                elif key in ['user_id', 'transaction_id']:
                    new_record[key] = 1
                else:
                    new_record[key] = None
            else:
                # Converter explicitamente para o tipo correto baseado na tabela/campo
                if table_name == 'reminders' and key in ['user_id', 'transaction_id']:
                    # Garantir que são inteiros para a tabela reminders
                    new_record[key] = int(float(value)) if isinstance(value, (str, float)) else int(value)
                elif key in ['active', 'recurring', 'fixed_expense'] and isinstance(value, (int, bool)):
                    new_record[key] = bool(value)
                else:
                    new_record[key] = value
        
        # Garantir campos específicos por tabela
        if table_name == 'goals' and 'updated_at' not in new_record:
            new_record['updated_at'] = new_record.get('created_at')
            
        # Para reminders, garantir que ID não seja enviado para permitir geração automática
        if table_name == 'reminders':
            if 'id' in new_record:
                del new_record['id']
                
        processed_records.append(new_record)
    
    # Limpar tabela existente no Supabase
    try:
        supabase.table(table_name).delete().neq('id', 0).execute()
        st.success(f"Tabela {table_name} limpa com sucesso")
    except Exception as e:
        st.warning(f"Aviso ao limpar tabela: {e}")
    
    # Inserir registros um por um para melhor controle de erros
    success_count = 0
    error_count = 0
    
    for i, record in enumerate(processed_records):
        try:
            response = supabase.table(table_name).insert(record).execute()
            success_count += 1
        except Exception as e:
            st.error(f"Erro ao inserir registro {i+1}: {e}")
            st.write("Dados do registro:", record)
            error_count += 1
    
    # Mostrar resumo
    if error_count == 0:
        st.success(f"✅ Todos os {success_count} registros migrados com sucesso!")
        return True
    else:
        st.warning(f"⚠️ Migração com avisos: {success_count} sucesso, {error_count} erros")
        return False

def main():
    st.title("Migração de Tabelas Restantes")
    
    st.markdown("""
    ## Migração de Tabelas Pendentes
    
    Esta ferramenta completa a migração, focando nas tabelas que ainda não foram migradas com sucesso.
    
    ### Importante:
    Antes de continuar, certifique-se de que você:
    1. Criou as tabelas manualmente no SQL Editor do Supabase
    2. Verificou que as tabelas foram criadas corretamente
    """)
    
    # Verificar conexão com Supabase
    supabase = init_supabase()
    if not supabase:
        st.error("❌ Falha ao conectar ao Supabase")
        return
    
    # Lista de tabelas com problemas
    problem_tables = ["goals", "reminders", "user_settings"]
    
    # Permitir seleção de tabela
    selected_table = st.selectbox("Selecione a tabela para migrar:", problem_tables)
    
    # Caminho do banco SQLite
    db_path = st.text_input("Caminho do banco SQLite:", "financas.db")
    
    # Botão para migrar
    if st.button(f"Migrar Tabela {selected_table}"):
        with st.spinner(f"Migrando tabela {selected_table}..."):
            success = migrate_table(supabase, selected_table, db_path)
    
    # Instruções finais
    st.markdown("""
    ### Próximos Passos
    
    Após migrar todas as tabelas:
    
    1. Execute seu aplicativo principal:
       ```
       streamlit run run.py
       ```
       
    2. Atualize o aplicativo no Streamlit Cloud com suas credenciais do Supabase
    
    3. Desfrute do acesso aos seus dados de qualquer dispositivo!
    """)

if __name__ == "__main__":
    main()
