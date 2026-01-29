"""缓存模块"""
import time
from functools import wraps
from typing import Callable, Any

class LRUCache:
    """LRU缓存实现"""
    
    def __init__(self, capacity=128, ttl=3600):
        self.capacity = capacity
        self.ttl = ttl
        self.cache = {}
        self.access_time = {}
    
    def get(self, key):
        """获取缓存值"""
        if key not in self.cache:
            return None
        
        # 检查是否过期
        if time.time() - self.access_time[key] > self.ttl:
            del self.cache[key]
            del self.access_time[key]
            return None
        
        self.access_time[key] = time.time()
        return self.cache[key]
    
    def put(self, key, value):
        """存储值到缓存"""
        # 移除最少使用的键
        if len(self.cache) >= self.capacity and key not in self.cache:
            lru_key = min(self.access_time, key=self.access_time.get)
            del self.cache[lru_key]
            del self.access_time[lru_key]
        
        self.cache[key] = value
        self.access_time[key] = time.time()
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.access_time.clear()

def cached(cache: LRUCache):
    """缓存装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            key = f"{func.__name__}:{args}:{kwargs}"
            
            result = cache.get(key)
            if result is not None:
                return result
            
            result = func(*args, **kwargs)
            cache.put(key, result)
            return result
        
        return wrapper
    return decorator
