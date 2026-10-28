B3 Market Analysis — Performance de Ações e Séries Temporais
Dashboard interativo para explorar o desempenho histórico de ações negociadas na B3, com indicadores de rentabilidade e risco, visualizações em Plotly e carregamento resiliente de dados.
Status do projeto: o dashboard local foi executado com sucesso e o fallback para CSV foi testado. Antes da entrega, complete os links indicados abaixo e confira a lista de requisitos no final deste README.

Objetivo
Analisar séries históricas de preços de ações brasileiras para comparar rentabilidade acumulada, volatilidade, comportamento dos retornos e drawdown. A aplicação tem finalidade educacional e analítica; não constitui recomendação de investimento.
Ativos e período
A rotina de ETL está configurada para buscar dados históricos de 4 de janeiro de 2021 a 28 de dezembro de 2023 (considerando as datas efetivamente retornadas pela fonte) para os seguintes ativos:
- WEGE3 — Bens industriais
- EMBJ3 — Aeroespacial
- VALE3 — Mineração
- GGBR4 — Siderurgia
- KLBN11 — Papel e celulose
- PETR4 — Petróleo e gás
- PRIO3 — Petróleo e gás
- EGIE3 — Energia elétrica
- ITUB4 — Bancário
- BBDC4 — Bancário
- ABEV3 — Bebidas
- RENT3 — Locação de veículos
A coleta é realizada em Python por meio da biblioteca yfinance, que consulta dados históricos disponibilizados pelo Yahoo Finance. A disponibilidade, a cobertura e os ajustes históricos dependem dessa fonte; não se trata de uma conexão direta com uma API oficial da B3.
Funcionalidades conhecidas
- Filtros por ativo, setor e intervalo de datas.
- Quatro KPIs relacionados a rentabilidade acumulada, melhor e pior desempenho e volatilidade anualizada média.
- Cinco visualizações analíticas: desempenho normalizado em Base 100, relação risco-retorno, distribuição dos retornos diários, drawdown e preço ajustado com médias móveis de 21 e 50 pregões.
- Consulta ao PostgreSQL/Supabase com cache de 600 segundos.
- Fallback automático para historico_acoes.csv quando a consulta ao banco falha.
- Script de ETL para coleta e carga dos dados históricos no PostgreSQL.
Observação: a cópia CSV é um retrato estático dos dados no momento da exportação. Para atualizá-la, gere novamente o arquivo a partir da base. O dashboard só usará o CSV como contingência se estiver disponível na pasta de execução.
Tecnologias
- Python
- Streamlit
- Pandas
- Plotly
- PostgreSQL/Supabase
- SQLAlchemy e Psycopg
- yfinance
Estrutura esperada
b3-market-analysis/
├── app.py
├── carregar_dados.py
├── historico_acoes.csv       # contingência local
├── requirements.txt
├── README.md
├── .gitignore
└── .streamlit/
    └── secrets.toml          # credenciais locais; não versionar
Como executar localmente
1. Preparar o ambiente
No Windows, abra o terminal na pasta do projeto e execute:
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
2. Configurar as credenciais
Crie o arquivo .streamlit/secrets.toml localmente, sem colocar credenciais diretamente no código:
[connections.postgresql]
dialect = "postgresql"
host = "SEU_HOST"
port = 5432
database = "SEU_BANCO"
username = "SEU_USUARIO"
password = "SUA_SENHA"
Substitua os valores de exemplo pelas credenciais do seu banco. Nunca publique esse arquivo nem compartilhe senhas. Confirme que .streamlit/secrets.toml está listado no .gitignore. Para publicação no Streamlit Community Cloud, configure os mesmos valores na área de Secrets do aplicativo hospedado.
3. Iniciar o dashboard
python -m streamlit run app.py
Acesse o endereço local mostrado no terminal, normalmente http://localhost:8501.
Atualização da base (ETL)
O script carregar_dados.py baixa os dados históricos configurados e insere no PostgreSQL os registros que ainda não existem, usando a chave de conflito (data, ticker).

Com o ambiente virtual ativo e o arquivo de credenciais configurado, execute:
python carregar_dados.py
A rotina depende de conexão com a fonte de dados e com o banco. Verifique a saída do terminal e a quantidade de registros gravados antes de considerar a atualização concluída.
Indicadores e interpretação
Os retornos históricos, a volatilidade, o drawdown e as médias móveis descrevem o período observado. Eles não garantem resultados futuros. Diferenças de setor, eventos corporativos, condições macroeconômicas e a metodologia de ajuste dos preços podem afetar a comparação. Correlação ou coincidência temporal, isoladamente, não demonstra causalidade.
Links do projeto
- Repositório GitHub: https://github.com/stefanolaurito/b3-market-analysis
- Aplicação pública no Streamlit Community Cloud: PREENCHER_COM_URL_PUBLICA
- Quadro Trello público: PREENCHER_COM_URL_DO_TRELLO
- Vídeo de apresentação (3–5 minutos): PREENCHER_COM_URL_DO_VIDEO
Checklist antes da entrega
- [x] Dashboard local abre sem erro fatal.
- [x] Fallback para CSV testado; a tela indicou CSV local (modo alternativo).
- [x] Retorno ao PostgreSQL/Supabase confirmado.
- [ ] Confirmar que .streamlit/secrets.toml está no .gitignore e que nenhum segredo foi enviado ao GitHub.
- [ ] Conferir se a interface está organizada com st.tabs.
- [ ] Conferir botão funcional de reset dos filtros com persistência adequada via st.session_state.
- [ ] Conferir exportação dos dados filtrados via st.download_button.
- [ ] Conferir KPIs com deltas de comparação, conforme a rubrica.
- [ ] Preencher e testar a URL pública do Streamlit Community Cloud.
- [ ] Inserir o link público do quadro Trello e garantir que as tarefas estejam atualizadas.
- [ ] Gravar o pitch de 3 a 5 minutos e inserir o link.
- [ ] Confirmar que o código final está integrado à branch main e que as branches do GitFlow foram mantidas conforme as instruções.
- [ ] Atualizar a lista de dependências em requirements.txt e testar a instalação limpa.
Referências técnicas
- Streamlit: https://docs.streamlit.io/
- Streamlit SQL connections: https://docs.streamlit.io/develop/api-reference/connections/st.connections.sqlconnection
- Plotly Python: https://plotly.com/python/
- Pandas: https://pandas.pydata.org/docs/
- yfinance: https://github.com/ranaroussi/yfinance
- SQLAlchemy: https://docs.sqlalchemy.org/
- Psycopg: https://www.psycopg.org/psycopg3/docs/