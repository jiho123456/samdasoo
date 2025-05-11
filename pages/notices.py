import streamlit as st
from libs.db import get_conn
import psycopg2

def get_fresh_connection():
    """Get a completely fresh connection for this operation"""
    try:
        # Create a fresh connection every time
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
        return conn
    except Exception as e:
        st.error(f"데이터베이스 연결 오류: {str(e)}")
        if st.button("연결 문제 해결하기"):
            st.switch_page("pages/connection_fix.py")
        return None

def render_notices():
    """Render active notices on the main page."""
    try:
        # Get a fresh connection for this operation
        conn = get_fresh_connection()
        if not conn:
            return
        
        cur = conn.cursor()
        
        try:
            # Get all active notices
            cur.execute("""
                SELECT title, content, heading_level
                FROM notices
                WHERE is_active = true
                ORDER BY created_at DESC
            """)
            notices = cur.fetchall()
            
            if notices:
                st.markdown("---")
                st.markdown("### 📢 공지사항")
                
                for notice in notices:
                    title, content, heading_level = notice
                    
                    # Apply heading level
                    heading = "#" * heading_level
                    st.markdown(f"{heading} {title}")
                    st.markdown(content)
                    st.markdown("---")
        
        except Exception as e:
            st.error(f"공지사항을 불러오는 중 오류가 발생했습니다: {str(e)}")
            # Show repair link
            if st.button("데이터베이스 연결 문제 해결"):
                st.switch_page("pages/connection_fix.py")
        
        finally:
            # Always close cursor and connection
            try:
                cur.close()
            except:
                pass
            try:
                conn.close()
            except:
                pass
    
    except Exception as e:
        st.error(f"공지사항을 불러오는 중 오류가 발생했습니다: {str(e)}")
        # Show repair link
        if st.button("데이터베이스 연결 문제 해결"):
            st.switch_page("pages/connection_fix.py") 