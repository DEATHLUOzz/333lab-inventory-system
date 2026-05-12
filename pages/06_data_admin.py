import streamlit as st
import pandas as pd
from utils import (
    load_json, save_json, init_files, 
    generate_excel_backup
)

init_files()
# render_sidebar_auth()

st.title("实验室物品借用系统")

if not st.session_state.logged_in_manager:
    st.error("仅管理员可查看")
else:
    st.subheader("数据管理中心")

    # ===================== 1. Excel 导出功能 =====================
    st.markdown("### 1. 导出 Excel 备份")
    st.info("点击下方按钮生成包含【物品清单】、【人员档案】、【借用流水】的 Excel 文件。")
    
    if st.button("生成并下载 Excel"):
        with st.spinner("正在生成报表..."):
            excel_data = generate_excel_backup()
            
            st.download_button(
                label="下载 backup.xlsx",
                data=excel_data,
                file_name=f"lab_backup_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    st.divider()

    # ===================== 2. 人员信息查询与修改 =====================
    st.markdown("### 2. 人员档案管理")
    
    users = load_json("user_logging.json")
    if not users:
        st.info("暂无人员档案")
    else:
        # 搜索框
        search_id = st.text_input("按用户名搜索：")
        
        target_user = None
        if search_id:
            target_user = next((u for u in users if u['username'] == search_id), None)
            if not target_user:
                st.warning("未找到该人员")
        
        # 显示列表或搜索结果
        display_list = [target_user] if target_user else users
        
        for u in display_list:
            if not u: continue
            with st.expander(f"👤 {u['name']} (ID: {u['username']})"):
                # st.write(f"**来源**: {u['source']}")
                # 可编辑字段
                new_name = st.text_input("姓名", u['name'], key=f"name_{u['username']}")
                new_class = st.text_input("班级/单位", u['class'], key=f"cls_{u['username']}")
                new_phone = st.text_input("手机号", u['phone'], key=f"phone_{u['username']}")
                
                if st.button("更新人员信息", key=f"save_{u['username']}"):
                    # 回写数据
                    all_users = load_json("user_logging.json")
                    for idx, user_in_list in enumerate(all_users):
                        if user_in_list['username'] == u['username']:
                            all_users[idx]['name'] = new_name
                            all_users[idx]['class'] = new_class
                            all_users[idx]['phone'] = new_phone
                            break
                    save_json("user_logging.json", all_users)
                    st.success("人员信息已更新")
                    st.rerun()