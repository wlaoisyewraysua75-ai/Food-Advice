# app/llm_engine.py

import requests
import json
import re

# 配置 Ollama 本地地址
OLLAMA_API_URL = "http://localhost:11434/api/generate"
# 确保这里用的模型名字和你 ollama list 出来的一致
MODEL_NAME = "qwen3:8b_Q8"


def query_ollama(prompt, system_prompt=""):
    """
    发送请求给 Ollama，并返回生成的原始文本
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "format": "json",  # 新增这一行：强制模型输出 JSON 格式
        "options": {
            "temperature": 0.0,
            "num_ctx": 2048,
            "num_predict": 1000,
            "repeat_penalty": 1.1,  # 降低惩罚值
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
    你是一个专业的美食推荐助手。

    【任务】
    1. 分析用户的需求（可能是具体的条件，也可能是一段模糊的文字）。
    2. 如果用户没有提供预算，请根据其描述的场景（如“穷游”vs“商务”）自动估算合理的预算范围。
    3. 必须输出 JSON 格式。

    【输出格式】
    先输出分析过程，然后输出 JSON：
    ```json
    {
        "analysis": "用户想吃清淡的，且提到了女朋友，推测是约会场景，预算预估 200元...",
        "recommendations": [
            {
                "dish_name": "菜名",
                "cuisine": "菜系",
                "price": 50,
                "reason": "理由"
            }
        ]
    }
    ```
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
        user_prompt = f"""
        【用户自述需求】
        "{input_data}"

        请根据这段话，推测用户的预算、口味和场景，并推荐 3-5 道合适的菜品。
        如果是询问做法或无关话题，请委婉拒绝并引导回美食推荐。
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