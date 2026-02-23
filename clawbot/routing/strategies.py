"""Routing strategies for multi-agent system"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import time
import random


class RoutingStrategy(ABC):
    """Base class for routing strategies"""
    
    @abstractmethod
    def select_agent(
        self,
        agents: List[Dict[str, Any]],
        request: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Select an agent to handle the request"""
        pass


class RoundRobinStrategy(RoutingStrategy):
    """Round-robin routing strategy"""
    
    def __init__(self):
        self.current_index = 0
    
    def select_agent(
        self,
        agents: List[Dict[str, Any]],
        request: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Select next agent in round-robin fashion"""
        if not agents:
            return None
        
        # Filter to only available agents
        available = [a for a in agents if a.get('available', True)]
        if not available:
            return None
        
        agent = available[self.current_index % len(available)]
        self.current_index += 1
        return agent


class LoadBalanceStrategy(RoutingStrategy):
    """Load-balanced routing strategy based on agent load"""
    
    def select_agent(
        self,
        agents: List[Dict[str, Any]],
        request: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Select agent with lowest load"""
        if not agents:
            return None
        
        # Filter to only available agents
        available = [a for a in agents if a.get('available', True)]
        if not available:
            return None
        
        # Sort by load (lower is better)
        available.sort(key=lambda a: a.get('current_load', 0))
        
        # Return agent with lowest load
        return available[0]


class IntentBasedStrategy(RoutingStrategy):
    """Intent-based routing strategy"""
    
    def __init__(self):
        # Map intents to agent capabilities
        self.intent_agent_map = {
            'gmail': ['gmail', 'email', 'message'],
            'calendar': ['calendar', 'event', 'meeting', 'schedule'],
            'gsuite': ['user', 'group', 'admin', 'directory'],
            'general': ['general', 'assistant']
        }
    
    def select_agent(
        self,
        agents: List[Dict[str, Any]],
        request: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Select agent based on request intent"""
        if not agents:
            return None
        
        # Extract intent from request
        intent = self._extract_intent(request)
        
        # Find agents that can handle this intent
        capable_agents = []
        for agent in agents:
            if not agent.get('available', True):
                continue
            
            capabilities = agent.get('capabilities', [])
            if any(cap in self.intent_agent_map.get(intent, []) for cap in capabilities):
                capable_agents.append(agent)
        
        if not capable_agents:
            # Fallback to general agents or any available agent
            capable_agents = [a for a in agents if a.get('available', True)]
        
        if not capable_agents:
            return None
        
        # Select agent with lowest load among capable agents
        capable_agents.sort(key=lambda a: a.get('current_load', 0))
        return capable_agents[0]
    
    def _extract_intent(self, request: Dict[str, Any]) -> str:
        """Extract intent from request"""
        # Check explicit intent field
        if 'intent' in request:
            return request['intent'].lower()
        
        # Check action field
        if 'action' in request:
            action = request['action'].lower()
            if 'gmail' in action or 'email' in action or 'message' in action:
                return 'gmail'
            elif 'calendar' in action or 'event' in action or 'meeting' in action:
                return 'calendar'
            elif 'user' in action or 'group' in action or 'admin' in action:
                return 'gsuite'
        
        # Check text/query field
        if 'text' in request or 'query' in request:
            text = (request.get('text', '') + ' ' + request.get('query', '')).lower()
            if any(word in text for word in ['email', 'gmail', 'message', 'send']):
                return 'gmail'
            elif any(word in text for word in ['calendar', 'event', 'meeting', 'schedule', 'appointment']):
                return 'calendar'
            elif any(word in text for word in ['user', 'group', 'admin', 'directory']):
                return 'gsuite'
        
        return 'general'


class RandomStrategy(RoutingStrategy):
    """Random routing strategy"""
    
    def select_agent(
        self,
        agents: List[Dict[str, Any]],
        request: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Select random available agent"""
        if not agents:
            return None
        
        available = [a for a in agents if a.get('available', True)]
        if not available:
            return None
        
        return random.choice(available)
