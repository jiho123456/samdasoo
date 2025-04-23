import streamlit as st
from streamlit_autorefresh import st_autorefresh
from libs.db import init_tables
from libs.auth import render_login_sidebar
from libs.ui_helpers import header

# Initialize session state variables
if 'role' not in st.session_state:
    st.session_state.role = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'is_logged_in' not in st.session_state:
    st.session_state.is_logged_in = False

# ── 최초 1회만 실행하고 주석 처리하세요 ───────────────────
# init_tables()

# ── 글로벌 자동 새로고침 (5초) ──────────────────────────
_ = st_autorefresh(interval=5_000, key="global_autorefresh")

# ── 사이드바 로그인/회원가입 렌더링 ──────────────────────
render_login_sidebar()

# ── 상단 헤더 ────────────────────────────────────────────
header()

# ── 홈 페이지 내용 ──────────────────────────────────────
st.header("🏠 홈")
mood = st.selectbox("오늘의 기분은?", ["😄 굿굿!", "😎 멋져!", "😴 졸려요...", "🥳 신나요!"])
st.write(f"오늘의 기분: {mood}")
if st.button("새로고침"):
    st.rerun()
