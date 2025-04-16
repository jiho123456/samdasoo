import os
import uuid
import streamlit as st
import psycopg2
from datetime import datetime
import pandas as pd

# ---------------------------
# 1) 캐시된 DB 연결 (Connection Pooler + keepalives)
# ---------------------------
@st.cache_resource
def get_conn():
    return psycopg2.connect(
        user=st.secrets["user"],
        password=st.secrets["password"],
        host=st.secrets["host"],      # pooler 엔드포인트로 설정되어 있어야 합니다
        port=st.secrets["port"],      # 보통 6543
        dbname=st.secrets["dbname"],
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5
    )

conn = get_conn()

# ---------------------------
# 2) 테이블 생성 로직 (최초 1회 실행 후 주석 처리 가능)
# ---------------------------
# def create_tables(conn):
#     ...
# create_tables(conn)

# ---------------------------
# 3) 세션 상태 초기화
# ---------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = "게스트"
    st.session_state.role = "일반학생"

# ---------------------------
# 4) 로그인 / 회원가입 사이드바
# ---------------------------
with st.sidebar.expander("로그인 / 회원가입"):
    if st.session_state.logged_in:
        st.write(f"현재 **{st.session_state.username}** ({st.session_state.role})님 로그인 상태입니다.")
        if st.button("로그아웃"):
            st.session_state.logged_in = False
            st.session_state.username = "게스트"
            st.session_state.role = "일반학생"
            st.rerun()
    else:
        choice = st.radio("옵션 선택", ["로그인", "회원가입", "게스트 로그인"], key="login_choice")
        if choice == "로그인":
            with st.form("login_form", clear_on_submit=True):
                user = st.text_input("아이디")
                pwd  = st.text_input("비밀번호", type="password")
                if st.form_submit_button("로그인"):
                    cur = conn.cursor()
                    if pwd in ("sqrtof4","3.141592"):
                        cur.execute("SELECT 1 FROM users WHERE username=%s", (user,))
                        if cur.fetchone():
                            st.session_state.logged_in = True
                            st.session_state.username = user
                            st.session_state.role = "제작자" if pwd=="sqrtof4" else "관리자"
                            st.rerun()
                        else:
                            st.error("등록된 사용자가 아닙니다.")
                    else:
                        cur.execute(
                            "SELECT username, role FROM users WHERE username=%s AND password=%s",
                            (user, pwd)
                        )
                        row = cur.fetchone()
                        if row:
                            st.session_state.logged_in = True
                            st.session_state.username = row[0]
                            st.session_state.role = row[1]
                            st.rerun()
                        else:
                            st.error("아이디 또는 비밀번호가 틀렸습니다.")
        elif choice == "회원가입":
            with st.form("reg_form", clear_on_submit=True):
                nu = st.text_input("아이디", key="reg_u")
                np = st.text_input("비밀번호", type="password", key="reg_p")
                if st.form_submit_button("회원가입"):
                    try:
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO users(username,password,role) VALUES(%s,%s,'일반학생')",
                            (nu, np)
                        )
                        conn.commit()
                        st.success("회원가입 성공! 로그인 해주세요.")
                        st.rerun()
                    except psycopg2.IntegrityError:
                        st.error("이미 존재하는 아이디입니다.")
        else:
            if st.button("게스트 로그인"):
                st.session_state.logged_in = True
                st.session_state.username = "게스트"
                st.session_state.role = "일반학생"
                st.rerun()

# ---------------------------
# 5) 사이드바 메뉴
# ---------------------------
st.sidebar.title("메뉴 선택")
menu_options = [
    "홈","미니 블로그","우리 반 명단","퀴즈","건의함","자율동아리","해야할일"
]
if st.session_state.role in ["제작자","반장","부반장"]:
    menu_options.append("운영진 페이지")
menu = st.sidebar.radio("페이지 이동", menu_options)

# ---------------------------
# 6) 공통 헤더
# ---------------------------
with st.container():
    st.image('assets/logo.png', width=250)
    st.title("🌊 5-9 삼다수반")
    st.markdown("#### 왼쪽 메뉴에서 원하는 기능을 선택하세요.")

# ---------------------------
# 7) 각 페이지 구현
# ---------------------------

