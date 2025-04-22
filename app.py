import streamlit as st
from libs.db import init_tables
from libs.auth import render_login_sidebar
from libs.ui_helpers import header

# ── 최초 1회만 실행하고 주석 처리하세요 ───────────────────
# init_tables()

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
