import streamlit as st
import psycopg2
from libs.db import get_conn

def render_login_sidebar():
    conn = get_conn()
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username  = "게스트"
        st.session_state.role      = "일반학생"

    with st.sidebar.expander("로그인 / 회원가입"):
        if st.session_state.logged_in:
            st.write(f"현재 **{st.session_state.username}** ({st.session_state.role})님 로그인 상태입니다.")
            if st.button("로그아웃"):
                st.session_state.logged_in = False
                st.session_state.username  = "게스트"
                st.session_state.role      = "일반학생"
                st.rerun()
        else:
            choice = st.radio("옵션 선택", ["로그인","회원가입","게스트 로그인"], key="login_choice")
            if choice == "로그인":
                with st.form("login_form", clear_on_submit=True):
                    user = st.text_input("아이디")
                    pwd  = st.text_input("비밀번호", type="password")
                    if st.form_submit_button("로그인"):
                        cur = conn.cursor()
                        # special passwords for roles
                        if pwd in ("sqrtof4","3.141592"):
                            cur.execute("SELECT 1 FROM users WHERE username=%s", (user,))
                            if cur.fetchone():
                                st.session_state.logged_in = True
                                st.session_state.username  = user
                                st.session_state.role      = "제작자" if pwd=="sqrtof4" else "관리자"
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
                                st.session_state.username  = row[0]
                                st.session_state.role      = row[1]
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
                    st.session_state.username  = "게스트"
                    st.session_state.role      = "일반학생"
                    st.rerun()
