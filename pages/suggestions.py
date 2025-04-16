import streamlit as st
from datetime import datetime
from libs.db import get_conn
from libs.ui_helpers import header

conn = get_conn()
header()
st.header("📢 건의함")

with st.form("s_form", clear_on_submit=True):
    sc = st.text_area("건의 내용")
    if st.form_submit_button("제출") and sc:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO suggestions(content,username,timestamp) "
            "VALUES(%s,%s,%s)",
            (sc, st.session_state.username, now)
        )
        conn.commit()
        st.success("제출 완료")
        st.rerun()

st.markdown("### 최신 건의")
cur = conn.cursor()
cur.execute(
    "SELECT id,content,username,timestamp FROM suggestions ORDER BY id DESC"
)
for sid, co, u, tm in cur.fetchall():
    st.markdown(f"**[{sid}]** {co} _(by {u}, {tm})_")
    st.markdown("---")
