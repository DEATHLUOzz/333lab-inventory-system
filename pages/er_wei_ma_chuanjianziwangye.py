import streamlit as st
from datetime import datetime
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils import load_json,IP_AND_HOST,handle_redirect

#http://192.168.3.23:8501/er_wei_ma_chuanjianziwangye?item_id=ITEM1777465443
print("现在在er_wei_ma_chuanjianziwangye.py")
st.set_page_config(
    page_title="物品详情",
    page_icon="📦",
    layout="wide"
)

st.title("📦 物品详情")
st.subheader("通过扫描物品二维码或输入物品ID查看物品详情，并可跳转到相关操作界面。")
st.markdown("---")

# 从 session_state 获取 item_id，默认为空字符串
# st.query_params["item_id"] = st.session_state.get("goto_item_id", "") # 初始化 query_params
# st.query_params = params

query_params = {"item_id": st.session_state.get("goto_item_id", "")} 
# print (f"st.Query Params: {st.query_params}")
# print (f"Query Params: {query_params}")

# 获取URL传递的参数(通常是二维码中的物品ID)

if query_params["item_id"]:
    # 获取物品ID(二维码内容)
    item_id = query_params["item_id"].strip()
    st.success("现在query_params为真")
else:
    item_id = ""
    input_item_id = st.text_input("扫码物品ID").strip()
    if st.button("查询", use_container_width=True):
        item_id = input_item_id
if item_id:
    st.success(f"✅ 已识别物品ID: **{item_id}**")
    st.markdown("---")
    #读取信息物品，及绑定人员信息
    items = load_json("items.json")
    item_found = None
    for i, it in enumerate(items):
        if it["item_id"] == item_id:
            item_found = i
            break
    if item_found is not None:
        item_id = items[item_found]["item_id"]
        item_name = items[item_found]["item_name"]
        remark = items[item_found]["remark"]
        user_name = items[item_found]["user"]
        user_id = items[item_found]["user_id"] # 🆕 存ID
        user_class = items[item_found]["user_class"] # 🆕 存班级
        user_source = items[item_found]["user_source"]
        usage = items[item_found]["usage"]
        take_time = items[item_found]["take_time"]
        due_date = items[item_found]["due_date"]
        status = items[item_found]["status"]
    # ==================== 显示物品信息 ====================
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.header("物品基本信息")
        st.info(f"**物品名称:** {item_name}")
        st.info(f"**物品id:** {item_id}")
        st.info(f"**物品备注:** {remark}")
        st.success(f"**当前状态:** {status}")
    
    with col2:
        st.header("用户基本信息")
        st.warning(f"**用户姓名:** {user_name}")
        st.info(f"**用户ID:** {user_id}")
        st.info(f"**用户班级:** {user_class}")
        st.info(f"**用户来源:** {user_source}")
        st.info(f"**使用用途:** {usage}")
        st.info(f"**领用时间:** {take_time}")
        st.info(f"**到期时间:** {due_date}")
        
        # 可以添加地图组件
    st.markdown("---")
    st.subheader("📦 物品位置")
    # st.map(location=[22.5, 113.5], zoom=15) # 模拟位置，实际应用中应根据物品位置信息显示

    st.header("🔧 操作")
    
    col3, col4 = st.columns(2)
    
    with col3:
        if st.button("跳转到申请借阅界面", use_container_width=True):
            st.info("正在跳转到申请借阅界面中")
            handle_redirect(goto = "page1", params = {"item_id": item_id} )
        # 构建查询字符串
        # query_string = "&".join([f"{k}={v}" for k, v in params.items() if v])
        # # 构建目标URL
        # "http://192.168.3.23:8501/er_wei_ma_chuanjianziwangye?item_id={item_id}"
        # 实验室内网
        # target_url = f"http://192.168.3.23:8501/?{query_string}"
        # 热点
        # target_url = f"http://{IP_AND_HOST}/?{query_string}&goto=page1"
        # st.success(f"✅ 跳转到申请借阅界面: **{target_url}**")
        # print (target_url)
        # st.link_button("📝 跳转到申请借阅界面", url = target_url,use_container_width=True)
            # st.info("跳转到借阅申请流程...")
            # 构建URL参数字典

            

            # 跳转到子页面
            # st.success("✅ 正在跳转...")
            # st.link_button("跳转", target_url)
            # st.query_params = params  # 将参数传递给子页面
            # print(st.query_params)
            # st.switch_page("pages/detail_page.py")
    
    with col4:
        if st.button("🔄 更新位置", use_container_width=True):
            st.info("跳转到位置更新页面...")
#     else:
#         st.error("❌ 未提供物品ID参数")
#         st.info("💡 请通过扫描二维码或输入物品ID访问此页面")

# else:
#     st.warning("⚠️ 未检测到任何参数")
#     st.info("💡 请通过扫描二维码或输入物品ID访问此页面")
#     # 测试输入框
#     st.markdown("---")
#     st.subheader("🧪 手动测试")
#     test_item_id = st.text_input("请输入物品ID进行测试", placeholder="例如: ITEM001")
#     if test_item_id and st.button("查询", use_container_width=True):
#         st.switch_page(f"pages/item_detail.py?item_id={test_item_id}")
