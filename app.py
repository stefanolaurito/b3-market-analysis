import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="B3 Market Analysis",
    page_icon="📈",
    layout="wide",
)

# --------------------------------------------------
# CONFIGURAÇÃO
# --------------------------------------------------

st.title("📈 B3 Market Analysis")
st.caption(
    "Análise de desempenho e risco de ações brasileiras "
    "no período de 2021 a 2023."
)

# --------------------------------------------------
# PREPARAÇÃO E CARREGAMENTO DOS DADOS
# --------------------------------------------------

COLUNAS_NUMERICAS = [
    "abertura",
    "maxima",
    "minima",
    "fechamento",
    "fechamento_ajustado",
    "volume",
]


def preparar_dados(df):
    """Padroniza os tipos usados pelo dashboard."""
    df = df.copy()
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["ticker"] = df["ticker"].astype(str)
    df["setor"] = df["setor"].astype(str)

    for coluna in COLUNAS_NUMERICAS:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")

    return df.dropna(subset=["data", "ticker", "setor"])


@st.cache_data(ttl=600)
def carregar_csv():
    """Usa a cópia local se o PostgreSQL/Supabase estiver indisponível."""
    df = pd.read_csv("historico_acoes.csv")
    return preparar_dados(df)


@st.cache_data(ttl=600)
def carregar_dados():
    """Prioriza o PostgreSQL/Supabase e recorre ao CSV em caso de falha."""
    query = """
        SELECT
            data,
            ticker,
            setor,
            abertura,
            maxima,
            minima,
            fechamento,
            fechamento_ajustado,
            volume
        FROM public.historico_acoes
        ORDER BY data, ticker
    """

    try:
        conn = st.connection("postgresql", type="sql")
        df = conn.query(query, ttl=600)
        if df.empty:
            raise RuntimeError("A consulta ao PostgreSQL não retornou registros.")
        return preparar_dados(df), "PostgreSQL / Supabase"
    except Exception as erro_postgres:
        try:
            df = carregar_csv()
            if df.empty:
                raise RuntimeError("O arquivo CSV está vazio.")
            return df, "CSV local (modo alternativo)"
        except Exception as erro_csv:
            raise RuntimeError(
                "Falha ao carregar os dados do banco e do CSV. "
                f"Erro do banco: {erro_postgres}. Erro do CSV: {erro_csv}."
            ) from erro_csv


try:
    df, fonte_dados = carregar_dados()
    st.caption(f"Fonte dos dados: {fonte_dados}")
    st.caption("A visão inicial prioriza 5 ativos para facilitar a leitura; selecione todos os ativos na barra lateral para a comparação completa.")
except Exception as erro:
    st.error("Não foi possível carregar os dados do banco nem do CSV.")
    with st.expander("Detalhes técnicos do erro"):
        st.exception(erro)
    st.stop()

if df.empty:
    st.warning("A tabela histórica não contém registros.")
    st.stop()

# --------------------------------------------------
# FILTROS
# --------------------------------------------------

st.sidebar.header("Filtros")

tickers_disponiveis = sorted(df["ticker"].dropna().unique().tolist())
setores_disponiveis = sorted(df["setor"].dropna().unique().tolist())
data_minima = df["data"].min().date()
data_maxima = df["data"].max().date()

# Seleção inicial enxuta e diversificada para reduzir sobreposição nos gráficos.
# Não é um ranking ou uma recomendação de investimento.
TICKERS_VISAO_ENXUTA = ["ABEV3", "ITUB4", "PETR4", "VALE3", "WEGE3"]
tickers_padrao = [
    ticker for ticker in TICKERS_VISAO_ENXUTA
    if ticker in tickers_disponiveis
]
if not tickers_padrao:
    tickers_padrao = tickers_disponiveis[:min(5, len(tickers_disponiveis))]


def restaurar_padrao():
    st.session_state["filtro_tickers_v2"] = tickers_padrao.copy()
    st.session_state["filtro_setores_v2"] = []  # vazio significa todos os setores
    st.session_state["filtro_datas_v2"] = (data_minima, data_maxima)


