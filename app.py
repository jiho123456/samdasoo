# Initialize session state variables before any Streamlit commands
import streamlit as st

# Initialize all session state variables at the very beginning
for key in ['role', 'user_id', 'is_logged_in']:
    if key not in st.session_state:
        st.session_state[key] = None

# Now import other modules
from streamlit_autorefresh import st_autorefresh
from libs.db import init_tables
from libs.auth import render_login_sidebar
from libs.ui_helpers import header
from pages.currency import render_currency_page
from pages.stocks import render_stocks_page

# ── 최초 1회만 실행하고 주석 처리하세요 ───────────────────
# init_tables()

# ── 글로벌 자동 새로고침 (5초) ──────────────────────────
_ = st_autorefresh(interval=5_000, key="global_autorefresh")

# ── 사이드바 로그인/회원가입 렌더링 ──────────────────────
render_login_sidebar()

# ── 상단 헤더 ────────────────────────────────────────────
header()

# ── 페이지 라우팅 ──────────────────────────────────────
page = st.sidebar.selectbox("페이지 선택", ["홈", "학급 화폐", "모의 주식"])

if page == "홈":
    st.header("🏠 홈")
    mood = st.selectbox("오늘의 기분은?", ["😄 굿굿!", "😎 멋져!", "😴 졸려요...", "🥳 신나요!"])
    st.write(f"오늘의 기분: {mood}")
    if st.button("새로고침"):
        st.rerun()
elif page == "학급 화폐":
    render_currency_page()
elif page == "모의 주식":
    render_stocks_page()
