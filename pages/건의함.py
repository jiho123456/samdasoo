import streamlit as st
from libs.db import get_conn
import pandas as pd
from datetime import datetime

# Check if user is logged in
if not st.session_state.get('logged_in'):
    st.warning("로그인이 필요합니다.")
    st.stop()

st.title("📝 건의함")

# Form for submitting suggestions
st.subheader("건의사항 작성")
with st.form("suggestion_form"):
    content = st.text_area("건의 내용", height=150)
    submit = st.form_submit_button("제출")
    
    if submit and content:
        try:
            # Get a fresh connection for this operation
            conn = get_conn()
            cur = conn.cursor()
            
            # Insert the suggestion
            cur.execute(
                "INSERT INTO suggestions (content, username, user_id) VALUES (%s, %s, %s)",
                (content, st.session_state.get('username'), st.session_state.get('user_id'))
            )
            
            # Commit and close cursor (but don't close connection as it's cached)
            conn.commit()
            cur.close()
            
            st.success("건의사항이 제출되었습니다!")
            st.rerun()
        except Exception as e:
            st.error(f"건의사항 제출 중 오류가 발생했습니다: {str(e)}")

st.markdown("### 최신 건의")
try:
    # Get a fresh connection for this operation
    conn = get_conn()
    cur = conn.cursor()
    
    # Get suggestions with proper error handling
    try:
        cur.execute(
            "SELECT id, content, username, timestamp FROM suggestions ORDER BY id DESC"
        )
        suggestions = cur.fetchall()
    except Exception as e:
        st.error(f"건의사항을 불러오는 중 오류가 발생했습니다: {str(e)}")
        # Check if suggestions table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables WHERE table_name = 'suggestions'
            )
        """)
        table_exists = cur.fetchone()[0]
        
        if not table_exists:
            # Create suggestions table if it doesn't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS suggestions (
                    id SERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    username TEXT NOT NULL,
                    user_id INTEGER REFERENCES users(user_id),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending'
                )
            """)
            conn.commit()
            st.info("건의함 테이블이 생성되었습니다. 건의사항을 작성해주세요.")
            suggestions = []
        else:
            suggestions = []
    
    # Close cursor but don't close connection as it's cached
    cur.close()
    
    # Display suggestions
    if suggestions:
        for s_id, s_content, s_username, s_timestamp in suggestions:
            with st.expander(f"#{s_id} - {s_username} ({s_timestamp})"):
                st.write(s_content)
                
                # Only allow admins to delete suggestions
                if st.session_state.get('role') in ['teacher', '제작자']:
                    if st.button("삭제", key=f"delete_{s_id}"):
                        try:
                            # Get a fresh connection for this operation
                            conn = get_conn()
                            cur = conn.cursor()
                            
                            cur.execute("DELETE FROM suggestions WHERE id = %s", (s_id,))
                            conn.commit()
                            cur.close()
                            
                            st.success("건의사항이 삭제되었습니다!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"삭제 중 오류가 발생했습니다: {str(e)}")
    else:
        st.info("아직 건의사항이 없습니다.")
        
except Exception as e:
    st.error(f"건의함을 불러오는 중 오류가 발생했습니다: {str(e)}")
    st.info("관리자에게 문의하거나 데이터베이스 초기화를 진행해주세요.")
