# 💰 Controle Financeiro Pessoal

Uma aplicação web moderna para gerenciamento de finanças pessoais, construída com Python e Streamlit.

## 🌟 Funcionalidades

### 📊 Dashboard
- Visão geral das finanças
- Saldo atual
- Gráficos de receitas e despesas
- Distribuição por categorias

### 💸 Transações
- Cadastro de receitas, despesas e investimentos
- Categorização automática
- Filtros avançados
- Status de pagamento
- Transações recorrentes

### 📈 Orçamento 50/30/20
- Análise baseada na regra 50/30/20
- Distribuição entre necessidades, desejos e investimentos
- Recomendações personalizadas
- Acompanhamento mensal

### 📑 Relatórios
- Análise mensal detalhada
- Comparativos de períodos
- Evolução patrimonial
- Exportação de dados

### 🎯 Metas Financeiras
- Definição de metas com prazo
- Acompanhamento do progresso
- Categorização por objetivo
- Visualização em cards e gráficos

### 🤖 Assistente Financeiro
- Dicas personalizadas
- Análise de gastos
- Recomendações de investimentos
- Alertas importantes

## 🛠️ Tecnologias

- **Python**: Linguagem principal
- **Streamlit**: Interface web
- **SQLite**: Banco de dados
- **Pandas**: Análise de dados
- **Plotly**: Visualizações interativas

## 📁 Estrutura do Projeto

```
financas-streamlit/
├── run.py                    # Arquivo principal e ponto de entrada
├── db.py                     # Configuração central do banco de dados
├── ui.py                     # Componentes de UI reutilizáveis
├── settings.py               # Configurações do sistema
├── categories.py             # Gerenciamento de categorias
├── dashboard.py             # Dashboard principal
├── budget_tool.py           # Ferramenta de orçamento
├── reports.py               # Relatórios e análises
├── finance_assistant.py     # Assistente financeiro
├── goals.py                 # Interface de metas
├── goals_db.py              # Operações de BD de metas
├── transactions_db.py       # Operações de BD de transações
└── transactions_analysis.py # Análises de transações
```

## ⚙️ Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/financas-streamlit.git
cd financas-streamlit
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Execute a aplicação:
```bash
streamlit run run.py
```

## 📦 Dependências

Principais pacotes necessários:
```
streamlit>=1.24.0
pandas>=2.0.0
plotly>=5.13.0
sqlite3
python-dotenv>=1.0.0
```

## 🚀 Uso

1. Inicie cadastrando suas categorias de transações
2. Adicione suas transações regulares
3. Configure suas metas financeiras
4. Acompanhe seu progresso no dashboard
5. Consulte os relatórios mensais
6. Use o assistente financeiro para dicas

## 🔒 Segurança

- Dados armazenados localmente em SQLite
- Sem envio de informações para servidores externos
- Backup automático do banco de dados

## 🤝 Contribuição

1. Faça um Fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👤 Autor

Leonardo Fragoso

## 🙏 Agradecimentos

- Streamlit pela excelente framework
- Comunidade Python
- Todos os contribuidores
