"""Agent role consistency contract tests (#3869).

Static checks that Codex, Claude, Gemini, Copilot, and OpenCode role surfaces
do not contradict each other on LR, Live-Go, MCP, writes, Brain Evidence,
or onboarding routing references.

MCP capability resolution depth remains #3870; here we only guard shared
role references and forbidden live-go phrasing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.agents._agent_os_contract_helpers import (
    CANONICAL_AGENT_ROLE_PATHS,
    FORBIDDEN_ROLE_LIVE_GO_PHRASES,
    FORBIDDEN_ROLE_LIVE_GO_STANDALONE,
    MCP_CAPABILITY_REFERENCE_ANCHORS,
    ONBOARDING_PRIMARY_ROUTE,
    ONBOARDING_ROUTING_ROLE_PATHS,
    ROLE_SPECIFIC_GUARDRAIL_ANCHORS,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]

OPEN_CODE_AGENTS = REPO_ROOT / "agents" / "OPEN_CODE_AGENTS.md"
AGENTS_REGISTRY = REPO_ROOT / "agents" / "AGENTS.md"


def _read_repo(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Role file presence + shared guardrails
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("relative_path", list(CANONICAL_AGENT_ROLE_PATHS.values()))
def test_canonical_agent_role_files_exist(relative_path: str) -> None:
    assert (REPO_ROOT / relative_path).is_file(), f"missing role file: {relative_path}"


@pytest.mark.parametrize(
    ("role_name", "relative_path"),
    list(CANONICAL_AGENT_ROLE_PATHS.items()),
)
def test_roles_share_brain_evidence_and_status_guardrails(
    role_name: str, relative_path: str
) -> None:
    text = _read_repo(relative_path)
    anchors = ROLE_SPECIFIC_GUARDRAIL_ANCHORS[role_name]
    for anchor in anchors:
        assert anchor in text, f"{role_name}: missing guardrail {anchor!r}"


@pytest.mark.parametrize(
    ("role_name", "relative_path"),
    list(CANONICAL_AGENT_ROLE_PATHS.items()),
)
def test_roles_do_not_authorize_live_go_phrases(
    role_name: str, relative_path: str
) -> None:
    text = _read_repo(relative_path)
    for phrase in FORBIDDEN_ROLE_LIVE_GO_PHRASES:
        assert phrase not in text, f"{role_name}: forbidden live-go phrase {phrase!r}"
    for phrase in FORBIDDEN_ROLE_LIVE_GO_STANDALONE:
        if phrase not in text:
            continue
        for line in text.splitlines():
            if phrase not in line:
                continue
            lowered = line.lower()
            if any(neg in lowered for neg in ("kein ", "nicht ", "no ", "never ", "nie ")):
                continue
            pytest.fail(
                f"{role_name}: affirmative live-go phrase {phrase!r} in line: {line.strip()}"
            )


# ---------------------------------------------------------------------------
# Onboarding routing consistency (#3869)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("relative_path", ONBOARDING_ROUTING_ROLE_PATHS)
def test_onboarding_entry_surfaces_route_to_orchestrator(relative_path: str) -> None:
    text = _read_repo(relative_path)
    assert ONBOARDING_PRIMARY_ROUTE in text, (
        f"{relative_path}: missing onboarding orchestrator route"
    )


def test_agents_registry_documents_onboarding_intent_router() -> None:
    text = _read_repo("AGENTS.md")
    assert "Quick Intent Router" in text or "onboarding" in text.lower()
    assert ONBOARDING_PRIMARY_ROUTE in text


def test_codex_role_defers_onboarding_from_session_start() -> None:
    text = _read_repo("agents/roles/CODEX.md")
    assert "Do not start `cdb-session-start` or `onboarding_doctor`" in text
    assert "Default output is the CDB Onboarding status card." in text


# ---------------------------------------------------------------------------
# Brain Evidence + MCP capability references (#3869, not full #3870)
# ---------------------------------------------------------------------------


def test_open_code_agents_requires_brain_evidence_before_planning() -> None:
    text = OPEN_CODE_AGENTS.read_text(encoding="utf-8")
    assert "Brain Evidence Gate" in text
    assert "brain_source" in text
    assert "context_brain_attempted" in text
    assert "vor jeder Planung" in text


def test_open_code_agents_references_mcp_capability_resolution() -> None:
    text = OPEN_CODE_AGENTS.read_text(encoding="utf-8")
    for anchor in MCP_CAPABILITY_REFERENCE_ANCHORS:
        assert anchor in text, f"OPEN_CODE_AGENTS missing MCP anchor: {anchor!r}"


def test_open_code_agents_blocks_writes_without_human_go() -> None:
    text = OPEN_CODE_AGENTS.read_text(encoding="utf-8")
    assert "Keine Writes ohne Human-GO" in text
    assert "MUTATION_ALLOWED=False" in text
    assert "PERSIST_ALLOWED=False" in text


def test_agents_registry_brain_evidence_matches_open_code_contract() -> None:
    registry = AGENTS_REGISTRY.read_text(encoding="utf-8")
    opencode = OPEN_CODE_AGENTS.read_text(encoding="utf-8")
    for field in ("context_brain_attempted", "repo_fallback_reason", "brain_source"):
        assert field in registry, f"agents/AGENTS.md missing {field!r}"
        assert field in opencode, f"OPEN_CODE_AGENTS missing {field!r}"


def test_gemini_role_declares_trade_capable_not_lr_go() -> None:
    text = _read_repo("agents/roles/GEMINI.md")
    assert "trade-capable` ist kein LR-GO" in text or "kein LR-GO" in text
    assert "kein Live-Kapital" in text or "Live-Kapital" in text


def test_copilot_role_preserves_lr_no_go_with_trade_capable_stage() -> None:
    text = _read_repo("agents/roles/COPILOT.md")
    assert "trade-capable" in text
    assert "LR-050 NO-GO" in text or "NO-GO" in text
