# main.py

import json
import os
import platform
import random
from datetime import date

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from app.cf_engine import get_cf_recommendations
# 导入自定义业务模块
from app.constants import ALL_CUISINES
from app.database import (
    init_db, verify_user, register_user,
    save_history, clear_user_history, save_daily_data_v2
)
from app.llm_engine import get_food_recommendation

# --- 1. 环境与字体配置 ---
system_name = platform.system()

if system_name == "Windows":
    plt.rcParams['font.sans-serif'] = ['SimHei']
elif system_name == "Linux":
    # 针对 Ubuntu 22.04 开发服务器配置
    plt.rcParams['font.sans-serif'] = ['文泉驿正黑']
else:
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']

plt.rcParams['axes.unicode_minus'] = False

# --- 2. 页面与数据库初始化 ---
st.set_page_config(page_title="智味 AI - 全能版", page_icon="🍲", layout="wide")

if "db_initialized" not in st.session_state:
    os.makedirs("data", exist_ok=True)
    init_db()
    st.session_state.db_initialized = True

# 核心状态持久化：存储当前的推荐结果，防止页面刷新丢失
if "recs_data" not in st.session_state:
    st.session_state.recs_data = None


# --- 3. 登录鉴权模块 ---
def login_ui():
    st.title("🔐 欢迎登录智味 AI")
    auth_mode = st.radio("选择操作", ["登录", "注册"], horizontal=True)
    username = st.text_input("用户名")
    password = st.text_input("密码", type="password")

    if auth_mode == "登录":
        if st.button("登录", type="primary"):
            uid = verify_user(username, password)
            if uid:
                st.session_state.logged_in = True
                st.session_state.user_id = uid
                st.session_state.username = username
                st.rerun()
            else:
                st.error("用户名或密码错误")
    else:
        if st.button("注册"):
            if register_user(username, password):
                st.success("注册成功，请切换至登录页面")
            else:
                st.error("用户名已存在")


# --- 4. 推荐结果渲染逻辑 ---
def render_recommendation_results():
    """渲染存储在 session_state 中的推荐结果，并提供保存功能"""
    if st.session_state.recs_data is None:
        return

    data = st.session_state.recs_data
    if "error" in data:
        st.warning(data["error"])
        return

    with st.expander("🕵️ 推荐逻辑分析 (CoT / 协同矩阵)", expanded=True):
        st.info(data.get("analysis", "暂无分析细节"))

    if "recommendations" in data and data["recommendations"]:
        recs = data["recommendations"]
        df = pd.DataFrame(recs)

        col_table, col_chart = st.columns([2, 1])

        with col_table:
            st.subheader("🍽️ 推荐清单")
            st.dataframe(df, use_container_width=True)

            # 记录偏好：点击后数据进入 SQLite 数据库，供协同过滤使用
            selected_dish = st.selectbox(
                "采纳这道菜吗？(保存后将计入您的长期偏好)",
                ["暂不采纳"] + [r['dish_name'] for r in recs],
                key="save_pref_select"
            )
            if st.button("💾 确认采纳并保存"):
                if selected_dish != "暂不采纳":
                    dish_info = next(item for item in recs if item["dish_name"] == selected_dish)
                    # 显式标记来源为 search_fav
                    save_history(st.session_state.user_id, dish_info['dish_name'], dish_info.get('cuisine', ''),
                                 source='search_fav')
                    st.success(f"已加入收藏夹（不影响膳食协同过滤）")

        with col_chart:
            st.subheader("📊 价格分析")
            if "price" in df.columns and not df['price'].isnull().all():
                fig, ax = plt.subplots(figsize=(4, 3))
                ax.barh(df['dish_name'], df['price'], color='#ff7f50')
                ax.set_xlabel('预估价格 (元)')
                st.pyplot(fig)
    else:
        st.error("未找到有效的推荐数据。")


# --- 5. 主程序逻辑 ---
if not st.session_state.get("logged_in", False):
    login_ui()
