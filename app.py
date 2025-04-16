import os
import uuid
import streamlit as st
import psycopg2
from datetime import datetime
import pandas as pd

def init_db():
    USER = st.secrets["user"]
    PASSWORD = st.secrets["password"]
    HOST = st.secrets["host"]
    PORT = st.secrets["port"]
    DBNAME = st.secrets["dbname"]

    # Connect to the database
    try:
        conn = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            dbname=DBNAME
        )
        
        # Create a cursor to execute SQL queries
        c = conn.cursor()

    except Exception as e:
        st.error("서버 데이터베이스 문제임 이거 보면 제작자한테 말하셈")
        st.error(e)


    # 1) users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT DEFAULT '일반학생'
        )
    ''')
    conn.commit()

    # 2) blog_posts: 미니 블로그 & 자랑하기 통합
    c.execute('''
        CREATE TABLE IF NOT EXISTS blog_posts (
            id SERIAL PRIMARY KEY,
            title TEXT,
            content TEXT,
            timestamp TEXT,
            username TEXT,
            category TEXT DEFAULT '블로그',
            image_url TEXT DEFAULT ''
        )
    ''')
    conn.commit()

    # 3) blog_comments: 댓글 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS blog_comments (
            id SERIAL PRIMARY KEY,
            post_id INTEGER,
            username TEXT,
            comment TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()

    # 4) clubs and related tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS clubs (
            id SERIAL PRIMARY KEY,
            club_name TEXT,
            description TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS club_members (
            id SERIAL PRIMARY KEY,
            club_id INTEGER,
            username TEXT,
            UNIQUE(club_id, username)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS club_chats (
            id SERIAL PRIMARY KEY,
            club_id INTEGER,
            username TEXT,
            message TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()

    # club_media: 동아리 미디어 (이미지/동영상 등)
    c.execute('''
        CREATE TABLE IF NOT EXISTS club_media (
            id SERIAL PRIMARY KEY,
            club_id INTEGER,
            username TEXT,
            file_path TEXT,
            upload_time TEXT
        )
    ''')
    conn.commit()

    # 5) quizzes and quiz_attempts tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS quizzes (
            id SERIAL PRIMARY KEY,
            title TEXT,
            description TEXT,
            created_by TEXT,
            timestamp TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id SERIAL PRIMARY KEY,
            quiz_id INTEGER,
            username TEXT,
            score INTEGER,
            timestamp TEXT
        )
    ''')
    conn.commit()

    # 6) suggestions: 건의함
    c.execute('''
        CREATE TABLE IF NOT EXISTS suggestions (
            id SERIAL PRIMARY KEY,
            content TEXT,
            username TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()

    # todos: 해야할일
    c.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id SERIAL PRIMARY KEY,
            content TEXT,
            is_done INTEGER DEFAULT 0, 
            timestamp TEXT
        )
    ''')
    conn.commit()

    return conn

conn = init_db()

# ---------------------------
# 세션 상태 초기화
# ---------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = "게스트"
    st.session_state.role = "일반학생"

