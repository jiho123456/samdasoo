import streamlit as st
import pandas as pd
from libs.ui_helpers import header

header()
st.header("👥 우리 반 명단")
data = {
    "번호": list(range(1,29)),
    "이름":[
      "김도현","김상준","","","김시연","김윤우","김은솔","","","",
      "","서민성","송선우","","신희건","안준우","양지호","","","",
      "","","","","","","","황라윤"
    ]
}
df = pd.DataFrame(data)
st.table(df)
if st.button("새로고침"):
    st.rerun()
