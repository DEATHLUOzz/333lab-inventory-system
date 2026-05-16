import time

import streamlit as st

from inventory_qr import (
    CUSTOM_PAPER_LABEL,
    ITEMS_FILE,
    PRINTED_QR_FILE,
    build_qr_records,
    decode_qr_image,
    list_printer_forms,
    list_printers,
    make_qr_pil_image,
    mark_printed,
    next_number_from_existing,
    normalize_item_id,
    print_qr_labels,
    register_item,
    register_printed_records,
)
from utils import init_files, load_json, save_json


def show_powershell_output(result):
    stdout = result.stdout or ""
    stderr = result.stderr or ""

    if result.returncode != 0:
        detail = stdout.strip() or stderr.strip() or f"PowerShell 退出码：{result.returncode}"
        st.error("打印失败")
        st.code(detail, language="powershell")

    if stdout.strip() or stderr.strip():
        with st.expander("打印日志"):
            st.write(f"退出码：{result.returncode}")
            if stdout.strip():
                st.code(stdout, language="powershell")
            if stderr.strip():
                st.code(stderr, language="powershell")


def render_photo_scanner():
    image_file = st.file_uploader(
        "拍照识别二维码",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=False,
        key="qr_photo_upload",
        label_visibility="collapsed",
    )
    if not image_file:
        return

    item_id, error = decode_qr_image(image_file)
    if item_id:
        st.session_state["register_scan_input"] = item_id
        st.session_state["show_photo_scanner"] = False
        st.success(f"已识别：{item_id}")
        st.rerun()
    else:
        st.error(error)


def render_generate_tab():
    st.subheader("生成二维码")

    printed_qrs = load_json(PRINTED_QR_FILE)
    prefix_col, digits_col, count_col = st.columns(3)
    with prefix_col:
        prefix = st.text_input("ID 前缀", value="ITEM", max_chars=12)
    with digits_col:
        digits = st.number_input("数字位数", min_value=3, max_value=12, value=6, step=1)
    with count_col:
        create_count = st.number_input("生成数量", min_value=1, max_value=1000, value=20, step=1)

    auto_start = st.checkbox("自动起始编号", value=True)
    default_start = next_number_from_existing(prefix)
    start_number = st.number_input(
        "起始编号",
        min_value=1,
        value=int(default_start),
        step=1,
        disabled=auto_start,
    )

    preview_id = f"{prefix}{int(default_start if auto_start else start_number):0{int(digits)}d}"
    st.image(make_qr_pil_image(preview_id), caption=preview_id, width=160)

    if st.button("生成二维码ID", type="primary"):
        start = default_start if auto_start else start_number
        new_records = build_qr_records(prefix, int(start), int(create_count), int(digits))
        save_json(PRINTED_QR_FILE, printed_qrs + new_records)
        st.session_state["last_generated_ids"] = [record["item_id"] for record in new_records]
        st.success(f"已生成 {len(new_records)} 个二维码ID")
        st.rerun()

    st.divider()
    render_print_panel()


