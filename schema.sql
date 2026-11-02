CREATE TABLE IF NOT EXISTS public.historico_acoes (
    data DATE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    setor VARCHAR(100),
    abertura NUMERIC(18,6),
    maxima NUMERIC(18,6),
    minima NUMERIC(18,6),
    fechamento NUMERIC(18,6),
    fechamento_ajustado NUMERIC(18,6),
    volume BIGINT
);

CREATE UNIQUE INDEX IF NOT EXISTS
    ux_historico_acoes_data_ticker
ON public.historico_acoes (data, ticker);