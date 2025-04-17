# pages/08_moderator.py
import streamlit as st
from libs.db import get_conn
from libs.ui_helpers import header

conn = get_conn()
cur = conn.cursor()

header()
st.header("🔧 운영진 페이지")

# 접근 권한 체크
if st.session_state.role not in ["제작자", "반장", "부반장"]:
    st.error("🔒 접근 권한이 없습니다.")
    st.stop()

# 1) 유저 관리: 역할 변경 + 강제 탈퇴
st.subheader("👤 사용자 관리")
cur.execute("SELECT id, username, role FROM users ORDER BY id")
for uid, un, ur in cur.fetchall():
    col1, col2, col3 = st.columns([0.6, 0.2, 0.2])
    col1.write(f"**{un}**  (역할: {ur})")

    # 역할 변경 (제작자만)
    if st.session_state.role == "제작자":
        roles = ["제작자", "관리자", "반장", "부반장", "일반학생"]
        idx = roles.index(ur) if ur in roles else len(roles)-1
        new_role = col2.selectbox(
            "", roles, index=idx, key=f"role_{uid}"
        )
        if col2.button("변경", key=f"chg_{uid}"):
            cur.execute(
                "UPDATE users SET role=%s WHERE id=%s",
                (new_role, uid)
            )
            conn.commit()
            st.success(f"{un}님의 역할을 **{new_role}**(으)로 변경했습니다.")
            st.rerun()
    else:
        col2.write("변경 불가")

    # 강제 탈퇴 (킥)
    if st.session_state.role == "제작자":
        with col3.expander("킥하기"):
            reason = st.text_input(
                "사유 입력", key=f"kick_reason_{uid}"
            )
            if st.button("강제 탈퇴", key=f"kick_{uid}"):
                # kicked_users에 기록
                cur.execute(
                    """
                    INSERT INTO kicked_users(username, reason)
                    VALUES(%s, %s)
                    ON CONFLICT(username) DO UPDATE
                      SET reason=EXCLUDED.reason,
                          kicked_at=NOW()
                    """,
                    (un, reason)
                )
                # users에서 삭제
                cur.execute(
                    "DELETE FROM users WHERE username=%s",
                    (un,)
                )
                conn.commit()
                st.success(f"{un}님을 강제 탈퇴했습니다.\n사유: {reason}")
                st.rerun()
    else:
        col3.write("권한 없음")

    st.markdown("---")


# 2) 블로그 게시글 모더레이션
st.subheader("📝 블로그 게시글 모더레이션")
cur.execute("""
    SELECT id, title, username, timestamp 
    FROM blog_posts 
    ORDER BY id DESC
""")
for pid, pt, pu, tm in cur.fetchall():
    col1, col2 = st.columns([0.8, 0.2])
    col1.write(f"[{pid}] **{pt}** by {pu} ({tm})")
    if col2.button("삭제", key=f"delp_{pid}"):
        # 게시글 + 댓글 삭제
        cur.execute("DELETE FROM blog_comments WHERE post_id=%s", (pid,))
        cur.execute("DELETE FROM blog_posts WHERE id=%s", (pid,))
        conn.commit()
        st.success("게시글 및 댓글을 삭제했습니다.")
        st.rerun()
st.markdown("---")


# 3) 블로그 댓글 모더레이션
st.subheader("💬 블로그 댓글 모더레이션")
cur.execute("""
    SELECT id, post_id, username, comment, timestamp 
    FROM blog_comments 
    ORDER BY id DESC
""")
for cid, post_id, cu, cm, ctm in cur.fetchall():
    col1, col2 = st.columns([0.8, 0.2])
    col1.write(f"[{cid}] ({post_id}) {cu}: {cm} ({ctm})")
    if col2.button("삭제", key=f"delcmt_{cid}"):
        cur.execute("DELETE FROM blog_comments WHERE id=%s", (cid,))
        conn.commit()
        st.success("댓글을 삭제했습니다.")
        st.rerun()
st.markdown("---")


