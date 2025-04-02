import streamlit as st
from transactions_db import view_transactions, update_transaction
import pandas as pd

def main():
    st.title("Atualização de Categorias de Transações")
    
    # Obtém todas as transações
    transactions = view_transactions()
    
    if not transactions:
        st.error("Não foi possível obter as transações do banco de dados.")
        return
    
    # Cria um DataFrame para facilitar o trabalho com os dados
    df = pd.DataFrame(transactions)
    
    # Mapeamento das descrições para as categorias desejadas
    category_updates = {
        "Cartão Magalu": "Contas",
        "Cartão de crédito Santander": "Contas",
        "Empréstimo mãe": "Contas",
        "IAs": "Contas",
        "Internet Celular": "Contas",
        "Cerveja Mãe/Deborah + Massagem": "Lazer",
        "Resumo das contas": "Contas"
    }
    
    # Exibe o DataFrame original
    st.subheader("Transações Originais")
    st.dataframe(
        df[['id', 'description', 'category', 'amount', 'type', 'status']],
        use_container_width=True
    )
    
    # Botão para executar a atualização
    if st.button("Atualizar Categorias"):
        updated_count = 0
        st.subheader("Atualizações:")
        
        # Percorre todas as transações e atualiza as que correspondem ao mapeamento
        for index, row in df.iterrows():
            transaction_id = row['id']
            description = row['description']
            current_category = row['category']
            
            # Verifica se esta transação precisa ser atualizada
            if description in category_updates:
                new_category = category_updates[description]
                
                # Só atualiza se a categoria atual for diferente da desejada
                if current_category != new_category:
                    # Cria um dicionário com todos os campos da transação
                    transaction_data = row.to_dict()
                    # Atualiza a categoria
                    transaction_data['category'] = new_category
                    
                    # Faz a atualização no banco de dados
                    result = update_transaction(transaction_id, transaction_data)
                    
                    if result:
                        updated_count += 1
                        st.success(f"✅ Transação '{description}': Categoria alterada de '{current_category if current_category else 'Não definida'}' para '{new_category}'")
                    else:
                        st.error(f"❌ Erro ao atualizar transação '{description}'")
                else:
                    st.info(f"ℹ️ Transação '{description}' já está com a categoria '{new_category}'")
        
        # Exibe um resumo das atualizações
        if updated_count > 0:
            st.success(f"Total de {updated_count} transações atualizadas com sucesso!")
            st.info("Recarregue o dashboard para ver as mudanças refletidas nos gráficos e tabelas.")
        else:
            st.info("Nenhuma transação precisou ser atualizada.")

if __name__ == "__main__":
    main()
