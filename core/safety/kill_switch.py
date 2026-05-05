"""
Emergency Stop / Kill-Switch Mechanism
Provides manual and automatic trading halt with persistent state.

CRITICAL SAFETY:
- Halts ALL trading immediately
- State persists across service restarts
- Cannot be bypassed (safety first)
- Audit log every activation/deactivation
"""

import os
import logging
import re
from pathlib import Path
from typing import Optional, Tuple
from enum import Enum

from core.utils.clock import utcnow

logger = logging.getLogger(__name__)


def _sanitize_for_log(value: str) -> str:
    """Neutralize CR, LF, and control characters for safe log output.

    Replaces \\r and \\n with escaped literal sequences and strips
    other control characters (0x00-0x08, 0x0b, 0x0c, 0x0e-0x1f)
    to prevent log injection attacks.
    """
    value = value.replace("\r", "\\r").replace("\n", "\\n")
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value)


class KillSwitchState(Enum):
    """Kill-switch activation states."""

    ACTIVE = "active"  # Trading STOPPED
    INACTIVE = "inactive"  # Trading allowed (normal operation)


class KillSwitchReason(Enum):
    """Reasons for kill-switch activation."""

    MANUAL = "manual"  # Manual intervention by operator
    CIRCUIT_BREAKER = "circuit_breaker"  # Auto: Daily loss limit exceeded
    RISK_LIMIT = "risk_limit"  # Auto: Risk exposure limit exceeded
    SYSTEM_ERROR = "system_error"  # Auto: Critical system error
    EXCHANGE_ERROR = "exchange_error"  # Auto: Exchange connection failure
    AUTH_FAILURE = "auth_failure"  # Auto: Authentication/authorization failure


class KillSwitch:
    """
    Persistent kill-switch for emergency trading halt.

    Stores state in file system for persistence across restarts.
    """

    def __init__(self, state_file: Optional[str] = None):
        """
        Initialize kill-switch.

        Args:
            state_file: Path to state file (default: .cdb_kill_switch.state in project root)

        Examples:
            >>> ks = KillSwitch()
            >>> ks.is_active()
            False

            >>> ks.activate(KillSwitchReason.MANUAL, "Emergency stop requested")
            >>> ks.is_active()
            True
        """
        if state_file is None:
            # Default to project root
            state_file = str(Path.cwd() / ".cdb_kill_switch.state")

        self.state_file = Path(state_file)
        self._ensure_state_file_exists()

    def _ensure_state_file_exists(self):
        """Create state file if it doesn't exist."""
        if not self.state_file.exists():
            self._write_state(
                state=KillSwitchState.INACTIVE,
                reason=None,
                message="Initial state",
                activated_at=None,
            )

    def _read_state(self) -> dict:
        """Read current state from file."""
        try:
            with open(self.state_file, "r") as f:
                lines = f.readlines()

            if not lines:
                return {
                    "state": KillSwitchState.INACTIVE.value,
                    "reason": None,
                    "message": "Empty state file",
                    "activated_at": None,
                }

            state_dict = {}
            for line in lines:
                line = line.strip()
                if not line or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                state_dict[key.strip()] = value.strip()

            return state_dict

        except Exception as e:
            logger.error(f"Error reading kill-switch state file: {e}")
            # Safe default: ACTIVE (halt trading on error)
            return {
                "state": KillSwitchState.ACTIVE.value,
                "reason": KillSwitchReason.SYSTEM_ERROR.value,
                "message": "State file read error",
                "activated_at": utcnow().isoformat(),
            }

    def _write_state(
        self,
        state: KillSwitchState,
        reason: Optional[KillSwitchReason],
        message: str,
        activated_at: Optional[str],
    ):
        """Write state to file with audit trail."""
        try:
            timestamp = utcnow().isoformat()

            content = (
                f"state={state.value}\n"
                f"reason={reason.value if reason else 'none'}\n"
                f"message={message}\n"
                f"activated_at={activated_at or 'none'}\n"
                f"updated_at={timestamp}\n"
            )

            # Atomic write (write to temp, then rename)
            temp_file = self.state_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                f.write(content)

            temp_file.replace(self.state_file)

            logger.info(
                f"Kill-switch state updated: {state.value} (reason: {reason.value if reason else 'none'})"
            )

        except Exception as e:
            logger.critical(f"CRITICAL: Failed to write kill-switch state: {e}")
            # If we can't write state, log loudly
            logger.critical(
                f"Intended state: {state.value}, reason: {reason}, message: {_sanitize_for_log(message)}"
            )

    def is_active(self) -> bool:
        """
        Check if kill-switch is currently active.

        Returns:
            True if trading is STOPPED, False if allowed

        Examples:
            >>> ks = KillSwitch()
            >>> ks.is_active()
            False  # Normal operation

            >>> ks.activate(KillSwitchReason.MANUAL, "Test")
            >>> ks.is_active()
            True  # Trading stopped
        """
        state_dict = self._read_state()
        state_value = state_dict.get("state", KillSwitchState.ACTIVE.value)
        return state_value == KillSwitchState.ACTIVE.value

    def get_state(self) -> Tuple[KillSwitchState, Optional[str], str, Optional[str]]:
        """
        Get full kill-switch state.

        Returns:
            (state, reason, message, activated_at)

        Examples:
            >>> ks = KillSwitch()
            >>> state, reason, message, activated_at = ks.get_state()
            >>> state == KillSwitchState.INACTIVE
            True
        """
        state_dict = self._read_state()

        state_value = state_dict.get("state", KillSwitchState.INACTIVE.value)
        state = (
            KillSwitchState.ACTIVE
            if state_value == "active"
            else KillSwitchState.INACTIVE
        )

        reason_value = state_dict.get("reason")
        reason = reason_value if reason_value and reason_value != "none" else None

        message = state_dict.get("message", "Unknown")
        activated_at = state_dict.get("activated_at")
        if activated_at == "none":
            activated_at = None

        return state, reason, message, activated_at

    def activate(
        self, reason: KillSwitchReason, message: str, operator: Optional[str] = None
    ) -> bool:
        """
        Activate kill-switch (STOP all trading).

        Args:
            reason: Reason for activation
            message: Human-readable explanation
            operator: Optional operator name/ID for manual stops

        Returns:
            True if activation successful

        Examples:
            >>> ks = KillSwitch()
            >>> ks.activate(KillSwitchReason.MANUAL, "Emergency stop requested", "admin")
            True

            >>> ks.is_active()
            True
        """
        activated_at = utcnow().isoformat()

        full_message = message
        if operator:
            full_message = f"{message} (operator: {operator})"

        self._write_state(
            state=KillSwitchState.ACTIVE,
            reason=reason,
            message=full_message,
            activated_at=activated_at,
        )

        logger.warning("=" * 80)
        logger.warning("🚨 KILL-SWITCH ACTIVATED - ALL TRADING STOPPED 🚨")
        logger.warning(f"Reason: {reason.value}")
        logger.warning(f"Message: {_sanitize_for_log(full_message)}")
        logger.warning(f"Activated at: {activated_at}")
        logger.warning("=" * 80)

        return True

    def deactivate(self, operator: str, justification: str) -> bool:
        """
        Deactivate kill-switch (RESUME trading).

        Args:
            operator: Operator name/ID (required for audit)
            justification: Reason for resuming trading (required)

        Returns:
            True if deactivation successful

        Examples:
            >>> ks = KillSwitch()
            >>> ks.activate(KillSwitchReason.MANUAL, "Test")
            >>> ks.deactivate("admin", "Issue resolved, safe to resume")
            True

            >>> ks.is_active()
            False
        """
        if not operator or not justification:
            logger.error("Kill-switch deactivation requires operator and justification")
            return False

        message = f"Deactivated by {operator}: {justification}"

        self._write_state(
            state=KillSwitchState.INACTIVE,
            reason=None,
            message=message,
            activated_at=None,
        )

        logger.warning("=" * 80)
        logger.warning("✅ KILL-SWITCH DEACTIVATED - TRADING RESUMED")
        logger.warning(f"Operator: {_sanitize_for_log(operator)}")
        logger.warning(f"Justification: {_sanitize_for_log(justification)}")
        logger.warning("=" * 80)

        return True


