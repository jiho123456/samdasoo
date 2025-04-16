import streamlit as st
from streamlit_autorefresh import st_autorefresh
from libs.db import get_conn
from libs.auth import render_login_sidebar
from libs.ui_helpers import header

# 1) global auto‑refresh every 5 s
_ = st_autorefresh(interval=5_000, key="global_autorefresh")

# 2) sidebar login/signup
render_login_sidebar()

# 3) page header
header()

# 4) 홈 페이지 content
st.header("🏠 홈")
mood = st.selectbox("오늘의 기분은?", ["😄 굿굿!", "😎 OK", "😴 졸림", "🥳 신남"])
st.write(f"오늘의 기분: {mood}")
if st.button("새로고침"):
    st.rerun()