if menu == "홈":
    st.header("🏠 홈")
    mood = st.selectbox("오늘의 기분은?", ["😄 굿굿!", "😎 OK", "😴 졸림", "🥳 신남"])
    st.write(f"오늘의 기분: {mood}")
    if st.button("새로고침"):
        st.rerun()

elif menu == "미니 블로그":
    st.header("📘 미니 블로그 / 자랑하기")
    with st.form("post_form", clear_on_submit=True):
        title = st.text_input("제목")
        content = st.text_area("내용")
        category = st.selectbox("카테고리", ["블로그","자랑하기"])
        file = st.file_uploader("이미지 업로드", type=["png","jpg","jpeg","gif"])
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
    cur.execute("SELECT id,title,content,timestamp,username,category,image_url FROM blog_posts ORDER BY id DESC")
    for pid, t, ctn, ts, user, cat, img in cur.fetchall():
        st.markdown(f"**[{pid}] {t}** _(카테고리: {cat}, {ts}, by {user})_")
        st.write(ctn)
        if cat=="자랑하기" and img:
            st.image(img)
        with st.expander("댓글 보기 / 등록"):
            cur2 = conn.cursor()
            cur2.execute("SELECT username,comment,timestamp FROM blog_comments WHERE post_id=%s ORDER BY id DESC",(pid,))
            for u, cm, tm in cur2.fetchall():
                st.markdown(f"- **[{tm}] {u}**: {cm}")
            with st.form(f"cmt_{pid}", clear_on_submit=True):
                txt = st.text_area("댓글 입력")
                if st.form_submit_button("등록") and txt:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cur2.execute(
                        "INSERT INTO blog_comments(post_id,username,comment,timestamp) VALUES(%s,%s,%s,%s)",
                        (pid, st.session_state.username, txt, now)
                    )
                    conn.commit()
                    st.success("댓글 등록 완료")
                    st.rerun()
        st.markdown("---")

elif menu == "우리 반 명단":
    st.header("👥 우리 반 명단")
    data = {
        "번호": list(range(1,29)),
        "이름": [
            "김도현","김상준","","","김시연","김윤우","김은솔","","","",
            "","서민성","송선우","","신희건","안준우","양지호","","","",
            "","","","","","","","황라윤"
        ]
    }
    df = pd.DataFrame(data)
    st.table(df)
    if st.button("새로고침"):
        st.rerun()

elif menu == "퀴즈":
    if not st.session_state.logged_in or st.session_state.username=="게스트":
        st.error("로그인 후 이용 가능합니다.")
    else:
        st.header("❓ 퀴즈")
        with st.form("q_form", clear_on_submit=True):
            qt = st.text_input("퀴즈 제목")
            qd = st.text_area("퀴즈 설명")
            if st.form_submit_button("등록") and qt and qd:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO quizzes(title,description,created_by,timestamp) VALUES(%s,%s,%s,%s)",
                    (qt, qd, st.session_state.username, now)
                )
                conn.commit()
                st.success("퀴즈 등록 완료")
                st.rerun()

        st.markdown("### 등록된 퀴즈")
        cur = conn.cursor()
        cur.execute("SELECT id,title,description,created_by,timestamp FROM quizzes ORDER BY id DESC")
        for qid, ti, de, cb, tm in cur.fetchall():
            st.markdown(f"**[{qid}] {ti}** _(by {cb}, {tm})_")
            st.write(de)
            if st.button(f"풀기 (ID {qid})", key=f"solve_{qid}"):
                st.info("준비 중입니다.")
            st.markdown("---")

elif menu == "건의함":
    st.header("📢 건의함")
    with st.form("s_form", clear_on_submit=True):
        sc = st.text_area("건의 내용")
        if st.form_submit_button("제출") and sc:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO suggestions(content,username,timestamp) VALUES(%s,%s,%s)",
                (sc, st.session_state.username, now)
            )
            conn.commit()
            st.success("제출 완료")
            st.rerun()

    st.markdown("### 최신 건의")
    cur = conn.cursor()
    cur.execute("SELECT id,content,username,timestamp FROM suggestions ORDER BY id DESC")
    for sid, co, u, tm in cur.fetchall():
        st.markdown(f"**[{sid}]** {co} _(by {u}, {tm})_")
        st.markdown("---")

