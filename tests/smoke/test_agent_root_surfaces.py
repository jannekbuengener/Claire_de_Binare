from __future__ import annotations

from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[2]

SHARED_ONBOARDING_TEXT = (
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
FORBIDDEN_PATTERNS = [
    "token",
    "auth",
    "secret",
    "transcript",
    "cache",
    "github_issue_body",
]


def read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def git_ls_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    return set(result.stdout.strip().splitlines())


def gitignore_text() -> str:
    return (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")


class TestGeminiNotBlanketIgnored:
    def test_gemini_not_blanket_ignored(self):
        gi = gitignore_text()
        assert (
            ".gemini/*" in gi
        ), ".gemini/ blanket ignore must be replaced with .gemini/*"
        assert "!.gemini/README.md" in gi, "README.md must be allowlisted"
        assert "!.gemini/settings.json" in gi, "settings.json must be allowlisted"
        assert "!.gemini/onboarding.md" in gi, "onboarding.md must be allowlisted"


class TestVscodeNotBlanketIgnored:
    def test_vscode_not_blanket_ignored(self):
        gi = gitignore_text()
        assert (
            ".vscode/*" in gi
        ), ".vscode/ blanket ignore must be replaced with .vscode/*"
        assert "!.vscode/README.md" in gi, "README.md must be allowlisted"
        assert "!.vscode/extensions.json" in gi, "extensions.json must be allowlisted"
        assert "!.vscode/settings.json" in gi, "settings.json must be allowlisted"


class TestGeminiSurface:
    def test_gemini_readme_exists_and_tracked(self):
        path = ".gemini/README.md"
        assert (REPO_ROOT / path).exists()
        tracked = git_ls_files()
        assert path in tracked, f"{path} must be tracked"

    def test_gemini_onboarding_md_exists_and_tracked(self):
        path = ".gemini/onboarding.md"
        assert (REPO_ROOT / path).exists()
        tracked = git_ls_files()
        assert path in tracked, f"{path} must be tracked"

    def test_gemini_settings_json_tracked(self):
        path = ".gemini/settings.json"
        tracked = git_ls_files()
        assert path in tracked, f"{path} must be tracked"

    def test_gemini_onboarding_md_routes_correctly(self):
        text = read_text(".gemini/onboarding.md")
        assert PRIMARY_ROUTE in text
        assert READ_ONLY_DEFAULT in text
        assert NO_ENV_DEFAULT in text


class TestVscodeSurface:
    def test_vscode_readme_exists_and_tracked(self):
        path = ".vscode/README.md"
        assert (REPO_ROOT / path).exists()
        tracked = git_ls_files()
        assert path in tracked, f"{path} must be tracked"


class TestAllSixRootSurfacesExist:
    def test_all_surfaces_exist(self):
        for surface in [
            ".claude",
            ".codex",
            ".cursor",
            ".gemini",
            ".opencode",
            ".vscode",
        ]:
            assert (REPO_ROOT / surface).is_dir(), f"{surface}/ must exist"


class TestAllSurfacesHaveDocumentation:
    def test_claude_has_documentation(self):
        paths = [".claude/README.md", ".claude/CLAUDE_BOOTLOADER.md"]
        assert any(
            (REPO_ROOT / p).exists() for p in paths
        ), ".claude must have README.md or CLAUDE_BOOTLOADER.md"

    def test_codex_has_documentation(self):
        paths = [".codex/README.md", ".codex/cdb_skills/README.md"]
        assert any(
            (REPO_ROOT / p).exists() for p in paths
        ), ".codex must have root README.md or cdb_skills/README.md"

    def test_cursor_has_documentation(self):
        paths = [
            ".cursor/README.md",
            ".cursor/skills/README.md",
            ".cursor/agents/README_CDB_CURSOR_SUBAGENTS.md",
        ]
        assert any(
            (REPO_ROOT / p).exists() for p in paths
        ), ".cursor must have README.md or equivalent documentation"

    def test_gemini_has_documentation(self):
        paths = [".gemini/README.md", "GEMINI.md"]
        assert any(
            (REPO_ROOT / p).exists() for p in paths
        ), ".gemini must have README.md or GEMINI.md"

    def test_opencode_has_documentation(self):
        paths = [".opencode/README.md", ".opencode/skills/README.md"]
        assert any(
            (REPO_ROOT / p).exists() for p in paths
        ), ".opencode must have root README.md or skills/README.md"

    def test_vscode_has_documentation(self):
        assert (REPO_ROOT / ".vscode/README.md").exists(), ".vscode must have README.md"


class TestOnboardingRoutes:
    def test_agents_md_routes_to_orchestrator(self):
        text = read_text("AGENTS.md")
        assert PRIMARY_ROUTE in text
        assert SHARED_ONBOARDING_TEXT in text

    def test_gemini_root_routes_to_orchestrator(self):
        text = read_text("GEMINI.md")
        assert PRIMARY_ROUTE in text

    def test_opencode_skills_onboarding_routes(self):
        text = read_text(".opencode/skills/onboarding/SKILL.md")
        assert PRIMARY_ROUTE in text

    def test_cursor_skills_onboarding_routes(self):
        text = read_text(".cursor/skills/onboarding/SKILL.md")
        assert PRIMARY_ROUTE in text

    def test_codex_skills_onboarding_routes(self):
        text = read_text(".codex/cdb_skills/onboarding/SKILL.md")
        assert PRIMARY_ROUTE in text

    def test_claude_skills_onboarding_routes(self):
        text = read_text(".claude/skills/onboarding/SKILL.md")
        assert PRIMARY_ROUTE in text


class TestSurfaceMatrixDoc:
    def test_surface_matrix_exists(self):
        path = "docs/onboarding/AGENT_ROOT_SURFACE_MATRIX.md"
        assert (REPO_ROOT / path).exists(), f"{path} must exist"

    def test_surface_matrix_lists_all_surfaces(self):
        text = read_text("docs/onboarding/AGENT_ROOT_SURFACE_MATRIX.md")
        for surface in [
            ".claude",
            ".codex",
            ".cursor",
            ".gemini",
            ".opencode",
            ".vscode",
        ]:
            assert surface in text, f"Matrix must mention {surface}"

    def test_surface_matrix_lists_onboarding_route(self):
        text = read_text("docs/onboarding/AGENT_ROOT_SURFACE_MATRIX.md")
        assert PRIMARY_ROUTE in text


class TestForbiddenPrivatePatterns:
    def test_no_tracked_surface_file_has_forbidden_patterns(self):
        tracked = git_ls_files()
        surfaces = [
            ".claude/",
            ".codex/",
            ".cursor/",
            ".gemini/",
            ".opencode/",
            ".vscode/",
        ]
        surface_files = [f for f in tracked if any(f.startswith(s) for s in surfaces)]
        forbidden = []
        for pattern in FORBIDDEN_PATTERNS:
            for f in surface_files:
                if pattern in f.lower():
                    forbidden.append(f)
        assert len(forbidden) == 0, (
            f"No tracked file in agent root surfaces should match forbidden patterns "
            f"{FORBIDDEN_PATTERNS}. Found: {forbidden}"
        )

    def test_gemini_issue_body_remains_untracked(self):
        tracked = git_ls_files()
        issue_files = [f for f in tracked if "github_issue_body" in f.lower()]
        assert (
            len(issue_files) == 0
        ), f"github_issue_body.txt must NOT be tracked, found: {issue_files}"


class TestSafetyBoundaries:
    def test_gemini_surface_preserves_lr_no_go(self):
        text = read_text(".gemini/README.md")
        assert "NO-GO" in text
        assert "trade-capable" in text
        assert "Live-Go" in text

    def test_gemini_onboarding_preserves_lr_no_go(self):
        text = read_text(".gemini/onboarding.md")
        assert "NO-GO" in text
        assert "trade-capable" in text

    def test_vscode_surface_preserves_lr_no_go(self):
        text = read_text(".vscode/README.md")
        assert "NO-GO" in text
        assert "trade-capable" in text
        assert "Live-Go" in text

    def test_claude_surface_preserves_lr_no_go(self):
        text = read_text(".claude/README.md")
        assert "NO-GO" in text
        assert "trade-capable" in text
        assert "Live-Go" in text

    def test_codex_surface_preserves_lr_no_go(self):
        text = read_text(".codex/README.md")
        assert "NO-GO" in text
        assert "trade-capable" in text
        assert "Live-Go" in text

    def test_cursor_surface_preserves_lr_no_go(self):
        text = read_text(".cursor/README.md")
        assert "NO-GO" in text
        assert "trade-capable" in text
        assert "Live-Go" in text

    def test_opencode_surface_preserves_lr_no_go(self):
        text = read_text(".opencode/README.md")
        assert "NO-GO" in text
        assert "trade-capable" in text
        assert "Live-Go" in text

    def test_surface_matrix_preserves_lr_no_go(self):
        text = read_text("docs/onboarding/AGENT_ROOT_SURFACE_MATRIX.md")
        assert "NO-GO" in text
        assert "trade-capable" in text
        assert "Live-Go" in text
