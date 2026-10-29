# B3 Market Analysis — Performance de Ações e Séries Temporais

Dashboard interativo para analisar o desempenho histórico de ações negociadas na B3, comparando rentabilidade acumulada, volatilidade, distribuição dos retornos, drawdown e tendências de preços. O projeto foi desenvolvido como aplicação de Business Intelligence com Python, Streamlit, Plotly e PostgreSQL/Supabase.

> **Aplicação publicada:** [B3 Market Analysis no Streamlit Community Cloud](https://stefanolaurito-b3-market-analysis-app-yotwkt.streamlit.app/)  
> **Repositório:** [stefanolaurito/b3-market-analysis](https://github.com/stefanolaurito/b3-market-analysis)

A aplicação tem finalidade educacional e analítica. Não constitui recomendação de compra ou venda de ativos.

## 1. Contexto de negócio

Investidores e gestores precisam comparar retorno e risco histórico antes de avaliar ativos. O dashboard reúne indicadores e visualizações para ajudar a responder:

1. Como os ativos se comportaram em uma base normalizada 100?
2. Quais ativos combinaram retorno acumulado e volatilidade histórica de forma mais favorável?
3. Como se distribuem os retornos diários e o que a assimetria e a curtose sugerem sobre eventos extremos?
4. Qual foi o drawdown máximo de cada ativo e qual apresentou a menor queda máxima no intervalo analisado?
5. Como o preço ajustado se comportou frente às médias móveis simples de 21 e 50 pregões?

## 2. Universo de ativos e período

A rotina de extração está configurada para consultar o intervalo `2021-01-01` (inclusivo) até `2024-01-01` (exclusivo). As datas efetivamente retornadas pelo provedor para o conjunto validado vão de **04/01/2021 a 28/12/2023**, cobrindo os pregões disponíveis de 2021 a 2023.

| Ticker usado | Setor atribuído no projeto |
|---|---|
| WEGE3 | Bens industriais |
| EMBJ3 | Aeroespacial |
| VALE3 | Mineração |
| GGBR4 | Siderurgia |
| KLBN11 | Papel e celulose |
| PETR4 | Petróleo e gás |
| PRIO3 | Petróleo e gás |
| EGIE3 | Energia elétrica |
| ITUB4 | Bancário |
| BBDC4 | Bancário |
| ABEV3 | Bebidas |
| RENT3 | Locação de veículos |

**Observação sobre o ticker da Embraer:** a configuração usa `EMBJ3.SA` no provedor de dados, exibido no dashboard como `EMBJ3`. O enunciado da atividade lista `EMBR3`; registre-se a diferença de nomenclatura utilizada na extração para facilitar a rastreabilidade.

## 3. Fonte dos dados e condições de uso

A extração é feita em Python com a biblioteca `yfinance`, que consulta dados históricos disponibilizados pelo Yahoo Finance. Portanto, esta aplicação **não é uma conexão direta com uma API oficial da B3**. A disponibilidade, a cobertura e o ajuste dos históricos dependem do provedor de dados.

- Biblioteca de extração: [yfinance](https://github.com/ranaroussi/yfinance)
- Provedor consultado: [Yahoo Finance](https://finance.yahoo.com/)
- Período: dados históricos diários de 2021 a 2023.
- Uso: projeto educacional e analítico. O usuário deve observar os termos de uso aplicáveis ao provedor de dados; não se declara aqui uma licença de redistribuição dos dados.

## 4. Pipeline de dados (ETL)

O processo de ingestão está no arquivo `carregar_dados.py`.

1. **Extração:** consulta os doze tickers configurados com `yfinance`, usando `auto_adjust=False` para preservar campos de fechamento bruto e ajustado.
2. **Padronização:** trata colunas que eventualmente chegam como `MultiIndex`, renomeia os campos para nomes consistentes e converte a data para formato de data.
3. **Conversão de tipos:** converte campos de preço e volume para tipos numéricos, coercindo valores inválidos para nulos.
4. **Limpeza:** descarta linhas sem data, preço de fechamento ou fechamento ajustado válidos.
5. **Persistência:** insere os registros na tabela `public.historico_acoes` do PostgreSQL, evitando reinserir a mesma combinação de data e ticker por meio de `ON CONFLICT (data, ticker) DO NOTHING`.
6. **Contingência:** o dashboard tenta carregar os dados do PostgreSQL/Supabase; se a conexão ou consulta falhar, utiliza `historico_acoes.csv`.
7. **Cache:** consultas e tratamentos utilizam `st.cache_data` com TTL de 600 segundos.

O arquivo `exportar_csv.py` exporta a tabela histórica do banco para criar/atualizar o CSV de contingência.

### Reproduzir a carga de dados

Com o ambiente configurado e credenciais válidas no arquivo local `.streamlit/secrets.toml`:

```powershell
python carregar_dados.py
```

Para exportar a cópia de contingência a partir do banco:

```powershell
python exportar_csv.py
```

O arquivo CSV de contingência é uma **fotografia estática** da base no momento da exportação. Para refletir atualizações do banco, execute novamente o script de exportação.

## 5. Dicionário de dados

### Campos persistidos em `historico_acoes`

| Campo | Tipo esperado | Significado |
|---|---|---|
| `data` | Data (`DATE` no banco; datetime no dashboard) | Data do pregão. |
| `ticker` | Texto | Código do ativo usado pelo provedor e no dashboard. |
| `setor` | Texto | Categoria setorial atribuída pelo projeto para agrupar/comparar ativos. |
| `abertura` | Numérico | Preço de abertura do pregão. |
| `maxima` | Numérico | Maior preço registrado no pregão. |
| `minima` | Numérico | Menor preço registrado no pregão. |
| `fechamento` | Numérico | Preço de fechamento não ajustado. |
| `fechamento_ajustado` | Numérico | Preço ajustado disponibilizado pelo provedor, utilizado no cálculo de retornos. |
| `volume` | Inteiro/numérico | Quantidade de ações negociadas, conforme o campo de volume do provedor; não é, por si só, volume financeiro em reais. |

### Indicadores calculados na aplicação

| Indicador | Regra de cálculo / interpretação |
|---|---|
| Retorno diário | Variação percentual do fechamento ajustado em relação ao pregão anterior. |
| Retorno acumulado | Fechamento ajustado final dividido pelo inicial, menos 1. |
| Base 100 | Fechamento ajustado dividido pelo primeiro fechamento ajustado do intervalo, multiplicado por 100. |
| Volatilidade anualizada | Desvio-padrão dos retornos diários multiplicado por √252. É uma estimativa histórica. |
| Sharpe simplificado | Média diária dos retornos dividida pelo desvio-padrão diário, multiplicada por √252; assume taxa livre de risco de 0% a.a. |
| Drawdown | Queda percentual do fechamento ajustado frente ao maior preço ajustado acumulado até aquela data dentro do intervalo analisado. |
| Drawdown máximo | Menor valor de drawdown de cada ativo no intervalo selecionado. Quanto mais próximo de zero, menor foi a queda máxima observada. |
| Assimetria | Medida de inclinação da distribuição dos retornos diários. |
| Curtose (excesso) | Medida de forma da distribuição; valores positivos podem indicar caudas mais pesadas que a distribuição normal. |
| Volume financeiro médio estimado | Média de `fechamento × volume` no intervalo selecionado. É uma aproximação para o tamanho das bolhas, não o volume financeiro oficial de cada negócio. |

## 6. Resultados históricos observados

Na comparação validada dos fechamentos ajustados entre a primeira e a última data disponível do período, os maiores retornos acumulados entre os ativos estudados foram:

| Ativo | Retorno acumulado aproximado |
|---|---:|
| PETR4 | +228,69% |
| PRIO3 | +208,32% |
| EMBJ3 | +167,50% |

Entre os retornos acumulados negativos observados na mesma comparação, destacaram-se BBDC4 (−6,93%), KLBN11 (−0,80%) e RENT3 (−0,25%).

Esses percentuais descrevem o intervalo histórico selecionado e dependem da série ajustada utilizada. Os indicadores exibidos no dashboard são recalculados conforme o usuário altera os filtros; por isso, os valores dos KPIs podem diferir quando a seleção de ativos ou datas é diferente.

### Como interpretar os gráficos

- **Desempenho — Base 100:** cada ativo começa em 100 no início do intervalo selecionado; valores acima de 100 indicam valorização relativa, e abaixo de 100, desvalorização.
- **Risco versus retorno:** mostra o retorno acumulado em relação à volatilidade anualizada. O tamanho da bolha usa uma estimativa de volume financeiro baseada em preço de fechamento × quantidade negociada, não uma série oficial de volume financeiro.
- **Distribuição dos retornos diários:** histograma e boxplot ajudam a observar concentração, dispersão e valores extremos. Assimetria e curtose complementam a leitura estatística.
- **Drawdown histórico e máximo:** mostram quedas em relação aos picos anteriores; uma queda máxima menos negativa indica menor perda de pico a vale no intervalo considerado, sem garantir menor risco futuro.
- **Médias móveis (SMA 21 e SMA 50):** comparam o fechamento ajustado com médias de 21 e 50 pregões para inspeção de tendência histórica.

## 7. Tecnologias

| Tecnologia | Uso no projeto |
|---|---|
| Python | Linguagem principal para ETL e aplicação. |
| Pandas | Limpeza, transformação e agregação de séries temporais. |
| NumPy | Cálculos estatísticos e anualização da volatilidade. |
| yfinance | Coleta de histórico de preços no Yahoo Finance. |
| PostgreSQL / Supabase | Persistência do histórico de preços. |
| SQLAlchemy + Psycopg | Conexão e operações de gravação/exportação no PostgreSQL. |
| Streamlit | Interface interativa, filtros, KPIs, abas e download de CSV. |
| Plotly Express / Graph Objects | Gráficos interativos de séries temporais e distribuição. |
| Git / GitHub | Versionamento do código e integração das branches. |

## 8. Funcionalidades do dashboard

- Filtros cruzados por ativo, setor e intervalo de datas.
- Botões de seleção rápida de ativos e opção para visualizar todos.
- Quatro KPIs: retorno médio dos ativos, melhor ativo, pior ativo e volatilidade anualizada média, com deltas comparativos.
- Abas temáticas para desempenho, risco/volatilidade e tendência/dados.
- Cinco gráficos principais: Base 100, risco versus retorno, distribuição dos retornos diários, drawdown e médias móveis.
- Ranking do Índice de Sharpe simplificado, tabela de estatísticas de distribuição e resumo de drawdown máximo.
- Exportação dos dados filtrados para CSV.
- Carregamento resiliente pelo Supabase com fallback para CSV local.

## 9. Limitações e cautelas de interpretação

- O período examinado é histórico e se limita aos pregões de 2021 a 2023; resultados passados não garantem retornos futuros.
- A base veio de uma fonte pública consolidada por `yfinance`; ela não é apresentada como fonte direta oficial da B3.
- `volume` representa quantidade de ações negociadas. O valor financeiro mostrado nas bolhas é estimado por preço de fechamento × quantidade e pode diferir do volume financeiro oficial dos negócios.
- O Sharpe da aplicação assume taxa livre de risco de 0% a.a. e é, portanto, simplificado; um cálculo que use uma série histórica da taxa livre de risco pode produzir resultados diferentes.
- A anualização por √252 é uma convenção de estimação e não garante que a volatilidade futura seja semelhante.
- Os resultados variam de acordo com os filtros selecionados.
- Correlação, coincidência temporal e desempenho histórico não demonstram causalidade.
- O CSV de contingência é estático e pode ficar desatualizado em relação ao banco.

## 10. Como executar localmente

### Pré-requisitos

- Python instalado.
- Acesso ao repositório.
- Credenciais de acesso ao PostgreSQL/Supabase para usar o banco; sem conexão, o app pode utilizar o CSV local.

### Instalação no Windows

Clone o repositório e entre na pasta:

```powershell
git clone https://github.com/stefanolaurito/b3-market-analysis.git
cd b3-market-analysis
```

Crie e ative um ambiente virtual e instale as dependências:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Crie localmente `.streamlit/secrets.toml` com a configuração do banco. Exemplo de estrutura (substitua pelos dados reais; **não publique credenciais**):

```toml
[connections.postgresql]
dialect = "postgresql"
host = "SEU_HOST_REMOTO"
port = 5432
database = "SEU_BANCO"
username = "SEU_USUARIO"
password = "SUA_SENHA"
```

Execute a aplicação:

```powershell
python -m streamlit run app.py
```

Abra o endereço local indicado pelo Streamlit, normalmente `http://localhost:8501`.

### Configuração no Streamlit Community Cloud

O deploy público está configurado no [B3 Market Analysis](https://stefanolaurito-b3-market-analysis-app-yotwkt.streamlit.app/). As credenciais do banco devem ser configuradas na área **Settings → Secrets** do aplicativo hospedado; o arquivo local `.streamlit/secrets.toml` não deve ser versionado.

## 11. Estrutura do repositório

```text
b3-market-analysis/
├── app.py
├── carregar_dados.py
├── exportar_csv.py
├── historico_acoes.csv
├── requirements.txt
├── README.md
├── .gitignore
└── .streamlit/
    └── secrets.toml  # somente local; ignorado pelo Git
```

## 12. Publicação, gestão ágil e apresentação

- **Repositório GitHub:** https://github.com/stefanolaurito/b3-market-analysis
- **Aplicação publicada:** https://stefanolaurito-b3-market-analysis-app-yotwkt.streamlit.app/
- **Quadro Kanban no Trello:** `PREENCHER_COM_URL_PUBLICA_DO_TRELLO`
- **Vídeo de apresentação (3–5 minutos):** `PREENCHER_COM_URL_DO_VIDEO`
- **Captura do quadro Trello:** adicionar ao repositório e inserir a imagem nesta seção.
- **Capturas da aplicação:** adicionar capturas atualizadas das três abas para documentar a interface publicada.

O quadro Trello deve mostrar as colunas Backlog, A Fazer, Em Andamento e Concluído, além dos cards e evidências de movimentação solicitados pela avaliação.

## 13. Roteiro sugerido para o vídeo

1. **0:00–0:45 — Contexto:** apresentar o problema de negócio, o período e as perguntas financeiras.
2. **0:45–1:30 — Dados e ETL:** explicar a coleta com `yfinance`, a limpeza com Pandas, a persistência PostgreSQL/Supabase e a contingência CSV.
3. **1:30–3:45 — Aplicação:** demonstrar as abas, filtros, seleção rápida de ativos, KPIs, gráficos, cache, reset de filtros e download CSV.
4. **3:45–5:00 — Conclusão:** comentar os principais resultados e as limitações, enfatizando que indicadores históricos não são previsões.

## 14. Autoria e referências

**Autor:** Stéfano Laurito  
**LinkedIn:** `PREENCHER_COM_URL_DO_LINKEDIN`

Referências técnicas:

- [Streamlit — documentação](https://docs.streamlit.io/)
- [Streamlit — conexões SQL](https://docs.streamlit.io/develop/api-reference/connections/st.connections.sqlconnection)
- [Plotly Python](https://plotly.com/python/)
- [Pandas](https://pandas.pydata.org/docs/)
- [yfinance](https://github.com/ranaroussi/yfinance)
- [SQLAlchemy](https://docs.sqlalchemy.org/)
- [Psycopg 3](https://www.psycopg.org/psycopg3/docs/)
- [Yahoo Finance](https://finance.yahoo.com/)

## 15. Checklist de entrega

- [x] Aplicação executada localmente.
- [x] Conexão Supabase e contingência CSV testadas localmente.
- [x] Aplicação publicada no Streamlit Community Cloud.
- [x] Secrets configurados na nuvem sem inserir credenciais no repositório.
- [x] Interface com abas, filtros, KPIs, gráficos e exportação CSV.
- [x] Versão final integrada à branch `main`.
- [ ] Inserir a URL pública do Trello e uma captura do quadro.
- [ ] Gravar e inserir a URL do vídeo de apresentação de 3 a 5 minutos.
- [ ] Inserir a URL do LinkedIn do autor.
- [ ] Adicionar capturas atualizadas das abas ao README.
- [ ] Fazer a leitura final de todos os links antes de submeter no AVA.
