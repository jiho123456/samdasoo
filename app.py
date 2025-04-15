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
    # 기존 사용자 테이블 업데이트: role 컬럼 추가 (default '일반학생')
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
    # 헌재(의뢰) 테이블 – 각 의뢰(청구)
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
    # 헌재 의뢰별 채팅 (잠금방)
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
# CSS: 사이드바 토글 버튼 라벨 (대안: 사이드바 상단에 이미 '메뉴 선택' 표시)
# ---------------------------
st.markdown("""
<style>
/* 사이드바 상단에 라벨을 더 크게 표시 */
.css-1d391kg edgvbvh3 { display: none; }
</style>
""", unsafe_allow_html=True)

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
                    # 특수 비번에 따른 역할 할당
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
                            # 로컬 DB에 저장된 역할 사용. 없으면 기본 '일반학생'
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
                        # 회원가입 시 기본 role은 '일반학생'
                        c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)", (new_username, new_password, "일반학생"))
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
# 사이드바 메뉴 선택 (새로운 탭 추가: 자랑하기, 퀴즈, 건의함)
# ---------------------------
st.sidebar.title("메뉴 선택")
menu = st.sidebar.radio("페이지 이동", ["홈", "채팅방", "미니 블로그", "우리 반 명단", "헌재", "자율동아리", "자랑하기", "퀴즈", "건의함"])

# ---------------------------
# 공통 헤더: 로고와 타이틀
# ---------------------------
with st.container():
    st.image('assets/logo.png', width=250)
    st.title("🌊 5-9 삼다수반")
    st.markdown("""#### 안녕하세요? 제작자인 양지호입니다.  
왼쪽 탭에서 원하는 메뉴를 선택하세요.  
(새로고침 버튼을 누르면 최신 내용이 반영됩니다.)""")

# ---------------------------
# 헌재 - 의뢰(잠금방) 페이지 (권한에 따라 노출)
# ---------------------------
if menu == "헌재":
    st.header("⚖️ 헌재")
    st.markdown("""
    **삼다수 헌재**는 판결이나 의뢰를 부탁할 시, 공정한 결정을 내리는 **헌법재판소** 역할을 합니다.
    
    ### 재판관 소개
    1. **송선우** | *첫 재판의 재판관 및 Founder*
    2. **김상준** | *첫 재판의 재판관 및 Founder*
    3. **장태민** | *첫 재판의 피고측 검사*
    4. **안준우**
    5. **양지호** | *첫 재판의 피고인*
    
    ### 용어 설명
    - **인용:** 청구인의 주장을 받아들이는 것.
    - **기각:** 인용의 반대.
    - **각하:** 청구가 부적절하여 판결을 거부하는 것.
    
    ### 결정 방식
    헌재 의뢰에 대한 결정은 다수결 혹은 합의로 이루어지며, 인용/각하/기각/처리 중 상태로 관리됩니다.
    ###### (인용과 각하는 반드시 3명 이상 찬성 시 이행)
    """)
    st.markdown("<small>※ 헌재 의뢰 가능 시간: 월~금 1교시 쉬는시간부터 점심시간까지</small>", unsafe_allow_html=True)
    st.markdown("---")
    
    c = conn.cursor()
    # 의뢰(청구) 제출 – 일반 사용자(또는 반장/부반장 포함)라면 본인이 제출한 의뢰만 볼 수 있음.
    if st.session_state.role not in ["제작자", "관리자", "헌재"]:
        st.subheader("헨재 의뢰 제출 (본인 의뢰만 열람 가능)")
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
        st.subheader("모든 의뢰 보기 (관리자/헌재 전용)")
    # 모든 의뢰 목록 표시 – 접근 제어: 제작자, 관리자, 헌재는 전체, 그 외는 본인 의뢰만
    c.execute("SELECT id, title, content, timestamp, username, status FROM petitions ORDER BY id DESC")
    petitions = c.fetchall()
    if petitions:
        for pet in petitions:
            pet_id, pet_title, pet_content, pet_timestamp, pet_username, pet_status = pet
            # 접근 제어: 현재 사용자가 제작자/관리자/헌재거나 본인이 제출한 의뢰인 경우에만 표시
            if st.session_state.role in ["제작자", "관리자", "헌재"] or (pet_username == st.session_state.username):
                st.markdown(f"**[{pet_id}] {pet_title}**  _(작성일: {pet_timestamp}, 작성자: {pet_username}, 상태: {pet_status})_")
                st.write(pet_content)
                # 헌재 의뢰별 잠긴 채팅방 – 접근: 위와 동일하게 제작자/관리자/헌재 또는 의뢰자만
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
                # 관리자인 경우 의뢰 상태 업데이트 및 삭제 기능 제공
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
# 자랑하기 페이지 (공개)
# ---------------------------
elif menu == "자랑하기":
    st.header("🎉 자랑하기")
    st.markdown("자랑할 내용을 작성하세요. 이미지 URL을 입력하면 이미지도 표시됩니다.")
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
            st.success("자랑글이 등록되었습니다!")
    st.markdown("### 최신 자랑글")
    c.execute("SELECT id, title, description, image_url, timestamp, username FROM proud_posts ORDER BY id DESC")
    proud_data = c.fetchall()
    if proud_data:
        for post in proud_data:
            post_id, title, desc, image_url, timestamp, author = post
            st.markdown(f"**[{post_id}] {title}**  _(작성일: {timestamp}, 작성자: {author})_")
            st.write(desc)
            if image_url:
                st.image(image_url)
            # 댓글 기능
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
        st.subheader("퀴즈 생성 (자신의 퀴즈를 등록)")
        with st.form("quiz_form", clear_on_submit=True):
            quiz_title = st.text_input("퀴즈 제목", placeholder="제목 입력")
            quiz_desc = st.text_area("퀴즈 설명", placeholder="설명 입력")
            submitted_quiz = st.form_submit_button("퀴즈 등록")
            if submitted_quiz and quiz_title and quiz_desc:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("INSERT INTO quizzes (title, description, created_by, timestamp) VALUES (?,?,?,?)",
                          (quiz_title, quiz_desc, st.session_state.username, now))
                conn.commit()
                st.success("퀴즈가 등록되었습니다!")
        st.markdown("### 등록된 퀴즈 목록")
        c.execute("SELECT id, title, description, created_by, timestamp FROM quizzes ORDER BY id DESC")
        quizzes = c.fetchall()
        if quizzes:
            for quiz in quizzes:
                quiz_id, title, desc, creator, ts = quiz
                st.markdown(f"**[{quiz_id}] {title}**  _(작성자: {creator}, {ts})_")
                st.write(desc)
                # 퀴즈 풀기(더 자세한 문제 출제 로직은 생략)
                if st.button(f"퀴즈 풀기 (ID {quiz_id})", key=f"solve_{quiz_id}"):
                    st.info("퀴즈 풀기 기능은 차후 업데이트 예정입니다.")
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
        suggestion_content = st.text_area("건의 내용", placeholder="건의할 내용을 입력하세요")
        submitted_sugg = st.form_submit_button("건의 제출")
        if submitted_sugg and suggestion_content:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO suggestions (content, username, timestamp) VALUES (?,?,?)",
                      (suggestion_content, st.session_state.username, now))
            conn.commit()
            st.success("건의가 제출되었습니다!")
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
# 홈, 채팅방, 미니 블로그, 우리 반 명단 등 기존 페이지의 새로고침 버튼은 위에서 처리함
# ---------------------------
st.markdown("***-Made By #17 양지호-***")