else:
    # 🌟 状态初始化：防止各 Tab 切换时出现 KeyError
    if "current_meals" not in st.session_state:
        st.session_state.current_meals = {}
    if "meal_locks" not in st.session_state:
        st.session_state.meal_locks = {"breakfast": False, "lunch": False, "dinner": False}

    # 侧边栏：用户信息与退出
    st.sidebar.write(f"👤 当前用户: **{st.session_state.username}**")
    if st.sidebar.button("退出登录"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

    st.title("🤖 您的私人美食顾问")
    st.markdown("本地隐私保护 | 协同过滤引擎 | 智能膳食管理")

    tab1, tab2, tab3 = st.tabs(["🎯 精准筛选", "🗣️ 自由对话", "📅 营养膳食"])

    # === Tab 1: 精准筛选 ===
    with tab1:
        col_in, _ = st.columns([1, 2])
        with col_in:
            city = st.text_input("📍 城市", "深圳")
            budget = st.slider("💰 预算", 50, 800, 100)
            scenario = st.selectbox("🥂 场景", ["一人食", "朋友聚餐", "商务宴请", "情侣约会"])
            selected_tastes = st.multiselect("口味偏好", ALL_CUISINES, default=["粤菜"])

            if st.button("生成精准推荐", type="primary", use_container_width=True):
                payload = {"city": city, "budget": budget, "scenario": scenario, "taste": ",".join(selected_tastes)}
                res = get_food_recommendation(payload, mode="structured")
                st.session_state.recs_data = res.get("data", {})

        render_recommendation_results()

    # === Tab 2: 自由对话 ===
    with tab2:
        user_text = st.text_area("告诉 AI 您的需求（如：想在后海找个适合写代码的咖啡厅）", height=150)
        if st.button("智能分析并推荐", type="primary"):
            if user_text:
                res = get_food_recommendation(user_text, mode="text")
                st.session_state.recs_data = res.get("data", {})

        render_recommendation_results()

    # === Tab 3: 营养膳食 (核心交互区) ===
    with tab3:
        st.subheader("🍱 膳食管理与智能发现")

        # 协同过滤入口：移至本页
        with st.expander("✨ 发现新口味 (基于协同过滤算法)", expanded=False):
            st.write("算法将根据您在“营养膳食”中的打卡记录和全站用户偏好为您计算。")
            if st.button("开启协同过滤推荐", type="secondary", use_container_width=True):
                st.session_state.recs_data = get_cf_recommendations(st.session_state.user_id)
            render_recommendation_results()

        st.divider()

        # 膳食计划控制区
        col_t, col_d, col_c = st.columns([2, 2, 1])
        with col_t:
            target_cal = st.slider("🎯 目标总热量 (kcal)", 1000, 3000, 1800, 100)
        with col_d:
            log_date = st.date_input("📅 记录日期", date.today())
        with col_c:
            st.write("偏好管理")
            if st.button("🗑️ 清空历史记录", help="清空偏好库将重置协同过滤引擎"):
                clear_user_history(st.session_state.user_id)
                st.session_state.recs_data = None
                st.toast("已清空历史数据")


        # 数据加载与随机生成逻辑
        @st.cache_data
        def load_food_data():
            with open("app/food_data.json", "r", encoding="utf-8") as f: return json.load(f)


        food_db = load_food_data()


        def generate_single_meal(meal_type):
            pool = food_db.get(meal_type, {})
            items, raw_names, cals = [], [], 0
            for category in ["staple", "protein", "side"]:
                if pool.get(category):
                    choice = random.choice(pool[category])
                    items.append(f"{choice['name']}({choice['unit']})")
                    raw_names.append(choice['name'])  # 提取纯菜名
                    cals += choice['calories']
            return {"desc": " + ".join(items), "calories": cals, "raw_names": raw_names}


        def roll_meals():
            best_diff, best_combo = float('inf'), {}
            for _ in range(100):
                temp_meals, current_total = {}, 0
                for m_type in ["breakfast", "lunch", "dinner"]:
                    if st.session_state.meal_locks[m_type] and m_type in st.session_state.current_meals:
                        temp_meals[m_type] = st.session_state.current_meals[m_type]
                    else:
                        temp_meals[m_type] = generate_single_meal(m_type)
                    current_total += temp_meals[m_type]["calories"]

                if abs(current_total - target_cal) < best_diff:
                    best_diff, best_combo = abs(current_total - target_cal), temp_meals
                if best_diff <= target_cal * 0.05: break
            st.session_state.current_meals = best_combo


        if not st.session_state.current_meals: roll_meals()

        # 展示三餐卡片
        meals = st.session_state.current_meals
        total_calories = sum(m.get("calories", 0) for m in meals.values())
        st.metric("预估摄入", f"{total_calories} kcal", f"{total_calories - target_cal}", delta_color="inverse")

        cols = st.columns(3)
        for i, (m_type, label) in enumerate(zip(["breakfast", "lunch", "dinner"], ["🍳 早餐", "🍱 午餐", "🥗 晚餐"])):
            with cols[i]:
                st.info(label)
                st.write(f"**{meals.get(m_type, {}).get('desc')}**")
                st.caption(f"{meals.get(m_type, {}).get('calories')} kcal")
                st.session_state.meal_locks[m_type] = st.checkbox("🔒 锁定", value=st.session_state.meal_locks[m_type],
                                                                  key=f"lk_{m_type}")

        st.write("")
        b_col1, b_col2, _ = st.columns([1, 1, 2])
        with b_col1:
            if st.button("🔄 换一批", use_container_width=True):
                roll_meals()
                st.rerun()
        with b_col2:
            if st.button("💾 记录摄入", type="primary", use_container_width=True):
                # 1. 保存热量日志（用于趋势绘图）
                save_daily_data_v2(st.session_state.user_id, total_calories, log_date)

                # 2. 🌟 核心点：将三餐菜品存入数据库，标记来源为 'diet_log'
                # 只有这里的记录会被协同过滤引擎读取
                count = 0
                for m_data in meals.values():
                    for dish in m_data.get("raw_names", []):
                        save_history(st.session_state.user_id, dish, "健康配餐", source='diet_log')
                        count += 1

                st.success(f"已记录 {log_date} 的 {count} 项膳食数据。协同过滤引擎已更新！")

        # 摄入趋势图（最近 30 天）
        st.divider()
        st.subheader("📈 摄入趋势 (最近 30 天)")
        log_path = f"data/daily_log_{st.session_state.user_id}.csv"
        if os.path.exists(log_path):
            df_log = pd.read_csv(log_path).sort_values(by="date")
            recent_log = df_log.tail(30)
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(recent_log['date'], recent_log['calories'], marker='o', color='#1f77b4', linewidth=2)
            plt.xticks(rotation=45)
            ax.set_ylabel("卡路里 (kcal)")
            ax.grid(True, axis='y', linestyle='--', alpha=0.7)
            st.pyplot(fig)
        else:
            st.info("暂无历史记录，开始记录您的第一笔数据吧！")
