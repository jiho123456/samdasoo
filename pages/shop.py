import streamlit as st
from libs.db import get_conn
from libs.currency import get_user_currency
import psycopg2
from datetime import datetime

st.title("🛍️ 프로필 아이템 상점")

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
    
    # Get user balance
    balance = get_user_currency(user_id)
    st.metric("내 잔고", f"{balance:,}원")
    
    # Check if shop_items table exists
    cur.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'shop_items'
        )
    """)
    
    table_exists = cur.fetchone()[0]
    if not table_exists:
        st.warning("상점 시스템이 아직 준비되지 않았습니다. 데이터베이스 초기화가 필요합니다.")
        st.stop()
    
    # Initialize the shop with default items if none exist
    cur.execute("SELECT COUNT(*) FROM shop_items")
    if cur.fetchone()[0] == 0:
        # Only teachers and admins can add items
        if st.session_state.get('role') in ['teacher', '제작자']:
            st.info("상점에 아이템이 없습니다. 몇 가지 기본 아이템을 추가할까요?")
            if st.button("기본 아이템 추가"):
                # Add some default avatars
                default_items = [
                    ("고양이 아바타", "귀여운 고양이 아바타입니다.", "avatar", 100, "https://i.imgur.com/9LFtH1T.png"),
                    ("강아지 아바타", "충성스러운 강아지 아바타입니다.", "avatar", 100, "https://i.imgur.com/H9SbJRO.png"),
                    ("펭귄 아바타", "시원한 펭귄 아바타입니다.", "avatar", 150, "https://i.imgur.com/u2b02Th.png"),
                    ("황금 테두리", "프로필에 황금색 테두리를 추가합니다.", "badge", 200, "https://i.imgur.com/1abgIrY.png"),
                    ("빛나는 배경", "프로필에 빛나는 배경을 추가합니다.", "background", 300, "https://i.imgur.com/zBGt5KM.png"),
                    ("별 배지", "특별한 별 모양 배지입니다.", "badge", 250, "https://i.imgur.com/LJnzBbZ.png"),
                    ("VIP 색상", "이름을 VIP 색상으로 변경합니다.", "color", 500, "https://i.imgur.com/pZQCnbd.png"),
                    ("우주 배경", "우주 테마 배경입니다.", "background", 400, "https://i.imgur.com/JN5QgbH.png"),
                    ("귀여운 폰트", "귀여운 폰트로 텍스트를 표시합니다.", "font", 150, "https://i.imgur.com/QA3SrWc.png"),
                    ("댄디 폰트", "댄디한 폰트로 텍스트를 표시합니다.", "font", 150, "https://i.imgur.com/8Zn8X5m.png"),
                ]
                
                for name, desc, type_, price, img_url in default_items:
                    cur.execute(
                        "INSERT INTO shop_items (name, description, type, price, image_url) VALUES (%s, %s, %s, %s, %s)",
                        (name, desc, type_, price, img_url)
                    )
                
                conn.commit()
                st.success("기본 아이템이 추가되었습니다!")
                st.rerun()
        else:
            st.error("상점에 아이템이 없습니다. 선생님에게 문의하세요.")
            st.stop()
    
    # Teacher/Admin abilities to add new items
    if st.session_state.get('role') in ['teacher', '제작자']:
        with st.expander("🆕 새 아이템 추가"):
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("아이템 이름")
                new_description = st.text_area("아이템 설명")
                new_price = st.number_input("가격", min_value=1, step=1)
            
            with col2:
                new_type = st.selectbox("아이템 유형", 
                                        ["avatar", "badge", "background", "font", "color"],
                                        format_func=lambda x: {
                                            "avatar": "아바타",
                                            "badge": "배지",
                                            "background": "배경",
                                            "font": "폰트",
                                            "color": "색상"
                                        }.get(x, x))
                new_image_url = st.text_input("이미지 URL")
            
            if st.button("아이템 추가"):
                if new_name and new_description and new_price > 0:
                    try:
                        cur.execute(
                            "INSERT INTO shop_items (name, description, type, price, image_url) VALUES (%s, %s, %s, %s, %s)",
                            (new_name, new_description, new_type, new_price, new_image_url)
                        )
                        conn.commit()
                        st.success(f"'{new_name}' 아이템이 상점에 추가되었습니다!")
                    except Exception as e:
                        st.error(f"아이템 추가 중 오류가 발생했습니다: {str(e)}")
                else:
                    st.error("모든 필드를 입력해주세요.")
    
    # Display shop items by category
    st.subheader("🛒 아이템 구매")
    
    # Get all available shop items
    cur.execute("""
        SELECT item_id, name, description, type, price, image_url
        FROM shop_items
        ORDER BY type, price
    """)
    all_items = cur.fetchall()
    
    # Get user's purchased items
    cur.execute("""
        SELECT item_id FROM user_items
        WHERE user_id = %s
    """, (user_id,))
    purchased_items = [row[0] for row in cur.fetchall()]
    
    # Create tabs for each item category
    tabs = st.tabs(["전체", "아바타", "배지", "배경", "폰트", "색상"])
    
    # Filter function for items
    def filter_items(items, item_type=None):
        if item_type:
            return [item for item in items if item[3] == item_type]
        return items
    
    # Display items on each tab
    for i, tab_name in enumerate(["전체", "avatar", "badge", "background", "font", "color"]):
        with tabs[i]:
            filtered_items = all_items if i == 0 else filter_items(all_items, tab_name)
            
            if not filtered_items:
                st.info(f"현재 이 카테고리에는 아이템이 없습니다.")
                continue
            
            # Create a grid of items
            cols = st.columns(3)
            for idx, (item_id, name, description, item_type, price, image_url) in enumerate(filtered_items):
                with cols[idx % 3]:
                    st.subheader(name)
                    if image_url:
                        st.image(image_url, width=150)
                    st.write(description)
                    st.write(f"유형: {item_type}")
                    st.write(f"가격: {price:,}원")
                    
                    # Check if already purchased
                    if item_id in purchased_items:
                        st.success("구매 완료!")
                    else:
                        # Buy button
                        if st.button(f"구매하기", key=f"buy_{item_id}_{idx}_{tab_name}"):
                            # Check if user has enough currency
                            if balance >= price:
                                try:
                                    # Add to user's inventory
                                    cur.execute(
                                        "INSERT INTO user_items (user_id, item_id) VALUES (%s, %s)",
                                        (user_id, item_id)
                                    )
                                    
                                    # Deduct currency
                                    cur.execute(
                                        "UPDATE users SET currency = currency - %s WHERE user_id = %s",
                                        (price, user_id)
                                    )
                                    
                                    # Record transaction
                                    cur.execute(
                                        """
                                        INSERT INTO transactions 
                                        (from_user_id, to_user_id, amount, type, description, created_by)
                                        VALUES (%s, NULL, %s, 'transfer', %s, %s)
                                        """,
                                        (user_id, price, f"상점에서 '{name}' 아이템 구매", user_id)
                                    )
                                    
                                    conn.commit()
                                    st.success(f"'{name}' 아이템을 구매했습니다!")
                                    st.rerun()
                                except Exception as e:
                                    conn.rollback()
                                    st.error(f"구매 중 오류가 발생했습니다: {str(e)}")
                            else:
                                st.error("잔액이 부족합니다!")
                    st.markdown("---")
    
    # Display user's inventory
    st.subheader("🎒 내 인벤토리")
    
    # Get user's purchased items with details
    cur.execute("""
        SELECT i.item_id, i.name, i.description, i.type, i.image_url, ui.is_equipped
        FROM user_items ui
        JOIN shop_items i ON ui.item_id = i.item_id
        WHERE ui.user_id = %s
        ORDER BY ui.purchased_at DESC
    """, (user_id,))
    user_items = cur.fetchall()
    
    if not user_items:
        st.info("구매한 아이템이 없습니다.")
    else:
        inventory_tabs = st.tabs(["전체", "아바타", "배지", "배경", "폰트", "색상"])
        
        # Display items on each inventory tab
        for i, tab_name in enumerate(["전체", "avatar", "badge", "background", "font", "color"]):
            with inventory_tabs[i]:
                filtered_items = user_items if i == 0 else [item for item in user_items if item[3] == tab_name]
                
                if not filtered_items:
                    st.info(f"현재 이 카테고리에는 아이템이 없습니다.")
                    continue
                
                # Create a grid of items
                cols = st.columns(3)
                for idx, (item_id, name, description, item_type, image_url, is_equipped) in enumerate(filtered_items):
                    with cols[idx % 3]:
                        st.subheader(name)
                        if image_url:
                            st.image(image_url, width=150)
                        st.write(description)
                        
                        # Button to equip/unequip
                        button_text = "장착 해제하기" if is_equipped else "장착하기"
                        if st.button(button_text, key=f"equip_{item_id}_{idx}_{tab_name}"):
                            try:
                                # If equipping, unequip any other items of the same type first
                                if not is_equipped:
                                    cur.execute("""
                                        UPDATE user_items
                                        SET is_equipped = FALSE
                                        WHERE user_id = %s AND item_id IN (
                                            SELECT i.item_id
                                            FROM shop_items i
                                            JOIN user_items ui ON i.item_id = ui.item_id
                                            WHERE ui.user_id = %s AND i.type = %s
                                        )
                                    """, (user_id, user_id, item_type))
                                
                                # Toggle equipped status for this item
                                cur.execute("""
                                    UPDATE user_items
                                    SET is_equipped = NOT is_equipped
                                    WHERE user_id = %s AND item_id = %s
                                """, (user_id, item_id))
                                
                                conn.commit()
                                st.success(f"아이템을 {'장착 해제' if is_equipped else '장착'}했습니다!")
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"오류가 발생했습니다: {str(e)}")
                        st.markdown("---")

except Exception as e:
    st.error(f"오류가 발생했습니다: {str(e)}")
    st.write("Debug - Error Details:", e) 