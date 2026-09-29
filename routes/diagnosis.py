"""
诊断路由
========
处理错题诊断相关的 API 请求。支持多学科、图片上传、SSE 流式输出和缓存。
"""

from flask import Blueprint, request, jsonify, Response
import json
import hashlib
from ai.diagnosis import diagnose, diagnose_stream, _validate_result
from ai.llm import _parse_json
from models.database import save_diagnosis
from utils.auth import get_current_user_id
from utils.errors import invalid_request, missing_field, server_error
from utils.cache import cache_get, cache_set
from utils.logger import logger
import traceback

bp = Blueprint('diagnosis', __name__)


def _cache_key(question, student_answer, correct_answer, subject):
    raw = f"{subject}|{question}|{student_answer}|{correct_answer}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


@bp.route('/diagnosis', methods=['POST'])
def create_diagnosis():
    """错题诊断接口（非流式，带缓存）"""
    try:
        data = request.get_json()
        if not data:
            return invalid_request()

        question = data.get('question', '').strip()
        student_answer = data.get('student_answer', '').strip()
        correct_answer = data.get('correct_answer', '').strip()
        subject = data.get('subject', '高等数学').strip()
        image_path = data.get('image_path')

        if not question:
            return missing_field("题目")
        if not student_answer:
            return missing_field("学生答案")
        if not correct_answer:
            return missing_field("标准答案")

        user_id = get_current_user_id()

        # 缓存检查
        key = _cache_key(question, student_answer, correct_answer, subject)
        cached = cache_get(key)
        if cached:
            cached['cached'] = True
            return jsonify(cached), 200

        logger.info(f"开始诊断: user_id={user_id}, subject={subject}, 题目={question[:30]}...")

        result = diagnose(question, student_answer, correct_answer, subject=subject)

        record_id = save_diagnosis(
            question, student_answer, correct_answer, result,
            user_id=user_id, subject=subject, image_path=image_path
        )
        result['record_id'] = record_id

        # 写入缓存
        cache_set(key, result, ttl=3600)

        logger.info(f"诊断完成: record_id={record_id}")
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"诊断失败: {e}")
        traceback.print_exc()
        return server_error("诊断服务暂时不可用，请稍后重试")


@bp.route('/diagnosis/stream', methods=['POST'])
def create_diagnosis_stream():
    """
    流式诊断接口 (SSE)
    前端通过 fetch + ReadableStream 接收逐字输出。
    """
    data = request.get_json()
    if not data:
        return invalid_request()

    question = data.get('question', '').strip()
    student_answer = data.get('student_answer', '').strip()
    correct_answer = data.get('correct_answer', '').strip()
    subject = data.get('subject', '高等数学').strip()
    image_path = data.get('image_path')

    if not question:
        return missing_field("题目")
    if not student_answer:
        return missing_field("学生答案")
    if not correct_answer:
        return missing_field("标准答案")

    user_id = get_current_user_id()

    # 缓存检查：如果有缓存直接一次性返回
    key = _cache_key(question, student_answer, correct_answer, subject)
    cached = cache_get(key)
    if cached:
        # 缓存命中时仍为当前用户保存一条新记录
        record_id = save_diagnosis(
            question, student_answer, correct_answer, cached,
            user_id=user_id, subject=subject, image_path=image_path
        )
        cached['record_id'] = record_id
        cached['cached'] = True

        def cached_stream():
            yield f"data: {json.dumps({'type': 'done', 'result': cached}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        return Response(cached_stream(), mimetype='text/event-stream')

    def generate():
        full_text = ""
        try:
            for chunk in diagnose_stream(question, student_answer, correct_answer, subject=subject):
                full_text += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"

            # 解析完整 JSON
            try:
                result = _parse_json(full_text)
                result = _validate_result(result, subject)
            except Exception:
                result = {
                    "subject": subject,
                    "primary_knowledge_point": {"id": "UNKNOWN", "name": "解析失败"},
                    "error_type": {"id": "E07", "name": "其他"},
                    "error_reason": full_text[:500] or "诊断结果解析失败",
                    "weakness": "未知",
                    "mastery_estimate": 0.5,
                    "recommendation": ["请重新尝试诊断"],
                }

            record_id = save_diagnosis(
                question, student_answer, correct_answer, result,
                user_id=user_id, subject=subject, image_path=image_path
            )
            result['record_id'] = record_id

            # 写入缓存
            cache_set(key, result, ttl=3600)

            yield f"data: {json.dumps({'type': 'done', 'result': result}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"流式诊断失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return Response(generate(), mimetype='text/event-stream')
