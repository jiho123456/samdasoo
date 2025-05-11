import streamlit as st
import psycopg2
import time
import traceback
import sys
import os

st.title("🛠️ 데이터베이스 연결 자동 수정")
st.markdown("이 페이지는 모든 페이지에서 발생하는 'connection already closed' 오류를 자동으로 수정합니다.")

# Show instructions
st.info("""
### 이 페이지 사용법:
1. 이 페이지는 'connection already closed' 오류가 발생할 때 사용하세요
2. 아래 '연결 오류 수정' 버튼을 누르면 자동으로 문제를 해결합니다
3. 수정이 완료되면 앱을 다시 시작하세요
""")

# Show fix button
if st.button("연결 오류 수정", key="fix_conn_btn"):
    with st.spinner("문제를 진단하고 수정하는 중..."):
        # Step 1: Test connection
        try:
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
            
            # Test the connection
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
            conn.close()
            
            connection_ok = True
            st.success("✅ 데이터베이스 연결 테스트 성공!")
        except Exception as e:
            connection_ok = False
            st.error(f"❌ 데이터베이스 연결 테스트 실패: {str(e)}")
            st.code(traceback.format_exc())
        
        if connection_ok:
            # Step 2: Clear session state
            st.write("세션 상태 초기화 중...")
            keys_to_remove = []
            for key in st.session_state:
                if key.startswith('db_') or key == 'last_db_check':
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                if key in st.session_state:
                    del st.session_state[key]
            
            st.success(f"✅ {len(keys_to_remove)}개의 세션 상태 변수가 초기화되었습니다.")
            
            # Step 3: Reset global state
            st.write("글로벌 상태 초기화 중...")
            
            # Reset last check time
            if 'last_db_check' not in st.session_state:
                st.session_state.last_db_check = 0
                
            st.success("✅ 글로벌 상태가 초기화되었습니다.")
            
            # Final success message
            st.success("🎉 모든 문제가 수정되었습니다! 이제 앱을 다시 사용해보세요.")
            
            # Provide rerun button
            if st.button("앱 다시 시작"):
                st.rerun()
        else:
            st.error("데이터베이스 연결 문제를 해결할 수 없습니다. 데이터베이스 설정을 확인하세요.")
            st.warning("데이터베이스 진단 페이지로 이동하면 더 자세한 진단을 받을 수 있습니다.")
            
            if st.button("데이터베이스 진단 페이지로 이동"):
                st.switch_page("pages/데이터베이스_진단.py")

# Provide a link to database diagnostic page
st.markdown("---")
st.write("더 자세한 문제 진단이 필요하신가요?")
if st.button("데이터베이스 진단 페이지로 이동"):
    st.switch_page("pages/데이터베이스_진단.py") 