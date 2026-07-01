"""Unit tests for the skill surface mirror drift guard (#3643)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools import validate_skill_surface_mirror as guard

pytestmark = pytest.mark.unit


CANON_HEADER = (
    "<!--\n"
    "Canonical Skill Source: docs/skills/{name}/SKILL.md\n"
    "Surface: docs (canonical)\n"
    "Sync Status: canonical\n"
    "Last Verified: 2026-07-01\n"
    "Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.\n"
    "-->\n"
)

ADAPTER_HEADER = (
    "<!--\n"
    "Canonical Skill Source: docs/skills/{name}/SKILL.md\n"
    "Surface: {surface}\n"
    "Sync Status: mirrored-from-canon\n"
    "Last Verified: 2026-07-01\n"
    "Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.\n"
    "-->\n"
)

BODY = "---\nname: {name}\n---\n\n# {name}\n\nSome skill body content.\n"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _adapter_path(root: Path, surface: str, name: str) -> Path:
    return root / guard.SURFACES[surface].format(name=name)


def _make_skill(
    root: Path,
    name: str,
    *,
    surfaces: tuple[str, ...] = ("opencode", "cursor", "codex", "claude"),
    body: str | None = None,
    adapter_bodies: dict[str, str] | None = None,
) -> None:
    """Create a canon skill and its adapter mirrors in a fake repo."""
    resolved_body = (body or BODY).format(name=name)
    _write(
        root / "docs" / "skills" / name / "SKILL.md",
        CANON_HEADER.format(name=name) + resolved_body,
    )
    adapter_bodies = adapter_bodies or {}
    for surface in surfaces:
        surface_body = adapter_bodies.get(surface, resolved_body)
        _write(
            _adapter_path(root, surface, name),
            ADAPTER_HEADER.format(name=name, surface=surface) + surface_body,
        )


# --- header / body normalization ---


def test_strip_header_removes_leading_comment() -> None:
    text = CANON_HEADER.format(name="x") + "body"
    assert guard.strip_header(text) == "body"


def test_strip_header_no_header_is_noop() -> None:
    assert guard.strip_header("no header here") == "no header here"


def test_normalize_body_ignores_header_and_line_endings() -> None:
    canon = CANON_HEADER.format(name="x") + "line one\nline two\n"
    adapter = ADAPTER_HEADER.format(name="x", surface="cursor") + "line one\r\nline two\r\n"
    assert guard.normalize_body(canon) == guard.normalize_body(adapter)


# --- PASS ---


def test_pass_identical_body_different_headers(tmp_path: Path) -> None:
    _make_skill(tmp_path, "cdb-alpha")
    report = guard.run(tmp_path)
    assert report["status"] == "PASS"
    assert report["canon_count"] == 1
    assert report["adapter_count"] == 4
    assert report["mismatches"] == []
    assert report["missing"] == []


# --- DRIFT: modified adapter body ---


def test_drift_found_on_modified_adapter_body(tmp_path: Path) -> None:
    _make_skill(
        tmp_path,
        "cdb-beta",
        adapter_bodies={"cursor": "---\nname: cdb-beta\n---\n\n# tampered\n"},
    )
    report = guard.run(tmp_path)
    assert report["status"] == "DRIFT_FOUND"
    assert len(report["mismatches"]) == 1
    assert report["mismatches"][0]["surface"] == "cursor"
    assert report["mismatches"][0]["skill"] == "cdb-beta"


# --- DRIFT: missing expected adapter ---


def test_drift_found_on_missing_expected_adapter(tmp_path: Path) -> None:
    _make_skill(tmp_path, "cdb-gamma")
    _adapter_path(tmp_path, "claude", "cdb-gamma").unlink()
    report = guard.run(tmp_path)
    assert report["status"] == "DRIFT_FOUND"
    assert len(report["missing"]) == 1
    assert report["missing"][0]["surface"] == "claude"


# --- BLOCKED: missing canon tree ---


def test_blocked_when_canon_dir_missing(tmp_path: Path) -> None:
    with pytest.raises(guard.DriftCheckError):
        guard.run(tmp_path)


def test_blocked_when_no_canon_skills(tmp_path: Path) -> None:
    (tmp_path / "docs" / "skills").mkdir(parents=True)
    with pytest.raises(guard.DriftCheckError):
        guard.run(tmp_path)


def test_blocked_on_unknown_skill_filter(tmp_path: Path) -> None:
    _make_skill(tmp_path, "cdb-alpha")
    with pytest.raises(guard.DriftCheckError):
        guard.run(tmp_path, skill_filter="does-not-exist")


# --- documented exception: cdb-onboarding codex-only ---


def test_cdb_onboarding_codex_only_is_not_drift(tmp_path: Path) -> None:
    # Only the codex adapter exists; opencode/cursor/claude are excluded.
    _make_skill(tmp_path, "cdb-onboarding", surfaces=("codex",))
    report = guard.run(tmp_path, skill_filter="cdb-onboarding")
    assert report["status"] == "PASS"
    assert report["adapter_count"] == 1
    excluded_surfaces = {e["surface"] for e in report["excluded"]}
    assert excluded_surfaces == {"opencode", "cursor", "claude"}


# --- gh-fix-ci extras must not affect comparison ---


def test_gh_fix_ci_canon_extras_do_not_cause_drift(tmp_path: Path) -> None:
    _make_skill(tmp_path, "gh-fix-ci")
    # Canon-only extra artifacts alongside SKILL.md.
    _write(tmp_path / "docs" / "skills" / "gh-fix-ci" / "META.yaml", "meta: true\n")
    _write(tmp_path / "docs" / "skills" / "gh-fix-ci" / "evals.json", "{}\n")
    _write(
        tmp_path / "docs" / "skills" / "gh-fix-ci" / "scripts" / "run.sh",
        "echo hi\n",
    )
    report = guard.run(tmp_path, skill_filter="gh-fix-ci")
    assert report["status"] == "PASS"
    assert report["mismatches"] == []


# --- JSON / CLI contract ---


def test_report_has_required_json_fields(tmp_path: Path) -> None:
    _make_skill(tmp_path, "cdb-alpha")
    report = guard.run(tmp_path)
    for field in (
        "status",
        "canon_count",
        "adapter_count",
        "mismatches",
        "missing",
        "excluded",
        "limitations",
    ):
        assert field in report


def test_main_exit_code_pass(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _make_skill(tmp_path, "cdb-alpha")
    code = guard.main(["--repo-root", str(tmp_path), "--json"])
    assert code == 0
    out = capsys.readouterr().out
    assert '"status": "PASS"' in out


def test_main_exit_code_drift(tmp_path: Path) -> None:
    _make_skill(
        tmp_path,
        "cdb-beta",
        adapter_bodies={"codex": "---\nname: cdb-beta\n---\n\n# tampered\n"},
    )
    code = guard.main(["--repo-root", str(tmp_path)])
    assert code == 1


def test_main_exit_code_blocked(tmp_path: Path) -> None:
    code = guard.main(["--repo-root", str(tmp_path)])
    assert code == 2


def test_main_blocked_json_emits_status(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = guard.main(["--repo-root", str(tmp_path), "--json"])
    assert code == 2
    out = capsys.readouterr().out
    assert '"status": "BLOCKED"' in out


# --- real repo drift gate (runs in CI, no workflow change needed) ---


def test_real_repo_skill_surfaces_are_in_sync() -> None:
    """CI gate: real canon skills must match their adapters (Issue #3643).

    Fails if a canon `docs/skills/<name>/SKILL.md` was changed without
    re-mirroring the `.opencode`/`.cursor`/`.codex`/`.claude` adapters.
    """
    report = guard.run(guard.REPO_ROOT_DEFAULT)
    assert report["status"] == "PASS", (
        f"skill surface drift detected: "
        f"mismatches={report['mismatches']} missing={report['missing']}"
    )
    assert report["canon_count"] >= 1