# 4) 퀴즈 모더레이션
st.subheader("❓ 퀴즈 모더레이션")
cur.execute("""
    SELECT id, title, created_by, timestamp 
    FROM quizzes 
    ORDER BY id DESC
""")
for qid, qt, qb, qtm in cur.fetchall():
    col1, col2 = st.columns([0.8, 0.2])
    col1.write(f"[{qid}] **{qt}** by {qb} ({qtm})")
    if col2.button("삭제", key=f"delquiz_{qid}"):
        # 퀴즈 + 응시기록 삭제
        cur.execute("DELETE FROM quiz_attempts WHERE quiz_id=%s", (qid,))
        cur.execute("DELETE FROM quizzes WHERE id=%s", (qid,))
        conn.commit()
        st.success("퀴즈 및 응시 기록을 삭제했습니다.")
        st.rerun()
st.markdown("---")


# 5) 건의 모더레이션
st.subheader("📢 건의 모더레이션")
cur.execute("""
    SELECT id, content, username, timestamp 
    FROM suggestions 
    ORDER BY id DESC
""")
for sid, sc, su, stm in cur.fetchall():
    col1, col2 = st.columns([0.8, 0.2])
    col1.write(f"[{sid}] {sc} by {su} ({stm})")
    if col2.button("삭제", key=f"delsugg_{sid}"):
        cur.execute("DELETE FROM suggestions WHERE id=%s", (sid,))
        conn.commit()
        st.success("건의를 삭제했습니다.")
        st.rerun()
st.markdown("---")


# 6) 할 일 모더레이션
st.subheader("📝 해야할일 모더레이션")
cur.execute("""
    SELECT id, content, is_done, timestamp 
    FROM todos 
    ORDER BY id DESC
""")
for tid, tco, tdone, ttm in cur.fetchall():
    status = "✅" if tdone else "❌"
    col1, col2 = st.columns([0.8, 0.2])
    col1.write(f"[{tid}] {tco} ({ttm}) 상태: {status}")
    if col2.button("삭제", key=f"deltodo_{tid}"):
        cur.execute("DELETE FROM todos WHERE id=%s", (tid,))
        conn.commit()
        st.success("할 일을 삭제했습니다.")
        st.rerun()
st.markdown("---")


# 7) 동아리 관리
st.subheader("🎨 동아리 관리")
cur.execute("""
    SELECT id, club_name, description 
    FROM clubs 
    ORDER BY id
""")
for cid, cn, cd in cur.fetchall():
    col1, col2 = st.columns([0.7, 0.3])
    col1.write(f"[{cid}] **{cn}** — {cd}")
    if st.session_state.role in ["제작자", "관리자"] and col2.button("삭제", key=f"delclub_{cid}"):
        # 동아리 + 관련 데이터 삭제
        cur.execute("DELETE FROM club_media WHERE club_id=%s", (cid,))
        cur.execute("DELETE FROM club_chats WHERE club_id=%s", (cid,))
        cur.execute("DELETE FROM club_members WHERE club_id=%s", (cid,))
        cur.execute("DELETE FROM clubs WHERE id=%s", (cid,))
        conn.commit()
        st.success("동아리 및 관련 데이터를 삭제했습니다.")
        st.rerun()
st.markdown("---")


# 8) 동아리 채팅 모더레이션
st.subheader("💬 동아리 채팅 모더레이션")
cur.execute("""
    SELECT id, club_id, username, message, timestamp 
    FROM club_chats 
    ORDER BY id DESC
""")
for mid, mclub, mu, mm, mt in cur.fetchall():
    col1, col2 = st.columns([0.8, 0.2])
    col1.write(f"[{mid}] (동아리 {mclub}) {mu}: {mm} ({mt})")
    if col2.button("삭제", key=f"delchat_{mid}"):
        cur.execute("DELETE FROM club_chats WHERE id=%s", (mid,))
        conn.commit()
        st.success("채팅 메시지를 삭제했습니다.")
        st.rerun()
st.markdown("---")


# 9) 동아리 미디어 모더레이션
st.subheader("🖼️ 동아리 미디어 모더레이션")
cur.execute("""
    SELECT id, club_id, username, file_path, upload_time 
    FROM club_media 
    ORDER BY id DESC
""")
for mid, mclub, mu, mp, mup in cur.fetchall():
    col1, col2 = st.columns([0.8, 0.2])
    col1.write(f"[{mid}] (동아리 {mclub}) by {mu} at {mup} — {mp}")
    if col2.button("삭제", key=f"delmedia_{mid}"):
        cur.execute("DELETE FROM club_media WHERE id=%s", (mid,))
        conn.commit()
        st.success("미디어 파일 레코드를 삭제했습니다.")
        st.rerun()
st.markdown("---")
