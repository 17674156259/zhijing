"""
内存缓存层
==========
轻量替代 Redis，带 TTL 自动过期。
用于缓存重复诊断结果，降低 API 成本。
"""

import time
import hashlib
import json
from functools import wraps
from utils.logger import logger

_cache: dict = {}

# 默认 TTL: 1 小时
DEFAULT_TTL = 3600


def _make_key(*args) -> str:
    """根据参数生成缓存键"""
    raw = json.dumps(args, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def cache_get(key: str):
    """获取缓存，不存在返回 None"""
    entry = _cache.get(key)
    if not entry:
        return None
    if time.time() > entry["expire"]:
        del _cache[key]
        return None
    logger.info(f"缓存命中: {key[:12]}...")
    return entry["data"]


def cache_set(key: str, data, ttl: int = DEFAULT_TTL):
    """写入缓存"""
    _cache[key] = {"data": data, "expire": time.time() + ttl}
    logger.info(f"缓存写入: {key[:12]}..., TTL={ttl}s")


def cached(ttl: int = DEFAULT_TTL):
    """
    装饰器：缓存函数返回值。
    用函数名+参数生成缓存键。
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = _make_key(func.__name__, *args, *sorted(kwargs.items()))
            result = cache_get(key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            cache_set(key, result, ttl)
            return result
        return wrapper
    return decorator


def cache_invalidate(prefix: str = ""):
    """清除匹配前缀的缓存"""
    if not prefix:
        _cache.clear()
        logger.info("缓存全部清除")
    else:
        keys_to_del = [k for k in _cache if k.startswith(prefix)]
        for k in keys_to_del:
            del _cache[k]
        logger.info(f"清除缓存: {len(keys_to_del)} 条")


def cache_stats() -> dict:
    """返回缓存统计"""
    now = time.time()
    active = sum(1 for v in _cache.values() if v["expire"] > now)
    expired = len(_cache) - active
    return {"total_entries": len(_cache), "active": active, "expired": expired}
