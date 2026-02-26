# main.py

import platform

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from app.constants import CUISINE_DATA, ALL_CUISINES  # 导入新数据
from app.llm_engine import get_food_recommendation

# --- 字体配置 ---
system_name = platform.system()

if system_name == "Windows":
    # Windows 默认支持 "SimHei" (黑体) 或 "Microsoft YaHei" (微软雅黑)
    plt.rcParams['font.sans-serif'] = ['SimHei']
elif system_name == "Linux":
    # Ubuntu/Linux 使用我们之前安装的 "WenQuanYi Zen Hei"
    plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']
else:
    # Mac OS (可选备用)
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']

plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# --- 页面配置 ---
st.set_page_config(page_title="智味 AI - 全能版", page_icon="🍲", layout="wide")

st.title("🤖 您的私人美食顾问")
st.markdown("本地隐私保护 | 深度推理引擎")


# --- 核心逻辑封装 ---
def handle_recommendation(payload, mode):
    """处理 UI 触发的推荐请求"""
    with st.spinner("🧠 大脑正在飞速运转..."):
        result = get_food_recommendation(payload, mode=mode)
        data = result.get("data", {})

        # 1. 展示思维链 (CoT)
        with st.expander("🕵️ 偷看 AI 的分析笔记 (CoT)", expanded=True):
            if "analysis" in data:
                st.info(data["analysis"])
            else:
                st.text(result.get("raw_text", ""))

        # 2. 结果展示区
        if "recommendations" in data and data["recommendations"]:
            recs = data["recommendations"]
            df = pd.DataFrame(recs)

            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader("🍽️ 推荐清单")
                st.dataframe(
                    df,
                    column_config={
                        "dish_name": "菜品",
                        "cuisine": "菜系",
                        "price": st.column_config.NumberColumn("预估(元)", format="¥%d"),
                        "reason": "推荐理由"
                    },
                    width='stretch'
                )

            with col2:
                st.subheader("📊 价格分析")
                if "price" in df.columns:
                    fig, ax = plt.subplots(figsize=(4, 3))
                    ax.barh(df['dish_name'], df['price'], color='#ff7f50')
                    ax.set_xlabel('价格 (元)')
                    st.pyplot(fig)
        else:
            st.error("抱歉，未能提取出有效推荐。可能是模型开了小差，请重试。")


# --- 界面布局：双模式切换 ---
tab1, tab2 = st.tabs(["🎯 精准筛选模式", "🗣️ 自由对话模式"])

# === 模式一：精准筛选 ===
with tab1:
    col_input, col_space = st.columns([1, 2])
    with col_input:
        st.subheader("参数设置")
        city = st.text_input("📍 城市", "成都")
        budget = st.slider("💰 预算", 50, 800, 100)
        scenario = st.selectbox("🥂 场景", ["朋友聚餐", "商务宴请", "情侣约会", "一人食", "家庭聚会"])

        st.write("🌶️ **选择口味 (支持搜索)**")
        # 简单的扁平化多选
        selected_tastes = st.multiselect("直接搜索或选择", ALL_CUISINES, default=["川菜"])

        # 或者是按类别折叠展示 (可选的高级交互)
        with st.expander("📂 按分类浏览 (点击展开)"):
            for category, items in CUISINE_DATA.items():
                st.write(f"**{category}**")
                # 这里只做展示，实际选择还是靠上面的 multiselect 比较符合 Streamlit 逻辑
                st.caption(" | ".join(items))

        btn_structured = st.button("生成精准推荐", type="primary")

    if btn_structured:
        payload = {
            "city": city,
            "budget": budget,
            "scenario": scenario,
            "taste": ",".join(selected_tastes)
        }
        handle_recommendation(payload, mode="structured")

# === 模式二：自由对话 ===
with tab2:
    st.subheader("💬 告诉我您的想法")
    st.info("💡 提示：你可以说 '我想在上海找个适合求婚的地方，预算不限，要精致一点的法餐' 或者 '想吃点辣的，便宜点的夜宵'")

    user_text = st.text_area("请输入您的需求...", height=150)
    btn_text = st.button("智能分析并推荐", type="primary")

    if btn_text and user_text:
        handle_recommendation(user_text, mode="text")
