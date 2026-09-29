"""
练习路由
========
处理练习题生成相关的 API 请求。
优先从题库抽题，不足时 AI 生成补充。
练习结果通过 BKT 模型更新掌握度。
"""

from flask import Blueprint, request, jsonify
from ai.diagnosis import generate_practice_questions
from models.database import save_practice_record
from models.question_bank import get_questions_from_bank, get_questions_by_kp_id
from ai.knowledge_tracing import update_knowledge_state
from utils.auth import get_current_user_id
from utils.errors import invalid_request, server_error
from utils.logger import logger
import traceback

bp = Blueprint('practice', __name__)


@bp.route('/practice', methods=['POST'])
def create_practice():
    """生成针对性练习题（题库优先 + AI 兜底 / 可选 source 参数）"""
    try:
        data = request.get_json() or {}
        weakness = data.get('weakness', '链式法则使用')
        count = data.get('count', 3)
        diagnosis_id = data.get('diagnosis_id')
        subject = data.get('subject', '高等数学')
        source = data.get('source', 'auto')  # auto | bank | ai
        kp_id = data.get('kp_id')  # 图谱节点ID，用于精准匹配题库

        logger.info(f"生成练习题: subject={subject}, 薄弱点={weakness}, 数量={count}, 来源={source}, kp_id={kp_id}")

        questions = []

        # 如果有 kp_id，优先用图谱精准映射抽题
        if kp_id:
            bank_questions = get_questions_by_kp_id(kp_id, count)
            questions.extend(bank_questions)

            if len(questions) < count and source != 'bank':
                need = count - len(questions)
                logger.info(f"图谱题库不足({len(questions)}/{count})，AI 生成 {need} 道补充")
                try:
                    ai_questions = generate_practice_questions(weakness, need, subject=subject)
                    for q in ai_questions:
                        q['source'] = 'AI生成'
                    questions.extend(ai_questions)
                except Exception as e:
                    logger.warning(f"AI 生成练习题失败: {e}")

        elif source == 'ai':
            # 全部 AI 生成
            try:
                ai_questions = generate_practice_questions(weakness, count, subject=subject)
                for q in ai_questions:
                    q['source'] = 'AI生成'
                questions.extend(ai_questions)
            except Exception as e:
                logger.warning(f"AI 生成练习题失败: {e}")
                # 回退到题库
                questions = get_questions_from_bank(subject, weakness, count)

        elif source == 'bank':
            # 仅题库抽题
            questions = get_questions_from_bank(subject, weakness, count)
            if len(questions) < count:
                logger.info(f"题库不足({len(questions)}/{count})，题库模式不补充")

        else:
            # auto: 题库优先 + AI 兜底
            questions = get_questions_from_bank(subject, weakness, count)
            if len(questions) < count:
                need = count - len(questions)
                logger.info(f"题库不足({len(questions)}/{count})，AI 生成 {need} 道补充")
                try:
                    ai_questions = generate_practice_questions(weakness, need, subject=subject)
                    for q in ai_questions:
                        q['source'] = 'AI生成'
                    questions.extend(ai_questions)
                except Exception as e:
                    logger.warning(f"AI 生成练习题失败: {e}")
                    if not questions:
                        raise

        logger.info(f"练习题生成完成: {len(questions)}道 (题库{sum(1 for q in questions if q.get('source')=='题库')} + AI{sum(1 for q in questions if q.get('source')=='AI生成')})")
        return jsonify({
            "weakness": weakness,
            "questions": questions[:count]
        }), 200

    except Exception as e:
        logger.error(f"练习题生成失败: {e}")
        traceback.print_exc()
        return server_error("练习题生成失败，请稍后重试")


@bp.route('/practice/record', methods=['POST'])
def submit_practice_record():
    """提交练习结果记录 + BKT 掌握度更新"""
    try:
        data = request.get_json()
        if not data:
            return invalid_request()

        user_id = get_current_user_id()
        weakness = data.get('weakness', '')
        subject = data.get('subject', '高等数学')
        total = data.get('total', 0)
        correct = data.get('correct', 0)

        record_id = save_practice_record(
            diagnosis_id=data.get('diagnosis_id'),
            weakness=weakness,
            accuracy=data.get('accuracy', 0),
            total=total,
            correct=correct,
            user_id=user_id
        )

        # BKT: 根据每题正误更新掌握度
        if user_id and weakness and total > 0:
            results = data.get('results', [])
            if not results:
                # 没有逐题结果，按正确率近似
                for _ in range(correct):
                    update_knowledge_state(user_id, weakness, subject, is_correct=True)
                for _ in range(total - correct):
                    update_knowledge_state(user_id, weakness, subject, is_correct=False)
            else:
                for r in results:
                    update_knowledge_state(user_id, weakness, subject, is_correct=r.get('correct', False))

        return jsonify({"record_id": record_id, "status": "saved"}), 200

    except Exception as e:
        logger.error(f"练习记录保存失败: {e}")
        return server_error("保存练习记录失败")