def selecionar_visao_enxuta():
    st.session_state["filtro_tickers_v2"] = tickers_padrao.copy()


def selecionar_todos_ativos():
    st.session_state["filtro_tickers_v2"] = tickers_disponiveis.copy()

if "filtro_tickers_v2" not in st.session_state:
    st.session_state["filtro_tickers_v2"] = tickers_padrao.copy()
if "filtro_setores_v2" not in st.session_state:
    st.session_state["filtro_setores_v2"] = []
if "filtro_datas_v2" not in st.session_state:
    st.session_state["filtro_datas_v2"] = (data_minima, data_maxima)

st.sidebar.button(
    "Restaurar visão padrão",
    on_click=restaurar_padrao,
    width="stretch",
)

st.sidebar.caption(
    "Comece com 5 ativos para facilitar a leitura. A seleção inicial é apenas comparativa, não é recomendação."
)
col_atl1, col_atl2 = st.sidebar.columns(2)
col_atl1.button(
    "Visão enxuta (5)",
    on_click=selecionar_visao_enxuta,
    width="stretch",
    help="Seleciona cinco ativos de setores distintos para reduzir a poluição visual.",
)
col_atl2.button(
    "Todos os ativos",
    on_click=selecionar_todos_ativos,
    width="stretch",
    help="Seleciona os 12 ativos disponíveis para uma comparação completa.",
)

tickers_selecionados = st.sidebar.multiselect(
    "Ativos em análise",
    options=tickers_disponiveis,
    key="filtro_tickers_v2",
    placeholder="Escolha os ativos",
    help="Use os botões acima para alternar rapidamente entre 5 ativos e o universo completo.",
)

setores_selecionados = st.sidebar.multiselect(
    "Setores (opcional)",
    options=setores_disponiveis,
    key="filtro_setores_v2",
    placeholder="Todos os setores",
    help="Deixe vazio para incluir todos os setores; selecione um ou mais para restringir a análise.",
)
setores_para_filtrar = setores_selecionados if setores_selecionados else setores_disponiveis

periodo = st.sidebar.date_input(
    "Período da análise",
    min_value=data_minima,
    max_value=data_maxima,
    key="filtro_datas_v2",
    format="DD/MM/YYYY",
)

if not isinstance(periodo, (tuple, list)) or len(periodo) != 2:
    st.info("Selecione a data inicial e a data final.")
    st.stop()

data_inicial, data_final = periodo
if data_inicial > data_final:
    st.error("A data inicial não pode ser posterior à data final.")
    st.stop()

# Filtros cruzados: ativos, setores e intervalo de datas.
df_filtrado = df[
    df["ticker"].isin(tickers_selecionados)
    & df["setor"].isin(setores_para_filtrar)
    & (df["data"].dt.date >= data_inicial)
    & (df["data"].dt.date <= data_final)
].copy()

if df_filtrado.empty:
    st.warning(
        "Nenhum registro corresponde à seleção atual. Use 'Visão enxuta (5)' ou "
        "'Todos os ativos', ou ajuste os filtros na barra lateral."
    )
    st.stop()

# --------------------------------------------------
# CÁLCULOS FINANCEIROS
# --------------------------------------------------

# Os retornos usam fechamento ajustado. O volume disponível na base é
# quantidade de ações negociadas, não volume financeiro em reais.
df_filtrado = df_filtrado.sort_values(["ticker", "data"])
df_filtrado = df_filtrado.dropna(subset=["fechamento_ajustado"])

if df_filtrado.empty:
    st.warning("Não há preços ajustados válidos para os filtros selecionados.")
    st.stop()

df_filtrado["retorno_diario"] = (
    df_filtrado.groupby("ticker")["fechamento_ajustado"].pct_change()
)
df_filtrado["retorno_acumulado"] = df_filtrado.groupby("ticker")[
    "fechamento_ajustado"
].transform(lambda serie: serie / serie.iloc[0] - 1)

