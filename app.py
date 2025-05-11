# Initialize session state variables before any Streamlit commands
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from libs.db import get_conn
from libs.auth import render_login_sidebar
from libs.ui_helpers import header
from pages.notices import render_notices
import time
import psycopg2
import traceback

# Initialize session state variables
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'role' not in st.session_state:
    st.session_state.role = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'db_initialized' not in st.session_state:
    st.session_state.db_initialized = False
if 'last_db_check' not in st.session_state:
    st.session_state.last_db_check = 0

# Function to get a fresh connection for each operation
def get_fresh_connection():
    """Get a completely fresh database connection for this operation"""
    try:
        # Create a brand new connection using secrets
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
        return conn, None
    except Exception as e:
        return None, str(e)

# Global auto-refresh (30 seconds)
st_autorefresh(interval=30000, key="global_autorefresh")

# Only check database connection once every 5 minutes to reduce overhead
current_time = time.time()
if current_time - st.session_state.last_db_check > 300:  # 5 minutes in seconds
    # Check if database is properly connected (without using cached connections)
    conn, error = get_fresh_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
            conn.close()
            db_connected = True
            # Update last check time
            st.session_state.last_db_check = current_time
        except Exception as e:
            db_connected = False
            st.error(f"Database connection error: {str(e)}")
    else:
        db_connected = False
        st.error(f"Database connection error: {error}")
else:
    # Use the last known database connection status
    db_connected = True

# Render login sidebar only if database is connected
if db_connected:
    render_login_sidebar()

# Render header
header()

# Only continue if database is connected
if db_connected:
    # Display notices if user is logged in
    if st.session_state.logged_in:
        try:
            render_notices()
        except Exception as e:
            st.warning(f"공지사항을 불러오는 중 오류가 발생했습니다: {str(e)}")
            st.info("관리자 페이지에서 공지사항 테이블을 초기화해주세요.")

    # Main content area
    if not st.session_state.logged_in:
        st.header("🏠 홈")
        st.write("로그인이 필요합니다. 사이드바에서 로그인 또는 회원가입을 진행해주세요.")
    else:
        # Sidebar for page selection
        st.sidebar.markdown("---")
        
        # Let Streamlit handle page navigation automatically
        # We won't try to import or route to pages manually
        st.header("🏠 홈")
        st.write(f"환영합니다, {st.session_state.username}님! 사이드바에서 메뉴를 선택해주세요.")
        
        # Show database initialization button for admins
        if st.session_state.role in ['teacher', '제작자']:
            st.markdown("---")
            st.subheader("🛠️ 관리자 도구")
            
            if st.button("데이터베이스 테이블 초기화", key="init_db_button"):
                try:
                    conn, error = get_fresh_connection()
                    if conn:
                        from libs.db import init_tables
                        init_tables()
                        st.session_state.db_initialized = True
                        st.success("데이터베이스 테이블이 성공적으로 초기화되었습니다!")
                        st.info("페이지를 새로고침하면 모든 기능이 활성화됩니다.")
                        conn.close()
                    else:
                        st.error(f"데이터베이스 연결 실패: {error}")
                except Exception as e:
                    st.error(f"데이터베이스 초기화 오류: {str(e)}")
                    st.code(traceback.format_exc())
            
            if st.session_state.db_initialized:
                st.success("데이터베이스가 초기화되었습니다!")
            
else:
    st.header("⚠️ 데이터베이스 연결 오류")
    st.write("데이터베이스에 연결할 수 없습니다. 관리자에게 문의하거나 데이터베이스 진단 페이지에서 연결을 확인해보세요.")
    
    if st.button("데이터베이스 진단 페이지로 이동"):
        st.switch_page("pages/데이터베이스_진단.py")
