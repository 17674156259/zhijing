"""
接口限流中间件
================
滑动窗口算法，按 IP 限流。
"""

import time
from collections import defaultdict, deque
from functools import wraps
from flask import request, jsonify, g
from utils.logger import logger

# 滑动窗口: { ip: deque([timestamp, ...]) }
_windows: dict = defaultdict(deque)

# 默认限流: 60秒内最多30次请求
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 30

# AI 接口更严格: 120秒内最多10次
AI_RATE_LIMIT_WINDOW = 120
AI_RATE_LIMIT_MAX = 10

AI_PATHS = ['/api/diagnosis', '/api/practice', '/api/chat/', '/api/ocr/scan']

# 不走 AI 限流的特殊路径（虽然前缀匹配，但不是 AI 调用）
AI_EXCLUDE_PATHS = ['/api/practice/record']


def rate_limit_middleware(app):
    """注册为 Flask before_request 钩子"""

    @app.before_request
    def _check_rate_limit():
        if not request.path.startswith('/api/'):
            return

        ip = request.remote_addr or 'unknown'
        now = time.time()

        is_ai = any(request.path.startswith(p) for p in AI_PATHS) and request.path not in AI_EXCLUDE_PATHS
        window = AI_RATE_LIMIT_WINDOW if is_ai else RATE_LIMIT_WINDOW
        max_req = AI_RATE_LIMIT_MAX if is_ai else RATE_LIMIT_MAX

        key = f"{ip}:{'ai' if is_ai else 'general'}"
        w = _windows[key]

        while w and w[0] < now - window:
            w.popleft()

        if len(w) >= max_req:
            logger.warning(f"限流触发: ip={ip}, path={request.path}, count={len(w)}")
            return jsonify({
                "error": {
                    "code": "RATE_LIMITED",
                    "message": f"请求过于频繁，请{int(window)}秒后重试"
                }
            }), 429

        w.append(now)
        g.rate_limit_remaining = max_req - len(w)
