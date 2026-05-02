# utils.py
import streamlit as st
import json
import os
import time
import re
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
from barcode import Code128
from barcode.writer import ImageWriter
import qrcode

# ===================== 配置 =====================
DATA_FILE = "items.json"
LOG_FILE = "logs.json"
USER_FILE = "users.json"
BACKUP_DIR = "auto_backups"  # 🆕 自动备份目录
ADMIN_PASSWORD = "123456"
INTERNAL_STAFF_PASSWORD = "1"
USERNAME = "admin"
PASSWORD = "adminadmin"
MANAGER_USERNAME = "1"
MANAGER_PASSWORD = "1"
IP_AND_HOST = "192.168.1.106:8501"
PAGE_ROUTING_MAP = {

    "page1": "pages/01_item_checkout.py",
    "page2": "pages/02_item_checkin.py",
    "page3": "pages/03_item_registratio.py",
    "page4": "pages/04_item_inventory.py",
    "page5": "pages/05_transaction_logs.py",
    "page6": "pages/06_data_admin.py",
    "page7": "pages/er_wei_ma_chuanjianziwangye.py",
}


# ===================== 初始化文件（幂等性） =====================
def init_files():
    for f in [DATA_FILE, LOG_FILE, USER_FILE]:
        if not os.path.exists(f):
            with open(f, "w", encoding="utf-8") as fp:
                json.dump([], fp, ensure_ascii=False, indent=2)
    if not os.path.exists("qrcodes"):
        os.mkdir("qrcodes")
    if not os.path.exists(BACKUP_DIR):  # 🆕 初始化备份目录
        os.mkdir(BACKUP_DIR)
    if not os.path.exists("lab_human"):
        os.mkdir("lab_human")

# ===================== 数据持久化工具 =====================
def load_json(path):
    with open(path, "r", encoding="utf-8") as fp:
        return json.load(fp)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
    # 🆕 每次保存数据后自动触发备份
    auto_backup()

# 登录页面
def login():

    st.header("登录")
    st.divider()

    username = st.text_input("用户名")
    password = st.text_input("密码", type="password")

    if st.button("Login"):
        if username == USERNAME and password == PASSWORD:
            st.session_state.logged_in = True
            st.success("登录成功!")
            time.sleep(0.5)
            st.rerun()
        elif username == MANAGER_USERNAME and password == MANAGER_PASSWORD:
            st.session_state.logged_in = True
            st.session_state.logged_in_manager = True
            st.success("登录成功!")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("用户名或密码错误")

# ===================== 条码生成工具 =====================
# 条形码生成
# def gen_barcode(item_id):
#     path = f"barcodes/{item_id}"
#     Code128(item_id, writer=ImageWriter()).save(path)
#     return path + ".png"

# 二维码生成
def gen_qrcode(item_id):
    path = f"qrcodes/{item_id}.png"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(f"http://{IP_AND_HOST}/?item_id={item_id}&goto=page7")
    qr.make(fit=True)
    qr.make_image(fit=True).save(path)
    return path



# ===================== 业务逻辑工具 =====================
def is_valid_phone(phone):
    """校验手机号：11位数字"""
    return re.match(r'^\d{11}$', phone) is not None

def get_or_create_user(user_id, name, user_class, source):
    """获取或创建人员档案，返回用户对象"""
    users = load_json(USER_FILE)
    existing = next((u for u in users if u['user_id'] == user_id), None)
    if existing:
        existing['name'] = name
        existing['class'] = user_class
        save_json(USER_FILE, users)
        return existing
    else:
        new_user = {
            "user_id": user_id,
            "name": name,
            "class": user_class,
            "source": source,
            "create_time": time.strftime("%Y-%m-%d %H:%M")
        }
        users.append(new_user)
        save_json(USER_FILE, users)
        return new_user

# def cheak_is_labhuman(user_id):



