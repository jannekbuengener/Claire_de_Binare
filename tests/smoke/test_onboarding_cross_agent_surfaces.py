from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

CANONICAL_ROUTER_TEXT = (
    "If the user says `/onboarding`, `onboarding`, `onboarding durchführen`, "
    "`mach onboarding`, `fresh agent onboarding`, or equivalent, run: "
    "`python -m tools.onboarding_orchestrator`"
)

PRIMARY_ROUTE = "python -m tools.onboarding_orchestrator"
READ_ONLY_DEFAULT = "Read-only by default"
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

    def test_claude_onboarding_present_and_routed(self):
        text = read_text(".claude/skills/onboarding/SKILL.md")
        assert PRIMARY_ROUTE in text
        assert "tools/onboarding_orchestrator.py" in text

    def test_cursor_onboarding_present_and_routed(self):
        text = read_text(".cursor/skills/onboarding/SKILL.md")
        assert PRIMARY_ROUTE in text
        assert "tools/onboarding_orchestrator.py" in text


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
