"""Token caching system for Google OAuth tokens"""
import json
import os
import time
from typing import Optional, Dict, Any
from pathlib import Path
import hashlib
try:
    import redis
except ImportError:
    redis = None  # type: ignore
from clawbot.config import settings


class TokenCache:
    """Manages caching of OAuth tokens with automatic refresh"""
    
    def __init__(self):
        self.cache_type = settings.TOKEN_CACHE_TYPE
        if self.cache_type == "redis":
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST or "localhost",
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True
            )
        else:
            self.cache_dir = Path(settings.TOKEN_CACHE_PATH)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, user_id: str) -> str:
        """Generate cache key for user"""
        return hashlib.sha256(f"clawbot_token_{user_id}".encode()).hexdigest()
    
    def _get_file_path(self, user_id: str) -> Path:
        """Get file path for token cache"""
        cache_key = self._get_cache_key(user_id)
        return self.cache_dir / f"{cache_key}.json"
    
    def get_token(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached token for user"""
        if self.cache_type == "redis":
            try:
                cached = self.redis_client.get(self._get_cache_key(user_id))
                if cached:
                    return json.loads(cached)
            except Exception as e:
                print(f"Redis cache error: {e}")
                return None
        else:
            cache_file = self._get_file_path(user_id)
            if cache_file.exists():
                try:
                    with open(cache_file, 'r') as f:
                        return json.load(f)
                except Exception as e:
                    print(f"File cache read error: {e}")
            # Fallback: read from env var (survives Render redeploys)
            env_key = f"GOOGLE_TOKEN_DATA_{self._get_cache_key(user_id)}"
            env_val = os.environ.get(env_key, "")
            if env_val:
                try:
                    data = json.loads(env_val)
                    # Warm the disk cache so subsequent calls are faster
                    try:
                        cache_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(cache_file, 'w') as f:
                            json.dump(data, f)
                        os.chmod(cache_file, 0o600)
                    except Exception:
                        pass
                    return data
                except Exception as e:
                    print(f"Env token parse error: {e}")
        return None
    
    def set_token(self, user_id: str, token_data: Dict[str, Any]) -> bool:
        """Store token in cache"""
        token_data['cached_at'] = time.time()
        
        if self.cache_type == "redis":
            try:
                # Set expiration to 1 hour before token expiry
                expires_in = token_data.get('expires_in', 3600)
                ttl = max(expires_in - 3600, 300)  # At least 5 minutes
                self.redis_client.setex(
                    self._get_cache_key(user_id),
                    ttl,
                    json.dumps(token_data)
                )
                return True
            except Exception as e:
                print(f"Redis cache write error: {e}")
                return False
        else:
            cache_file = self._get_file_path(user_id)
            try:
                with open(cache_file, 'w') as f:
                    json.dump(token_data, f)
                # Set file permissions to be readable only by owner
                os.chmod(cache_file, 0o600)
                return True
            except Exception as e:
                print(f"File cache write error: {e}")
                return False
    
    def delete_token(self, user_id: str) -> bool:
        """Remove token from cache"""
        if self.cache_type == "redis":
            try:
                self.redis_client.delete(self._get_cache_key(user_id))
                return True
            except Exception as e:
                print(f"Redis cache delete error: {e}")
                return False
        else:
            cache_file = self._get_file_path(user_id)
            try:
                if cache_file.exists():
                    cache_file.unlink()
                return True
            except Exception as e:
                print(f"File cache delete error: {e}")
                return False
    
    def is_token_valid(self, token_data: Dict[str, Any]) -> bool:
        """Check if token is still valid (not expired)"""
        if not token_data:
            return False
        
        expires_at = token_data.get('expires_at')
        if expires_at:
            return time.time() < expires_at
        
        # Fallback: check expires_in
        expires_in = token_data.get('expires_in', 0)
        cached_at = token_data.get('cached_at', 0)
        if cached_at and expires_in:
            return time.time() < (cached_at + expires_in)
        
        return True


# Global token cache instance
token_cache = TokenCache()
