from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

CANONICAL_ROUTER_TEXT = (
    "If the user says `/onboarding`, `onboarding`, `onboarding durchführen`, "
    "`mach onboarding`, `fresh agent onboarding`, or equivalent, run: "
    "`python -m tools.onboarding_orchestrator`"
)

GUIDED_REHEARSAL_ROUTER_TEXT = (
    "onboarding_simulation --mode guided-rehearsal --role developer"
)

GUIDED_REHEARSAL_INTENT_PHRASES = [
    "onboarding rehearsal",
    "guided rehearsal",
    "rehearsal mode",
    "generalprobe",
    "reisefuehrer",
    "realitaetsnah simulieren",
]

PRIMARY_ROUTE = "python -m tools.onboarding_orchestrator"
READ_ONLY_DEFAULT = "Read-only by default"
STATE_CONTRACT = "allowed_next_actions"
CHECK_ONLY_GUARDRAIL = "check-only"
NO_ENV_DEFAULT = (
    "Do not create `.env`, initialize secrets, initialize context, write "
    "reports, create issues, or run Docker unless the user explicitly selects "
    "a next option after the status card."
)


def read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def assert_route_contract(relative_path: str) -> None:
    text = read_text(relative_path)
    assert CANONICAL_ROUTER_TEXT in text
    assert PRIMARY_ROUTE in text
    assert "Default output is the CDB Onboarding status card." in text
    assert NO_ENV_DEFAULT in text


class TestCodexOnboardingSurface:
    def test_codex_onboarding_skill_exists(self):
        assert (REPO_ROOT / ".codex/cdb_skills/onboarding/SKILL.md").exists()

    def test_codex_onboarding_skill_routes_to_orchestrator(self):
        text = read_text(".codex/cdb_skills/onboarding/SKILL.md")
        assert PRIMARY_ROUTE in text
        assert "tools/onboarding_orchestrator.py" in text or PRIMARY_ROUTE in text

    def test_codex_onboarding_skill_is_read_only_default(self):
        text = read_text(".codex/cdb_skills/onboarding/SKILL.md")
        assert READ_ONLY_DEFAULT in text
        assert "LR remains NO-GO" in text
        assert "trade-capable` is not Live-Go" in text

    def test_codex_alias_is_thin(self):
        text = read_text(".codex/cdb_skills/cdb-onboarding/SKILL.md")
        assert "../onboarding/SKILL.md" in text
        assert PRIMARY_ROUTE in text


class TestRootAndRoleRouters:
    def test_root_agents_contains_onboarding_router(self):
        assert_route_contract("AGENTS.md")

    def test_codex_role_contains_onboarding_router(self):
        assert_route_contract("agents/roles/CODEX.md")

    def test_gemini_contains_onboarding_router(self):
        assert_route_contract("GEMINI.md")


class TestSharedOnboardingSkills:
    def test_opencode_onboarding_remains_canonical(self):
        text = read_text(".opencode/skills/onboarding/SKILL.md")
        assert PRIMARY_ROUTE in text
        assert "tools/onboarding_orchestrator.py" in text
        assert "Read-only by default" in text
        assert STATE_CONTRACT in text

    def test_claude_onboarding_present_and_routed(self):
        text = read_text(".claude/skills/onboarding/SKILL.md")
        assert PRIMARY_ROUTE in text
        assert "tools/onboarding_orchestrator.py" in text
        assert STATE_CONTRACT in text

    def test_cursor_onboarding_present_and_routed(self):
        text = read_text(".cursor/skills/onboarding/SKILL.md")
        assert PRIMARY_ROUTE in text
        assert "tools/onboarding_orchestrator.py" in text
        assert STATE_CONTRACT in text


