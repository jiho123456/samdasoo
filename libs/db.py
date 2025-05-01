# libs/db.py
import streamlit as st
import psycopg2

@st.cache_resource
def get_conn():
    try:
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
    except Exception as e:
        st.error(f"데이터베이스 연결 오류: {str(e)}")
        raise e

def init_tables():
    """
    최초 1회만 실행하세요. 
    여기서는 별도 임시 커넥션을 사용하고, 
    캐시된 get_conn() 커넥션은 닫지 않습니다.
    """
    try:
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

        # Users 테이블 생성 (with roles and currency)
        tmp_cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('teacher', 'student')),
                currency INTEGER DEFAULT 0,
                job_id INTEGER,
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)

        # Jobs 테이블 생성
        tmp_cur.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                salary INTEGER NOT NULL,
                description TEXT,
                created_by INTEGER REFERENCES users(user_id),
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)

        # Quests/Missions 테이블 생성
        tmp_cur.execute("""
            CREATE TABLE IF NOT EXISTS quests (
                quest_id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                reward INTEGER NOT NULL,
                created_by INTEGER REFERENCES users(user_id),
                is_daily BOOLEAN DEFAULT false,
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)

        # Quest Completions 테이블 생성
        tmp_cur.execute("""
            CREATE TABLE IF NOT EXISTS quest_completions (
                completion_id SERIAL PRIMARY KEY,
                quest_id INTEGER REFERENCES quests(quest_id),
                user_id INTEGER REFERENCES users(user_id),
                completed_at TIMESTAMPTZ DEFAULT now(),
                verified_by INTEGER REFERENCES users(user_id),
                verified_at TIMESTAMPTZ
            );
        """)

        # Transactions 테이블 생성
        tmp_cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id SERIAL PRIMARY KEY,
                from_user_id INTEGER REFERENCES users(user_id),
                to_user_id INTEGER REFERENCES users(user_id),
                amount INTEGER NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('salary', 'quest', 'transfer')),
                description TEXT,
                created_by INTEGER REFERENCES users(user_id),
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)

        # Stocks 테이블 생성
        tmp_cur.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                stock_id SERIAL PRIMARY KEY,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL,
                current_price DECIMAL(10,2) NOT NULL,
                last_updated TIMESTAMPTZ DEFAULT now()
            );
        """)

        # Stock Portfolios 테이블 생성
        tmp_cur.execute("""
            CREATE TABLE IF NOT EXISTS stock_portfolios (
                portfolio_id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(user_id),
                stock_id INTEGER REFERENCES stocks(stock_id),
                quantity INTEGER NOT NULL,
                average_price DECIMAL(10,2) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            );
        """)

        # Stock Transactions 테이블 생성
        tmp_cur.execute("""
            CREATE TABLE IF NOT EXISTS stock_transactions (
                transaction_id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(user_id),
                stock_id INTEGER REFERENCES stocks(stock_id),
                type TEXT NOT NULL CHECK (type IN ('buy', 'sell')),
                quantity INTEGER NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                total_amount DECIMAL(10,2) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)

        tmp_conn.commit()
        st.success("데이터베이스 테이블이 성공적으로 생성되었습니다!")
    except Exception as e:
        st.error(f"데이터베이스 초기화 오류: {str(e)}")
        raise e
    finally:
        tmp_conn.close()  # 여기만 닫고, 캐시된 커넥션은 손대지 않습니다.
