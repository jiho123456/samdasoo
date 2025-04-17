import streamlit as st
import psycopg2

@st.cache_resource
def get_conn():
    conn = psycopg2.connect(
        user=st.secrets["user"],
        password=st.secrets["password"],
        host=st.secrets["host"],
        port=st.secrets["port"],
        dbname=st.secrets["dbname"],
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5
    )
    conn.autocommit = True   # 트랜잭션 자동 커밋
    return conn

def init_tables():
    """
    최초 1회만 실행하세요. 
    kicked_users 테이블을 생성합니다.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kicked_users (
            username TEXT PRIMARY KEY,
            reason   TEXT NOT NULL,
            kicked_at TIMESTAMPTZ DEFAULT now()
        );
    """)
    conn.commit()
