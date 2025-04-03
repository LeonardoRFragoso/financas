import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from openai import OpenAI
from transactions_db import view_transactions
from categories import get_categories
from theme_manager import init_theme_manager, theme_config_section, get_theme_colors
from supabase_db import init_supabase

# Configuração da API OpenAI usando st.secrets
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

class FinanceAssistant:
    """Assistente de finanças usando a API OpenAI para fornecer dicas personalizadas."""
    
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        
    def get_financial_summary(self):
        """Obtém um resumo dos dados financeiros do usuário."""
        try:
            # Obter transações diretamente do Supabase
            supabase = init_supabase()
            if not supabase:
                return {"status": "error", "message": "Erro ao conectar ao banco de dados."}
                
            print("Buscando transações para o assistente financeiro...")
            response = supabase.table("transactions").select("*").limit(100).execute()
            transactions = response.data
            print(f"Total de transações encontradas: {len(transactions)}")
            
            if not transactions:
                return {"status": "empty", "message": "Nenhuma transação encontrada."}
            
            # Exibir IDs das transações para debug
            print(f"IDs das transações: {[t.get('id') for t in transactions]}")
            
            # Converter transações para DataFrame
            df = pd.DataFrame(transactions)
            
            # Filtrar apenas transações pagas
            df = df[df['status'].str.lower().isin(['pago', 'paid'])]
            
            # Calcular receitas e despesas
            receitas = df[df['type'].str.lower().isin(['receita', 'income', 'revenue'])]['amount'].astype(float).sum()
            despesas = df[df['type'].str.lower().isin(['despesa', 'expense', 'expenses'])]['amount'].astype(float).sum()
            investimentos = df[df['type'].str.lower().isin(['investimento', 'investment'])]['amount'].astype(float).sum()
            saldo = receitas - despesas - investimentos
            
            # Obter contas a pagar para os próximos 30 dias
            hoje = datetime.now().date()
            proximo_mes = (hoje + timedelta(days=30)).strftime('%Y-%m-%d')
            hoje_str = hoje.strftime('%Y-%m-%d')
            
            proximas_contas = df[
                (df['type'].str.lower().isin(['despesa', 'expense', 'expenses'])) & 
                (df['status'].str.lower().isin(['pendente', 'pending'])) & 
                (df['due_date'] <= proximo_mes) &
                (df['due_date'] >= hoje_str)
            ].sort_values('due_date')
            
            # Calcular distribuição 50/30/20
            necessidades = df[(df['type'].str.lower().isin(['despesa', 'expense', 'expenses'])) & 
                             (df['categoria_tipo'].str.lower().isin(['necessidade', 'necessidades']))]['amount'].astype(float).sum()
            
            desejos = df[(df['type'].str.lower().isin(['despesa', 'expense', 'expenses'])) & 
                        (df['categoria_tipo'].str.lower().isin(['desejo', 'desejos']))]['amount'].astype(float).sum()
            
            poupanca = df[(df['type'].str.lower().isin(['despesa', 'expense', 'expenses'])) & 
                         (df['categoria_tipo'].str.lower() == 'poupanca')]['amount'].astype(float).sum()
            
            # Adicionar investimentos à poupança
            poupanca += investimentos
            
            # Calcular percentuais
            if receitas > 0:
                perc_necessidades = (necessidades / receitas) * 100
                perc_desejos = (desejos / receitas) * 100
                perc_poupanca = (poupanca / receitas) * 100
            else:
                perc_necessidades = perc_desejos = perc_poupanca = 0
            
            # Preparar dados de contas próximas
            proximas_contas_formatadas = []
            for _, conta in proximas_contas.iterrows():
                proximas_contas_formatadas.append({
                    "description": conta['description'],
                    "amount": float(conta['amount']),
                    "due_date": conta['due_date'],
                    "category": conta.get('category', ''),
                    "priority": int(conta.get('priority', 1))
                })
            
            # Buscar as datas reais dos últimos recebimentos (receitas)
            receitas_df = df[df['type'].str.lower().isin(['receita', 'income', 'revenue'])].sort_values('date', ascending=False)
            ultimos_recebimentos = []
            
            if not receitas_df.empty:
                for _, receita in receitas_df.head(6).iterrows():  # Analisar até 6 recebimentos recentes para identificar padrão
                    try:
                        data_receita = datetime.strptime(receita['date'], '%Y-%m-%d').date()
                        ultimos_recebimentos.append(data_receita)
                    except:
                        pass
            
            # Se temos histórico de recebimentos, usar para calcular próximo pagamento
            proximo_recebimento = None
            if len(ultimos_recebimentos) >= 2:
                # Analisar o padrão de recebimentos do usuário
                dias_recebimento = [data.day for data in ultimos_recebimentos]
                
                # Identificar os dias do mês em que o usuário costuma receber
                dias_comuns = {}
                for dia in dias_recebimento:
                    if dia in dias_comuns:
                        dias_comuns[dia] += 1
                    else:
                        dias_comuns[dia] = 1
                
                # Ordenar os dias de recebimento por frequência
                dias_ordenados = sorted(dias_comuns.items(), key=lambda x: x[1], reverse=True)
                
                hoje = datetime.now().date()
                mes_atual = hoje.month
                ano_atual = hoje.year
                
                # Verificar se há um padrão claro de dias de recebimento
                if dias_ordenados:
                    # Pegar o dia mais comum de recebimento
                    dia_mais_comum = dias_ordenados[0][0]
                    
                    # Verificar se o dia mais comum já passou neste mês
                    if hoje.day >= dia_mais_comum:
                        # Próximo recebimento será no próximo mês
                        if mes_atual == 12:
                            proximo_recebimento = datetime(ano_atual + 1, 1, dia_mais_comum).date()
                        else:
                            proximo_recebimento = datetime(ano_atual, mes_atual + 1, dia_mais_comum).date()
                    else:
                        # Próximo recebimento será ainda neste mês
                        proximo_recebimento = datetime(ano_atual, mes_atual, dia_mais_comum).date()
                    
                    # Se houver um segundo dia comum de recebimento (padrão quinzenal)
                    if len(dias_ordenados) > 1 and dias_ordenados[1][1] > 1:
                        segundo_dia_comum = dias_ordenados[1][0]
                        data_segundo_recebimento = None
                        
                        # Verificar se o segundo dia comum já passou neste mês
                        if hoje.day >= segundo_dia_comum:
                            # Segundo recebimento será no próximo mês
                            if mes_atual == 12:
                                data_segundo_recebimento = datetime(ano_atual + 1, 1, segundo_dia_comum).date()
                            else:
                                data_segundo_recebimento = datetime(ano_atual, mes_atual + 1, segundo_dia_comum).date()
                        else:
                            # Segundo recebimento será ainda neste mês
                            data_segundo_recebimento = datetime(ano_atual, mes_atual, segundo_dia_comum).date()
                        
                        # Escolher a data mais próxima como próximo recebimento
                        if data_segundo_recebimento and (proximo_recebimento is None or data_segundo_recebimento < proximo_recebimento):
                            proximo_recebimento = data_segundo_recebimento
            
            # Se não conseguimos determinar um padrão, usar o último recebimento + 30 dias como estimativa
            if proximo_recebimento is None and ultimos_recebimentos:
                ultimo_recebimento = ultimos_recebimentos[0]  # Data mais recente
                proximo_recebimento = ultimo_recebimento + timedelta(days=30)  # Estimativa de ciclo mensal
            
            # Calcular dias até o próximo recebimento
            dias_ate_proximo_recebimento = None
            if proximo_recebimento:
                dias_ate_proximo_recebimento = (proximo_recebimento - hoje).days
            
            # Resumo
            summary = {
                "status": "success",
                "receitas": float(receitas),
                "despesas": float(despesas),
                "investimentos": float(investimentos),
                "saldo": float(saldo),
                "proximas_contas": proximas_contas_formatadas,
                "distribuicao": {
                    "necessidades": {
                        "valor": float(necessidades),
                        "percentual": float(perc_necessidades),
                        "ideal": 50.0,
                        "diferenca": float(perc_necessidades - 50.0)
                    },
                    "desejos": {
                        "valor": float(desejos),
                        "percentual": float(perc_desejos),
                        "ideal": 30.0,
                        "diferenca": float(perc_desejos - 30.0)
                    },
                    "poupanca": {
                        "valor": float(poupanca),
                        "percentual": float(perc_poupanca),
                        "ideal": 20.0,
                        "diferenca": float(perc_poupanca - 20.0)
                    }
                },
                "quinzena_atual": 1 if hoje.day <= 15 else 2,
                "proximo_pagamento": proximo_recebimento.strftime('%Y-%m-%d') if proximo_recebimento else None,
                "dias_ate_proximo_pagamento": dias_ate_proximo_recebimento
            }
            
            print(f"Resumo financeiro calculado: {json.dumps(summary, default=str)}")
            return summary
            
        except Exception as e:
            import traceback
            print(f"Erro ao obter resumo financeiro: {e}")
            print(traceback.format_exc())
            return {"status": "error", "message": f"Erro ao processar dados: {str(e)}"}
    
    def get_advice(self, query_type=None):
        """
        Obtém conselhos financeiros personalizados com base nos dados financeiros.
        
        Args:
            query_type (str, optional): Tipo específico de conselho 
                ("orçamento", "contas", "poupança", "imprevistos", "geral")
        
        Returns:
            dict: Resposta com o conselho financeiro
        """
        summary = self.get_financial_summary()
        
        if summary["status"] == "empty":
            return {
                "type": "error",
                "message": "Não há dados financeiros suficientes para fornecer conselhos personalizados."
            }
        
        # Construir a mensagem para a API com base no resumo financeiro
        user_message = self._build_user_message(summary, query_type)
        
        try:
            # Fazer a chamada para a API
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            # Extrair e retornar a resposta
            return {
                "type": "success",
                "message": response.choices[0].message.content
            }
            
        except Exception as e:
            return {
                "type": "error",
                "message": f"Erro ao conectar com a API da OpenAI: {str(e)}"
            }
    
    def _get_system_prompt(self):
        """Retorna o prompt do sistema para o assistente financeiro."""
        return """
        Você é um assistente financeiro especializado em finanças pessoais, focado em ajudar o usuário a alcançar seus objetivos financeiros.
        
        Suas principais responsabilidades são:
        1. Analisar a saúde financeira do usuário e fornecer um diagnóstico claro
        2. Ajudar a otimizar o orçamento usando a regra 50/30/20 (50% necessidades, 30% desejos, 20% poupança/investimentos)
        3. Criar estratégias para pagamento de contas considerando o recebimento quinzenal (dias 15 e 30) exceto se cair final de semana, neste caso devemos considerar a ultima sexta feita da quinzena.
        4. Sugerir formas de aumentar a poupança e investimentos
        5. Ajudar a construir uma reserva de emergência
        
        Diretrizes importantes:
        1. Use uma linguagem amigável e acessível, evitando jargões financeiros complexos
        2. Forneça conselhos práticos e específicos baseados nos dados reais do usuário
        3. Priorize a construção de hábitos financeiros saudáveis
        4. Considere o fluxo de caixa quinzenal ao sugerir estratégias de pagamento
        5. Enfatize a importância do equilíbrio entre necessidades, desejos e poupança
        
        Ao analisar os dados:
        1. Compare os percentuais atuais com a regra 50/30/20
        2. Identifique padrões de gastos e oportunidades de economia
        3. Considere a prioridade das contas ao sugerir ordem de pagamento
        4. Avalie se o nível de poupança/investimentos está adequado
        5. Sugira ajustes específicos para melhorar a distribuição do orçamento
        
        Formate suas respostas usando markdown para melhor legibilidade, incluindo:
        - Títulos e subtítulos claros
        - Listas organizadas
        - Destaque para informações importantes
        - Tabelas quando relevante
        - Separação clara entre análise e recomendações
        
        Lembre-se: seu objetivo é ajudar o usuário a desenvolver uma relação saudável com o dinheiro
        e atingir seus objetivos financeiros de forma sustentável.
        """
    
    def _build_user_message(self, summary, query_type):
        """
        Constrói a mensagem para a API com base no resumo financeiro e no tipo de consulta.
        
        Args:
            summary (dict): Resumo financeiro
            query_type (str): Tipo de consulta
        
        Returns:
            str: Mensagem para enviar à API
        """
        hoje = datetime.now().date()
        
        if query_type == "contas":
            return f"""
            Preciso de ajuda para gerenciar minhas próximas contas a pagar. 
            
            Situação financeira atual:
            - Saldo em conta: R$ {summary['saldo']:.2f}
            - Receita mensal: R$ {summary['receitas']:.2f}
            - Despesas mensais: R$ {summary['despesas']:.2f}
            - Investimentos: R$ {summary['investimentos']:.2f}
            
            Informações do recebimento:
            - Quinzena atual: {summary['quinzena_atual']}
            - Próximo pagamento: {summary['proximo_pagamento']} (em {summary['dias_ate_proximo_pagamento']} dias)
            
            Distribuição atual do orçamento:
            - Necessidades: {summary['distribuicao']['necessidades']['percentual']:.1f}% (R$ {summary['distribuicao']['necessidades']['valor']:.2f})
            - Desejos: {summary['distribuicao']['desejos']['percentual']:.1f}% (R$ {summary['distribuicao']['desejos']['valor']:.2f})
            - Poupança/Investimentos: {summary['distribuicao']['poupanca']['percentual']:.1f}% (R$ {summary['distribuicao']['poupanca']['valor']:.2f})
            
            Próximas contas a pagar:
            {self._format_bills_list(summary['proximas_contas'])}
            
            Por favor:
            1. Analise minha capacidade de pagamento atual
            2. Crie uma estratégia detalhada para pagamento das contas considerando:
               - Datas de vencimento
               - Prioridade das contas
               - Data do próximo recebimento
               - Saldo disponível
            3. Identifique quais contas devem ser pagas com o próximo recebimento
            4. Sugira possíveis ajustes no orçamento se necessário
            5. Indique se há risco de não conseguir pagar alguma conta
            
            Formate a resposta de forma clara e organizada, usando markdown para melhor legibilidade.
            """
        
        elif query_type == "orçamento":
            return f"""
            Preciso de uma análise detalhada do meu orçamento atual e recomendações para otimizá-lo.
            
            Situação atual:
            - Receita mensal: R$ {summary['receitas']:.2f}
            - Despesas mensais: R$ {summary['despesas']:.2f}
            - Investimentos: R$ {summary['investimentos']:.2f}
            - Saldo em conta: R$ {summary['saldo']:.2f}
            
            Distribuição atual vs. Regra 50/30/20:
            1. Necessidades:
               - Atual: {summary['distribuicao']['necessidades']['percentual']:.1f}% (R$ {summary['distribuicao']['necessidades']['valor']:.2f})
               - Ideal: 50% (R$ {summary['receitas'] * 0.5:.2f})
               - Diferença: {summary['distribuicao']['necessidades']['diferenca']:.1f}%
            
            2. Desejos:
               - Atual: {summary['distribuicao']['desejos']['percentual']:.1f}% (R$ {summary['distribuicao']['desejos']['valor']:.2f})
               - Ideal: 30% (R$ {summary['receitas'] * 0.3:.2f})
               - Diferença: {summary['distribuicao']['desejos']['diferenca']:.1f}%
            
            3. Poupança/Investimentos:
               - Atual: {summary['distribuicao']['poupanca']['percentual']:.1f}% (R$ {summary['distribuicao']['poupanca']['valor']:.2f})
               - Ideal: 20% (R$ {summary['receitas'] * 0.2:.2f})
               - Diferença: {summary['distribuicao']['poupanca']['diferenca']:.1f}%
            
            Por favor:
            1. Faça uma análise detalhada da distribuição atual do orçamento
            2. Identifique os principais desvios da regra 50/30/20
            3. Sugira ajustes específicos para cada categoria
            4. Proponha um plano gradual para atingir a distribuição ideal
            5. Indique quais gastos podem ser otimizados
            6. Recomende estratégias para aumentar a poupança/investimentos
            
            Formate a resposta de forma clara e organizada, usando markdown para melhor legibilidade.
            """
        
        elif query_type == "poupança":
            return f"""
            Preciso de orientações específicas sobre como melhorar minha poupança e investimentos.
            
            Situação atual:
            - Receita mensal: R$ {summary['receitas']:.2f}
            - Total investido: R$ {summary['investimentos']:.2f}
            - Valor mensal para poupança/investimentos: R$ {summary['distribuicao']['poupanca']['valor']:.2f}
            - Percentual atual para poupança: {summary['distribuicao']['poupanca']['percentual']:.1f}%
            - Diferença para meta de 20%: {summary['distribuicao']['poupanca']['diferenca']:.1f}%
            
            Distribuição dos gastos:
            - Necessidades: R$ {summary['distribuicao']['necessidades']['valor']:.2f} ({summary['distribuicao']['necessidades']['percentual']:.1f}%)
            - Desejos: R$ {summary['distribuicao']['desejos']['valor']:.2f} ({summary['distribuicao']['desejos']['percentual']:.1f}%)
            
            Por favor:
            1. Analise minha capacidade atual de poupança
            2. Identifique oportunidades para aumentar o valor poupado:
               - Possíveis reduções em gastos com necessidades
               - Possíveis reduções em gastos com desejos
               - Estratégias para otimizar o orçamento
            3. Sugira metas realistas de poupança considerando:
               - Minha renda atual
               - Meus gastos fixos
               - O objetivo de 20% para poupança/investimentos
            4. Proponha um plano de ação para:
               - Aumentar gradualmente o percentual poupado
               - Criar uma reserva de emergência
               - Desenvolver hábitos de economia
            5. Forneça dicas práticas de educação financeira
            
            Formate a resposta de forma clara e organizada, usando markdown para melhor legibilidade.
            """
        
        elif query_type == "imprevistos":
            return f"""
            Preciso de orientações para criar e manter uma reserva de emergência adequada.
            
            Situação atual:
            - Receita mensal: R$ {summary['receitas']:.2f}
            - Despesas mensais: R$ {summary['despesas']:.2f}
            - Saldo em conta: R$ {summary['saldo']:.2f}
            - Total investido: R$ {summary['investimentos']:.2f}
            - Valor mensal para poupança: R$ {summary['distribuicao']['poupanca']['valor']:.2f}
            
            Distribuição dos gastos:
            - Necessidades: R$ {summary['distribuicao']['necessidades']['valor']:.2f} (mensais)
            - Desejos: R$ {summary['distribuicao']['desejos']['valor']:.2f} (mensais)
            
            Por favor:
            1. Calcule o valor ideal da minha reserva de emergência considerando:
               - 6 a 12 meses de despesas básicas
               - Meus gastos fixos mensais
               - Possíveis imprevistos
            
            2. Analise minha situação atual e sugira:
               - Quanto posso destinar mensalmente para a reserva
               - Em quanto tempo posso atingir o valor ideal
               - Onde guardar a reserva de emergência
            
            3. Crie um plano de ação para:
               - Começar ou aumentar a reserva
               - Proteger o dinheiro da inflação
               - Manter a disciplina de poupança
            
            4. Forneça dicas sobre:
               - Como acelerar a construção da reserva
               - Como evitar usar a reserva desnecessariamente
               - Quando e como usar a reserva
            
            5. Sugira estratégias para:
               - Reduzir gastos não essenciais
               - Aumentar a renda se possível
               - Proteger-se de imprevistos
            
            Formate a resposta de forma clara e organizada, usando markdown para melhor legibilidade.
            """
        
        else:  # Conselho geral
            return f"""
            Por favor, faça uma análise completa da minha saúde financeira e forneça recomendações personalizadas.
            
            Panorama financeiro atual:
            - Receita mensal: R$ {summary['receitas']:.2f}
            - Despesas mensais: R$ {summary['despesas']:.2f}
            - Investimentos: R$ {summary['investimentos']:.2f}
            - Saldo em conta: R$ {summary['saldo']:.2f}
            
            Distribuição do orçamento (atual vs. ideal):
            1. Necessidades: {summary['distribuicao']['necessidades']['percentual']:.1f}% vs. 50%
               - Valor: R$ {summary['distribuicao']['necessidades']['valor']:.2f}
               - Diferença: {summary['distribuicao']['necessidades']['diferenca']:.1f}%
            
            2. Desejos: {summary['distribuicao']['desejos']['percentual']:.1f}% vs. 30%
               - Valor: R$ {summary['distribuicao']['desejos']['valor']:.2f}
               - Diferença: {summary['distribuicao']['desejos']['diferenca']:.1f}%
            
            3. Poupança/Investimentos: {summary['distribuicao']['poupanca']['percentual']:.1f}% vs. 20%
               - Valor: R$ {summary['distribuicao']['poupanca']['valor']:.2f}
               - Diferença: {summary['distribuicao']['poupanca']['diferenca']:.1f}%
            
            Próximas contas a pagar:
            {self._format_bills_list(summary['proximas_contas'])}
            
            Informações adicionais:
            - Quinzena atual: {summary['quinzena_atual']}
            - Próximo pagamento: {summary['proximo_pagamento']} (em {summary['dias_ate_proximo_pagamento']} dias)
            
            Por favor, forneça:
            1. Uma análise abrangente da minha saúde financeira:
               - Pontos fortes e fracos
               - Riscos e oportunidades
               - Comparação com as melhores práticas
            
            2. Recomendações específicas para:
               - Otimização do orçamento
               - Gestão das dívidas/contas
               - Aumento da poupança
               - Proteção financeira
            
            3. Um plano de ação detalhado:
               - Ações imediatas (próximos 30 dias)
               - Metas de curto prazo (3-6 meses)
               - Objetivos de longo prazo (1 ano ou mais)
            
            4. Dicas práticas para:
               - Melhorar hábitos financeiros
               - Aumentar receitas
               - Reduzir despesas
               - Investir melhor
            
            Formate a resposta de forma clara e organizada, usando markdown para melhor legibilidade.
            Priorize recomendações práticas e alcançáveis, considerando minha realidade financeira atual.
            """
    
    def _format_bills_list(self, bills):
        """Formata a lista de contas para o prompt"""
        if not bills:
            return "Não há contas pendentes no momento."
        
        formatted_bills = []
        for bill in bills:
            formatted_bills.append(
                f"- {bill['description']}: R$ {bill['amount']:.2f} "
                f"(vencimento: {bill['due_date']}, "
                f"prioridade: {'Alta' if bill['priority'] == 3 else 'Média' if bill['priority'] == 2 else 'Baixa'})"
            )
        
        return "\n".join(formatted_bills)

