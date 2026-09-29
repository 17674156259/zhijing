"""
看板路由
========
学习进度看板的数据接口。
"""

from flask import Blueprint, jsonify, request
from models.database import (
    get_dashboard_stats, get_knowledge_stats, get_practice_trend,
    get_knowledge_graph, get_prerequisites
)
from utils.auth import login_required, get_current_user_id
from utils.errors import server_error
from utils.logger import logger

bp = Blueprint('dashboard', __name__)


@bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """获取看板数据"""
    try:
        user_id = get_current_user_id()
        if not user_id:
            # 未登录用户返回空数据
            return jsonify({
                "diagnosis": {"total_diagnoses": 0, "avg_mastery": 0, "favorites": 0},
                "practice": {"total_sessions": 0, "avg_accuracy": 0, "total_questions": 0, "total_correct": 0},
                "weakness_distribution": [],
                "mastery_trend": [],
                "knowledge_stats": [],
                "practice_trend": []
            }), 200

        stats = get_dashboard_stats(user_id)
        stats["knowledge_stats"] = get_knowledge_stats(user_id)
        stats["practice_trend"] = get_practice_trend(user_id)

        return jsonify(stats), 200

    except Exception as e:
        logger.error(f"获取看板数据失败: {e}")
        return server_error("获取看板数据失败")


@bp.route('/knowledge-graph', methods=['GET'])
def knowledge_graph():
    """获取知识点图谱数据"""
    try:
        graph = get_knowledge_graph()
        user_id = get_current_user_id()

        if user_id:
            stats = get_knowledge_stats(user_id)
            mastery_map = {s['knowledge_point']: s.get('avg_mastery', 0) for s in stats}
            diag_count_map = {s['knowledge_point']: s.get('count', 0) for s in stats}
            for node in graph['nodes']:
                m = mastery_map.get(node['name'], 0)
                node['mastery'] = round(m * 100) if m else 0
                node['diag_count'] = diag_count_map.get(node['name'], 0)
        else:
            for node in graph['nodes']:
                node['mastery'] = 0
                node['diag_count'] = 0

        return jsonify(graph), 200
    except Exception as e:
        logger.error(f"获取知识图谱失败: {e}")
        return server_error("获取知识图谱失败")


@bp.route('/prerequisites', methods=['GET'])
def prerequisites():
    """获取某知识点的前置知识"""
    try:
        kp_name = request.args.get('kp', '').strip()
        if not kp_name:
            return jsonify({"prerequisites": []}), 200
        prereqs = get_prerequisites(kp_name)
        return jsonify({"knowledge_point": kp_name, "prerequisites": prereqs}), 200
    except Exception as e:
        logger.error(f"获取前置知识失败: {e}")
        return server_error("获取前置知识失败")