KILL_SWITCH_STATE_FILE_ENV = "CDB_KILL_SWITCH_STATE_FILE"

# Global singleton for easy access
_global_kill_switch: Optional[KillSwitch] = None


def resolve_kill_switch_state_file(state_file: Optional[str] = None) -> Path:
    """Resolve kill-switch state file path with optional env override."""
    if state_file:
        return Path(state_file)
    env_state_file = os.getenv(KILL_SWITCH_STATE_FILE_ENV, "").strip()
    if env_state_file:
        return Path(env_state_file)
    return Path.cwd() / ".cdb_kill_switch.state"


def get_kill_switch_details(
    state_file: Optional[str] = None, *, create_if_missing: bool = True
) -> Tuple[bool, Optional[str], str, Optional[str]]:
    """Read kill-switch state details without exposing internal state format.

    Returns:
        (is_active, reason, message, activated_at)
    """
    resolved_state_file = resolve_kill_switch_state_file(state_file)
    if not create_if_missing and not resolved_state_file.exists():
        return False, None, "State file missing", None
    kill_switch = KillSwitch(str(resolved_state_file))
    state, reason, message, activated_at = kill_switch.get_state()
    return state == KillSwitchState.ACTIVE, reason, message, activated_at


def get_kill_switch_state(state_file: Optional[str] = None) -> bool:
    """
    Check if kill-switch is active (global singleton).

    Args:
        state_file: Optional state file path

    Returns:
        True if trading is STOPPED, False if allowed

    Examples:
        >>> get_kill_switch_state()
        False  # Normal operation

        >>> activate_kill_switch(KillSwitchReason.MANUAL, "Test")
        >>> get_kill_switch_state()
        True  # Trading stopped
    """
    global _global_kill_switch

    if _global_kill_switch is None:
        _global_kill_switch = KillSwitch(state_file)

    return _global_kill_switch.is_active()


def activate_kill_switch(
    reason: KillSwitchReason, message: str, operator: Optional[str] = None
) -> bool:
    """
    Activate global kill-switch.

    Args:
        reason: Reason for activation
        message: Human-readable explanation
        operator: Optional operator name/ID

    Returns:
        True if activation successful

    Examples:
        >>> activate_kill_switch(KillSwitchReason.MANUAL, "Emergency", "admin")
        True
    """
    global _global_kill_switch

    if _global_kill_switch is None:
        _global_kill_switch = KillSwitch()

    return _global_kill_switch.activate(reason, message, operator)
