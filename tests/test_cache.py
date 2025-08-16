"""
Tests for cache system
"""

import pytest
import asyncio
import time
from app.core.cache import (
    CacheKeyBuilder,
    InMemoryCache,
    CachePolicy,
    CacheEntry,
    get_l1_cache,
    cache_stats
)


class TestCacheKeyBuilder:
    """Test cache key generation"""
    
    def test_normalize_prompt(self):
        """Test prompt normalization"""
        test_cases = [
            ("  hello   world  ", "hello world"),
            ("hello\n\nworld", "hello world"),
            ("hello\tworld", "hello world"),
            ("  ", ""),
            ("normal text", "normal text"),
        ]
        
        for input_text, expected in test_cases:
            result = CacheKeyBuilder.normalize_prompt(input_text)
            assert result == expected
    
    def test_build_key_basic(self):
        """Test basic cache key generation"""
        key1 = CacheKeyBuilder.build_key("hello world", "gpt-4")
        key2 = CacheKeyBuilder.build_key("hello world", "gpt-4")
        
        # Same inputs should generate same key
        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex length
    
    def test_build_key_different_inputs(self):
        """Test that different inputs generate different keys"""
        key1 = CacheKeyBuilder.build_key("hello world", "gpt-4")
        key2 = CacheKeyBuilder.build_key("hello world", "gpt-3.5")
        key3 = CacheKeyBuilder.build_key("hello there", "gpt-4")
        
        assert key1 != key2  # Different models
        assert key1 != key3  # Different prompts
        assert key2 != key3  # Different everything
    
    def test_build_key_temperature_bucketing(self):
        """Test temperature bucketing for deterministic caching"""
        # Low temperatures should be identical
        key1 = CacheKeyBuilder.build_key("test", "gpt-4", temperature=0.0)
        key2 = CacheKeyBuilder.build_key("test", "gpt-4", temperature=0.1)
        assert key1 == key2  # Both below threshold
        
        # High temperatures should be different
        key3 = CacheKeyBuilder.build_key("test", "gpt-4", temperature=0.5)
        key4 = CacheKeyBuilder.build_key("test", "gpt-4", temperature=0.6)
        assert key3 != key4  # Different buckets
    
    def test_build_key_with_functions(self):
        """Test cache key generation with functions"""
        functions = [
            {"name": "test_func", "parameters": {"type": "object"}},
            {"name": "other_func", "parameters": {"type": "string"}}
        ]
        
        key1 = CacheKeyBuilder.build_key("test", "gpt-4", functions=functions)
        key2 = CacheKeyBuilder.build_key("test", "gpt-4", functions=functions)
        key3 = CacheKeyBuilder.build_key("test", "gpt-4")  # No functions
        
        assert key1 == key2  # Same functions
        assert key1 != key3  # Different functions


class TestCacheEntry:
    """Test cache entry functionality"""
    
    def test_cache_entry_creation(self):
        """Test cache entry creation"""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=time.time(),
            expires_at=time.time() + 3600,
            size_bytes=100
        )
        
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert not entry.is_expired
        assert entry.hit_count == 0
    
    def test_cache_entry_expiration(self):
        """Test cache entry expiration"""
        # Expired entry
        expired_entry = CacheEntry(
            key="expired",
            value="value",
            created_at=time.time() - 3600,
            expires_at=time.time() - 1800  # Expired 30 minutes ago
        )
        assert expired_entry.is_expired
        
        # Non-expiring entry
        no_expire_entry = CacheEntry(
            key="no_expire",
            value="value",
            created_at=time.time()
        )
        assert not no_expire_entry.is_expired