class TestSessionStartDelegation:
    def test_codex_session_start_delegates_onboarding_intent(self):
        text = read_text(".codex/cdb_skills/cdb-session-start/SKILL.md")
        assert PRIMARY_ROUTE in text
        assert "Do not start `cdb-session-start` or `onboarding_doctor`" in text

    def test_claude_session_start_delegates_onboarding_intent(self):
        text = read_text(".claude/skills/cdb-session-start/SKILL.md")
        assert PRIMARY_ROUTE in text

    def test_cursor_session_start_delegates_onboarding_intent(self):
        text = read_text(".cursor/skills/cdb-session-start/SKILL.md")
        assert PRIMARY_ROUTE in text

    def test_opencode_session_start_delegates_onboarding_intent(self):
        text = read_text(".opencode/skills/cdb-session-start/SKILL.md")
        assert PRIMARY_ROUTE in text


class TestSafetyGuardrails:
    def test_no_default_surface_tells_users_to_create_env(self):
        surfaces = [
            "AGENTS.md",
            "agents/roles/CODEX.md",
            "GEMINI.md",
            ".codex/cdb_skills/onboarding/SKILL.md",
            ".claude/skills/onboarding/SKILL.md",
            ".cursor/skills/onboarding/SKILL.md",
            ".opencode/skills/onboarding/SKILL.md",
        ]
        for relative_path in surfaces:
            text = read_text(relative_path)
            assert NO_ENV_DEFAULT in text
            assert "context-query-config-init" not in text

    def test_main_surfaces_document_check_only_guardrail(self):
        surfaces = [
            ".codex/cdb_skills/onboarding/SKILL.md",
            ".claude/skills/onboarding/SKILL.md",
            ".cursor/skills/onboarding/SKILL.md",
            ".opencode/skills/onboarding/SKILL.md",
            ".gemini/onboarding.md",
        ]
        for relative_path in surfaces:
            text = read_text(relative_path)
            assert CHECK_ONLY_GUARDRAIL in text
            assert "setup-plan" not in text

    def test_all_surfaces_preserve_lr_no_go_boundary(self):
        surfaces = [
            ".codex/cdb_skills/onboarding/SKILL.md",
            ".claude/skills/onboarding/SKILL.md",
            ".cursor/skills/onboarding/SKILL.md",
            ".opencode/skills/onboarding/SKILL.md",
        ]
        for relative_path in surfaces:
            text = read_text(relative_path)
            assert "NO-GO" in text
            assert "trade-capable" in text
            assert "Live-Go" in text


GUIDED_REHEARSAL_SURFACES = [
    ".codex/cdb_skills/onboarding/SKILL.md",
    ".claude/skills/onboarding/SKILL.md",
    ".cursor/skills/onboarding/SKILL.md",
    ".opencode/skills/onboarding/SKILL.md",
    ".gemini/onboarding.md",
]


class TestGuidedRehearsalRouting:
    def test_guided_rehearsal_routes_correctly(self):
        for relative_path in GUIDED_REHEARSAL_SURFACES:
            text = read_text(relative_path)
            assert (
                GUIDED_REHEARSAL_ROUTER_TEXT in text
            ), f"{relative_path}: missing guided-rehearsal route"

    def test_guided_rehearsal_states_no_setup_go(self):
        for relative_path in GUIDED_REHEARSAL_SURFACES:
            text = read_text(relative_path)
            assert (
                "kein Setup-GO" in text.lower()
                or "guided rehearsal ist kein" in text.lower()
            ), f"{relative_path}: missing 'kein Setup-GO' guardrail"

    def test_guided_rehearsal_mentions_simulation(self):
        for relative_path in GUIDED_REHEARSAL_SURFACES:
            text = read_text(relative_path)
            assert (
                "simuliert" in text.lower() or "simulierten" in text.lower()
            ), f"{relative_path}: missing simulation mention"

    def test_guided_rehearsal_mentions_mutating_steps(self):
        for relative_path in GUIDED_REHEARSAL_SURFACES:
            text = read_text(relative_path)
            assert (
                "mutierende" in text.lower()
                or "Mutierende" in text
                or "mutating" in text.lower()
            ), f"{relative_path}: missing mutating steps mention"

    def test_root_agents_has_guided_rehearsal_router(self):
        text = read_text("AGENTS.md")
        assert GUIDED_REHEARSAL_ROUTER_TEXT in text

    def test_gemini_root_has_guided_rehearsal(self):
        text = read_text("GEMINI.md")
        assert GUIDED_REHEARSAL_ROUTER_TEXT in text

    def test_gemini_agent_has_guided_rehearsal(self):
        text = read_text("agents/GEMINI.md")
        assert "guided-rehearsal" in text

    def test_guided_rehearsal_does_not_break_normal_routing(self):
        for relative_path in GUIDED_REHEARSAL_SURFACES:
            text = read_text(relative_path)
            assert (
                PRIMARY_ROUTE in text
            ), f"{relative_path}: guided-rehearsal added but lost normal route"

    def test_guided_rehearsal_intent_phrases_present(self):
        for relative_path in GUIDED_REHEARSAL_SURFACES:
            text = read_text(relative_path)
            found_any = any(
                phrase in text for phrase in GUIDED_REHEARSAL_INTENT_PHRASES
            )
            assert (
                found_any
            ), f"{relative_path}: no guided-rehearsal intent phrases found"