def render_print_panel():
    st.subheader("打印标签")

    printed_qrs = load_json(PRINTED_QR_FILE)
    if not printed_qrs:
        st.info("暂无二维码ID")
        return

    printers, default_printer = list_printers()
    if not printers:
        st.warning("未检测到打印机")
        return

    default_index = printers.index(default_printer) if default_printer in printers else 0
    printer_name = st.selectbox("打印机", printers, index=default_index)
    paper_options = [CUSTOM_PAPER_LABEL] + list_printer_forms(printer_name)
    paper_name = st.selectbox("纸张", paper_options, index=0)

    col_width, col_height, col_copies = st.columns(3)
    with col_width:
        label_width = st.number_input("宽度(mm)", min_value=10, max_value=150, value=30, step=1)
    with col_height:
        label_height = st.number_input("高度(mm)", min_value=10, max_value=150, value=20, step=1)
    with col_copies:
        copies = st.number_input("份数", min_value=1, max_value=20, value=1, step=1)

    options = [record["item_id"] for record in printed_qrs]
    last_generated_ids = st.session_state.get("last_generated_ids", [])
    default_selection = [item_id for item_id in last_generated_ids if item_id in options] or options[-min(20, len(options)) :]
    selected_ids = st.multiselect("二维码ID", options=options, default=default_selection)

    with st.expander("自动入库"):
        auto_register = st.checkbox("打印成功后自动入库", value=False)
        name_prefix = st.text_input("物品名前缀", value="esp32", disabled=not auto_register)
        start_col, digits_col = st.columns(2)
        with start_col:
            name_start = st.number_input("起始序号", min_value=0, value=0, step=1, disabled=not auto_register)
        with digits_col:
            name_digits = st.number_input("序号位数", min_value=1, max_value=6, value=2, step=1, disabled=not auto_register)
        batch_remark = st.text_input("备注", value="", disabled=not auto_register)

    if st.button("打印", type="primary", disabled=not selected_ids):
        selected_id_set = set(selected_ids)
        selected_records = [record for record in printed_qrs if record["item_id"] in selected_id_set]
        with st.spinner("正在打印..."):
            result = print_qr_labels(
                selected_records,
                printer_name,
                paper_name,
                label_width,
                label_height,
                int(copies),
            )

        if result.returncode == 0:
            mark_printed(selected_records, int(copies))
            st.success(f"已发送 {len(selected_records) * int(copies)} 张标签")
            if auto_register:
                if not name_prefix.strip():
                    st.warning("物品名前缀不能为空")
                else:
                    created, skipped = register_printed_records(
                        selected_records,
                        name_prefix.strip(),
                        int(name_start),
                        int(name_digits),
                        batch_remark.strip(),
                    )
                    st.success(f"已入库 {len(created)} 个物品")
                    if skipped:
                        st.info(f"已跳过 {len(skipped)} 个物品")

        show_powershell_output(result)

    with st.expander("二维码ID列表"):
        st.dataframe(printed_qrs, use_container_width=True, hide_index=True)


def render_register_tab():
    st.subheader("扫码入库")

    if st.session_state.pop("clear_register_form", False):
        st.session_state["register_scan_input"] = ""
        st.session_state["register_item_name"] = ""
        st.session_state["register_item_remark"] = ""

    query_item_id = st.query_params.get("item_id", "") or st.session_state.get("goto_item_id", "")
    if query_item_id and st.session_state.get("register_scan_input") != str(query_item_id):
        st.session_state["register_scan_input"] = str(query_item_id)

    scan_col, close_col = st.columns([1, 4])
    with scan_col:
        if st.button("拍照识别", type="primary"):
            st.session_state["show_photo_scanner"] = True
    with close_col:
        if st.session_state.get("show_photo_scanner") and st.button("关闭"):
            st.session_state["show_photo_scanner"] = False
            st.rerun()

    if st.session_state.get("show_photo_scanner"):
        render_photo_scanner()

    scanned_value = st.text_input(
        "物品ID",
        placeholder="扫描或输入物品ID",
        key="register_scan_input",
    )
    item_id = normalize_item_id(scanned_value)

    if not item_id:
        return

    printed_qrs = load_json(PRINTED_QR_FILE)
    items = load_json(ITEMS_FILE)
    printed_record = next((record for record in printed_qrs if record.get("item_id") == item_id), None)
    registered_record = next((item for item in items if item.get("item_id") == item_id), None)

    if printed_record is None:
        st.error("二维码ID不存在")
        return
    if registered_record is not None:
        st.warning(f"已入库：{registered_record.get('item_name', '')}")
        return

    st.success(f"待入库：{item_id}")
    item_name = st.text_input("物品名称", key="register_item_name")
    remark = st.text_input("备注", key="register_item_remark")

    if st.button("录入", type="primary"):
        if not item_name.strip():
            st.warning("请输入物品名称")
            return
        register_item(item_id, item_name.strip(), remark.strip())
        st.success(f"{item_id} 入库成功")
        st.session_state["clear_register_form"] = True
        if "item_id" in st.query_params:
            del st.query_params["item_id"]
        time.sleep(0.3)
        st.rerun()


init_files()

st.title("物品入库")

if not st.session_state.get("logged_in_manager"):
    st.error("请先使用管理员账号登录")
    st.stop()

tab_generate, tab_register = st.tabs(["二维码管理", "扫码入库"])

with tab_generate:
    render_generate_tab()

with tab_register:
    render_register_tab()
