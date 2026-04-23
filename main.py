# main.py

import os
import json
import random
import platform
from datetime import date

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from app.constants import CUISINE_DATA, ALL_CUISINES
from app.llm_engine import get_food_recommendation

# --- 字体配置 ---
system_name = platform.system()

if system_name == "Windows":
    plt.rcParams['font.sans-serif'] = ['SimHei']
elif system_name == "Linux":
    plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']
else:
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


def save_daily_data(total_cal):
    """持久化当日摄入热量至 CSV"""
    os.makedirs("data", exist_ok=True)
    file_path = "data/daily_log.csv"
    today_str = str(date.today())

    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        if today_str in df['date'].values:
            df.loc[df['date'] == today_str, 'calories'] = total_cal
        else:
            new_row = pd.DataFrame([{'date': today_str, 'calories': total_cal}])
            df = pd.concat([df, new_row], ignore_index=True)
    else:
        df = pd.DataFrame([{'date': today_str, 'calories': total_cal}])

    df.to_csv(file_path, index=False)


# --- 界面布局：多模式切换 ---
tab1, tab2, tab3 = st.tabs(["🎯 精准筛选模式", "🗣️ 自由对话模式", "📅 营养膳食"])

# === 模式一：精准筛选 ===
with tab1:
    col_input, col_space = st.columns([1, 2])
    with col_input:
        st.subheader("参数设置")
        city = st.text_input("📍 城市", "成都")
        budget = st.slider("💰 预算", 50, 800, 100)
        scenario = st.selectbox("🥂 场景", ["朋友聚餐", "商务宴请", "情侣约会", "一人食", "家庭聚会"])

        st.write("🌶️ **选择口味 (支持搜索)**")
        selected_tastes = st.multiselect("直接搜索或选择", ALL_CUISINES, default=["川菜"])

        with st.expander("📂 按分类浏览 (点击展开)"):
            for category, items in CUISINE_DATA.items():
                st.write(f"**{category}**")
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

# === 模式三：营养膳食 ===
with tab3:
    st.subheader("今日膳食计划")

    # 顶部控制区
    col_target, col_space = st.columns([1, 2])
    with col_target:
        target_cal = st.slider("🎯 目标摄入总热量 (kcal)", 1000, 3000, 1600, 100)


    @st.cache_data
    def load_food_data():
        try:
            with open("app/food_data.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}


    food_db = load_food_data()

    # 初始化 session_state
    if "current_meals" not in st.session_state:
        st.session_state.current_meals = {}
    if "meal_locks" not in st.session_state:
        st.session_state.meal_locks = {"breakfast": False, "lunch": False, "dinner": False}


    def generate_single_meal(meal_type):
        """为单餐随机生成主副食组合"""
        pool = food_db.get(meal_type, {})
        items = []
        cals = 0
        for category in ["staple", "protein", "side"]:
            if pool.get(category):
                choice = random.choice(pool[category])
                items.append(f"{choice['name']}({choice['unit']})")
                cals += choice['calories']

        return {
            "desc": " + ".join(items) if items else "暂无数据",
            "calories": cals
        }


    def roll_meals():
        """具有重采样机制的组合生成算法"""
        best_diff = float('inf')
        best_combo = {}

        # 尝试最多 100 次重采样，寻找最贴近目标热量的组合
        for _ in range(100):
            temp_meals = {}
            current_total = 0

            for meal_type in ["breakfast", "lunch", "dinner"]:
                # 如果该餐被锁定，直接继承现有数据
                if st.session_state.meal_locks[meal_type] and meal_type in st.session_state.current_meals:
                    temp_meals[meal_type] = st.session_state.current_meals[meal_type]
                else:
                    # 未锁定则重新生成组合
                    temp_meals[meal_type] = generate_single_meal(meal_type)

                current_total += temp_meals[meal_type]["calories"]

            diff = abs(current_total - target_cal)

            # 记录误差最小的一组
            if diff < best_diff:
                best_diff = diff
                best_combo = temp_meals

            # 如果总热量与目标的误差在 5% 以内，即可认为匹配成功，提前终止计算
            if diff <= target_cal * 0.05:
                break

        st.session_state.current_meals = best_combo


    # 首次进入页面时初始化
    if not st.session_state.current_meals:
        roll_meals()

    meals = st.session_state.current_meals
    total_calories = sum(m.get("calories", 0) for m in meals.values())

    # 展示总热量与目标偏差
    diff_val = total_calories - target_cal
    diff_str = f"+{diff_val}" if diff_val > 0 else f"{diff_val}"
    st.metric("预估总热量 (大卡)", f"{total_calories}", diff_str, delta_color="inverse")

    # 展示三餐卡片并提供锁定功能
    col_b, col_l, col_d = st.columns(3)

    with col_b:
        st.info("🍳 早餐")
        st.write(f"**{meals.get('breakfast', {}).get('desc', '未分配')}**")
        st.caption(f"{meals.get('breakfast', {}).get('calories', 0)} kcal")
        st.session_state.meal_locks["breakfast"] = st.checkbox("🔒 锁定不变",
                                                               value=st.session_state.meal_locks["breakfast"],
                                                               key="lock_b")

    with col_l:
        st.warning("🍱 午餐")
        st.write(f"**{meals.get('lunch', {}).get('desc', '未分配')}**")
        st.caption(f"{meals.get('lunch', {}).get('calories', 0)} kcal")
        st.session_state.meal_locks["lunch"] = st.checkbox("🔒 锁定不变", value=st.session_state.meal_locks["lunch"],
                                                           key="lock_l")

    with col_d:
        st.success("🥗 晚餐")
        st.write(f"**{meals.get('dinner', {}).get('desc', '未分配')}**")
        st.caption(f"{meals.get('dinner', {}).get('calories', 0)} kcal")
        st.session_state.meal_locks["dinner"] = st.checkbox("🔒 锁定不变", value=st.session_state.meal_locks["dinner"],
                                                            key="lock_d")

    st.write("")
    col_btn1, col_btn2, _ = st.columns([1, 1, 2])
    with col_btn1:
        if st.button("🔄 换一批 (仅限未锁定)", use_container_width=True):
            roll_meals()
            st.rerun()
    with col_btn2:
        if st.button("💾 记录今日摄入", type="primary", use_container_width=True):
            save_daily_data(total_calories)
            st.success("成功记录今日摄入数据！")

    # 历史趋势绘图保持不变
    st.divider()
    st.subheader("📈 近期摄入趋势")
    log_path = "data/daily_log.csv"
    if os.path.exists(log_path):
        df_log = pd.read_csv(log_path)
        recent_log = df_log.tail(7)

        fig, ax = plt.subplots(figsize=(10, 3))
        ax.plot(recent_log['date'], recent_log['calories'], marker='o', linestyle='-', color='#1f77b4')
        ax.set_title("最近7天热量摄入")
        ax.set_xlabel("日期")
        ax.set_ylabel("卡路里 (kcal)")
        ax.grid(True, linestyle='--', alpha=0.6)
        st.pyplot(fig)
    else:
        st.info("暂无历史记录，点击上方按钮开始记录您的第一笔数据！")