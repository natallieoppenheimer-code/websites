"""Multi-agent router"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from clawbot.routing.strategies import (
    RoutingStrategy,
    RoundRobinStrategy,
    LoadBalanceStrategy,
    IntentBasedStrategy
)
from clawbot.config import settings


class RouteRequest(BaseModel):
    """Request to route to an agent"""
    intent: Optional[str] = Field(None, description="Intent of the request")
    action: Optional[str] = Field(None, description="Action to perform")
    text: Optional[str] = Field(None, description="Text content")
    query: Optional[str] = Field(None, description="Query string")
    user_id: str = Field(..., description="User ID making the request")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class RouteResponse(BaseModel):
    """Response from routing"""
    agent_id: str = Field(..., description="Selected agent ID")
    agent_name: str = Field(..., description="Agent name")
    strategy_used: str = Field(..., description="Routing strategy used")
    confidence: float = Field(..., description="Confidence score (0-1)")


class AgentRouter:
    """Multi-agent router"""
    
    def __init__(self, strategy: Optional[str] = None):
        self.strategy_name = strategy or settings.AGENT_ROUTING_STRATEGY
        self.strategy = self._create_strategy(self.strategy_name)
        self.agents: List[Dict[str, Any]] = []
        self._initialize_default_agents()
    
    def _create_strategy(self, strategy_name: str) -> RoutingStrategy:
        """Create routing strategy instance"""
        strategies = {
            'round_robin': RoundRobinStrategy,
            'load_balance': LoadBalanceStrategy,
            'intent_based': IntentBasedStrategy,
            'random': None  # Will be handled separately
        }
        
        strategy_class = strategies.get(strategy_name.lower())
        if not strategy_class:
            return RoundRobinStrategy()  # Default
        
        return strategy_class()
    
    def _initialize_default_agents(self):
        """Initialize default agent pool"""
        self.agents = [
            {
                'id': 'gmail_agent_1',
                'name': 'Gmail Agent 1',
                'type': 'gmail',
                'capabilities': ['gmail', 'email', 'message'],
                'available': True,
                'current_load': 0,
                'max_load': 10,
                'endpoint': None  # Can be set to external agent endpoint
            },
            {
                'id': 'calendar_agent_1',
                'name': 'Calendar Agent 1',
                'type': 'calendar',
                'capabilities': ['calendar', 'event', 'meeting'],
                'available': True,
                'current_load': 0,
                'max_load': 10,
                'endpoint': None
            },
            {
                'id': 'gsuite_agent_1',
                'name': 'GSuite Agent 1',
                'type': 'gsuite',
                'capabilities': ['gsuite', 'user', 'group', 'admin'],
                'available': True,
                'current_load': 0,
                'max_load': 10,
                'endpoint': None
            },
            {
                'id': 'general_agent_1',
                'name': 'General Agent 1',
                'type': 'general',
                'capabilities': ['general', 'assistant'],
                'available': True,
                'current_load': 0,
                'max_load': 10,
                'endpoint': None
            }
        ]
    
    def register_agent(self, agent: Dict[str, Any]):
        """Register a new agent"""
        # Validate agent structure
        required_fields = ['id', 'name', 'type', 'capabilities']
        if not all(field in agent for field in required_fields):
            raise ValueError(f"Agent must have fields: {required_fields}")
        
        # Set defaults
        agent.setdefault('available', True)
        agent.setdefault('current_load', 0)
        agent.setdefault('max_load', 10)
        
        # Check if agent already exists
        existing_index = next(
            (i for i, a in enumerate(self.agents) if a['id'] == agent['id']),
            None
        )
        
        if existing_index is not None:
            # Update existing agent
            self.agents[existing_index].update(agent)
        else:
            # Add new agent
            self.agents.append(agent)
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent"""
        self.agents = [a for a in self.agents if a['id'] != agent_id]
    
    def update_agent_status(
        self,
        agent_id: str,
        available: Optional[bool] = None,
        current_load: Optional[int] = None
    ):
        """Update agent status"""
        agent = next((a for a in self.agents if a['id'] == agent_id), None)
        if agent:
            if available is not None:
                agent['available'] = available
            if current_load is not None:
                agent['current_load'] = current_load
    
    def route(self, request: RouteRequest) -> RouteResponse:
        """Route request to appropriate agent"""
        request_dict = request.dict(exclude_none=True)
        
        selected_agent = self.strategy.select_agent(self.agents, request_dict)
        
        if not selected_agent:
            raise ValueError("No available agent found")
        
        # Calculate confidence based on strategy and agent match
        confidence = self._calculate_confidence(selected_agent, request_dict)
        
        # Update agent load
        if selected_agent['current_load'] < selected_agent.get('max_load', 10):
            selected_agent['current_load'] += 1
        
        return RouteResponse(
            agent_id=selected_agent['id'],
            agent_name=selected_agent['name'],
            strategy_used=self.strategy_name,
            confidence=confidence
        )
    
    def _calculate_confidence(
        self,
        agent: Dict[str, Any],
        request: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for agent selection"""
        base_confidence = 0.5
        
        # Increase confidence if agent capabilities match request intent
        if 'intent' in request:
            intent = request['intent'].lower()
            capabilities = [c.lower() for c in agent.get('capabilities', [])]
            if intent in capabilities:
                base_confidence += 0.3
        
        # Increase confidence if agent has low load
        max_load = agent.get('max_load', 10)
        current_load = agent.get('current_load', 0)
        load_factor = 1.0 - (current_load / max_load) if max_load > 0 else 1.0
        base_confidence += load_factor * 0.2
        
        return min(base_confidence, 1.0)
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent by ID"""
        return next((a for a in self.agents if a['id'] == agent_id), None)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents"""
        return self.agents.copy()
