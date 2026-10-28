
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sqlalchemy import text

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
# CONEXÃO E CARREGAMENTO DOS DADOS
# --------------------------------------------------

@st.cache_data(ttl=600)
def carregar_dados():
    conn = st.connection("postgresql", type="sql")

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

    df = conn.query(query, ttl=600)

    df["data"] = pd.to_datetime(df["data"])
    df["ticker"] = df["ticker"].astype(str)
    df["setor"] = df["setor"].astype(str)

    colunas_numericas = [
        "abertura",
        "maxima",
        "minima",
        "fechamento",
        "fechamento_ajustado",
        "volume",
    ]

    for coluna in colunas_numericas:
        df[coluna] = pd.to_numeric(
            df[coluna],
            errors="coerce",
        )

    return df


try:
    df = carregar_dados()

except Exception as erro:
    st.error(
        "Não foi possível carregar os dados do PostgreSQL. "
        "Confira a conexão e as credenciais do Supabase."
    )

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

if "reset_filtros" not in st.session_state:
    st.session_state["reset_filtros"] = False


def resetar_filtros():
    st.session_state["filtro_tickers"] = df["ticker"].unique().tolist()
    st.session_state["filtro_setores"] = df["setor"].unique().tolist()
    st.session_state["filtro_datas"] = (
        df["data"].min().date(),
        df["data"].max().date(),
    )


if st.sidebar.button("Limpar filtros"):
    resetar_filtros()


tickers_disponiveis = sorted(df["ticker"].unique().tolist())
setores_disponiveis = sorted(df["setor"].unique().tolist())

if "filtro_tickers" not in st.session_state:
    st.session_state["filtro_tickers"] = tickers_disponiveis

if "filtro_setores" not in st.session_state:
    st.session_state["filtro_setores"] = setores_disponiveis

if "filtro_datas" not in st.session_state:
    st.session_state["filtro_datas"] = (
        df["data"].min().date(),
        df["data"].max().date(),
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
    min_value=df["data"].min().date(),
    max_value=df["data"].max().date(),
    key="filtro_datas",
)

if not isinstance(periodo, (tuple, list)) or len(periodo) != 2:
    st.info("Selecione a data inicial e a data final.")
    st.stop()

data_inicial, data_final = periodo

if data_inicial > data_final:
    st.error("A data inicial não pode ser posterior à data final.")
    st.stop()


df_filtrado = df[
    df["ticker"].isin(tickers_selecionados)
    & df["setor"].isin(setores_selecionados)
    & (df["data"].dt.date >= data_inicial)
    & (df["data"].dt.date <= data_final)
].copy()


if df_filtrado.empty:
    st.warning(
        "Nenhum registro encontrado com os filtros selecionados."
    )
    st.stop()


# --------------------------------------------------
# CÁLCULOS FINANCEIROS
# --------------------------------------------------

# Usamos fechamento ajustado para os retornos,
# reduzindo distorções causadas por proventos e eventos
# societários, conforme os dados fornecidos pela fonte.

df_filtrado = df_filtrado.sort_values(["ticker", "data"])

df_filtrado["retorno_diario"] = (
    df_filtrado.groupby("ticker")["fechamento_ajustado"]
    .pct_change()
)

retornos = df_filtrado.dropna(subset=["retorno_diario"]).copy()

retorno_acumulado = (
    df_filtrado.groupby("ticker")
    .apply(
        lambda grupo: (
            grupo["fechamento_ajustado"]
            / grupo["fechamento_ajustado"].iloc[0]
            - 1
        ),
        include_groups=False,
    )
    .reset_index(level=0, drop=True)
)

df_filtrado["retorno_acumulado"] = retorno_acumulado

retornos_por_ativo = (
    df_filtrado.groupby("ticker")
    .apply(
        lambda grupo: (
            grupo["fechamento_ajustado"].iloc[-1]
            / grupo["fechamento_ajustado"].iloc[0]
            - 1
        ),
        include_groups=False,
    )
    .dropna()    
)

volatilidade_por_ativo = (
    retornos.groupby("ticker")["retorno_diario"]
    .std()
    * np.sqrt(252)
)