# Estimativa do volume financeiro diário: preço de fechamento × quantidade negociada.
# A base não contém o volume financeiro oficial em reais.
df_filtrado["volume_financeiro_estimado"] = (
    df_filtrado["fechamento"] * df_filtrado["volume"]
)

retornos_por_ativo = df_filtrado.groupby("ticker")["fechamento_ajustado"].agg(
    lambda serie: serie.iloc[-1] / serie.iloc[0] - 1
)
retornos_validos = df_filtrado.dropna(subset=["retorno_diario"])
volatilidade_por_ativo = (
    retornos_validos.groupby("ticker")["retorno_diario"].std() * np.sqrt(252)
)

retorno_medio_carteira = retornos_por_ativo.mean()
retorno_mediano_ativos = retornos_por_ativo.median()
volatilidade_media = volatilidade_por_ativo.mean()
volatilidade_mediana = volatilidade_por_ativo.median()

if not retornos_por_ativo.empty:
    melhor_ativo = retornos_por_ativo.idxmax()
    melhor_retorno = retornos_por_ativo.max()
    pior_ativo = retornos_por_ativo.idxmin()
    pior_retorno = retornos_por_ativo.min()
else:
    melhor_ativo, pior_ativo = "N/D", "N/D"
    melhor_retorno = pior_retorno = np.nan


def formatar_numero_ptbr(valor, casas=2, milhar=True):
    """Formata números com ponto de milhar e vírgula decimal."""
    if pd.isna(valor):
        return "N/D"
    formato = f"{valor:,.{casas}f}" if milhar else f"{valor:.{casas}f}"
    return formato.replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")


def formatar_percentual(valor):
    return f"{valor:.2%}".replace(".", ",") if pd.notna(valor) else "N/D"


def formatar_delta(valor, complemento=""):
    if pd.isna(valor):
        return "N/D"
    return f"{valor:+.2%}".replace(".", ",") + complemento

# --------------------------------------------------
# KPIs
# --------------------------------------------------

st.subheader("Indicadores de desempenho")
col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Retorno médio dos ativos",
    formatar_percentual(retorno_medio_carteira),
    delta=formatar_delta(
        retorno_medio_carteira - retorno_mediano_ativos,
        " vs. mediana dos ativos",
    ),
    help="O delta compara a média dos retornos dos ativos à mediana individual.",
)
col2.metric(
    "Melhor ativo",
    melhor_ativo,
    delta=formatar_delta(
        melhor_retorno - retorno_medio_carteira,
        " vs. retorno médio",
    ),
    help="O delta mostra quanto o melhor retorno ficou acima ou abaixo da média.",
)
col3.metric(
    "Pior ativo",
    pior_ativo,
    delta=formatar_delta(
        pior_retorno - retorno_medio_carteira,
        " vs. retorno médio",
    ),
    help="O delta compara o retorno do pior ativo à média dos ativos selecionados.",
)
col4.metric(
    "Volatilidade anualizada média",
    formatar_percentual(volatilidade_media),
    delta=formatar_delta(
        volatilidade_media - volatilidade_mediana,
        " vs. mediana (p.p.)",
    ),
    delta_color="inverse",
    help="Volatilidade anualizada estimada pelo desvio-padrão dos retornos diários × raiz de 252.",
)

st.caption(
    "Os deltas comparam a média de retorno à mediana dos ativos, "
    "os melhores/piores retornos à média e a volatilidade média à mediana. "
    "São comparações entre os ativos selecionados, não previsões de desempenho futuro."
)

# Exportação dos dados filtrados em formato amigável ao Excel em português.
df_exportacao = df_filtrado.copy()
df_exportacao["data"] = df_exportacao["data"].dt.strftime("%d/%m/%Y")
csv_filtrado = df_exportacao.to_csv(
    index=False,
    sep=";",
    decimal=",",
).encode("utf-8-sig")
st.download_button(
    "Baixar dados filtrados (CSV)",
    data=csv_filtrado,
    file_name="b3_dados_filtrados.csv",
    mime="text/csv",
    width="content",
    help="Arquivo compatível com configurações brasileiras do Excel: datas dd/mm/aaaa, separador ; e vírgula decimal.",
)

