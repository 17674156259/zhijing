"""
认证工具
=======
密码哈希 + JWT 生成/验证。
"""

import hashlib
import hmac
import json
import base64
import time
from config import Config
from functools import wraps
from flask import request, g
from utils.errors import error_response
from models.database import get_user_by_id

# 简单的密码哈希（不依赖 bcrypt，用 werkzeug）
from werkzeug.security import generate_password_hash, check_password_hash


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password, password_hash):
    return check_password_hash(password_hash, password)


# ===== 简易 JWT（不依赖 PyJWT） =====

def _b64encode(data):
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b'=').decode()


def _b64decode(s):
    padding = 4 - len(s) % 4
    if padding != 4:
        s += '=' * padding
    return json.loads(base64.urlsafe_b64decode(s))


def create_token(user_id, username):
    """生成 JWT token"""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": int(time.time()) + 7 * 24 * 3600  # 7 天过期
    }
    header_b64 = _b64encode(header)
    payload_b64 = _b64encode(payload)
    signature = hmac.new(
        Config.SECRET_KEY.encode(),
        f"{header_b64}.{payload_b64}".encode(),
        hashlib.sha256
    ).hexdigest()
    return f"{header_b64}.{payload_b64}.{signature}"


def verify_token(token):
    """验证 JWT token，返回 payload 或 None"""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature = parts
        expected_sig = hmac.new(
            Config.SECRET_KEY.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return None

        payload = _b64decode(payload_b64)
        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None


def login_required(f):
    """装饰器：要求用户登录"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return error_response("UNAUTHORIZED", "请先登录", 401)

        token = auth_header[7:]
        payload = verify_token(token)
        if not payload:
            return error_response("TOKEN_INVALID", "登录已过期，请重新登录", 401)

        user = get_user_by_id(payload['user_id'])
        if not user:
            return error_response("USER_NOT_FOUND", "用户不存在", 401)

        g.current_user = user
        return f(*args, **kwargs)
    return decorated


def get_current_user_id():
    """获取当前登录用户 ID（未登录返回 None）"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header[7:]
    payload = verify_token(token)
    return payload['user_id'] if payload else None