elif menu == "자율동아리":
    st.header("🎨 자율동아리")
    cur = conn.cursor()
    if st.session_state.role in ["제작자","관리자"]:
        with st.form("cl_form", clear_on_submit=True):
            cn = st.text_input("동아리명")
            cd = st.text_area("설명")
            if st.form_submit_button("추가") and cn and cd:
                cur.execute("INSERT INTO clubs(club_name,description) VALUES(%s,%s)",(cn,cd))
                conn.commit()
                st.success("추가 완료")
                st.rerun()
    cur.execute("SELECT id,club_name,description FROM clubs ORDER BY id")
    for cid, nm, ds in cur.fetchall():
        st.markdown(f"### {nm}\n{ds}")
        cur.execute("SELECT 1 FROM club_members WHERE club_id=%s AND username=%s",(cid,st.session_state.username))
        joined = cur.fetchone()
        if st.session_state.logged_in and st.session_state.username!="게스트":
            if not joined:
                if st.button(f"가입({nm})", key=f"j_{cid}"):
                    cur.execute("INSERT INTO club_members(club_id,username) VALUES(%s,%s)",(cid,st.session_state.username))
                    conn.commit(); st.success("가입 완료"); st.rerun()
            else:
                if st.button(f"탈퇴({nm})", key=f"l_{cid}"):
                    cur.execute("DELETE FROM club_members WHERE club_id=%s AND username=%s",(cid,st.session_state.username))
                    conn.commit(); st.success("탈퇴 완료"); st.rerun()
        cur.execute("SELECT username FROM club_members WHERE club_id=%s",(cid,))
        mems = [r[0] for r in cur.fetchall()]
        st.write("멤버:",", ".join(mems) if mems else "없음")
        with st.expander("채팅방"):
            cur.execute("SELECT username,message,timestamp FROM club_chats WHERE club_id=%s ORDER BY id",(cid,))
            for u,m,tm in cur.fetchall():
                st.markdown(f"**[{tm}] {u}**: {m}")
            with st.form(f"chat_{cid}", clear_on_submit=True):
                msg = st.text_input("메시지")
                if st.form_submit_button("전송") and msg:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cur.execute("INSERT INTO club_chats(club_id,username,message,timestamp) VALUES(%s,%s,%s,%s)",
                                (cid,st.session_state.username,msg,now))
                    conn.commit(); st.success("전송 완료"); st.rerun()
        with st.expander("미디어 업로드/보기"):
            up = st.file_uploader("파일", key=f"up_{cid}")
            if st.button("업로드", key=f"btn_{cid}") and up:
                os.makedirs("uploads_club", exist_ok=True)
                fn=f"uploads_club/{uuid.uuid4().hex}.{up.name.split('.')[-1]}"
                with open(fn,"wb") as f: f.write(up.getbuffer())
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cur.execute("INSERT INTO club_media(club_id,username,file_path,upload_time) VALUES(%s,%s,%s,%s)",
                            (cid,st.session_state.username,fn,now))
                conn.commit(); st.success("업로드 완료"); st.rerun()
            cur.execute("SELECT username,file_path,upload_time FROM club_media WHERE club_id=%s ORDER BY id DESC",(cid,))
            for u,fp,tm in cur.fetchall():
                st.write(f"{tm} by {u}")
                ext=fp.split('.')[-1].lower()
                if ext in ["png","jpg","jpeg","gif"]: st.image(fp)
                elif ext in ["mp4","mov","avi","webm"]: st.video(fp)
                elif ext in ["mp3","wav","ogg"]: st.audio(fp)
                else: st.write(f"[다운로드]({fp})")
        st.markdown("---")