# --------------------------------------------------
# VISUALIZAÇÕES ORGANIZADAS EM ABAS
# --------------------------------------------------

aba_desempenho, aba_risco, aba_tendencia = st.tabs(
    ["Desempenho", "Risco e volatilidade", "Tendência e dados"]
)

# GRÁFICO 1 — RETORNO ACUMULADO BASE 100
with aba_desempenho:
    st.subheader("Retorno acumulado — base 100")
    df_grafico = df_filtrado.sort_values(["ticker", "data"]).copy()
    df_grafico["base_100"] = (
        df_grafico["fechamento_ajustado"]
        / df_grafico.groupby("ticker")["fechamento_ajustado"].transform("first")
        * 100
    )

    fig_retorno = px.line(
        df_grafico,
        x="data",
        y="base_100",
        color="ticker",
        title="Evolução do desempenho dos ativos",
        labels={
            "data": "Data",
            "base_100": "Índice (base 100)",
            "ticker": "Ativo",
        },
    )
    fig_retorno.update_layout(
        hovermode="x unified",
        separators=",.",
        legend_title_text="Ativos",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        margin=dict(t=90, b=40),
        height=520,
    )
    fig_retorno.update_traces(
        hovertemplate=(
            "<b>Ativo: %{fullData.name}</b><br>"
            "Data: %{x|%d/%m/%Y}<br>"
            "Índice (base 100): %{y:.2f}<extra></extra>"
        )
    )
    fig_retorno.update_xaxes(dtick="M3", tickformat="%m/%Y")
    fig_retorno.update_yaxes(tickformat=".0f")
    fig_retorno.add_hline(
        y=100,
        line_dash="dash",
        line_color="gray",
        annotation_text="Base 100",
        annotation_position="top left",
    )
    st.plotly_chart(fig_retorno, width="stretch")

    st.caption(
        "Como ler: todos os ativos começam em 100 na primeira data selecionada. "
        "Um índice de 120 representa valorização acumulada de 20%; um índice de 90, "
        "queda acumulada de 10%. Passe o cursor sobre a linha para ver ativo, data e índice."
    )