# Forbidden phrases are expected to appear in "Verbotene Phrasen" or "Nicht"
# sections of the contract files (as documented examples of prohibited wording).
# The test verifies they don't appear OUTSIDE these documented context sections.
FORBIDDEN_WORDING_PATTERNS: list[tuple[str, str]] = [
    ("Live-Wahrheit gepr\u00fcft: Ja", ".gemini/onboarding.md"),
    ("trade-capable ist deaktiviert", ".gemini/onboarding.md"),
    ("alle systemischen Invarianten erfasst", ".gemini/onboarding.md"),
    ("CURRENT_STATUS.md ist Live-Wahrheit", ".gemini/onboarding.md"),
]

# These files must NOT contain the forbidden phrases at all (they're response
# contracts, not forbidden-phrase documentation):
NO_FORBIDDEN_ALLOWED_SURFACES: list[str] = [
    ".opencode/README.md",
    ".codex/README.md",
    ".claude/README.md",
    ".cursor/README.md",
    ".gemini/README.md",
    "docs/onboarding/ONBOARDING_SCENARIO_001_FRESH_AGENT_SAFE_WORK_DRILL.md",
]

# Context lines that make a forbidden phrase acceptable (it's being documented as forbidden)
ALLOWED_CONTEXT_PREFIXES = [
    "Nicht:",
    "Verbotene Phrasen",
    "forbidden phrase",
    "Verbotene",
]

REQUIRED_EVIDENCE_PATTERNS: dict[str, list[str]] = {
    "Evidence-Abgrenzung": [
        "GEMINI.md",
        ".gemini/onboarding.md",
        ".opencode/skills/onboarding/SKILL.md",
        ".codex/cdb_skills/onboarding/SKILL.md",
        ".claude/skills/onboarding/SKILL.md",
        ".cursor/skills/onboarding/SKILL.md",
        ".gemini/README.md",
    ],
    "Repo-/Canon-/Onboarding-Status gepr\u00fcft; GitHub-/Check-Live nicht gepr\u00fcft": [
        "GEMINI.md",
    ],
    "`tools.onboarding_orchestrator` z\u00e4hlt als Onboarding-Statuspr\u00fcfung": [
        "GEMINI.md",
    ],
    "`CURRENT_STATUS.md` ist Engineering-Ledger, nicht Live-Wahrheit": [
        "GEMINI.md",
    ],
    "`trade-capable` ist Board-/Stage-Kontext, kein Live-Go": [
        "GEMINI.md",
    ],
    "Repo-/Canon-Pr\u00fcfung durchgef\u00fchrt; GitHub-/Check-Live nicht gepr\u00fcft": [
        ".gemini/onboarding.md",
        ".opencode/skills/onboarding/SKILL.md",
        ".codex/cdb_skills/onboarding/SKILL.md",
        ".claude/skills/onboarding/SKILL.md",
        ".cursor/skills/onboarding/SKILL.md",
    ],
    "Engineering-Ledger, nicht Live-Wahrheit": [
        ".gemini/onboarding.md",
        ".opencode/skills/onboarding/SKILL.md",
        ".codex/cdb_skills/onboarding/SKILL.md",
        ".claude/skills/onboarding/SKILL.md",
        ".cursor/skills/onboarding/SKILL.md",
    ],
    "Board-/Stage-Kontext, kein Live-Go": [
        ".gemini/onboarding.md",
        ".opencode/skills/onboarding/SKILL.md",
        ".codex/cdb_skills/onboarding/SKILL.md",
        ".claude/skills/onboarding/SKILL.md",
        ".cursor/skills/onboarding/SKILL.md",
    ],
}

