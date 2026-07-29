"""
Core safety module for Claire de Binare.
"""

from .kill_switch import KillSwitch, get_kill_switch_state, activate_kill_switch
from .stop_loss_protection import (
    STOP_LOSS_PROTECTION_STATUS,
    assert_stop_loss_protection_available,
    stop_loss_protection_is_available,
)

__all__ = [
    "KillSwitch",
    "get_kill_switch_state",
    "activate_kill_switch",
    "STOP_LOSS_PROTECTION_STATUS",
    "assert_stop_loss_protection_available",
    "stop_loss_protection_is_available",
]
