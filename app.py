"""
AI 错题诊断助手 - 后端服务入口
=============================

职责：
1. 创建 Flask 应用
2. 注册路由蓝图
3. 初始化数据库
4. 启动服务
"""

from flask import Flask, send_from_directory
from flask_cors import CORS
from config import Config
from models.database import init_db
from routes.diagnosis import bp as diagnosis_bp
from routes.practice import bp as practice_bp
from routes.history import bp as history_bp
from routes.auth import bp as auth_bp
from routes.chat import bp as chat_bp
from routes.dashboard import bp as dashboard_bp
from routes.upload import bp as upload_bp
from routes.ocr import bp as ocr_bp
from routes.teacher import bp as teacher_bp
from ai.llm import get_config
from utils.logger import logger
from utils.rate_limit import rate_limit_middleware
from models.question_bank import init_question_bank
import os


def create_app():
    """创建并配置 Flask 应用"""
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config.from_object(Config)
    CORS(app)

    # 接口限流
    rate_limit_middleware(app)

    # 注册 API 蓝图
    app.register_blueprint(diagnosis_bp, url_prefix='/api')
    app.register_blueprint(practice_bp, url_prefix='/api')
    app.register_blueprint(history_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(chat_bp, url_prefix='/api')
    app.register_blueprint(dashboard_bp, url_prefix='/api')
    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(ocr_bp, url_prefix='/api')
    app.register_blueprint(teacher_bp, url_prefix='/api')

    # 页面路由
    @app.route('/')
    def index():
        return send_from_directory('.', 'index.html')

    # 上传文件静态服务
    UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        return send_from_directory(UPLOAD_DIR, filename)

    # 健康检查
    @app.route('/api/health')
    def health():
        return {"status": "ok", "service": "AI 错题诊断助手"}, 200

    return app


app = create_app()


if __name__ == '__main__':
    init_db()
    init_question_bank()

    print("=" * 50)
    print("  AI 错题诊断助手 - 后端服务")
    print("=" * 50)
    print()
    print(f"  访问地址: http://localhost:5000")
    print(f"  健康检查: http://localhost:5000/api/health")
    print(f"  历史记录: http://localhost:5000/api/history")
    print()

    llm_config = get_config()
    print(f"  AI 模型提供商: {llm_config['provider']}")
    if llm_config['provider'] != 'mock':
        print(f"  模型名称: {llm_config['model']}")
    else:
        print("  (使用 Mock 数据，无需 API Key)")
    print()

    app.run(host='0.0.0.0', port=5000, debug=False)
