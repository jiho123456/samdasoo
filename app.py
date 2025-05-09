# Initialize session state variables before any Streamlit commands
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from libs.db import get_conn
from libs.auth import render_login_sidebar
from libs.ui_helpers import header
from pages.notices import render_notices

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

# Global auto-refresh (30 seconds)
st_autorefresh(interval=30000, key="global_autorefresh")

# Check if database is properly connected
db_connected = False
try:
    # Get a new connection for this check, don't rely on cached connections
    get_conn()
    db_connected = True
except Exception as e:
    st.error(f"Database connection error: {str(e)}")
    st.warning("Please check your database configuration in .streamlit/secrets.toml")

# Render login sidebar only if database is connected
if db_connected:
    try:
        render_login_sidebar()
    except Exception as e:
        st.error(f"Login sidebar error: {str(e)}")

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
                    from libs.db import init_tables
                    init_tables()
                    st.session_state.db_initialized = True
                    st.success("데이터베이스 테이블이 성공적으로 초기화되었습니다!")
                    st.info("페이지를 새로고침하면 모든 기능이 활성화됩니다.")
                except Exception as e:
                    st.error(f"데이터베이스 초기화 오류: {str(e)}")
            
            if st.session_state.db_initialized:
                st.success("데이터베이스가 초기화되었습니다!")
            
else:
    st.header("⚠️ 데이터베이스 연결 오류")
    st.write("데이터베이스에 연결할 수 없습니다. 관리자에게 문의해주세요.")
    
    # Show troubleshooting information for admins
    with st.expander("문제 해결 정보"):
        st.write("""
        1. `.streamlit/secrets.toml` 파일이 올바르게 설정되어 있는지 확인하세요.
        2. 데이터베이스 서버가 실행 중인지 확인하세요.
        3. 데이터베이스 사용자 이름, 비밀번호, 호스트 등이 올바른지 확인하세요.
        4. 방화벽 설정을 확인하세요.
        """)
        
        # Database connection test form
        st.subheader("데이터베이스 연결 테스트")
        
        with st.form("db_test_form"):
            db_user = st.text_input("사용자 이름", value=st.secrets["user"])
            db_password = st.text_input("비밀번호", type="password", value=st.secrets["password"])
            db_host = st.text_input("호스트", value=st.secrets["host"])
            db_port = st.text_input("포트", value=st.secrets["port"])
            db_name = st.text_input("데이터베이스 이름", value=st.secrets["dbname"])
            
            submit = st.form_submit_button("연결 테스트")
            
            if submit:
                try:
                    import psycopg2
                    test_conn = psycopg2.connect(
                        user=db_user,
                        password=db_password,
                        host=db_host,
                        port=db_port,
                        dbname=db_name
                    )
                    test_cur = test_conn.cursor()
                    test_cur.execute("SELECT 1")
                    test_cur.fetchone()
                    test_cur.close()
                    test_conn.close()
                    
                    st.success("데이터베이스 연결 성공!")
                    st.info("앱을 새로고침하면 정상적으로 작동할 것입니다.")
                except Exception as e:
                    st.error(f"연결 테스트 실패: {str(e)}")
                    st.info("위 오류 메시지를 확인하고 연결 정보를 수정하세요.")
        
        st.markdown("---")
        st.info("설정을 변경한 후 앱을 다시 시작하세요.")
        if st.button("앱 새로고침"):
            st.rerun()
