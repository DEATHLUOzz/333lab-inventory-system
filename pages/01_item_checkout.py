import streamlit as st
import time
from datetime import datetime
from utils import (
    load_json, save_json, init_files, 
    INTERNAL_STAFF_PASSWORD, is_valid_phone, get_or_create_user
)

init_files()
# render_sidebar_auth()

st.title("实验室物品借用系统")
st.subheader("扫码领用物品")

# if "item_id_input" not in st.session_state:
#     st.session_state.item_id_input = ""


item_id = st.text_input("商品ID", key="goto_item_id")

if "user_source" not in st.session_state:
    st.session_state.user_source = "实验室内部人员"

user_source = st.radio(
    "人员来源", 
    ["实验室内部人员", "外来人员"], 
    key="user_source",
    horizontal=True
)

user_name = st.text_input("姓名")
due_date = st.date_input("预计归还日期", min_value=datetime.now())
usage = st.text_area("用途说明")

# 🆕 重构表单逻辑：两边都要填班级和手机
col1, col2 = st.columns(2)
user_class = col1.text_input("班级/单位")
user_phone = col2.text_input("手机号 (11位数字)")

# 只有内部人员需要密码
internal_pwd = None
if user_source == "实验室内部人员":
    internal_pwd = st.text_input("内部人员核验密码", type="password")

if st.button("确认领用"):
    # 1. 基础校验
    if not item_id or not user_name:
        st.error("请扫码并填写姓名")
    elif not usage:
        st.error("请填写用途说明")
    elif not user_class or not user_phone:
        st.error("请填写完整的班级/单位和手机号")
    elif not is_valid_phone(user_phone):
        st.error("手机号格式不正确，请输入11位数字")
    elif user_source == "实验室内部人员" and internal_pwd != INTERNAL_STAFF_PASSWORD:
        st.error("内部人员核验密码错误！")
    else:
        # 2. 业务逻辑
        user_id = user_phone # 🆕 直接使用手机号作为人员ID
        
        # 🆕 先把人员存入库（如果不存在）
        get_or_create_user(user_id, user_name, user_class, user_source)

        items = load_json("items.json")
        logs = load_json("logs.json")

        item_found = None
        for i, it in enumerate(items):
            if it["item_id"] == item_id:
                item_found = i
                break

        if item_found is None:
            st.error("无此物品")
        elif items[item_found]["status"] == "使用中":
            st.warning("此物品已被借用")
        else:
            # 更新物品状态
            items[item_found]["user"] = user_name
            items[item_found]["user_id"] = user_id # 🆕 存ID
            items[item_found]["user_class"] = user_class # 🆕 存班级
            items[item_found]["user_source"] = user_source
            items[item_found]["usage"] = usage
            items[item_found]["take_time"] = time.strftime("%Y-%m-%d %H:%M")
            items[item_found]["due_date"] = due_date.strftime("%Y-%m-%d")
            items[item_found]["status"] = "使用中"
            save_json("items.json", items)

            # 记录日志
            logs.append({
                "type": "领用",
                "item_id": item_id,
                "item_name": items[item_found]["item_name"],
                "user_id": user_id, # 🆕
                "user_name": user_name,
                "user_class": user_class, # 🆕
                "user_source": user_source,
                "usage": usage,
                "time": time.strftime("%Y-%m-%d %H:%M"),
                "due_date": due_date.strftime("%Y-%m-%d")
            })
            save_json("logs.json", logs)
            st.success(f"{user_name} (ID:{user_id}) 成功领用 {items[item_found]['item_name']}")