# GRÁFICOS 2, 3 E 4 — RISCO, DISTRIBUIÇÃO E DRAWDOWN
with aba_risco:
    st.subheader("Risco versus retorno")
    st.caption(
        "Cada bolha representa um ativo. O eixo horizontal mostra a volatilidade anualizada "
        "(risco histórico); o vertical mostra o retorno acumulado. Bolhas mais à direita "
        "tiveram maior oscilação, e bolhas mais acima tiveram maior retorno. O tamanho usa "
        "uma estimativa de volume financeiro médio, não o volume financeiro oficial."
    )
    estatisticas_ativos = (
        df_filtrado.sort_values(["ticker", "data"])
        .groupby(["ticker", "setor"])
        .agg(
            preco_inicial=("fechamento_ajustado", "first"),
            preco_final=("fechamento_ajustado", "last"),
            desvio_diario=("retorno_diario", "std"),
            retorno_medio_diario=("retorno_diario", "mean"),
            volume_financeiro_medio_estimado=("volume_financeiro_estimado", "mean"),
        )
        .reset_index()
    )
    estatisticas_ativos["retorno_acumulado"] = (
        estatisticas_ativos["preco_final"] / estatisticas_ativos["preco_inicial"] - 1
    )
    estatisticas_ativos["volatilidade_anualizada"] = (
        estatisticas_ativos["desvio_diario"] * np.sqrt(252)
    )
    # Sharpe anualizado simplificado, assumindo taxa livre de risco de 0% a.a.
    estatisticas_ativos["sharpe_simplificado"] = (
        estatisticas_ativos["retorno_medio_diario"]
        / estatisticas_ativos["desvio_diario"].replace(0, np.nan)
        * np.sqrt(252)
    )
    estatisticas_ativos = estatisticas_ativos.dropna(
        subset=["retorno_acumulado", "volatilidade_anualizada"]
    )

    if not estatisticas_ativos.empty:
        fig_risco_retorno = px.scatter(
            estatisticas_ativos,
            x="volatilidade_anualizada",
            y="retorno_acumulado",
            size="volume_financeiro_medio_estimado",
            color="setor",
            hover_name="ticker",
            custom_data=["setor", "volume_financeiro_medio_estimado"],
            title="Risco anualizado versus retorno acumulado por ativo",
            labels={
                "volatilidade_anualizada": "Volatilidade anualizada",
                "retorno_acumulado": "Retorno acumulado",
                "volume_financeiro_medio_estimado": "Volume financeiro médio estimado (R$)",
                "setor": "Setor",
            },
            size_max=45,
        )
        fig_risco_retorno.update_layout(separators=",.")
        fig_risco_retorno.update_traces(
            hovertemplate=(
                "<b>Ativo: %{hovertext}</b><br>"
                "Setor: %{customdata[0]}<br>"
                "Volatilidade anualizada: %{x:.2%}<br>"
                "Retorno acumulado: %{y:.2%}<br>"
                "Volume financeiro médio estimado: R$ %{customdata[1]:,.0f}"
                "<extra></extra>"
            )
        )
        fig_risco_retorno.update_xaxes(tickformat=".0%")
        fig_risco_retorno.update_yaxes(tickformat=".0%")
        fig_risco_retorno.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig_risco_retorno, width="stretch")
    else:
        st.warning(
            "Não há dados suficientes para calcular risco e retorno "
            "dos ativos selecionados. Selecione um intervalo com mais pregões."
        )

    st.divider()
    st.subheader("Ranking do Índice de Sharpe")
    st.caption(
        "Sharpe anualizado simplificado, assumindo taxa livre de risco igual a 0% a.a. "
        "Valores maiores representam maior retorno médio por unidade de volatilidade. "
        "É uma medida histórica, não uma previsão de desempenho futuro."
    )

    ranking_sharpe = estatisticas_ativos.dropna(
        subset=["sharpe_simplificado"]
    ).sort_values("sharpe_simplificado", ascending=False)[
        [
            "ticker",
            "retorno_acumulado",
            "volatilidade_anualizada",
            "sharpe_simplificado",
        ]
    ].rename(
        columns={
            "ticker": "Ativo",
            "retorno_acumulado": "Retorno acumulado",
            "volatilidade_anualizada": "Volatilidade anualizada",
            "sharpe_simplificado": "Sharpe simplificado",
        }
    )

    if not ranking_sharpe.empty:
        ranking_sharpe_exibicao = ranking_sharpe.copy()
        ranking_sharpe_exibicao["Retorno acumulado"] = (
            ranking_sharpe_exibicao["Retorno acumulado"].map(formatar_percentual)
        )
        ranking_sharpe_exibicao["Volatilidade anualizada"] = (
            ranking_sharpe_exibicao["Volatilidade anualizada"].map(formatar_percentual)
        )
        ranking_sharpe_exibicao["Sharpe simplificado"] = (
            ranking_sharpe_exibicao["Sharpe simplificado"].map(
                lambda valor: formatar_numero_ptbr(valor, casas=3)
            )
        )
        st.dataframe(ranking_sharpe_exibicao, width="stretch", hide_index=True)
    else:
        st.info("Não há observações suficientes para calcular o índice de Sharpe.")

    st.divider()
    st.subheader("Distribuição dos retornos diários")
    st.caption(
        "As barras mostram a frequência dos retornos diários em diferentes faixas. "
        "O boxplot acima resume mediana e dispersão; pontos distantes do centro podem "
        "indicar dias atípicos. Caudas longas sugerem que movimentos extremos ocorreram "
        "no período, mas não indicam quando ocorrerão novamente."
    )
    dados_histograma = df_filtrado.dropna(subset=["retorno_diario"]).copy()
    if not dados_histograma.empty:
        fig_histograma = px.histogram(
            dados_histograma,
            x="retorno_diario",
            color="ticker",
            marginal="box",
            barmode="overlay",
            opacity=0.6,
            nbins=60,
            title="Distribuição dos retornos diários por ativo",
            labels={
                "retorno_diario": "Retorno diário",
                "count": "Frequência",
                "ticker": "Ativo",
            },
        )
        fig_histograma.update_layout(
            xaxis_title="Retorno diário",
            yaxis_title="Frequência",
            legend_title="Ativos",
            bargap=0.05,
            separators=",.",
        )
        fig_histograma.update_traces(
            hovertemplate=(
                "<b>Ativo: %{fullData.name}</b><br>"
                "Retorno diário: %{x:.2%}<br>Frequência: %{y}<extra></extra>"
            ),
            selector=dict(type="histogram"),
        )
        fig_histograma.update_traces(
            hovertemplate=("Retorno diário: %{x:.2%}<extra></extra>"),
            selector=dict(type="box"),
        )
        fig_histograma.update_xaxes(tickformat=".1%")
        st.plotly_chart(fig_histograma, width="stretch")
    else:
        st.warning("Não há retornos diários para os filtros selecionados.")

    st.subheader("Estatísticas da distribuição dos retornos")
    st.caption(
        "Assimetria positiva indica uma cauda mais longa à direita; negativa, à esquerda. "
        "A curtose é apresentada como excesso de curtose: valores positivos indicam caudas "
        "mais pesadas do que na distribuição normal e maior presença de retornos extremos. "
        "Interprete essas medidas junto ao histograma; elas descrevem o período histórico."
    )
    estatisticas_distribuicao = (
        retornos_validos[retornos_validos["ticker"].isin(tickers_selecionados)]
        .groupby("ticker")["retorno_diario"]
        .agg(
            assimetria="skew",
            curtose_excesso="kurt",
        )
        .reset_index()
        .rename(
            columns={
                "ticker": "Ativo",
                "assimetria": "Assimetria",
                "curtose_excesso": "Curtose (excesso)",
            }
        )
        .sort_values("Ativo")
    )
    if not estatisticas_distribuicao.empty:
        estatisticas_distribuicao["Assimetria"] = estatisticas_distribuicao["Assimetria"].map(
            lambda valor: formatar_numero_ptbr(valor, casas=3) if pd.notna(valor) else "N/D"
        )
        estatisticas_distribuicao["Curtose (excesso)"] = estatisticas_distribuicao["Curtose (excesso)"].map(
            lambda valor: formatar_numero_ptbr(valor, casas=3) if pd.notna(valor) else "N/D"
        )
        st.dataframe(estatisticas_distribuicao, width="stretch", hide_index=True)
    else:
        st.info("Não há retornos suficientes para calcular as estatísticas da distribuição.")

    st.divider()
    st.subheader("Drawdown histórico")
    st.caption(
        "O drawdown mede a queda do preço ajustado em relação ao pico anterior. "
        "Linhas que descem mais representam perdas mais profundas desde um topo; "
        "a recuperação acontece quando o drawdown volta em direção a 0%. "
        "O indicador mede a trajetória histórica, não a perda máxima futura."
    )
    df_drawdown = df_filtrado.sort_values(["ticker", "data"]).copy()
    df_drawdown["pico_historico"] = df_drawdown.groupby("ticker")[
        "fechamento_ajustado"
    ].cummax()
    df_drawdown["drawdown_pct"] = (
        df_drawdown["fechamento_ajustado"] / df_drawdown["pico_historico"] - 1
    ) * 100

    fig_drawdown = go.Figure()
    for ticker in df_drawdown["ticker"].unique():
        df_ativo_drawdown = df_drawdown[df_drawdown["ticker"] == ticker]
        fig_drawdown.add_trace(
            go.Scatter(
                x=df_ativo_drawdown["data"],
                y=df_ativo_drawdown["drawdown_pct"],
                mode="lines",
                name=ticker,
                line=dict(width=1.6),
                hovertemplate=(
                    "<b>Ativo: " + ticker + "</b><br>"
                    "Data: %{x|%d/%m/%Y}<br>"
                    "Drawdown: %{y:.2f}%<extra></extra>"
                ),
            )
        )
    fig_drawdown.update_layout(
        title="Drawdown ao longo do período",
        xaxis_title="Data",
        yaxis_title="Drawdown",
        hovermode="x unified",
        separators=",.",
        legend_title_text="Ativos",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(t=85, b=40),
        height=520,
    )
    fig_drawdown.update_xaxes(dtick="M3", tickformat="%m/%Y")
    fig_drawdown.update_yaxes(ticksuffix="%", rangemode="tozero")
    st.plotly_chart(fig_drawdown, width="stretch")

    st.divider()
    st.subheader("Drawdown máximo por ativo")
    st.caption(
        "O drawdown máximo é a maior queda percentual de cada ativo em relação ao pico anterior. "
        "Valores mais próximos de zero indicam quedas máximas menos severas no intervalo selecionado."
    )
    resumo_drawdown = (
        df_drawdown.groupby("ticker", as_index=False)
        .agg(drawdown_maximo_pct=("drawdown_pct", "min"))
        .sort_values("drawdown_maximo_pct", ascending=False)
    )
    resumo_drawdown_exibicao = resumo_drawdown.rename(
        columns={
            "ticker": "Ativo",
            "drawdown_maximo_pct": "Drawdown máximo (%)",
        }
    ).copy()
    resumo_drawdown_exibicao["Drawdown máximo (%)"] = (
        resumo_drawdown_exibicao["Drawdown máximo (%)"].map(
            lambda valor: f"{formatar_numero_ptbr(valor, casas=2, milhar=False)}%"
        )
    )
    st.dataframe(resumo_drawdown_exibicao, width="stretch", hide_index=True)

    if not resumo_drawdown.empty:
        ativo_resiliente = resumo_drawdown.iloc[0]
        st.info(
            f"**Ativo mais resiliente no intervalo selecionado:** {ativo_resiliente['ticker']}, "
            f"com drawdown máximo de "
            f"{formatar_numero_ptbr(ativo_resiliente['drawdown_maximo_pct'], casas=2, milhar=False)}%."
        )

