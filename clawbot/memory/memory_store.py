"""Core memory storage system"""
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from pydantic import BaseModel, Field
import hashlib
try:
    import redis
except ImportError:
    redis = None  # type: ignore
from clawbot.config import settings


class MemoryEntry(BaseModel):
    """Single memory entry"""
    id: str
    user_id: str
    thread_id: Optional[str] = None
    content: str
    role: str = Field(default="user", description="user, assistant, system")
    timestamp: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MemoryQuery(BaseModel):
    """Query for retrieving memories"""
    user_id: str
    thread_id: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    tags: Optional[List[str]] = None
    min_importance: Optional[float] = None
    limit: int = Field(default=50, ge=1, le=1000)
    role: Optional[str] = None


class MemoryStore:
    """Memory storage backend (Redis or file-based)"""
    
    def __init__(self):
        self.store_type = settings.TOKEN_CACHE_TYPE  # Reuse same config
        if self.store_type == "redis":
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST or "localhost",
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB + 1,  # Use different DB than token cache
                password=settings.REDIS_PASSWORD,
                decode_responses=True
            )
        else:
            self.memory_dir = Path("./.memory_store")
            self.memory_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_user_key(self, user_id: str) -> str:
        """Get Redis key for user memories"""
        return f"clawbot:memory:user:{user_id}"
    
    def _get_thread_key(self, user_id: str, thread_id: str) -> str:
        """Get Redis key for thread memories"""
        return f"clawbot:memory:thread:{user_id}:{thread_id}"
    
    def _get_file_path(self, user_id: str, thread_id: Optional[str] = None) -> Path:
        """Get file path for memory storage"""
        if thread_id:
            filename = f"{user_id}_{thread_id}.jsonl"
        else:
            filename = f"{user_id}_general.jsonl"
        return self.memory_dir / filename
    
    def store(self, entry: MemoryEntry) -> bool:
        """Store a memory entry"""
        entry_dict = entry.dict()
        
        if self.store_type == "redis":
            try:
                # Store in user's memory list
                user_key = self._get_user_key(entry.user_id)
                self.redis_client.lpush(user_key, json.dumps(entry_dict))
                
                # Also store in thread if specified
                if entry.thread_id:
                    thread_key = self._get_thread_key(entry.user_id, entry.thread_id)
                    self.redis_client.lpush(thread_key, json.dumps(entry_dict))
                
                # Set expiration (keep memories for 90 days)
                self.redis_client.expire(user_key, 90 * 24 * 3600)
                if entry.thread_id:
                    self.redis_client.expire(thread_key, 90 * 24 * 3600)
                
                return True
            except Exception as e:
                print(f"Redis memory store error: {e}")
                return False
        else:
            # File-based storage (JSONL format)
            try:
                file_path = self._get_file_path(entry.user_id, entry.thread_id)
                with open(file_path, 'a') as f:
                    f.write(json.dumps(entry_dict) + '\n')
                return True
            except Exception as e:
                print(f"File memory store error: {e}")
                return False
    
    def retrieve(self, query: MemoryQuery) -> List[MemoryEntry]:
        """Retrieve memories matching query"""
        entries = []
        
        if self.store_type == "redis":
            try:
                if query.thread_id:
                    key = self._get_thread_key(query.user_id, query.thread_id)
                else:
                    key = self._get_user_key(query.user_id)
                
                # Get all entries
                raw_entries = self.redis_client.lrange(key, 0, -1)
                
                for raw_entry in raw_entries:
                    try:
                        entry_dict = json.loads(raw_entry)
                        entry = MemoryEntry(**entry_dict)
                        
                        # Apply filters
                        if query.start_time and entry.timestamp < query.start_time:
                            continue
                        if query.end_time and entry.timestamp > query.end_time:
                            continue
                        if query.role and entry.role != query.role:
                            continue
                        if query.tags and not any(tag in entry.tags for tag in query.tags):
                            continue
                        if query.min_importance and entry.importance < query.min_importance:
                            continue
                        
                        entries.append(entry)
                    except Exception as e:
                        print(f"Error parsing memory entry: {e}")
                        continue
                
            except Exception as e:
                print(f"Redis memory retrieve error: {e}")
                return []
        else:
            # File-based retrieval
            try:
                file_path = self._get_file_path(query.user_id, query.thread_id)
                if not file_path.exists():
                    return []
                
                with open(file_path, 'r') as f:
                    for line in f:
                        try:
                            entry_dict = json.loads(line.strip())
                            entry = MemoryEntry(**entry_dict)
                            
                            # Apply filters
                            if query.start_time and entry.timestamp < query.start_time:
                                continue
                            if query.end_time and entry.timestamp > query.end_time:
                                continue
                            if query.role and entry.role != query.role:
                                continue
                            if query.tags and not any(tag in entry.tags for tag in query.tags):
                                continue
                            if query.min_importance and entry.importance < query.min_importance:
                                continue
                            
                            entries.append(entry)
                        except Exception as e:
                            print(f"Error parsing memory entry: {e}")
                            continue
            except Exception as e:
                print(f"File memory retrieve error: {e}")
                return []
        
        # Sort by timestamp (newest first) and limit
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        return entries[:query.limit]
    
    def get_daily_memories(
        self,
        user_id: str,
        date: Optional[datetime] = None,
        thread_id: Optional[str] = None
    ) -> List[MemoryEntry]:
        """Get memories for a specific day"""
        if date is None:
            date = datetime.now()
        
        start_of_day = datetime.combine(date.date(), datetime.min.time())
        end_of_day = start_of_day + timedelta(days=1)
        
        query = MemoryQuery(
            user_id=user_id,
            thread_id=thread_id,
            start_time=start_of_day.timestamp(),
            end_time=end_of_day.timestamp(),
            limit=1000
        )
        
        return self.retrieve(query)
    
    def get_recent_memories(
        self,
        user_id: str,
        hours: int = 24,
        thread_id: Optional[str] = None,
        limit: int = 100
    ) -> List[MemoryEntry]:
        """Get recent memories within specified hours"""
        start_time = time.time() - (hours * 3600)
        
        query = MemoryQuery(
            user_id=user_id,
            thread_id=thread_id,
            start_time=start_time,
            limit=limit
        )
        
        return self.retrieve(query)
    
    def delete_memory(self, user_id: str, memory_id: str) -> bool:
        """Delete a specific memory entry"""
        # This is more complex - would need to scan and remove
        # For now, mark as deleted in metadata
        # Full implementation would require updating the storage
        return True
    
    def clear_user_memories(
        self,
        user_id: str,
        thread_id: Optional[str] = None,
        older_than_days: Optional[int] = None
    ) -> bool:
        """Clear memories for a user (optionally older than X days)"""
        if self.store_type == "redis":
            try:
                if thread_id:
                    key = self._get_thread_key(user_id, thread_id)
                else:
                    key = self._get_user_key(user_id)
                self.redis_client.delete(key)
                return True
            except Exception as e:
                print(f"Redis clear error: {e}")
                return False
        else:
            try:
                file_path = self._get_file_path(user_id, thread_id)
                if file_path.exists():
                    if older_than_days:
                        # Filter and rewrite file
                        cutoff_time = time.time() - (older_than_days * 24 * 3600)
                        entries = self.retrieve(MemoryQuery(user_id=user_id, thread_id=thread_id, limit=10000))
                        with open(file_path, 'w') as f:
                            for entry in entries:
                                if entry.timestamp >= cutoff_time:
                                    f.write(json.dumps(entry.dict()) + '\n')
                    else:
                        file_path.unlink()
                return True
            except Exception as e:
                print(f"File clear error: {e}")
                return False
