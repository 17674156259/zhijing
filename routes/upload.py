"""
图片上传路由
============
接收用户上传的题目图片，保存到 uploads 目录。
"""

import os
import uuid
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from utils.errors import invalid_request, server_error
from utils.logger import logger

bp = Blueprint('upload', __name__)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/upload', methods=['POST'])
def upload_image():
    """上传图片，返回图片路径"""
    try:
        if 'file' not in request.files:
            return invalid_request("请选择图片文件")

        file = request.files['file']
        if not file.filename:
            return invalid_request("请选择图片文件")

        if not _allowed_file(file.filename):
            return jsonify({"error": {"code": "INVALID_FILE", "message": "仅支持 PNG/JPG/GIF/WebP 格式"}}), 400

        # 确保上传目录存在
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        # 生成唯一文件名
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex[:16]}.{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        file.save(filepath)

        logger.info(f"图片上传成功: {filename}")

        return jsonify({
            "path": f"/uploads/{filename}",
            "filename": filename
        }), 200

    except Exception as e:
        logger.error(f"图片上传失败: {e}")
        return server_error("图片上传失败")
