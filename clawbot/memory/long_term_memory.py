"""Long-term memory and context management"""
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from clawbot.memory.memory_store import MemoryStore, MemoryEntry, MemoryQuery


class LongTermMemory:
    """Manages long-term memory, summaries, and persistent context"""
    
    def __init__(self, memory_store: MemoryStore):
        self.memory_store = memory_store
    
    def create_summary(
        self,
        user_id: str,
        thread_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Create a summary of long-term context"""
        cutoff_time = time.time() - (days * 24 * 3600)
        
        query = MemoryQuery(
            user_id=user_id,
            thread_id=thread_id,
            start_time=cutoff_time,
            limit=1000
        )
        
        memories = self.memory_store.retrieve(query)
        
        # Analyze patterns
        patterns = self._analyze_patterns(memories)
        
        # Create summary
        summary = {
            "user_id": user_id,
            "thread_id": thread_id,
            "period_days": days,
            "total_memories": len(memories),
            "patterns": patterns,
            "frequent_topics": self._get_frequent_topics(memories),
            "important_events": self._get_important_events(memories),
            "user_preferences": self._extract_preferences(memories),
            "context_summary": self._generate_context_summary(memories)
        }
        
        return summary
    
    def get_user_profile(
        self,
        user_id: str,
        include_recent: bool = True
    ) -> Dict[str, Any]:
        """Get comprehensive user profile from long-term memory"""
        # Get all memories (or recent if specified)
        if include_recent:
            memories = self.memory_store.get_recent_memories(user_id, hours=24*30)  # Last 30 days
        else:
            query = MemoryQuery(user_id=user_id, limit=10000)
            memories = self.memory_store.retrieve(query)
        
        profile = {
            "user_id": user_id,
            "total_interactions": len(memories),
            "preferences": self._extract_preferences(memories),
            "common_topics": self._get_frequent_topics(memories),
            "interaction_patterns": self._analyze_patterns(memories),
            "key_context": self._get_key_context(memories),
            "last_updated": datetime.now().isoformat()
        }
        
        return profile
    
    def store_important_memory(
        self,
        user_id: str,
        content: str,
        category: str,
        thread_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryEntry:
        """Store an important memory with high importance"""
        entry = MemoryEntry(
            id=f"{user_id}_{int(time.time() * 1000)}",
            user_id=user_id,
            thread_id=thread_id,
            content=content,
            role="system",
            timestamp=time.time(),
            metadata=metadata or {},
            tags=[category, "important"],
            importance=0.9
        )
        
        self.memory_store.store(entry)
        return entry
    
    def search_memories(
        self,
        user_id: str,
        query_text: str,
        days: Optional[int] = None,
        thread_id: Optional[str] = None,
        limit: int = 20
    ) -> List[MemoryEntry]:
        """Search memories by content (simple text matching)"""
        if days:
            start_time = time.time() - (days * 24 * 3600)
        else:
            start_time = None
        
        query = MemoryQuery(
            user_id=user_id,
            thread_id=thread_id,
            start_time=start_time,
            limit=limit * 10  # Get more to filter
        )
        
        memories = self.memory_store.retrieve(query)
        
        # Simple text matching (could be enhanced with vector search)
        query_lower = query_text.lower()
        matching = [
            m for m in memories
            if query_lower in m.content.lower() or
            any(query_lower in tag.lower() for tag in m.tags)
        ]
        
        return matching[:limit]
    
    def _analyze_patterns(self, memories: List[MemoryEntry]) -> Dict[str, Any]:
        """Analyze interaction patterns"""
        if not memories:
            return {}
        
        # Time patterns
        hours = [datetime.fromtimestamp(m.timestamp).hour for m in memories]
        most_active_hour = max(set(hours), key=hours.count) if hours else None
        
        # Frequency patterns
        days_with_activity = len(set(
            datetime.fromtimestamp(m.timestamp).date() for m in memories
        ))
        
        # Role distribution
        role_counts = {}
        for m in memories:
            role_counts[m.role] = role_counts.get(m.role, 0) + 1
        
        return {
            "most_active_hour": most_active_hour,
            "days_with_activity": days_with_activity,
            "role_distribution": role_counts,
            "average_importance": sum(m.importance for m in memories) / len(memories) if memories else 0
        }
    
    def _get_frequent_topics(self, memories: List[MemoryEntry], top_n: int = 10) -> List[str]:
        """Get most frequent topics/tags"""
        tag_counts = {}
        for m in memories:
            for tag in m.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return [tag for tag, count in sorted_tags[:top_n]]
    
    def _get_important_events(self, memories: List[MemoryEntry], top_n: int = 10) -> List[Dict[str, Any]]:
        """Get most important events"""
        important = sorted(memories, key=lambda x: x.importance, reverse=True)[:top_n]
        return [
            {
                "content": m.content[:200],
                "timestamp": m.timestamp,
                "tags": m.tags,
                "importance": m.importance
            }
            for m in important
        ]
    
    def _extract_preferences(self, memories: List[MemoryEntry]) -> Dict[str, Any]:
        """Extract user preferences from memories"""
        preferences = {}
        
        # Look for preference indicators in metadata
        for m in memories:
            if "preference" in m.metadata:
                pref_type = m.metadata.get("preference_type")
                pref_value = m.metadata.get("preference_value")
                if pref_type:
                    preferences[pref_type] = pref_value
        
        # Extract from tags
        tag_preferences = {}
        for m in memories:
            for tag in m.tags:
                if tag.startswith("pref:"):
                    pref_name = tag.replace("pref:", "")
                    tag_preferences[pref_name] = True
        
        preferences.update(tag_preferences)
        
        return preferences
    
    def _generate_context_summary(self, memories: List[MemoryEntry]) -> str:
        """Generate a high-level context summary"""
        if not memories:
            return "No long-term context available."
        
        # Get key memories
        important = sorted(memories, key=lambda x: x.importance, reverse=True)[:5]
        
        summary_parts = []
        summary_parts.append(f"Total interactions: {len(memories)}")
        
        if important:
            summary_parts.append("Key events:")
            for m in important[:3]:
                summary_parts.append(f"- {m.content[:100]}...")
        
        topics = self._get_frequent_topics(memories, top_n=5)
        if topics:
            summary_parts.append(f"Common topics: {', '.join(topics)}")
        
        return "\n".join(summary_parts)
    
    def _get_key_context(self, memories: List[MemoryEntry]) -> List[str]:
        """Get key context points"""
        # Get memories with high importance or recent
        important = [m for m in memories if m.importance >= 0.7]
        recent = sorted(memories, key=lambda x: x.timestamp, reverse=True)[:10]
        
        # Combine and deduplicate
        key_memories = {m.id: m for m in important + recent}
        
        return [
            f"{m.content[:150]}..." 
            for m in sorted(key_memories.values(), key=lambda x: x.importance, reverse=True)[:5]
        ]
