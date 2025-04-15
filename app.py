import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd

# ---------------------------
# 데이터베이스 초기화 함수 (추가 테이블 포함)
# ---------------------------
def init_db():
    conn = sqlite3.connect('samdasu.db', check_same_thread=False)
    c = conn.cursor()
    # 사용자 테이블: role 컬럼 추가 (제작자, 관리자, 헌재, 반장, 부반장, 일반학생)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT DEFAULT '일반학생'
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS blog_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            timestamp TEXT,
            username TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS clubs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            club_name TEXT,
            description TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS club_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            club_id INTEGER,
            username TEXT,
            UNIQUE(club_id, username)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS club_chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            club_id INTEGER,
            username TEXT,
            message TEXT,
            timestamp TEXT
        )
    ''')
    # 헌재(의뢰) 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS petitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            timestamp TEXT,
            username TEXT,
            status TEXT DEFAULT '처리 안됨'
        )
    ''')
    # 헌재 의뢰별 채팅 테이블 (잠금방)
    c.execute('''
        CREATE TABLE IF NOT EXISTS petition_chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            petition_id INTEGER,
            username TEXT,
            message TEXT,
            timestamp TEXT
        )
    ''')
    # 자랑하기 게시판
    c.execute('''
        CREATE TABLE IF NOT EXISTS proud_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            image_url TEXT,
            timestamp TEXT,
            username TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS proud_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            username TEXT,
            comment TEXT,
            timestamp TEXT
        )
    ''')
    # 퀴즈 테이블 (간단 구현)
    c.execute('''
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            created_by TEXT,
            timestamp TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER,
            username TEXT,
            score INTEGER,
            timestamp TEXT
        )
    ''')
    # 건의함
    c.execute('''
        CREATE TABLE IF NOT EXISTS suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            username TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    return conn

conn = init_db()

# ---------------------------
# 세션 상태 초기화 (로그인/채팅 등)
# ---------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = "게스트"
    st.session_state.role = "일반학생"  # 제작자, 관리자, 헌재, 반장, 부반장, 일반학생
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []  # 일반 채팅

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
    else:
        login_choice = st.radio("옵션 선택", ["로그인", "회원가입", "게스트 로그인"], key="login_choice")
        if login_choice == "로그인":
            with st.form("login_form", clear_on_submit=True):
                username = st.text_input("아이디")
                password = st.text_input("비밀번호", type="password")
                submitted = st.form_submit_button("로그인")
                if submitted:
                    c = conn.cursor()
                    # 특수 비밀번호에 따른 역할 인증
                    if password == "sqrtof4":  # 제작자 비번
                        c.execute("SELECT * FROM users WHERE username=?", (username,))
                        user = c.fetchone()
                        if user:
                            st.session_state.logged_in = True
                            st.session_state.username = username
                            st.session_state.role = "제작자"
                            st.success(f"{username}님, 제작자 인증 완료!")
                        else:
                            st.error("등록된 사용자가 아닙니다.")
                    elif password == "3.141592":  # 관리자 비번
                        c.execute("SELECT * FROM users WHERE username=?", (username,))
                        user = c.fetchone()
                        if user:
                            st.session_state.logged_in = True
                            st.session_state.username = username
                            st.session_state.role = "관리자"
                            st.success(f"{username}님, 관리자 인증 완료!")
                        else:
                            st.error("등록된 사용자가 아닙니다.")
                    elif password == "1.414":  # 헌재 비번
                        c.execute("SELECT * FROM users WHERE username=?", (username,))
                        user = c.fetchone()
                        if user:
                            st.session_state.logged_in = True
                            st.session_state.username = username
                            st.session_state.role = "헌재"
                            st.success(f"{username}님, 헌재 인증 완료!")
                        else:
                            st.error("등록된 사용자가 아닙니다.")
                    else:
                        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
                        user = c.fetchone()
                        if user:
                            st.session_state.logged_in = True
                            st.session_state.username = username
                            st.session_state.role = user[3] if len(user) >= 4 else "일반학생"
                            st.success(f"{username}님, 환영합니다! (역할: {st.session_state.role})")
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
                        c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)", 
                                  (new_username, new_password, "일반학생"))
                        conn.commit()
                        st.success("회원가입 성공! 이제 로그인 해주세요.")
                    except sqlite3.IntegrityError:
                        st.error("이미 존재하는 아이디입니다.")
        elif login_choice == "게스트 로그인":
            if st.button("게스트 모드로 로그인"):
                st.session_state.logged_in = True
                st.session_state.username = "게스트"
                st.session_state.role = "일반학생"
                st.success("게스트 모드로 로그인 되었습니다.")

# ---------------------------
# 사이드바 메뉴 선택 (추가 탭: 자랑하기, 퀴즈, 건의함)
# ---------------------------
st.sidebar.title("메뉴 선택")
menu = st.sidebar.radio("페이지 이동", ["홈", "채팅방", "미니 블로그", "우리 반 명단", "헌재", "자율동아리", "자랑하기", "퀴즈", "건의함"])

# ---------------------------
# 공통 헤더
# ---------------------------
with st.container():
    st.image('assets/logo.png', width=250)
    st.title("🌊 5-9 삼다수반")
    st.markdown("""#### 안녕하세요? 제작자인 양지호입니다.
왼쪽 탭에서 원하는 메뉴를 선택하세요.
(하단의 '새로고침' 버튼을 누르면 최신 내용이 반영됩니다.)""")

# ---------------------------
# 홈 페이지
# ---------------------------
if menu == "홈":
    st.header("🏠 홈")
    st.markdown("""
    **삼다수반** 웹사이트입니다.  
    이 웹사이트는 채팅방에서 대화하고, 공지 등 다양한 기능을 통해 **즐겁게 생활하는** 것을 돕습니다.
    """)
    mood = st.selectbox("📆 오늘의 기분은?", ["😄 행복해!", "😎 멋져!", "😴 피곤해...", "🥳 신나!"])
    st.write(f"오늘의 기분: {mood}")
    if st.button("새로고침"):
        st.rerun()

# ---------------------------
# 채팅방 페이지
# ---------------------------
elif menu == "채팅방":
    st.header("💬 채팅방")
    st.markdown("예 뭐.. 채팅방입니다.")
    with st.form("chat_form", clear_on_submit=True):
        nickname = st.text_input("닉네임", placeholder="닉네임")
        message = st.text_input("메시지", placeholder="내용")
        submitted = st.form_submit_button("전송")
        if submitted and nickname and message:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.chat_messages.append((nickname, message, now))
            st.success("전송 완료")
    st.markdown("### 대화 내역")
    if st.session_state.chat_messages:
        for nick, msg, timestamp in reversed(st.session_state.chat_messages):
            st.markdown(f"**[{timestamp}] {nick}**: {msg}")
    else:
        st.info("아직 대화 내용이 없습니다.")
    if st.button("새로고침"):
        st.rerun()

# ---------------------------
# 미니 블로그 페이지
# ---------------------------
elif menu == "미니 블로그":
    st.header("📘 미니 블로그")
    st.markdown("블로그 같은 미니 게시판입니다.")
    with st.form("blog_form", clear_on_submit=True):
        title = st.text_input("글 제목", placeholder="제목 입력")
        content = st.text_area("글 내용", placeholder="내용 입력")
        submitted = st.form_submit_button("게시하기")
        if submitted and title and content:
            now = datetime.now().strftime("%Y-%m-%d")
            c = conn.cursor()
            c.execute("INSERT INTO blog_posts (title, content, timestamp, username) VALUES (?,?,?,?)", 
                      (title, content, now, st.session_state.username))
            conn.commit()
            st.success("게시글 등록 완료")
    st.markdown("### 최신 게시글")
    c = conn.cursor()
    c.execute("SELECT id, title, content, timestamp, username FROM blog_posts ORDER BY id DESC")
    blog_data = c.fetchall()
    if blog_data:
        for row in blog_data:
            post_id, title, content, timestamp, author = row
            st.markdown(f"**[{post_id}] {title}** _(작성일: {timestamp}, 작성자: {author})_")
            st.write(content)
            if st.session_state.logged_in and st.session_state.role in ["제작자", "관리자", "헌재"]:
                if st.button(f"삭제 (ID {post_id})", key=f"delete_{post_id}"):
                    c.execute("DELETE FROM blog_posts WHERE id=?", (post_id,))
                    conn.commit()
                    st.success("게시글 삭제 완료")
            st.markdown("---")
    else:
        st.info("등록된 게시글이 없습니다.")
    if st.button("새로고침"):
        st.rerun()

# ---------------------------
# 우리 반 명단 페이지
# ---------------------------
elif menu == "우리 반 명단":
    st.header("👥 우리 반 명단")
    data = {
        "번호": list(range(1, 29)),
        "이름": ["김도현", "김상준", "", "", "김시연", "김윤우", "김은솔", "", "", "", "", "서민성", "송선우", "", "신희건", "안준우", "양지호", "", "", "", "", "", "", "", "", "", "", "황라윤"]
    }
    roster_df = pd.DataFrame(data)
    st.table(roster_df)
    if st.button("새로고침"):
        st.rerun()

# ---------------------------
# 헌재 페이지 (의뢰 및 잠금채팅) 
# ---------------------------
elif menu == "헌재":
    st.header("⚖️ 헌재")
    st.markdown("""
    **삼다수 헌재**는 판결이나 의뢰를 통해 공정한 결정을 내리는 헌법재판소의 역할을 합니다.
    
    ### 재판관 소개
    1. **송선우** | *첫 재판 재판관 및 Founder*
    2. **김상준** | *첫 재판 재판관 및 Founder*
    3. **장태민** | *피고측 검사*
    4. **안준우**
    5. **양지호** | *피고인*
    
    ### 용어 설명
    - **인용:** 청구인의 주장을 채택하는 것.
    - **기각:** 청구인을 기각하는 것.
    - **각하:** 청구를 부적절하여 처리 거부하는 것.
    
    ### 결정 방식
    의뢰에 대한 판결은 다수결 또는 합의로 진행되며, 상태는 '처리 안됨', '처리 중', '인용', '기각', '각하' 중 하나로 설정됩니다.
    """)
    st.markdown("<small>※ 의뢰 제출 가능 시간: 월~금 1교시 쉬는시간부터 점심시간까지</small>", unsafe_allow_html=True)
    st.markdown("---")
    c = conn.cursor()
    # 의뢰 제출 – 권한: 제작자/관리자/헌재를 제외한 나머지는 본인 의뢰만 볼 수 있음
    if st.session_state.role not in ["제작자", "관리자", "헌재"]:
        st.subheader("본인 의뢰 제출 (타인의 의뢰는 볼 수 없음)")
        with st.form("petition_form", clear_on_submit=True):
            pet_title = st.text_input("의뢰 제목", placeholder="제목 입력")
            pet_content = st.text_area("의뢰 내용", placeholder="내용 입력")
            submitted_pet = st.form_submit_button("의뢰 제출")
            if submitted_pet and pet_title and pet_content:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("INSERT INTO petitions (title, content, timestamp, username) VALUES (?,?,?,?)",
                          (pet_title, pet_content, now, st.session_state.username))
                conn.commit()
                st.success("의뢰가 제출되었습니다!")
    else:
        st.subheader("전체 의뢰 보기 (제작자/관리자/헌재 전용)")
    # 의뢰 목록 표시 – 접근: 제작자/관리자/헌재는 전체, 그 외는 본인 의뢰만
    c.execute("SELECT id, title, content, timestamp, username, status FROM petitions ORDER BY id DESC")
    petitions = c.fetchall()
    if petitions:
        for pet in petitions:
            pet_id, pet_title, pet_content, pet_timestamp, pet_username, pet_status = pet
            if st.session_state.role in ["제작자", "관리자", "헌재"] or (pet_username == st.session_state.username):
                st.markdown(f"**[{pet_id}] {pet_title}** _(작성일: {pet_timestamp}, 작성자: {pet_username}, 상태: {pet_status})_")
                st.write(pet_content)
                # 잠금 채팅방: 제작자/관리자/헌재 또는 해당 의뢰 제출자만 접근 가능
                with st.expander("의뢰 채팅방"):
                    with st.form(f"petition_chat_form_{pet_id}", clear_on_submit=True):
                        pet_chat = st.text_input("메시지 입력", placeholder="의뢰 채팅 내용")
                        submitted_chat = st.form_submit_button("전송")
                        if submitted_chat and pet_chat:
                            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            c.execute("INSERT INTO petition_chats (petition_id, username, message, timestamp) VALUES (?,?,?,?)",
                                      (pet_id, st.session_state.username, pet_chat, now))
                            conn.commit()
                            st.success("의뢰 채팅 메시지 전송 완료")
                    c.execute("SELECT username, message, timestamp FROM petition_chats WHERE petition_id=? ORDER BY id DESC", (pet_id,))
                    pet_chats = c.fetchall()
                    if pet_chats:
                        for chat_username, chat_msg, chat_time in reversed(pet_chats):
                            st.markdown(f"**[{chat_time}] {chat_username}**: {chat_msg}")
                    else:
                        st.info("의뢰 채팅 메시지가 없습니다.")
                # 관리자는 의뢰 상태 업데이트 및 삭제 가능
                if st.session_state.role in ["제작자", "관리자", "헌재"]:
                    col1, col2 = st.columns(2)
                    with col1:
                        new_status = st.selectbox(f"상태 변경 (ID {pet_id})", 
                                                  ['처리 안됨', '처리 중', '인용', '기각', '각하'],
                                                  index=['처리 안됨', '처리 중', '인용', '기각', '각하'].index(pet_status),
                                                  key=f"status_{pet_id}")
                    with col2:
                        if st.button(f"상태 업데이트 (ID {pet_id})", key=f"update_{pet_id}"):
                            c.execute("UPDATE petitions SET status=? WHERE id=?", (new_status, pet_id))
                            conn.commit()
                            st.success("상태 업데이트 완료")
                    if st.button(f"의뢰 삭제 (ID {pet_id})", key=f"delete_pet_{pet_id}"):
                        c.execute("DELETE FROM petitions WHERE id=?", (pet_id,))
                        conn.commit()
                        st.success("의뢰 삭제 완료")
                st.markdown("---")
    else:
        st.info("등록된 의뢰가 없습니다.")
    if st.button("새로고침"):
        st.rerun()

# ---------------------------
# 자랑하기 페이지 (공개, 댓글 포함)
# ---------------------------
elif menu == "자랑하기":
    st.header("🎉 자랑하기")
    st.markdown("자랑할 내용을 작성하세요. 이미지 URL 입력 시 이미지도 표시됩니다.")
    c = conn.cursor()
    with st.form("proud_form", clear_on_submit=True):
        proud_title = st.text_input("제목", placeholder="제목 입력")
        proud_desc = st.text_area("설명", placeholder="설명 입력")
        proud_image = st.text_input("이미지 URL (선택)", placeholder="이미지 URL 입력")
        submitted_proud = st.form_submit_button("자랑 등록")
        if submitted_proud and proud_title and proud_desc:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO proud_posts (title, description, image_url, timestamp, username) VALUES (?,?,?,?,?)",
                      (proud_title, proud_desc, proud_image, now, st.session_state.username))
            conn.commit()
            st.success("자랑글 등록 완료")
    st.markdown("### 최신 자랑글")
    c.execute("SELECT id, title, description, image_url, timestamp, username FROM proud_posts ORDER BY id DESC")
    proud_data = c.fetchall()
    if proud_data:
        for post in proud_data:
            post_id, title, desc, image_url, timestamp, author = post
            st.markdown(f"**[{post_id}] {title}** _(작성일: {timestamp}, 작성자: {author})_")
            st.write(desc)
            if image_url:
                st.image(image_url)
            # 댓글 입력
            with st.expander("댓글 달기"):
                with st.form(f"proud_comment_form_{post_id}", clear_on_submit=True):
                    comment = st.text_area("댓글 입력", placeholder="댓글 입력")
                    submitted_comment = st.form_submit_button("댓글 등록")
                    if submitted_comment and comment:
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        c.execute("INSERT INTO proud_comments (post_id, username, comment, timestamp) VALUES (?,?,?,?)",
                                  (post_id, st.session_state.username, comment, now))
                        conn.commit()
                        st.success("댓글 등록 완료")
            # 댓글 출력
            c.execute("SELECT username, comment, timestamp FROM proud_comments WHERE post_id=? ORDER BY id DESC", (post_id,))
            comments = c.fetchall()
            if comments:
                st.markdown("**댓글:**")
                for comm in comments:
                    comm_username, comm_text, comm_time = comm
                    st.markdown(f"- **[{comm_time}] {comm_username}**: {comm_text}")
            st.markdown("---")
    else:
        st.info("등록된 자랑글이 없습니다.")
    if st.button("새로고침"):
        st.rerun()

# ---------------------------
# 퀴즈 페이지 (간단 구현, 로그인 필수)
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
                c.execute("INSERT INTO quizzes (title, description, created_by, timestamp) VALUES (?,?,?,?)",
                          (quiz_title, quiz_desc, st.session_state.username, now))
                conn.commit()
                st.success("퀴즈 등록 완료")
        st.markdown("### 등록된 퀴즈 목록")
        c.execute("SELECT id, title, description, created_by, timestamp FROM quizzes ORDER BY id DESC")
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
# 건의함 페이지
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
            c.execute("INSERT INTO suggestions (content, username, timestamp) VALUES (?,?,?)",
                      (suggestion_content, st.session_state.username, now))
            conn.commit()
            st.success("건의 제출 완료")
    st.markdown("### 최신 건의 목록")
    c.execute("SELECT id, content, username, timestamp FROM suggestions ORDER BY id DESC")
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
# 자율동아리 페이지
# ---------------------------
elif menu == "자율동아리":
    st.header("🎨 자율동아리")
    st.markdown("동아리 리스트 및 관련 기능입니다.")
    c = conn.cursor()
    if st.session_state.logged_in and st.session_state.role in ["제작자", "관리자", "헌재"]:
        with st.form("club_form", clear_on_submit=True):
            club_name = st.text_input("동아리명", placeholder="동아리 이름")
            description = st.text_area("동아리 설명", placeholder="설명 입력")
            submitted = st.form_submit_button("동아리 추가")
            if submitted and club_name and description:
                c.execute("INSERT INTO clubs (club_name, description) VALUES (?,?)", (club_name, description))
                conn.commit()
                st.success("동아리 추가 완료")
    c.execute("SELECT id, club_name, description FROM clubs ORDER BY id ASC")
    clubs_data = c.fetchall()
    if clubs_data:
        for row in clubs_data:
            cid, club_name, description = row
            st.markdown(f"### {club_name}")
            st.write(description)
            if st.session_state.logged_in and st.session_state.username != "게스트":
                c.execute("SELECT * FROM club_members WHERE club_id=? AND username=?", (cid, st.session_state.username))
                is_member = c.fetchone() is not None
                if not is_member:
                    if st.button(f"가입하기 ({club_name})", key=f"join_club_{cid}"):
                        c.execute("INSERT OR IGNORE INTO club_members (club_id, username) VALUES (?,?)", (cid, st.session_state.username))
                        conn.commit()
                        st.success(f"{club_name} 동아리에 가입했습니다!")
                else:
                    if st.button(f"탈퇴하기 ({club_name})", key=f"leave_club_{cid}"):
                        c.execute("DELETE FROM club_members WHERE club_id=? AND username=?", (cid, st.session_state.username))
                        conn.commit()
                        st.success(f"{club_name} 동아리에서 탈퇴했습니다!")
            else:
                st.info("동아리 가입/탈퇴는 로그인 필수입니다.")
            c.execute("SELECT username FROM club_members WHERE club_id=?", (cid,))
            members = c.fetchall()
            if members:
                member_list = ", ".join([m[0] for m in members])
                st.markdown(f"**멤버:** {member_list}")
            else:
                st.markdown("**멤버:** 없음")
            # 동아리 채팅방 (잠긴방)
            if st.button("채팅방 새로고침", key=f"refresh_chat_{cid}"):
                st.rerun()
            with st.expander("동아리 채팅방"):
                st.markdown("동아리 채팅 메시지")
                with st.form(f"club_chat_form_{cid}", clear_on_submit=True):
                    club_message = st.text_input("메시지 입력", placeholder="내용 입력")
                    submitted_chat = st.form_submit_button("전송")
                    if submitted_chat and club_message:
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        c.execute("INSERT INTO club_chats (club_id, username, message, timestamp) VALUES (?,?,?,?)",
                                  (cid, st.session_state.username, club_message, now))
                        conn.commit()
                        st.success("채팅 메시지 전송 완료")
                c.execute("SELECT username, message, timestamp FROM club_chats WHERE club_id=? ORDER BY id DESC", (cid,))
                club_chats = c.fetchall()
                if club_chats:
                    for chat_username, chat_msg, chat_time in reversed(club_chats):
                        st.markdown(f"**[{chat_time}] {chat_username}**: {chat_msg}")
                else:
                    st.info("채팅 메시지가 없습니다.")
            st.markdown("---")
    else:
        st.info("등록된 동아리가 없습니다.")
    if st.button("새로고침"):
        st.rerun()

# ---------------------------
# 하단 제작자 표시
# ---------------------------
st.markdown("***-Made By #17 양지호-***")