retorno_medio_carteira = retornos_por_ativo.mean()

if not retornos_por_ativo.empty:
    melhor_ativo = retornos_por_ativo.idxmax()
    melhor_retorno = retornos_por_ativo.max()

    pior_ativo = retornos_por_ativo.idxmin()
    pior_retorno = retornos_por_ativo.min()
else:
    melhor_ativo = "N/D"
    melhor_retorno = np.nan
    pior_ativo = "N/D"
    pior_retorno = np.nan

volatilidade_media = volatilidade_por_ativo.mean()


# --------------------------------------------------
# KPIs
# --------------------------------------------------

st.subheader("Indicadores de desempenho")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Retorno médio dos ativos",
    f"{retorno_medio_carteira:.2%}",
)

col2.metric(
    "Melhor ativo",
    melhor_ativo,
    f"{melhor_retorno:.2%}",
)

col3.metric(
    "Pior ativo",
    pior_ativo,
    f"{pior_retorno:.2%}",
)

col4.metric(
    "Volatilidade anualizada média",
    f"{volatilidade_media:.2%}",
)


# --------------------------------------------------
# GRÁFICO 1 — RETORNO ACUMULADO BASE 100
# --------------------------------------------------

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
    legend_title_text="Ativos",
)

st.plotly_chart(fig_retorno, use_container_width=True)


# --------------------------------------------------
# GRÁFICO 2 — RISCO VERSUS RETORNO
# --------------------------------------------------

st.subheader("Risco versus retorno")

# Calcula os indicadores individualmente para cada ativo.
# O volume representa o volume financeiro? Não: a base contém
# volume negociado em quantidade de ações.

estatisticas_ativos = (
    df_filtrado.sort_values(["ticker", "data"])
    .groupby(["ticker", "setor"], as_index=False)
    .apply(
        lambda grupo: pd.Series({
            "retorno_acumulado": (
                grupo["fechamento_ajustado"].iloc[-1]
                / grupo["fechamento_ajustado"].iloc[0]
                - 1
            ),
            "volatilidade_anualizada": (
                grupo["retorno_diario"].std() * np.sqrt(252)
            ),
            "volume_medio": grupo["volume"].mean(),
        }),
        include_groups=False,
    )
    .reset_index(drop=True)
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
            "volatilidade_anualizada": "Volatilidade anualizada (% a.a.)",
            "retorno_acumulado": "Retorno acumulado (%)",
            "volume_medio": "Volume médio negociado",
            "setor": "Setor",
        },
        size_max=45,
    )

    fig_risco_retorno.update_xaxes(tickformat=".0%")
    fig_risco_retorno.update_yaxes(tickformat=".0%")

    fig_risco_retorno.add_hline(
        y=0,
        line_dash="dash",
        line_color="gray",
    )

    st.plotly_chart(
        fig_risco_retorno,
        use_container_width=True,
    )

else:
    st.warning(
        "Não há dados suficientes para calcular risco e retorno "
        "dos ativos selecionados."
    )



# --------------------------------------------------
# GRÁFICO 3 — HISTOGRAMA DE RETORNOS DIÁRIOS
# --------------------------------------------------

st.subheader("Distribuição dos retornos diários")

import plotly.express as px

# Considera somente retornos diários válidos
dados_histograma = df_filtrado.dropna(
    subset=["retorno_diario"]
).copy()

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
            "retorno_diario": "Retorno diário (%)",
            "count": "Frequência",
            "ticker": "Ativo",
        },
    )

    fig_histograma.update_layout(
        xaxis_title="Retorno diário (%)",
        yaxis_title="Frequência",
        legend_title="Ativos",
        bargap=0.05,
    )

    st.plotly_chart(
        fig_histograma,
        use_container_width=True,
    )
else:
    st.warning(
        "Não há retornos diários disponíveis para os filtros selecionados."
    )


# --------------------------------------------------
# GRÁFICO 4 — ÁREA DE DRAWDOWN
# --------------------------------------------------

st.subheader("Drawdown histórico")

st.caption(
    "Queda percentual do preço ajustado em relação ao maior "
    "valor registrado até cada data."
)

