"""
Base Agent Class

Provides common functionality for all specialized agents in the feature workflow.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class BaseAgent(ABC):
    """Base class for all workflow agents"""
    
    def __init__(self, name: str, role: str, description: str):
        self.name = name
        self.role = role
        self.description = description
        self.created_at = datetime.utcnow()
    
    def _error_response(self, error_message: str) -> Dict[str, Any]:
        """Generate standardized error response"""
        return {
            "agent": self.name,
            "error": True,
            "message": error_message,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _success_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate standardized success response"""
        response = {
            "agent": self.name,
            "error": False,
            "timestamp": datetime.utcnow().isoformat()
        }
        response.update(data)
        return response
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get agent information"""
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "created_at": self.created_at.isoformat()
        }