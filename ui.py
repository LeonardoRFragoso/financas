import streamlit as st
from transactions_db import add_transaction, view_transactions, delete_transaction, update_transaction
from goals import add_goal, view_goals, delete_goal
from categories import get_categories
import pandas as pd
from datetime import datetime
from theme_manager import init_theme_manager, theme_config_section, get_theme_colors, style_dataframe

def create_transaction_form():
    """Cria o formulário para adicionar uma nova transação"""
    # Inicializa o tipo de transação no session state se não existir
    if 'transaction_type' not in st.session_state:
        st.session_state.transaction_type = "Despesa"
    
    # Seleciona o tipo fora do formulário
    type_trans = st.selectbox(
        "Tipo",
        ["Despesa", "Receita", "Investimento"],
        key="type_select"
    )
    st.session_state.transaction_type = type_trans
    
    with st.form(key='transaction_form'):
        st.subheader("Nova Transação")
        
        col1, col2 = st.columns(2)
        with col1:
            description = st.text_input("Descrição")
            amount = st.number_input("Valor", min_value=0.0, format="%.2f")
            
            # Busca categorias filtradas pelo tipo atual
            categoria_tipo = "outros"  # valor padrão inicial
            categoria_tipo_map = {}
            
            if st.session_state.transaction_type == "Despesa":
                categories = get_categories(type_filter="Despesa")
                if not categories:
                    category_names = ["Alimentação", "Moradia", "Transporte", "Outros"]
                    categoria_tipo = "necessidade"
                else:
                    category_names = [cat.get("name", "Outros") for cat in categories]
                    categoria_tipo_map = {cat.get("name"): cat.get("categoria_tipo", "outros") for cat in categories}
            elif st.session_state.transaction_type == "Receita":
                categories = get_categories(type_filter="Receita")
                if not categories:
                    category_names = ["Salário", "Freelancer", "Investimentos", "Outros"]
                    categoria_tipo = "receita"
                else:
                    category_names = [cat.get("name", "Outros") for cat in categories]
                    categoria_tipo_map = {cat.get("name"): cat.get("categoria_tipo", "outros") for cat in categories}
            else:  # Investimento
                categories = get_categories(type_filter="Investimento")
                if not categories:
                    category_names = ["Poupança", "Renda Fixa", "Fundos Imobiliários", "Ações", "Tesouro Direto", "CDB", "Fundos", "Outros"]
                    categoria_tipo = "investimento"
                else:
                    category_names = [cat.get("name", "Outros") for cat in categories]
                    categoria_tipo_map = {cat.get("name"): cat.get("categoria_tipo", "investimento") for cat in categories}
            
            category = st.selectbox("Categoria", category_names)
            # Pegar o tipo da categoria do mapa ou usar o valor padrão
            categoria_tipo = categoria_tipo_map.get(category, categoria_tipo)
        
        with col2:
            date = st.date_input("Data")
            due_date = st.date_input("Data de Vencimento")
            status = st.selectbox("Status", ["pendente", "pago", "atrasado"])
        
        st.markdown("### Opções Avançadas")
        col1, col2 = st.columns(2)
        with col1:
            # Mostrar opções avançadas apenas para despesas
            if st.session_state.transaction_type == "Despesa":
                recurring = st.checkbox("Transação Recorrente")
                fixed_expense = st.checkbox("Despesa Fixa")
            else:
                recurring = False
                fixed_expense = False
        
        with col2:
            if st.session_state.transaction_type == "Despesa":
                priority = st.select_slider("Prioridade", options=[1, 2, 3], value=2,
                                      format_func=lambda x: {1: "Baixa", 2: "Média", 3: "Alta"}[x])
                installments = st.number_input("Número de Parcelas", min_value=1, value=1)
            else:
                priority = 1
                installments = 1
        
        col1, col2 = st.columns(2)
        with col1:
            submit_button = st.form_submit_button(label='Adicionar')
        with col2:
            pass
        
        if submit_button:
            add_transaction(
                description=description, 
                amount=amount,
                category=category,
                date=date.strftime("%Y-%m-%d"),
                type_trans=type_trans,
                due_date=due_date.strftime("%Y-%m-%d"),
                status=status,
                recurring=recurring,
                priority=priority,
                fixed_expense=fixed_expense,
                installments=installments,
                categoria_tipo=categoria_tipo
            )
            st.success("Transação adicionada com sucesso!")
            st.rerun()

