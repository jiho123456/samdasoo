import streamlit as st
from libs.db_utils import test_connection, recover_connection, diagnose_database, check_table_exists, execute_query
from libs.db import init_tables
import json
import pandas as pd
import time

# Check if user is logged in and is admin
if not st.session_state.get('logged_in'):
    st.warning("로그인이 필요합니다.")
    st.stop()

if st.session_state.get('role') not in ['teacher', '제작자']:
    st.error("관리자만 접근할 수 있습니다.")
    st.stop()

st.title("🔍 데이터베이스 진단 도구")
st.write("이 페이지는 데이터베이스 연결 문제를 진단하고 해결하는 도구를 제공합니다.")

# Connection test section
st.header("1️⃣ 데이터베이스 연결 테스트")

if st.button("연결 테스트 실행", key="test_conn_btn"):
    with st.spinner("데이터베이스 연결 테스트 중..."):
        success, message = test_connection()
        
        if success:
            st.success(f"✅ 연결 성공: {message}")
        else:
            st.error(f"❌ 연결 실패: {message}")
            
            if st.button("연결 복구 시도", key="recover_conn_btn"):
                with st.spinner("연결 복구 중..."):
                    recovery_success, conn, recovery_message = recover_connection()
                    
                    if recovery_success:
                        st.success(f"✅ 복구 성공: {recovery_message}")
                    else:
                        st.error(f"❌ 복구 실패: {recovery_message}")

# Full diagnostic section
st.header("2️⃣ 전체 시스템 진단")

if st.button("전체 진단 실행", key="diagnose_btn"):
    with st.spinner("시스템 진단 중..."):
        results = diagnose_database()
        
        # Connection status
        st.subheader("연결 상태")
        if results["connection"]["status"] == "ok":
            st.success(f"✅ {results['connection']['message']}")
        else:
            st.error(f"❌ {results['connection']['message']}")
        
        # Tables status
        st.subheader("테이블 상태")
        tables_df = pd.DataFrame({
            "테이블": list(results["tables"].keys()),
            "존재 여부": ["✅ 존재" if v else "❌ 없음" for v in results["tables"].values()],
            "레코드 수": [results["counts"].get(t, "N/A") for t in results["tables"].keys()]
        })
        st.dataframe(tables_df)
        
        # Recommended actions
        if results["recommended_actions"]:
            st.subheader("권장 조치")
            for i, action in enumerate(results["recommended_actions"], 1):
                st.write(f"{i}. {action}")

# Database initialization section
st.header("3️⃣ 데이터베이스 초기화")
st.warning("⚠️ 이 기능은 데이터베이스 테이블을 새로 생성합니다. 기존 데이터가 삭제될 수 있습니다.")

init_option = st.radio(
    "초기화 옵션 선택:",
    ["기존 테이블 유지 (누락된 테이블만 생성)", "전체 테이블 재생성 (모든 데이터 삭제)"],
    key="init_option"
)

confirm_text = st.text_input("확인을 위해 '초기화' 라고 입력하세요:", key="confirm_init")

if st.button("데이터베이스 초기화 실행", key="init_db_btn"):
    if confirm_text != "초기화":
        st.error("확인 텍스트가 일치하지 않습니다.")
    else:
        with st.spinner("데이터베이스 초기화 중..."):
            try:
                force_recreate = init_option.startswith("전체 테이블")
                
                # Call the init_tables function
                init_tables(force_recreate=force_recreate)
                
                # Wait a moment to let initialization complete
                time.sleep(2)
                
                # Check if it worked
                tables = ["users", "kicked_users", "transactions", "jobs", "quests"]
                all_exist = True
                missing = []
                
                for table in tables:
                    if not check_table_exists(table):
                        all_exist = False
                        missing.append(table)
                
                if all_exist:
                    st.success("✅ 데이터베이스 초기화가 성공적으로 완료되었습니다!")
                    st.session_state.db_initialized = True
                else:
                    st.warning(f"⚠️ 일부 테이블이 생성되지 않았습니다: {', '.join(missing)}")
            except Exception as e:
                st.error(f"❌ 초기화 중 오류가 발생했습니다: {str(e)}")

# Manual query section (for advanced users)
st.header("4️⃣ 수동 쿼리 실행 (고급)")
st.warning("⚠️ 이 기능은 SQL 지식이 있는 관리자만 사용해야 합니다.")

query = st.text_area("SQL 쿼리 입력:", height=100)
execute_btn = st.button("쿼리 실행", key="execute_query_btn")

if execute_btn and query:
    with st.spinner("쿼리 실행 중..."):
        try:
            # Determine query type
            query_type = query.strip().split()[0].upper()
            
            if query_type in ("SELECT", "SHOW", "DESCRIBE", "EXPLAIN"):
                results = execute_query(query, fetch_all=True)
                
                if results:
                    # Convert to dataframe if possible
                    try:
                        df = pd.DataFrame(results)
                        st.dataframe(df)
                    except:
                        st.code(str(results))
                else:
                    st.info("쿼리가 결과를 반환하지 않았습니다.")
            else:
                # For non-SELECT queries (INSERT, UPDATE, DELETE, etc.)
                affected_rows = execute_query(query)
                st.success(f"쿼리가 성공적으로 실행되었습니다. 영향 받은 행: {affected_rows}")
                
        except Exception as e:
            st.error(f"쿼리 실행 중 오류 발생: {str(e)}")

# Connection pool status (for monitoring)
st.header("5️⃣ 연결 풀 상태")

if st.button("연결 풀 상태 확인", key="check_pool_btn"):
    if "db_conn" in st.session_state:
        st.success("✅ 세션 상태에 연결 객체가 있습니다.")
        
        # Test if it's still valid
        try:
            success, message = test_connection(st.session_state.db_conn)
            if success:
                st.success(f"✅ 연결 상태: {message}")
            else:
                st.error(f"❌ 연결 상태: {message}")
        except Exception as e:
            st.error(f"❌ 연결 테스트 중 오류 발생: {str(e)}")
    else:
        st.warning("⚠️ 세션 상태에 연결 객체가 없습니다.")
    
    # Show number of active connections (if PostgreSQL)
    try:
        result = execute_query(
            "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()",
            fetch_one=True
        )
        st.info(f"현재 활성 연결 수: {result[0]}")
    except:
        st.warning("활성 연결 수를 확인할 수 없습니다.")

st.markdown("---")
st.info("""
**사용 방법:**
1. **연결 테스트**를 실행하여 데이터베이스 연결 상태를 확인합니다.
2. 문제가 있는 경우 **전체 진단**을 실행하여 구체적인 원인을 찾습니다.
3. 필요한 경우 **데이터베이스 초기화**를 실행하여 테이블을 재생성합니다.
4. 고급 사용자는 **수동 쿼리**를 사용하여 직접 쿼리를 실행할 수 있습니다.
5. **연결 풀 상태**를 확인하여 활성 연결을 모니터링할 수 있습니다.
""") 