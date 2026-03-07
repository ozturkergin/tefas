import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

def get_db_engine():
    host = st.session_state.get("POSTGRES_HOST", "postgre_db")
    port = st.session_state.get("POSTGRES_PORT", 5432)
    db = st.session_state.get("POSTGRES_DB", "postgres")
    user = st.session_state.get("POSTGRES_USER", "postgres")
    password = st.session_state.get("POSTGRES_PASSWORD", "postgres")
    return create_engine(f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}')

@st.cache_data(ttl=3600, show_spinner=False)
def read_table(table_name, parse_dates=None, filter_condition=None):
    engine = get_db_engine()
    query = f'SELECT * FROM "{table_name}"'
    if filter_condition:
        query += f' WHERE {filter_condition}'
    df = pd.read_sql(query, engine, parse_dates=parse_dates)
    engine.dispose()
    return df