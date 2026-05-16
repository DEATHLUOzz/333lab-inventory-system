import streamlit as st

from utils import handle_redirect, load_json


def get_scanned_item_id():
    return (
        st.query_params.get("item_id", "")
        or st.session_state.get("goto_item_id", "")
    ).strip()


st.set_page_config(page_title="物品详情", page_icon="📦", layout="wide")

st.title("物品详情")
st.subheader("通过手机微信扫一扫物品二维码后，可查看物品详情；未入库的二维码可继续录入。")
st.markdown("---")

scanned_item_id = get_scanned_item_id()

if scanned_item_id:
    st.session_state["er_wei_ma_input"] = scanned_item_id
    st.session_state["current_item_id"] = scanned_item_id
elif "er_wei_ma_input" not in st.session_state:
    st.session_state["er_wei_ma_input"] = ""

if "current_item_id" not in st.session_state:
    st.session_state["current_item_id"] = ""

input_item_id = st.text_input("扫码物品ID", key="er_wei_ma_input").strip()
if st.button("查询", use_container_width=True):
    st.session_state["current_item_id"] = input_item_id

item_id = st.session_state.get("current_item_id", "").strip()

if not item_id:
    st.info("请用微信扫一扫物品二维码，或手动输入物品ID。")
    st.stop()

st.markdown("---")
items = load_json("items.json")
item = next((it for it in items if it.get("item_id") == item_id), None)

if item is None:
    printed_qrs = load_json("printed_qrs.json")
    qr_found = any(qr.get("item_id") == item_id for qr in printed_qrs)

    if qr_found:
        st.warning(f"二维码 {item_id} 已生成，但这个物品还没有入库。")
        if st.session_state.get("logged_in_manager"):
            st.info("管理员可以继续录入这个二维码对应的物品名称。")
            if st.button("录入这个物品", type="primary", use_container_width=True):
                handle_redirect(goto="page3", params={"item_id": item_id})
        else:
            st.error("请使用管理员账号登录后再录入这个物品。")
    else:
        st.error("没有找到这个物品，也没有找到对应的二维码生成记录。请确认二维码是否由系统生成。")
    st.stop()

status = item.get("status", "")
username = item.get("username")

col1, col2 = st.columns([1, 2])

with col1:
    st.header("物品基本信息")
    st.info(f"**物品名称:** {item.get('item_name', '-')}")
    st.info(f"**物品ID:** {item.get('item_id', '-')}")
    st.info(f"**备注:** {item.get('remark', '-')}")
    st.success(f"**当前状态:** {status}")

with col2:
    st.header("当前使用信息")
    st.info(f"**用户ID:** {username or '-'}")
    st.warning(f"**用户姓名:** {item.get('name') or '-'}")
    st.info(f"**用户班级:** {item.get('user_class') or '-'}")
    st.info(f"**用户电话:** {item.get('user_phone') or '-'}")
    st.info(f"**使用用途:** {item.get('usage') or '-'}")
    st.info(f"**领用时间:** {item.get('take_time') or '-'}")
    st.info(f"**到期时间:** {item.get('due_date') or '-'}")

st.markdown("---")
st.header("操作")
col3, col4 = st.columns(2)

with col3:
    if st.button("借用", use_container_width=True):
        if status == "使用中":
            st.error("物品已借出，请勿重复借出。")
        else:
            handle_redirect(goto="page1", params={"item_id": item_id})

with col4:
    if st.button("归还", use_container_width=True):
        if status == "空闲":
            st.error("物品当前为空闲状态，无需归还。")
        elif username != st.session_state.get("user"):
            st.error("您不是当前物品的领用人，无法归还。")
        else:
            handle_redirect(goto="page2", params={"item_id": item_id})
