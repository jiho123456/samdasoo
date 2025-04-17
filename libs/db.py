# libs/db.py
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
    conn.autocommit = True
    return conn

def init_tables():
    """
    최초 1회만 실행하세요. 
    여기서는 별도 임시 커넥션을 사용하고, 
    캐시된 get_conn() 커넥션은 닫지 않습니다.
    """
    # 임시 커넥션
    tmp_conn = psycopg2.connect(
        user=st.secrets["user"],
        password=st.secrets["password"],
        host=st.secrets["host"],
        port=st.secrets["port"],
        dbname=st.secrets["dbname"]
    )
    tmp_cur = tmp_conn.cursor()

    # kicked_users 테이블 생성
    tmp_cur.execute("""
        CREATE TABLE IF NOT EXISTS kicked_users (
            username TEXT PRIMARY KEY,
            reason   TEXT NOT NULL,
            kicked_at TIMESTAMPTZ DEFAULT now()
        );
    """)
    tmp_conn.commit()
    tmp_conn.close()  # 여기만 닫고, 캐시된 커넥션은 손대지 않습니다.
