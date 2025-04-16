import os, uuid, streamlit as st
from datetime import datetime
from libs.db import get_conn
from libs.ui_helpers import header

conn = get_conn()
header()
st.header("📘 미니 블로그 / 자랑하기")

with st.form("post_form", clear_on_submit=True):
    title    = st.text_input("제목")
    content  = st.text_area("내용")
    category = st.selectbox("카테고리", ["블로그","자랑하기"])
    file     = st.file_uploader("이미지 업로드", type=["png","jpg","jpeg","gif"])
    if st.form_submit_button("게시하기") and title and content:
        img_path = ""
        if file:
            os.makedirs("uploads", exist_ok=True)
            fn = f"uploads/{uuid.uuid4().hex}.{file.name.split('.')[-1]}"
            with open(fn,"wb") as f:
                f.write(file.getbuffer())
            img_path = fn
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO blog_posts(title,content,timestamp,username,category,image_url) VALUES(%s,%s,%s,%s,%s,%s)",
            (title, content, ts, st.session_state.username, category, img_path)
        )
        conn.commit()
        st.success("게시글 등록 완료")
        st.rerun()

st.markdown("### 최신 게시글")
cur = conn.cursor()
cur.execute(
    "SELECT id,title,content,timestamp,username,category,image_url "
    "FROM blog_posts ORDER BY id DESC"
)
for pid, t, ctn, ts, user, cat, img in cur.fetchall():
    st.markdown(f"**[{pid}] {t}** _(카테고리: {cat}, {ts}, by {user})_")
    st.write(ctn)
    if cat=="자랑하기" and img:
        st.image(img)
    with st.expander("댓글 보기 / 등록"):
        cur2 = conn.cursor()
        cur2.execute(
            "SELECT username,comment,timestamp FROM blog_comments "
            "WHERE post_id=%s ORDER BY id DESC", (pid,)
        )
        for u, cm, tm in cur2.fetchall():
            st.markdown(f"- **[{tm}] {u}**: {cm}")
        with st.form(f"cmt_{pid}", clear_on_submit=True):
            txt = st.text_area("댓글 입력")
            if st.form_submit_button("등록") and txt:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cur2.execute(
                    "INSERT INTO blog_comments(post_id,username,comment,timestamp) "
                    "VALUES(%s,%s,%s,%s)",
                    (pid, st.session_state.username, txt, now)
                )
                conn.commit()
                st.success("댓글 등록 완료")
                st.rerun()
    st.markdown("---")
