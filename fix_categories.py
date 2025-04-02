"""
Script para corrigir as categorias e tipos de categoria das transações existentes.
"""
from categories import recategorize_transactions
from supabase_db import init_supabase

def main():
    print("Iniciando correção de categorias das transações...")
    
    # Inicializar conexão com Supabase
    supabase = init_supabase()
    if not supabase:
        print("Erro: Não foi possível conectar ao Supabase")
        return
    
    # Recategorizar todas as transações
    print("Atualizando categorias das transações...")
    recategorize_transactions()
    print("Processo de atualização concluído!")

if __name__ == "__main__":
    main()
