import streamlit as st
from datetime import datetime
from libs.db import get_conn
from libs.ui_helpers import header

conn = get_conn()
header()
st.header("❓ 퀴즈")

if not st.session_state.logged_in or st.session_state.username=="게스트":
    st.error("로그인 후 이용 가능합니다.")
else:
    with st.form("q_form", clear_on_submit=True):
        qt = st.text_input("퀴즈 제목")
        qd = st.text_area("퀴즈 설명")
        if st.form_submit_button("등록") and qt and qd:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO quizzes(title,description,created_by,timestamp) "
                "VALUES(%s,%s,%s,%s)",
                (qt, qd, st.session_state.username, now)
            )
            conn.commit()
            st.success("퀴즈 등록 완료")
            st.rerun()

    st.markdown("### 등록된 퀴즈")
    cur = conn.cursor()
    cur.execute(
        "SELECT id,title,description,created_by,timestamp "
        "FROM quizzes ORDER BY id DESC"
    )
    for qid, ti, de, cb, tm in cur.fetchall():
        st.markdown(f"**[{qid}] {ti}** _(by {cb}, {tm})_")
        st.write(de)
        if st.button(f"풀기 (ID {qid})", key=f"solve_{qid}"):
            st.info("준비 중입니다.")
        st.markdown("---")