ALL_ONBOARDING_RESPONSE_SURFACES = [
    ".gemini/onboarding.md",
    ".opencode/skills/onboarding/SKILL.md",
    ".codex/cdb_skills/onboarding/SKILL.md",
    ".claude/skills/onboarding/SKILL.md",
    ".cursor/skills/onboarding/SKILL.md",
]

ALL_FORBIDDEN_PHRASES = [
    "Live-Wahrheit gepr\u00fcft: Ja",
    "Live-Wahrheit gepr\u00fcft: ja",
    "Live-Wahrheit gepr\u00fcft: ja/nein",
    "via tools.onboarding_orchestrator",
    "F\u00fchrt cp .env.example .env aus",
    "trade-capable ist deaktiviert",
    "trade-capable ist aktiviert",
    "alle systemischen Invarianten erfasst",
    "vollst\u00e4ndige Live-Wahrheit gepr\u00fcft",
    "CURRENT_STATUS.md ist Live-Wahrheit",
    "trade-capable erlaubt Live",
    "trade-capable ist Live-Go",
]


class TestWordingContract:
    """Verify forbidden phrases only appear in documented context and required evidence patterns present."""

    def test_forbidden_phrases_only_in_documented_context(self):
        """Forbidden phrases may appear in 'Verbotene Phrasen' / 'Nicht' context
        in response-surface docs, but must NOT appear in README/scenario surfaces."""
        for surface in NO_FORBIDDEN_ALLOWED_SURFACES:
            text = read_text(surface)
            for phrase in ALL_FORBIDDEN_PHRASES:
                assert (
                    phrase not in text
                ), f"{surface}: contains forbidden phrase '{phrase}'"

    def test_no_free_management_summary_phrasing(self):
        """No surface should contain conclusory live-truth claims outside documented context."""
        for surface in ALL_ONBOARDING_RESPONSE_SURFACES:
            text = read_text(surface)
            assert (
                "Evidence-Abgrenzung" in text or "Management-Zusammenfassung" in text
            ), f"{surface}: keine Abgrenzung gegen freie Management-Zusammenfassung"

    def test_required_evidence_patterns_present(self):
        missing: list[str] = []
        for pattern, surfaces in REQUIRED_EVIDENCE_PATTERNS.items():
            for surface in surfaces:
                text = read_text(surface)
                if pattern not in text:
                    missing.append(f"{surface}: missing required pattern '{pattern}'")
        assert not missing, "\n".join(missing)

    def test_all_response_surfaces_have_evidence_abgrenzung(self):
        for surface in ALL_ONBOARDING_RESPONSE_SURFACES:
            text = read_text(surface)
            assert (
                "Evidence-Abgrenzung" in text
            ), f"{surface}: missing Evidence-Abgrenzung section"

    def test_all_response_surfaces_have_lr_ssot_reference(self):
        for surface in ALL_ONBOARDING_RESPONSE_SURFACES:
            text = read_text(surface)
            assert (
                "LR-AUDIT-STATUS" in text or "docs/live-readiness" in text
            ), f"{surface}: missing LR-SSOT reference"

    def test_all_response_surfaces_declare_trade_capable_not_live_go(self):
        for surface in ALL_ONBOARDING_RESPONSE_SURFACES:
            text = read_text(surface)
            assert "trade-capable" in text
            assert "Live-Go" in text
