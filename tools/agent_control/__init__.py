"""CDB Agent Control Plane tooling (registry + governed dispatcher).

Issues #4252 (registry) and #4253 (dispatcher). Provider-neutral.
No live provider mutations in these slices; mock-only execute.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "1.0.0"