def show_finance_assistant():
    """Interface do Assistente Financeiro no Streamlit"""
    st.subheader("Assistente Financeiro Inteligente")
    
    # Inicializar o gerenciador de tema
    init_theme_manager()
    
    # Mostrar configuração de tema
    theme_config_section()
    
    assistant = FinanceAssistant()
    
    st.write("""
    Este assistente usa inteligência artificial para analisar seus dados financeiros e fornecer conselhos personalizados 
    para ajudá-lo a gerenciar suas finanças, atingir seus objetivos e planejar o pagamento de contas.
    """)
    
    # Tabs para diferentes tipos de conselhos
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Conselho Geral", 
        "Orçamento 50/30/20", 
        "Pagamento de Contas", 
        "Poupança", 
        "Reserva de Emergência"
    ])
    
    with tab1:
        st.write("**Análise Geral das Suas Finanças**")
        if st.button("Obter Conselho Geral", key="btn_geral"):
            with st.spinner("Analisando seus dados financeiros..."):
                response = assistant.get_advice()
                if response["type"] == "success":
                    st.success("Análise Completa!")
                    st.markdown(response["message"])
                else:
                    st.error(response["message"])
    
    with tab2:
        st.write("**Melhorando Seu Orçamento 50/30/20**")
        if st.button("Obter Dicas de Orçamento", key="btn_orcamento"):
            with st.spinner("Analisando seu orçamento..."):
                response = assistant.get_advice("orçamento")
                if response["type"] == "success":
                    st.success("Análise Completa!")
                    st.markdown(response["message"])
                else:
                    st.error(response["message"])
    
    with tab3:
        st.write("**Estratégia para Pagamento de Contas**")
        if st.button("Planejar Pagamentos", key="btn_contas"):
            with st.spinner("Analisando suas contas a pagar..."):
                response = assistant.get_advice("contas")
                if response["type"] == "success":
                    st.success("Análise Completa!")
                    st.markdown(response["message"])
                else:
                    st.error(response["message"])
    
    with tab4:
        st.write("**Estratégias para Aumentar sua Poupança**")
        if st.button("Dicas de Poupança", key="btn_poupanca"):
            with st.spinner("Analisando sua poupança..."):
                response = assistant.get_advice("poupança")
                if response["type"] == "success":
                    st.success("Análise Completa!")
                    st.markdown(response["message"])
                else:
                    st.error(response["message"])
    
    with tab5:
        st.write("**Preparando-se para Imprevistos**")
        if st.button("Como Criar Reserva de Emergência", key="btn_imprevistos"):
            with st.spinner("Analisando sua situação financeira..."):
                response = assistant.get_advice("imprevistos")
                if response["type"] == "success":
                    st.success("Análise Completa!")
                    st.markdown(response["message"])
                else:
                    st.error(response["message"])
    
    # Exibir resumo dos dados financeiros para o usuário
    with st.expander("Ver Resumo dos Seus Dados Financeiros"):
        summary = assistant.get_financial_summary()
        if summary["status"] == "success":
            st.write(f"**Receita Total:** R$ {summary['receitas']:.2f}")
            st.write(f"**Despesas Totais:** R$ {summary['despesas']:.2f}")
            st.write(f"**Saldo Atual:** R$ {summary['saldo']:.2f}")
            
            st.write("**Distribuição do Orçamento:**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Necessidades", 
                    f"{summary['distribuicao']['necessidades']['percentual']:.1f}%", 
                    f"{summary['distribuicao']['necessidades']['diferenca']:.1f}%",
                    delta_color="inverse" if summary['distribuicao']['necessidades']['diferenca'] > 0 else "normal"
                )
            
            with col2:
                st.metric(
                    "Desejos", 
                    f"{summary['distribuicao']['desejos']['percentual']:.1f}%", 
                    f"{summary['distribuicao']['desejos']['diferenca']:.1f}%",
                    delta_color="inverse" if summary['distribuicao']['desejos']['diferenca'] > 0 else "normal"
                )
            
            with col3:
                st.metric(
                    "Poupança", 
                    f"{summary['distribuicao']['poupanca']['percentual']:.1f}%", 
                    f"{summary['distribuicao']['poupanca']['diferenca']:.1f}%",
                    delta_color="normal" if summary['distribuicao']['poupanca']['diferenca'] > 0 else "inverse"
                )
            
            st.write("**Próximas Contas a Pagar:**")
            if summary['proximas_contas']:
                for conta in summary['proximas_contas']:
                    st.write(f"- {conta['description']}: R$ {conta['amount']:.2f} (vencimento: {conta['due_date']})")
            else:
                st.write("- Não há contas próximas para pagar.")
            
            if 'quinzena_atual' in summary and 'proximo_pagamento' in summary and 'dias_ate_proximo_pagamento' in summary:
                st.write(f"**Quinzena Atual:** {summary['quinzena_atual']}")
                if summary['proximo_pagamento']:
                    st.write(f"**Próximo Pagamento:** {summary['proximo_pagamento']} ({summary['dias_ate_proximo_pagamento']} dias)")
                else:
                    st.write("**Próximo Pagamento:** Não foi possível determinar")
            else:
                st.write("**Informações de pagamento:** Dados insuficientes")
        else:
            st.info(summary["message"])