# GRÁFICO 5 — PREÇO E MÉDIAS MÓVEIS, AMOSTRA E MÉTRICAS DA BASE
with aba_tendencia:
    st.subheader("Análise de tendência — Médias móveis")
    st.caption(
        "A linha do preço mostra a cotação ajustada; SMA 21 resume os últimos 21 pregões "
        "e SMA 50 os últimos 50. A comparação ajuda a observar tendências de curto e médio prazo. "
        "Cruzamentos são sinais descritivos, não garantias de direção futura."
    )

    ativos_disponiveis = sorted(df_filtrado["ticker"].unique().tolist())
    if ativos_disponiveis:
        ativo_selecionado = st.selectbox(
            "Selecione o ativo para analisar:",
            options=ativos_disponiveis,
            key="ativo_medias_moveis",
        )
        df_ativo = df_filtrado[df_filtrado["ticker"] == ativo_selecionado].copy()
        df_ativo = df_ativo.sort_values("data")
        df_ativo["SMA_21"] = df_ativo["fechamento_ajustado"].rolling(
            window=21, min_periods=21
        ).mean()
        df_ativo["SMA_50"] = df_ativo["fechamento_ajustado"].rolling(
            window=50, min_periods=50
        ).mean()

        fig_medias = go.Figure()
        fig_medias.add_trace(
            go.Scatter(
                x=df_ativo["data"],
                y=df_ativo["fechamento_ajustado"],
                mode="lines",
                name="Preço ajustado",
                line=dict(width=1.5),
                hovertemplate=(
                    "<b>Ativo: " + ativo_selecionado + "</b><br>"
                    "Data: %{x|%d/%m/%Y}<br>Preço ajustado: R$ %{y:,.2f}<extra></extra>"
                ),
            )
        )
        fig_medias.add_trace(
            go.Scatter(
                x=df_ativo["data"],
                y=df_ativo["SMA_21"],
                mode="lines",
                name="SMA 21",
                line=dict(width=2),
                hovertemplate=(
                    "<b>Ativo: " + ativo_selecionado + "</b><br>"
                    "Data: %{x|%d/%m/%Y}<br>SMA 21: R$ %{y:,.2f}<extra></extra>"
                ),
            )
        )
        fig_medias.add_trace(
            go.Scatter(
                x=df_ativo["data"],
                y=df_ativo["SMA_50"],
                mode="lines",
                name="SMA 50",
                line=dict(width=2),
                hovertemplate=(
                    "<b>Ativo: " + ativo_selecionado + "</b><br>"
                    "Data: %{x|%d/%m/%Y}<br>SMA 50: R$ %{y:,.2f}<extra></extra>"
                ),
            )
        )
        fig_medias.update_layout(
            title=f"{ativo_selecionado} — Preço e médias móveis",
            xaxis_title="Data",
            yaxis_title="Preço ajustado (R$)",
            hovermode="x unified",
            separators=",.",
            legend_title="Indicadores",
        )
        fig_medias.update_xaxes(dtick="M3", tickformat="%m/%Y")
        st.plotly_chart(fig_medias, width="stretch")
    else:
        st.warning("Não há ativos disponíveis para os filtros selecionados.")

    st.divider()
    with st.expander("Informações sobre os dados", expanded=False):
        col1, col2, col3 = st.columns(3)
        col1.metric("Registros filtrados", f"{len(df_filtrado):,}".replace(",", "."))
        col2.metric("Ativos selecionados", df_filtrado["ticker"].nunique())
        col3.metric("Setores selecionados", df_filtrado["setor"].nunique())
        st.write("Amostra dos dados filtrados")
        st.caption(
            "Amostra dos registros que atendem aos filtros. Valores numéricos são apresentados "
            "com vírgula decimal; a exportação mantém as colunas em formato de dados para análise."
        )
        amostra = df_filtrado.head(20).copy()
        amostra["data"] = amostra["data"].dt.strftime("%d/%m/%Y")
        colunas_decimal = [
            "abertura", "maxima", "minima", "fechamento", "fechamento_ajustado",
            "retorno_diario", "retorno_acumulado",
        ]
        for coluna in colunas_decimal:
            if coluna in amostra.columns:
                amostra[coluna] = amostra[coluna].map(
                    lambda valor: formatar_numero_ptbr(valor, casas=2) if pd.notna(valor) else "N/D"
                )
        if "volume_financeiro_estimado" in amostra.columns:
            amostra["volume_financeiro_estimado"] = amostra["volume_financeiro_estimado"].map(
                lambda valor: (
                    "R$ " + formatar_numero_ptbr(valor, casas=0)
                    if pd.notna(valor) else "N/D"
                )
            )
        if "volume" in amostra.columns:
            amostra["volume"] = amostra["volume"].map(
                lambda valor: formatar_numero_ptbr(valor, casas=0) if pd.notna(valor) else "N/D"
            )
        st.dataframe(amostra, width="stretch", hide_index=True)

# --------------------------------------------------
# NOTA METODOLÓGICA
# --------------------------------------------------

with st.expander("📌 Nota metodológica e limitações da análise"):
    st.markdown("""
    **Retornos e volatilidade**

    Os retornos são calculados com base nos preços de fechamento ajustados. A volatilidade anualizada utiliza o desvio-padrão dos retornos diários multiplicado pela raiz quadrada de 252 pregões.

    **Volume negociado**

    O volume original da base representa a quantidade de ações negociadas. Para dimensionar as bolhas, o volume financeiro é estimado por preço de fechamento × quantidade negociada; não equivale ao volume financeiro oficial de cada negócio.

    **Índice de Sharpe**

    O Sharpe apresentado é simplificado e assume taxa livre de risco de 0% ao ano. Os resultados podem diferir de cálculos que utilizem uma taxa histórica, como a Selic.

    **Limitações**

    A análise cobre o período de 2021 a 2023. Resultados passados não garantem desempenho futuro, e associações estatísticas não demonstram causalidade.
    """)
