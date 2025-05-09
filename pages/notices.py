import streamlit as st
from libs.db import get_conn

def render_notices():
    """Render active notices on the main page."""
    conn = get_conn()
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
        st.error(f"공지를 불러오는 중 오류가 발생했습니다: {str(e)}")
    
    finally:
        cur.close()
        conn.close() 