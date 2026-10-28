import pandas as pd
from sqlalchemy import text

from carregar_dados import criar_engine

engine = criar_engine()

try:
    query = text("""
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
    """)

    with engine.connect() as conexao:
        df = pd.read_sql(query, conexao)

    if df.empty:
        raise RuntimeError("A tabela do banco não contém registros.")

    df.to_csv(
        "historico_acoes.csv",
        index=False,
        encoding="utf-8",
    )

    print(f"CSV criado com {len(df)} registros.")
    print("Arquivo: historico_acoes.csv")

finally:
    engine.dispose()