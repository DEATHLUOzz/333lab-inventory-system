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
import bcrypt
import secrets
import hashlib
from PIL import Image
from io import BytesIO

# ===================== 配置 =====================
DATA_FILE = "items.json"
LOG_FILE = "logs.json"
PRINTED_QR_FILE = "printed_qrs.json"
# USER_FILE = "users.json"
LAB_HUNMAN = "lab_human.json"
USER_LOGGING_FILE = "user_logging.json"
BACKUP_DIR = "auto_backups"
QRCODES = "qrcodes"

SECRET_KEY = "my_lab_system_2025_abcxyz"
ADMIN_PASSWORD = "123456"
INTERNAL_STAFF_PASSWORD = "1"
USERNAME = "admin"
PASSWORD = "adminadmin"
MANAGER_USERNAME = "1"
MANAGER_PASSWORD = "1"
IP_AND_HOST = "192.168.153.13:8501"
PAGE_ROUTING_MAP = {
    "page1": "pages/01_item_checkout.py",
    "page2": "pages/02_item_checkin.py",
    "page3": "pages/03_item_registration.py",
    "page4": "pages/04_item_inventory.py",
    "page5": "pages/05_transaction_logs.py",
    "page6": "pages/06_data_admin.py",
    "page7": "pages/07_item_details.py",
}
SENDER = "zhaozehao135208412@qq.com"
AUTH_CODE = "tlvyzexzarqwciif"



# ===================== 初始化文件 =====================
def init_files():
    for f in [DATA_FILE, LOG_FILE, USER_LOGGING_FILE, PRINTED_QR_FILE]: # USER_FILE,
        if not os.path.exists(f):
            with open(f, "w", encoding="utf-8") as fp:
                json.dump([], fp, ensure_ascii=False, indent=2)
    if not os.path.exists(QRCODES):
        os.mkdir(QRCODES)
    if not os.path.exists(BACKUP_DIR):
        os.mkdir(BACKUP_DIR)
        #新


# ===================== 数据持久化工具 =====================
def load_json(path):
    with open(path, "r", encoding="utf-8") as fp:
        return json.load(fp)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
    # 每次保存数据后自动触发备份
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


def init_admin():
    users = load_json(USER_LOGGING_FILE)
    if users:   # 已经有用户了，不允许再次初始化
        st.session_state.init_admin = True
        st.rerun()
    st.subheader("初始化管理员")
    username = st.text_input("请输入管理员用户名: ", key="admin_username").strip()
    password = st.text_input("请输入管理员密码: ", type="password", key="admin_password").strip()
    reg_email = st.text_input("请输入邮箱", key="reg_email")
    col1, col2 = st.columns([3, 1]) # 创建两列，邮箱/按钮布局更美观
    with col1:
            reg_verify_code = st.text_input("请输入验证码", key="reg_verify_code")
    with col2:
        # 增加一个垂直间距，使按钮与输入框对齐
        st.write("") 
        st.write("")
        if st.button("发送验证码", key="btn_send_code"):
            if not reg_email:
                st.warning("请先输入邮箱地址")
            else:
                with st.spinner("正在发送验证码..."):
                    code = send_verify_code(reg_email)
                    if code:
                        st.session_state.sent_code = code # 将验证码存入 session_state
                        st.session_state.code_expire_time = time.time() + 300 # 记录过期时间（5分钟）
                        st.success("验证码已发送，请查收邮箱")
                    else:
                        st.error("验证码发送失败，请稍后重试")
    if st.button("立即注册"):
        if username in users:  # 检测用户名是否已存在
            st.error("用户名已存在，请换一个！")
        elif not username:
            st.warning("用户名不能为空")
        elif not password:
            st.warning("密码不能为空")
        elif not reg_email:
            st.warning("邮箱不能为空")
        elif not reg_verify_code:
            st.warning("验证码不能为空")
        else:
            if st.session_state.sent_code is False:
                st.warning("请先发送验证码到邮箱")
            elif reg_verify_code != str(st.session_state.sent_code):
                st.error("验证码错误")
            elif time.time() > st.session_state.code_expire_time:
                st.error("验证码已过期，请重新发送")
            else:
                hashed = hash_password(password)
                save_user(username, hashed, reg_email, role="admin")
                st.success("注册成功！可以去登录了") 

