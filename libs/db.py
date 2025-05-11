# libs/db.py
import streamlit as st
import psycopg2
import psycopg2.errors
import time

# Remove cache to prevent connection from being reused
def get_conn():
    """
    데이터베이스 연결을 가져오거나 새로 생성합니다.
    항상 새로운 연결을 반환하여 "connection already closed" 오류를 방지합니다.
    """
    try:
        # Always create a brand new connection
        conn = psycopg2.connect(
            user=st.secrets["user"],
            password=st.secrets["password"],
            host=st.secrets["host"],
            port=st.secrets["port"],
            dbname=st.secrets["dbname"],
            # Connection timeout parameters
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

def db_operation(operation_func, error_msg="데이터베이스 작업 중 오류가 발생했습니다"):
    """
    데이터베이스 작업을 안전하게 수행하는 헬퍼 함수입니다.
    
    Args:
        operation_func: 실행할 함수 (conn 인자를 받아야 함)
        error_msg: 오류 발생 시 표시할 메시지
    
    Returns:
        작업 결과
    """
    conn = None
    try:
        # Get a fresh connection
        conn = get_conn()
        # Execute the operation
        return operation_func(conn)
    except Exception as e:
        st.error(f"{error_msg}: {str(e)}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
        raise e
    finally:
        # Always close the connection
        if conn:
            try:
                conn.close()
            except:
                pass

def select_query(query, params=None, fetch_all=True):
    """
    SELECT 쿼리를 실행하고 결과를 반환합니다.
    
    Args:
        query: SQL 쿼리
        params: 쿼리 파라미터
        fetch_all: True면 fetchall(), False면 fetchone() 호출
    
    Returns:
        쿼리 결과
    """
    def execute(conn):
        cur = conn.cursor()
        cur.execute(query, params)
        result = cur.fetchall() if fetch_all else cur.fetchone()
        cur.close()
        return result
    
    return db_operation(execute, f"쿼리 실행 오류: {query}")

def execute_query(query, params=None):
    """
    INSERT, UPDATE, DELETE 쿼리 등을 실행합니다.
    
    Args:
        query: SQL 쿼리
        params: 쿼리 파라미터
    
    Returns:
        영향 받은 행 수
    """
    def execute(conn):
        cur = conn.cursor()
        cur.execute(query, params)
        result = cur.rowcount
        cur.close()
        return result
    
    return db_operation(execute, f"쿼리 실행 오류: {query}")

def init_tables(force_recreate=False):
    """
    데이터베이스 테이블을 초기화합니다.
    
    Args:
        force_recreate (bool): True인 경우 기존 테이블을 모두 삭제하고 새로 생성합니다.
                              False인 경우 존재하지 않는 테이블만 생성합니다.
    """
    try:
        # Always use a fresh connection
        conn = get_conn()
        cur = conn.cursor()

        # 기존 테이블 삭제 (force_recreate가 True인 경우에만)
        if force_recreate:
            st.info("기존 테이블을 삭제하고 새로 생성합니다...")
            cur.execute("""
                DROP TABLE IF EXISTS refunds CASCADE;
                DROP TABLE IF EXISTS user_items CASCADE;
                DROP TABLE IF EXISTS shop_items CASCADE;
                DROP TABLE IF EXISTS notices CASCADE;
                DROP TABLE IF EXISTS blog_posts CASCADE;
                DROP TABLE IF EXISTS blog_comments CASCADE;
                DROP TABLE IF EXISTS stock_transactions CASCADE;
                DROP TABLE IF EXISTS stock_portfolios CASCADE;
                DROP TABLE IF EXISTS stocks CASCADE;
                DROP TABLE IF EXISTS transactions CASCADE;
                DROP TABLE IF EXISTS quest_completions CASCADE;
                DROP TABLE IF EXISTS quests CASCADE;
                DROP TABLE IF EXISTS jobs CASCADE;
                DROP TABLE IF EXISTS kicked_users CASCADE;
                DROP TABLE IF EXISTS users CASCADE;
                DROP TABLE IF EXISTS suggestions CASCADE;
            """)
        else:
            st.info("누락된 테이블만 생성합니다...")

        # Users 테이블 생성 (with roles, currency, and password)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('teacher', 'student', '제작자', '일반학생')),
                currency INTEGER DEFAULT 0,
                job_id INTEGER,
                bio TEXT DEFAULT '',
                avatar_url TEXT DEFAULT '',
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)

        # Jobs 테이블 생성
        cur.execute("""
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
        cur.execute("""
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
        cur.execute("""
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
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id SERIAL PRIMARY KEY,
                from_user_id INTEGER REFERENCES users(user_id),
                to_user_id INTEGER REFERENCES users(user_id),
                amount INTEGER NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                created_by INTEGER REFERENCES users(user_id),
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)

        # Shop Items Table (for profile items)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS shop_items (
                item_id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('avatar', 'badge', 'background', 'font', 'color')),
                price INTEGER NOT NULL,
                image_url TEXT,
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)

        # User Items Table (inventory of purchased items)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_items (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(user_id),
                item_id INTEGER REFERENCES shop_items(item_id),
                is_equipped BOOLEAN DEFAULT false,
                is_active BOOLEAN DEFAULT true,
                purchased_at TIMESTAMPTZ DEFAULT now()
            );
        """)

        # Blog Posts Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS blog_posts (
                post_id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(user_id),
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                image_urls TEXT,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            );
        """)

        # Blog Comments Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS blog_comments (
                comment_id SERIAL PRIMARY KEY,
                post_id INTEGER REFERENCES blog_posts(post_id),
                user_id INTEGER REFERENCES users(user_id),
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)

        # Kicked Users Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS kicked_users (
                username TEXT PRIMARY KEY,
                reason TEXT NOT NULL,
                kicked_at TIMESTAMPTZ DEFAULT now()
            );
        """)

        # Refunds Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS refunds (
                refund_id SERIAL PRIMARY KEY,
                user_item_id INTEGER REFERENCES user_items(id),
                user_id INTEGER REFERENCES users(user_id),
                item_id INTEGER REFERENCES shop_items(item_id),
                amount INTEGER NOT NULL,
                reason TEXT,
                processed_by INTEGER REFERENCES users(user_id),
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)
        
        # Notices Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notices (
                notice_id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                heading_level INTEGER NOT NULL CHECK (heading_level BETWEEN 1 AND 6),
                is_active BOOLEAN DEFAULT true,
                created_by INTEGER REFERENCES users(user_id),
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            );
        """)
        
        # Suggestions Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS suggestions (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                username TEXT NOT NULL,
                user_id INTEGER REFERENCES users(user_id),
                timestamp TIMESTAMPTZ DEFAULT now(),
                status TEXT DEFAULT 'pending'
            );
        """)
        
        # Stocks Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                stock_id SERIAL PRIMARY KEY,
                symbol TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                current_price DECIMAL(10, 2) NOT NULL,
                last_updated TIMESTAMPTZ DEFAULT now(),
                created_by INTEGER REFERENCES users(user_id),
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)
        
        # Stock Portfolios Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stock_portfolios (
                portfolio_id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(user_id),
                stock_id INTEGER REFERENCES stocks(stock_id),
                quantity INTEGER NOT NULL,
                avg_purchase_price DECIMAL(10, 2) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now(),
                UNIQUE(user_id, stock_id)
            );
        """)
        
        # Stock Transactions Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stock_transactions (
                transaction_id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(user_id),
                stock_id INTEGER REFERENCES stocks(stock_id),
                quantity INTEGER NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('buy', 'sell')),
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)

        conn.commit()
        st.success("데이터베이스 테이블이 성공적으로 생성되었습니다!")
    except Exception as e:
        st.error(f"데이터베이스 초기화 오류: {str(e)}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
        raise e
    finally:
        # Always close the connection
        if 'cur' in locals() and cur:
            try:
                cur.close()
            except:
                pass
        if 'conn' in locals() and conn:
            try:
                conn.close()
            except:
                pass
