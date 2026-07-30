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
    adapter = (
        ADAPTER_HEADER.format(name="x", surface="cursor") + "line one\r\nline two\r\n"
    )
    assert guard.normalize_body(canon) == guard.normalize_body(adapter)


def test_header_issue_detects_missing_and_valid_headers() -> None:
    valid = ADAPTER_HEADER.format(name="cdb-alpha", surface="cursor") + "body"
    assert guard.header_issue("cdb-alpha", valid) is None
    assert guard.header_issue("cdb-alpha", "no header body") is not None
    canon_hdr = CANON_HEADER.format(name="cdb-alpha") + "body"
    # canon header lacks the mirrored-from-canon marker
    assert guard.header_issue("cdb-alpha", canon_hdr) is not None


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


def test_drift_found_on_missing_adapter_header(tmp_path: Path) -> None:
    _make_skill(tmp_path, "cdb-delta")
    # Overwrite one adapter with the correct body but NO surface header.
    adapter = _adapter_path(tmp_path, "opencode", "cdb-delta")
    adapter.write_text(BODY.format(name="cdb-delta"), encoding="utf-8")
    report = guard.run(tmp_path)
    assert report["status"] == "DRIFT_FOUND"
    header_mismatches = [m for m in report["mismatches"] if m.get("kind") == "header"]
    assert len(header_mismatches) == 1
    assert header_mismatches[0]["surface"] == "opencode"


def test_drift_found_on_wrong_sync_status_header(tmp_path: Path) -> None:
    _make_skill(tmp_path, "cdb-epsilon")
    adapter = _adapter_path(tmp_path, "cursor", "cdb-epsilon")
    wrong_header = ADAPTER_HEADER.format(name="cdb-epsilon", surface="cursor").replace(
        "mirrored-from-canon", "canonical"
    )
    adapter.write_text(wrong_header + BODY.format(name="cdb-epsilon"), encoding="utf-8")
    report = guard.run(tmp_path)
    assert report["status"] == "DRIFT_FOUND"
    assert any(m.get("kind") == "header" for m in report["mismatches"])


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


def test_main_exit_code_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
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
    """CI gate: real canon skills must match their adapters (Issues #3643/#4122).

    Fails if a canon `docs/skills/<name>/SKILL.md` was changed without
    re-mirroring the `.opencode`/`.cursor`/`.codex`/`.claude` adapters,
    or if skill-local linked assets / anchors are broken.
    """
    report = guard.run(guard.REPO_ROOT_DEFAULT)
    assert report["status"] == "PASS", (
        f"skill surface drift detected: "
        f"mismatches={report['mismatches']} missing={report['missing']}"
    )
    assert report["canon_count"] >= 1


# --- Issue #4122: local links, assets, anchors ---


def _body_with_links(name: str, extra: str) -> str:
    return f"---\nname: {name}\n---\n\n# {name}\n\n{extra}\n"


def test_pass_valid_relative_file_and_external_url(tmp_path: Path) -> None:
    name = "cdb-link-ok"
    extra = (
        "See [ref](references/note.md) and [ext](https://example.com/docs).\n"
        "Also [mail](mailto:ops@example.com).\n"
    )
    _make_skill(tmp_path, name, body=_body_with_links(name, extra))
    note = "# Note\n\n## Detail Section\n\nbody\n"
    for surface in ("canon", "opencode", "cursor", "codex", "claude"):
        skill_dir = (
            tmp_path / "docs" / "skills" / name
            if surface == "canon"
            else _adapter_path(tmp_path, surface, name).parent
        )
        _write(skill_dir / "references" / "note.md", note)
    report = guard.run(tmp_path, skill_filter=name)
    assert report["status"] == "PASS", report["mismatches"]


