"""
Core safety module for Claire de Binare.
"""

from .kill_switch import KillSwitch, get_kill_switch_state, activate_kill_switch

__all__ = ["KillSwitch", "get_kill_switch_state", "activate_kill_switch"]