# ---------------------------
# 로그인 / 회원가입
# ---------------------------
with st.sidebar.expander("로그인 / 회원가입"):
    if st.session_state.logged_in:
        st.write(f"현재 **{st.session_state.username}** ({st.session_state.role})님 로그인 상태입니다.")
        st.info(f"안녕하세요, {st.session_state.username}님! 반가워요.")
        if st.button("로그아웃"):
            st.session_state.logged_in = False
            st.session_state.username = "게스트"
            st.session_state.role = "일반학생"
            st.success("로그아웃 되었습니다.")
            st.rerun()
    else:
        login_choice = st.radio("옵션 선택", ["로그인", "회원가입", "게스트 로그인"], key="login_choice")
        if login_choice == "로그인":
            with st.form("login_form", clear_on_submit=True):
                username = st.text_input("아이디")
                password = st.text_input("비밀번호", type="password")
                submitted = st.form_submit_button("로그인")
                if submitted:
                    c = conn.cursor()
                    if password == "sqrtof4":  # 제작자 인증
                        c.execute("SELECT * FROM users WHERE username=%s", (username,))
                        user = c.fetchone()
                        if user:
                            st.session_state.logged_in = True
                            st.session_state.username = username
                            st.session_state.role = "제작자"
                            st.success(f"{username}님, 제작자 인증 완료!")
                            st.rerun()
                        else:
                            st.error("등록된 사용자가 아닙니다.")
                    elif password == "3.141592":  # 관리자 인증
                        c.execute("SELECT * FROM users WHERE username=%s", (username,))
                        user = c.fetchone()
                        if user:
                            st.session_state.logged_in = True
                            st.session_state.username = username
                            st.session_state.role = "관리자"
                            st.success(f"{username}님, 관리자 인증 완료!")
                            st.rerun()
                        else:
                            st.error("등록된 사용자가 아닙니다.")
                    else:
                        c.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
                        user = c.fetchone()
                        if user:
                            st.session_state.logged_in = True
                            st.session_state.username = user[1]
                            st.session_state.role = user[3] if len(user) >= 4 else "일반학생"
                            st.success(f"{username}님, 환영합니다! (역할: {st.session_state.role})")
                            st.rerun()
                        else:
                            st.error("아이디 또는 비밀번호가 틀렸습니다.")
        elif login_choice == "회원가입":
            with st.form("register_form", clear_on_submit=True):
                new_username = st.text_input("아이디 (회원가입)", key="reg_username")
                new_password = st.text_input("비밀번호 (회원가입)", type="password", key="reg_password")
                submitted = st.form_submit_button("회원가입")
                if submitted:
                    try:
                        c = conn.cursor()
                        c.execute("""
                            INSERT INTO users (username, password, role) 
                            VALUES (%s, %s, %s)
                        """, (new_username, new_password, "일반학생"))
                        conn.commit()
                        st.success("회원가입 성공! 이제 로그인 해주세요.")
                        st.rerun()
                    except psycopg2.IntegrityError:
                        st.error("이미 존재하는 아이디입니다.")
        elif login_choice == "게스트 로그인":
            if st.button("게스트 모드로 로그인"):
                st.session_state.logged_in = True
                st.session_state.username = "게스트"
                st.session_state.role = "일반학생"
                st.success("게스트 모드로 로그인 되었습니다.")
                st.rerun()

# ---------------------------
# Sidebar Menu
# ---------------------------
st.sidebar.title("메뉴 선택")
menu_options = [
    "홈",
    "미니 블로그",
    "우리 반 명단",
    "퀴즈",
    "건의함",
    "자율동아리",
    "해야할일"
]
if st.session_state.role in ["제작자", "반장", "부반장"]:
    menu_options.append("운영진 페이지")
menu = st.sidebar.radio("페이지 이동", menu_options)

# ---------------------------
# 공통 헤더
# ---------------------------
with st.container():
    st.image('assets/logo.png', width=250)
    st.title("🌊 5-9 삼다수반")
    st.markdown("""#### 안녕하세요? 제작자인 양지호입니다.
왼쪽 탭에서 원하는 메뉴를 선택하세요.
(하단의 '새로고침' 버튼을 누르면 최신 내용이 반영됩니다.)
###### 공지: 서버 데이터베이스 이전 완료되었습니다. 이제 서버가 정상작동 할 것입니다.(아마도)
""")

# ---------------------------
# 홈 페이지
# ---------------------------
if menu == "홈":
    st.header("🏠 홈")
    st.markdown("""
    **삼다수반** 웹사이트입니다.  
    이 웹사이트는 블로그, 동아리, 건의함, 퀴즈, 해야할일 등으로 **즐겁게 생활**을 돕습니다.
    """)
    mood = st.selectbox("📆 오늘의 기분은?", ["😄 굿굿!", "😎 ㄴㅇㅅ", "😴 졸기 직전...", "🥳 해피해피해피"])
    st.write(f"오늘의 기분: {mood}")
    if st.button("새로고침"):
        st.rerun()

