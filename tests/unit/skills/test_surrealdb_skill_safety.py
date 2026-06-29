from __future__ import annotations

from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[3]
TRACKED_SKILL_DIRS = [
    ".opencode/skills/surrealql",
    ".opencode/skills/surrealdb-vector",
    ".opencode/skills/surrealdb-python",
    ".cursor/skills/surrealql",
    ".cursor/skills/surrealdb-vector",
    ".cursor/skills/surrealdb-python",
    ".codex/cdb_skills/surrealql",
    ".codex/cdb_skills/surrealdb-vector",
    ".codex/cdb_skills/surrealdb-python",
    ".claude/skills/surrealql",
    ".claude/skills/surrealdb-vector",
    ".claude/skills/surrealdb-python",
]
CURSOR_RULES = [
    ".cursor/rules/surrealql.mdc",
    ".cursor/rules/surrealdb-vector.mdc",
    ".cursor/rules/surrealdb-python.mdc",
    ".cursor/rules/surrealdb-python-embedded.mdc",
]
DISALLOWED_SCRIPT_SUFFIXES = {".py", ".js", ".ps1", ".sh", ".bat"}
DISALLOWED_TEXT_MARKERS = [
    "npx ",
    "skills add",
    "git clone ",
    "curl -",
    "| bash",
    "npm install",
    "pip install",
]
DISALLOWED_SECRET_OR_LIVE_MARKERS = [
    "-p root",
    '"password":',
    "api key",
    "live capital",
]
BOUNDARY_TEXT = "CDB Governance gewinnt vor externer Doku."
SOURCE_TEXT = "Offizielle Quelle"
NO_GO_TEXT = "No Live-GO / Echtgeld-GO"


def git_ls_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def tracked_files_under(relative_dir: str) -> list[str]:
    prefix = f"{relative_dir}/"
    return [path for path in git_ls_files() if path.startswith(prefix)]


def test_skill_md_only_for_surrealdb_skills() -> None:
    for relative_dir in TRACKED_SKILL_DIRS:
        tracked_files = tracked_files_under(relative_dir)
        assert tracked_files, f"expected tracked files under {relative_dir}"
        for path in tracked_files:
            suffix = Path(path).suffix
            assert suffix not in DISALLOWED_SCRIPT_SUFFIXES, (
                f"unexpected executable file in skill dir: {path}"
            )
            assert suffix in {".md", ".mdc"}, f"unexpected file type in {path}"


def test_no_installers_or_autorun() -> None:
    for relative_dir in TRACKED_SKILL_DIRS:
        text = read_text(f"{relative_dir}/SKILL.md").lower()
        for marker in DISALLOWED_TEXT_MARKERS:
            assert marker not in text, f"disallowed execution hint {marker!r} in {relative_dir}"

    for relative_path in CURSOR_RULES:
        text = read_text(relative_path).lower()
        for marker in DISALLOWED_TEXT_MARKERS:
            assert marker not in text, f"disallowed execution hint {marker!r} in {relative_path}"


def test_no_secret_or_live_targets() -> None:
    for relative_dir in TRACKED_SKILL_DIRS:
        text = read_text(f"{relative_dir}/SKILL.md").lower()
        for marker in DISALLOWED_SECRET_OR_LIVE_MARKERS:
            assert marker not in text, f"disallowed secret/live marker {marker!r} in {relative_dir}"


def test_cdb_governance_boundary_present() -> None:
    for relative_dir in TRACKED_SKILL_DIRS:
        text = read_text(f"{relative_dir}/SKILL.md")
        assert BOUNDARY_TEXT in text
        assert NO_GO_TEXT in text


def test_official_source_recorded() -> None:
    for relative_dir in TRACKED_SKILL_DIRS:
        text = read_text(f"{relative_dir}/SKILL.md")
        assert SOURCE_TEXT in text
        assert "95628976" in text


def test_cursor_rules_are_present_and_script_free() -> None:
    tracked = set(git_ls_files())

    for relative_path in CURSOR_RULES:
        assert relative_path in tracked, f"missing rule file: {relative_path}"
        text = read_text(relative_path)
        assert BOUNDARY_TEXT in text
        assert NO_GO_TEXT in text