# Prepara os dados filtrados
df_drawdown = df_filtrado.copy()

# Garante a ordenação cronológica por ativo
df_drawdown = df_drawdown.sort_values(["ticker", "data"])

# Remove registros sem preço válido
df_drawdown = df_drawdown.dropna(
    subset=["fechamento_ajustado"]
)

# Calcula o maior preço ajustado registrado até cada data
df_drawdown["pico_historico"] = (
    df_drawdown.groupby("ticker")["fechamento_ajustado"]
    .cummax()
)

# Calcula o drawdown percentual
df_drawdown["drawdown_pct"] = (
    (
        df_drawdown["fechamento_ajustado"]
        / df_drawdown["pico_historico"]
    ) - 1
) * 100

# Cria o gráfico
import plotly.graph_objects as go

fig_drawdown = go.Figure()

for ticker in df_drawdown["ticker"].unique():

    df_ativo = df_drawdown[
        df_drawdown["ticker"] == ticker
    ].sort_values("data")

    fig_drawdown.add_trace(
        go.Scatter(
            x=df_ativo["data"],
            y=df_ativo["drawdown_pct"],
            mode="lines",
            name=ticker,
            fill="tozeroy",
            hovertemplate=(
                "<b>" + ticker + "</b><br>"
                "Data: %{x|%d/%m/%Y}<br>"
                "Drawdown: %{y:.2f}%"
                "<extra></extra>"
            ),
        )
    )

fig_drawdown.update_layout(
    title="Queda percentual em relação ao pico histórico",
    xaxis_title="Data",
    yaxis_title="Drawdown (%)",
    hovermode="x unified",
    legend_title="Ativos",
)

fig_drawdown.update_yaxes(
    ticksuffix="%",
    rangemode="tozero",
)

st.plotly_chart(
    fig_drawdown,
    use_container_width=True,
)



# --------------------------------------------------
# GRÁFICO 5 — PREÇO E MÉDIAS MÓVEIS
# --------------------------------------------------

st.subheader("Análise de tendência — Médias móveis")

st.caption(
    "Compare o preço ajustado com as médias móveis simples "
    "de 21 e 50 pregões."
)

# Cria uma cópia dos dados para o cálculo
df_medias = df_filtrado.copy()

# Garante a ordenação cronológica
df_medias = df_medias.sort_values(["ticker", "data"])

# Remove registros sem preço ajustado
df_medias = df_medias.dropna(
    subset=["fechamento_ajustado"]
)

# Lista os ativos disponíveis nos filtros
ativos_disponiveis = sorted(
    df_medias["ticker"].unique().tolist()
)

if ativos_disponiveis:

    ativo_selecionado = st.selectbox(
        "Selecione o ativo para analisar:",
        options=ativos_disponiveis,
        key="ativo_medias_moveis",
    )

    # Seleciona o ativo escolhido
    df_ativo = df_medias[
        df_medias["ticker"] == ativo_selecionado
    ].copy()

    # Calcula as médias móveis por número de pregões
    df_ativo["SMA_21"] = (
        df_ativo["fechamento_ajustado"]
        .rolling(window=21, min_periods=21)
        .mean()
    )

    df_ativo["SMA_50"] = (
        df_ativo["fechamento_ajustado"]
        .rolling(window=50, min_periods=50)
        .mean()
    )

    # Cria o gráfico
    import plotly.graph_objects as go

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

    st.plotly_chart(
        fig_medias,
        use_container_width=True,
    )

else:
    st.warning(
        "Não há ativos disponíveis para os filtros selecionados."
    )


# --------------------------------------------------
# INFORMAÇÕES DA BASE
# --------------------------------------------------

with st.expander("Informações sobre os dados"):
    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Registros filtrados",
        f"{len(df_filtrado):,}".replace(",", "."),
    )

    col2.metric(
        "Ativos selecionados",
        df_filtrado["ticker"].nunique(),
    )

    col3.metric(
        "Setores selecionados",
        df_filtrado["setor"].nunique(),
    )

    st.write("Amostra dos dados filtrados")

    st.dataframe(
        df_filtrado.head(20),
        use_container_width=True,
    )
