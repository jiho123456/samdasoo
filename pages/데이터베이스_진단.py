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

st.title("데이터베이스 수리")
st.write("데이터베이스 에러나면 여기서 절차 밟고 수리하세요.")

st.info("""
**사용 방법:**
1. **연결 테스트** 를 실행해서 연결 상태를 확인하세요.
2. 문제가 있으면 **전체 진단** 을 통해서 문제 원인을 찾으세요.
3. 필요한 경우 **데이터베이스 초기화**를 실행하여 테이블을 재생성하세요.
4. 고급 사용자는 **수동 쿼리**를 사용하여 직접 쿼리를 실행할 수 있습니다.(일반 학생은 절대 사용 금지)
5. **연결 풀 상태**를 확인하여 활성 연결을 모니터링할 수 있습니다.(테스트 중 하나)
""") 

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

# Database schema upgrade section
st.header("6️⃣ 스키마 업그레이드")
st.write("데이터베이스 스키마 변경이 필요한 경우 이 섹션을 사용하세요.")

# Check if necessary columns exist
col_checks = []

with st.expander("누락된 컬럼 확인"):
    if st.button("컬럼 확인 실행", key="check_columns_btn"):
        with st.spinner("컬럼 확인 중..."):
            try:
                # Check if is_active column exists in user_items table
                result = execute_query(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'user_items' AND column_name = 'is_active'
                    )
                    """,
                    fetch_one=True
                )
                
                has_is_active = result[0] if result else False
                col_checks.append(("user_items", "is_active", has_is_active))
                
                # Display results
                for table, column, exists in col_checks:
                    if exists:
                        st.success(f"✅ {table} 테이블에 {column} 컬럼이 존재합니다.")
                    else:
                        st.error(f"❌ {table} 테이블에 {column} 컬럼이 없습니다.")
                
                # Add missing columns button if needed
                missing_columns = [(t, c) for t, c, e in col_checks if not e]
                if missing_columns:
                    if st.button("누락된 컬럼 추가", key="add_missing_columns"):
                        for table, column in missing_columns:
                            try:
                                if table == "user_items" and column == "is_active":
                                    execute_query(
                                        "ALTER TABLE user_items ADD COLUMN is_active BOOLEAN DEFAULT true"
                                    )
                                    st.success(f"✅ {table} 테이블에 {column} 컬럼이 추가되었습니다.")
                            except Exception as e:
                                st.error(f"❌ {table} 테이블에 {column} 컬럼 추가 실패: {str(e)}")
            except Exception as e:
                st.error(f"컬럼 확인 중 오류 발생: {str(e)}")

# Add a quick fix for the is_active column
with st.expander("is_active 컬럼 빠른 추가"):
    st.warning("환불 기능을 위해 user_items 테이블에 is_active 컬럼이 필요합니다.")
    if st.button("is_active 컬럼 추가", key="add_is_active"):
        try:
            # Check if column exists first
            result = execute_query(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'user_items' AND column_name = 'is_active'
                )
                """,
                fetch_one=True
            )
            
            column_exists = result[0] if result else False
            
            if column_exists:
                st.info("is_active 컬럼이 이미 존재합니다.")
            else:
                execute_query(
                    "ALTER TABLE user_items ADD COLUMN is_active BOOLEAN DEFAULT true"
                )
                st.success("✅ user_items 테이블에 is_active 컬럼이 추가되었습니다!")
                # Set all existing records to active
                execute_query(
                    "UPDATE user_items SET is_active = true"
                )
                st.success("✅ 모든 기존 아이템이 활성 상태로 설정되었습니다.")
        except Exception as e:
            st.error(f"is_active 컬럼 추가 중 오류 발생: {str(e)}")
            
# Also fix the refund management section to handle missing is_active column
st.header("7️⃣ 환불 관리 페이지 수정")
st.write("환불 관리 페이지에서 is_active 컬럼 오류를 방지하기 위한 수정입니다.")

if st.button("환불 관리 페이지 쿼리 수정", key="fix_refund_page"):
    try:
        # Check if column exists
        result = execute_query(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'user_items' AND column_name = 'is_active'
            )
            """,
            fetch_one=True
        )
        
        column_exists = result[0] if result else False
        
        if column_exists:
            st.success("환불 관리 페이지를 사용할 수 있습니다. is_active 컬럼이 존재합니다.")
        else:
            st.warning("환불 관리 페이지를 사용하려면 먼저 위의 'is_active 컬럼 추가' 버튼을 사용하세요.")
    except Exception as e:
        st.error(f"환불 관리 페이지 쿼리 확인 중 오류 발생: {str(e)}")

st.markdown("---")