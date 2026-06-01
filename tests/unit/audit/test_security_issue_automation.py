"""Unit tests for security_issue_automation.py.

Injected helpers simulate GitHub calls so no network / gh auth needed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

# Use same import pattern as the existing audit tests.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from audit.security_issue_automation import (  # noqa: E402
    AUTOMATION_SEVERITY_BANDS,
    _FINGERPRINT_RE,
    _validate_fingerprint,
    _render_issue_body,
    main,
    run_automation,
)
from audit.security_alert_issue_candidates import build_fingerprint  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SCHEMA = "security_alert_delta.v1"


def _base_delta(
    *, new_groups: list | None = None, escalations: list | None = None
) -> dict:
    """Canonical-key delta shape (already normalized — mirrors what candidates tests use)."""
    return {
        "schema_version": _SCHEMA,
        "counts": {
            "new_alerts": 0,
            "reopened_alerts": 0,
            "new_groups": len(new_groups or []),
            "escalation_alerts": len(escalations or []),
        },
        "sources": {"current_reference_now_utc": "2026-05-15T06:15:00Z"},
        "comparison_skipped_sources": [],
        "new_groups": new_groups or [],
        "escalations": escalations or [],
    }


def _real_delta_shape(
    *, new_groups: list | None = None, escalation_alerts: list | None = None
) -> dict:
    """Flat-count / escalation_alerts delta shape — as emitted by security_alert_delta.py."""
    return {
        "schema_version": _SCHEMA,
        "new_alert_count": 0,
        "reopened_alert_count": 0,
        "new_group_count": len(new_groups or []),
        "escalation_alert_count": len(escalation_alerts or []),
        "comparison_skipped_sources": [],
        "new_groups": new_groups or [],
        "escalation_alerts": escalation_alerts or [],
        "current_readout": {"reference_now_utc": "2026-05-15T06:15:00Z"},
    }


def _write_delta(tmp_path: Path, delta: dict) -> Path:
    p = tmp_path / "security_alert_delta.json"
    p.write_text(json.dumps(delta), encoding="utf-8")
    return p


# Injected stub factories.


def _no_dedupe(**_kwargs: Any) -> bool:
    """Simulate: no existing issue found."""
    return False


def _always_dedupe(**_kwargs: Any) -> bool:
    """Simulate: issue already exists."""
    return True


def _create_ok(**_kwargs: Any) -> bool:
    return {
        "number": "1234",
        "url": "https://github.com/owner/repo/issues/1234",
        "title": "stub",
        "fingerprint": "abcd1234ef567890",
    }


def _create_fail(**_kwargs: Any) -> bool:
    return None


def _dedupe_error(**_kwargs: Any) -> bool:
    raise RuntimeError("graphql timeout")


# ---------------------------------------------------------------------------
# Fingerprint / validation tests
# ---------------------------------------------------------------------------


def test_fingerprint_re_accepts_valid() -> None:
    assert _FINGERPRINT_RE.match("abcd1234ef567890")
    assert _FINGERPRINT_RE.match("0000000000000000")


def test_fingerprint_re_rejects_invalid() -> None:
    assert not _FINGERPRINT_RE.match("ABCD1234EF56789")  # uppercase
    assert not _FINGERPRINT_RE.match("too-short")
    assert not _FINGERPRINT_RE.match("abcd1234ef567890a")  # 17 chars


def test_validate_fingerprint_ok() -> None:
    fp = "abcdef0123456789"
    assert _validate_fingerprint(fp) == fp


def test_validate_fingerprint_raises_on_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid fingerprint format"):
        _validate_fingerprint("NOTHEX!")


# ---------------------------------------------------------------------------
# Automation severity band tests
# ---------------------------------------------------------------------------


def test_automation_bands_include_high_only() -> None:
    assert "high" in AUTOMATION_SEVERITY_BANDS
    assert "medium" not in AUTOMATION_SEVERITY_BANDS
    assert "low" not in AUTOMATION_SEVERITY_BANDS


# ---------------------------------------------------------------------------
# run_automation — no candidates
# ---------------------------------------------------------------------------


def test_no_new_groups_produces_no_creates(tmp_path: Path) -> None:
    delta_path = _write_delta(tmp_path, _base_delta())
    summary = run_automation(
        delta_path=delta_path,
        repo="owner/repo",
        dry_run=True,
        _check_dedupe=_no_dedupe,
        _create_issue=_create_ok,
    )
    assert summary["created"] == 0
    assert summary["failed"] == 0


# ---------------------------------------------------------------------------
# run_automation — dry-run
# ---------------------------------------------------------------------------


def test_dry_run_does_not_call_create(tmp_path: Path) -> None:
    """Dry-run must not invoke _create_issue even when a candidate would qualify."""
    create_calls: list[dict] = []

    def _capture_create(**kwargs: Any) -> bool:
        create_calls.append(kwargs)
        return True

    delta = _base_delta(
        new_groups=[
            {"source": "code_scanning", "subject": "cve-2026-0001", "branch": "main"},
        ],
        escalations=[
            {
                "source": "code_scanning",
                "severity": "critical",
                "subject": "cve-2026-0001",
                "affected_component": "core/risk",
                "branch": "main",
            }
        ],
    )
    delta_path = _write_delta(tmp_path, delta)
    summary = run_automation(
        delta_path=delta_path,
        repo="owner/repo",
        dry_run=True,
        _check_dedupe=_no_dedupe,
        _create_issue=_capture_create,
    )
    assert create_calls == [], "dry-run must not call _create_issue"
    assert summary["created"] == 0
    assert summary["failed"] == 0


# ---------------------------------------------------------------------------
# run_automation — live mode
# ---------------------------------------------------------------------------


def test_live_mode_creates_for_critical_candidate(tmp_path: Path) -> None:
    delta = _base_delta(
        new_groups=[
            {"source": "code_scanning", "subject": "cve-2026-0002", "branch": "main"},
        ],
        escalations=[
            {
                "source": "code_scanning",
                "severity": "critical",
                "subject": "cve-2026-0002",
                "affected_component": "services/execution",
                "branch": "main",
            }
        ],
    )
    delta_path = _write_delta(tmp_path, delta)
    summary = run_automation(
        delta_path=delta_path,
        repo="owner/repo",
        dry_run=False,
        _check_dedupe=_no_dedupe,
        _create_issue=_create_ok,
    )
    assert summary["created"] == 1
    assert summary["failed"] == 0


def test_live_mode_creates_for_high_candidate(tmp_path: Path) -> None:
    delta = _base_delta(
        new_groups=[
            {"source": "dependabot", "subject": "urllib3", "branch": "main"},
        ],
        escalations=[
            {
                "source": "dependabot",
                "severity": "high",
                "subject": "urllib3",
                "affected_component": "requirements.txt",
                "branch": "main",
            }
        ],
    )
    delta_path = _write_delta(tmp_path, delta)
    summary = run_automation(
        delta_path=delta_path,
        repo="owner/repo",
        dry_run=False,
        _check_dedupe=_no_dedupe,
        _create_issue=_create_ok,
    )
    assert summary["created"] == 1
    assert summary["failed"] == 0


# ---------------------------------------------------------------------------
# run_automation — medium/low filtered out
# ---------------------------------------------------------------------------


def test_medium_severity_candidate_not_created(tmp_path: Path) -> None:
    delta = _base_delta(
        new_groups=[
            {"source": "code_scanning", "subject": "cve-2026-low", "branch": "main"},
        ],
        # No escalations → severity_band will be low/medium → filtered
    )
    delta_path = _write_delta(tmp_path, delta)
    create_calls: list[dict] = []

    def _capture(**kwargs: Any) -> bool:
        create_calls.append(kwargs)
        return True

    summary = run_automation(
        delta_path=delta_path,
        repo="owner/repo",
        dry_run=False,
        _check_dedupe=_no_dedupe,
        _create_issue=_capture,
    )
    assert create_calls == [], "medium/low should never trigger issue creation"
    assert summary["created"] == 0


# ---------------------------------------------------------------------------
# run_automation — dedupe match → skip
# ---------------------------------------------------------------------------


def test_existing_dedupe_marker_skips_create(tmp_path: Path) -> None:
    delta = _base_delta(
        new_groups=[
            {"source": "code_scanning", "subject": "cve-2026-dup", "branch": "main"},
        ],
        escalations=[
            {
                "source": "code_scanning",
                "severity": "critical",
                "subject": "cve-2026-dup",
                "affected_component": "core/safety",
                "branch": "main",
            }
        ],
    )
    delta_path = _write_delta(tmp_path, delta)
    create_calls: list[dict] = []

    def _capture(**kwargs: Any) -> bool:
        create_calls.append(kwargs)
        return True

    summary = run_automation(
        delta_path=delta_path,
        repo="owner/repo",
        dry_run=False,
        _check_dedupe=_always_dedupe,
        _create_issue=_capture,
    )
    assert create_calls == [], "dedupe match must suppress issue creation"
    assert summary["created"] == 0
    assert summary["deduped"] >= 1
    assert summary["failed"] == 0


# ---------------------------------------------------------------------------
# run_automation — dedupe error → fail-closed (exit 2)
# ---------------------------------------------------------------------------


def test_dedupe_error_is_fail_closed(tmp_path: Path) -> None:
    delta = _base_delta(
        new_groups=[
            {"source": "code_scanning", "subject": "cve-2026-err", "branch": "main"},
        ],
        escalations=[
            {
                "source": "code_scanning",
                "severity": "critical",
                "subject": "cve-2026-err",
                "affected_component": "core/contracts",
                "branch": "main",
            }
        ],
    )
    delta_path = _write_delta(tmp_path, delta)
    create_calls: list[dict] = []

    def _capture(**kwargs: Any) -> bool:
        create_calls.append(kwargs)
        return True

    summary = run_automation(
        delta_path=delta_path,
        repo="owner/repo",
        dry_run=False,
        _check_dedupe=_dedupe_error,
        _create_issue=_capture,
    )
    assert create_calls == [], "dedupe failure must not trigger issue creation"
    assert summary["created"] == 0
    assert summary["failed"] >= 1


# ---------------------------------------------------------------------------
# run_automation — issue create failure → exit 2
# ---------------------------------------------------------------------------


def test_failed_create_reports_exit_2(tmp_path: Path) -> None:
    delta = _base_delta(
        new_groups=[
            {"source": "code_scanning", "subject": "cve-2026-cfail", "branch": "main"},
        ],
        escalations=[
            {
                "source": "code_scanning",
                "severity": "critical",
                "subject": "cve-2026-cfail",
                "affected_component": "core/execution",
                "branch": "main",
            }
        ],
    )
    delta_path = _write_delta(tmp_path, delta)
    summary = run_automation(
        delta_path=delta_path,
        repo="owner/repo",
        dry_run=False,
        _check_dedupe=_no_dedupe,
        _create_issue=_create_fail,
    )
    assert summary["failed"] >= 1
    assert summary["created"] == 0


# ---------------------------------------------------------------------------
# run_automation — comparison_skipped source is excluded
# ---------------------------------------------------------------------------


def test_comparison_skipped_source_excluded(tmp_path: Path) -> None:
    """Groups from a comparison_skipped source must not generate candidates."""
    delta = {
        "schema_version": _SCHEMA,
        "counts": {
            "new_alerts": 0,
            "reopened_alerts": 0,
            "new_groups": 0,
            "escalation_alerts": 0,
        },
        "sources": {"current_reference_now_utc": "2026-05-15T06:15:00Z"},
        "comparison_skipped_sources": [{"source": "dependabot", "reason": "no token"}],
        "new_groups": [
            # This group's source is in comparison_skipped_sources — should be excluded.
            {"source": "dependabot", "subject": "openssl", "branch": "main"},
        ],
        "escalations": [
            {
                "source": "dependabot",
                "severity": "critical",
                "subject": "openssl",
                "affected_component": "requirements.txt",
                "branch": "main",
            }
        ],
    }
    delta_path = _write_delta(tmp_path, delta)
    create_calls: list[dict] = []

    def _capture(**kwargs: Any) -> bool:
        create_calls.append(kwargs)
        return True

    summary = run_automation(
        delta_path=delta_path,
        repo="owner/repo",
        dry_run=False,
        _check_dedupe=_no_dedupe,
        _create_issue=_capture,
    )
    assert create_calls == [], "comparison_skipped source must be excluded"
    assert summary["created"] == 0


# ---------------------------------------------------------------------------
# run_automation — secret_scanning excluded
# ---------------------------------------------------------------------------


def test_secret_scanning_source_excluded(tmp_path: Path) -> None:
    delta = _base_delta(
        new_groups=[
            {"source": "secret_scanning", "subject": "ghp_token", "branch": "main"},
        ],
        escalations=[
            {
                "source": "secret_scanning",
                "severity": "critical",
                "subject": "ghp_token",
                "affected_component": "repo",
                "branch": "main",
            }
        ],
    )
    delta_path = _write_delta(tmp_path, delta)
    create_calls: list[dict] = []

    def _capture(**kwargs: Any) -> bool:
        create_calls.append(kwargs)
        return True

    summary = run_automation(
        delta_path=delta_path,
        repo="owner/repo",
        dry_run=False,
        _check_dedupe=_no_dedupe,
        _create_issue=_capture,
    )
    assert create_calls == [], "secret_scanning must always be excluded"
    assert summary["created"] == 0


# ---------------------------------------------------------------------------
# run_automation — real delta JSON shape (normalization test)
# ---------------------------------------------------------------------------


def test_real_delta_json_shape_is_normalized(tmp_path: Path) -> None:
    """Verify that the flat-count / escalation_alerts shape from the delta module
    is correctly normalized before reaching the candidates layer."""
    delta = _real_delta_shape(
        new_groups=[
            {
                "source": "code_scanning",
                "subject": "cve-2026-norm",
                "branch": "main",
                "affected_component": "core/risk",
            }
        ],
        escalation_alerts=[
            {
                "source": "code_scanning",
                "severity": "critical",
                "subject": "cve-2026-norm",
                "affected_component": "core/risk",
                "branch": "main",
            }
        ],
    )
    delta_path = _write_delta(tmp_path, delta)
    summary = run_automation(
        delta_path=delta_path,
        repo="owner/repo",
        dry_run=True,
        _check_dedupe=_no_dedupe,
        _create_issue=_create_ok,
    )
    # With dry-run: created=0, skipped≥1 (the one escalation-severity candidate), failed=0
    assert summary["failed"] == 0
    assert summary["skipped"] >= 1


# ---------------------------------------------------------------------------
# run_automation — missing delta JSON
# ---------------------------------------------------------------------------


def test_missing_delta_json_returns_exit_1(tmp_path: Path) -> None:
    result = main(
        ["--delta-json", str(tmp_path / "does_not_exist.json"), "--repo", "owner/repo"]
    )
    assert result == 1


# ---------------------------------------------------------------------------
# CLI exit-code mapping
# ---------------------------------------------------------------------------


def test_cli_exit_0_when_no_candidates(tmp_path: Path) -> None:
    delta_path = _write_delta(tmp_path, _base_delta())
    result = main(["--delta-json", str(delta_path), "--repo", "owner/repo"])
    assert result == 0


def test_cli_requires_delta_json_and_repo(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--repo", "owner/repo"])
    assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# Issue body contains dedupe marker
# ---------------------------------------------------------------------------


def test_render_issue_body_contains_dedupe_marker() -> None:
    fp = build_fingerprint(
        source="code_scanning",
        severity_band="high",
        subject="cve-test",
        affected_component="core/utils",
        branch="main",
    )
    candidate = {
        "fingerprint": fp,
        "dedupe_marker": f"<!-- cdb-security-alert-group:{fp} -->",
        "suggested_title": "Security: cve-test",
        "suggested_labels": ["type:security"],
        "references": ["#2289"],
        "body_safe_fields": {
            "source": "code_scanning",
            "severity": "critical",
            "severity_band": "high",
            "subject": "cve-test",
            "affected_component": "core/utils",
            "branch": "main",
            "fingerprint": fp,
            "current_reference_now_utc": "2026-05-15T06:15:00Z",
            "generated_from_readout": "2026-05-15",
            "counts": {"new_alerts": 1},
            "next_action": "Triage required.",
            "references": ["#2289"],
        },
    }
    body = _render_issue_body(candidate)
    assert fp in body
    assert f"<!-- cdb-security-alert-group:{fp} -->" in body


# ---------------------------------------------------------------------------
# Fingerprint stability across invocations
# ---------------------------------------------------------------------------


def test_fingerprint_stability_across_invocations() -> None:
    kwargs = dict(
        source="dependabot",
        severity_band="high",
        subject="urllib3",
        affected_component="requirements.txt",
        branch="main",
    )
    fp1 = build_fingerprint(**kwargs)
    fp2 = build_fingerprint(**kwargs)
    assert fp1 == fp2
    assert _FINGERPRINT_RE.match(fp1), "fingerprint must match 16-char hex pattern"


def test_live_mode_caps_created_issues_to_10(tmp_path: Path) -> None:
    new_groups = []
    escalations = []
    for i in range(12):
        subject = f"cve-2026-cap-{i}"
        new_groups.append(
            {"source": "code_scanning", "subject": subject, "branch": "main"}
        )
        escalations.append(
            {
                "source": "code_scanning",
                "severity": "critical",
                "subject": subject,
                "affected_component": f"svc/{i}",
                "branch": "main",
            }
        )
    delta_path = _write_delta(
        tmp_path, _base_delta(new_groups=new_groups, escalations=escalations)
    )
    summary = run_automation(
        delta_path=delta_path,
        repo="owner/repo",
        dry_run=False,
        _check_dedupe=_no_dedupe,
        _create_issue=_create_ok,
    )
    assert summary["eligible_candidates"] == 12
    assert summary["created"] == 10
    assert summary["capped"] == 2
    assert summary["failed"] == 0


def test_deduped_top_10_do_not_block_later_new_candidates(tmp_path: Path) -> None:
    new_groups = []
    escalations = []
    for i in range(12):
        subject = f"cve-2026-dedupe-cap-{i}"
        new_groups.append(
            {"source": "code_scanning", "subject": subject, "branch": "main"}
        )
        escalations.append(
            {
                "source": "code_scanning",
                "severity": "critical",
                "subject": subject,
                "affected_component": f"svc/{i}",
                "branch": "main",
            }
        )

    delta_path = _write_delta(
        tmp_path, _base_delta(new_groups=new_groups, escalations=escalations)
    )

    def _dedupe_first_ten(*, fingerprint: str, repo: str) -> bool:
        del repo
        for i in range(10):
            if fingerprint == build_fingerprint(
                source="code_scanning",
                severity_band="high",
                subject=f"cve-2026-dedupe-cap-{i}",
                affected_component=f"svc/{i}",
                branch="main",
            ):
                return True
        return False

    summary = run_automation(
        delta_path=delta_path,
        repo="owner/repo",
        dry_run=False,
        _check_dedupe=_dedupe_first_ten,
        _create_issue=_create_ok,
    )
    assert summary["eligible_candidates"] == 12
    assert summary["created"] == 2
    assert summary["deduped"] == 10
    assert summary["capped"] == 0
    assert summary["failed"] == 0


def test_cap_counts_only_non_deduped_candidates(tmp_path: Path) -> None:
    new_groups = []
    escalations = []
    for i in range(14):
        subject = f"cve-2026-cap-only-new-{i}"
        new_groups.append(
            {"source": "code_scanning", "subject": subject, "branch": "main"}
        )
        escalations.append(
            {
                "source": "code_scanning",
                "severity": "critical",
                "subject": subject,
                "affected_component": f"svc/{i}",
                "branch": "main",
            }
        )

    delta_path = _write_delta(
        tmp_path, _base_delta(new_groups=new_groups, escalations=escalations)
    )
    summary = run_automation(
        delta_path=delta_path,
        repo="owner/repo",
        dry_run=False,
        _check_dedupe=_no_dedupe,
        _create_issue=_create_ok,
    )
    assert summary["eligible_candidates"] == 14
    assert summary["created"] == 10
    assert summary["capped"] == 4
    assert summary["deduped"] == 0
    assert summary["failed"] == 0


def test_priority_is_critical_then_high_then_error(tmp_path: Path) -> None:
    delta = _base_delta(
        new_groups=[
            {"source": "code_scanning", "subject": "s-critical", "branch": "main"},
            {"source": "code_scanning", "subject": "s-high", "branch": "main"},
            {"source": "code_scanning", "subject": "s-error", "branch": "main"},
        ],
        escalations=[
            {
                "source": "code_scanning",
                "severity": "high",
                "subject": "s-high",
                "affected_component": "a",
                "branch": "main",
            },
            {
                "source": "code_scanning",
                "severity": "error",
                "subject": "s-error",
                "affected_component": "b",
                "branch": "main",
            },
            {
                "source": "code_scanning",
                "severity": "critical",
                "subject": "s-critical",
                "affected_component": "c",
                "branch": "main",
            },
        ],
    )
    delta_path = _write_delta(tmp_path, delta)
    seen_titles: list[str] = []

    def _capture_create(*, candidate: dict[str, Any], repo: str) -> dict[str, Any]:
        del repo
        seen_titles.append(str(candidate.get("suggested_title", "")))
        return _create_ok()

    summary = run_automation(
        delta_path=delta_path,
        repo="owner/repo",
        dry_run=False,
        _check_dedupe=_no_dedupe,
        _create_issue=_capture_create,
    )
    assert summary["created"] == 3
    assert "s-critical" in seen_titles[0].lower()
    assert "s-high" in seen_titles[1].lower()
    assert "s-error" in seen_titles[2].lower()
