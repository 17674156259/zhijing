"""
认证路由
========
用户注册、登录、获取当前用户信息。
"""

from flask import Blueprint, request, jsonify, g
from models.database import create_user, get_user_by_username
from utils.auth import hash_password, verify_password, create_token, login_required
from utils.errors import invalid_request, missing_field, error_response
from utils.logger import logger

bp = Blueprint('auth', __name__)


@bp.route('/auth/register', methods=['POST'])
def register():
    """
    用户注册

    请求体:
        username: 用户名（3-20字符）
        password: 密码（6位以上）

    返回: JWT token + 用户信息
    """
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'student').strip()
    class_code = data.get('class_code', '').strip().upper() or None

    if not username:
        return missing_field("用户名")
    if len(username) < 3 or len(username) > 20:
        return error_response("INVALID_USERNAME", "用户名需要3-20个字符", 400)
    if not password:
        return missing_field("密码")
    if len(password) < 6:
        return error_response("INVALID_PASSWORD", "密码至少6位", 400)
    if not any(c.isalpha() for c in password):
        return error_response("INVALID_PASSWORD", "密码需要包含字母", 400)
    if not any(c.isdigit() for c in password):
        return error_response("INVALID_PASSWORD", "密码需要包含数字", 400)
    if role not in ('student', 'teacher'):
        return error_response("INVALID_ROLE", "角色必须是学生或教师", 400)

    existing = get_user_by_username(username)
    if existing:
        return error_response("USERNAME_EXISTS", "用户名已被注册", 409)

    user_id = create_user(username, hash_password(password), username, role=role, class_code=class_code)
    token = create_token(user_id, username)

    logger.info(f"用户注册成功: {username}, role={role}")
    return jsonify({
        "token": token,
        "user": {"id": user_id, "username": username, "nickname": username, "role": role, "class_code": class_code}
    }), 201


@bp.route('/auth/login', methods=['POST'])
def login():
    """
    用户登录

    请求体:
        username: 用户名
        password: 密码

    返回: JWT token + 用户信息
    """
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username:
        return missing_field("用户名")
    if not password:
        return missing_field("密码")

    user = get_user_by_username(username)
    if not user or not verify_password(password, user['password_hash']):
        return error_response("AUTH_FAILED", "用户名或密码错误", 401)

    token = create_token(user['id'], user['username'])

    logger.info(f"用户登录: {username}, role={user.get('role', 'student')}")
    return jsonify({
        "token": token,
        "user": {
            "id": user['id'],
            "username": user['username'],
            "nickname": user.get('nickname') or user['username'],
            "role": user.get('role', 'student'),
            "class_code": user.get('class_code'),
            "class_name": user.get('class_name')
        }
    }), 200


@bp.route('/auth/me', methods=['GET'])
@login_required
def get_profile():
    """获取当前登录用户信息"""
    return jsonify({"user": g.current_user}), 200