# ---------------------------
# 미니 블로그 (자랑하기 통합)
# ---------------------------
elif menu == "미니 블로그":
    st.header("📘 미니 블로그 / 자랑하기")
    st.markdown("글 작성 시 '블로그' 또는 '자랑하기' 카테고리를 선택하고, 필요하면 이미지도 업로드할 수 있어요.")
    with st.form("blog_form", clear_on_submit=True):
        title = st.text_input("글 제목", placeholder="제목 입력")
        content = st.text_area("글 내용", placeholder="내용 입력")
        category = st.selectbox("카테고리", ["블로그", "자랑하기"])
        uploaded_file = st.file_uploader("이미지 파일 업로드 (선택)", type=["png", "jpg", "jpeg", "gif"])
        submitted = st.form_submit_button("게시하기")
        if submitted and title and content:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            image_path = ""
            if uploaded_file is not None:
                if not os.path.exists("uploads"):
                    os.makedirs("uploads")
                ext = uploaded_file.name.split('.')[-1]
                unique_filename = f"{uuid.uuid4().hex}.{ext}"
                save_path = os.path.join("uploads", unique_filename)
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                image_path = save_path
            c = conn.cursor()
            c.execute("""
                INSERT INTO blog_posts (title, content, timestamp, username, category, image_url)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (title, content, now, st.session_state.username, category, image_path))
            conn.commit()
            st.success("게시글 등록 완료")
            st.rerun()
    st.markdown("### 최신 게시글")
    c = conn.cursor()
    c.execute("""
        SELECT id, title, content, timestamp, username, category, image_url
        FROM blog_posts
        ORDER BY id DESC
    """)
    blog_data = c.fetchall()
    if blog_data:
        for row in blog_data:
            post_id, btitle, bcontent, btimestamp, bauthor, bcategory, bimage_url = row
            st.markdown(f"**[{post_id}] {btitle}** _(카테고리: {bcategory}, 작성일: {btimestamp}, 작성자: {bauthor})_")
            st.write(bcontent)
            if bcategory == "자랑하기" and bimage_url:
                st.image(bimage_url)
            with st.expander("댓글 달기"):
                with st.form(f"blog_comment_form_{post_id}", clear_on_submit=True):
                    comment_text = st.text_area("댓글 입력", placeholder="댓글 입력")
                    submitted_comment = st.form_submit_button("댓글 등록")
                    if submitted_comment and comment_text:
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        c.execute("""
                            INSERT INTO blog_comments (post_id, username, comment, timestamp)
                            VALUES (%s, %s, %s, %s)
                        """, (post_id, st.session_state.username, comment_text, now))
                        conn.commit()
                        st.success("댓글 등록 완료")
                        st.rerun()
            c.execute("""
                SELECT username, comment, timestamp 
                FROM blog_comments
                WHERE post_id=%s
                ORDER BY id DESC
            """, (post_id,))
            comments = c.fetchall()
            if comments:
                st.markdown("**댓글:**")
                for comm in comments:
                    comm_username, comm_text, comm_time = comm
                    st.markdown(f"- **[{comm_time}] {comm_username}**: {comm_text}")
            if st.session_state.logged_in and st.session_state.role in ["제작자", "관리자"]:
                if st.button(f"삭제 (ID {post_id})", key=f"delete_{post_id}"):
                    c.execute("DELETE FROM blog_posts WHERE id=%s", (post_id,))
                    conn.commit()
                    st.success("게시글 삭제 완료")
                    st.rerun()
            st.markdown("---")
    else:
        st.info("등록된 게시글이 없습니다.")
    if st.button("새로고침"):
        st.rerun()

# ---------------------------
# 우리 반 명단
# ---------------------------
elif menu == "우리 반 명단":
    st.header("👥 우리 반 명단")
    data = {
        "번호": list(range(1, 29)),
        "이름": [
            "김도현", "김상준", "", "", "김시연", "김윤우", "김은솔", "", "", "",
            "", "서민성", "송선우", "", "신희건", "안준우", "양지호", "", "", "",
            "", "", "", "", "", "", "", "황라윤"
        ]
    }
    roster_df = pd.DataFrame(data)
    st.table(roster_df)
    if st.button("새로고침"):
        st.rerun()

# ---------------------------
# 퀴즈
# ---------------------------
elif menu == "퀴즈":
    if not st.session_state.logged_in or st.session_state.username == "게스트":
        st.error("퀴즈 기능은 로그인 후 사용 가능합니다.")
    else:
        st.header("❓ 퀴즈")
        c = conn.cursor()
        st.subheader("퀴즈 생성 (본인 퀴즈 등록)")
        with st.form("quiz_form", clear_on_submit=True):
            quiz_title = st.text_input("퀴즈 제목", placeholder="제목 입력")
            quiz_desc = st.text_area("퀴즈 설명", placeholder="설명 입력")
            submitted_quiz = st.form_submit_button("퀴즈 등록")
            if submitted_quiz and quiz_title and quiz_desc:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("""
                    INSERT INTO quizzes (title, description, created_by, timestamp) 
                    VALUES (%s, %s, %s, %s)
                """, (quiz_title, quiz_desc, st.session_state.username, now))
                conn.commit()
                st.success("퀴즈 등록 완료")
                st.rerun()
        st.markdown("### 등록된 퀴즈 목록")
        c.execute("""
            SELECT id, title, description, created_by, timestamp
            FROM quizzes
            ORDER BY id DESC
        """)
        quizzes = c.fetchall()
        if quizzes:
            for quiz in quizzes:
                quiz_id, title, desc, creator, ts = quiz
                st.markdown(f"**[{quiz_id}] {title}** _(작성자: {creator}, {ts})_")
                st.write(desc)
                if st.button(f"퀴즈 풀기 (ID {quiz_id})", key=f"solve_{quiz_id}"):
                    st.info("퀴즈 풀기 기능은 추후 업데이트 예정입니다.")
                st.markdown("---")
        else:
            st.info("등록된 퀴즈가 없습니다.")
    if st.button("새로고침"):
        st.rerun()

# ---------------------------
# 건의함
# ---------------------------
elif menu == "건의함":
    st.header("📢 건의함")
    st.markdown("학교에 건의할 내용을 작성하세요.")
    c = conn.cursor()
    with st.form("suggestion_form", clear_on_submit=True):
        suggestion_content = st.text_area("건의 내용", placeholder="내용 입력")
        submitted_sugg = st.form_submit_button("건의 제출")
        if submitted_sugg and suggestion_content:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("""
                INSERT INTO suggestions (content, username, timestamp)
                VALUES (%s, %s, %s)
            """, (suggestion_content, st.session_state.username, now))
            conn.commit()
            st.success("건의 제출 완료")
            st.rerun()
    st.markdown("### 최신 건의 목록")
    c.execute("""
        SELECT id, content, username, timestamp 
        FROM suggestions
        ORDER BY id DESC
    """)
    suggestions = c.fetchall()
    if suggestions:
        for sugg in suggestions:
            sugg_id, content, author, ts = sugg
            st.markdown(f"**[{sugg_id}]** _(작성자: {author}, {ts})_")
            st.write(content)
            st.markdown("---")
    else:
        st.info("등록된 건의가 없습니다.")
    if st.button("새로고침"):
        st.rerun()

# ---------------------------
# 자율동아리
# ---------------------------
elif menu == "자율동아리":
    st.header("🎨 자율동아리")
    st.markdown("동아리 리스트, 가입/탈퇴, 채팅, 그리고 미디어(이미지/영상 등) 업로드 기능입니다.")
    c = conn.cursor()
    if st.session_state.logged_in and st.session_state.role in ["제작자", "관리자"]:
        with st.form("club_form", clear_on_submit=True):
            club_name = st.text_input("동아리명", placeholder="동아리 이름")
            description = st.text_area("동아리 설명", placeholder="설명 입력")
            submitted = st.form_submit_button("동아리 추가")
            if submitted and club_name and description:
                c.execute("INSERT INTO clubs (club_name, description) VALUES (%s, %s)", (club_name, description))
                conn.commit()
                st.success("동아리 추가 완료")
                st.rerun()
    c.execute("SELECT id, club_name, description FROM clubs ORDER BY id ASC")
    clubs_data = c.fetchall()
    if clubs_data:
        for row in clubs_data:
            cid, club_name, description = row
            st.markdown(f"### {club_name}")
            st.write(description)
            if st.session_state.logged_in and st.session_state.username != "게스트":
                c.execute("SELECT * FROM club_members WHERE club_id=%s AND username=%s", (cid, st.session_state.username))
                is_member = (c.fetchone() is not None)
                if not is_member:
                    if st.button(f"가입하기 ({club_name})", key=f"join_club_{cid}"):
                        c.execute("INSERT INTO club_members (club_id, username) VALUES (%s, %s) ON CONFLICT DO NOTHING", (cid, st.session_state.username))
                        conn.commit()
                        st.success(f"{club_name} 동아리에 가입했습니다!")
                        st.rerun()
                else:
                    if st.button(f"탈퇴하기 ({club_name})", key=f"leave_club_{cid}"):
                        c.execute("DELETE FROM club_members WHERE club_id=%s AND username=%s", (cid, st.session_state.username))
                        conn.commit()
                        st.success(f"{club_name} 동아리에서 탈퇴했습니다!")
                        st.rerun()
            else:
                st.info("동아리 가입/탈퇴는 로그인 필수입니다.")
            c.execute("SELECT username FROM club_members WHERE club_id=%s", (cid,))
            members = c.fetchall()
            if members:
                member_list = ", ".join([m[0] for m in members])
                st.markdown(f"**멤버:** {member_list}")
            else:
                st.markdown("**멤버:** 없음")
            if st.button("채팅방 새로고침", key=f"refresh_chat_{cid}"):
                st.rerun()
            with st.expander("동아리 채팅방"):
                st.markdown("동아리 채팅 메시지")
                with st.form(f"club_chat_form_{cid}", clear_on_submit=True):
                    club_message = st.text_input("메시지 입력", placeholder="내용 입력")
                    submitted_chat = st.form_submit_button("전송")
                    if submitted_chat and club_message:
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        c.execute("""
                            INSERT INTO club_chats (club_id, username, message, timestamp)
                            VALUES (%s, %s, %s, %s)
                        """, (cid, st.session_state.username, club_message, now))
                        conn.commit()
                        st.success("채팅 메시지 전송 완료")
                        st.rerun()
                c.execute("""
                    SELECT username, message, timestamp 
                    FROM club_chats 
                    WHERE club_id=%s
                    ORDER BY id DESC
                """, (cid,))
                club_chats = c.fetchall()
                if club_chats:
                    for chat_username, chat_msg, chat_time in reversed(club_chats):
                        st.markdown(f"**[{chat_time}] {chat_username}**: {chat_msg}")
                else:
                    st.info("채팅 메시지가 없습니다.")
            with st.expander("동아리 미디어 업로드 / 보기"):
                st.markdown(f"**{club_name}** 미디어 업로드")
                uploaded_media = st.file_uploader("파일 업로드 (이미지, 동영상, 오디오, 문서 등)", key=f"media_uploader_{cid}", type=None)
                if st.button("업로드", key=f"upload_btn_{cid}") and uploaded_media is not None:
                    if not os.path.exists("uploads_club"):
                        os.makedirs("uploads_club")
                    ext = uploaded_media.name.split('.')[-1].lower()
                    unique_filename = f"{uuid.uuid4().hex}.{ext}"
                    save_path = os.path.join("uploads_club", unique_filename)
                    with open(save_path, "wb") as f:
                        f.write(uploaded_media.getbuffer())
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("""
                        INSERT INTO club_media (club_id, username, file_path, upload_time)
                        VALUES (%s, %s, %s, %s)
                    """, (cid, st.session_state.username, save_path, now))
                    conn.commit()
                    st.success("미디어 업로드 완료!")
                    st.rerun()
                st.markdown(f"**{club_name} 미디어 목록**")
                c.execute("""
                    SELECT id, username, file_path, upload_time
                    FROM club_media
                    WHERE club_id=%s
                    ORDER BY id DESC
                """, (cid,))
                media_rows = c.fetchall()
                if media_rows:
                    for mid, muser, mpath, mtime in media_rows:
                        st.write(f"[{mid}] 업로드: {muser} / {mtime}")
                        file_ext = mpath.split('.')[-1].lower()
                        if file_ext in ["png", "jpg", "jpeg", "gif"]:
                            st.image(mpath)
                        elif file_ext in ["mp4", "mov", "avi", "webm"]:
                            st.video(mpath)
                        elif file_ext in ["mp3", "wav", "ogg"]:
                            st.audio(mpath)
                        else:
                            st.write(f"[다운로드 링크]({mpath})")
                        st.markdown("---")
                else:
                    st.info("아직 업로드된 미디어가 없습니다.")
            st.markdown("---")
    else:
        st.info("등록된 동아리가 없습니다.")
    if st.button("새로고침"):
        st.rerun()

# ---------------------------
# 해야할일 (ToDo)
# ---------------------------
elif menu == "해야할일":
    st.header("📝 해야할일 (ToDo)")
    st.markdown("오늘 학교숙제 뭐였지? 그럴 땐 여기서 확인하세요!")
    c = conn.cursor()
    with st.form("todo_form", clear_on_submit=True):
        todo_content = st.text_input("할 일 내용", placeholder="예: 영어 숙제하기")
        submitted_todo = st.form_submit_button("추가하기")
        if submitted_todo and todo_content:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("""
                INSERT INTO todos (content, is_done, timestamp)
                VALUES (%s, %s, %s)
            """, (todo_content, 0, now))
            conn.commit()
            st.success("할 일이 추가되었습니다!")
            st.rerun()
    st.markdown("### 할일 목록")
    c.execute("""
        SELECT id, content, is_done, timestamp
        FROM todos
        ORDER BY id DESC
    """)
    todos = c.fetchall()
    if todos:
        for t in todos:
            tid, content, is_done, ttime = t
            col1, col2, col3 = st.columns([0.05, 0.8, 0.15])
            with col1:
                checked = st.checkbox("", value=bool(is_done), key=f"todo_done_{tid}")
                if checked != bool(is_done):
                    new_val = 1 if checked else 0
                    c.execute("UPDATE todos SET is_done=%s WHERE id=%s", (new_val, tid))
                    conn.commit()
                    st.experimental_rerun()
            with col2:
                done_str = "~~" if is_done else ""
                st.markdown(f"{done_str}{content}{done_str}  \n*({ttime})*")
            with col3:
                if st.button("삭제", key=f"delete_todo_{tid}"):
                    c.execute("DELETE FROM todos WHERE id=%s", (tid,))
                    conn.commit()
                    st.success("할 일이 삭제되었습니다.")
                    st.rerun()
            st.markdown("---")
    else:
        st.info("등록된 할 일이 없습니다.")
    if st.button("새로고침"):
        st.rerun()

# ---------------------------
# 운영진 페이지 (Moderator Page)
# ---------------------------
elif menu == "운영진 페이지":
    st.header("🔧 운영진 페이지 (Moderator Page)")
    if st.session_state.role not in ["제작자", "반장", "부반장"]:
        st.error("이 페이지에 접근할 권한이 없습니다.")
        st.stop()
    st.markdown("여기는 **반장, 부반장, 제작자** 전용 페이지입니다.")
    st.subheader("👤 유저 관리")
    c = conn.cursor()
    c.execute("SELECT id, username, role FROM users ORDER BY id ASC")
    user_list = c.fetchall()
    for user_id, uname, urole in user_list:
        st.write(f"**{uname}** (현재 역할: {urole})")
        if st.session_state.role == "제작자":
            roles = ["제작자", "관리자", "반장", "부반장", "일반학생"]
            current_index = roles.index(urole) if urole in roles else roles.index("일반학생")
            new_role = st.selectbox(
                f"역할 변경 ({uname})",
                roles,
                index=current_index,
                key=f"role_select_{user_id}"
            )
            if st.button(f"역할 업데이트 ({uname})", key=f"update_role_{user_id}"):
                c.execute("UPDATE users SET role=%s WHERE id=%s", (new_role, user_id))
                conn.commit()
                st.success(f"{uname}님의 역할이 **{new_role}**(으)로 변경되었습니다.")
                st.rerun()
        else:
            st.info("※ 역할 변경 권한은 '제작자'에게만 있습니다.")
        st.markdown("---")
    st.subheader("📝 게시글 모더레이션")
    c.execute("SELECT id, title, username, timestamp FROM blog_posts ORDER BY id DESC")
    all_posts = c.fetchall()
    if all_posts:
        for pid, ptitle, puser, pts in all_posts:
            st.write(f"- [ID {pid}] **{ptitle}** | 작성자: {puser} | 작성일: {pts}")
            if st.button(f"게시글 삭제 (ID {pid})", key=f"mod_delete_{pid}"):
                c.execute("DELETE FROM blog_posts WHERE id=%s", (pid,))
                conn.commit()
                st.success("게시글을 삭제했습니다.")
                st.rerun()
    else:
        st.info("등록된 게시글이 없습니다.")

# ---------------------------
# 하단 제작자 표시
# ---------------------------
st.markdown("***-Made By #17 양지호-***")
