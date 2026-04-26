# app/database.py

import hashlib
import os
import sqlite3
from datetime import datetime

import pandas as pd

DB_PATH = "data/food_app.db"


def init_db():
    """初始化数据库表结构"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # 用户表
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY
                     AUTOINCREMENT,
                     username
                     TEXT
                     UNIQUE,
                     password_hash
                     TEXT
                 )''')
    # 历史记录表：增加 record_source 字段
    # record_source 值为 'search_fav' (搜索收藏) 或 'diet_log' (膳食记录)
    c.execute('''CREATE TABLE IF NOT EXISTS recommendation_history
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY
                     AUTOINCREMENT,
                     user_id
                     INTEGER,
                     dish_name
                     TEXT,
                     cuisine
                     TEXT,
                     record_source
                     TEXT,
                     timestamp
                     DATETIME
                 )''')
    conn.commit()
    conn.close()


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def verify_user(username, password):
    """验证用户登录"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=? AND password_hash=?", (username, hash_password(password)))
    user = c.fetchone()
    conn.close()
    return user[0] if user else None


def register_user(username, password):
    """注册新用户"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def save_history(user_id, dish_name, cuisine, source='search_fav'):
    """保存记录，并区分数据来源"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO recommendation_history (user_id, dish_name, cuisine, record_source, timestamp) VALUES (?, ?, ?, ?, ?)",
        (user_id, dish_name, cuisine, source, datetime.now()))
    conn.commit()
    conn.close()


def clear_user_history(user_id):
    """清空指定用户的所有推荐历史记录"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM recommendation_history WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def save_daily_data_v2(user_id, total_cal, target_date):
    """支持自定义日期的热量记录保存（用于生成折线图）"""
    os.makedirs("data", exist_ok=True)
    file_path = f"data/daily_log_{user_id}.csv"
    date_str = str(target_date)

    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        if date_str in df['date'].values:
            df.loc[df['date'] == date_str, 'calories'] = total_cal
        else:
            new_row = pd.DataFrame([{'date': date_str, 'calories': total_cal}])
            df = pd.concat([df, new_row], ignore_index=True)
    else:
        df = pd.DataFrame([{'date': date_str, 'calories': total_cal}])

    df.to_csv(file_path, index=False)


def get_dietary_history_df():
    """专门提取“营养膳食”打卡记录的数据源供协同过滤使用"""
    conn = sqlite3.connect(DB_PATH)
    # 核心逻辑：只查询 record_source 为 'diet_log' 的数据
    query = "SELECT user_id, dish_name FROM recommendation_history WHERE record_source = 'diet_log'"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df
