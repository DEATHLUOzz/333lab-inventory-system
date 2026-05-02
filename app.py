
import streamlit as st
import time
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils import (
    init_files,  
    load_json, 
    check_near_expiry,
    login,
    render_alerts,
    goto_page,
    handle_redirect,
)

init_files()
print("现在在app.py")
print("【刚进页面】原始参数:", st.query_params)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "logged_in_manager" not in st.session_state:
    st.session_state.logged_in_manager = False


login_page = st.Page(login, title="登录")
pg = st.navigation([login_page])


# 默认只有login页面

if st.session_state.logged_in:
    page1 = st.Page("pages\\01_item_checkout.py", title="01_扫码领用")
    page2 = st.Page("pages\\02_item_checkin.py", title="02_扫码归还")
    page7 = st.Page("pages\\er_wei_ma_chuanjianziwangye.py", title="07_物品详情")
    page3 = st.Page("pages\\03_item_registratio.py", title="03_录入新物品")
    page4 = st.Page("pages\\04_item_inventory.py", title="04_物品总览")
    page5 = st.Page("pages\\05_transaction_logs.py", title="05_借用记录")
    page6 = st.Page("pages\\06_data_admin.py", title="06_数据备份管理")

    pg = st.navigation({"主要功能": [page1, page2, page7], "管理员功能": [page3, page4, page5, page6] if st.session_state.logged_in_manager else []})
# if st.session_state.logged_in_manager:
#     render_alerts()
    #判定是都是扫码进入，是跳转页面。并标记跳转过
    print (f"app_query_params: {st.query_params}")
    print(f"app_item_id: {st.query_params.get('item_id', '')}")
    print(f"app_goto: {st.query_params.get('goto', '')}")
    if st.query_params.get("goto","") == "page7":
        handle_redirect(goto = "page7",params = {"item_id":st.query_params.get("item_id","")})


pg.run()