def test_pass_valid_subdirectory_link(tmp_path: Path) -> None:
    name = "cdb-dir-ok"
    extra = "Browse [refs](references/).\n"
    _make_skill(tmp_path, name, body=_body_with_links(name, extra))
    for surface in ("canon", "opencode", "cursor", "codex", "claude"):
        skill_dir = (
            tmp_path / "docs" / "skills" / name
            if surface == "canon"
            else _adapter_path(tmp_path, surface, name).parent
        )
        (skill_dir / "references").mkdir(parents=True, exist_ok=True)
    report = guard.run(tmp_path, skill_filter=name)
    assert report["status"] == "PASS", report["mismatches"]


def test_pass_valid_markdown_anchor(tmp_path: Path) -> None:
    name = "cdb-anchor-ok"
    extra = "Jump to [detail](references/note.md#detail-section).\n"
    _make_skill(tmp_path, name, body=_body_with_links(name, extra))
    note = "# Note\n\n## Detail Section\n\nbody\n"
    for surface in ("canon", "opencode", "cursor", "codex", "claude"):
        skill_dir = (
            tmp_path / "docs" / "skills" / name
            if surface == "canon"
            else _adapter_path(tmp_path, surface, name).parent
        )
        _write(skill_dir / "references" / "note.md", note)
    report = guard.run(tmp_path, skill_filter=name)
    assert report["status"] == "PASS", report["mismatches"]


def test_drift_missing_local_file(tmp_path: Path) -> None:
    name = "cdb-missing-file"
    extra = "See [gone](references/missing.md).\n"
    _make_skill(tmp_path, name, body=_body_with_links(name, extra))
    report = guard.run(tmp_path, skill_filter=name)
    assert report["status"] == "DRIFT_FOUND"
    kinds = {m["kind"] for m in report["mismatches"]}
    assert "MISSING_LOCAL_TARGET" in kinds or "MISSING_MIRRORED_ASSET" in kinds


def test_drift_missing_local_directory(tmp_path: Path) -> None:
    name = "cdb-missing-dir"
    extra = "Browse [refs](references/).\n"
    _make_skill(tmp_path, name, body=_body_with_links(name, extra))
    report = guard.run(tmp_path, skill_filter=name)
    assert report["status"] == "DRIFT_FOUND"
    assert any(m["kind"] == "MISSING_LOCAL_TARGET" for m in report["mismatches"])


def test_drift_missing_anchor(tmp_path: Path) -> None:
    name = "cdb-missing-anchor"
    extra = "Jump to [x](references/note.md#does-not-exist).\n"
    _make_skill(tmp_path, name, body=_body_with_links(name, extra))
    note = "# Note\n\n## Other Heading\n\nbody\n"
    for surface in ("canon", "opencode", "cursor", "codex", "claude"):
        skill_dir = (
            tmp_path / "docs" / "skills" / name
            if surface == "canon"
            else _adapter_path(tmp_path, surface, name).parent
        )
        _write(skill_dir / "references" / "note.md", note)
    report = guard.run(tmp_path, skill_filter=name)
    assert report["status"] == "DRIFT_FOUND"
    assert any(m["kind"] == "MISSING_ANCHOR" for m in report["mismatches"])


def test_drift_invalid_asset_class_canon_only_relative_link(tmp_path: Path) -> None:
    name = "gh-fix-ci"
    extra = "See [meta](./META.yaml).\n"
    _make_skill(tmp_path, name, body=_body_with_links(name, extra))
    _write(tmp_path / "docs" / "skills" / name / "META.yaml", "meta: true\n")
    report = guard.run(tmp_path, skill_filter=name)
    assert report["status"] == "DRIFT_FOUND"
    assert any(m["kind"] == "INVALID_ASSET_CLASS" for m in report["mismatches"])


def test_drift_missing_mirrored_asset_on_adapter(tmp_path: Path) -> None:
    name = "cdb-asset-gap"
    extra = "See [ref](references/note.md).\n"
    _make_skill(tmp_path, name, body=_body_with_links(name, extra))
    note = "# Note\n\nbody\n"
    # Canon + three adapters have the asset; claude does not.
    for surface in ("canon", "opencode", "cursor", "codex"):
        skill_dir = (
            tmp_path / "docs" / "skills" / name
            if surface == "canon"
            else _adapter_path(tmp_path, surface, name).parent
        )
        _write(skill_dir / "references" / "note.md", note)
    report = guard.run(tmp_path, skill_filter=name)
    assert report["status"] == "DRIFT_FOUND"
    assert any(
        m["kind"] in {"MISSING_MIRRORED_ASSET", "MISSING_LOCAL_TARGET"}
        and m.get("surface") == "claude"
        for m in report["mismatches"]
    )