@pytest.mark.asyncio
class TestInMemoryCache:
    """Test in-memory cache implementation"""
    
    async def test_cache_set_and_get(self):
        """Test basic cache set and get operations"""
        cache = InMemoryCache(max_size=10)
        
        # Set and get value
        assert await cache.set("key1", "value1")
        value = await cache.get("key1")
        assert value == "value1"
    
    async def test_cache_miss(self):
        """Test cache miss behavior"""
        cache = InMemoryCache(max_size=10)
        
        # Get non-existent key
        value = await cache.get("nonexistent")
        assert value is None
    
    async def test_cache_expiration(self):
        """Test cache entry expiration"""
        cache = InMemoryCache(max_size=10)
        
        # Set with short TTL
        await cache.set("expire_key", "expire_value", ttl=1)
        
        # Should exist immediately
        assert await cache.exists("expire_key")
        value = await cache.get("expire_key")
        assert value == "expire_value"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired
        assert not await cache.exists("expire_key")
        value = await cache.get("expire_key")
        assert value is None
    
    async def test_cache_lru_eviction(self):
        """Test LRU eviction behavior"""
        cache = InMemoryCache(max_size=3)
        
        # Fill cache to capacity
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # All should exist
        assert await cache.exists("key1")
        assert await cache.exists("key2")
        assert await cache.exists("key3")
        
        # Access key1 to make it most recently used
        await cache.get("key1")
        
        # Add one more item (should evict key2, least recently used)
        await cache.set("key4", "value4")
        
        # key2 should be evicted, others should remain
        assert await cache.exists("key1")  # Recently accessed
        assert not await cache.exists("key2")  # Should be evicted
        assert await cache.exists("key3")
        assert await cache.exists("key4")  # New item
    
    async def test_cache_delete(self):
        """Test cache deletion"""
        cache = InMemoryCache(max_size=10)
        
        await cache.set("delete_key", "delete_value")
        assert await cache.exists("delete_key")
        
        assert await cache.delete("delete_key")
        assert not await cache.exists("delete_key")
        
        # Deleting non-existent key should return False
        assert not await cache.delete("nonexistent")
    
    async def test_cache_clear(self):
        """Test cache clearing"""
        cache = InMemoryCache(max_size=10)
        
        # Add multiple items
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        assert await cache.clear()
        
        # All items should be gone
        assert not await cache.exists("key1")
        assert not await cache.exists("key2")
        assert not await cache.exists("key3")
    
    async def test_cache_stats(self):
        """Test cache statistics"""
        cache = InMemoryCache(max_size=10)
        
        # Perform some operations
        await cache.set("key1", "value1")
        await cache.get("key1")  # Hit
        await cache.get("nonexistent")  # Miss
        
        stats = await cache.stats()
        
        assert stats["level"] == "l1_memory"
        assert stats["entries"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
        assert stats["total_size_bytes"] > 0


class TestCachePolicy:
    """Test cache policy configuration"""
    
    def test_cache_policy_defaults(self):
        """Test default cache policy"""
        policy = CachePolicy()
        
        assert policy.l1_enabled
        assert not policy.l2_enabled
        assert not policy.l3_enabled
        assert not policy.bypass_cache
    
    def test_should_cache_temperature(self):
        """Test temperature-based caching decisions"""
        policy = CachePolicy()
        
        # Low temperature should be cached
        assert policy.should_cache(temperature=0.0)
        assert policy.should_cache(temperature=0.1)
        
        # High temperature should not be cached
        assert not policy.should_cache(temperature=0.5)
        assert not policy.should_cache(temperature=1.0)
    
    def test_should_cache_bypass(self):
        """Test cache bypass functionality"""
        policy = CachePolicy(bypass_cache=True)
        
        # Should not cache anything when bypass is enabled
        assert not policy.should_cache(temperature=0.0)
        assert not policy.should_cache(temperature=0.5)


@pytest.mark.asyncio
class TestCacheIntegration:
    """Test cache system integration"""
    
    async def test_global_cache_instance(self):
        """Test global cache instance management"""
        cache1 = get_l1_cache()
        cache2 = get_l1_cache()
        
        # Should return same instance
        assert cache1 is cache2
        
        # Should be usable
        await cache1.set("test", "value")
        value = await cache2.get("test")
        assert value == "value"
    
    async def test_cache_stats_integration(self):
        """Test comprehensive cache statistics"""
        # Use global cache
        cache = get_l1_cache()
        await cache.clear()  # Start fresh
        
        # Perform some operations
        await cache.set("stats_test", "value")
        await cache.get("stats_test")
        
        # Get comprehensive stats
        stats = await cache_stats()
        
        assert "l1" in stats
        assert "l2" in stats
        assert "l3" in stats
        
        assert stats["l1"]["level"] == "l1_memory"
        assert stats["l2"]["enabled"] is False
        assert stats["l3"]["enabled"] is False
    
    async def test_end_to_end_caching(self):
        """Test end-to-end caching workflow"""
        cache = InMemoryCache(max_size=100)
        
        # Generate cache key
        prompt = "What is the capital of France?"
        cache_key = CacheKeyBuilder.build_key(
            prompt=prompt,
            model="gpt-4",
            temperature=0.0
        )
        
        # Check cache policy
        policy = CachePolicy()
        should_cache = policy.should_cache(temperature=0.0)
        assert should_cache
        
        # Simulate cache miss
        cached_response = await cache.get(cache_key)
        assert cached_response is None
        
        # Simulate API response and caching
        api_response = "The capital of France is Paris."
        await cache.set(cache_key, api_response, ttl=3600)
        
        # Verify cached response
        cached_response = await cache.get(cache_key)
        assert cached_response == api_response
        
        # Verify stats
        stats = await cache.stats()
        assert stats["hits"] == 1  # One hit from successful retrieval
        assert stats["misses"] == 1  # One miss from initial lookup