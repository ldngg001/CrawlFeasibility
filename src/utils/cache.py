"""Cache mechanism for CrawlFeasibility"""
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .. import __version__
from ..models.result import CrawlFeasibilityResult


class CacheManager:
    """Manage caching of detection results"""
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize cache manager
        
        Args:
            cache_dir: Directory to store cache files. Defaults to ~/.crawlfeasibility/cache/
        """
        if cache_dir is None:
            cache_dir = os.path.join(os.path.expanduser("~"), ".crawlfeasibility", "cache")
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache TTL (time to live) in seconds
        self.ttl = {
            "basic": 24 * 3600,      # 24 hours
            "tech_stack": 7 * 24 * 3600,  # 7 days
            "anti_spider": 6 * 3600,      # 6 hours
            "assessment": 24 * 3600,      # 24 hours
        }
    
    def _get_cache_key(self, url: str, check_type: str, deep: bool = False) -> str:
        """
        Generate a cache key for a URL and check type
        
        Args:
            url: Target URL
            check_type: Type of check (basic, tech_stack, anti_spider, assessment)
            deep: Whether deep scan is enabled
            
        Returns:
            Cache key string
        """
        # Include deep flag in key for anti_spider checks since they behave differently
        key_data = f"{url}:{check_type}:{deep}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key"""
        return self.cache_dir / f"{cache_key}.json"
    
    def _is_cache_valid(self, cache_path: Path, ttl_seconds: int) -> bool:
        """
        Check if cache file is still valid based on TTL
        
        Args:
            cache_path: Path to cache file
            ttl_seconds: Time to live in seconds
            
        Returns:
            True if cache is valid, False otherwise
        """
        if not cache_path.exists():
            return False
        
        # Check file age
        file_age = time.time() - cache_path.stat().st_mtime
        return file_age < ttl_seconds
    
    def get(self, url: str, check_type: str, deep: bool = False) -> Optional[Any]:
        """
        Get cached result for a URL and check type
        
        Args:
            url: Target URL
            check_type: Type of check (basic, tech_stack, anti_spider, assessment)
            deep: Whether deep scan is enabled
            
        Returns:
            Cached result if valid, None otherwise
        """
        cache_key = self._get_cache_key(url, check_type, deep)
        cache_path = self._get_cache_path(cache_key)
        
        if not self._is_cache_valid(cache_path, self.ttl.get(check_type, 3600)):
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except (json.JSONDecodeError, IOError):
            # If cache is corrupted, treat as miss
            return None
    
    def set(self, url: str, check_type: str, data: Any, deep: bool = False) -> None:
        """
        Store result in cache
        
        Args:
            url: Target URL
            check_type: Type of check (basic, tech_stack, anti_spider, assessment)
            data: Data to cache
            deep: Whether deep scan is enabled
        """
        cache_key = self._get_cache_key(url, check_type, deep)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except IOError:
            # Failed to write cache, continue without caching
            pass
    
    def clear(self, pattern: Optional[str] = None) -> int:
        """
        Clear cache files
        
        Args:
            pattern: Optional pattern to match cache keys (for partial clearing)
            
        Returns:
            Number of files cleared
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            if pattern is None or pattern in cache_file.name:
                try:
                    cache_file.unlink()
                    count += 1
                except OSError:
                    pass
        return count
    
    def clear_all(self) -> int:
        """
        Clear all cache files
        
        Returns:
            Number of files cleared
        """
        return self.clear()
    
    def get_cache_size(self) -> Tuple[int, int]:
        """
        Get cache size information
        
        Returns:
            Tuple of (file_count, total_size_in_bytes)
        """
        file_count = 0
        total_size = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                file_count += 1
                total_size += cache_file.stat().st_size
            except OSError:
                pass
                
        return file_count, total_size


# Global cache manager instance
cache_manager = CacheManager()