def test_drift_mirrored_asset_content_drift(tmp_path: Path) -> None:
    name = "cdb-asset-drift"
    extra = "See [ref](references/note.md).\n"
    _make_skill(tmp_path, name, body=_body_with_links(name, extra))
    for surface in ("canon", "opencode", "cursor", "codex", "claude"):
        skill_dir = (
            tmp_path / "docs" / "skills" / name
            if surface == "canon"
            else _adapter_path(tmp_path, surface, name).parent
        )
        content = "# Note\n\ncanon\n" if surface == "canon" else "# Note\n\ndrift\n"
        _write(skill_dir / "references" / "note.md", content)
    report = guard.run(tmp_path, skill_filter=name)
    assert report["status"] == "DRIFT_FOUND"
    assert any(m["kind"] == "ASSET_CONTENT_DRIFT" for m in report["mismatches"])


def test_drift_path_escapes_repo_root(tmp_path: Path) -> None:
    name = "cdb-escape"
    extra = "See [outside](../../../../../../etc/passwd).\n"
    _make_skill(tmp_path, name, body=_body_with_links(name, extra))
    report = guard.run(tmp_path, skill_filter=name)
    assert report["status"] == "DRIFT_FOUND"
    assert any(m["kind"] == "PATH_ESCAPES_REPO_ROOT" for m in report["mismatches"])


def test_gh_fix_ci_canon_only_extras_still_pass_without_mirror(tmp_path: Path) -> None:
    """META/evals/scripts remain canon-only and must not force adapter copies."""
    _make_skill(tmp_path, "gh-fix-ci")
    _write(tmp_path / "docs" / "skills" / "gh-fix-ci" / "META.yaml", "meta: true\n")
    _write(tmp_path / "docs" / "skills" / "gh-fix-ci" / "evals.json", "{}\n")
    _write(
        tmp_path / "docs" / "skills" / "gh-fix-ci" / "scripts" / "run.sh",
        "echo hi\n",
    )
    report = guard.run(tmp_path, skill_filter="gh-fix-ci")
    assert report["status"] == "PASS", report["mismatches"]


def test_gh_fix_ci_explicit_canon_path_to_discovery_passes(tmp_path: Path) -> None:
    """Canon-path link to DISCOVERY_REPORT is allowed; no adapter mirror required."""
    name = "gh-fix-ci"
    extra = (
        "Based on [DISCOVERY_REPORT.md]"
        "(../../../docs/skills/gh-fix-ci/DISCOVERY_REPORT.md).\n"
    )
    _make_skill(tmp_path, name, body=_body_with_links(name, extra))
    _write(
        tmp_path / "docs" / "skills" / "gh-fix-ci" / "DISCOVERY_REPORT.md",
        "# Discovery\n",
    )
    report = guard.run(tmp_path, skill_filter=name)
    assert report["status"] == "PASS", report["mismatches"]
    assert not any(m["kind"] == "MISSING_MIRRORED_ASSET" for m in report["mismatches"])


def test_github_slug_and_duplicate_headings() -> None:
    md = "# Hello World\n\n## Hello World\n\n## Detail Section\n"
    anchors = guard.collect_heading_anchors(md)
    assert "hello-world" in anchors
    assert "hello-world-1" in anchors
    assert "detail-section" in anchors


def test_invalid_exception_unknown_surface(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        guard.EXCLUDED_ADAPTERS,
        "cdb-onboarding",
        {"not-a-surface": "bad"},
    )
    mismatches = guard.validate_exclusion_tables()
    assert any(m["kind"] == "INVALID_EXCEPTION" for m in mismatches)
