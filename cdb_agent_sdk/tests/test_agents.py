"""Tests für die spezialisierten CDB Agenten."""

import pytest

from cdb_agent_sdk.agents.dataflow_observer import (
    DATAFLOW_OBSERVER_PROMPT,
    DATAFLOW_OBSERVER_TOOLS,
    create_dataflow_observer_options,
)
from cdb_agent_sdk.agents.determinism_inspector import (
    DETERMINISM_INSPECTOR_PROMPT,
    DETERMINISM_INSPECTOR_TOOLS,
    create_determinism_inspector_options,
)
from cdb_agent_sdk.agents.governance_auditor import (
    GOVERNANCE_AUDITOR_PROMPT,
    GOVERNANCE_AUDITOR_TOOLS,
    create_governance_auditor_options,
)
from cdb_agent_sdk.agents.change_impact_analyst import (
    CHANGE_IMPACT_ANALYST_PROMPT,
    CHANGE_IMPACT_TOOLS,
    create_change_impact_analyst_options,
)


class TestDataflowObserver:
    """Tests für den Data Flow & Observability Engineer."""

    def test_prompt_contains_role_definition(self):
        """Prompt enthält Rollendefinition."""
        assert "Data Flow & Observability Engineer" in DATAFLOW_OBSERVER_PROMPT

    def test_prompt_contains_data_ontology(self):
        """Prompt enthält Datenontologie."""
        assert "Event" in DATAFLOW_OBSERVER_PROMPT
        assert "State" in DATAFLOW_OBSERVER_PROMPT
        assert "Metric" in DATAFLOW_OBSERVER_PROMPT
        assert "Log" in DATAFLOW_OBSERVER_PROMPT

    def test_prompt_defines_scope_boundary(self):
        """Prompt definiert klare Scope-Grenzen."""
        assert "sichtbar machen" in DATAFLOW_OBSERVER_PROMPT.lower()
        assert "niemals erzeugen" in DATAFLOW_OBSERVER_PROMPT.lower()

    def test_tools_include_bash(self):
        """Bash ist für Commands vorhanden."""
        assert "Bash" in DATAFLOW_OBSERVER_TOOLS

    def test_options_creation(self):
        """Options werden korrekt erstellt."""
        options = create_dataflow_observer_options()
        assert options.system_prompt == DATAFLOW_OBSERVER_PROMPT
        assert options.allowed_tools == DATAFLOW_OBSERVER_TOOLS
        assert options.permission_mode == "bypassPermissions"


class TestDeterminismInspector:
    """Tests für den Execution Determinism Inspector."""

    def test_prompt_contains_core_question(self):
        """Prompt enthält die Kernfrage."""
        assert "identischer Input" in DETERMINISM_INSPECTOR_PROMPT
        assert "identischem Output" in DETERMINISM_INSPECTOR_PROMPT

    def test_prompt_defines_scope_boundary(self):
        """Prompt definiert klare Scope-Grenzen."""
        assert "out of scope" in DETERMINISM_INSPECTOR_PROMPT.lower()
        assert "einzige frage" in DETERMINISM_INSPECTOR_PROMPT.lower()

    def test_prompt_contains_determinism_definition(self):
        """Prompt enthält Definition von Determinismus."""
        assert "Gleicher Input" in DETERMINISM_INSPECTOR_PROMPT
        assert "Gleicher Output" in DETERMINISM_INSPECTOR_PROMPT

    def test_tools_are_read_only(self):
        """Tools sind primär read-only."""
        # Keine Write/Edit Tools
        assert "Write" not in DETERMINISM_INSPECTOR_TOOLS
        assert "Edit" not in DETERMINISM_INSPECTOR_TOOLS
        # Read-Tools vorhanden
        assert "Read" in DETERMINISM_INSPECTOR_TOOLS
        assert "Grep" in DETERMINISM_INSPECTOR_TOOLS

    def test_options_creation(self):
        """Options werden korrekt erstellt."""
        options = create_determinism_inspector_options()
        assert options.system_prompt == DETERMINISM_INSPECTOR_PROMPT
        assert options.allowed_tools == DETERMINISM_INSPECTOR_TOOLS
        assert options.permission_mode == "bypassPermissions"

    def test_options_with_custom_cwd(self):
        """Custom CWD wird akzeptiert."""
        cwd = "/custom/path"
        options = create_determinism_inspector_options(cwd=cwd)
        assert options.cwd == cwd


