import streamlit as st
import time
from db import migrate_to_supabase, use_supabase, init_db

def show_migration_tool():
    st.title("Ferramenta de Migração de Dados")
    
    # Verificar se o Supabase está configurado
    if not use_supabase():
        st.error("""
        ### Supabase não configurado!
        
        Para usar esta ferramenta, você precisa configurar as credenciais do Supabase.
        
        1. Adicione as seguintes chaves ao seu arquivo `.streamlit/secrets.toml`:
        ```toml
        SUPABASE_URL = "sua-url-do-projeto"
        SUPABASE_KEY = "sua-chave-anon"
        ```
        
        2. Ou adicione esses secrets nas configurações do seu app no Streamlit Cloud.
        """)
        return
    
    st.info("""
    ### Migração SQLite para Supabase
    
    Esta ferramenta irá migrar todos os seus dados do banco de dados SQLite local para o Supabase.
    
    **Atenção**: A migração pode demorar dependendo da quantidade de dados. 
    Os dados existentes no Supabase NÃO serão apagados, mas podem ocorrer duplicações 
    se você executar a migração mais de uma vez.
    """)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if st.button("Iniciar Migração", type="primary"):
            with st.spinner("Migrando dados para o Supabase..."):
                # Inicializar as tabelas do Supabase primeiro
                init_db()
                
                # Realizar a migração
                success = migrate_to_supabase()
                
                if success:
                    st.success("✅ Migração concluída com sucesso!")
                else:
                    st.error("❌ Ocorreu um erro durante a migração.")
    
    with col2:
        st.info("""
        #### Próximos passos após a migração:
        
        1. Verifique se todos os dados foram migrados corretamente.
        2. Após confirmar que tudo está em ordem, você pode começar a usar exclusivamente o Supabase.
        3. Os dados adicionados via aplicação no Streamlit Cloud serão salvos no Supabase.
        """)
    
    st.divider()
    
    # Informações sobre o uso do banco de dados
    st.subheader("Status do Banco de Dados")
    
    if use_supabase():
        st.success("✅ Usando Supabase como banco de dados principal")
        st.info("""
        Como o Supabase está configurado, todas as operações (consultas, inserções, atualizações) 
        estão sendo direcionadas para o Supabase automaticamente.
        
        Agora você pode acessar seus dados de qualquer dispositivo, incluindo o aplicativo 
        hospedado no Streamlit Cloud.
        """)
    else:
        st.warning("⚠️ Usando SQLite como banco de dados principal")
        st.info("""
        Para começar a usar o Supabase, configure as credenciais conforme instruções acima.
        """)

if __name__ == "__main__":
    show_migration_tool()
