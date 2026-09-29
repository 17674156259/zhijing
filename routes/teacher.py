"""
教师路由
========
教师创建班级、查看班级看板、管理学生。
"""

from flask import Blueprint, request, jsonify, g
from models.database import (
    create_class, get_classes_by_teacher, get_class_by_code,
    get_class_students, get_class_dashboard, update_user_class
)
from utils.auth import login_required, get_current_user_id
from utils.errors import invalid_request, missing_field, error_response, server_error
from utils.logger import logger

bp = Blueprint('teacher', __name__)


@bp.route('/teacher/classes', methods=['GET'])
@login_required
def list_classes():
    """获取教师创建的班级列表"""
    try:
        user = g.current_user
        if user.get('role') != 'teacher':
            return error_response("FORBIDDEN", "仅教师可访问", 403)
        classes = get_classes_by_teacher(user['id'])
        return jsonify({"classes": classes}), 200
    except Exception as e:
        logger.error(f"获取班级列表失败: {e}")
        return server_error("获取班级列表失败")


@bp.route('/teacher/class', methods=['POST'])
@login_required
def create_new_class():
    """创建班级"""
    try:
        user = g.current_user
        if user.get('role') != 'teacher':
            return error_response("FORBIDDEN", "仅教师可创建班级", 403)

        data = request.get_json() or {}
        name = data.get('name', '').strip()
        if not name:
            return missing_field("班级名称")

        result = create_class(name, user['id'])
        return jsonify(result), 201
    except Exception as e:
        logger.error(f"创建班级失败: {e}")
        return server_error("创建班级失败")


@bp.route('/teacher/class/<code>', methods=['GET'])
@login_required
def get_class_detail(code):
    """获取班级详情（学生列表 + 看板数据）"""
    try:
        user = g.current_user
        if user.get('role') != 'teacher':
            return error_response("FORBIDDEN", "仅教师可访问", 403)

        cls = get_class_by_code(code)
        if not cls:
            return error_response("NOT_FOUND", "班级不存在", 404)
        if cls['teacher_id'] != user['id']:
            return error_response("FORBIDDEN", "无权访问此班级", 403)

        students = get_class_students(code)
        dashboard = get_class_dashboard(code)
        return jsonify({
            "class_info": cls,
            "students": students,
            "dashboard": dashboard
        }), 200
    except Exception as e:
        logger.error(f"获取班级详情失败: {e}")
        return server_error("获取班级详情失败")


@bp.route('/student/join-class', methods=['POST'])
@login_required
def join_class():
    """学生加入班级"""
    try:
        user = g.current_user
        if user.get('role') != 'student':
            return error_response("FORBIDDEN", "仅学生可加入班级", 403)

        data = request.get_json() or {}
        code = data.get('class_code', '').strip().upper()

        if not code:
            update_user_class(user['id'], None)
            return jsonify({"class": None, "message": "已退出班级"}), 200

        cls = get_class_by_code(code)
        if not cls:
            return error_response("CLASS_NOT_FOUND", "班级码无效", 404)

        update_user_class(user['id'], code)
        return jsonify({"class": cls}), 200
    except Exception as e:
        logger.error(f"加入班级失败: {e}")
        return server_error("加入班级失败")
