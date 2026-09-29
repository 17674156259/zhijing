"""
LLM 通用调用模块
=================

统一封装不同大模型提供商的 API 调用，都兼容 OpenAI Chat Completions 格式。

支持的提供商：
- openai:    OpenAI GPT 系列
- dashscope: 阿里云通义千问
- deepseek:  DeepSeek
- zhipu:     智谱 AI (GLM 系列)
- mock:      内置 Mock 数据（无需 API Key）

使用方式：
    from ai.llm import chat
    result = chat([
        {"role": "system", "content": "你是一个数学老师"},
        {"role": "user", "content": "请分析这道题..."}
    ])
"""

import json
import os
import time
import random
from typing import List, Dict


# 各提供商的默认 API 地址
PROVIDER_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
    "ark": "https://ark.cn-beijing.volces.com/api/v3",
}


def get_config() -> Dict:
    """
    读取 LLM 配置。
    优先从环境变量读，没有则用默认值（mock 模式）。
    """
    provider = os.environ.get("LLM_PROVIDER", "mock").strip().lower()
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    model = os.environ.get("LLM_MODEL", "qwen-plus").strip()
    base_url = os.environ.get("LLM_BASE_URL", "").strip()

    # 如果没填 base_url，用提供商默认地址
    if not base_url and provider in PROVIDER_BASE_URLS:
        base_url = PROVIDER_BASE_URLS[provider]

    # 如果没有 API Key 且不是 mock，自动降级为 mock
    if provider != "mock" and not api_key:
        print(f"[LLM] 未配置 {provider} 的 API Key，自动降级为 mock 模式")
        provider = "mock"

    return {
        "provider": provider,
        "api_key": api_key,
        "model": model,
        "base_url": base_url,
    }


def get_vision_config() -> Dict:
    """
    读取视觉模型配置（OCR 专用）。
    如果没有配置视觉模型，回退到主配置。
    """
    provider = os.environ.get("LLM_VISION_PROVIDER", "").strip().lower()
    api_key = os.environ.get("LLM_VISION_API_KEY", "").strip()
    model = os.environ.get("LLM_VISION_MODEL", "").strip()
    base_url = os.environ.get("LLM_VISION_BASE_URL", "").strip()

    # 如果没有配置视觉模型，回退到主配置
    if not provider or not api_key:
        return get_config()

    # 如果没填 base_url，用提供商默认地址
    if not base_url and provider in PROVIDER_BASE_URLS:
        base_url = PROVIDER_BASE_URLS[provider]

    return {
        "provider": provider,
        "api_key": api_key,
        "model": model,
        "base_url": base_url,
    }


def chat(messages: List[Dict], temperature: float = 0.3) -> str:
    """
    调用大模型对话接口，返回模型输出的文本内容。
    """
    config = get_config()

    if config["provider"] == "mock":
        return _mock_chat(messages)

    return _real_chat(messages, config, temperature)


def chat_stream(messages: List[Dict], temperature: float = 0.3):
    """
    流式调用大模型，逐块 yield 文本内容。
    用于 SSE 推送给前端实现"逐字显示"效果。

    Yields:
        str: 每次返回一小段文本
    """
    config = get_config()

    if config["provider"] == "mock":
        yield from _mock_chat_stream(messages)
        return

    yield from _real_chat_stream(messages, config, temperature)


