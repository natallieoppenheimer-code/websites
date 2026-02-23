"""Daily context management for OpenClaw"""
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from clawbot.memory.memory_store import MemoryStore, MemoryEntry, MemoryQuery


class DailyContextManager:
    """Manages daily context windows and summaries"""
    
    def __init__(self, memory_store: MemoryStore):
        self.memory_store = memory_store
    
    def get_today_context(
        self,
        user_id: str,
        thread_id: Optional[str] = None,
        include_summary: bool = True
    ) -> Dict[str, Any]:
        """Get today's context with optional summary"""
        today = datetime.now()
        memories = self.memory_store.get_daily_memories(
            user_id=user_id,
            date=today,
            thread_id=thread_id
        )
        
        context = {
            "date": today.date().isoformat(),
            "user_id": user_id,
            "thread_id": thread_id,
            "memory_count": len(memories),
            "memories": [m.dict() for m in memories]
        }
        
        if include_summary:
            context["summary"] = self._generate_daily_summary(memories)
        
        return context
    
    def get_context_window(
        self,
        user_id: str,
        days: int = 7,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get context for multiple days"""
        contexts = []
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            memories = self.memory_store.get_daily_memories(
                user_id=user_id,
                date=date,
                thread_id=thread_id
            )
            
            if memories:
                contexts.append({
                    "date": date.date().isoformat(),
                    "memory_count": len(memories),
                    "summary": self._generate_daily_summary(memories),
                    "key_memories": [
                        m.dict() for m in memories[:10]  # Top 10 per day
                    ]
                })
        
        return {
            "user_id": user_id,
            "thread_id": thread_id,
            "days": days,
            "contexts": contexts,
            "total_memories": sum(c["memory_count"] for c in contexts)
        }
    
    def add_to_daily_context(
        self,
        user_id: str,
        content: str,
        role: str = "user",
        thread_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        importance: float = 0.5
    ) -> MemoryEntry:
        """Add an entry to today's context"""
        entry = MemoryEntry(
            id=f"{user_id}_{int(time.time() * 1000)}",
            user_id=user_id,
            thread_id=thread_id,
            content=content,
            role=role,
            timestamp=time.time(),
            metadata=metadata or {},
            tags=tags or [],
            importance=importance
        )
        
        self.memory_store.store(entry)
        return entry
    
    def get_conversation_summary(
        self,
        user_id: str,
        thread_id: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get summary of recent conversation"""
        memories = self.memory_store.get_recent_memories(
            user_id=user_id,
            hours=hours,
            thread_id=thread_id
        )
        
        # Separate by role
        user_messages = [m for m in memories if m.role == "user"]
        assistant_messages = [m for m in memories if m.role == "assistant"]
        
        return {
            "user_id": user_id,
            "thread_id": thread_id,
            "time_window_hours": hours,
            "total_exchanges": len(memories),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "summary": self._generate_conversation_summary(memories),
            "topics": self._extract_topics(memories),
            "key_points": self._extract_key_points(memories)
        }
    
    def _generate_daily_summary(self, memories: List[MemoryEntry]) -> str:
        """Generate a summary of daily memories"""
        if not memories:
            return "No memories for this day."
        
        # Group by importance and role
        important = [m for m in memories if m.importance >= 0.7]
        user_messages = [m for m in memories if m.role == "user"]
        assistant_messages = [m for m in memories if m.role == "assistant"]
        
        summary_parts = []
        
        if important:
            summary_parts.append(
                f"Key events: {len(important)} important interactions"
            )
        
        if user_messages:
            summary_parts.append(
                f"User interactions: {len(user_messages)} messages"
            )
        
        if assistant_messages:
            summary_parts.append(
                f"Assistant responses: {len(assistant_messages)} messages"
            )
        
        # Extract tags
        all_tags = set()
        for m in memories:
            all_tags.update(m.tags)
        
        if all_tags:
            summary_parts.append(f"Topics: {', '.join(list(all_tags)[:5])}")
        
        return ". ".join(summary_parts) + "."
    
    def _generate_conversation_summary(self, memories: List[MemoryEntry]) -> str:
        """Generate conversation summary"""
        if not memories:
            return "No recent conversation."
        
        # Get most important memories
        important = sorted(memories, key=lambda x: x.importance, reverse=True)[:5]
        
        summary_parts = []
        for mem in important:
            if mem.role == "user":
                summary_parts.append(f"User: {mem.content[:100]}...")
            elif mem.role == "assistant":
                summary_parts.append(f"Assistant: {mem.content[:100]}...")
        
        return "\n".join(summary_parts)
    
    def _extract_topics(self, memories: List[MemoryEntry]) -> List[str]:
        """Extract topics from memories"""
        topics = set()
        for mem in memories:
            topics.update(mem.tags)
            # Could add NLP-based topic extraction here
        return list(topics)[:10]
    
    def _extract_key_points(self, memories: List[MemoryEntry]) -> List[str]:
        """Extract key points from memories"""
        key_points = []
        important = sorted(memories, key=lambda x: x.importance, reverse=True)[:5]
        for mem in important:
            if mem.importance >= 0.7:
                key_points.append(mem.content[:200])
        return key_points
