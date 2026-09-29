"""
日志系统
=======
统一管理应用日志，替代 print()。
"""

import logging
import sys
from datetime import datetime


def setup_logger(name="app", level=logging.INFO):
    """创建并返回一个配置好的 logger"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )
    handler.setFormatter(fmt)
    logger.addHandler(handler)

    return logger


# 全局 logger 实例
logger = setup_logger()
