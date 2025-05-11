import streamlit as st
from libs.db_utils import test_connection, recover_connection, check_table_exists, execute_query
from libs.db import init_tables
import json
import pandas as pd
import time
import psycopg2
import traceback

# Check if user is logged in and is admin
if not st.session_state.get('logged_in'):
    st.warning("로그인이 필요합니다.")
    st.stop()

if st.session_state.get('role') not in ['teacher', '제작자']:
    st.error("관리자만 접근할 수 있습니다.")
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

# Connection test section
st.header("1️⃣ 데이터베이스 연결 테스트")

if st.button("연결 테스트 실행", key="test_conn_btn"):
    with st.spinner("데이터베이스 연결 테스트 중..."):
        conn, error = get_fresh_connection()
        
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.fetchone()
                cur.close()
                st.success("✅ 연결 성공: 데이터베이스에 성공적으로 연결되었습니다.")
                
                # Explicitly close the connection after use
                conn.close()
            except Exception as e:
                st.error(f"❌ 쿼리 실행 실패: {str(e)}")
                try:
                    conn.close()
                except:
                    pass
                    
                if st.button("연결 복구 시도", key="recover_conn_btn"):
                    with st.spinner("연결 복구 중..."):
                        # Clear session state for connections
                        if "db_conn" in st.session_state:
                            del st.session_state.db_conn
                            
                        # Try a completely fresh connection    
                        new_conn, new_error = get_fresh_connection()
                        if new_conn:
                            st.success("✅ 복구 성공: 새 연결이 성공적으로 생성되었습니다.")
                            try:
                                new_conn.close()
                            except:
                                pass
                        else:
                            st.error(f"❌ 복구 실패: {new_error}")
        else:
            st.error(f"❌ 연결 실패: {error}")

# Full diagnostic section
st.header("2️⃣ 전체 시스템 진단")

if st.button("전체 진단 실행", key="diagnose_btn"):
    with st.spinner("시스템 진단 중..."):
        results = {
            "connection": {"status": "unknown", "message": ""},
            "tables": {},
            "counts": {},
            "columns": {},
            "recommended_actions": []
        }
        
        # Test connection
        conn, error = get_fresh_connection()
        if conn:
            results["connection"]["status"] = "ok"
            results["connection"]["message"] = "데이터베이스에 성공적으로 연결되었습니다."
            
            try:
                cur = conn.cursor()
                
                # Check essential tables
                essential_tables = ["users", "kicked_users", "transactions", "jobs", "quests", "user_items"]
                for table in essential_tables:
                    # Check if table exists
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.tables 
                            WHERE table_name = %s
                        )
                    """, (table,))
                    table_exists = cur.fetchone()[0]
                    results["tables"][table] = table_exists
                    
                    if not table_exists:
                        results["recommended_actions"].append(f"'{table}' 테이블이 없습니다. 데이터베이스 초기화가 필요합니다.")
                    else:
                        # Get record count
                        try:
                            cur.execute(f"SELECT COUNT(*) FROM {table}")
                            count = cur.fetchone()[0]
                            results["counts"][table] = count
                        except:
                            results["counts"][table] = "error"
                        
                        # Check specific columns
                        if table == "user_items":
                            cur.execute("""
                                SELECT EXISTS (
                                    SELECT 1 FROM information_schema.columns 
                                    WHERE table_name = 'user_items' AND column_name = 'is_active'
                                )
                            """)
                            has_is_active = cur.fetchone()[0]
                            results["columns"]["user_items.is_active"] = has_is_active
                            
                            if not has_is_active:
                                results["recommended_actions"].append("'user_items' 테이블에 'is_active' 컬럼이 없습니다. 스키마 업그레이드가 필요합니다.")
                
                cur.close()
            except Exception as e:
                results["connection"]["message"] += f" (하지만 쿼리 실행 중 오류 발생: {str(e)})"
                results["recommended_actions"].append("데이터베이스 쿼리 중 오류가 발생했습니다. 연결을 확인하세요.")
                try:
                    cur.close()
                except:
                    pass
            finally:
                try:
                    conn.close()
                except:
                    pass
        else:
            results["connection"]["status"] = "error"
            results["connection"]["message"] = f"연결 실패: {error}"
            results["recommended_actions"].append("데이터베이스 연결 설정을 확인하세요.")
        
        # Display results
        st.subheader("연결 상태")
        if results["connection"]["status"] == "ok":
            st.success(f"✅ {results['connection']['message']}")
        else:
            st.error(f"❌ {results['connection']['message']}")
        
        # Tables status
        if results["tables"]:
            st.subheader("테이블 상태")
            tables_data = []
            for table, exists in results["tables"].items():
                record_count = results["counts"].get(table, "N/A") if exists else "N/A"
                tables_data.append({
                    "테이블": table,
                    "존재 여부": "✅ 존재" if exists else "❌ 없음",
                    "레코드 수": record_count
                })
            
            tables_df = pd.DataFrame(tables_data)
            st.dataframe(tables_df)
        
        # Column status
        if results["columns"]:
            st.subheader("중요 컬럼 상태")
            columns_data = []
            for col_name, exists in results["columns"].items():
                table, column = col_name.split(".")
                columns_data.append({
                    "테이블": table,
                    "컬럼": column,
                    "존재 여부": "✅ 존재" if exists else "❌ 없음"
                })
            
            columns_df = pd.DataFrame(columns_data)
            st.dataframe(columns_df)
        
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
                conn, error = get_fresh_connection()
                if conn:
                    try:
                        cur = conn.cursor()
                        tables = ["users", "kicked_users", "transactions", "jobs", "quests"]
                        all_exist = True
                        missing = []
                        
                        for table in tables:
                            cur.execute("""
                                SELECT EXISTS (
                                    SELECT 1 FROM information_schema.tables 
                                    WHERE table_name = %s
                                )
                            """, (table,))
                            table_exists = cur.fetchone()[0]
                            if not table_exists:
                                all_exist = False
                                missing.append(table)
                        
                        cur.close()
                        conn.close()
                        
                        if all_exist:
                            st.success("✅ 데이터베이스 초기화가 성공적으로 완료되었습니다!")
                            st.session_state.db_initialized = True
                        else:
                            st.warning(f"⚠️ 일부 테이블이 생성되지 않았습니다: {', '.join(missing)}")
                    except Exception as e:
                        st.error(f"❌ 테이블 확인 중 오류가 발생했습니다: {str(e)}")
                        try:
                            cur.close()
                            conn.close()
                        except:
                            pass
                else:
                    st.error(f"❌ 데이터베이스 연결 실패: {error}")
            except Exception as e:
                st.error(f"❌ 초기화 중 오류가 발생했습니다: {str(e)}")
                st.code(traceback.format_exc())

# Database schema upgrade section
st.header("4️⃣ 스키마 업그레이드")
st.write("데이터베이스 스키마 변경이 필요한 경우 이 섹션을 사용하세요.")

# Add is_active column to user_items table
with st.expander("is_active 컬럼 추가"):
    st.warning("환불 기능을 위해 user_items 테이블에 is_active 컬럼이 필요합니다.")
    if st.button("is_active 컬럼 추가", key="add_is_active"):
        conn, error = get_fresh_connection()
        if conn:
            try:
                cur = conn.cursor()
                
                # Check if column exists first
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'user_items' AND column_name = 'is_active'
                    )
                """)
                column_exists = cur.fetchone()[0]
                
                if column_exists:
                    st.info("is_active 컬럼이 이미 존재합니다.")
                else:
                    cur.execute("ALTER TABLE user_items ADD COLUMN is_active BOOLEAN DEFAULT true")
                    st.success("✅ user_items 테이블에 is_active 컬럼이 추가되었습니다!")
                    
                    # Set all existing records to active
                    cur.execute("UPDATE user_items SET is_active = true")
                    st.success("✅ 모든 기존 아이템이 활성 상태로 설정되었습니다.")
                
                cur.close()
                conn.close()
            except Exception as e:
                st.error(f"is_active 컬럼 추가 중 오류 발생: {str(e)}")
                try:
                    cur.close()
                    conn.close()
                except:
                    pass
        else:
            st.error(f"데이터베이스 연결 실패: {error}")

