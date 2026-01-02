"""
MEXC Client - Re-export from core.clients

DEPRECATED: Import from core.clients.mexc instead.
This file exists for backwards compatibility.

Fix for Issue #307: Consolidated duplicated code to core/clients/mexc.py
"""

# Re-export from central location
import time
from core.clients.mexc import MexcClient

__all__ = ["MexcClient", "time"]
