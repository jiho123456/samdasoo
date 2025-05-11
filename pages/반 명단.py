import streamlit as st
import pandas as pd
from libs.ui_helpers import header

header()
st.header("👥 우리 반 명단")

# Get stored class roster from session state or initialize with default data
if 'class_roster' not in st.session_state:
    st.session_state.class_roster = {
        "번호": list(range(1, 29)),
        "이름": [
            "김도현", "김상준", "", "", "김시연", "김윤우", "김은솔", "", "", "",
            "", "서민성", "송선우", "", "신희건", "안준우", "양지호", "", "", "",
            "", "", "", "", "", "", "", "황라윤"
        ]
    }

# Display the current roster
df = pd.DataFrame(st.session_state.class_roster)
st.table(df)

# Add edit mode
if st.button("편집 모드 전환", key="toggle_edit"):
    st.session_state.edit_mode = not st.session_state.get('edit_mode', False)
    st.rerun()

# Show editable form in edit mode
if st.session_state.get('edit_mode', False):
    st.subheader("명단 편집")
    st.write("각 번호의 이름을 수정할 수 있습니다.")
    
    # Create a form for editing names
    with st.form("edit_roster_form"):
        # Create a dictionary to store the edited values
        edited_names = {}
        
        # Create 4 columns with 7 students each (total 28 students)
        cols = st.columns(4)
        for i in range(28):
            col_idx = i // 7
            with cols[col_idx]:
                student_num = i + 1
                original_name = st.session_state.class_roster["이름"][i] if i < len(st.session_state.class_roster["이름"]) else ""
                edited_names[student_num] = st.text_input(f"{student_num}번", value=original_name, key=f"student_{student_num}")
        
        # Submit button
        submitted = st.form_submit_button("저장")
        if submitted:
            # Update the class roster
            updated_names = []
            for i in range(1, 29):
                updated_names.append(edited_names.get(i, ""))
            
            st.session_state.class_roster["이름"] = updated_names
            st.session_state.edit_mode = False
            st.success("명단이 업데이트되었습니다!")
            st.rerun()

# Add a refresh button
if st.button("새로고침"):
    st.rerun()
