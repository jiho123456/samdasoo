# libs/db.py
import streamlit as st
import psycopg2
import psycopg2.errors

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
        tmp_conn.autocommit = True
        tmp_cur = tmp_conn.cursor()

        # 기존 테이블 삭제 (외래 키 제약조건을 고려한 순서로 삭제)
        tmp_cur.execute("""
            DROP TABLE IF EXISTS user_items CASCADE;
            DROP TABLE IF EXISTS shop_items CASCADE;
            DROP TABLE IF EXISTS blog_posts CASCADE;
            DROP TABLE IF EXISTS blog_comments CASCADE;
            DROP TABLE IF EXISTS transactions CASCADE;
            DROP TABLE IF EXISTS quest_completions CASCADE;
            DROP TABLE IF EXISTS quests CASCADE;
            DROP TABLE IF EXISTS jobs CASCADE;
            DROP TABLE IF EXISTS kicked_users CASCADE;
            DROP TABLE IF EXISTS users CASCADE;
        """)

        # Users 테이블 생성 (with roles, currency, and password)
        tmp_cur.execute("""
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

        # Shop Items Table (for profile items)
        tmp_cur.execute("""
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
        tmp_cur.execute("""
            CREATE TABLE IF NOT EXISTS user_items (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(user_id),
                item_id INTEGER REFERENCES shop_items(item_id),
                is_equipped BOOLEAN DEFAULT false,
                purchased_at TIMESTAMPTZ DEFAULT now()
            );
        """)

        # Blog Posts Table
        tmp_cur.execute("""
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
        tmp_cur.execute("""
            CREATE TABLE IF NOT EXISTS blog_comments (
                comment_id SERIAL PRIMARY KEY,
                post_id INTEGER REFERENCES blog_posts(post_id),
                user_id INTEGER REFERENCES users(user_id),
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)

        # kicked_users 테이블 생성 (마지막에 생성)
        tmp_cur.execute("""
            CREATE TABLE IF NOT EXISTS kicked_users (
                username TEXT PRIMARY KEY,
                reason   TEXT NOT NULL,
                kicked_at TIMESTAMPTZ DEFAULT now()
            );
        """)

        # Create refunds table
        tmp_cur.execute("""
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

        tmp_conn.commit()
        st.success("데이터베이스 테이블이 성공적으로 생성되었습니다!")
    except Exception as e:
        st.error(f"데이터베이스 초기화 오류: {str(e)}")
        raise e
    finally:
        tmp_conn.close()  # 여기만 닫고, 캐시된 커넥션은 손대지 않습니다.
