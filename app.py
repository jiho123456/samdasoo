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

# ── 페이지 라우팅 ──────────────────────────────────────
if st.session_state.get('is_logged_in'):
    with st.sidebar:
        st.subheader("📱 메뉴")
        page = st.radio(
            "페이지 선택",
            ["홈", "학급 화폐", "모의 주식"],
            label_visibility="collapsed"
        )
else:
    page = "홈"

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
