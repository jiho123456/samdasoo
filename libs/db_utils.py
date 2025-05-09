import streamlit as st
import psycopg2
import psycopg2.errors
import functools
import time
from libs.db import get_conn

def test_connection(conn=None):
    """
    데이터베이스 연결이 유효한지 테스트합니다.
    
    Args:
        conn: 테스트할 연결, None이면 새 연결을 가져옵니다.
    
    Returns:
        (bool, str): (연결 성공 여부, 오류 메시지 또는 성공 메시지)
    """
    try:
        # Connection is provided
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.close()
                return True, "연결이 유효합니다."
            except (psycopg2.InterfaceError, psycopg2.OperationalError) as e:
                return False, f"연결이 닫혔거나 유효하지 않습니다: {str(e)}"
        
        # Get new connection
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            return True, "새 연결이 성공적으로 생성되었습니다."
        except Exception as e:
            return False, f"새 연결 생성 실패: {str(e)}"
    except Exception as e:
        return False, f"연결 테스트 중 오류 발생: {str(e)}"

def recover_connection():
    """
    데이터베이스 연결을 복구하고 결과를 반환합니다.
    
    Returns:
        (bool, psycopg2.connection, str): (성공 여부, 연결 객체 또는 None, 메시지)
    """
    try:
        # Clear existing connection
        if "db_conn" in st.session_state:
            try:
                st.session_state.db_conn.close()
            except:
                pass
            del st.session_state.db_conn
        
        # Get fresh connection
        conn = get_conn()
        success, message = test_connection(conn)
        
        if success:
            return True, conn, "연결이 성공적으로 복구되었습니다."
        else:
            return False, None, f"연결 복구 실패: {message}"
    except Exception as e:
        return False, None, f"연결 복구 중 오류 발생: {str(e)}"

def with_connection_retry(max_retries=3, retry_delay=1):
    """
    데이터베이스 함수에 자동 재시도 기능을 추가하는 데코레이터입니다.
    
    Args:
        max_retries (int): 최대 재시도 횟수
        retry_delay (float): 재시도 사이의 대기 시간(초)
    
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            last_error = None
            
            while retries <= max_retries:
                try:
                    # Get a fresh connection for the function
                    conn = get_conn()
                    
                    # Test if connection is valid
                    success, message = test_connection(conn)
                    if not success:
                        # Try to recover connection
                        success, conn, message = recover_connection()
                        if not success:
                            raise Exception(f"데이터베이스 연결 실패: {message}")
                    
                    # Call the function with the connection
                    return func(conn, *args, **kwargs)
                
                except (psycopg2.InterfaceError, psycopg2.OperationalError) as e:
                    last_error = e
                    retries += 1
                    
                    if retries <= max_retries:
                        # Wait before retrying
                        time.sleep(retry_delay)
                        # Try to recover connection
                        success, conn, message = recover_connection()
                    else:
                        # Max retries reached
                        break
                
                except Exception as e:
                    # Other exceptions are not retried
                    raise e
            
            # If we get here, all retries failed
            raise Exception(f"데이터베이스 연결 재시도 실패 ({max_retries}회): {str(last_error)}")
        
        return wrapper
    return decorator

def execute_query(query, params=None, fetch_all=False, fetch_one=False):
    """
    SQL 쿼리를 실행하고 결과를 반환합니다. 연결 오류 시 자동으로 재시도합니다.
    
    Args:
        query (str): 실행할 SQL 쿼리
        params (tuple): 쿼리 파라미터
        fetch_all (bool): 모든 결과 가져올지 여부
        fetch_one (bool): 단일 결과 가져올지 여부
    
    Returns:
        Query results or affected row count
    """
    @with_connection_retry(max_retries=3)
    def _execute(conn, query, params, fetch_all, fetch_one):
        try:
            cur = conn.cursor()
            cur.execute(query, params)
            
            result = None
            if fetch_all:
                result = cur.fetchall()
            elif fetch_one:
                result = cur.fetchone()
            else:
                result = cur.rowcount
            
            conn.commit()
            cur.close()
            return result
        except Exception as e:
            conn.rollback()
            raise e
    
    return _execute(query, params, fetch_all, fetch_one)

def check_table_exists(table_name):
    """
    테이블이 존재하는지 확인합니다.
    
    Args:
        table_name (str): 확인할 테이블 이름
    
    Returns:
        bool: 테이블 존재 여부
    """
    try:
        result = execute_query(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s)",
            (table_name,),
            fetch_one=True
        )
        return result[0] if result else False
    except Exception:
        return False

def diagnose_database():
    """
    데이터베이스 연결과 주요 테이블의 상태를 진단합니다.
    
    Returns:
        dict: 진단 결과
    """
    results = {
        "connection": {"status": "unknown", "message": ""},
        "tables": {},
        "counts": {},
        "recommended_actions": []
    }
    
    # Test connection
    try:
        success, message = test_connection()
        results["connection"]["status"] = "ok" if success else "error"
        results["connection"]["message"] = message
        
        if not success:
            results["recommended_actions"].append("데이터베이스 연결 설정을 확인하세요.")
            return results
        
        # Check essential tables
        essential_tables = ["users", "kicked_users", "transactions", "jobs", "quests"]
        for table in essential_tables:
            exists = check_table_exists(table)
            results["tables"][table] = exists
            
            if not exists:
                results["recommended_actions"].append(f"'{table}' 테이블이 없습니다. 데이터베이스 초기화가 필요합니다.")
        
        # Get record counts for existing tables
        for table in [t for t, exists in results["tables"].items() if exists]:
            try:
                count = execute_query(f"SELECT COUNT(*) FROM {table}", fetch_one=True)
                results["counts"][table] = count[0] if count else 0
            except:
                results["counts"][table] = "error"
        
        # Check if users table is empty
        if results["tables"].get("users", False) and results["counts"].get("users", 0) == 0:
            results["recommended_actions"].append("'users' 테이블이 비어 있습니다. 계정을 생성해야 합니다.")
        
    except Exception as e:
        results["connection"]["status"] = "error"
        results["connection"]["message"] = f"진단 중 오류 발생: {str(e)}"
        results["recommended_actions"].append("관리자에게 문의하세요.")
    
    return results 