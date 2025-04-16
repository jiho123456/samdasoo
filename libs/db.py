import psycopg2, streamlit as st

@st.cache_resource
def get_conn():
    return psycopg2.connect(
        user=st.secrets["user"],
        password=st.secrets["password"],
        host=st.secrets["host"],
        port=st.secrets["port"],
        dbname=st.secrets["dbname"],
        keepalives=1, keepalives_idle=30,
        keepalives_interval=10, keepalives_count=5
    )
