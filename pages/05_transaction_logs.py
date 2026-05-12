import streamlit as st
import pandas as pd
from utils import load_json, init_files

init_files()
# render_sidebar_auth()

st.title("实验室物品借用系统")

if not st.session_state.logged_in_manager:
    st.error("仅管理员可查看")
else:
    st.subheader("借用记录审计")
    logs = load_json("logs.json")
    
    if not logs:
        st.info("暂无记录")
    else:
        # 反转列表，最新的在最上面
        logs_reversed = list(reversed(logs))
        
        # 转为 DataFrame
        df = pd.DataFrame(logs_reversed)
        
        # 🆕 增加筛选器
        col1, col2 = st.columns(2)
        with col1:
            type_filter = st.multiselect("筛选操作类型", options=df['type'].unique(), default=df['type'].unique())
        # with col2:
        #     if 'user_source' in df.columns:
        #         source_filter = st.multiselect("筛选人员来源", options=df['user_source'].unique(), default=df['user_source'].unique())
        #     else:
        #         source_filter = []

        # 应用筛选
        filtered_df = df[df['type'].isin(type_filter)]
        # if source_filter and 'user_source' in filtered_df.columns:
        #     filtered_df = filtered_df[filtered_df['user_source'].isin(source_filter)]

        # 显示表格
        st.dataframe(filtered_df, use_container_width=True)