# Manual query section (for advanced users)
st.header("5️⃣ 수동 쿼리 실행 (고급)")
st.warning("⚠️ 이 기능은 SQL 지식이 있는 관리자만 사용해야 합니다.")

query = st.text_area("SQL 쿼리 입력:", height=100)
execute_btn = st.button("쿼리 실행", key="execute_query_btn")

if execute_btn and query:
    with st.spinner("쿼리 실행 중..."):
        conn, error = get_fresh_connection()
        if conn:
            try:
                cur = conn.cursor()
                
                # Determine query type
                query_type = query.strip().split()[0].upper()
                
                if query_type in ("SELECT", "SHOW", "DESCRIBE", "EXPLAIN"):
                    cur.execute(query)
                    results = cur.fetchall()
                    
                    if results:
                        # Get column names
                        column_names = [desc[0] for desc in cur.description]
                        
                        # Convert to dataframe if possible
                        try:
                            df = pd.DataFrame(results, columns=column_names)
                            st.dataframe(df)
                        except:
                            st.code(str(results))
                    else:
                        st.info("쿼리가 결과를 반환하지 않았습니다.")
                else:
                    # For non-SELECT queries (INSERT, UPDATE, DELETE, etc.)
                    cur.execute(query)
                    conn.commit()
                    affected_rows = cur.rowcount
                    st.success(f"쿼리가 성공적으로 실행되었습니다. 영향 받은 행: {affected_rows}")
                
                cur.close()
                conn.close()
            except Exception as e:
                st.error(f"쿼리 실행 중 오류 발생: {str(e)}")
                try:
                    conn.rollback()
                    cur.close()
                    conn.close()
                except:
                    pass
        else:
            st.error(f"데이터베이스 연결 실패: {error}")

# Connection pool status (for monitoring)
st.header("6️⃣ 연결 풀 상태")
if st.button("연결 풀 상태 확인", key="check_pool_btn"):
    conn, error = get_fresh_connection()
    if conn:
        try:
            cur = conn.cursor()
            # Show number of active connections (PostgreSQL)
            cur.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
            result = cur.fetchone()[0]
            st.info(f"현재 활성 연결 수: {result}")
            
            cur.close()
            conn.close()
        except Exception as e:
            st.error(f"연결 풀 상태 확인 중 오류 발생: {str(e)}")
            try:
                cur.close()
                conn.close()
            except:
                pass
    else:
        st.error(f"데이터베이스 연결 실패: {error}")

st.markdown("---")