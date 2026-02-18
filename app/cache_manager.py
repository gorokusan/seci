"""
Redisキャッシュ管理
"""
import redis
from flask import session
import json
from functools import wraps
from datetime import timedelta

redis_client = None


def init_cache(app):
    """Redisキャッシュ初期化"""
    global redis_client
    
    redis_url = app.config.get('REDIS_URL')
    if not redis_url:
        app.logger.warning("REDIS_URL not set. Cache disabled.")
        redis_client = None
        return

    try:
        redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
        )
        redis_client.ping()
        app.logger.info("Redis cache enabled.")
    except Exception as e:
        app.logger.warning(f"Redis init failed: {e}. Cache disabled.")
        redis_client = None

def get_cache():
    """Redisクライアント取得"""
    return redis_client


def cache_key(prefix, *args):
    """キャッシュキー生成"""
    return f"{prefix}:{':'.join(str(arg) for arg in args)}"


def cached(prefix, expire=300):
    """キャッシュデコレーター"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # キャッシュキーの生成
            if redis_client is None:
                return func(*args, **kwargs)

            #key = cache_key(prefix, *args, *sorted(kwargs.items()))
            key = f"{prefix}:{':'.join(str(a) for a in args)}"
            
            # キャッシュから取得
            cached_value = redis_client.get(key)
            if cached_value:
                return json.loads(cached_value)
            
            # 関数実行
            result = func(*args, **kwargs)
            
            # キャッシュに保存
            redis_client.setex(
                key,
                expire,
                json.dumps(result, ensure_ascii=False)
            )
            
            return result
        return wrapper
    return decorator


def invalidate_cache(prefix, *args):
    """キャッシュ無効化"""
    global redis_client
    if redis_client is None:
        return
    #key = cache_key(prefix, *args)
    key = f"{prefix}:{':'.join(str(a) for a in args)}"
    redis_client.delete(key)


def get_session_id():
    """セッションID取得または生成"""
    if 'session_id' not in session:
        import uuid
        session['session_id'] = str(uuid.uuid4())
        session.permanent = True
    return session['session_id']


def get_session_data(key, default=None):
    """セッションデータ取得"""
    if redis_client is None:
        return default

    session_id = get_session_id()
    cache_key_str = cache_key('session', session_id, key)
    data = redis_client.get(cache_key_str)
    return json.loads(data) if data else default


def set_session_data(key, value, expire=None):
    if redis_client is None:
        return

    """セッションデータ設定"""
    session_id = get_session_id()
    cache_key_str = cache_key('session', session_id, key)
    
    if expire:
        redis_client.setex(
            cache_key_str,
            expire,
            json.dumps(value, ensure_ascii=False)
        )
    else:
        redis_client.set(
            cache_key_str,
            json.dumps(value, ensure_ascii=False)
        )


def delete_session_data(key):
    if redis_client is None:
        return

    """セッションデータ削除"""
    session_id = get_session_id()
    cache_key_str = cache_key('session', session_id, key)
    redis_client.delete(cache_key_str)


def get_user_nodes_cache(session_id):
    if redis_client is None:
        return

    """ユーザーノードのキャッシュ取得"""
    key = cache_key('nodes', session_id)
    data = redis_client.get(key)
    return json.loads(data) if data else None


def set_user_nodes_cache(session_id, nodes, expire=3600):
    if redis_client is None:
        return

    """ユーザーノードのキャッシュ設定"""
    key = cache_key('nodes', session_id)
    redis_client.setex(
        key,
        expire,
        json.dumps(nodes, ensure_ascii=False)
    )


def invalidate_user_cache(session_id):
    if redis_client is None:
        return

    """ユーザーキャッシュ無効化"""
    patterns = [
        cache_key('nodes', session_id),
        cache_key('analytics', session_id),
        cache_key('session', session_id, '*')
    ]
    
    for pattern in patterns:
        if '*' in pattern:
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        else:
            redis_client.delete(pattern)
