import streamlit as st
import psycopg2
import psycopg2.errors
from libs.db import get_conn
import re

def namecheck(name):
    if not isinstance(name, str):
        return False
    name = name.strip()
    if not (2 <= len(name) <= 50):
        return False

    # Korean name: all Hangul
    if all('\uAC00' <= ch <= '\uD7A3' for ch in name):
        return True

    # English name: allow letters, space, hyphen, apostrophe, period
    if re.fullmatch(r"[A-Za-z][A-Za-z\s\-'\.]{1,49}", name):
        return True

    return False


def render_login_sidebar():
    conn = get_conn()
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username  = "게스트"
        st.session_state.role      = "일반학생"
        st.session_state.user_id   = None

    with st.sidebar.expander("로그인 / 회원가입"):
        if st.session_state.logged_in:
            st.write(f"현재 **{st.session_state.username}** ({st.session_state.role})님 로그인 상태입니다.")
            if st.button("로그아웃"):
                st.session_state.logged_in = False
                st.session_state.username  = "게스트"
                st.session_state.role      = "일반학생"
                st.session_state.user_id   = None
                st.rerun()
        else:
            choice = st.radio("옵션 선택", ["로그인","회원가입","게스트 로그인"], key="login_choice")
            if choice == "로그인":
                with st.form("login_form", clear_on_submit=True):
                    user = st.text_input("아이디")
                    pwd  = st.text_input("비밀번호", type="password")
                    if st.form_submit_button("로그인"):
                        cur = conn.cursor()
                        # 1) 강제 탈퇴 여부 확인
                        cur.execute("SELECT reason FROM kicked_users WHERE username=%s", (user,))
                        row = cur.fetchone()
                        if row:
                            reason = row[0]
                            st.error(f"🚫 강제 탈퇴되었습니다:\n{reason}\n새 계정을 만들어주세요.")
                            return

                        # 2) 특별 비밀번호로 제작자/관리자 인증
                        if pwd in ("sqrtof4"):
                            # check user exists and get user_id
                            cur.execute("SELECT user_id FROM users WHERE username=%s", (user,))
                            id_row = cur.fetchone()
                            if id_row:
                                st.session_state.logged_in = True
                                st.session_state.username  = user
                                st.session_state.role      = "제작자"
                                st.session_state.user_id   = id_row[0]
                                st.rerun()
                            else:
                                st.error("등록된 사용자가 아닙니다.")
                        else:
                            # 3) 일반 로그인 (get user_id, username, role)
                            try:
                                cur.execute(
                                    "SELECT user_id, username, role FROM users WHERE username=%s AND password=%s",
                                    (user, pwd)
                                )
                                row2 = cur.fetchone()
                            except psycopg2.errors.UndefinedColumn:
                                # fallback for DB without password column
                                cur.execute(
                                    "SELECT user_id, username, role FROM users WHERE username=%s",
                                    (user,)
                                )
                                row2 = cur.fetchone()
                            if row2:
                                st.session_state.logged_in = True
                                st.session_state.user_id   = row2[0]
                                st.session_state.username  = row2[1]
                                st.session_state.role      = row2[2]
                                st.rerun()
                            else:
                                st.error("아이디 또는 비밀번호가 틀렸습니다.")
            elif choice == "회원가입":
                with st.form("reg_form", clear_on_submit=True):
                    nu = st.text_input("아이디", key="reg_u")
                    np = st.text_input("비밀번호", type="password", key="reg_p")
                    btn = st.form_submit_button("회원가입")
                    if btn:
                        if not namecheck(nu):
                            st.error("회원가입은 본인 이름(한글 혹은 영어)로 해주세요.")
                            st.stop()
                        try:
                            cur = conn.cursor()
                            cur.execute(
                            "INSERT INTO users(username, password, role, bio, avatar_url) "
                            "VALUES(%s, %s, '일반학생', '', '')",
                            (nu, np)
                            )
                            conn.commit()
                            st.success("회원가입 완료되었습니다. 로그인 해주세요.")
                            st.rerun()
                        except psycopg2.IntegrityError:
                            st.error("이미 존재하는 아이디입니다.")

            else:
                if st.button("게스트 로그인"):
                    st.session_state.logged_in = True
                    st.session_state.username  = "게스트"
                    st.session_state.role      = "일반학생"
                    st.session_state.user_id   = None
                    st.rerun()