def create_goal_form():
    """Formulário para adicionar uma nova meta"""
    with st.form(key='goal_form'):
        description = st.text_input("Descrição da Meta")
        target_amount = st.number_input("Valor Alvo", min_value=0.0, format="%.2f")
        current_amount = st.number_input("Valor Atual", min_value=0.0, format="%.2f")
        deadline = st.date_input("Prazo")
        category = st.text_input("Categoria")
        submit_button = st.form_submit_button(label='Adicionar Meta')
        if submit_button:
            add_goal(description, target_amount, deadline.strftime("%Y-%m-%d"), category)
            st.success("Meta adicionada com sucesso!")

def display_transactions(transactions):
    """Exibe a lista de transações em formato de tabela compacta com visualização por abas"""
    if not transactions:
        st.info("Nenhuma transação registrada ainda.")
        return

    # Inicializar dados
    theme_colors = get_theme_colors()
    
    # Converter para DataFrame para facilitar manipulação
    df = pd.DataFrame(transactions)
    
    # Garantir que todas as colunas esperadas existam
    expected_columns = [
        'id', 'user_id', 'description', 'amount', 'category', 'date',
        'due_date', 'type', 'status', 'recurring', 'priority',
        'quinzena', 'installments', 'current_installment',
        'fixed_expense', 'categoria_tipo', 'created_at'
    ]
    
    for col in expected_columns:
        if col not in df.columns:
            df[col] = None
    
    # Converter datas para formato mais amigável
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%d/%m/%Y')
        df['due_date'] = pd.to_datetime(df['due_date'], errors='coerce').dt.strftime('%d/%m/%Y')
        
        # Formatar valores monetários
        df['amount'] = df['amount'].apply(lambda x: f"R$ {float(x):.2f}" if pd.notnull(x) else "R$ 0.00")
    
    # Criar subtítulo com contador
    st.subheader(f"📋 Transações ({len(df)} registros)")
    
    # Criar abas para diferentes visualizações
    tab_lista, tab_tabela, tab_mes = st.tabs(["Lista Compacta", "Tabela Detalhada", "Visualização por Mês"])
    
    # Definir faixas de tempo
    hoje = datetime.now().strftime('%Y-%m-%d')
    
    # Função auxiliar para aplicar filtros
    def aplicar_filtros(dataframe, prefix="lista"):
        df_filtrado = dataframe.copy()
        
        # Container para filtros
        with st.container():
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Filtro por tipo de transação
                tipos_transacao = ['Todos', 'Receita', 'Despesa', 'Investimento']
                tipo_filtro = st.selectbox("Tipo de Transação", tipos_transacao, key=f"{prefix}_tipo_filtro")
            
            with col2:
                # Filtro por categoria
                categorias = ['Todas'] + sorted(df['category'].dropna().unique().tolist())
                categoria_filtro = st.selectbox("Categoria", categorias, key=f"{prefix}_categoria_filtro")
            
            with col3:
                # Ordenação
                ordem_opcoes = ['Data (mais recente)', 'Data (mais antiga)', 'Valor (maior)', 'Valor (menor)', 'Descrição (A-Z)']
                ordem = st.selectbox("Ordenar por", ordem_opcoes, key=f"{prefix}_ordem_transacoes")
        
        # Filtrar dados conforme seleção
        if tipo_filtro != 'Todos':
            df_filtrado = df_filtrado[df_filtrado['type'] == tipo_filtro]
        
        if categoria_filtro != 'Todas':
            df_filtrado = df_filtrado[df_filtrado['category'] == categoria_filtro]
        
        # Ordenar dados
        if ordem == 'Data (mais recente)':
            df_filtrado['date_temp'] = pd.to_datetime(df_filtrado['date'], format='%d/%m/%Y', errors='coerce')
            df_filtrado = df_filtrado.sort_values('date_temp', ascending=False)
        elif ordem == 'Data (mais antiga)':
            df_filtrado['date_temp'] = pd.to_datetime(df_filtrado['date'], format='%d/%m/%Y', errors='coerce')
            df_filtrado = df_filtrado.sort_values('date_temp', ascending=True)
        elif ordem == 'Valor (maior)':
            df_filtrado['amount_num'] = df_filtrado['amount'].str.replace('R$ ', '').str.replace(',', '.').astype(float)
            df_filtrado = df_filtrado.sort_values('amount_num', ascending=False)
        elif ordem == 'Valor (menor)':
            df_filtrado['amount_num'] = df_filtrado['amount'].str.replace('R$ ', '').str.replace(',', '.').astype(float)
            df_filtrado = df_filtrado.sort_values('amount_num', ascending=True)
        elif ordem == 'Descrição (A-Z)':
            df_filtrado = df_filtrado.sort_values('description')
            
        return df_filtrado
    
    # Configurar paginação 
    if 'pagina_atual' not in st.session_state:
        st.session_state.pagina_atual = 1
        
    if 'pagina_atual_tabela' not in st.session_state:
        st.session_state.pagina_atual_tabela = 1
    
    # 1. ABA DE LISTA COMPACTA
    with tab_lista:
        df_filtrado = aplicar_filtros(df, prefix="lista")
        
        # Configurar paginação para essa aba
        itens_por_pagina = 15  # Aumentado para mostrar mais itens na visualização compacta
        num_paginas = max(1, (len(df_filtrado) + itens_por_pagina - 1) // itens_por_pagina)
        
        if not df_filtrado.empty:
            # Dividir em páginas
            inicio = (st.session_state.pagina_atual - 1) * itens_por_pagina
            fim = min(inicio + itens_por_pagina, len(df_filtrado))
            
            df_pagina = df_filtrado.iloc[inicio:fim].copy()
            
            # Definir cores para os tipos de transações
            cores_tipo = {
                'Receita': theme_colors['revenue_color'],
                'Despesa': theme_colors['expense_color'],
                'Investimento': theme_colors['investment_color']
            }
            
            # Definir ícones para os tipos de transações
            icones_tipo = {
                'Receita': '💰',
                'Despesa': '💸',
                'Investimento': '📈'
            }
            
            # Definir ícones para status
            icones_status = {
                'pago': '✅',
                'pendente': '⏳',
                'atrasado': '🔴'
            }
            
            # Criar uma tabela compacta com elementos visuais
            for i, transaction in df_pagina.iterrows():
                tipo = transaction['type']
                status = transaction['status'] if transaction['status'] else 'pendente'
                cor_borda = cores_tipo.get(tipo, '#cccccc')
                icone_tipo = icones_tipo.get(tipo, '🔄')
                icone_status = icones_status.get(status, '❓')
                
                # Usar colunas para criar uma visualização mais compacta
                with st.container(border=True):
                    cols = st.columns([0.15, 0.4, 0.25, 0.2])
                    
                    with cols[0]:
                        st.markdown(f"<h3 style='margin:0'>{icone_tipo}</h3>", unsafe_allow_html=True)
                        st.caption(transaction['date'])
                    
                    with cols[1]:
                        st.markdown(f"**{transaction['description']}**")
                        st.caption(f"{transaction['category']} {icone_status}")
                    
                    with cols[2]:
                        valor_formatado = transaction['amount']
                        st.markdown(f"<h4 style='color:{cor_borda};margin:0'>{valor_formatado}</h4>", unsafe_allow_html=True)
                    
                    with cols[3]:
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("✏️", key=f"edit_{transaction['id']}"):
                                st.session_state['show_edit_form'] = True
                                st.session_state['editing_transaction'] = transaction
                                st.rerun()
                        
                        with col_btn2:
                            if st.button("🗑️", key=f"delete_{transaction['id']}"):
                                if st.session_state.get(f"confirm_delete_{transaction['id']}", False):
                                    delete_transaction(transaction['id'])
                                    st.success("Transação excluída com sucesso!")
                                    st.rerun()
                                else:
                                    st.session_state[f"confirm_delete_{transaction['id']}"] = True
                                    st.warning("Clique novamente para confirmar a exclusão.")
                    
            # Navegação de paginação
            if num_paginas > 1:
                col1, col2, col3 = st.columns([1, 3, 1])
                
                with col2:
                    pagination_container = st.container()
                    paginas_cols = pagination_container.columns(min(num_paginas, 10) + 2)
                    
                    # Botão anterior
                    if paginas_cols[0].button("◀️", key="prev_page", disabled=st.session_state.pagina_atual == 1):
                        st.session_state.pagina_atual = max(1, st.session_state.pagina_atual - 1)
                        st.rerun()
                    
                    # Botões de número das páginas
                    max_visible_pages = min(num_paginas, 10)
                    page_start = max(1, min(st.session_state.pagina_atual - max_visible_pages // 2, num_paginas - max_visible_pages + 1))
                    
                    for p_idx, p in enumerate(range(page_start, page_start + max_visible_pages)):
                        if p <= num_paginas:
                            if paginas_cols[p_idx + 1].button(
                                f"{p}", 
                                key=f"page_{p}",
                                type="primary" if p == st.session_state.pagina_atual else "secondary"
                            ):
                                st.session_state.pagina_atual = p
                                st.rerun()
                    
                    # Botão próximo
                    if paginas_cols[-1].button("▶️", key="next_page", disabled=st.session_state.pagina_atual == num_paginas):
                        st.session_state.pagina_atual = min(num_paginas, st.session_state.pagina_atual + 1)
                        st.rerun()
        else:
            st.info("Nenhuma transação encontrada com os filtros selecionados.")
    
    # 2. ABA DE TABELA DETALHADA
    with tab_tabela:
        df_filtrado_tabela = aplicar_filtros(df, prefix="tabela")
        
        if not df_filtrado_tabela.empty:
            # Preparar DataFrame para exibição
            display_df = df_filtrado_tabela.copy()
            
            # Selecionar apenas colunas relevantes para exibição
            cols_exibir = ['description', 'amount', 'category', 'date', 'status', 'type']
            display_df = display_df[cols_exibir].copy()
            
            # Renomear colunas para português
            colunas_renomeadas = {
                'description': 'Descrição',
                'amount': 'Valor',
                'category': 'Categoria',
                'date': 'Data',
                'status': 'Status',
                'type': 'Tipo'
            }
            display_df = display_df.rename(columns=colunas_renomeadas)
            
            # Aplicar estilo e exibir a tabela
            st.dataframe(
                display_df,
                use_container_width=True,
                column_config={
                    "Valor": st.column_config.NumberColumn(
                        format="R$ %.2f",
                    ),
                    "Tipo": st.column_config.SelectboxColumn(
                        options=["Receita", "Despesa", "Investimento"],
                        width="medium"
                    ),
                    "Status": st.column_config.SelectboxColumn(
                        options=["pago", "pendente", "atrasado"],
                        width="medium"
                    ),
                },
                hide_index=True
            )
        else:
            st.info("Nenhuma transação encontrada com os filtros selecionados.")
    
    # 3. ABA DE VISUALIZAÇÃO POR MÊS
    with tab_mes:
        df_filtrado_mes = aplicar_filtros(df, prefix="mes")
        
        # Agrupar transações por mês
        if not df_filtrado_mes.empty:
            # Converter data para datetime para poder agrupar
            df_filtrado_mes['date'] = pd.to_datetime(df_filtrado_mes['date'], errors='coerce')
            
            # Extrair ano e mês
            df_filtrado_mes['ano_mes'] = df_filtrado_mes['date'].dt.strftime('%Y-%m')
            
            # Agrupar por ano-mês
            meses_distintos = sorted(df_filtrado_mes['ano_mes'].unique(), reverse=True)
            
            if meses_distintos:
                # Criar acordeão para cada mês
                for mes in meses_distintos:
                    try:
                        # Converter para um formato mais legível
                        data_obj = datetime.strptime(mes, '%Y-%m')
                        mes_nome = data_obj.strftime('%B %Y').capitalize()
                    except:
                        mes_nome = mes
                    
                    # Filtrar transações deste mês
                    df_mes = df_filtrado_mes[df_filtrado_mes['ano_mes'] == mes].copy()
                    
                    # Calcular totais para este mês
                    receitas = df_mes[df_mes['type'] == 'Receita']['amount'].str.replace('R$ ', '').str.replace(',', '.').astype(float).sum()
                    despesas = df_mes[df_mes['type'] == 'Despesa']['amount'].str.replace('R$ ', '').str.replace(',', '.').astype(float).sum()
                    investimentos = df_mes[df_mes['type'] == 'Investimento']['amount'].str.replace('R$ ', '').str.replace(',', '.').astype(float).sum()
                    saldo = receitas - despesas - investimentos
                    
                    # Criar um expander para cada mês com resumo
                    with st.expander(f"📅 {mes_nome} - Saldo: R$ {saldo:.2f}"):
                        # Mostrar resumo do mês
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Receitas", f"R$ {receitas:.2f}")
                        col2.metric("Despesas", f"R$ {despesas:.2f}")
                        col3.metric("Investimentos", f"R$ {investimentos:.2f}")
                        
                        # Mostrar tabela com transações do mês
                        display_cols = ['description', 'amount', 'category', 'date', 'type']
                        display_df_mes = df_mes[display_cols].copy()
                        
                        # Renomear colunas
                        colunas_renomeadas = {
                            'description': 'Descrição',
                            'amount': 'Valor',
                            'category': 'Categoria',
                            'date': 'Data',
                            'type': 'Tipo'
                        }
                        display_df_mes = display_df_mes.rename(columns=colunas_renomeadas)
                        
                        # Exibir tabela compacta
                        st.dataframe(
                            display_df_mes,
                            use_container_width=True,
                            hide_index=True
                        )
            else:
                st.info("Não foi possível agrupar transações por mês.")
        else:
            st.info("Nenhuma transação encontrada para visualização por mês.")
    
    # Formulário de edição
    if st.session_state.get('show_edit_form', False):
        transaction = st.session_state['editing_transaction']
        
        with st.form(key=f"edit_form_{transaction['id']}"):
            st.subheader("Editar Transação")
            
            col1, col2 = st.columns(2)
            with col1:
                # Remover "R$ " para obter valor numérico
                amount_str = transaction['amount'].replace('R$ ', '') if isinstance(transaction['amount'], str) else '0.00'
                amount_str = amount_str.replace(',', '.')
                
                description = st.text_input("Descrição", value=transaction['description'])
                amount = st.number_input("Valor", value=float(amount_str), format="%.2f")
                
                # Busca categorias filtradas pelo tipo atual
                categoria_tipo = "outros"  # valor padrão inicial
                categoria_tipo_map = {}
                
                # Verifica o tipo de transação real na base de dados (não a string que pode estar incorreta)
                transaction_type = str(transaction['type']).lower()
                
                # Determinar o tipo correto de transação para buscar as categorias apropriadas
                if "expense" in transaction_type or "despesa" in transaction_type:
                    transaction_display_type = "Despesa"
                elif "income" in transaction_type or "receita" in transaction_type:
                    transaction_display_type = "Receita"
                elif "investment" in transaction_type or "investimento" in transaction_type:
                    transaction_display_type = "Investimento"
                else:
                    # Fallback para o tipo original se não conseguir determinar
                    transaction_display_type = transaction['type']
                
                # Obtém as cores do tema atual
                theme_colors = get_theme_colors()
                
                # Verificar se o tipo de transação pode ser alterado também durante a edição
                tipo_anterior = transaction_display_type
                
                # Estilizar o seletor de tipo com cores correspondentes ao tipo
                tipo_color_map = {
                    "Despesa": theme_colors['expense_color'],
                    "Receita": theme_colors['revenue_color'],
                    "Investimento": theme_colors['investment_color']
                }
                
                st.markdown(f"""
                <style>
                div[data-testid="stSelectbox"] .st-emotion-cache-1aehpvj {{
                    font-weight: bold;
                }}
                </style>
                """, unsafe_allow_html=True)
                
                novo_tipo = st.selectbox(
                    "Tipo de Transação",
                    ["Despesa", "Receita", "Investimento"],
                    index=["Despesa", "Receita", "Investimento"].index(tipo_anterior) if tipo_anterior in ["Despesa", "Receita", "Investimento"] else 0,
                    key=f"edit_type_{transaction['id']}"
                )
                
                # Se o tipo mudou, recarregar as categorias apropriadas
                if novo_tipo != tipo_anterior:
                    st.session_state[f'tipo_alterado_{transaction["id"]}'] = True
                    st.session_state[f'novo_tipo_{transaction["id"]}'] = novo_tipo
                    st.rerun()
                
                if novo_tipo == "Despesa":
                    categories = get_categories(type_filter="Despesa")
                    if not categories:
                        category_names = ["Alimentação", "Moradia", "Transporte", "Outros"]
                        categoria_tipo = "necessidade"
                    else:
                        category_names = [cat.get("name", "Outros") for cat in categories]
                        categoria_tipo_map = {cat.get("name"): cat.get("categoria_tipo", "outros") for cat in categories}
                elif novo_tipo == "Receita":
                    categories = get_categories(type_filter="Receita")
                    if not categories:
                        category_names = ["Salário", "Freelancer", "Investimentos", "Outros"]
                        categoria_tipo = "receita"
                    else:
                        category_names = [cat.get("name", "Outros") for cat in categories]
                        categoria_tipo_map = {cat.get("name"): cat.get("categoria_tipo", "outros") for cat in categories}
                else:  # Investimento
                    categories = get_categories(type_filter="Investimento")
                    if not categories:
                        category_names = ["Poupança", "Renda Fixa", "Fundos Imobiliários", "Ações", "Tesouro Direto", "CDB", "Fundos", "Outros"]
                        categoria_tipo = "investimento"
                    else:
                        category_names = [cat.get("name", "Outros") for cat in categories]
                        categoria_tipo_map = {cat.get("name"): cat.get("categoria_tipo", "investimento") for cat in categories}
                
                category = st.selectbox("Categoria", category_names, 
                                      index=category_names.index(transaction['category']) if transaction['category'] in category_names else 0)
                categoria_tipo = categoria_tipo_map.get(category, categoria_tipo)
            
            with col2:
                try:
                    date_value = pd.to_datetime(transaction['date'], format='%d/%m/%Y')
                except:
                    date_value = datetime.now()
                    
                try:
                    due_date_value = pd.to_datetime(transaction['due_date'], format='%d/%m/%Y')
                except:
                    due_date_value = datetime.now()
                
                date = st.date_input("Data", value=date_value)
                due_date = st.date_input("Data de Vencimento", value=due_date_value)
                status = st.selectbox("Status", ["pendente", "pago", "atrasado"], 
                                    index=["pendente", "pago", "atrasado"].index(transaction['status']) if transaction['status'] in ["pendente", "pago", "atrasado"] else 0)
            
            st.markdown("### Opções Avançadas")
            col1, col2 = st.columns(2)
            with col1:
                recurring = st.checkbox("Transação Recorrente", value=bool(transaction['recurring']))
                fixed_expense = st.checkbox("Despesa Fixa", value=bool(transaction['fixed_expense']))
            
            with col2:
                priority = st.select_slider("Prioridade", options=[1, 2, 3],
                                      value=int(transaction['priority']) if transaction['priority'] in [1, 2, 3] else 2,
                                      format_func=lambda x: {1: "Baixa", 2: "Média", 3: "Alta"}[x])
                installments = st.number_input("Número de Parcelas", min_value=1, value=int(transaction['installments']) if transaction['installments'] else 1)
            
            col1, col2 = st.columns(2)
            with col1:
                submit_button = st.form_submit_button(label='Salvar Alterações')
            with col2:
                cancel_button = st.form_submit_button(label='Cancelar')
            
            if submit_button:
                update_transaction(
                    transaction_id=transaction['id'],
                    description=description,
                    amount=amount,
                    category=category,
                    date=date.strftime("%Y-%m-%d"),
                    type_trans=novo_tipo,
                    due_date=due_date.strftime("%Y-%m-%d"),
                    status=status,
                    recurring=recurring,
                    priority=priority,
                    fixed_expense=fixed_expense,
                    installments=installments,
                    categoria_tipo=categoria_tipo
                )
                st.success("Transação atualizada com sucesso!")
                st.session_state['show_edit_form'] = False
                st.rerun()
            
            if cancel_button:
                st.session_state['show_edit_form'] = False
                st.rerun()

def display_goals(goals):
    """Exibe a lista de metas em uma tabela formatada"""
    if not goals:
        st.info("Nenhuma meta cadastrada ainda.")
        return

    # Converter dados para formato de exibição consistente
    formatted_goals = []
    for goal in goals:
        formatted_goals.append({
            'ID': goal.get('id', ''),
            'User': goal.get('user_id', ''),
            'Descrição': goal.get('description', 'Sem descrição'),
            'Valor Alvo': f"R$ {float(goal.get('target_amount', 0)):,.2f}",
            'Valor Atual': f"R$ {float(goal.get('current_amount', 0)):,.2f}",
            'Prazo': goal.get('deadline', ''),
            'Categoria': goal.get('category', 'Sem categoria'),
            'Data Criação': goal.get('created_at', '')
        })
    
    # Criar DataFrame com as metas formatadas
    df = pd.DataFrame(formatted_goals)
    
    # Aplicar estilo consistente com o tema atual
    theme_colors = get_theme_colors()
    styled_df = style_dataframe(df)
    
    st.dataframe(styled_df, use_container_width=True)

    # Opção para deletar
    with st.expander("Gerenciar Metas"):
        col1, col2 = st.columns(2)
        with col1:
            goal_to_delete = st.number_input("ID da Meta para Excluir", min_value=1)
        with col2:
            if st.button("Excluir Meta"):
                from goals import delete_goal
                delete_goal(goal_to_delete)
                st.success(f"Meta ID {goal_to_delete} excluída!")
                st.rerun()

def show_transactions_page():
    """Página de gerenciamento de transações"""
    st.title("Gerenciamento de Transações")
    
    # Inicializar o gerenciador de tema
    init_theme_manager()
    
    # Mostrar configuração de tema
    theme_config_section()
    
    # Formulário para adicionar transações e exibir as existentes
    create_transaction_form()
    
    # Buscar transações existentes
    transactions = view_transactions()
    
    # Exibir transações
    if transactions:
        display_transactions(transactions)
    else:
        st.info("Nenhuma transação cadastrada.")

def show_goals_page():
    """Página de gerenciamento de metas financeiras"""
    st.title("Metas Financeiras")
    
    # Inicializar o gerenciador de tema
    init_theme_manager()
    
    # Mostrar configuração de tema
    theme_config_section()
    
    # Formulário para adicionar metas
    create_goal_form()
    
    # Buscar metas existentes
    goals = view_goals()
    
    # Exibir metas
    if goals:
        display_goals(goals)
    else:
        st.info("Nenhuma meta cadastrada.")
