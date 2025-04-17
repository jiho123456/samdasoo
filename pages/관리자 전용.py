import streamlit as st
from libs.db import get_conn
from libs.ui_helpers import header

conn = get_conn()
header()
st.header("🔧 운영진 페이지")

if st.session_state.role not in ["제작자","반장","부반장"]:
    st.error("권한이 없습니다."); st.stop()

cur = conn.cursor()

# 1) 유저 관리: 역할 변경 + 강제 탈퇴
st.subheader("👤 유저 관리")
cur.execute("SELECT id, username, role FROM users ORDER BY id")
for uid, un, ur in cur.fetchall():
    col1, col2, col3 = st.columns([0.6,0.2,0.2])
    col1.write(f"**{un}** (역할: {ur})")

    # 역할 변경 (제작자만)
    if st.session_state.role == "제작자":
        roles = ["제작자","관리자","반장","부반장","일반학생"]
        idx = roles.index(ur) if ur in roles else 4
        new_role = col2.selectbox("", roles, index=idx, key=f"role_{uid}")
        if col2.button("변경", key=f"chg_{uid}"):
            cur.execute("UPDATE users SET role=%s WHERE id=%s", (new_role, uid))
            conn.commit()
            st.success(f"{un}님의 역할을 {new_role}(으)로 변경했습니다.")
            st.rerun()
    else:
        col2.write("변경 불가")

    # 강제 탈퇴 (킥)
    if st.session_state.role == "제작자":
        with col3.expander("킥하기"):
            reason = st.text_input("사유 입력", key=f"kick_reason_{uid}")
            if st.button("강제 탈퇴", key=f"kick_{uid}"):
                # kicked_users에 기록
                cur.execute("""
                    INSERT INTO kicked_users(username, reason)
                    VALUES(%s, %s)
                    ON CONFLICT(username) DO UPDATE
                      SET reason = EXCLUDED.reason,
                          kicked_at = now();
                """, (un, reason))
                # users에서 삭제
                cur.execute("DELETE FROM users WHERE username=%s", (un,))
                conn.commit()
                st.success(f"{un}님을 강제 탈퇴했습니다:\n{reason}")
                st.rerun()
    else:
        col3.write("권한 없음")

    st.markdown("---")

# 2) 게시글 모더레이션
st.subheader("📝 게시글 모더레이션")
cur.execute("SELECT id,title,username,timestamp FROM blog_posts ORDER BY id DESC")
for pid, pt, pu, tm in cur.fetchall():
    st.write(f"- [ID {pid}] **{pt}** by {pu} ({tm})")
    c1,c2 = st.columns([0.7,0.3])
    if c2.button("삭제", key=f"delp_{pid}"):
        cur.execute("DELETE FROM blog_posts WHERE id=%s",(pid,)); conn.commit()
        st.success("삭제 완료"); st.rerun()
    if c2.button("수정", key=f"editp_{pid}"):
        post_cur = conn.cursor()
        post_cur.execute("SELECT title,content,category FROM blog_posts WHERE id=%s",(pid,))
        old_t, old_c, old_cat = post_cur.fetchone()
        with st.form(f"edit_form_{pid}", clear_on_submit=True):
            nt   = st.text_input("제목", value=old_t, key=f"nt_{pid}")
            nc   = st.text_area("내용", value=old_c, key=f"nc_{pid}")
            ncat = st.selectbox("카테고리",["블로그","자랑하기"],
                                index=0 if old_cat=="블로그" else 1,
                                key=f"ncat_{pid}")
            if st.form_submit_button("저장"):
                cur.execute(
                  "UPDATE blog_posts SET title=%s,content=%s,category=%s WHERE id=%s",
                  (nt,nc,ncat,pid)
                )
                conn.commit(); st.success("수정 완료"); st.rerun()
    st.markdown("---")

# 3) 동아리 관리
st.subheader("🏢 동아리 관리")
cur.execute("SELECT id,club_name,description FROM clubs ORDER BY id")
for cid, cn, cd in cur.fetchall():
    st.write(f"• [ID {cid}] **{cn}**")
    c1,c2 = st.columns([0.7,0.3])
    if c2.button("삭제", key=f"delc_{cid}"):
        cur.execute("DELETE FROM clubs WHERE id=%s",(cid,)); conn.commit()
        st.success("삭제 완료"); st.rerun()
    if c2.button("수정", key=f"editc_{cid}"):
        with st.form(f"club_form_{cid}", clear_on_submit=True):
            new_name = st.text_input("동아리명", value=cn, key=f"cn_{cid}")
            new_desc = st.text_area("설명", value=cd, key=f"cd_{cid}")
            if st.form_submit_button("저장"):
                cur.execute(
                  "UPDATE clubs SET club_name=%s,description=%s WHERE id=%s",
                  (new_name,new_desc,cid)
                )
                conn.commit(); st.success("수정 완료"); st.rerun()
    st.markdown("---")