# ===================== 日期与预警工具 =====================
def check_near_expiry(items):
    alerts = []
    now = datetime.now()
    for it in items:
        if it["status"] == "使用中" and it.get("due_date"):
            due = datetime.strptime(it["due_date"], "%Y-%m-%d")
            delta = (due - now).days
            if delta <= 1:
                it_copy = it.copy()
                it_copy['days_left'] = delta
                alerts.append(it_copy)
    return alerts

# ===================== Excel 导出工具 =====================
def generate_excel_backup():
    """生成Excel备份数据（用于手动下载）"""
    items = load_json(DATA_FILE)
    users = load_json(USER_FILE)
    logs = load_json(LOG_FILE)

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')

    # Sheet 1: 物品清单
    df_items = pd.DataFrame(items)
    sheet1_cols = ["item_id", "item_name", "status", "remark"]
    for col in sheet1_cols:
        if col not in df_items.columns:
            df_items[col] = ""
    df_items[sheet1_cols].to_excel(writer, index=False, sheet_name='物品清单')

    # Sheet 2: 人员档案
    df_users = pd.DataFrame(users)
    df_users.to_excel(writer, index=False, sheet_name='人员档案')

    # Sheet 3: 借用明细
    detailed_data = []
    for log in logs:
        row = log.copy()
        detailed_data.append(row)
    
    if detailed_data:
        df_detail = pd.DataFrame(detailed_data)
    else:
        df_detail = pd.DataFrame(columns=["type", "item_id", "item_name", "user_name", "user_id", "time"])
    
    df_detail.to_excel(writer, index=False, sheet_name='借用流水')

    writer.close()
    return output.getvalue()

