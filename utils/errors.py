"""
统一错误处理
===========
所有 API 错误返回统一格式：
{
    "error": {
        "code": "ERROR_CODE",
        "message": "用户可读的错误信息"
    }
}
"""

from flask import jsonify


def error_response(code, message, status=400):
    """生成统一格式的错误响应"""
    return jsonify({
        "error": {
            "code": code,
            "message": message
        }
    }), status


def invalid_request(message="请求体不能为空"):
    """400 - 请求格式错误"""
    return error_response("INVALID_REQUEST", message, 400)


def missing_field(field_name):
    """400 - 缺少必填字段"""
    return error_response("MISSING_FIELD", f"请输入{field_name}", 400)


def server_error(message="服务暂时不可用，请稍后重试"):
    """500 - 服务器内部错误"""
    return error_response("INTERNAL_ERROR", message, 500)
