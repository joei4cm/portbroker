"""
Cache system interfaces and implementations
Basic skeleton for future LLM call caching implementation
"""

import hashlib
import json
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass
from enum import Enum

from .logging_utils import get_logger

logger = get_logger(__name__)


class CacheLevel(str, Enum):
    """Cache levels for multi-tier caching"""
    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"
    L3_STORAGE = "l3_storage"


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: float
    expires_at: Optional[float] = None
    hit_count: int = 0
    size_bytes: int = 0
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class CacheBackend(ABC):
    """Abstract cache backend interface"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries"""
        pass
    
    @abstractmethod
    async def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        pass


class CacheKeyBuilder:
    """Cache key builder for LLM requests"""
    
    @staticmethod
    def normalize_prompt(prompt: str) -> str:
        """Normalize prompt for cache key generation"""
        # Remove extra whitespace and normalize Unicode
        normalized = " ".join(prompt.split())
        # TODO: Add date/number placeholder normalization
        return normalized
    
    @staticmethod
    def build_key(
        prompt: str,
        model: str,
        temperature: float = 0.0,
        top_p: float = 1.0,
        functions: Optional[list] = None,
        version: str = "v1"
    ) -> str:
        """Build cache key for LLM request"""
        
        # Normalize inputs
        normalized_prompt = CacheKeyBuilder.normalize_prompt(prompt)
        
        # Temperature bucketing for probabilistic models
        temp_bucket = 0.0 if temperature <= 0.15 else round(temperature, 1)
        
        # Sort functions for consistent hashing
        functions_hash = ""
        if functions:
            functions_str = json.dumps(functions, sort_keys=True)
            functions_hash = hashlib.sha256(functions_str.encode()).hexdigest()[:16]
        
        # Build stable metadata object
        metadata = {
            "model": model,
            "temp_bucket": temp_bucket,
            "top_p": top_p,
            "functions_hash": functions_hash,
            "version": version
        }
        
        # Create cache key
        metadata_str = json.dumps(metadata, sort_keys=True)
        combined = f"{normalized_prompt}|{metadata_str}"
        
        # Generate SHA256 hash
        cache_key = hashlib.sha256(combined.encode()).hexdigest()
        
        logger.debug(
            "Generated cache key",
            extra={
                "cache_key": cache_key,
                "model": model,
                "temp_bucket": temp_bucket,
                "has_functions": bool(functions),
                "prompt_length": len(prompt)
            }
        )
        
        return cache_key


class InMemoryCache(CacheBackend):
    """Simple in-memory LRU cache implementation"""
    
    def __init__(self, max_size: int = 5000, default_ttl: int = 1800):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from in-memory cache"""
        entry = self._cache.get(key)
        
        if entry is None:
            self._misses += 1
            logger.debug("Cache miss", extra={"cache_key": key, "level": "l1_memory"})
            return None
        
        if entry.is_expired:
            await self.delete(key)
            self._misses += 1
            logger.debug("Cache expired", extra={"cache_key": key, "level": "l1_memory"})
            return None
        
        # Update hit count and move to end (LRU)
        entry.hit_count += 1
        self._cache[key] = self._cache.pop(key)  # Move to end
        self._hits += 1
        
        logger.debug(
            "Cache hit", 
            extra={
                "cache_key": key, 
                "level": "l1_memory",
                "hit_count": entry.hit_count
            }
        )
        
        return entry.value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in in-memory cache"""
        try:
            # Calculate expiration
            expires_at = None
            if ttl or self.default_ttl:
                expires_at = time.time() + (ttl or self.default_ttl)
            
            # Estimate size (rough approximation)
            size_bytes = len(str(value).encode('utf-8'))
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                expires_at=expires_at,
                size_bytes=size_bytes
            )
            
            # Evict LRU entries if needed
            while len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._evictions += 1
            
            self._cache[key] = entry
            
            logger.debug(
                "Cache set",
                extra={
                    "cache_key": key,
                    "level": "l1_memory",
                    "size_bytes": size_bytes,
                    "ttl": ttl
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Cache set failed",
                extra={
                    "cache_key": key,
                    "level": "l1_memory",
                    "error": str(e)
                }
            )
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from in-memory cache"""
        if key in self._cache:
            del self._cache[key]
            logger.debug("Cache delete", extra={"cache_key": key, "level": "l1_memory"})
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        entry = self._cache.get(key)
        if entry and not entry.is_expired:
            return True
        return False
    
    async def clear(self) -> bool:
        """Clear all cache entries"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        logger.info("Cache cleared", extra={"level": "l1_memory"})
        return True
    
    async def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0
        
        total_size = sum(entry.size_bytes for entry in self._cache.values())
        
        return {
            "level": "l1_memory",
            "entries": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "hit_rate": hit_rate,
            "total_size_bytes": total_size
        }


class CachePolicy:
    """Cache policy configuration"""
    
    def __init__(
        self,
        l1_enabled: bool = True,
        l1_max_size: int = 5000,
        l1_ttl: int = 1800,  # 30 minutes
        l2_enabled: bool = False,
        l2_ttl: int = 3600,  # 1 hour
        l3_enabled: bool = False,
        l3_ttl: int = 86400,  # 24 hours
        bypass_cache: bool = False
    ):
        self.l1_enabled = l1_enabled
        self.l1_max_size = l1_max_size
        self.l1_ttl = l1_ttl
        self.l2_enabled = l2_enabled
        self.l2_ttl = l2_ttl
        self.l3_enabled = l3_enabled
        self.l3_ttl = l3_ttl
        self.bypass_cache = bypass_cache
    
    def should_cache(self, temperature: float, has_functions: bool = False) -> bool:
        """Determine if request should be cached based on policy"""
        if self.bypass_cache:
            return False
        
        # Don't cache high-temperature (non-deterministic) requests
        if temperature > 0.15:
            return False
        
        # Cache simple text requests and function calls
        return True


# Global cache instance (will be initialized in main app)
_l1_cache: Optional[InMemoryCache] = None


def get_l1_cache() -> InMemoryCache:
    """Get L1 cache instance"""
    global _l1_cache
    if _l1_cache is None:
        _l1_cache = InMemoryCache()
    return _l1_cache


async def cache_stats() -> Dict[str, Any]:
    """Get comprehensive cache statistics"""
    stats = {}
    
    # L1 stats
    l1_cache = get_l1_cache()
    stats["l1"] = await l1_cache.stats()
    
    # TODO: Add L2 and L3 stats when implemented
    stats["l2"] = {"level": "l2_redis", "enabled": False}
    stats["l3"] = {"level": "l3_storage", "enabled": False}
    
    return stats