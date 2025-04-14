import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd

# ---------------------------
# 데이터베이스 초기화 함수
# ---------------------------
def init_db():
    conn = sqlite3.connect('samdasu.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            is_admin INTEGER DEFAULT 0
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
    # 동아리 가입 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS club_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            club_id INTEGER,
            username TEXT,
            UNIQUE(club_id, username)
        )
    ''')
    # 동아리 별 채팅 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS club_chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            club_id INTEGER,
            username TEXT,
            message TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    return conn

conn = init_db()

# ---------------------------
# 토글 버튼에 레이블 붙이기
# ---------------------------

st.markdown("""
<style>
.sidebar-toggle-hint {
    position: fixed;
    top: 10px;
    left: 10px;
    background-color: #f0f2f6;
    padding: 5px 10px;
    border-radius: 5px;
    z-index: 1000;
    font-size: 14px;
    color: #333;
}
</style>
<div class="sidebar-toggle-hint">← 메뉴 보기</div>
""", unsafe_allow_html=True)

# ---------------------------
# 세션 상태 초기화 (로그인/채팅)
# ---------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = "게스트"
    st.session_state.is_admin = False

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []  # 각 채팅 메시지는 (닉네임, 메시지, 타임스탬프) 튜플

# ---------------------------
# 사이드바: 로그인 / 회원가입 / 게스트 로그인
# ---------------------------
with st.sidebar.expander("로그인 / 회원가입"):
    if st.session_state.logged_in:
        st.write(f"현재 **{st.session_state.username}**님 로그인 상태입니다.")
        st.info(f"안녕하세요, {st.session_state.username}님! 반가워요.")
        if st.button("로그아웃"):
            st.session_state.logged_in = False
            st.session_state.username = "게스트"
            st.session_state.is_admin = False
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
                    # 관리자 인증: 비밀번호가 "3.141592"이면 관리자 인증 시도
                    if password == "3.141592":
                        c.execute("SELECT * FROM users WHERE username=?", (username,))
                        user = c.fetchone()
                        if user:
                            st.session_state.logged_in = True
                            st.session_state.username = username
                            st.session_state.is_admin = True
                            st.success(f"{username}님, 관리자 인증 완료!")
                        else:
                            st.error("등록된 사용자가 아닙니다.")
                    else:
                        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
                        user = c.fetchone()
                        if user:
                            st.session_state.logged_in = True
                            st.session_state.username = username
                            st.session_state.is_admin = bool(user[3])
                            st.success(f"{username}님, 환영합니다!")
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
                        c.execute("INSERT INTO users (username, password) VALUES (?,?)", (new_username, new_password))
                        conn.commit()
                        st.success("회원가입 성공! 이제 로그인 해주세요.")
                    except sqlite3.IntegrityError:
                        st.error("이미 존재하는 아이디입니다.")
        elif login_choice == "게스트 로그인":
            if st.button("게스트 모드로 로그인"):
                st.session_state.logged_in = True
                st.session_state.username = "게스트"
                st.session_state.is_admin = False
                st.success("게스트 모드로 로그인 되었습니다.")

# ---------------------------
# 사이드바 메뉴 선택
# ---------------------------
st.sidebar.title("메뉴 선택")
menu = st.sidebar.radio("페이지 이동", ["홈", "채팅방", "미니 블로그", "우리 반 명단", "헌재", "자율동아리"])

# ---------------------------
# 공통 헤더: 로고와 타이틀
# ---------------------------
with st.container():
    st.image('assets/logo.png', width=250)
    st.title("🌊 5-9 삼다수반")
    st.markdown("#### 안녕하세요? 제작자인 양지호입니다. 왼쪽 탭에서 원하는 메뉴를 선택하세요.")

# ---------------------------
# 각 페이지별 기능 구현
# ---------------------------
if menu == "홈":
    st.header("🏠 홈")
    st.markdown("""
    **삼다수반** 웹사이트입니다.  
    이 웹사이트는 채팅방에서 대화하고, 공지? 같은 것도 올리며 **즐겁게 생활하는** 것을
    돕는 것이 목적입니다.
    """)
    mood = st.selectbox("📆 오늘의 기분은?", ["😄 행복해!", "😎 멋져!", "😴 피곤해...", "🥳 신나!"])
    st.write(f"오늘의 기분: {mood}")
    if st.button("새로고침"):
        st.rerun()

elif menu == "채팅방":
    st.header("💬 채팅방")
    st.markdown("예 뭐.. 채팅방입니다")
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
        st.info("아직 없네여")
    if st.button("새로고침"):
        st.rerun()

elif menu == "미니 블로그":
    st.header("📘 미니 블로그")
    st.markdown("걍 뭐 블로그인듯 블로그아닌 블로그같은 미니블로그입니다")
    with st.form("blog_form", clear_on_submit=True):
        title = st.text_input("글 제목", placeholder="제목 입력")
        content = st.text_area("글 내용", placeholder="내용을 입력하세요")
        submitted = st.form_submit_button("게시하기")
        if submitted and title and content:
            now = datetime.now().strftime("%Y-%m-%d")
            username = st.session_state.username
            c = conn.cursor()
            c.execute("INSERT INTO blog_posts (title, content, timestamp, username) VALUES (?,?,?,?)", 
                      (title, content, now, username))
            conn.commit()
            st.success("등록됨ㅋ")
    st.markdown("### 최신 글")
    c = conn.cursor()
    c.execute("SELECT id, title, content, timestamp, username FROM blog_posts ORDER BY id DESC")
    blog_data = c.fetchall()
    if blog_data:
        for row in blog_data:
            post_id, title, content, timestamp, author = row
            st.markdown(f"**{title}**  _(작성일: {timestamp}, 작성자: {author})_")
            st.write(content)
            if st.session_state.logged_in and st.session_state.is_admin:
                if st.button(f"삭제 (ID {post_id})", key=f"delete_{post_id}"):
                    c.execute("DELETE FROM blog_posts WHERE id=?", (post_id,))
                    conn.commit()
                    st.success("삭제됨ㅋ 새로고침 필요")
            st.markdown("---")
    else:
        st.info("글 없음 o^0^o")
    if st.button("새로고침"):
        st.rerun()

elif menu == "우리 반 명단":
    st.header("👥 우리 반 명단")
    st.markdown("명단임")
    data = {
        "번호": list(range(1, 29)),
        "이름": ["김도현", "김상준", "", "", "김시연", "김윤우", "김은솔", "", "", "", "", "서민성", "송선우", "", "신희건", "안준우", "양지호", "", "", "", "", "", "", "", "", "", "", "황라윤"]
    }
    roster_df = pd.DataFrame(data)
    st.table(roster_df)
    if st.button("새로고침"):
        st.rerun()

elif menu == "헌재":
    st.header("⚖️ 헌재")
    st.markdown("""
    **삼다수 헌재**는 판결을 부탁할 시 공정한 결정을 내리는 **헌법재판소** 역할을 합니다.
    
    ### 재판관 소개
    1. **송선우** | *첫 재판의 재판관 및 Founder*
    2. **김상준** | *첫 재판의 재판관 및 Founder*
    3. **장태민** | *첫 재판의 피고측 검사*
    4. **안준우**
    5. **양지호** | *첫 재판의 피고인*
    
    ### 용어 설명
    - **인용:** 청구인의 주장을 받아들이는 것.
    - **기각:** 인용의 반대. 패소 느낌.
    - **각하:** 청구가 잘못되어 판결을 거부하는 것.
    
    ### 결정 방식
    헌재에서의 결정은 다수결 혹은 합의 과정을 통해 이루어지며, 각 재판관의 의견을 종합하여 최종 판결이 내려집니다.
    ###### 인용과 각하는 반드시 3명 이상 찬성 시 이행,
    ###### 인용이 아니라면 기각.
    
    ---
    
    **[삼다수 헌재]** 의 이름 아래, 우리 반의 정의와 공정함을 지켜냅니다.
    편파판정 **절대금지**.
    """)
    if st.button("새로고침"):
        st.rerun()

elif menu == "자율동아리":
    st.header("🎨 자율동아리")
    st.markdown("동아리 리스트입니다 왜여")
    c = conn.cursor()
    if st.session_state.logged_in and st.session_state.is_admin:
        with st.form("club_form", clear_on_submit=True):
            club_name = st.text_input("동아리명", placeholder="동아리 이름")
            description = st.text_area("동아리 설명", placeholder="설명을 입력하세요")
            submitted = st.form_submit_button("추가하기")
            if submitted and club_name and description:
                c.execute("INSERT INTO clubs (club_name, description) VALUES (?,?)", (club_name, description))
                conn.commit()
                st.success("동아리 추가됨!")
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
                st.info("동아리 가입/탈퇴 기능은 로그인 필수입니다.")
            
            c.execute("SELECT username FROM club_members WHERE club_id=?", (cid,))
            members = c.fetchall()
            if members:
                member_list = ", ".join([m[0] for m in members])
                st.markdown(f"**멤버:** {member_list}")
            else:
                st.markdown("**멤버:** 없음")
            
            # 동아리 채팅방 (Expander 사용) - 새로고침 버튼으로 실시간 업데이트를 구현
            if st.button("채팅방 새로고침", key=f"refresh_chat_{cid}"):
                st.rerun()
            with st.expander("동아리 채팅방"):
                st.markdown("동아리 채팅 메시지")
                with st.form(f"club_chat_form_{cid}", clear_on_submit=True):
                    club_message = st.text_input("메시지 입력", placeholder="내용 입력")
                    submitted_chat = st.form_submit_button("전송")
                    if submitted_chat and club_message:
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        username = st.session_state.username
                        c.execute("INSERT INTO club_chats (club_id, username, message, timestamp) VALUES (?,?,?,?)",
                                  (cid, username, club_message, now))
                        conn.commit()
                        st.success("메시지 전송 완료")
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

st.markdown("***-Made By #17 양지호-***")