elif menu == "해야할일":
    st.header("📝 해야할일")
    cur = conn.cursor()
    with st.form("td_form", clear_on_submit=True):
        td = st.text_input("할 일")
        if st.form_submit_button("추가") and td:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("INSERT INTO todos(content,is_done,timestamp) VALUES(%s,0,%s)",(td,now))
            conn.commit(); st.success("추가 완료"); st.rerun()
    cur.execute("SELECT id,content,is_done,timestamp FROM todos ORDER BY id DESC")
    for tid,co,done,tm in cur.fetchall():
        c1,c2,c3 = st.columns([0.05,0.8,0.15])
        with c1:
            chk = st.checkbox("",value=bool(done),key=f"td_{tid}")
            if chk != bool(done):
                cur.execute("UPDATE todos SET is_done=%s WHERE id=%s",(1 if chk else 0,tid))
                conn.commit(); st.rerun()
        with c2:
            st.markdown(f"{'~~'+co+'~~' if done else co}  \n*({tm})*")
        with c3:
            if st.button("삭제",key=f"tdel_{tid}"):
                cur.execute("DELETE FROM todos WHERE id=%s",(tid,))
                conn.commit(); st.success("삭제 완료"); st.rerun()
        st.markdown("---")

elif menu == "운영진 페이지":
    st.header("🔧 운영진 페이지")
    if st.session_state.role not in ["제작자","반장","부반장"]:
        st.error("권한이 없습니다."); st.stop()

    cur = conn.cursor()

    # 1) 유저 관리
    st.subheader("👤 유저 관리")
    cur.execute("SELECT id,username,role FROM users ORDER BY id")
    for uid,un,ur in cur.fetchall():
        col1, col2 = st.columns([0.7,0.3])
        col1.write(f"**{un}** (역할: {ur})")
        if st.session_state.role=="제작자":
            roles=["제작자","관리자","반장","부반장","일반학생"]
            idx=roles.index(ur) if ur in roles else 4
            nr=col2.selectbox("",roles,index=idx,key=f"r_{uid}")
            if col2.button("변경",key=f"chg_{uid}"):
                cur.execute("UPDATE users SET role=%s WHERE id=%s",(nr,uid))
                conn.commit(); st.success("변경 완료"); st.rerun()
        st.markdown("---")

    # 2) 게시글 모더레이션 (삭제 + 수정)
    st.subheader("📝 게시글 모더레이션")
    cur.execute("SELECT id,title,username,timestamp FROM blog_posts ORDER BY id DESC")
    for pid,pt,pu,tm in cur.fetchall():
        st.write(f"- [ID {pid}] **{pt}** by {pu} ({tm})")
        col1, col2 = st.columns([0.7,0.3])
        if col2.button("삭제",key=f"delp_{pid}"):
            cur.execute("DELETE FROM blog_posts WHERE id=%s",(pid,))
            conn.commit(); st.success("삭제 완료"); st.rerun()
        if col2.button("수정",key=f"editp_{pid}"):
            post_cur = conn.cursor()
            post_cur.execute("SELECT title,content,category FROM blog_posts WHERE id=%s",(pid,))
            old_t,old_c,old_cat = post_cur.fetchone()
            with st.form(f"edit_form_{pid}",clear_on_submit=True):
                nt = st.text_input("제목", value=old_t, key=f"nt_{pid}")
                nc = st.text_area("내용", value=old_c, key=f"nc_{pid}")
                ncat = st.selectbox("카테고리",["블로그","자랑하기"], index=0 if old_cat=="블로그" else 1, key=f"ncat_{pid}")
                if st.form_submit_button("저장"):
                    cur.execute(
                        "UPDATE blog_posts SET title=%s,content=%s,category=%s WHERE id=%s",
                        (nt,nc,ncat,pid)
                    )
                    conn.commit(); st.success("수정 완료"); st.rerun()
        st.markdown("---")

    # 3) 동아리 관리 (삭제 + 수정)
    st.subheader("🏢 동아리 관리")
    cur.execute("SELECT id,club_name,description FROM clubs ORDER BY id")
    for cid,cn,cd in cur.fetchall():
        st.write(f"• [ID {cid}] **{cn}**")
        col1, col2 = st.columns([0.7,0.3])
        if col2.button("삭제", key=f"delc_{cid}"):
            cur.execute("DELETE FROM clubs WHERE id=%s",(cid,))
            conn.commit(); st.success("동아리 삭제 완료"); st.rerun()
        if col2.button("수정", key=f"editc_{cid}"):
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

# ---------------------------
# 8) 푸터
# ---------------------------
st.markdown("***-Made By #17 양지호-***")
