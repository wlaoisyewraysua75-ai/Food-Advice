# app/cf_engine.py


import random

import pandas as pd

from app.database import get_dietary_history_df


def get_cf_recommendations(user_id, top_n=3):
    """
    基于用户“营养膳食”打卡记录的物品协同过滤
    """
    # 🌟 关键点：仅获取膳食打卡数据
    df = get_dietary_history_df()

    # 获取当前用户在“营养膳食”页面的记录
    user_diet_history = df[df['user_id'] == user_id]['dish_name'].tolist() if not df.empty else []

    if not user_diet_history:
        return {
            "error": "您在“营养膳食”页尚无打卡记录。协同过滤需要基于您的真实摄入记录进行推导，请先在膳食页记录几顿饭。"}

    # 注入虚拟社区数据（同样需要符合膳食逻辑）以解决冷启动
    if len(df) < 5:
        mock_diet_data = pd.DataFrame([
            {'user_id': 991, 'dish_name': '清蒸鲈鱼'}, {'user_id': 991, 'dish_name': '白灼虾'},
            {'user_id': 992, 'dish_name': '水煮鸡胸肉'}, {'user_id': 992, 'dish_name': '糙米饭'},
            {'user_id': 993, 'dish_name': '清蒸鲈鱼'}, {'user_id': 993, 'dish_name': '白灼西兰花'}
        ])
        df = pd.concat([df, mock_diet_data], ignore_index=True)

    # 计算 User-Item 矩阵
    interaction_matrix = pd.crosstab(df['user_id'], df['dish_name'])
    item_similarity = interaction_matrix.corr(method='pearson').fillna(0)

    recommendation_scores = pd.Series(dtype=float)
    for dish in user_diet_history:
        if dish in item_similarity.columns:
            sim_scores = item_similarity[dish].drop(user_diet_history, errors='ignore')
            recommendation_scores = recommendation_scores.add(sim_scores, fill_value=0)

    if recommendation_scores.empty or recommendation_scores.max() == 0:
        return {"error": "目前记录的食材组合过于独特，暂未在社区找到关联偏好。"}

    top_dishes = recommendation_scores.sort_values(ascending=False).head(top_n)

    recs = []
    for dish_name, score in top_dishes.items():
        recs.append({
            "dish_name": dish_name,
            "cuisine": "膳食协同发现",
            "price": random.randint(20, 60),
            "reason": f"根据您的膳食打卡习惯为您推荐 (匹配度: {score:.2f})"
        })

    return {
        "analysis": f"已锁定您在膳食页记录的 {len(user_diet_history)} 种食材偏好，正在进行行为矩阵交叉推导...",
        "recommendations": recs
    }
