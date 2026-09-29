"""
AI 追问路由
===========
诊断后用户可以跟 AI 对话追问。
"""

from flask import Blueprint, request, jsonify
from models.database import get_diagnosis_by_id, get_chat_history, save_chat_message
from ai.llm import chat as llm_chat
from utils.auth import login_required, get_current_user_id
from utils.errors import invalid_request, missing_field, server_error
from utils.logger import logger
import traceback

bp = Blueprint('chat', __name__)


@bp.route('/chat/<int:diagnosis_id>', methods=['POST'])
def chat_with_ai(diagnosis_id):
    """
    AI 追问

    请求体:
        message: 用户的问题

    返回: AI 回答
    """
    try:
        data = request.get_json() or {}
        message = data.get('message', '').strip()

        if not message:
            return missing_field("问题内容")

        diagnosis = get_diagnosis_by_id(diagnosis_id)
        if not diagnosis:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "诊断记录不存在"}}), 404

        # 构建对话上下文
        import json
        diagnosis_result = json.loads(diagnosis['result_json'])

        history = get_chat_history(diagnosis_id)

        # 获取学科
        subject = diagnosis.get('subject', '高等数学') or '高等数学'

        # 系统提示词：告诉 AI 之前的诊断结果
        system_prompt = f"""你是一位耐心的{subject}老师。学生之前提交了一道错题，你已经给出了诊断。

题目：{diagnosis['question']}
学生答案：{diagnosis['student_answer']}
标准答案：{diagnosis['correct_answer']}

诊断结果：
- 知识点：{diagnosis_result.get('primary_knowledge_point', {}).get('name', '')}
- 错误类型：{diagnosis_result.get('error_type', {}).get('name', '')}
- 薄弱环节：{diagnosis_result.get('weakness', '')}
- 错因分析：{diagnosis_result.get('error_reason', '')}

现在学生要追问你问题，请基于之前的诊断上下文，耐心解答。

回答要求：
1. 使用 Markdown 格式排版，合理使用标题、加粗、列表等，使回答条理清晰
2. 数学公式用 LaTeX 语法书写，行内公式用 $...$ 包裹，独立公式用 $$...$$ 包裹
3. 回答要有层次感，先给出结论，再详细解释
4. 如果涉及分步骤解答，用有序列表标明步骤
5. 回答要清晰、具体、有教学价值"""

        messages = [{"role": "system", "content": system_prompt}]

        for msg in history:
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })

        messages.append({"role": "user", "content": message})

        # 保存用户消息
        save_chat_message(diagnosis_id, "user", message)

        # 调用 AI
        ai_reply = llm_chat(messages)

        # 保存 AI 回复
        save_chat_message(diagnosis_id, "assistant", ai_reply)

        logger.info(f"追问成功: diagnosis_id={diagnosis_id}")
        return jsonify({"reply": ai_reply}), 200

    except Exception as e:
        logger.error(f"追问失败: {e}")
        traceback.print_exc()
        return server_error("AI 回答失败，请稍后重试")


@bp.route('/chat/<int:diagnosis_id>', methods=['GET'])
def get_chat_messages(diagnosis_id):
    """获取某个诊断的追问历史"""
    history = get_chat_history(diagnosis_id)
    return jsonify({"messages": history}), 200
