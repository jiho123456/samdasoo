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

def render_login_sidebar():
    """Render the login/signup sidebar with proper connection handling"""
    
    st.sidebar.title("🔑 Login / Sign Up")
    
    # Choice between login and signup with radio buttons
    login_choice = st.sidebar.radio(
        "Choose an option",
        options=["Login", "Sign Up"],
        key="login_choice"
    )
    
    if login_choice == "Login":
        render_login_form()
    else:
        render_signup_form()
    
    # Show logout button if logged in
    if st.session_state.get('logged_in'):
        st.sidebar.markdown("---")
        st.sidebar.write(f"Logged in as: **{st.session_state.get('username')}**")
        st.sidebar.write(f"Role: **{st.session_state.get('role')}**")
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.role = None
            st.rerun()


def render_login_form():
    """Render the login form with proper connection handling"""
    
    with st.sidebar.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if not username or not password:
                st.sidebar.error("Please enter both username and password.")
                return
                
            # Hash the password
            hashed_password = hash_password(password)
            
            try:
                # Get a fresh connection for this operation
                conn = get_conn()
                cur = conn.cursor()
                
                # Check if user exists and password matches
                cur.execute(
                    "SELECT user_id, role FROM users WHERE username = %s AND password = %s",
                    (username, hashed_password)
                )
                user = cur.fetchone()
                
                # Close cursor but not connection (it's cached)
                cur.close()
                
                if user:
                    user_id, role = user
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.session_state.username = username
                    st.session_state.role = role
                    st.sidebar.success(f"Welcome, {username}!")
                    st.rerun()
                else:
                    st.sidebar.error("Invalid username or password.")
            except Exception as e:
                st.sidebar.error(f"Login error: {str(e)}")
                st.sidebar.warning("Please try again or contact the administrator.")


def render_signup_form():
    """Render the signup form with proper connection handling"""
    
    with st.sidebar.form("signup_form"):
        new_username = st.text_input("Choose Username")
        new_password = st.text_input("Choose Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        role = st.selectbox("Role", ["student", "teacher"])
        submitted = st.form_submit_button("Sign Up")
        
        if submitted:
            if not new_username or not new_password or not confirm_password:
                st.sidebar.error("Please fill in all fields.")
                return
                
            if new_password != confirm_password:
                st.sidebar.error("Passwords do not match.")
                return
                
            # Hash the password
            hashed_password = hash_password(new_password)
            
            try:
                # Get a fresh connection for user check
                conn = get_conn()
                cur = conn.cursor()
                
                # First check if username already exists
                cur.execute("SELECT COUNT(*) FROM users WHERE username = %s", (new_username,))
                count = cur.fetchone()[0]
                cur.close()
                
                if count > 0:
                    st.sidebar.error("Username already exists. Please choose another.")
                    return
                
                # Check if username is in kicked_users list
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM kicked_users WHERE username = %s", (new_username,))
                is_kicked = cur.fetchone()[0] > 0
                cur.close()
                
                if is_kicked:
                    st.sidebar.error("This username has been banned. Please choose another.")
                    return
                
                # Create the new user
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO users (username, password, role) VALUES (%s, %s, %s) RETURNING user_id",
                    (new_username, hashed_password, role)
                )
                new_user_id = cur.fetchone()[0]
                conn.commit()
                cur.close()
                
                # Log the user in
                st.session_state.logged_in = True
                st.session_state.user_id = new_user_id
                st.session_state.username = new_username
                st.session_state.role = role
                
                st.sidebar.success("Account created successfully!")
                st.rerun()
                
            except Exception as e:
                st.sidebar.error(f"Sign-up error: {str(e)}")
                
                # Check if users table exists, and try to create it if it doesn't
                try:
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.tables WHERE table_name = 'users'
                        )
                    """)
                    table_exists = cur.fetchone()[0]
                    
                    if not table_exists:
                        st.sidebar.warning("Database tables may not be initialized yet.")
                        st.sidebar.info("Please ask an administrator to initialize the database.")
                    
                    cur.close()
                except:
                    st.sidebar.warning("Unable to check if users table exists. Database may not be initialized.")
