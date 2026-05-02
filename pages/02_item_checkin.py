import streamlit as st
import time
from utils import load_json, save_json, init_files

init_files()
# render_sidebar_auth()

st.title("实验室物品借用系统")
st.subheader("扫码归还物品")

item_id = st.text_input("扫码物品ID").strip()

if st.button("确认归还"):
    if not item_id:
        st.warning("请扫码")
    else:
        items = load_json("items.json")
        logs = load_json("logs.json")

        item_found = None
        for i, it in enumerate(items):
            if it["item_id"] == item_id:
                item_found = i
                break

        if item_found is None:
            st.error("无此物品")
        elif items[item_found]["status"] == "空闲":
            st.warning("物品本来就是空闲状态")
        else:
            user = items[item_found]["user"]
            items[item_found]["user"] = None
            items[item_found]["take_time"] = None
            items[item_found]["status"] = "空闲"
            items[item_found]["user_id"] = None # 🆕 存ID
            items[item_found]["user_class"] = None # 🆕 存班级
            items[item_found]["user_source"] = None
            items[item_found]["usage"] = None
            items[item_found]["due_date"] = None
            save_json("items.json", items)

            logs.append({
                "type": "归还",
                "item_id": item_id,
                "item_name": items[item_found]["item_name"],
                "user": user,
                "time": time.strftime("%Y-%m-%d %H:%M")
            })
            save_json("logs.json", logs)
            st.success(f"{items[item_found]['item_name']} 已归还")