def _real_chat_stream(messages: List[Dict], config: Dict, temperature: float):
    """真实流式调用 LLM API，逐块 yield"""
    import urllib.request
    import urllib.error

    url = config["base_url"].rstrip("/") + "/chat/completions"

    payload = {
        "model": config["model"],
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {config['api_key']}")

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            buffer = b""
            for chunk in iter(lambda: resp.read(1), b""):
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith(b"data: "):
                        line = line[6:]
                    if line == b"[DONE]":
                        return
                    try:
                        data = json.loads(line)
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise Exception(f"LLM API 流式调用失败 (HTTP {e.code}): {error_body}")
    except Exception as e:
        raise Exception(f"LLM API 流式调用异常: {e}")


def _mock_chat_stream(messages: List[Dict]):
    """Mock 模式流式输出：逐字 yield 预设文本"""
    import time as _time

    full = _mock_chat(messages)
    # 按一小段一段地 yield，模拟流式效果
    chunks = []
    current = ""
    for ch in full:
        current += ch
        if ch in "，。；！？\n}】" and len(current) >= 5:
            chunks.append(current)
            current = ""
    if current:
        chunks.append(current)

    for chunk in chunks:
        _time.sleep(0.05)
        yield chunk


def _real_chat(messages: List[Dict], config: Dict, temperature: float) -> str:
    """真实调用 LLM API（使用 urllib，避免依赖 openai 库）"""
    import urllib.request
    import urllib.error

    url = config["base_url"].rstrip("/") + "/chat/completions"

    payload = {
        "model": config["model"],
        "messages": messages,
        "temperature": temperature,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {config['api_key']}")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise Exception(f"LLM API 调用失败 (HTTP {e.code}): {error_body}")
    except Exception as e:
        raise Exception(f"LLM API 调用异常: {e}")


def chat_vision(system_prompt: str, user_prompt: str, image_b64: str, temperature: float = 0.1) -> Dict:
    """
    调用支持视觉的 LLM，发送图片+文本，返回解析后的 JSON dict。

    Args:
        system_prompt: 系统提示词
        user_prompt: 用户文本提示
        image_b64: base64 编码的图片数据（不含前缀）
        temperature: 温度

    Returns:
        解析后的 dict
    """
    config = get_vision_config()

    if config["provider"] == "mock":
        return {
            "question": "求函数 $f(x) = \\sin(x^2)$ 的导数 $f'(x)$",
            "student_answer": "$f'(x) = \\cos(x^2)$",
            "correct_answer": "$f'(x) = 2x\\cos(x^2)$"
        }

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
            ]
        }
    ]

    content = _real_chat(messages, config, temperature)

    try:
        return _parse_json(content)
    except (ValueError, json.JSONDecodeError):
        return {"question": content.strip(), "student_answer": "", "correct_answer": ""}


def chat_json(messages: List[Dict], temperature: float = 0.2) -> Dict:
    """
    调用大模型并解析返回的 JSON。
    会自动提取 ```json ... ``` 包裹的内容，或直接尝试解析全文。

    Args:
        messages: 对话消息列表
        temperature: 温度

    Returns:
        解析后的 dict
    """
    content = chat(messages, temperature)
    return _parse_json(content)


def _parse_json(content: str) -> Dict:
    """
    从模型输出中提取 JSON。
    支持以下格式：
    1. 纯 JSON 文本
    2. ```json ... ``` 包裹的代码块
    3. ``` ... ``` 包裹的代码块
    4. 从 { 到 } 提取

    关键：在 JSON 解析前，先将 LaTeX 反斜杠双写，防止
    \f, \n, \r, \t, \b 被当作 JSON 合法转义符而破坏公式。
    """
    text = content.strip()

    # 先提取 JSON 子串（从 4 种格式中尝试）
    json_str = None

    # 尝试1：直接看是不是纯 JSON
    try:
        # 先用 LaTeX 修复后尝试解析
        fixed = _escape_latex_backslashes(text)
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 尝试2：提取 ```json ... ```
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        json_str = text[start:end].strip()
    # 尝试3：提取 ``` ... ```
    elif "```" in text:
        start = text.index("```") + 3
        first_newline = text.index("\n", start) if "\n" in text[start:] else start
        start = first_newline + 1
        end = text.index("```", start)
        json_str = text[start:end].strip()
    # 尝试4：从第一个 { 到最后一个 } 提取
    elif "{" in text and "}" in text:
        start = text.index("{")
        end = text.rindex("}") + 1
        json_str = text[start:end]

    if json_str:
        # 提取出 JSON 子串后，再做 LaTeX 反斜杠修复
        fixed = _escape_latex_backslashes(json_str)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return _safe_json_loads(fixed)

    raise ValueError(f"无法从模型输出中解析 JSON: {text[:200]}...")


