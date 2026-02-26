# app/llm_engine.py

import json
import re

import requests

# 配置 Ollama 本地地址
OLLAMA_API_URL = "http://localhost:11434/api/generate"
# 确保这里用的模型名字和你 ollama list 出来的一致
MODEL_NAME = "qwen2.5_7b_instruct_q8"


def query_ollama(prompt, system_prompt=""):
    """
    发送请求给 Ollama，并返回生成的原始文本
    """
    # 🌟 新增：定义极其严格的 JSON Schema
    response_schema = {
        "type": "object",
        "properties": {
            "analysis": {
                "type": "string",
                "description": "对用户需求的分析和推导过程"
            },
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "dish_name": {"type": "string"},
                        "cuisine": {"type": "string"},
                        "price": {"type": "integer"},
                        "reason": {"type": "string"}
                    },
                    "required": ["dish_name", "cuisine", "price", "reason"]
                }
            }
        },
        "required": ["analysis", "recommendations"]
    }

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "format": response_schema,  # 🌟 将这里的 "json" 替换为我们定义的 schema
        "options": {
            "temperature": 0.0,
            "num_ctx": 4096,
            "num_predict": 2000,
            "repeat_penalty": 1.1,
        }
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=6000)
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.exceptions.RequestException as e:
        return f"Error: 连接 Ollama 失败，请检查服务是否启动。详细错误: {e}"


def parse_llm_output(raw_text):
    """
    解析算法：从 LLM 的混合输出中提取 JSON，兼容 Markdown 代码块
    """
    # 1. 尝试直接解析
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    # 2. 使用正则提取 ```json ... ``` 或 {...} 内容
    json_match = re.search(r'```json\s*(.*?)\s*```', raw_text, re.DOTALL)
    if not json_match:
        # 尝试找最外层的 {}
        json_match = re.search(r'(\{.*\})', raw_text, re.DOTALL)

    if json_match:
        json_str = json_match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {"error": "JSON 解析失败", "raw": raw_text}

    return {"error": "未找到有效的 JSON 结构", "raw": raw_text}


def get_food_recommendation(input_data, mode="structured"):
    """
    获取推荐结果
    :param input_data: 字典(结构化模式) 或 字符串(文本模式)
    :param mode: "structured" 或 "text"
    """

    # 通用的 System Prompt
    system_prompt = """
    你是一个后台美食推荐 API 接口。
    你只能返回合法的 JSON 数据，绝对不要输出任何问候语、Markdown 标记（如 ```json）或 "Assistant:" 等对话前缀。

    【任务】
    1. 根据用户输入，推测预算和场景。
    2. 推荐 3-5 道符合要求的菜品。
    3. 把你的思考分析过程写在 "analysis" 字段中。

    【严格的数据结构】
    必须严格遵循以下 JSON 结构，并确保所有的 Key 都是英文：
    {
        "analysis": "在这里写下你的分析推导过程，例如：根据需求，用户在成都寻找100元的川菜聚餐...",
        "recommendations": [
            {
                "dish_name": "宫保鸡丁",
                "cuisine": "川菜",
                "price": 38,
                "reason": "经典川菜，微辣鲜香，非常适合朋友聚餐分享。"
            }
        ]
    }
    """

    # 根据模式构建 User Prompt
    if mode == "structured":
        # 确保输入数据字典即使缺字段也不会报错
        city = input_data.get('city', '未知')
        budget = input_data.get('budget', '未知')
        taste = input_data.get('taste', '未知')
        scenario = input_data.get('scenario', '未知')

        user_prompt = f"""
        【结构化需求】
        - 城市：{city}
        - 预算：{budget} 元
        - 偏好：{taste}
        - 场景：{scenario}

        请推荐 3-5 道菜。
        """
    else:
        # 自然语言模式
        # 自然语言模式
        user_prompt = f"""
        【用户自述需求】
        "{input_data}"

        请根据用户的这段话进行推理。
        1. 将你推测出的用户预算、口味偏好、就餐场景等所有分析过程，以及应对无关话题的引导话术，全部写在 JSON 的 "analysis" 字段中！绝对不要尝试创建额外的 JSON 字段！
        2. 即使需求模糊或偏离主题，你也必须在 "recommendations" 字段中生硬地推荐 3-5 道默认的经典菜品以满足 JSON 格式要求，绝对不能漏掉 "recommendations" 数组或改变内部的 key。
        """

    # 1. 调用 LLM
    raw_response = query_ollama(user_prompt, system_prompt)

    # 2. 解析 JSON
    parsed_data = parse_llm_output(raw_response)

    # 3. 返回结果
    return {
        "raw_text": raw_response,
        "data": parsed_data
    }