# 🆕 自动备份函数
def auto_backup():
    """自动生成带时间戳的Excel备份文件到本地"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{BACKUP_DIR}/lab_backup_{timestamp}.xlsx"
        
        excel_data = generate_excel_backup()
        
        with open(filename, "wb") as f:
            f.write(excel_data)
            
        # 可选：保留最近30个备份，防止磁盘占用过多
        backup_files = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.xlsx')])
        if len(backup_files) > 30:
            for old_file in backup_files[:-30]:
                os.remove(os.path.join(BACKUP_DIR, old_file))
                
    except Exception as e:
        # 备份失败不影响主流程，只打印错误
        st.error(f"自动备份失败: {str(e)}")

# ===================== 管理员身份状态管理 =====================
# def init_admin_state():
#     if "is_admin" not in st.session_state:
#         st.session_state.is_admin = False

# def admin_login_widget():
#     pwd = st.sidebar.text_input("管理员密码", type="password", key="pwd_input")
#     if st.sidebar.button("登录管理员"):
#         if pwd == ADMIN_PASSWORD:
#             st.session_state.is_admin = True
#             st.sidebar.success("登录成功")
#         else:
#             st.sidebar.error("密码错误")

# def admin_logout_widget():
#     if st.sidebar.button("退出管理员"):
#         st.session_state.is_admin = False
#         st.rerun()

# def render_sidebar_auth():
#     init_admin_state()
#     if not st.session_state.is_admin:
#         st.sidebar.info("当前身份：游客（可领用/归还）")
#         admin_login_widget()
#     else:
#         st.sidebar.success("当前身份：管理员（可录入/查看/修改/删除）")
#         admin_logout_widget()
def render_alerts():
    items = load_json("items.json")
    alerts = check_near_expiry(items)
    if alerts:
        st.error(f"⚠️ 警告：有 {len(alerts)} 个物品即将到期！")
        for a in alerts:
            days = a['days_left']
            if days < 0:
                st.error(f"- 🔴 【{a['item_name']}】(ID:{a['item_id']}) 已超期 {abs(days)} 天！(使用人: {a['user']})")
            elif days == 0:
                st.warning(f"- 🟠 【{a['item_name']}】(ID:{a['item_id']}) 今天到期！(使用人: {a['user']})")
            else:
                st.info(f"- 🟡 【{a['item_name']}】(ID:{a['item_id']}) 将在 {days} 天后到期。(使用人: {a['user']})")

#跳转函数，传入想要跳转页面，以及需要传递的参数，
# def goto_page(page_name, state):

#     if f"target_{state}" not in st.session_state:
#         st.session_state[f"target_{state}"] = False
#     state = st.query_params.get(f"{state}", "")
#     if st.session_state.get("logged_in") and state:
#         st.session_state[f"target_{state}"] = state
#         state = None
#         st.switch_page(page_name)

def goto_page(page_name: str, params: dict = None):
    """
    通用页面跳转函数，支持通过 session_state 传递多个参数。
    
    Args:
        page_name (str): 目标页面路径，例如 "pages/detail.py"
        params (dict, optional): 需要传递的参数字典，例如 {"item_id": "123", "mode": "edit"}
    """
    print("进入goto_page")
    if params is None:
        params = {}
    
    # 2. 获取 URL 中的查询参数 (Query Params)
    # 注意：st.query_params 在 Streamlit 1.37+ 中行为类似字典
    # query_params = st.query_params
    
    # 3. 合并 URL 参数和手动传入的参数
    # URL 参数优先级通常较高，或者你可以选择手动传入优先，这里以手动传入为主，URL为辅
    final_params = {}
    
    # 先放入手动传入的
    final_params.update(params)
    
    # 如果手动没传，尝试从 URL 获取 (假设 URL key 和 session_state key 一致)
    # for key in params.keys():
    #     if key not in final_params or not final_params[key]:
    #         url_val = query_params.get(key, "")
    #         if url_val:
    #             final_params[key] = url_val

    # 4. 检查登录状态
    # is_logged_in = st.session_state.get("logged_in", False)
    
    # if not is_logged_in:
    #     # 如果未登录，保存当前想要访问的参数和目标页面，以便登录后跳回
    #     st.session_state["pending_redirect"] = {
    #         "page": page_name,
    #         "params": final_params
    #     }
    #     st.switch_page("pages/login.py")  # 确保你有这个登录页面
    #     return

    # 5. 如果已登录且有参数，存入 session_state
    if final_params:
        # 使用一个统一的前缀或专门的字典来存储跳转参数，避免污染全局 namespace
        # 这里我们直接存入 st.session_state，但建议加上前缀以防冲突，例如 "goto_params_"
        for key, value in final_params.items():
            st.session_state[f"goto_{key}"] = value
            
        print(f"goto_page_query_params: {st.query_params}")
        # 6. 执行跳转
        try:
            st.switch_page(page_name)
        except Exception as e:
            st.error(f"页面跳转失败: {page_name}, 错误: {str(e)}")
    else:
        # 没有参数，直接跳转
        try:
            st.switch_page(page_name)
        except Exception as e:
            st.error(f"页面跳转失败: {page_name}, 错误: {str(e)}")


    #页面路由
def handle_redirect(goto:str = None, params: dict = None):
    """
    实现页面定向跳转逻辑。自动搜索URl中的参数goto的值。并将传入的值进行跨页面传递。
    如果URl没有goto参数，则返回。
    如果没有传入要传递的参数默认None

    Args:
        goto (str): 目标页面标识符
        params (dict): 获取的查询参数字典，例如 {"item_id": "123"}
    """
    print("进入handle_redirect")
    goto_where = goto
    if goto is None:
        goto_where = st.query_params.get("goto","")
        return
    if params is None:
        params = {}
        params = {k: v for k, v in st.query_params.items() if k != "goto"}
    print (f"handle_redirect_params:{params}")
    print(f"handle_redirect_goto_where:{goto_where}")
    if goto_where and goto_where in PAGE_ROUTING_MAP:
        target_page = PAGE_ROUTING_MAP[goto_where]
        # print(f"跳转至{target_page}")
        # print(params)
        print(f"handle_redirect_query_params: {st.query_params}")
        goto_page(page_name=target_page,params=params)