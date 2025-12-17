"""
Feature Flag Management System

Provides environment-based feature toggles for safe feature deployment
and gradual rollout capabilities.
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class FeatureFlagState(Enum):
    """Feature flag states"""
    DISABLED = "disabled"
    ENABLED = "enabled"
    ROLLOUT = "rollout"  # Gradual rollout with percentage


@dataclass
class FeatureFlag:
    """Feature flag configuration"""
    name: str
    state: FeatureFlagState
    description: str
    rollout_percentage: float = 0.0
    environments: list = None
    
    def __post_init__(self):
        if self.environments is None:
            self.environments = ["development", "staging", "production"]


class FeatureFlagManager:
    """Manages feature flags with environment-based configuration"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.getenv("FEATURE_FLAGS_CONFIG", "config/feature_flags.json")
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.flags: Dict[str, FeatureFlag] = {}
        self._load_config()
    
    def _load_config(self):
        """Load feature flags from configuration file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    self._parse_config(config)
            else:
                # Initialize with default empty configuration
                self._init_default_config()
        except Exception as e:
            print(f"Warning: Failed to load feature flags config: {e}")
            self._init_default_config()
    
    def _parse_config(self, config: Dict[str, Any]):
        """Parse configuration dictionary into FeatureFlag objects"""
        for flag_name, flag_config in config.items():
            try:
                flag = FeatureFlag(
                    name=flag_name,
                    state=FeatureFlagState(flag_config.get("state", "disabled")),
                    description=flag_config.get("description", ""),
                    rollout_percentage=flag_config.get("rollout_percentage", 0.0),
                    environments=flag_config.get("environments", ["development", "staging", "production"])
                )
                self.flags[flag_name] = flag
            except Exception as e:
                print(f"Warning: Invalid flag configuration for {flag_name}: {e}")
    
    def _init_default_config(self):
        """Initialize with default configuration"""
        self.flags = {}
    
    def is_enabled(self, flag_name: str, user_id: Optional[str] = None) -> bool:
        """
        Check if a feature flag is enabled
        
        Args:
            flag_name: Name of the feature flag
            user_id: Optional user ID for rollout percentage calculation
            
        Returns:
            True if feature is enabled, False otherwise
        """
        flag = self.flags.get(flag_name)
        if not flag:
            # Unknown flags default to disabled
            return False
        
        # Check if flag is enabled for current environment
        if self.environment not in flag.environments:
            return False
        
        if flag.state == FeatureFlagState.DISABLED:
            return False
        elif flag.state == FeatureFlagState.ENABLED:
            return True
        elif flag.state == FeatureFlagState.ROLLOUT:
            # Simple hash-based percentage rollout
            if user_id and flag.rollout_percentage > 0:
                user_hash = hash(user_id) % 100
                return user_hash < flag.rollout_percentage
            return False
        
        return False
    
    def add_flag(self, flag: FeatureFlag):
        """Add a new feature flag"""
        self.flags[flag.name] = flag
    
    def update_flag(self, flag_name: str, state: FeatureFlagState, rollout_percentage: float = 0.0):
        """Update an existing feature flag"""
        if flag_name in self.flags:
            self.flags[flag_name].state = state
            self.flags[flag_name].rollout_percentage = rollout_percentage
    
    def get_all_flags(self) -> Dict[str, FeatureFlag]:
        """Get all feature flags"""
        return self.flags.copy()
    
    def save_config(self):
        """Save current feature flags to configuration file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            config = {}
            for flag_name, flag in self.flags.items():
                config[flag_name] = {
                    "state": flag.state.value,
                    "description": flag.description,
                    "rollout_percentage": flag.rollout_percentage,
                    "environments": flag.environments
                }
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving feature flags config: {e}")


# Global feature flag manager instance
_feature_flag_manager = None


def get_feature_flag_manager() -> FeatureFlagManager:
    """Get the global feature flag manager instance"""
    global _feature_flag_manager
    if _feature_flag_manager is None:
        _feature_flag_manager = FeatureFlagManager()
    return _feature_flag_manager


def is_feature_enabled(flag_name: str, user_id: Optional[str] = None) -> bool:
    """
    Convenience function to check if a feature is enabled
    
    Args:
        flag_name: Name of the feature flag
        user_id: Optional user ID for rollout calculation
        
    Returns:
        True if feature is enabled, False otherwise
    """
    return get_feature_flag_manager().is_enabled(flag_name, user_id)


# Common feature flags (can be extended)
class FeatureFlags:
    """Common feature flag names"""
    PAPER_TRADING_MODE = "paper_trading_mode"
    SIGNAL_OPTIMIZATION = "signal_optimization"
    ADVANCED_RISK_MANAGEMENT = "advanced_risk_management"
    NEW_WORKFLOW_ENGINE = "new_workflow_engine"
    AGENT_BLUEPRINT_SYSTEM = "agent_blueprint_system"