def _escape_latex_backslashes(text: str) -> str:
    """
    将 JSON 文本中"反斜杠+字母"的组合双写为"双反斜杠+字母"。
    这样 \frac, \sin, \nabla, \to, \rho 等 LaTeX 命令不会被
    json.loads 当作合法转义符（\f=换页, \n=换行, \t=制表, \r=回车, \b=退格）解析掉。
    只在 JSON 字符串值内部处理，不影响 JSON 结构字符。
    """
    result = []
    i = 0
    in_string = False
    while i < len(text):
        ch = text[i]
        if not in_string:
            if ch == '"':
                in_string = True
            result.append(ch)
            i += 1
        else:
            if ch == '\\':
                # 看下一个字符
                if i + 1 < len(text):
                    next_ch = text[i + 1]
                    if next_ch.isalpha():
                        # 反斜杠+字母 → 双写反斜杠（保护 LaTeX）
                        result.append('\\\\')
                        result.append(next_ch)
                        i += 2
                    elif next_ch == '"':
                        # \" 是合法 JSON 转义
                        result.append('\\"')
                        i += 2
                    elif next_ch == '\\':
                        # \\ 是合法 JSON 转义
                        result.append('\\\\')
                        i += 2
                    elif next_ch == '/':
                        # \/ 合法但不常见
                        result.append('\\/')
                        i += 2
                    elif next_ch == 'u' and i + 5 < len(text) and all(c in '0123456789abcdefABCDEF' for c in text[i+2:i+6]):
                        # \uXXXX 是 JSON Unicode 转义，保留原样
                        result.append('\\u')
                        result.append(text[i+2:i+6])
                        i += 6
                    elif next_ch in 'bfnrt':
                        # \b \f \n \r \t 是 JSON 标准转义，但更可能是 LaTeX 命令
                        # 双写保护：\frac → \\frac, \nabla → \\nabla 等
                        result.append('\\\\')
                        result.append(next_ch)
                        i += 2
                    else:
                        # 其他情况，双写保护
                        result.append('\\\\')
                        result.append(next_ch)
                        i += 2
                else:
                    result.append(ch)
                    i += 1
            elif ch == '"':
                in_string = False
                result.append(ch)
                i += 1
            else:
                result.append(ch)
                i += 1
    return ''.join(result)


def _safe_json_loads(json_str: str) -> Dict:
    """
    容错 JSON 解析：修复 AI 输出中常见的转义问题后重试。
    """
    import re

    # 第一步：修复字符串内的未转义控制字符（如字面换行符、制表符）
    # AI 有时会在 JSON 字符串值中直接输出换行符而非 \n
    fixed = _escape_control_chars_in_strings(json_str)

    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 第二步：修复 LaTeX 反斜杠
    # AI 返回的 JSON 中包含 LaTeX 公式（如 \sin, \frac, \nabla, \to, \rho）
    # 其中 \f, \n, \t, \r, \b 会被 JSON 当作合法转义而吞掉，导致公式乱码
    # 将所有"反斜杠+字母"的组合中的反斜杠双写，使 JSON 解析后保留原始反斜杠
    fixed2 = re.sub(r'\\(?=[a-zA-Z])', r'\\\\', fixed)
    try:
        return json.loads(fixed2)
    except json.JSONDecodeError:
        pass

    # 第三步：如果还失败，尝试用 eval 安全解析（去掉外层引号后重新构建）
    try:
        import ast
        python_str = fixed2.replace("true", "True").replace("false", "False").replace("null", "None")
        return ast.literal_eval(python_str)
    except (ValueError, SyntaxError):
        pass

    raise ValueError(f"JSON 解析失败，原始内容: {json_str[:300]}...")


def _escape_control_chars_in_strings(s: str) -> str:
    """将 JSON 字符串值内的未转义控制字符替换为转义形式"""
    result = []
    in_string = False
    escaped = False
    for ch in s:
        if not in_string:
            if ch == '"':
                in_string = True
            result.append(ch)
        else:
            if escaped:
                result.append(ch)
                escaped = False
            elif ch == '\\':
                result.append(ch)
                escaped = True
            elif ch == '"':
                result.append(ch)
                in_string = False
            elif ch == '\n':
                result.append('\\n')
            elif ch == '\r':
                result.append('\\r')
            elif ch == '\t':
                result.append('\\t')
            else:
                result.append(ch)
    return ''.join(result)


def _mock_chat(messages: List[Dict]) -> str:
    """
    Mock 模式：不调用真实 API，根据用户消息类型返回预设数据。
    用于开发调试和没有 API Key 的情况。
    """
    # 模拟一点延迟，有真实感
    time.sleep(random.uniform(2.5, 4.0))

    # 看看是诊断请求还是练习请求
    # 检查多个关键词：练习题、选择题、practice、题目
    last_msg = messages[-1]["content"] if messages else ""
    practice_keywords = ["练习题", "选择题", "practice", "题目生成", "生成练习", "针对性练习"]
    is_practice = any(kw in last_msg for kw in practice_keywords)

    if is_practice:
        return _mock_practice_response()
    else:
        return _mock_diagnosis_response()


