import streamlit as st
import pandas as pd
from sqlalchemy import text

st.set_page_config(
    page_title="B3 Market Analysis",
    page_icon="📈",
    layout="wide",
)

st.title("📈 B3 Market Analysis")
st.write("Teste de conexão com o PostgreSQL.")

try:
    conn = st.connection("postgresql", type="sql")

    resultado = conn.query(
        "SELECT version() AS versao, current_database() AS banco",
        ttl=0,
    )

    st.success("Conexão com PostgreSQL estabelecida!")

    st.write("Banco de dados:")
    st.dataframe(resultado, use_container_width=True)

except Exception as erro:
    st.error("Não foi possível conectar ao PostgreSQL.")
    st.exception(erro)