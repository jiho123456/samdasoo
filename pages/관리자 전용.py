import streamlit as st
from libs.db import get_conn
import pandas as pd
from datetime import datetime
import json
import base64
from io import BytesIO
from PIL import Image

st.title("🔧 관리자 페이지")

# Check if user is logged in and has admin privileges
if not st.session_state.get('logged_in'):
    st.warning("로그인이 필요합니다.")
    st.stop()

if st.session_state.get('role') not in ['teacher', '제작자']:
    st.error("관리자 권한이 필요합니다.")
    st.stop()

user_id = st.session_state.get('user_id')
if not user_id:
    st.warning("로그인이 필요합니다.")
    st.stop()

try:
    conn = get_conn()
    cur = conn.cursor()
    
    # Admin dashboard tabs
    tabs = st.tabs(["사용자 관리", "화폐 시스템", "상점 관리", "블로그 관리", "통계", "환불 관리", "공지 관리"])
    
    #-----------------------------------------------------------
    # 1. USER MANAGEMENT TAB
    #-----------------------------------------------------------
    with tabs[0]:
        st.header("👥 사용자 관리")
        
        # Get all users
        cur.execute("""
            SELECT user_id, username, role, currency, 
                   CASE WHEN EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name = 'users' AND column_name = 'bio')
                        THEN bio ELSE '' END as bio,
                   created_at 
            FROM users
            ORDER BY role, username
        """)
        users = cur.fetchall()
        
        # Convert to DataFrame for easier display
        if not users:
            st.info("등록된 사용자가 없습니다.")
        else:
            users_df = pd.DataFrame(users, columns=["ID", "사용자명", "역할", "잔고", "소개", "가입일"])
            
            # Role filter
            roles = ["모두 보기"] + sorted(users_df["역할"].unique().tolist())
            selected_role = st.selectbox("역할별 필터링", roles, key="user_role_filter")
            
            if selected_role != "모두 보기":
                filtered_df = users_df[users_df["역할"] == selected_role]
            else:
                filtered_df = users_df
            
            # Display users
            st.dataframe(filtered_df)
            
            # User management actions
            st.subheader("🛠️ 사용자 작업")
            
            # 1. Change user role
            with st.expander("역할 변경"):
                user_list = {row["사용자명"]: row["ID"] for _, row in users_df.iterrows()}
                
                if not user_list:
                    st.info("사용자가 없습니다.")
                else:
                    selected_user = st.selectbox("사용자 선택", list(user_list.keys()), key="role_change_user")
                    new_role = st.selectbox("새 역할", ["student", "teacher", "일반학생", "제작자"], key="new_role_select")
                    
                    if st.button("역할 변경"):
                        try:
                            cur.execute(
                                "UPDATE users SET role = %s WHERE user_id = %s",
                                (new_role, user_list[selected_user])
                            )
                            conn.commit()
                            st.success(f"{selected_user}의 역할이 {new_role}로 변경되었습니다!")
                        except Exception as e:
                            conn.rollback()
                            st.error(f"오류가 발생했습니다: {str(e)}")
            
            # 2. Add currency to user
            with st.expander("화폐 추가/차감"):
                if not user_list:
                    st.info("사용자가 없습니다.")
                else:
                    selected_user2 = st.selectbox("사용자 선택", list(user_list.keys()), key="currency_user")
                    amount = st.number_input("금액 (차감시 음수 입력)", step=100)
                    reason = st.text_input("사유")
                    
                    if st.button("적용"):
                        try:
                            # Update user currency
                            cur.execute(
                                "UPDATE users SET currency = currency + %s WHERE user_id = %s",
                                (amount, user_list[selected_user2])
                            )
                            
                            # Record transaction
                            transaction_type = "transfer"
                            if amount > 0:
                                cur.execute(
                                    """
                                    INSERT INTO transactions 
                                    (from_user_id, to_user_id, amount, type, description, created_by)
                                    VALUES (NULL, %s, %s, %s, %s, %s)
                                    """,
                                    (user_list[selected_user2], amount, transaction_type, f"관리자: {reason}", user_id)
                                )
                            else:
                                cur.execute(
                                    """
                                    INSERT INTO transactions 
                                    (from_user_id, to_user_id, amount, type, description, created_by)
                                    VALUES (%s, NULL, %s, %s, %s, %s)
                                    """,
                                    (user_list[selected_user2], abs(amount), transaction_type, f"관리자: {reason}", user_id)
                                )
                            
                            conn.commit()
                            st.success(f"{selected_user2}의 잔고가 {amount:+,}원 변경되었습니다!")
                        except Exception as e:
                            conn.rollback()
                            st.error(f"오류가 발생했습니다: {str(e)}")
            
            # 3. Delete user
            with st.expander("사용자 삭제"):
                if not user_list:
                    st.info("사용자가 없습니다.")
                else:
                    selected_user3 = st.selectbox("사용자 선택", list(user_list.keys()), key="delete_user")
                    reason = st.text_input("삭제 사유", key="delete_reason")
                    confirm = st.checkbox(f"정말로 {selected_user3} 사용자를 삭제하시겠습니까?")
                    
                    if st.button("삭제") and confirm:
                        try:
                            # First add to kicked_users
                            cur.execute(
                                "INSERT INTO kicked_users (username, reason) VALUES (%s, %s)",
                                (selected_user3, reason)
                            )
                            
                            # Now delete the user
                            cur.execute("DELETE FROM users WHERE user_id = %s", (user_list[selected_user3],))
                            
                            conn.commit()
                            st.success(f"{selected_user3} 사용자가 삭제되었습니다.")
                        except Exception as e:
                            conn.rollback()
                            st.error(f"오류가 발생했습니다: {str(e)}")
    
    #-----------------------------------------------------------
    # 2. CURRENCY SYSTEM TAB
    #-----------------------------------------------------------
    with tabs[1]:
        st.header("💰 화폐 시스템")
        
        # Transaction history
        st.subheader("📝 거래 내역")
        
        # Check if transactions table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'transactions'
            )
        """)
        
        if cur.fetchone()[0]:
            # Get transactions
            cur.execute("""
                SELECT t.transaction_id, 
                       COALESCE(u1.username, '시스템') as from_user, 
                       COALESCE(u2.username, '시스템') as to_user, 
                       t.amount, t.type, t.description, t.created_at
                FROM transactions t
                LEFT JOIN users u1 ON t.from_user_id = u1.user_id
                LEFT JOIN users u2 ON t.to_user_id = u2.user_id
                ORDER BY t.created_at DESC
                LIMIT 100
            """)
            
            transactions = cur.fetchall()
            transactions_df = pd.DataFrame(
                transactions, 
                columns=["ID", "보낸 사람", "받은 사람", "금액", "유형", "설명", "시간"]
            )
            
            # Filter options
            transaction_types = ["모두 보기"] + sorted(transactions_df["유형"].unique().tolist())
            selected_type = st.selectbox("거래 유형 필터링", transaction_types, key="transaction_type_filter")
            
            if selected_type != "모두 보기":
                filtered_transactions = transactions_df[transactions_df["유형"] == selected_type]
            else:
                filtered_transactions = transactions_df
            
            # Display transactions
            st.dataframe(filtered_transactions)
        else:
            st.info("거래 내역이 없습니다.")
        
        # Jobs management
        st.subheader("💼 직업 관리")
        
        # Check if jobs table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'jobs'
            )
        """)
        
        if cur.fetchone()[0]:
            # Get jobs
            cur.execute("""
                SELECT j.job_id, j.name, j.salary, j.description,
                       u.username as created_by, j.created_at,
                       COUNT(u2.user_id) as assigned_users
                FROM jobs j
                LEFT JOIN users u ON j.created_by = u.user_id
                LEFT JOIN users u2 ON u2.job_id = j.job_id
                GROUP BY j.job_id, j.name, j.salary, j.description, u.username, j.created_at
                ORDER BY j.name
            """)
            
            jobs = cur.fetchall()
            jobs_df = pd.DataFrame(
                jobs,
                columns=["ID", "직업명", "급여", "설명", "생성자", "생성일", "배정된 학생 수"]
            )
            
            # Display jobs
            st.dataframe(jobs_df)
            
            # Add new job
            with st.expander("새 직업 추가"):
                job_name = st.text_input("직업명", key="new_job_name")
                salary = st.number_input("급여", min_value=1, step=100, key="new_job_salary")
                description = st.text_area("설명", key="new_job_description")
                
                if st.button("직업 추가"):
                    try:
                        cur.execute(
                            """
                            INSERT INTO jobs (name, salary, description, created_by)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (job_name, salary, description, user_id)
                        )
                        conn.commit()
                        st.success(f"'{job_name}' 직업이 추가되었습니다!")
                    except Exception as e:
                        conn.rollback()
                        st.error(f"오류가 발생했습니다: {str(e)}")
            
            # Assign job to user
            st.subheader("💼 직업 배정")
            # Get all jobs
            cur.execute("SELECT job_id, name FROM jobs")
            job_rows = cur.fetchall()
            
            # Get all students
            cur.execute("SELECT user_id, username FROM users WHERE role IN ('student', '일반학생')")
            student_rows = cur.fetchall()
            
            if not job_rows:
                st.info("등록된 직업이 없습니다. 먼저 직업을 추가해주세요.")
            elif not student_rows:
                st.info("등록된 학생이 없습니다.")
            else:
                job_options = {row[1]: row[0] for row in job_rows}
                student_options = {row[1]: row[0] for row in student_rows}
                
                selected_job = st.selectbox("직업 선택", list(job_options.keys()), key="job_assign_select")
                selected_student = st.selectbox("학생 선택", list(student_options.keys()), key="job_student_select")
                
                if st.button("배정"):
                    try:
                        cur.execute(
                            "UPDATE users SET job_id = %s WHERE user_id = %s",
                            (job_options[selected_job], student_options[selected_student])
                        )
                        conn.commit()
                        st.success(f"{selected_student}에게 {selected_job} 직업이 배정되었습니다!")
                    except Exception as e:
                        conn.rollback()
                        st.error(f"오류가 발생했습니다: {str(e)}")
        else:
            st.info("직업 정보가 없습니다.")
        
        # Process monthly salaries
        st.subheader("💸 월급 처리")
        if st.button("월급 지급 처리"):
            try:
                # Get all users with jobs
                cur.execute("""
                    SELECT u.user_id, u.username, j.job_id, j.name, j.salary
                    FROM users u
                    JOIN jobs j ON u.job_id = j.job_id
                """)
                
                users_with_jobs = cur.fetchall()
                
                for user_id, username, job_id, job_name, salary in users_with_jobs:
                    # Add salary to user
                    cur.execute(
                        "UPDATE users SET currency = currency + %s WHERE user_id = %s",
                        (salary, user_id)
                    )
                    
                    # Record transaction
                    cur.execute(
                        """
                        INSERT INTO transactions 
                        (from_user_id, to_user_id, amount, type, description, created_by)
                        VALUES (NULL, %s, %s, %s, %s, %s)
                        """,
                        (user_id, salary, "salary", f"{job_name} 월급", user_id)
                    )
                
                conn.commit()
                st.success(f"{len(users_with_jobs)}명의 사용자에게 월급이 지급되었습니다!")
            except Exception as e:
                conn.rollback()
                st.error(f"오류가 발생했습니다: {str(e)}")
    
    #-----------------------------------------------------------
    # 3. SHOP MANAGEMENT TAB
    #-----------------------------------------------------------
    with tabs[2]:
        st.header("🛒 상점 관리")
        
        # Check if shop_items table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'shop_items'
            )
        """)
        
        shop_exists = cur.fetchone()[0]
        
        if not shop_exists:
            st.warning("상점 시스템이 초기화되지 않았습니다. 데이터베이스 초기화가 필요합니다.")
        else:
            # Get all shop items
            cur.execute("""
                SELECT item_id, name, description, type, price, image_url, created_at
                FROM shop_items
                ORDER BY type, name
            """)
            
            items = cur.fetchall()
            
            if not items:
                st.info("등록된 상품이 없습니다. 새 아이템을 추가해주세요.")
            else:
                items_df = pd.DataFrame(
                    items,
                    columns=["ID", "아이템명", "설명", "유형", "가격", "이미지 URL", "생성일"]
                )
                
                # Filter by type
                item_types = ["모두 보기"] + sorted(items_df["유형"].unique().tolist())
                selected_type = st.selectbox("아이템 유형 필터링", item_types, key="item_type_filter")
                
                if selected_type != "모두 보기":
                    filtered_items = items_df[items_df["유형"] == selected_type]
                else:
                    filtered_items = items_df
                
                # Display items
                st.dataframe(filtered_items)
            
            # Add new item
            with st.expander("새 아이템 추가"):
                col1, col2 = st.columns(2)
                
                with col1:
                    new_name = st.text_input("아이템 이름", key="new_item_name")
                    new_description = st.text_area("아이템 설명", key="new_item_description")
                    new_price = st.number_input("가격", min_value=1, step=10, key="new_item_price")
                
                with col2:
                    new_type = st.selectbox("아이템 유형", 
                                           ["avatar", "badge", "background", "font", "color"],
                                           key="new_item_type",
                                           format_func=lambda x: {
                                               "avatar": "아바타",
                                               "badge": "배지",
                                               "background": "배경",
                                               "font": "폰트",
                                               "color": "색상"
                                           }.get(x, x))
                    
                    # Two options for image upload
                    upload_method = st.radio("이미지 업로드 방식", ["URL 입력", "파일 업로드"], key="new_item_upload_method")
                    
                    if upload_method == "URL 입력":
                        new_image_url = st.text_input("이미지 URL", key="new_item_url")
                    else:
                        uploaded_file = st.file_uploader("이미지 파일", type=["jpg", "jpeg", "png"], key="new_item_file")
                        new_image_url = None
                        
                        if uploaded_file:
                            try:
                                # Convert to base64
                                image = Image.open(uploaded_file)
                                # Resize if needed
                                if max(image.size) > 400:
                                    image.thumbnail((400, 400))
                                buffered = BytesIO()
                                image.save(buffered, format="PNG")
                                img_str = base64.b64encode(buffered.getvalue()).decode()
                                new_image_url = f"data:image/png;base64,{img_str}"
                                st.image(new_image_url, width=150)
                            except Exception as e:
                                st.error(f"이미지 처리 중 오류: {str(e)}")
                
                if st.button("아이템 추가"):
                    if new_name and new_description and new_price > 0 and new_image_url:
                        try:
                            cur.execute(
                                """
                                INSERT INTO shop_items (name, description, type, price, image_url)
                                VALUES (%s, %s, %s, %s, %s)
                                """,
                                (new_name, new_description, new_type, new_price, new_image_url)
                            )
                            conn.commit()
                            st.success(f"'{new_name}' 아이템이 추가되었습니다!")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"오류가 발생했습니다: {str(e)}")
                    else:
                        st.error("모든 필드를 입력해주세요.")
            
            # Edit/Delete item
            with st.expander("아이템 수정/삭제"):
                # Get all items
                cur.execute("SELECT item_id, name, type FROM shop_items ORDER BY type, name")
                shop_items = cur.fetchall()
                
                if not shop_items:
                    st.info("아직 등록된 아이템이 없습니다. 아이템을 추가해주세요.")
                else:
                    item_options = {f"{row[1]} ({row[2]})": row[0] for row in shop_items}
                    selected_item = st.selectbox("아이템 선택", list(item_options.keys()), key="edit_item_select")
                    
                    if selected_item:
                        item_id = item_options[selected_item]
                        
                        # Get item details
                        cur.execute(
                            "SELECT name, description, type, price, image_url FROM shop_items WHERE item_id = %s",
                            (item_id,)
                        )
                        item = cur.fetchone()
                        if item:
                            name, description, type_, price, image_url = item
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                edit_name = st.text_input("아이템 이름", value=name, key="edit_item_name")
                                edit_description = st.text_area("아이템 설명", value=description, key="edit_item_description")
                                edit_price = st.number_input("가격", min_value=1, step=10, value=price, key="edit_item_price")
                            
                            with col2:
                                type_options = ["avatar", "badge", "background", "font", "color"]
                                type_index = type_options.index(type_) if type_ in type_options else 0
                                
                                edit_type = st.selectbox("아이템 유형", 
                                                       type_options,
                                                       index=type_index,
                                                       key="edit_item_type",
                                                       format_func=lambda x: {
                                                           "avatar": "아바타",
                                                           "badge": "배지",
                                                           "background": "배경",
                                                           "font": "폰트",
                                                           "color": "색상"
                                                       }.get(x, x))
                                
                                st.write("현재 이미지:")
                                if image_url:
                                    st.image(image_url, width=150)
                                else:
                                    st.info("이미지가 없습니다.")
                                
                                # Keep or change image
                                change_image = st.checkbox("이미지 변경", key="edit_change_image")
                                
                                if change_image:
                                    upload_method = st.radio("새 이미지 업로드 방식", ["URL 입력", "파일 업로드"], key="edit_item_upload_method")
                                    
                                    if upload_method == "URL 입력":
                                        edit_image_url = st.text_input("이미지 URL", value=image_url or "", key="edit_item_url")
                                    else:
                                        uploaded_file = st.file_uploader("이미지 파일", type=["jpg", "jpeg", "png"], key="edit_item_file")
                                        edit_image_url = image_url
                                        
                                        if uploaded_file:
                                            try:
                                                # Convert to base64
                                                image = Image.open(uploaded_file)
                                                # Resize if needed
                                                if max(image.size) > 400:
                                                    image.thumbnail((400, 400))
                                                buffered = BytesIO()
                                                image.save(buffered, format="PNG")
                                                img_str = base64.b64encode(buffered.getvalue()).decode()
                                                edit_image_url = f"data:image/png;base64,{img_str}"
                                                st.image(edit_image_url, width=150)
                                            except Exception as e:
                                                st.error(f"이미지 처리 중 오류: {str(e)}")
                                else:
                                    edit_image_url = image_url
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("아이템 수정"):
                                    if edit_name and edit_description and edit_price > 0 and edit_image_url:
                                        try:
                                            cur.execute(
                                                """
                                                UPDATE shop_items 
                                                SET name = %s, description = %s, type = %s, price = %s, image_url = %s
                                                WHERE item_id = %s
                                                """,
                                                (edit_name, edit_description, edit_type, edit_price, edit_image_url, item_id)
                                            )
                                            conn.commit()
                                            st.success(f"'{edit_name}' 아이템이 수정되었습니다!")
                                            st.rerun()
                                        except Exception as e:
                                            conn.rollback()
                                            st.error(f"오류가 발생했습니다: {str(e)}")
                                    else:
                                        st.error("모든 필드를 입력해주세요.")
                            
                            with col2:
                                delete_confirm = st.checkbox(f"'{name}' 아이템을 정말로 삭제하시겠습니까?", key=f"delete_item_confirm_{item_id}")
                                if st.button("아이템 삭제") and delete_confirm:
                                    try:
                                        # First delete from user_items
                                        cur.execute("DELETE FROM user_items WHERE item_id = %s", (item_id,))
                                        
                                        # Then delete the item
                                        cur.execute("DELETE FROM shop_items WHERE item_id = %s", (item_id,))
                                        
                                        conn.commit()
                                        st.success(f"'{name}' 아이템이 삭제되었습니다!")
                                        st.rerun()
                                    except Exception as e:
                                        conn.rollback()
                                        st.error(f"오류가 발생했습니다: {str(e)}")
                    else:
                        st.warning("아이템을 선택해주세요.")
    
    #-----------------------------------------------------------
    # 4. BLOG MANAGEMENT TAB
    #-----------------------------------------------------------
    with tabs[3]:
        st.header("📝 블로그 관리")
        
        # Check if blog_posts table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'blog_posts'
            )
        """)
        
        blog_exists = cur.fetchone()[0]
        
        if not blog_exists:
            st.warning("블로그 시스템이 초기화되지 않았습니다. 데이터베이스 초기화가 필요합니다.")
        else:
            # Get all posts with author info
            cur.execute("""
                SELECT p.post_id, p.title, 
                       CASE WHEN LENGTH(p.content) > 50 THEN SUBSTRING(p.content, 1, 50) || '...' ELSE p.content END,
                       u.username, p.created_at, 
                       (SELECT COUNT(*) FROM blog_comments WHERE post_id = p.post_id) AS comment_count
                FROM blog_posts p
                JOIN users u ON p.user_id = u.user_id
                ORDER BY p.created_at DESC
            """)
            
            posts = cur.fetchall()
            
            if posts:
                posts_df = pd.DataFrame(
                    posts,
                    columns=["ID", "제목", "내용", "작성자", "작성일", "댓글 수"]
                )
                
                # Filter options
                author_filter = ["모두 보기"] + sorted(posts_df["작성자"].unique().tolist())
                selected_author = st.selectbox("작성자별 필터링", author_filter, key="blog_author_filter")
                
                if selected_author != "모두 보기":
                    filtered_posts = posts_df[posts_df["작성자"] == selected_author]
                else:
                    filtered_posts = posts_df
                
                # Display posts
                st.dataframe(filtered_posts)
                
                # View/Edit/Delete post
                with st.expander("게시글 보기/수정/삭제"):
                    # Get all posts
                    cur.execute("""
                        SELECT p.post_id, p.title, u.username, p.created_at
                        FROM blog_posts p
                        JOIN users u ON p.user_id = u.user_id
                        ORDER BY p.created_at DESC
                    """)
                    
                    posts = cur.fetchall()
                    post_options = {f"{row[1]} (by {row[2]} - {row[3].strftime('%Y-%m-%d')})": row[0] for row in posts}
                    
                    selected_post = st.selectbox("게시글 선택", list(post_options.keys()), key="blog_post_select")
                    post_id = post_options[selected_post]
                    
                    # Get post details
                    cur.execute("""
                        SELECT p.title, p.content, p.image_urls, p.user_id, u.username
                        FROM blog_posts p
                        JOIN users u ON p.user_id = u.user_id
                        WHERE p.post_id = %s
                    """, (post_id,))
                    
                    post = cur.fetchone()
                    if post:
                        title, content, image_urls_json, author_id, author_name = post
                        
                        st.write(f"### {title}")
                        st.write(f"**작성자**: {author_name}")
                        st.write(content)
                        
                        # Display images if any
                        if image_urls_json:
                            try:
                                image_urls = json.loads(image_urls_json)
                                if image_urls:
                                    st.write("**첨부 이미지**:")
                                    cols = st.columns(min(len(image_urls), 3))
                                    for i, img_url in enumerate(image_urls):
                                        with cols[i % 3]:
                                            st.image(img_url, width=150)
                            except:
                                st.write("이미지를 불러올 수 없습니다.")
                        
                        # Get comments
                        cur.execute("""
                            SELECT c.comment_id, c.content, u.username, c.created_at
                            FROM blog_comments c
                            JOIN users u ON c.user_id = u.user_id
                            WHERE c.post_id = %s
                            ORDER BY c.created_at
                        """, (post_id,))
                        
                        comments = cur.fetchall()
                        
                        if comments:
                            st.write("### 댓글")
                            for comment_id, comment, comment_author, comment_time in comments:
                                st.markdown(f"""
                                    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                                        <p><strong>{comment_author}</strong> • {comment_time.strftime('%Y-%m-%d %H:%M')}</p>
                                        <p>{comment}</p>
                                    </div>
                                """, unsafe_allow_html=True)
                                
                                # Delete comment option
                                if st.button(f"댓글 삭제", key=f"delete_comment_{comment_id}"):
                                    try:
                                        cur.execute("DELETE FROM blog_comments WHERE comment_id = %s", (comment_id,))
                                        conn.commit()
                                        st.success("댓글이 삭제되었습니다!")
                                        st.rerun()
                                    except Exception as e:
                                        conn.rollback()
                                        st.error(f"오류가 발생했습니다: {str(e)}")
                        
                        # Delete post option
                        delete_confirm = st.checkbox(f"'{title}' 게시글을 정말로 삭제하시겠습니까?", key=f"delete_post_confirm_{post_id}")
                        if st.button("게시글 삭제") and delete_confirm:
                            try:
                                # Delete comments first
                                cur.execute("DELETE FROM blog_comments WHERE post_id = %s", (post_id,))
                                
                                # Then delete the post
                                cur.execute("DELETE FROM blog_posts WHERE post_id = %s", (post_id,))
                                
                                conn.commit()
                                st.success(f"'{title}' 게시글이 삭제되었습니다!")
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"오류가 발생했습니다: {str(e)}")
            else:
                st.info("게시글이 없습니다.")
    
    #-----------------------------------------------------------
    # 5. STATISTICS TAB
    #-----------------------------------------------------------
    with tabs[4]:
        st.header("📊 통계")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # User counts
            cur.execute("""
                SELECT COUNT(*) FROM users
            """)
            user_count = cur.fetchone()[0]
            
            cur.execute("""
                SELECT role, COUNT(*) FROM users GROUP BY role
            """)
            role_counts = cur.fetchall()
            
            st.metric("총 사용자 수", user_count)
            
            st.write("### 역할별 사용자 수")
            role_df = pd.DataFrame(role_counts, columns=["역할", "수"])
            st.dataframe(role_df)
        
        with col2:
            # Currency statistics
            cur.execute("""
                SELECT SUM(currency) FROM users
            """)
            total_currency = cur.fetchone()[0] or 0
            
            cur.execute("""
                SELECT MAX(currency) FROM users
            """)
            max_currency = cur.fetchone()[0] or 0
            
            cur.execute("""
                SELECT AVG(currency) FROM users
            """)
            avg_currency = cur.fetchone()[0] or 0
            
            st.metric("총 화폐량", f"{total_currency:,}원")
            st.metric("최고 보유량", f"{max_currency:,}원")
            st.metric("평균 보유량", f"{int(avg_currency):,}원")
        
        with col3:
            # Activity statistics
            try:
                cur.execute("""
                    SELECT COUNT(*) FROM transactions
                """)
                transaction_count = cur.fetchone()[0] or 0
                st.metric("총 거래 수", transaction_count)
            except:
                st.info("거래 정보가 없습니다.")
            
            try:
                cur.execute("""
                    SELECT COUNT(*) FROM blog_posts
                """)
                post_count = cur.fetchone()[0] or 0
                st.metric("총 게시글 수", post_count)
            except:
                st.info("게시글 정보가 없습니다.")
            
            try:
                cur.execute("""
                    SELECT COUNT(*) FROM blog_comments
                """)
                comment_count = cur.fetchone()[0] or 0
                st.metric("총 댓글 수", comment_count)
            except:
                pass
        
        # Activity over time
        st.subheader("시간별 활동")
        
        try:
            # Transactions by day
            cur.execute("""
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM transactions
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT 30
            """)
            
            transactions_by_day = cur.fetchall()
            
            if transactions_by_day:
                trans_df = pd.DataFrame(transactions_by_day, columns=["날짜", "거래 수"])
                trans_df = trans_df.sort_values("날짜")
                
                st.line_chart(trans_df.set_index("날짜"))
        except:
            st.info("거래 내역이 없습니다.")

    #-----------------------------------------------------------
    # 6. REFUND MANAGEMENT TAB
    #-----------------------------------------------------------
    with tabs[5]:
        st.header("💸 환불 관리")
        
        # Get all user items
        cur.execute("""
            SELECT ui.id, u.username, s.name, s.price, ui.purchased_at
            FROM user_items ui
            JOIN users u ON ui.user_id = u.user_id
            JOIN shop_items s ON ui.item_id = s.item_id
            WHERE ui.is_active = true
            ORDER BY ui.purchased_at DESC
        """)
        user_items = cur.fetchall()
        
        if not user_items:
            st.info("환불 가능한 아이템이 없습니다.")
        else:
            for item in user_items:
                with st.expander(f"{item[1]} - {item[2]} (구매일: {item[4]})"):
                    st.write(f"구매 금액: {item[3]}")
                    
                    # Refund form
                    with st.form(f"refund_form_{item[0]}"):
                        reason = st.text_input("환불 사유", key=f"refund_reason_{item[0]}")
                        submit = st.form_submit_button("환불 처리")
                        
                        if submit:
                            if reason:
                                try:
                                    # Start transaction
                                    cur.execute("BEGIN")
                                    
                                    # Get user_id and item_id
                                    cur.execute("SELECT user_id, item_id FROM user_items WHERE id = %s", (item[0],))
                                    user_item = cur.fetchone()
                                    
                                    if user_item:  # Ensure user_item exists
                                        # Add refund record
                                        cur.execute("""
                                            INSERT INTO refunds (user_item_id, user_id, item_id, amount, reason, processed_by)
                                            VALUES (%s, %s, %s, %s, %s, %s)
                                        """, (item[0], user_item[0], user_item[1], item[3], reason, user_id))
                                        
                                        # Update user's currency
                                        cur.execute("""
                                            UPDATE users 
                                            SET currency = currency + %s 
                                            WHERE user_id = %s
                                        """, (item[3], user_item[0]))
                                        
                                        # Deactivate user item
                                        cur.execute("""
                                            UPDATE user_items 
                                            SET is_active = false 
                                            WHERE id = %s
                                        """, (item[0],))
                                        
                                        # Add transaction record
                                        cur.execute("""
                                            INSERT INTO transactions (from_user_id, to_user_id, amount, type, description, created_by)
                                            VALUES (%s, %s, %s, %s, %s, %s)
                                        """, (user_id, user_item[0], item[3], 'refund', reason, user_id))
                                        
                                        # Commit transaction
                                        cur.execute("COMMIT")
                                        st.success(f"{item[2]} 아이템이 환불되었습니다.")
                                        st.rerun()
                                    else:
                                        cur.execute("ROLLBACK")
                                        st.error("아이템 정보를 찾을 수 없습니다.")
                                except Exception as e:
                                    cur.execute("ROLLBACK")
                                    st.error(f"환불 처리 중 오류 발생: {str(e)}")
                            else:
                                st.error("환불 사유를 입력해주세요.")

    #-----------------------------------------------------------
    # 7. NOTICE MANAGEMENT TAB
    #-----------------------------------------------------------
    with tabs[6]:
        st.header("📢 공지 관리")
        
        # Add new notice
        st.subheader("새 공지 작성")
        with st.form("add_notice_form"):
            notice_title = st.text_input("제목")
            notice_content = st.text_area("내용")
            heading_level = st.selectbox("제목 크기", [1, 2, 3, 4, 5, 6], format_func=lambda x: f"H{x}")
            submit = st.form_submit_button("공지 등록")
            
            if submit:
                if notice_title and notice_content:
                    try:
                        cur.execute(
                            """
                            INSERT INTO notices (title, content, heading_level, created_by)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (notice_title, notice_content, heading_level, user_id)
                        )
                        conn.commit()
                        st.success("공지가 등록되었습니다.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"공지 등록 중 오류 발생: {str(e)}")
                else:
                    st.error("제목과 내용을 모두 입력해주세요.")
        
        # List and manage existing notices
        st.subheader("공지 목록")
        try:
            cur.execute("""
                SELECT notice_id, title, content, heading_level, is_active, created_at, updated_at
                FROM notices
                ORDER BY created_at DESC
            """)
            notices = cur.fetchall()
            
            if not notices:
                st.info("등록된 공지가 없습니다.")
            else:
                for notice in notices:
                    with st.expander(f"{notice[1]} (작성일: {notice[5]})"):
                        st.write(f"제목 크기: H{notice[3]}")
                        st.write(f"상태: {'활성' if notice[4] else '비활성'}")
                        st.write(f"최종 수정일: {notice[6]}")
                        st.write("내용:")
                        st.write(notice[2])
                        
                        # Edit notice
                        with st.form(f"edit_notice_{notice[0]}"):
                            edit_title = st.text_input("제목 수정", value=notice[1], key=f"edit_title_{notice[0]}")
                            edit_content = st.text_area("내용 수정", value=notice[2], key=f"edit_content_{notice[0]}")
                            edit_heading = st.selectbox(
                                "제목 크기 수정",
                                [1, 2, 3, 4, 5, 6],
                                index=notice[3]-1,
                                format_func=lambda x: f"H{x}",
                                key=f"edit_heading_{notice[0]}"
                            )
                            edit_active = st.checkbox("활성화", value=notice[4], key=f"edit_active_{notice[0]}")
                            submit_edit = st.form_submit_button("수정")
                            
                            if submit_edit:
                                if edit_title and edit_content:
                                    try:
                                        cur.execute(
                                            """
                                            UPDATE notices 
                                            SET title = %s, content = %s, heading_level = %s, 
                                                is_active = %s, updated_at = CURRENT_TIMESTAMP
                                            WHERE notice_id = %s
                                            """,
                                            (edit_title, edit_content, edit_heading, edit_active, notice[0])
                                        )
                                        conn.commit()
                                        st.success("공지가 수정되었습니다.")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"공지 수정 중 오류 발생: {str(e)}")
                                else:
                                    st.error("제목과 내용을 모두 입력해주세요.")
                        
                        # Delete notice
                        if st.button("삭제", key=f"delete_notice_{notice[0]}"):
                            try:
                                cur.execute("DELETE FROM notices WHERE notice_id = %s", (notice[0],))
                                conn.commit()
                                st.success("공지가 삭제되었습니다.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"공지 삭제 중 오류 발생: {str(e)}")
        except Exception as e:
            st.error(f"공지 목록을 불러오는 중 오류가 발생했습니다: {str(e)}")

except Exception as e:
    st.error(f"오류가 발생했습니다: {str(e)}")
    st.write("Debug - Error Details:", e) 