import os, uuid, streamlit as st
from datetime import datetime
from libs.db import get_conn
from libs.ui_helpers import header

# Initialize all session state variables at the very beginning
if 'role' not in st.session_state:
    st.session_state.role = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'is_logged_in' not in st.session_state:
    st.session_state.is_logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = "게스트"
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

conn = get_conn()
header()
st.header("🎨 자율동아리")
cur = conn.cursor()

# add club (제작자/관리자)
if st.session_state.role in ["제작자","관리자"]:
    with st.form("cl_form", clear_on_submit=True):
        cn = st.text_input("동아리명")
        cd = st.text_area("설명")
        if st.form_submit_button("추가") and cn and cd:
            cur.execute(
                "INSERT INTO clubs(club_name,description) VALUES(%s,%s)",
                (cn, cd)
            )
            conn.commit()
            st.success("추가 완료")
            st.rerun()

# list clubs
cur.execute("SELECT id,club_name,description FROM clubs ORDER BY id")
for cid, nm, ds in cur.fetchall():
    st.markdown(f"### {nm}\n{ds}")

    # join/leave
    cur.execute(
        "SELECT 1 FROM club_members WHERE club_id=%s AND username=%s",
        (cid, st.session_state.username)
    )
    joined = cur.fetchone()
    if st.session_state.logged_in and st.session_state.username!="게스트":
        if not joined and st.button(f"가입({nm})", key=f"j_{cid}"):
            cur.execute(
                "INSERT INTO club_members(club_id,username) VALUES(%s,%s)",
                (cid, st.session_state.username)
            )
            conn.commit(); st.success("가입 완료"); st.rerun()
        elif joined and st.button(f"탈퇴({nm})", key=f"l_{cid}"):
            cur.execute(
                "DELETE FROM club_members WHERE club_id=%s AND username=%s",
                (cid, st.session_state.username)
            )
            conn.commit(); st.success("탈퇴 완료"); st.rerun()
    cur.execute("SELECT username FROM club_members WHERE club_id=%s",(cid,))
    members = [r[0] for r in cur.fetchall()]
    st.write("멤버:", ", ".join(members) if members else "없음")

    # chat
    with st.expander("채팅방"):
        cur.execute(
            "SELECT username,message,timestamp FROM club_chats "
            "WHERE club_id=%s ORDER BY id", (cid,)
        )
        for u, m, tm in cur.fetchall():
            st.markdown(f"**[{tm}] {u}**: {m}")
        with st.form(f"chat_{cid}", clear_on_submit=True):
            msg = st.text_input("메시지")
            if st.form_submit_button("전송") and msg:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cur.execute(
                    "INSERT INTO club_chats(club_id,username,message,timestamp) "
                    "VALUES(%s,%s,%s,%s)",
                    (cid, st.session_state.username, msg, now)
                )
                conn.commit(); st.success("전송 완료"); st.rerun()

    # media upload/view
    with st.expander("미디어 업로드/보기"):
        up = st.file_uploader("파일", key=f"up_{cid}")
        if st.button("업로드", key=f"btn_{cid}") and up:
            os.makedirs("uploads_club", exist_ok=True)
            fn = f"uploads_club/{uuid.uuid4().hex}.{up.name.split('.')[-1]}"
            with open(fn,"wb") as f: f.write(up.getbuffer())
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "INSERT INTO club_media(club_id,username,file_path,upload_time) "
                "VALUES(%s,%s,%s,%s)",
                (cid, st.session_state.username, fn, now)
            )
            conn.commit(); st.success("업로드 완료"); st.rerun()

        cur.execute(
            "SELECT username,file_path,upload_time FROM club_media "
            "WHERE club_id=%s ORDER BY id DESC", (cid,)
        )
        for u, fp, tm in cur.fetchall():
            st.write(f"{tm} by {u}")
            ext = fp.split('.')[-1].lower()
            if ext in ["png","jpg","jpeg","gif"]:
                try:
                     st.image(fp)
                except Exception:
                    st.warning("이미지를 불러올 수 없습니다.")
            elif ext in ["mp4","mov","avi","webm"]:
                try:
                     st.video(fp)
                except Exception:
                    st.warning("영상을 불러올 수 없습니다.")
            elif ext in ["mp3","wav","ogg"]:
                try:
                     st.audio(fp)
                except Exception:
                    st.warning("이미지를 불러올 수 없습니다.")
            else: st.write(f"[다운로드]({fp})")
            
    st.markdown("---")
