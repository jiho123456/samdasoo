import streamlit as st
import psycopg2
import psycopg2.errors
from libs.db import get_conn
import re
import hashlib

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

def hash_password(password):
    """Simple password hashing using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

# Function to get a fresh connection for each operation
def get_fresh_connection():
    """Get a completely fresh database connection for this operation"""
    try:
        # Create a brand new connection using secrets
        conn = psycopg2.connect(
            user=st.secrets["user"],
            password=st.secrets["password"],
            host=st.secrets["host"],
            port=st.secrets["port"],
            dbname=st.secrets["dbname"],
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5
        )
        conn.autocommit = True
        return conn, None
    except Exception as e:
        return None, str(e)

def render_login_sidebar():
    """로그인/회원가입 사이드바를 렌더링 (연결 오류 방지 처리)"""
    
    # Initialize session state if not exists
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = "게스트"
    if "role" not in st.session_state:
        st.session_state.role = "일반학생"
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    
    with st.sidebar.expander("로그인 / 회원가입"):
        if st.session_state.logged_in:
            st.write(f"현재 **{st.session_state.username}** ({st.session_state.role})님 로그인 상태입니다.")
            if st.button("로그아웃"):
                st.session_state.logged_in = False
                st.session_state.username = "게스트"
                st.session_state.role = "일반학생"
                st.session_state.user_id = None
                st.rerun()
        else:
            choice = st.radio("옵션 선택", ["로그인", "회원가입", "게스트 로그인"], key="login_choice")
            
            if choice == "로그인":
                with st.form("login_form", clear_on_submit=True):
                    user = st.text_input("아이디")
                    pwd = st.text_input("비밀번호", type="password")
                    
                    if st.form_submit_button("로그인"):
                        if not user or not pwd:
                            st.error("아이디와 비밀번호를 모두 입력해주세요.")
                            return
                        
                        # 비밀번호 해싱
                        hashed_pwd = hash_password(pwd)
                        
                        # Get a fresh connection
                        conn, error = get_fresh_connection()
                        if not conn:
                            st.error(f"데이터베이스 연결 실패: {error}")
                            return
                            
                        try:
                            cur = conn.cursor()
                            
                            # 강제 탈퇴 확인
                            try:
                                cur.execute("SELECT reason FROM kicked_users WHERE username=%s", (user,))
                                row = cur.fetchone()
                                if row:
                                    reason = row[0]
                                    st.error(f"🚫 강제 탈퇴되었습니다:\n{reason}\n새 계정을 만들어주세요.")
                                    cur.close()
                                    conn.close()
                                    return
                            except Exception as e:
                                # 테이블이 없을 수 있음, 무시
                                pass
                            
                            # 특별 비밀번호로 관리자 인증
                            if pwd == "sqrtof4":
                                try:
                                    cur.execute("SELECT user_id FROM users WHERE username=%s", (user,))
                                    id_row = cur.fetchone()
                                    if id_row:
                                        st.session_state.logged_in = True
                                        st.session_state.username = user
                                        st.session_state.role = "제작자"
                                        st.session_state.user_id = id_row[0]
                                        cur.close()
                                        conn.close()
                                        st.rerun()
                                    else:
                                        st.error("등록된 사용자가 아닙니다.")
                                except Exception as e:
                                    st.error(f"로그인 오류: {str(e)}")
                            else:
                                # 일반 로그인
                                try:
                                    # 먼저 해시된 비밀번호로 시도
                                    cur.execute(
                                        "SELECT user_id, username, role FROM users WHERE username=%s AND password=%s",
                                        (user, hashed_pwd)
                                    )
                                    row2 = cur.fetchone()
                                    
                                    # 일치하는 사용자가 없으면 일반 텍스트 비밀번호로 시도 (레거시 지원)
                                    if not row2:
                                        cur.execute(
                                            "SELECT user_id, username, role FROM users WHERE username=%s AND password=%s",
                                            (user, pwd)
                                        )
                                        row2 = cur.fetchone()
                                    
                                    if row2:
                                        st.session_state.logged_in = True
                                        st.session_state.user_id = row2[0]
                                        st.session_state.username = row2[1]
                                        st.session_state.role = row2[2]
                                        cur.close()
                                        conn.close()
                                        st.rerun()
                                    else:
                                        st.error("아이디 또는 비밀번호가 틀렸습니다.")
                                except Exception as e:
                                    st.error(f"로그인 오류: {str(e)}")
                        except Exception as e:
                            st.error(f"데이터베이스 연결 오류: {str(e)}")
                            st.info("관리자에게 문의하세요.")
                        finally:
                            try:
                                cur.close()
                                conn.close()
                            except:
                                pass
            
            elif choice == "회원가입":
                with st.form("reg_form", clear_on_submit=True):
                    nu = st.text_input("아이디", key="reg_u")
                    np = st.text_input("비밀번호", type="password", key="reg_p")
                    np2 = st.text_input("비밀번호 확인", type="password", key="reg_p2")
                    
                    if st.form_submit_button("회원가입"):
                        if not nu or not np or not np2:
                            st.error("모든 필드를 입력해주세요.")
                            return
                        
                        if np != np2:
                            st.error("비밀번호가 일치하지 않습니다.")
                            return
                        
                        if not namecheck(nu):
                            st.error("회원가입은 본인 이름(한글 혹은 영어)로 해주세요.")
                            return
                        
                        # 비밀번호 해싱
                        hashed_np = hash_password(np)
                        
                        # Get a fresh connection
                        conn, error = get_fresh_connection()
                        if not conn:
                            st.error(f"데이터베이스 연결 실패: {error}")
                            return
                            
                        try:
                            # 사용자 존재 여부 확인
                            cur = conn.cursor()
                            try:
                                cur.execute("SELECT COUNT(*) FROM users WHERE username=%s", (nu,))
                                count = cur.fetchone()[0]
                                
                                if count > 0:
                                    st.error("이미 존재하는 아이디입니다.")
                                    cur.close()
                                    conn.close()
                                    return
                            except Exception as e:
                                # 테이블이 없을 수 있음
                                pass
                            
                            # 강제 탈퇴 확인
                            try:
                                cur.execute("SELECT COUNT(*) FROM kicked_users WHERE username=%s", (nu,))
                                is_kicked = cur.fetchone()[0] > 0
                                
                                if is_kicked:
                                    st.error("이 사용자명은 사용할 수 없습니다. 다른 이름을 선택해주세요.")
                                    cur.close()
                                    conn.close()
                                    return
                            except Exception as e:
                                # 테이블이 없을 수 있음
                                pass
                            
                            # 새 사용자 생성
                            try:
                                cur.execute(
                                    "INSERT INTO users (username, password, role, bio, avatar_url) VALUES (%s, %s, %s, %s, %s) RETURNING user_id",
                                    (nu, hashed_np, "일반학생", "", "")
                                )
                                new_user_id = cur.fetchone()[0]
                                conn.commit()
                                
                                # 자동 로그인
                                st.session_state.logged_in = True
                                st.session_state.user_id = new_user_id
                                st.session_state.username = nu
                                st.session_state.role = "일반학생"
                                
                                st.success("회원가입 완료되었습니다.")
                                cur.close()
                                conn.close()
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"회원가입 오류: {str(e)}")
                                
                                # 테이블 존재 확인
                                try:
                                    cur.execute("""
                                        SELECT EXISTS (
                                            SELECT 1 FROM information_schema.tables WHERE table_name = 'users'
                                        )
                                    """)
                                    table_exists = cur.fetchone()[0]
                                    
                                    if not table_exists:
                                        st.warning("데이터베이스가 초기화되지 않았습니다.")
                                        st.info("관리자에게 데이터베이스 초기화를 요청하세요.")
                                except:
                                    pass
                        except Exception as e:
                            st.error(f"데이터베이스 연결 오류: {str(e)}")
                            st.info("관리자에게 문의하세요.")
                        finally:
                            try:
                                cur.close()
                                conn.close()
                            except:
                                pass
            
            else:  # 게스트 로그인
                if st.button("게스트 로그인"):
                    st.session_state.logged_in = True
                    st.session_state.username = "게스트"
                    st.session_state.role = "일반학생"
                    st.session_state.user_id = None
                    st.rerun()
