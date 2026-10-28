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


def resetar_filtros():
    st.session_state["filtro_tickers"] = tickers_disponiveis.copy()
    st.session_state["filtro_setores"] = setores_disponiveis.copy()
    st.session_state["filtro_datas"] = (data_minima, data_maxima)


if "filtro_tickers" not in st.session_state:
    st.session_state["filtro_tickers"] = tickers_disponiveis.copy()
if "filtro_setores" not in st.session_state:
    st.session_state["filtro_setores"] = setores_disponiveis.copy()
if "filtro_datas" not in st.session_state:
    st.session_state["filtro_datas"] = (data_minima, data_maxima)

st.sidebar.button(
    "Limpar filtros",
    on_click=resetar_filtros,
    width="stretch",
)

tickers_selecionados = st.sidebar.multiselect(
    "Ativos",
    options=tickers_disponiveis,
    key="filtro_tickers",
)

setores_selecionados = st.sidebar.multiselect(
    "Setores",
    options=setores_disponiveis,
    key="filtro_setores",
)

periodo = st.sidebar.date_input(
    "Período da análise",
    min_value=data_minima,
    max_value=data_maxima,
    key="filtro_datas",
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
    & df["setor"].isin(setores_selecionados)
    & (df["data"].dt.date >= data_inicial)
    & (df["data"].dt.date <= data_final)
].copy()

if df_filtrado.empty:
    st.warning("Nenhum registro encontrado com os filtros selecionados.")
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


def formatar_percentual(valor):
    return f"{valor:.2%}" if pd.notna(valor) else "N/D"


def formatar_delta(valor, complemento=""):
    if pd.isna(valor):
        return "N/D"
    return f"{valor:+.2%}{complemento}"

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

# Exportação dos dados filtrados, incluindo os retornos calculados.
csv_filtrado = df_filtrado.to_csv(index=False, date_format="%Y-%m-%d").encode("utf-8-sig")
st.download_button(
    "Baixar dados filtrados (CSV)",
    data=csv_filtrado,
    file_name="b3_dados_filtrados.csv",
    mime="text/csv",
    width="content",
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
    fig_retorno.update_layout(hovermode="x unified", legend_title_text="Ativos")
    st.plotly_chart(fig_retorno, width="stretch")

    st.caption(
        "Cada ativo começa em 100 na primeira data do intervalo selecionado. "
        "Valores acima de 100 indicam valorização no período; abaixo de 100, desvalorização."
    )

# GRÁFICOS 2, 3 E 4 — RISCO, DISTRIBUIÇÃO E DRAWDOWN
with aba_risco:
    st.subheader("Risco versus retorno")
    estatisticas_ativos = (
        df_filtrado.sort_values(["ticker", "data"])
        .groupby(["ticker", "setor"])
        .agg(
            preco_inicial=("fechamento_ajustado", "first"),
            preco_final=("fechamento_ajustado", "last"),
            desvio_diario=("retorno_diario", "std"),
            volume_medio=("volume", "mean"),
        )
        .reset_index()
    )
    estatisticas_ativos["retorno_acumulado"] = (
        estatisticas_ativos["preco_final"] / estatisticas_ativos["preco_inicial"] - 1
    )
    estatisticas_ativos["volatilidade_anualizada"] = (
        estatisticas_ativos["desvio_diario"] * np.sqrt(252)
    )
    estatisticas_ativos = estatisticas_ativos.dropna(
        subset=["retorno_acumulado", "volatilidade_anualizada"]
    )

    if not estatisticas_ativos.empty:
        fig_risco_retorno = px.scatter(
            estatisticas_ativos,
            x="volatilidade_anualizada",
            y="retorno_acumulado",
            size="volume_medio",
            color="setor",
            hover_name="ticker",
            title="Risco anualizado versus retorno acumulado por ativo",
            labels={
                "volatilidade_anualizada": "Volatilidade anualizada",
                "retorno_acumulado": "Retorno acumulado",
                "volume_medio": "Volume médio (ações negociadas)",
                "setor": "Setor",
            },
            size_max=45,
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
    st.subheader("Distribuição dos retornos diários")
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
        )
        fig_histograma.update_xaxes(tickformat=".1%")
        st.plotly_chart(fig_histograma, width="stretch")
    else:
        st.warning("Não há retornos diários para os filtros selecionados.")

    st.divider()
    st.subheader("Drawdown histórico")
    st.caption(
        "Queda percentual do preço ajustado em relação ao maior valor registrado "
        "até cada data dentro do período selecionado."
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
                fill="tozeroy",
                hovertemplate=(
                    "<b>" + ticker + "</b><br>"
                    "Data: %{x|%d/%m/%Y}<br>"
                    "Drawdown: %{y:.2f}%<extra></extra>"
                ),
            )
        )
    fig_drawdown.update_layout(
        title="Queda percentual em relação ao pico do período",
        xaxis_title="Data",
        yaxis_title="Drawdown",
        hovermode="x unified",
        legend_title="Ativos",
    )
    fig_drawdown.update_yaxes(ticksuffix="%", rangemode="tozero")
    st.plotly_chart(fig_drawdown, width="stretch")

# GRÁFICO 5 — PREÇO E MÉDIAS MÓVEIS, AMOSTRA E MÉTRICAS DA BASE
with aba_tendencia:
    st.subheader("Análise de tendência — Médias móveis")
    st.caption(
        "Compare o preço ajustado com as médias móveis simples de 21 e 50 pregões."
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
            )
        )
        fig_medias.add_trace(
            go.Scatter(
                x=df_ativo["data"],
                y=df_ativo["SMA_21"],
                mode="lines",
                name="SMA 21",
                line=dict(width=2),
            )
        )
        fig_medias.add_trace(
            go.Scatter(
                x=df_ativo["data"],
                y=df_ativo["SMA_50"],
                mode="lines",
                name="SMA 50",
                line=dict(width=2),
            )
        )
        fig_medias.update_layout(
            title=f"{ativo_selecionado} — Preço e médias móveis",
            xaxis_title="Data",
            yaxis_title="Preço ajustado (R$)",
            hovermode="x unified",
            legend_title="Indicadores",
        )
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
        st.dataframe(df_filtrado.head(20), width="stretch")

# --------------------------------------------------
# NOTA METODOLÓGICA
# --------------------------------------------------

st.caption(
    "Nota metodológica: resultados históricos não garantem retornos futuros. "
    "A volatilidade é uma estimativa baseada nos retornos diários disponíveis. "
    "O volume apresentado representa quantidade de ações, não valor financeiro. "
    "A análise é descritiva e não demonstra causalidade."
)
