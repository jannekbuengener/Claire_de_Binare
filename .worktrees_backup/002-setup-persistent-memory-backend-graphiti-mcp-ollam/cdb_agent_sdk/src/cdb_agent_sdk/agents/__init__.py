"""
CDB Agent SDK - Spezialisierte Agenten

Jeder Agent hat eine klare, abgegrenzte Verantwortung.
Kein Agent überschreitet seine Governance-Grenzen.
"""

from .dataflow_observer import (
    DATAFLOW_OBSERVER_PROMPT,
    DATAFLOW_OBSERVER_TOOLS,
    create_dataflow_observer_options,
    run_dataflow_observer,
)
from .determinism_inspector import (
    DETERMINISM_INSPECTOR_PROMPT,
    DETERMINISM_INSPECTOR_TOOLS,
    create_determinism_inspector_options,
    run_determinism_inspector,
)
from .governance_auditor import (
    GOVERNANCE_AUDITOR_PROMPT,
    GOVERNANCE_AUDITOR_TOOLS,
    create_governance_auditor_options,
    run_governance_auditor,
)
from .change_impact_analyst import (
    CHANGE_IMPACT_ANALYST_PROMPT,
    CHANGE_IMPACT_TOOLS,
    create_change_impact_analyst_options,
    run_change_impact_analyst,
)

__all__ = [
    # Data Flow & Observability Engineer
    "DATAFLOW_OBSERVER_PROMPT",
    "DATAFLOW_OBSERVER_TOOLS",
    "create_dataflow_observer_options",
    "run_dataflow_observer",
    # Determinism Inspector
    "DETERMINISM_INSPECTOR_PROMPT",
    "DETERMINISM_INSPECTOR_TOOLS",
    "create_determinism_inspector_options",
    "run_determinism_inspector",
    # Governance Auditor
    "GOVERNANCE_AUDITOR_PROMPT",
    "GOVERNANCE_AUDITOR_TOOLS",
    "create_governance_auditor_options",
    "run_governance_auditor",
    # Change Impact Analyst
    "CHANGE_IMPACT_ANALYST_PROMPT",
    "CHANGE_IMPACT_TOOLS",
    "create_change_impact_analyst_options",
    "run_change_impact_analyst",
]