def _mock_chat(messages: List[Dict]) -> str:
    """
    Mock 模式：不调用真实 API，根据用户消息类型返回预设数据。
    用于开发调试和没有 API Key 的情况。
    """
    time.sleep(random.uniform(2.0, 3.5))

    last_msg = messages[-1]["content"] if messages else ""

    # 判断是诊断、练习还是追问
    practice_keywords = ["练习题", "选择题", "practice", "题目生成", "生成练习", "针对性练习"]
    is_practice = any(kw in last_msg for kw in practice_keywords)

    # 检查是否是追问（messages 中有 system 且包含"追问"或"老师"）
    system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
    is_chat = "追问" in system_msg or "耐心" in system_msg and not is_practice

    if is_practice:
        return _mock_practice_response()
    elif is_chat:
        return _mock_chat_response(last_msg)
    else:
        return _mock_diagnosis_response()


def _mock_diagnosis_response() -> str:
    """Mock 诊断结果（含 Markdown 格式的错因分析）"""
    result = {
        "subject": "高等数学",
        "primary_knowledge_point": {
            "id": "D04",
            "name": "复合函数求导"
        },
        "related_knowledge_points": [
            {"id": "F03", "name": "复合函数"},
            {"id": "D02", "name": "基本求导公式"}
        ],
        "error_type": {
            "id": "E02",
            "name": "公式或法则错误"
        },
        "error_reason": (
            "### 正确部分\n"
            "你正确识别了外层函数 $\\sin$ 的导数公式 $(\\sin u)' = \\cos u$，"
            "说明你对基本求导公式的掌握是到位的。\n\n"
            "### 错误定位\n"
            "问题出现在**链式法则的应用**上。"
            "对于 $f(x) = \\sin(x^2)$，这是一个复合函数：\n"
            "- 外层：$\\sin(u)$，其中 $u = x^2$\n"
            "- 内层：$u = x^2$\n\n"
            "你写出的 $f'(x) = \\cos(x^2)$ 只对外层求了导，"
            "遗漏了内层函数 $x^2$ 的导数 $2x$。\n\n"
            "### 正确做法\n"
            "根据链式法则：\n"
            "$$f'(x) = \\cos(x^2) \\cdot (x^2)' = \\cos(x^2) \\cdot 2x = 2x\\cos(x^2)$$\n\n"
            "### 知识薄弱点分析\n"
            "这个错误反映出你对**复合函数的结构识别**还不够熟练，"
            "特别是当内层函数是多项式时，容易遗漏求导步骤。"
            "建议多练习识别「外层-内层」结构的题目，养成逐步求导的习惯。\n\n"
            "加油！链式法则是微积分的核心工具之一，掌握它后续求导都会变得轻松！"
        ),
        "weakness": "链式法则使用",
        "mastery_estimate": 0.35,
        "recommendation": [
            "第1步：复习复合函数的概念，学会识别 $f(g(x))$ 型函数的外层和内层结构，建议用教材第3章第2节配合视频讲解",
            "第2步：重新学习链式法则公式 $[f(g(x))]' = f'(g(x)) \\cdot g'(x)$，理解每一步的含义和推导过程",
            "第3步：完成3道基础复合函数求导题，如 $\\sin(2x)$、$e^{3x}$、$\\cos(x^2)$，逐步写出外层和内层的导数",
            "第4步：完成2道链式法则综合题，如 $\\ln(\\sin x)$、$e^{\\cos(2x)}$，注意多重复合时的处理顺序",
            "第5步：重新诊断该知识点，检验链式法则的掌握是否提升到 70% 以上"
        ]
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


def _mock_practice_response() -> str:
    """Mock 练习题结果（含详细解答）"""
    result = {
        "questions": [
            {
                "question": "求 $f(x) = \\sin(3x^2 + 1)$ 的导数 $f'(x)$",
                "options": [
                    "$f'(x) = 6x\\cos(3x^2 + 1)$",
                    "$f'(x) = \\cos(3x^2 + 1)$",
                    "$f'(x) = 3x\\cos(3x^2 + 1)$",
                    "$f'(x) = 6x^2\\cos(3x^2 + 1)$"
                ],
                "correct": 0,
                "explanation": (
                    "### 正确答案：A\n\n"
                    "**解题过程：**\n\n"
                    "1. 识别复合结构：外层 $\\sin(u)$，内层 $u = 3x^2 + 1$\n\n"
                    "2. 外层求导：$\\frac{d}{du}\\sin(u) = \\cos(u)$\n\n"
                    "3. 内层求导：$\\frac{d}{dx}(3x^2 + 1) = 6x$\n\n"
                    "4. 链式法则：$f'(x) = \\cos(3x^2 + 1) \\cdot 6x = 6x\\cos(3x^2 + 1)$\n\n"
                    "**其他选项分析：**\n"
                    "- B 错误：遗漏了内层导数 $6x$\n"
                    "- C 错误：内层求导时 $3x^2$ 的导数应为 $6x$ 而非 $3x$\n"
                    "- D 错误：多写了一个 $x$，$6x$ 不应变成 $6x^2$"
                )
            },
            {
                "question": "求 $f(x) = \\cos(x^3)$ 的导数 $f'(x)$",
                "options": [
                    "$f'(x) = -\\sin(x^3)$",
                    "$f'(x) = -3x^2\\sin(x^3)$",
                    "$f'(x) = 3x^2\\sin(x^3)$",
                    "$f'(x) = -3x\\sin(x^3)$"
                ],
                "correct": 1,
                "explanation": (
                    "### 正确答案：B\n\n"
                    "**解题过程：**\n\n"
                    "1. 识别复合结构：外层 $\\cos(u)$，内层 $u = x^3$\n\n"
                    "2. 外层求导：$\\frac{d}{du}\\cos(u) = -\\sin(u)$\n\n"
                    "3. 内层求导：$\\frac{d}{dx}(x^3) = 3x^2$\n\n"
                    "4. 链式法则：$f'(x) = -\\sin(x^3) \\cdot 3x^2 = -3x^2\\sin(x^3)$\n\n"
                    "**其他选项分析：**\n"
                    "- A 错误：遗漏了内层导数 $3x^2$\n"
                    "- C 错误：$\\cos$ 的导数是 $-\\sin$，符号遗漏\n"
                    "- D 错误：$x^3$ 的导数是 $3x^2$ 而非 $3x$"
                )
            },
            {
                "question": "求 $f(x) = e^{2x}$ 的导数 $f'(x)$",
                "options": [
                    "$f'(x) = e^{2x}$",
                    "$f'(x) = 2e^{2x}$",
                    "$f'(x) = x^2 e^{2x}$",
                    "$f'(x) = e^2$"
                ],
                "correct": 1,
                "explanation": (
                    "### 正确答案：B\n\n"
                    "**解题过程：**\n\n"
                    "1. 识别复合结构：外层 $e^u$，内层 $u = 2x$\n\n"
                    "2. 外层求导：$\\frac{d}{du}e^u = e^u$\n\n"
                    "3. 内层求导：$\\frac{d}{dx}(2x) = 2$\n\n"
                    "4. 链式法则：$f'(x) = e^{2x} \\cdot 2 = 2e^{2x}$\n\n"
                    "**其他选项分析：**\n"
                    "- A 错误：遗漏了内层导数 $2$\n"
                    "- C 错误：误将 $e^{2x}$ 当作幂函数处理\n"
                    "- D 错误：完全误解了指数函数的求导规则"
                )
            }
        ]
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


def _mock_chat_response(user_message: str) -> str:
    """Mock 追问回答（含 Markdown 和 LaTeX）"""
    return (
        "## 回答\n\n"
        f"你问的问题是：**{user_message}**\n\n"
        "这是一个很好的问题。让我来详细解答：\n\n"
        "### 关键思路\n"
        "1. 首先识别函数的复合结构\n"
        "2. 分别求外层和内层的导数\n"
        "3. 用链式法则组合起来\n\n"
        "### 公式回顾\n"
        "链式法则的核心公式：\n"
        "$$[f(g(x))]' = f'(g(x)) \\cdot g'(x)$$\n\n"
        "### 示例\n"
        "以 $f(x) = \\sin(x^2)$ 为例：\n"
        "- 外层 $\\sin(u)$ 的导数是 $\\cos(u)$\n"
        "- 内层 $u = x^2$ 的导数是 $2x$\n"
        "- 组合：$f'(x) = \\cos(x^2) \\cdot 2x = 2x\\cos(x^2)$\n\n"
        "希望这个解答对你有帮助！如果还有疑问，请继续追问。"
    )