class TestGovernanceAuditor:
    """Tests für den Governance & Canon Auditor."""

    def test_prompt_contains_drift_concept(self):
        """Prompt enthält das Drift-Konzept."""
        assert "Drift" in GOVERNANCE_AUDITOR_PROMPT
        assert "Canon" in GOVERNANCE_AUDITOR_PROMPT
        assert "Governance" in GOVERNANCE_AUDITOR_PROMPT

    def test_prompt_defines_four_layers(self):
        """Prompt definiert die vier Wahrheitsebenen."""
        assert "Canon" in GOVERNANCE_AUDITOR_PROMPT
        assert "Governance" in GOVERNANCE_AUDITOR_PROMPT
        assert "Code" in GOVERNANCE_AUDITOR_PROMPT
        assert "Runtime" in GOVERNANCE_AUDITOR_PROMPT

    def test_prompt_defines_scope_boundary(self):
        """Prompt definiert klare Scope-Grenzen."""
        assert "identifizierst Drift" in GOVERNANCE_AUDITOR_PROMPT
        assert "reparierst" in GOVERNANCE_AUDITOR_PROMPT
        assert "nicht" in GOVERNANCE_AUDITOR_PROMPT.lower()

    def test_tools_include_bash_for_git(self):
        """Bash ist für git history Analyse vorhanden."""
        assert "Bash" in GOVERNANCE_AUDITOR_TOOLS

    def test_options_creation(self):
        """Options werden korrekt erstellt."""
        options = create_governance_auditor_options()
        assert options.system_prompt == GOVERNANCE_AUDITOR_PROMPT
        assert options.allowed_tools == GOVERNANCE_AUDITOR_TOOLS


class TestChangeImpactAnalyst:
    """Tests für den Change Impact Analyst."""

    def test_prompt_contains_impact_concept(self):
        """Prompt enthält das Impact-Konzept."""
        assert "Impact" in CHANGE_IMPACT_ANALYST_PROMPT
        assert "Auswirkungen" in CHANGE_IMPACT_ANALYST_PROMPT

    def test_prompt_emphasizes_before_change(self):
        """Prompt betont Analyse VOR der Änderung."""
        assert "BEVOR" in CHANGE_IMPACT_ANALYST_PROMPT or \
               "bevor" in CHANGE_IMPACT_ANALYST_PROMPT

    def test_prompt_defines_scope_boundary(self):
        """Prompt definiert klare Scope-Grenzen."""
        assert "analysierst" in CHANGE_IMPACT_ANALYST_PROMPT.lower()
        assert "änderst nicht" in CHANGE_IMPACT_ANALYST_PROMPT.lower()

    def test_prompt_contains_cdb_specific_paths(self):
        """Prompt enthält CDB-spezifische Abhängigkeitspfade."""
        # Service-Abhängigkeiten
        assert "signal" in CHANGE_IMPACT_ANALYST_PROMPT.lower()
        assert "execution" in CHANGE_IMPACT_ANALYST_PROMPT.lower()
        # Datenstrukturen
        assert "core/domain" in CHANGE_IMPACT_ANALYST_PROMPT

    def test_tools_include_bash_for_git(self):
        """Bash ist für git diff/log Analyse vorhanden."""
        assert "Bash" in CHANGE_IMPACT_TOOLS

    def test_options_creation(self):
        """Options werden korrekt erstellt."""
        options = create_change_impact_analyst_options()
        assert options.system_prompt == CHANGE_IMPACT_ANALYST_PROMPT
        assert options.allowed_tools == CHANGE_IMPACT_TOOLS


class TestAgentScopeBoundaries:
    """Tests für die Scope-Grenzen aller Agenten."""

    def test_determinism_inspector_is_focused(self):
        """Determinism Inspector hat engen Fokus."""
        # Nur eine Frage
        assert "einzige frage" in DETERMINISM_INSPECTOR_PROMPT.lower()

    def test_governance_auditor_does_not_fix(self):
        """Governance Auditor repariert nicht."""
        prompt_lower = GOVERNANCE_AUDITOR_PROMPT.lower()
        assert "identifizierst drift" in prompt_lower
        assert "reparierst" in prompt_lower

    def test_change_impact_does_not_change(self):
        """Change Impact Analyst ändert nicht."""
        prompt_lower = CHANGE_IMPACT_ANALYST_PROMPT.lower()
        assert "analysierst" in prompt_lower
        assert "änderst nicht" in prompt_lower

    def test_all_agents_are_read_only(self):
        """Alle Agenten haben keine Write-Tools."""
        all_tools = (
            DATAFLOW_OBSERVER_TOOLS +
            DETERMINISM_INSPECTOR_TOOLS +
            GOVERNANCE_AUDITOR_TOOLS +
            CHANGE_IMPACT_TOOLS
        )
        assert "Write" not in all_tools
        assert "Edit" not in all_tools
