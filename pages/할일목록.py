import streamlit as st
from datetime import datetime
from libs.db import get_conn
from libs.ui_helpers import header

conn = get_conn()
header()
st.header("📝 해야할일")
cur = conn.cursor()

with st.form("td_form", clear_on_submit=True):
    td = st.text_input("할 일")
    if st.form_submit_button("추가") and td:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "INSERT INTO todos(content,is_done,timestamp) VALUES(%s,0,%s)",
            (td, now)
        )
        conn.commit(); st.success("추가 완료"); st.rerun()

cur.execute("SELECT id,content,is_done,timestamp FROM todos ORDER BY id DESC")
for tid, co, done, tm in cur.fetchall():
    c1, c2, c3 = st.columns([0.05,0.8,0.15])
    with c1:
        chk = st.checkbox("", value=bool(done), key=f"td_{tid}")
        if chk != bool(done):
            cur.execute(
                "UPDATE todos SET is_done=%s WHERE id=%s",
                (1 if chk else 0, tid)
            )
            conn.commit(); st.rerun()
    with c2:
        st.markdown(f"{'~~'+co+'~~' if done else co}  \n*({tm})*")
    with c3:
        if st.button("삭제", key=f"tdel_{tid}"):
            cur.execute("DELETE FROM todos WHERE id=%s",(tid,))
            conn.commit(); st.success("삭제 완료"); st.rerun()
    st.markdown("---")
