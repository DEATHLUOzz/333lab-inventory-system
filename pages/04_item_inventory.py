import streamlit as st
import pandas as pd
from datetime import datetime
from utils import load_json, save_json, init_files, render_alerts

init_files()
# render_sidebar_auth()

st.title("实验室物品借用系统")

if not st.session_state.logged_in_manager:
    st.error("仅管理员可查看")
else:
    st.subheader("📋 物品监控总览")
    items = load_json("items.json")
    render_alerts()
    
    if not items:
        st.info("暂无物品")
    else:
        display_data = []
        now = datetime.now()
        
        for it in items:
            status = it["status"]
            days_left_str = "N/A"
            display_status = status # 用于显示的文本
            
            if status == "使用中" and it.get("due_date"):
                due = datetime.strptime(it["due_date"], "%Y-%m-%d")
                delta = (due - now).days
                days_left_str = str(delta)
                
                # 🆕 优化：只通过文字和前缀图标来区分，不搞背景色
                if delta < 0:
                    display_status = f"🔴 已超期 {abs(delta)} 天"
                elif delta <= 1:
                    display_status = f"🟠 即将到期 ({delta}天)"
                else:
                    display_status = f"🟢 使用中"
            elif status == "空闲":
                display_status = "✅ 空闲"

            display_data.append({
                "ID": it["item_id"],
                "名称": it["item_name"],
                "状态": display_status, # 🆕 这里直接存带图标的字符串
                "使用人": it["user"] or "-",
                "来源": it.get("user_source", "-"),
                "用途": it.get("usage", "-"),
                "借用日": it.get("take_time", "-"),
                "到期日": it.get("due_date", "-"),
                "备注": it["remark"]
            })

        df = pd.DataFrame(display_data)
        
        # 🆕 优化：直接显示干净的表格，不需要 Pandas Styler
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            # 可以给状态列稍微加宽一点
            column_config={
                "状态": st.column_config.TextColumn("状态", width="medium")
            }
        )

        st.divider()
        st.subheader("🔧 详细管理 (展开修改/删除)")
        
        for idx, it in enumerate(items):
            stat = it["status"]
            with st.expander(f"[{stat}] {it['item_name']} ({it['item_id']})"):
                st.write(f"**使用人**: {it['user'] or '无'}")
                st.write(f"**用途**: {it.get('usage', '无')}")
                if it.get('user_source'):
                    st.write(f"**来源**: {it['user_source']}")
                    if it.get('extra_info'):
                        st.write(f"**联系**: {it['extra_info']['phone']}")
                
                new_name = st.text_input("物品名称", it["item_name"], key=f"n{idx}")
                new_remark = st.text_input("备注", it["remark"], key=f"r{idx}")
                if st.button("更新信息", key=f"u{idx}"):
                    items[idx]["item_name"] = new_name
                    items[idx]["remark"] = new_remark
                    save_json("items.json", items)
                    st.success("已更新")
                    st.rerun()

                if st.button("删除此物品", key=f"d{idx}"):
                    deleted_id = it["item_id"]
                    del items[idx]
                    save_json("items.json", items)
                    logs = load_json("logs.json")
                    new_logs = [log for log in logs if log["item_id"] != deleted_id]
                    save_json("logs.json", new_logs)
                    st.warning("已删除物品及相关借用记录")
                    st.rerun()