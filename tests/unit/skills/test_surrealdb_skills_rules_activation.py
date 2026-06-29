from __future__ import annotations

import json
from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[3]

SKILL_SURFACES = [
    ".opencode/skills",
    ".cursor/skills",
    ".codex/cdb_skills",
    ".claude/skills",
]
REQUIRED_SKILLS = ["surrealql", "surrealdb-vector", "surrealdb-python"]
GEMINI_SKILLS = [
    ".gemini/skills/surrealql/SKILL.md",
    ".gemini/skills/surrealdb-vector/SKILL.md",
    ".gemini/skills/surrealdb-python/SKILL.md",
]
SURFACE_MATRIX_PATH = REPO_ROOT / "artifacts/skills/surrealdb_skills_surface_matrix.json"
SOURCE_MANIFEST_PATH = (
    REPO_ROOT / "artifacts/skills/surrealdb_skills_source_manifest.json"
)
ALLOWED_SURFACE_STATUS = {"ACTIVE", "MISSING", "NOT_APPLICABLE", "GAP"}


def git_ls_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    return set(result.stdout.strip().splitlines())


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def test_surrealdb_required_skills_exist_on_valid_surfaces() -> None:
    tracked = git_ls_files()

    for surface in SKILL_SURFACES:
        for skill in REQUIRED_SKILLS:
            path = f"{surface}/{skill}/SKILL.md"
            assert path in tracked, f"missing tracked skill: {path}"


def test_no_unapproved_surface_created() -> None:
    tracked = git_ls_files()

    for path in GEMINI_SKILLS:
        assert path not in tracked, f"gemini skill surface must stay inactive: {path}"


def test_surface_parity_matrix_generated() -> None:
    assert SURFACE_MATRIX_PATH.exists(), "surface matrix artifact must exist"

    matrix = load_json(SURFACE_MATRIX_PATH)
    assert isinstance(matrix, list)

    rows_by_surface = {row["surface"]: row for row in matrix}
    assert set(rows_by_surface) == {
        "OpenCode",
        "Cursor",
        "Codex",
        "Claude",
        "Gemini",
    }

    for row in matrix:
        assert set(row) == {
            "surface",
            "path",
            "surrealql_status",
            "surrealdb_vector_status",
            "surrealdb_python_status",
            "rules_status",
            "notes",
        }
        assert row["surrealql_status"] in ALLOWED_SURFACE_STATUS
        assert row["surrealdb_vector_status"] in ALLOWED_SURFACE_STATUS
        assert row["surrealdb_python_status"] in ALLOWED_SURFACE_STATUS
        assert row["rules_status"] in ALLOWED_SURFACE_STATUS

    assert rows_by_surface["OpenCode"]["surrealql_status"] == "ACTIVE"
    assert rows_by_surface["Cursor"]["surrealdb_vector_status"] == "ACTIVE"
    assert rows_by_surface["Codex"]["surrealdb_python_status"] == "ACTIVE"
    assert rows_by_surface["Claude"]["surrealql_status"] == "ACTIVE"
    assert rows_by_surface["Cursor"]["rules_status"] == "ACTIVE"
    assert rows_by_surface["Gemini"]["surrealql_status"] == "NOT_APPLICABLE"


def test_rules_status_documented() -> None:
    matrix = load_json(SURFACE_MATRIX_PATH)

    rows_by_surface = {row["surface"]: row for row in matrix}

    assert rows_by_surface["OpenCode"]["rules_status"] == "GAP"
    assert rows_by_surface["Codex"]["rules_status"] == "GAP"
    assert rows_by_surface["Claude"]["rules_status"] == "GAP"
    assert rows_by_surface["Gemini"]["rules_status"] == "NOT_APPLICABLE"


def test_official_source_manifest_generated() -> None:
    assert SOURCE_MANIFEST_PATH.exists(), "source manifest artifact must exist"

    manifest = load_json(SOURCE_MANIFEST_PATH)
    assert isinstance(manifest, list)
    assert manifest, "source manifest must not be empty"

    required_keys = {
        "skill",
        "surface",
        "local_path",
        "official_source",
        "source_commit_or_version",
        "safety_status",
        "files_included",
        "files_excluded",
        "gap_reason",
    }

    for row in manifest:
        assert set(row) == required_keys
        assert row["skill"]
        assert row["surface"]
        assert row["local_path"]
        assert row["official_source"]
        assert row["source_commit_or_version"]
        assert isinstance(row["files_included"], list)
        assert isinstance(row["files_excluded"], list)


def test_local_candidate_matches_or_is_explained() -> None:
    manifest = load_json(SOURCE_MANIFEST_PATH)

    candidate_rows = [
        row
        for row in manifest
        if row["surface"] in {"OpenCode", "Cursor"}
        and row["skill"] in set(REQUIRED_SKILLS)
    ]
    assert len(candidate_rows) == 6

    for row in candidate_rows:
        assert row["safety_status"] in {"verified", "curated"}
        assert row["gap_reason"] == ""
