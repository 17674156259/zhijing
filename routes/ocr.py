"""
OCR 图片识别路由
================
接收裁剪后的图片，调用 LLM 视觉能力识别题目和答案，智能拆分填入对应字段。
"""

import re
import base64
from flask import Blueprint, request, jsonify
from ai.llm import chat_vision, chat_json, get_config, get_vision_config
from utils.errors import invalid_request, server_error
from utils.logger import logger
import traceback

bp = Blueprint('ocr', __name__)


@bp.route('/ocr/scan', methods=['POST'])
def scan_image():
    """
    图片 OCR 识别

    请求体:
        image: base64 编码的图片数据（不含 data:image/xxx;base64, 前缀）
        subject: 学科名称（可选，帮助 AI 理解上下文）

    返回:
        question: 识别出的题目
        student_answer: 识别出的学生答案
        correct_answer: 识别出的标准答案
    """
    try:
        data = request.get_json() or {}
        image_b64 = data.get('image', '')
        subject = data.get('subject', '高等数学')

        if not image_b64:
            return invalid_request("请提供图片数据")

        config = get_vision_config()

        if config["provider"] == "mock":
            return jsonify(_mock_ocr_result()), 200

        system_prompt = """你是OCR识别引擎，只输出JSON，不输出任何其他文字。

任务：识别图片中的数学题目和答案。

规则：
1. 数学公式用LaTeX格式：行内用$...$，独立公式用$$...$$
2. 识别题目原文，不要改写或简化
3. 如果只有题目没有答案，student_answer和correct_answer留空字符串
4. 如果有学生作答，填入student_answer
5. 如果有标准答案，填入correct_answer

只输出以下JSON，不要加任何解释、前缀或后缀：
{"question": "题目原文", "student_answer": "学生答案或空", "correct_answer": "标准答案或空"}"""

        user_prompt = f"请识别这张{subject}题目图片中的内容。"

        result = chat_vision(system_prompt, user_prompt, image_b64, temperature=0.1)

        # 后处理：确保 LaTeX 公式被 $...$ 包裹，否则前端 KaTeX 无法渲染
        for key in ("question", "student_answer", "correct_answer"):
            if result.get(key):
                original = result[key]
                result[key] = _ensure_latex_delimiters(original)
                if result[key] != original:
                    logger.info(f"OCR {key} 已补充 LaTeX 分隔符: {original[:60]}...")

        logger.info(f"OCR 识别完成: question长度={len(result.get('question', ''))}")
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"OCR 识别失败: {e}")
        traceback.print_exc()
        return server_error("图片识别失败，请稍后重试或手动输入")


def _mock_ocr_result():
    return {
        "question": "求函数 $f(x) = \\sin(x^2)$ 的导数 $f'(x)$",
        "student_answer": "$f'(x) = \\cos(x^2)$",
        "correct_answer": "$f'(x) = 2x\\cos(x^2)$"
    }


# 常见 LaTeX 命令列表，用于检测未包裹的公式
_LATEX_COMMANDS = re.compile(
    r'\\(?:'
    r'frac|sqrt|sum|int|lim|infty|partial|nabla|'
    r'sin|cos|tan|cot|sec|csc|arcsin|arccos|arctan|'
    r'log|ln|exp|'
    r'alpha|beta|gamma|delta|epsilon|theta|lambda|mu|pi|rho|sigma|phi|omega|'
    r'cdot|times|div|pm|mp|leq|geq|neq|approx|equiv|'
    r'left|right|over|under|hat|bar|vec|dot|'
    r'infty|partial|forall|exists|'
    r'mathbb|mathcal|mathbf|'
    r'dfrac|tfrac|binom|'
    r'in|notin|subset|supset|cup|cap|'
    r'angle|perp|parallel|'
    r'rightarrow|leftarrow|Rightarrow|Leftarrow|'
    r'leq|geq|neq|le|ge|'
    r'quad|qquad|'
    r'degree|circ|'
    r'propto|sim|'
    r'max|min|sup|inf|'
    r'det|dim|ker|'
    r'nabla|grad|div|rot|curl|'
    r'overset|underset|stackrel'
    r')\b'
)


def _ensure_latex_delimiters(text):
    """
    确保文本中的 LaTeX 公式被 $...$ 包裹。
    如果检测到 LaTeX 命令但没有 $ 分隔符，自动包裹。
    """
    if not text or '$' in text:
        return text

    if not _LATEX_COMMANDS.search(text):
        return text

    # 按中文字符分割，把含 LaTeX 命令的非中文片段用 $...$ 包裹
    parts = re.split(r'([\u4e00-\u9fff]+)', text)
    result = []
    for part in parts:
        if part and _LATEX_COMMANDS.search(part):
            stripped = part.strip()
            if stripped:
                prefix = part[:len(part) - len(part.lstrip())]
                suffix = part[len(part.rstrip()):]
                result.append(f'{prefix}${stripped}${suffix}')
            else:
                result.append(part)
        else:
            result.append(part)
    return ''.join(result)
