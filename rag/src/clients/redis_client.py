import redis
import json
from typing import Optional, Any
from src.config import config

_redis_client = None

def get_redis_client() -> Optional[redis.Redis]:
    """Get or create singleton Redis client"""
    global _redis_client
    
    if not config.REDIS_ENABLED:
        return None
    
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                password=config.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            _redis_client.ping()
            print(f"Connected to Redis at {config.REDIS_HOST}:{config.REDIS_PORT}")
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")
            _redis_client = None
    
    return _redis_client

def cache_get(key: str) -> Optional[Any]:
    """Get value from cache"""
    try:
        client = get_redis_client()
        if not client:
            return None
        
        value = client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        print(f"Cache get error: {e}")
        return None

def cache_set(key: str, value: Any, ttl: int = None) -> bool:
    """Set value in cache with optional TTL"""
    try:
        client = get_redis_client()
        if not client:
            return False
        
        if ttl is None:
            ttl = config.CACHE_TTL
        
        client.setex(key, ttl, json.dumps(value))
        return True
    except Exception as e:
        print(f"Cache set error: {e}")
        return False

def cache_delete(key: str) -> bool:
    """Delete value from cache"""
    try:
        client = get_redis_client()
        if not client:
            return False
        
        client.delete(key)
        return True
    except Exception as e:
        print(f"Cache delete error: {e}")
        return False

def invalidate_pattern(pattern: str) -> int:
    """Delete all keys matching pattern"""
    try:
        client = get_redis_client()
        if not client:
            return 0
        
        keys = client.keys(pattern)
        if keys:
            return client.delete(*keys)
        return 0
    except Exception as e:
        print(f"Cache invalidate error: {e}")
        return 0
