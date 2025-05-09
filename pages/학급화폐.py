import streamlit as st
from libs.currency import (
    get_user_currency, transfer_currency, create_job, assign_job,
    create_quest, complete_quest, get_rankings, process_monthly_salaries
)
from libs.db import get_conn

st.title("🏦 학급 화폐 시스템")

# Debug information
st.write("Debug - Session State:", st.session_state)

if not st.session_state.get('logged_in'):
    st.warning("로그인이 필요합니다.")
    st.stop()

user_id = st.session_state.get('user_id')
if not user_id:
    st.warning("로그인이 필요합니다.")
    st.stop()

try:
    conn = get_conn()
    cur = conn.cursor()
    
    # Get user role
    cur.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
    result = cur.fetchone()
    if not result:
        st.error("사용자 정보를 찾을 수 없습니다.")
        st.stop()
    
    user_role = result[0]
    st.write("Debug - User Role:", user_role)
    
    # Display user's current balance
    balance = get_user_currency(user_id)
    st.metric("내 잔고", f"{balance:,}원")
    
    # Teacher-specific features
    if user_role == 'teacher':
        st.subheader("👨‍🏫 선생님 기능")
        
        # Transfer currency
        with st.expander("💰 화폐 전송"):
            cur.execute("SELECT user_id, username FROM users WHERE role = 'student'")
            students = cur.fetchall()
            student_options = {f"{username} (ID: {user_id})": user_id for user_id, username in students}
            
            selected_student = st.selectbox("학생 선택", options=list(student_options.keys()))
            amount = st.number_input("전송 금액", min_value=1, step=1)
            description = st.text_input("설명")
            
            if st.button("전송"):
                try:
                    transfer_currency(user_id, student_options[selected_student], amount, description)
                    st.success("화폐 전송 완료!")
                except Exception as e:
                    st.error(str(e))
        
        # Create job
        with st.expander("💼 직업 생성"):
            job_name = st.text_input("직업 이름")
            salary = st.number_input("급여", min_value=1, step=1)
            description = st.text_area("설명")
            
            if st.button("직업 생성"):
                job_id = create_job(job_name, salary, description, user_id)
                st.success(f"직업 '{job_name}'이 생성되었습니다!")
        
        # Assign job
        with st.expander("👔 직업 배정"):
            cur.execute("SELECT job_id, name FROM jobs")
            jobs = cur.fetchall()
            job_options = {name: job_id for job_id, name in jobs}
            
            selected_job = st.selectbox("직업 선택", options=list(job_options.keys()))
            selected_student = st.selectbox("학생 선택", options=list(student_options.keys()))
            
            if st.button("배정"):
                assign_job(student_options[selected_student], job_options[selected_job])
                st.success("직업 배정 완료!")
        
        # Create quest
        with st.expander("🎯 퀘스트 생성"):
            quest_title = st.text_input("퀘스트 제목")
            quest_description = st.text_area("퀘스트 설명")
            reward = st.number_input("보상", min_value=1, step=1)
            is_daily = st.checkbox("일일 퀘스트")
            
            if st.button("퀘스트 생성"):
                quest_id = create_quest(quest_title, quest_description, reward, user_id, is_daily)
                st.success(f"퀘스트 '{quest_title}'이 생성되었습니다!")
        
        # Verify quest completion
        with st.expander("✅ 퀘스트 인증"):
            cur.execute("""
                SELECT q.quest_id, q.title, qc.user_id, u.username
                FROM quests q
                JOIN quest_completions qc ON q.quest_id = qc.quest_id
                JOIN users u ON qc.user_id = u.user_id
                WHERE qc.verified_at IS NULL
            """)
            pending_quests = cur.fetchall()
            
            for quest_id, title, student_id, username in pending_quests:
                st.write(f"퀘스트: {title} - 학생: {username}")
                if st.button(f"인증하기", key=f"verify_{quest_id}_{student_id}"):
                    complete_quest(student_id, quest_id, user_id)
                    st.success("퀘스트 인증 완료!")
    
    # Student-specific features
    if user_role == 'student':
        st.subheader("👨‍🎓 학생 기능")
        
        # Display current job
        cur.execute("""
            SELECT j.name, j.salary, j.description
            FROM jobs j
            JOIN users u ON u.job_id = j.job_id
            WHERE u.user_id = %s
        """, (user_id,))
        job_info = cur.fetchone()
        
        if job_info:
            job_name, salary, description = job_info
            st.write(f"현재 직업: {job_name}")
            st.write(f"월급: {salary:,}원")
            st.write(f"설명: {description}")
        
        # Display available quests
        st.subheader("🎯 가능한 퀘스트")
        cur.execute("""
            SELECT quest_id, title, description, reward
            FROM quests
            WHERE quest_id NOT IN (
                SELECT quest_id FROM quest_completions WHERE user_id = %s
            )
        """, (user_id,))
        quests = cur.fetchall()
        
        for quest_id, title, description, reward in quests:
            with st.expander(f"{title} (보상: {reward:,}원)"):
                st.write(description)
                if st.button("완료 신청", key=f"complete_{quest_id}"):
                    cur.execute("""
                        INSERT INTO quest_completions (quest_id, user_id)
                        VALUES (%s, %s)
                    """, (quest_id, user_id))
                    conn.commit()
                    st.success("완료 신청이 접수되었습니다!")
    
    # Display rankings
    st.subheader("🏆 랭킹")
    rankings = get_rankings()
    for i, (username, currency, role) in enumerate(rankings, 1):
        st.write(f"{i}. {username} ({role}) - {currency:,}원")
    
    # Monthly salary processing (only for teachers)
    if user_role == 'teacher':
        if st.button("월급 지급"):
            process_monthly_salaries()
            st.success("월급 지급이 완료되었습니다!")

except Exception as e:
    st.error(f"오류가 발생했습니다: {str(e)}")
    st.write("Debug - Error Details:", e) 