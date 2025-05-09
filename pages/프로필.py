import streamlit as st
from libs.db import get_conn
from libs.currency import get_user_currency
import psycopg2
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image

st.title("👤 프로필 관리")

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
    cur.execute("""
        SELECT username, role, currency, 
               CASE WHEN EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name = 'users' AND column_name = 'bio')
                    THEN bio ELSE '' END as bio,
               CASE WHEN EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name = 'users' AND column_name = 'avatar_url')
                    THEN avatar_url ELSE '' END as avatar_url,
               job_id
        FROM users 
        WHERE user_id = %s
    """, (user_id,))
    
    user_data = cur.fetchone()
    if not user_data:
        st.error("사용자 정보를 찾을 수 없습니다.")
        st.stop()
    
    username, role, currency, bio, avatar_url, job_id = user_data
    
    # Get user's equipped items
    cur.execute("""
        SELECT i.type, i.image_url
        FROM user_items ui
        JOIN shop_items i ON ui.item_id = i.item_id
        WHERE ui.user_id = %s AND ui.is_equipped = TRUE
    """, (user_id,))
    
    equipped_items = {item_type: url for item_type, url in cur.fetchall()}
    
    # Main profile display
    col1, col2 = st.columns([1, 3])
    
    with col1:
        # Display the user's avatar (or default)
        avatar_to_show = equipped_items.get('avatar') if 'avatar' in equipped_items else avatar_url
        if avatar_to_show:
            st.image(avatar_to_show, width=150)
        else:
            st.image("https://i.imgur.com/qPPI5t2.png", width=150)  # Default avatar
            
        # Display badges if any
        if 'badge' in equipped_items:
            st.image(equipped_items['badge'], width=100)
    
    with col2:
        # Background style if equipped
        bg_style = ""
        if 'background' in equipped_items:
            bg_style = f"background-image: url({equipped_items['background']}); background-size: cover; padding: 20px; border-radius: 10px;"
        
        # Font style if equipped
        font_style = ""
        if 'font' in equipped_items:
            # Different fonts based on equipped font item
            font_families = {
                "귀여운 폰트": "Comic Sans MS, cursive",
                "댄디 폰트": "Georgia, serif"
            }
            # Default to a general font style
            font_style = "font-family: Arial, sans-serif;"
        
        # Text color if equipped
        color_style = ""
        if 'color' in equipped_items:
            # Different colors based on equipped color item
            colors = {
                "VIP 색상": "gold"
            }
            # Default to a general color style
            color_style = "color: #333;"
        
        # Combine all styles
        combined_style = f"{bg_style} {font_style} {color_style}"
        
        # Apply styles
        st.markdown(f"""
            <div style="{combined_style}">
                <h2>{username}</h2>
                <p>역할: {role}</p>
                <p>잔고: {currency:,}원</p>
                <p>소개: {bio if bio else '소개가 없습니다.'}</p>
            </div>
        """, unsafe_allow_html=True)
    
    # Get job information if user has a job
    if job_id:
        cur.execute("""
            SELECT name, salary, description
            FROM jobs
            WHERE job_id = %s
        """, (job_id,))
        job_data = cur.fetchone()
        if job_data:
            job_name, salary, job_description = job_data
            
            st.subheader("💼 직업 정보")
            st.write(f"직업: {job_name}")
            st.write(f"급여: {salary:,}원")
            st.write(f"설명: {job_description}")
    
    # Edit profile section
    st.subheader("⚙️ 프로필 수정")
    
    with st.form("profile_edit"):
        new_bio = st.text_area("자기소개", value=bio if bio else "")
        
        # Custom avatar URL
        new_avatar_url = st.text_input("아바타 URL (비워두면 장착한 아바타 아이템이 사용됩니다)", 
                                      value=avatar_url if avatar_url else "")
        
        # Upload avatar image
        uploaded_file = st.file_uploader("아바타 이미지 업로드", type=["jpg", "jpeg", "png"])
        
        submit = st.form_submit_button("프로필 업데이트")
        
        if submit:
            try:
                # Process uploaded file if any
                if uploaded_file is not None:
                    # Convert the file to base64 for storage
                    # In a real application, you'd likely store this in a cloud storage service
                    image = Image.open(uploaded_file)
                    image = image.resize((150, 150))  # Resize for consistency
                    buffered = BytesIO()
                    image.save(buffered, format="PNG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    new_avatar_url = f"data:image/png;base64,{img_str}"
                
                # Update profile in database
                cur.execute("""
                    UPDATE users
                    SET bio = %s, avatar_url = %s
                    WHERE user_id = %s
                """, (new_bio, new_avatar_url, user_id))
                
                conn.commit()
                st.success("프로필이 업데이트되었습니다!")
                st.rerun()
            except Exception as e:
                conn.rollback()
                st.error(f"프로필 업데이트 중 오류가 발생했습니다: {str(e)}")
    
    # Equipped items display
    st.subheader("🎨 장착한 아이템")
    
    if not equipped_items:
        st.info("장착한 아이템이 없습니다. 상점에서 아이템을 구매하고 장착해보세요!")
    else:
        equipped_cols = st.columns(len(equipped_items))
        for i, (item_type, image_url) in enumerate(equipped_items.items()):
            with equipped_cols[i]:
                st.write(f"유형: {item_type}")
                st.image(image_url, width=100)
    
    # Activity history
    st.subheader("📊 활동 내역")
    
    # Transactions
    with st.expander("💰 거래 내역"):
        cur.execute("""
            SELECT t.amount, t.type, t.description, t.created_at,
                   CASE 
                       WHEN t.from_user_id = %s THEN '출금'
                       ELSE '입금'
                   END as direction,
                   CASE
                       WHEN t.from_user_id = %s THEN u.username
                       ELSE u2.username
                   END as other_user
            FROM transactions t
            LEFT JOIN users u ON t.to_user_id = u.user_id
            LEFT JOIN users u2 ON t.from_user_id = u2.user_id
            WHERE t.from_user_id = %s OR t.to_user_id = %s
            ORDER BY t.created_at DESC
            LIMIT 10
        """, (user_id, user_id, user_id, user_id))
        
        transactions = cur.fetchall()
        if transactions:
            for amount, t_type, description, created_at, direction, other_user in transactions:
                if direction == '출금':
                    st.write(f"🔴 {created_at.strftime('%Y-%m-%d %H:%M')} - {amount:,}원 {direction} - {description} → {other_user if other_user else '시스템'}")
                else:
                    st.write(f"🟢 {created_at.strftime('%Y-%m-%d %H:%M')} - {amount:,}원 {direction} - {description} ← {other_user if other_user else '시스템'}")
        else:
            st.info("거래 내역이 없습니다.")
    
    # Quests completed
    with st.expander("🎯 완료한 퀘스트"):
        cur.execute("""
            SELECT q.title, q.reward, qc.completed_at, qc.verified_at, u.username
            FROM quest_completions qc
            JOIN quests q ON qc.quest_id = q.quest_id
            LEFT JOIN users u ON qc.verified_by = u.user_id
            WHERE qc.user_id = %s
            ORDER BY qc.completed_at DESC
        """, (user_id,))
        
        quests = cur.fetchall()
        if quests:
            for title, reward, completed_at, verified_at, verifier in quests:
                verification_status = f"✅ 인증됨 ({verifier})" if verified_at else "⏳ 인증 대기 중"
                st.write(f"{completed_at.strftime('%Y-%m-%d')} - {title} - {reward:,}원 - {verification_status}")
        else:
            st.info("완료한 퀘스트가 없습니다.")
    
    # Purchased items
    with st.expander("🛍️ 구매한 아이템"):
        cur.execute("""
            SELECT i.name, i.price, ui.purchased_at
            FROM user_items ui
            JOIN shop_items i ON ui.item_id = i.item_id
            WHERE ui.user_id = %s
            ORDER BY ui.purchased_at DESC
        """, (user_id,))
        
        items = cur.fetchall()
        if items:
            for name, price, purchased_at in items:
                st.write(f"{purchased_at.strftime('%Y-%m-%d')} - {name} - {price:,}원")
        else:
            st.info("구매한 아이템이 없습니다.")

except Exception as e:
    st.error(f"오류가 발생했습니다: {str(e)}")
    st.write("Debug - Error Details:", e) 