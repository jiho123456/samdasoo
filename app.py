# Initialize session state variables before any Streamlit commands
import streamlit as st

# Initialize all session state variables at the very beginning
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'role' not in st.session_state:
    st.session_state.role = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None

# Now import other modules
from streamlit_autorefresh import st_autorefresh
from libs.db import init_tables
from libs.auth import render_login_sidebar
from libs.ui_helpers import header
# We will let Streamlit handle page imports from the 'pages' directory

# # 데이터베이스 초기화 (첫 사용 시 필요, 1회 사용 후 주석 처리하세요)
# try:
#     init_tables()
#     st.success("데이터베이스가 성공적으로 초기화되었습니다!")
# except Exception as e:
#     st.error(f"데이터베이스 초기화 중 오류가 발생했습니다: {str(e)}")

# ── 글로벌 자동 새로고침 (5초) ──────────────────────────
_ = st_autorefresh(interval=5_000, key="global_autorefresh")

# ── 사이드바 로그인/회원가입 렌더링 ──────────────────────
render_login_sidebar()

# ── 상단 헤더 ────────────────────────────────────────────
header()

# ── 기본 홈 페이지 내용 ───────────────────────────────────
# This content will be shown if no page from the 'pages' directory is selected,
# or if the user is not logged in and no specific public page is designated.

if not st.session_state.get('logged_in'):
    st.header("🏠 홈")
    st.write("로그인이 필요합니다. 사이드바에서 로그인 또는 회원가입을 진행해주세요.")
else:
    # If logged in, Streamlit will automatically show the selected page from the 'pages/' directory.
    # If no page is explicitly selected (e.g., on first load after login),
    # Streamlit usually shows the first page in alphabetical order from the 'pages/' directory.
    # You can add a default message here if needed, but it's often better to have a default page in 'pages/'.
    st.header("🏠 홈")
    st.write(f"환영합니다, {st.session_state.get('username', '사용자')}님! 사이드바에서 메뉴를 선택해주세요.")

# Streamlit will automatically create navigation for files in the 'pages/' directory.
# Example: if you have 'pages/currency.py', it will create a 'Currency' page.

# Initialize database tables
try:
    init_tables()
except Exception as e:
    st.error(f"Database initialization error: {str(e)}")

# Global auto-refresh
st_autorefresh(interval=30000, key="data_refresh")

# Render login sidebar
render_login_sidebar()

# Render header
header()

# Display notices if user is logged in
if st.session_state.get('logged_in'):
    render_notices()

# Sidebar for page selection
if st.session_state.get('logged_in'):
    st.sidebar.markdown("---")
    page = st.sidebar.radio(
        "페이지 선택",
        ["Home", "Classroom Currency", "Mock Stocks"],
        label_visibility="collapsed"
    )
    
    # Page routing
    if page == "Home":
        st.title("Welcome to the Classroom Currency System!")
        st.write("Please select a page from the sidebar to get started.")
    elif page == "Classroom Currency":
        render_currency_page()
    elif page == "Mock Stocks":
        render_stocks_page()
