"""
历史记录路由
============
查看过往的诊断记录、收藏/取消收藏、删除、添加备注。
"""

from flask import Blueprint, request, jsonify
from models.database import (
    get_diagnosis_list, get_diagnosis_by_id,
    update_diagnosis_favorite, update_diagnosis_notes, delete_diagnosis,
    get_knowledge_stats
)
from utils.auth import get_current_user_id
from utils.errors import server_error
from utils.logger import logger
import json

bp = Blueprint('history', __name__)


@bp.route('/history', methods=['GET'])
def list_history():
    """获取诊断历史列表，支持筛选"""
    try:
        user_id = get_current_user_id()
        favorite_only = request.args.get('favorite') == '1'
        kp = request.args.get('kp', '').strip()

        records = get_diagnosis_list(limit=50, user_id=user_id, favorite_only=favorite_only)

        if kp:
            records = [r for r in records if r.get('knowledge_point') == kp]

        for r in records:
            if 'result_json' in r:
                try:
                    parsed = json.loads(r['result_json'])
                    r['error_reason'] = parsed.get('error_reason', '')
                    r['recommendation'] = parsed.get('recommendation', [])
                    r['error_type'] = parsed.get('error_type', {})
                    r['primary_knowledge_point'] = parsed.get('primary_knowledge_point', {})
                except (json.JSONDecodeError, TypeError):
                    r['error_reason'] = ''
                    r['recommendation'] = []
                del r['result_json']

        return jsonify({"records": records}), 200
    except Exception as e:
        logger.error(f"获取历史记录失败: {e}")
        return server_error("获取历史记录失败")


@bp.route('/history/<int:record_id>', methods=['GET'])
def get_history_detail(record_id):
    """获取某条诊断记录的完整信息"""
    try:
        record = get_diagnosis_by_id(record_id)
        if not record:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "记录不存在"}}), 404

        record['result'] = json.loads(record['result_json'])
        del record['result_json']
        return jsonify(record), 200
    except Exception as e:
        logger.error(f"获取诊断详情失败: {e}")
        return server_error("获取诊断详情失败")


@bp.route('/history/<int:record_id>/favorite', methods=['POST'])
def toggle_favorite(record_id):
    """收藏/取消收藏"""
    try:
        data = request.get_json() or {}
        is_favorite = data.get('is_favorite', True)
        update_diagnosis_favorite(record_id, is_favorite)
        return jsonify({"record_id": record_id, "is_favorite": is_favorite}), 200
    except Exception as e:
        logger.error(f"更新收藏状态失败: {e}")
        return server_error("操作失败")


@bp.route('/history/<int:record_id>/notes', methods=['POST'])
def update_notes(record_id):
    """更新备注"""
    try:
        data = request.get_json() or {}
        notes = data.get('notes', '').strip()
        update_diagnosis_notes(record_id, notes)
        return jsonify({"record_id": record_id, "notes": notes}), 200
    except Exception as e:
        logger.error(f"更新备注失败: {e}")
        return server_error("操作失败")


@bp.route('/history/<int:record_id>', methods=['DELETE'])
def remove_diagnosis(record_id):
    """删除诊断记录"""
    try:
        delete_diagnosis(record_id)
        logger.info(f"诊断记录已删除: id={record_id}")
        return jsonify({"deleted": True}), 200
    except Exception as e:
        logger.error(f"删除诊断记录失败: {e}")
        return server_error("删除失败")


@bp.route('/knowledge-stats', methods=['GET'])
def knowledge_stats():
    """按知识点统计"""
    try:
        user_id = get_current_user_id()
        stats = get_knowledge_stats(user_id=user_id)
        return jsonify({"stats": stats}), 200
    except Exception as e:
        logger.error(f"获取知识点统计失败: {e}")
        return server_error("获取统计失败")
