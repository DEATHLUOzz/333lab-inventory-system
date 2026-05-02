import streamlit as st
import time
from utils import load_json, save_json, gen_qrcode, init_files

init_files()
# render_sidebar_auth()

st.title("实验室物品借用系统")

# 🆕 增加权限锁
if not st.session_state.logged_in_manager:
    st.error("🔒 仅管理员可录入新物品")
else:
    st.subheader("新增物品（自动生成唯一条码）")
    item_name = st.text_input("物品名称")
    remark = st.text_input("备注（选填）")

    if st.button("生成物品 + 二维码"):
        if not item_name:
            st.warning("请输入物品名称")
        else:
            items = load_json("items.json")
            
            # 禁止同名
            name_exists = any(it["item_name"] == item_name for it in items)
            if name_exists:
                st.error(f"物品名称【{item_name}】已存在，不允许重复录入！")
            else:
                item_id = f"ITEM{int(time.time())}"
                items.append({
                    "item_id": item_id,
                    "item_name": item_name,
                    "remark": remark,
                    "status": "空闲",
                    
                    "user": None,
                    "user_id": None,
                    "user_class": None,
                    "user_source": None,
                    "usage": None,
                    "take_time": None,
                    "due_date": None
                })
                save_json("items.json", items)
                img = gen_qrcode(item_id)
                st.success(f"物品 {item_id} 录入成功")
                st.image(img, width=250)