def login_hash():
    if 'sent_code' not in st.session_state:
        st.session_state.sent_code = False
    if 'code_expire_time' not in st.session_state:
        st.session_state.code_expire_time = 0

    tab1, tab2 = st.tabs(["登录", "注册"])

    with tab2:
        st.subheader("用户注册")
        users = load_json(USER_LOGGING_FILE)
        reg_user = st.text_input("设置用户名", key="reg_user")
        users_found = None
        for i, it in enumerate(users):
            if it["username"] == reg_user:
                users_found = i
                break
        if users_found is not None:
            st.error("用户名已存在")

        reg_pwd = st.text_input("设置密码", type="password", key="reg_pwd")
        reg_email = st.text_input("请输入邮箱", key="reg_email")
        col1, col2 = st.columns([3, 1]) # 创建两列，邮箱/按钮布局更美观
        with col1:
            reg_verify_code = st.text_input("请输入验证码", key="reg_verify_code")
        with col2:
            # 增加一个垂直间距，使按钮与输入框对齐
            st.write("") 
            st.write("")
            if st.button("发送验证码", key="btn_send_code"):
                if not reg_email:
                    st.warning("请先输入邮箱地址")
                else:
                    with st.spinner("正在发送验证码..."):
                        code = send_verify_code(reg_email)
                        if code:
                            st.session_state.sent_code = code # 将验证码存入 session_state
                            st.session_state.code_expire_time = time.time() + 300 # 记录过期时间（5分钟）
                            st.success("验证码已发送，请查收邮箱")
                        else:
                            st.error("验证码发送失败，请稍后重试")
        # reg_verify_code = st.text_input("请输入验证码", key="reg_verify_code")
        if st.button("立即注册"):
            if reg_user in users:  # 检测用户名是否已存在
                st.error("用户名已存在，请换一个！")
            elif not reg_user:
                st.warning("用户名不能为空")
            elif not reg_pwd:
                st.warning("密码不能为空")
            elif not reg_email:
                st.warning("邮箱不能为空")
            elif not reg_verify_code:
                st.warning("验证码不能为空")
            else:
                if st.session_state.sent_code is False:
                    st.warning("请先发送验证码到邮箱")
                elif time.time() > st.session_state.code_expire_time:
                    st.error("验证码已过期，请重新发送")
                elif reg_verify_code != str(st.session_state.sent_code):
                    st.error("验证码错误")
                else:
                    hashed = hash_password(reg_pwd)
                    save_user(reg_user, hashed, reg_email, role="user")
                    st.success("注册成功！可以去登录了") 


            # users = load_json(USER_LOGGING_FILE)
            # if reg_user in users:
            #     st.error("用户名已存在，请换一个！")
            # elif reg_user and reg_pwd:
            #     # 密码加密
            #     hashed = hash_password(reg_pwd)
            #     # 保存哈希后的密码
            #     save_user(reg_user, hashed, role="user")
            #     st.success("注册成功！可以去登录了")
            # else:
            #     st.warning("用户名和密码不能为空")

    with tab1:
        st.subheader("用户登录")
        login_user = st.text_input("用户名", key="login_user")
        login_pwd = st.text_input("密码", type="password", key="login_pwd")
        if st.button("登录"):
            users = load_json(USER_LOGGING_FILE)
            users_found = None
            for i, it in enumerate(users):
                if it["username"] == login_user:
                    users_found = i
                    break
            if users_found is None:
                st.error("用户名不存在")
            else:
                # 取出数据库里的哈希密码进行校验
                db_hashed_pwd = users[users_found]["hashed_pwd"]
                if check_password(login_pwd, db_hashed_pwd):
                    token, timestamp, nonce = generate_token(login_user)
                    st.session_state.user = login_user  # 登录成功后生成动态Token
                    st.session_state.token = token
                    st.session_state.timestamp = timestamp
                    st.session_state.nonce = nonce
                    if verify_token(st.session_state.get("user"), 
                                    st.session_state.get("token"), 
                                    st.session_state.get("timestamp"), 
                                    st.session_state.get("nonce")):  # 测试Token验证
                        st.session_state.logged_in = True
                        if users[users_found].get("role") == "admin":
                            st.session_state.logged_in_manager = True
                        st.success("登录成功!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.session_state.logged_in = False
                        st.error("Token验证失败，用户未登录或Token无效")
                else:
                    st.error("密码错误")


# 保存用户
def save_user(username, hashed_pwd, email, role="user"):
    users = load_json(USER_LOGGING_FILE)
    users.append({"username": username, "hashed_pwd": hashed_pwd,"create_time": time.strftime("%Y-%m-%d %H:%M"),"role": role,"user_email":email})
    with open(USER_LOGGING_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

# 密码哈希加密
def hash_password(raw_pwd):
    # 先转bytes，加盐哈希
    pwd_bytes = raw_pwd.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")

# 密码校验
def check_password(raw_pwd, hashed_pwd):
    pwd_bytes = raw_pwd.encode("utf-8")
    hashed_bytes = hashed_pwd.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)

# token
# token的生成必须用SHA256算法，不能用bcrypt
def generate_token(username: str) -> str:
    """生成动态Token"""
    # 时间戳 + 随机串
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(6)
    
    # 拼接原始字符串
    raw_str = f"{username}{timestamp}{nonce}{SECRET_KEY}"
    
    # SHA256 哈希作为Token
    token = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
    return token, timestamp, nonce

def verify_token(username: str, token: str, timestamp: str, nonce: str) -> bool:
    """验证Token是否合法"""
    raw_str = f"{username}{timestamp}{nonce}{SECRET_KEY}"
    calc_token = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
    return calc_token == token



# 绑定邮箱，发送验证码
def send_verify_code(email):
    """发送验证码，传入内容为目标邮箱地址，返回生成的验证码（如果发送失败则返回None）"""
    import smtplib
    import random
    from email.mime.text import MIMEText
    code = random.randint(100000, 999999)
    sender = SENDER
    auth_code = AUTH_CODE
    smtp_server = "smtp.qq.com"
    port = 587

    msg = MIMEText(f"你的验证码是：{code}，5分钟内有效", "plain", "utf-8")
    msg["Subject"] = "邮箱验证"
    msg["From"] = sender
    msg["To"] = email

    try:
        server = smtplib.SMTP(smtp_server, port)
        server.starttls()
        server.login(sender, auth_code)
        server.sendmail(sender, email, msg.as_string())
        server.quit()
        return code
        
    except:
        return None


# # 二维码生成
# def gen_qrcode(item_id):
#     """生成二维码，内容为访问物品详情页的URL"""
#     path = f"qrcodes/{item_id}.png"
#     qr = qrcode.QRCode(
#         version=1,
#         error_correction=qrcode.constants.ERROR_CORRECT_L,
#         box_size=10,
#         border=4,
#     )
#     qr.add_data(f"http://{IP_AND_HOST}/?item_id={item_id}&goto=page7")
#     qr.make(fit=True)
#     qr.make_image(fit=True).save(path)
#     return path

# 纯内存生成二维码
def gen_qrcode(item_id):
    """纯内存生成二维码，返回PIL Image对象，不保存任何文件到磁盘"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,  # 保留你原来的L级别
        box_size=10,
        border=4,
    )
    # 二维码内容与你原来完全一致：完整的访问URL
    qr.add_data(f"http://{IP_AND_HOST}/?item_id={item_id}&goto=page7")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img  # ✅ 直接返回PIL Image对象，不保存文件



# ===================== 业务逻辑工具 =====================
def is_valid_phone(phone):
    """校验手机号：11位数字"""
    return re.match(r'^\d{11}$', phone) is not None

def get_or_create_user(user_name, name, user_class,user_phone):
    """获取或创建人员档案，返回用户对象"""
    users = load_json(USER_LOGGING_FILE)
    # user_found = next((u for u in users if u['user_id'] == user_id), None)
    user_found = None
    for i, it in enumerate(users):
        if it["username"] == user_name:
            user_found = i
            break
    if user_found+1:
        users[user_found]["name"] = name
        users[user_found]["user_class"] = user_class
        users[user_found]["user_phone"] = user_phone
        save_json(USER_LOGGING_FILE, users)
        return user_found
    # else:
    #     new_user = {
    #         "name": name,
    #         "class": user_class,
    #         "phone": user_phone,
    #         "create_time": time.strftime("%Y-%m-%d %H:%M")
    #     }
    #     users.append(new_user)
    #     save_json(USER_LOGGING_FILE, users)
    #     return new_user

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
    users = load_json(USER_LOGGING_FILE)
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


def goto_page(page_name: str, params: dict = None):
    """
    通用页面跳转函数，支持通过 session_state 传递多个参数。
    
    Args:
        page_name (str): 目标页面路径，例如 "pages/detail.py"
        params (dict, optional): 需要传递的参数字典，例如 {"item_id": "123", "mode": "edit"}
    """
    if params is None:
        params = {}
    final_params = {}
    
    # 先放入手动传入的
    final_params.update(params)
    
    if final_params:
        # 使用一个统一的前缀或专门的字典来存储跳转参数，避免污染全局 namespace
        # 这里我们直接存入 st.session_state，但建议加上前缀以防冲突，例如 "goto_params_"
        for key, value in final_params.items():
            st.session_state[f"goto_{key}"] = value
            
        # print(f"goto_page_query_params: {st.query_params}")
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
    goto_where = goto
    if goto is None:
        goto_where = st.query_params.get("goto","")
        return
    if params is None:
        params = {}
        params = {k: v for k, v in st.query_params.items() if k != "goto"}
    # print (f"handle_redirect_params:{params}")
    # print(f"handle_redirect_goto_where:{goto_where}")
    if goto_where and goto_where in PAGE_ROUTING_MAP:
        target_page = PAGE_ROUTING_MAP[goto_where]
        # print(f"跳转至{target_page}")
        # print(params)
        # print(f"handle_redirect_query_params: {st.query_params}")
        try:
            goto_page(page_name=target_page,params=params)
        except Exception as e:
            st.error(f"跳转至{target_page}失败，请检查参数是否正确")
            print(e)
