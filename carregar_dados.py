
import pandas as pd
import yfinance as yf
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

# Ativos definidos no enunciado
ATIVOS = {
    "WEGE3.SA": "Bens industriais",
    "EMBJ3.SA": "Aeroespacial",
    "VALE3.SA": "Mineração",
    "GGBR4.SA": "Siderurgia",
    "KLBN11.SA": "Papel e celulose",
    "PETR4.SA": "Petróleo e gás",
    "PRIO3.SA": "Petróleo e gás",
    "EGIE3.SA": "Energia elétrica",
    "ITUB4.SA": "Bancário",
    "BBDC4.SA": "Bancário",
    "ABEV3.SA": "Bebidas",
    "RENT3.SA": "Locação de veículos",
}


def criar_engine():
    """Cria a conexão com PostgreSQL usando os secrets do Streamlit."""
    config = st.secrets["connections"]["postgresql"]

    url = URL.create(
        drivername="postgresql+psycopg",
        username=config["username"],
        password=config["password"],
        host=config["host"],
        port=int(config["port"]),
        database=config["database"],
    )

    return create_engine(url)


def baixar_dados():
    """Baixa os preços históricos de 2021 a 2023."""
    registros = []

    for ticker, setor in ATIVOS.items():
        print(f"Baixando {ticker}...")

        try:
            dados = yf.download(
                ticker,
                start="2021-01-01",
                end="2024-01-01",
                auto_adjust=False,
                progress=False,
                threads=False,
            )

            if dados.empty:
                print(f"AVISO: nenhum dado retornado para {ticker}.")
                continue

            # Trata tanto colunas simples quanto MultiIndex do yfinance.
            if isinstance(dados.columns, pd.MultiIndex):
                dados.columns = dados.columns.get_level_values(0)

            dados = dados.reset_index()

            if "Adj Close" not in dados.columns:
                print(f"AVISO: preço ajustado ausente para {ticker}.")
                continue

            dados["ticker"] = ticker.removesuffix(".SA")
            dados["setor"] = setor

            dados = dados.rename(
                columns={
                    "Date": "data",
                    "Open": "abertura",
                    "High": "maxima",
                    "Low": "minima",
                    "Close": "fechamento",
                    "Adj Close": "fechamento_ajustado",
                    "Volume": "volume",
                }
            )

            colunas = [
                "data",
                "ticker",
                "setor",
                "abertura",
                "maxima",
                "minima",
                "fechamento",
                "fechamento_ajustado",
                "volume",
            ]

            dados = dados[colunas].copy()
            dados["data"] = pd.to_datetime(dados["data"]).dt.date

            for coluna in [
                "abertura",
                "maxima",
                "minima",
                "fechamento",
                "fechamento_ajustado",
            ]:
                dados[coluna] = pd.to_numeric(
                    dados[coluna], errors="coerce"
                )

            dados["volume"] = pd.to_numeric(
                dados["volume"], errors="coerce"
            ).astype("Int64")

            dados = dados.dropna(
                subset=["data", "fechamento", "fechamento_ajustado"]
            )

            registros.append(dados)
            print(f"  {len(dados)} registros encontrados.")

        except Exception as erro:
            print(f"ERRO em {ticker}: {erro}")

    if not registros:
        raise RuntimeError("Nenhum dado foi baixado. Verifique a conexão e os tickers.")

    return pd.concat(registros, ignore_index=True)


def gravar_dados(dados):
    """Insere somente registros que ainda não existem."""
    engine = criar_engine()

    try:
        with engine.begin() as conexao:
            conexao.exec_driver_sql("""
                CREATE TEMP TABLE staging_acoes
                (LIKE public.historico_acoes INCLUDING DEFAULTS)
                ON COMMIT DROP
            """)

            dados.to_sql(
                "staging_acoes",
                con=conexao,
                if_exists="append",
                index=False,
                chunksize=1000,
                method="multi",
            )

            conexao.exec_driver_sql("""
                INSERT INTO public.historico_acoes (
                    data, ticker, setor, abertura, maxima, minima,
                    fechamento, fechamento_ajustado, volume
                )
                SELECT
                    data, ticker, setor, abertura, maxima, minima,
                    fechamento, fechamento_ajustado, volume
                FROM staging_acoes
                ON CONFLICT (data, ticker) DO NOTHING
            """)

            total = conexao.exec_driver_sql("""
                SELECT COUNT(*)
                FROM public.historico_acoes
            """).scalar_one()

        print(f"Total de registros na tabela: {total}")

    finally:
        engine.dispose()


if __name__ == "__main__":
    print("Iniciando download dos dados históricos...")
    historico = baixar_dados()

    print(f"\nTotal baixado: {len(historico)} registros.")
    print("\nGravando dados no PostgreSQL...")

    gravar_dados(historico)

    print("\nCarga concluída!")
