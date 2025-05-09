import streamlit as st
from libs.db import get_conn
import base64
from io import BytesIO
from PIL import Image
from datetime import datetime
import json

st.title("📝 교실 블로그")

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
    
    # Get user information
    cur.execute("SELECT username, role FROM users WHERE user_id = %s", (user_id,))
    username, role = cur.fetchone()
    
    # Create new post form
    st.subheader("✏️ 새 글 작성")
    
    with st.form("new_post_form"):
        post_title = st.text_input("제목")
        post_content = st.text_area("내용")
        
        # File uploader for images
        uploaded_files = st.file_uploader("이미지 첨부", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        
        submit = st.form_submit_button("게시하기")
        
        if submit:
            if not post_title or not post_content:
                st.error("제목과 내용을 모두 입력해주세요.")
            else:
                try:
                    # Process uploaded images
                    image_urls = []
                    
                    if uploaded_files:
                        for uploaded_file in uploaded_files:
                            # Process image
                            image = Image.open(uploaded_file)
                            
                            # Resize if needed (optional)
                            max_size = (800, 800)
                            image.thumbnail(max_size)
                            
                            # Convert to base64
                            buffered = BytesIO()
                            image.save(buffered, format="PNG")
                            img_str = base64.b64encode(buffered.getvalue()).decode()
                            image_url = f"data:image/png;base64,{img_str}"
                            image_urls.append(image_url)
                    
                    # Insert post into database
                    cur.execute("""
                        INSERT INTO blog_posts (user_id, title, content, image_urls)
                        VALUES (%s, %s, %s, %s)
                        RETURNING post_id
                    """, (user_id, post_title, post_content, image_urls if image_urls else None))
                    
                    post_id = cur.fetchone()[0]
                    conn.commit()
                    
                    st.success("게시글이 작성되었습니다!")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"게시글 작성 중 오류가 발생했습니다: {str(e)}")
    
    # Display blog posts
    st.subheader("📰 최근 게시글")
    
    # Get all posts with author info
    cur.execute("""
        SELECT p.post_id, p.title, p.content, p.image_urls, p.created_at, u.username, u.role
        FROM blog_posts p
        JOIN users u ON p.user_id = u.user_id
        ORDER BY p.created_at DESC
    """)
    
    posts = cur.fetchall()
    
    if not posts:
        st.info("아직 게시글이 없습니다. 첫 번째 글을 작성해보세요!")
    else:
        for post_id, title, content, image_urls, created_at, author, author_role in posts:
            with st.expander(f"{title} - by {author} ({created_at.strftime('%Y-%m-%d %H:%M')})"):
                st.write(content)
                
                # Display images if any
                if image_urls:
                    # Display images in a horizontal layout
                    cols = st.columns(min(len(image_urls), 3))
                    for i, img_url in enumerate(image_urls):
                        with cols[i % 3]:
                            st.image(img_url)
                
                # Comments section
                st.subheader("💬 댓글")
                
                # Get comments for this post
                cur.execute("""
                    SELECT c.content, c.created_at, u.username
                    FROM blog_comments c
                    JOIN users u ON c.user_id = u.user_id
                    WHERE c.post_id = %s
                    ORDER BY c.created_at
                """, (post_id,))
                
                comments = cur.fetchall()
                
                if comments:
                    for comment, comment_time, comment_author in comments:
                        st.markdown(f"""
                            <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                                <p><strong>{comment_author}</strong> • {comment_time.strftime('%Y-%m-%d %H:%M')}</p>
                                <p>{comment}</p>
                            </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("아직 댓글이 없습니다.")
                
                # Add comment form
                with st.form(f"comment_form_{post_id}"):
                    comment_content = st.text_area("댓글 작성", key=f"comment_{post_id}")
                    comment_submit = st.form_submit_button("댓글 달기")
                    
                    if comment_submit:
                        if not comment_content:
                            st.error("댓글 내용을 입력해주세요.")
                        else:
                            try:
                                cur.execute("""
                                    INSERT INTO blog_comments (post_id, user_id, content)
                                    VALUES (%s, %s, %s)
                                """, (post_id, user_id, comment_content))
                                
                                conn.commit()
                                st.success("댓글이 작성되었습니다!")
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"댓글 작성 중 오류가 발생했습니다: {str(e)}")
                
                # Delete post option (only for author or teacher)
                cur.execute("SELECT user_id FROM blog_posts WHERE post_id = %s", (post_id,))
                post_author_id = cur.fetchone()[0]
                if user_id == post_author_id or role in ['teacher', '제작자']:
                    if st.button(f"게시글 삭제", key=f"delete_{post_id}"):
                        try:
                            # Delete comments first
                            cur.execute("DELETE FROM blog_comments WHERE post_id = %s", (post_id,))
                            
                            # Then delete the post
                            cur.execute("DELETE FROM blog_posts WHERE post_id = %s", (post_id,))
                            
                            conn.commit()
                            st.success("게시글이 삭제되었습니다!")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"게시글 삭제 중 오류가 발생했습니다: {str(e)}")

except Exception as e:
    st.error(f"오류가 발생했습니다: {str(e)}")
    st.write("Debug - Error Details:", e) 