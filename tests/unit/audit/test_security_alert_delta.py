"""Tests for scripts.audit.security_alert_delta."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

repo_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo_root / "scripts"))
sys.path.insert(0, str(repo_root))

from audit.security_alert_delta import (  # noqa: E402
    SCHEMA_VERSION,
    AlertGroupKey,
    AlertKey,
    SecurityAlertDeltaError,
    build_delta_report,
    build_markdown_summary,
    compute_delta,
    generate_delta,
    main,
    normalize_readout_for_delta,
)


# ---------------------------------------------------------------------------
# Minimal readout fixture helpers
# ---------------------------------------------------------------------------


def _make_readout(
    *,
    reference_now_utc: str = "2026-05-01T00:00:00Z",
    status: str = "PASS",
    total_alerts: int = 0,
    alerts: list[dict] | None = None,
    code_scanning_surface_status: str = "readable",
    dependabot_surface_status: str = "readable",
    secret_scanning_surface_status: str = "redacted",
) -> dict:
    """Build a minimal github_security_quality_readout.v1 dict for testing."""
    return {
        "schema_version": "github_security_quality_readout.v1",
        "repo": "test/repo",
        "reference_now_utc": reference_now_utc,
        "status": status,
        "summary": {"total_alerts": total_alerts},
        "alerts": alerts or [],
        "surfaces": [
            {"source": "code_scanning", "status": code_scanning_surface_status},
            {"source": "dependabot", "status": dependabot_surface_status},
            {"source": "secret_scanning", "status": secret_scanning_surface_status},
        ],
    }


def _cs_alert(
    number: int,
    *,
    state: str = "open",
    severity: str = "medium",
    subject: str = "py/test-rule",
    branch: str = "main",
    affected_component: str = "app/test.py",
) -> dict:
    """Build a minimal code_scanning alert dict."""
    return {
        "source": "code_scanning",
        "number": number,
        "state": state,
        "severity": severity,
        "subject": subject,
        "rule_or_advisory": subject,
        "package": None,
        "affected_path": affected_component,
        "affected_component": affected_component,
        "branch": branch,
        "created_at": "2026-04-01T00:00:00Z",
        "updated_at": "2026-04-01T00:00:00Z",
        "age_bucket": "1-30d",
        "url": f"https://github.invalid/code/{number}",
        "tool": "CodeQL",
    }


def _dep_alert(
    number: int,
    *,
    state: str = "open",
    severity: str = "medium",
    subject: str = "lodash",
    branch: str = "main",
) -> dict:
    """Build a minimal dependabot alert dict."""
    return {
        "source": "dependabot",
        "number": number,
        "state": state,
        "severity": severity,
        "subject": subject,
        "rule_or_advisory": "GHSA-test-1234-5678",
        "package": subject,
        "affected_path": None,
        "affected_component": subject,
        "branch": branch,
        "created_at": "2026-04-01T00:00:00Z",
        "updated_at": "2026-04-01T00:00:00Z",
        "age_bucket": "1-30d",
        "url": f"https://github.invalid/dep/{number}",
        "tool": "Dependabot",
    }


# ---------------------------------------------------------------------------
# Tests: normalize_readout_for_delta
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalizeReadout:
    def test_excludes_secret_scanning_alerts(self):
        readout = _make_readout(
            alerts=[
                _cs_alert(1),
                {"source": "secret_scanning", "number": 99, "state": "open"},
            ]
        )
        safe = normalize_readout_for_delta(readout)
        assert len(safe.alerts) == 1
        assert safe.alerts[0].source == "code_scanning"

    def test_excludes_alerts_without_integer_number(self):
        readout = _make_readout(
            alerts=[
                {**_cs_alert(1), "number": "not-an-int"},
                _dep_alert(2),
            ]
        )
        safe = normalize_readout_for_delta(readout)
        assert len(safe.alerts) == 1
        assert safe.alerts[0].number == 2

    def test_returns_empty_alerts_for_missing_key(self):
        readout = {
            "schema_version": "github_security_quality_readout.v1",
            "reference_now_utc": "2026-05-01T00:00:00Z",
        }
        safe = normalize_readout_for_delta(readout)
        assert safe.alerts == ()

    def test_returns_empty_alerts_for_non_list_alerts(self):
        readout = _make_readout()
        readout["alerts"] = "not-a-list"
        safe = normalize_readout_for_delta(readout)
        assert safe.alerts == ()

    def test_secret_scanning_surface_status_extracted(self):
        readout = _make_readout(secret_scanning_surface_status="redacted")
        safe = normalize_readout_for_delta(readout)
        assert safe.secret_scanning_status == "redacted"

    def test_unknown_surface_status_falls_back(self):
        readout = _make_readout()
        readout["surfaces"] = []
        safe = normalize_readout_for_delta(readout)
        assert safe.secret_scanning_status == "unknown"

    def test_status_extracted_safely(self):
        readout = _make_readout(status="PASS")
        safe = normalize_readout_for_delta(readout)
        assert safe.status == "PASS"


# ---------------------------------------------------------------------------
# Tests: compute_delta — new alerts
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestComputeDeltaNewAlerts:
    def test_empty_prev_all_current_are_new(self):
        prev = _make_readout(alerts=[])
        current = _make_readout(alerts=[_cs_alert(1), _cs_alert(2)])
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert len(delta.new_alerts) == 2

    def test_same_alerts_no_new_alerts(self):
        alerts = [_cs_alert(1), _dep_alert(2)]
        prev = _make_readout(alerts=alerts)
        current = _make_readout(alerts=alerts)
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert delta.new_alerts == []

    def test_new_alert_by_number(self):
        prev = _make_readout(alerts=[_cs_alert(1)])
        current = _make_readout(alerts=[_cs_alert(1), _cs_alert(2)])
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert len(delta.new_alerts) == 1
        assert delta.new_alerts[0]["number"] == 2

    def test_new_alerts_sorted_by_source_then_number(self):
        prev = _make_readout(alerts=[])
        current = _make_readout(
            alerts=[_dep_alert(10), _cs_alert(5), _cs_alert(3)]
        )
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        numbers = [(a["source"], a["number"]) for a in delta.new_alerts]
        assert numbers == [("code_scanning", 3), ("code_scanning", 5), ("dependabot", 10)]

    def test_secret_scanning_alerts_not_counted_as_new(self):
        prev = _make_readout(alerts=[])
        current = _make_readout(
            alerts=[
                {"source": "secret_scanning", "number": 99, "state": "open"},
                _cs_alert(1),
            ]
        )
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert len(delta.new_alerts) == 1
        assert delta.new_alerts[0]["source"] == "code_scanning"


# ---------------------------------------------------------------------------
# Tests: compute_delta — resolved alerts
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestComputeDeltaResolvedAlerts:
    def test_no_resolved_when_all_still_open(self):
        alerts = [_cs_alert(1), _cs_alert(2)]
        prev = _make_readout(alerts=alerts)
        current = _make_readout(alerts=alerts)
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert delta.resolved_keys == []

    def test_resolved_when_open_alert_disappears_from_current(self):
        prev = _make_readout(alerts=[_cs_alert(1), _cs_alert(2)])
        # Alert 1 is now dismissed (state="dismissed"), alert 2 still open
        current = _make_readout(
            alerts=[_cs_alert(1, state="dismissed"), _cs_alert(2)]
        )
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert len(delta.resolved_keys) == 1
        assert delta.resolved_keys[0] == AlertKey(source="code_scanning", number=1)

    def test_alert_missing_from_current_counts_as_resolved(self):
        prev = _make_readout(alerts=[_cs_alert(1)])
        current = _make_readout(alerts=[])
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert any(k.number == 1 for k in delta.resolved_keys)


@pytest.mark.unit
class TestComputeDeltaUnavailableSurfaces:
    def test_current_unavailable_surface_not_counted_as_resolved(self):
        prev = _make_readout(
            status="PARTIAL",
            alerts=[_cs_alert(1)],
            code_scanning_surface_status="readable",
        )
        current = _make_readout(
            status="PARTIAL",
            alerts=[],
            code_scanning_surface_status="unavailable",
        )
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert delta.resolved_keys == []
        assert any(
            source["source"] == "code_scanning"
            for source in delta.comparison_skipped_sources
        )

    def test_previous_unavailable_surface_not_counted_as_new(self):
        prev = _make_readout(
            status="PARTIAL",
            alerts=[],
            dependabot_surface_status="unavailable",
        )
        current = _make_readout(
            alerts=[_dep_alert(7)],
            dependabot_surface_status="readable",
        )
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert delta.new_alerts == []
        assert any(
            source["source"] == "dependabot"
            for source in delta.comparison_skipped_sources
        )


# ---------------------------------------------------------------------------
# Tests: compute_delta — escalation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestComputeDeltaEscalation:
    def test_new_critical_open_alert_triggers_escalation(self):
        prev = _make_readout(alerts=[])
        current = _make_readout(
            alerts=[_cs_alert(1, severity="critical")]
        )
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert delta.escalation_needed is True
        assert len(delta.escalation_alerts) == 1

    def test_new_high_open_alert_triggers_escalation(self):
        prev = _make_readout(alerts=[])
        current = _make_readout(alerts=[_cs_alert(1, severity="high")])
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert delta.escalation_needed is True

    def test_codeql_error_severity_triggers_escalation(self):
        # CodeQL uses "error" as its highest severity — maps to escalation.
        prev = _make_readout(alerts=[])
        current = _make_readout(alerts=[_cs_alert(1, severity="error")])
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert delta.escalation_needed is True

    def test_new_medium_alert_does_not_escalate(self):
        prev = _make_readout(alerts=[])
        current = _make_readout(alerts=[_cs_alert(1, severity="medium")])
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert delta.escalation_needed is False
        assert delta.escalation_alerts == []

    def test_new_low_alert_does_not_escalate(self):
        prev = _make_readout(alerts=[])
        current = _make_readout(alerts=[_dep_alert(1, severity="low")])
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert delta.escalation_needed is False

    def test_dismissed_high_alert_does_not_escalate(self):
        # New alert (not in prev) but state=dismissed — no escalation.
        prev = _make_readout(alerts=[])
        current = _make_readout(
            alerts=[_cs_alert(1, severity="high", state="dismissed")]
        )
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert delta.escalation_needed is False

    def test_pre_existing_high_alert_does_not_escalate(self):
        alert = _cs_alert(1, severity="high")
        prev = _make_readout(alerts=[alert])
        current = _make_readout(alerts=[alert])
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert delta.escalation_needed is False

    def test_reopened_high_alert_triggers_escalation(self):
        prev = _make_readout(
            alerts=[_cs_alert(1, state="dismissed", severity="high")]
        )
        current = _make_readout(
            alerts=[_cs_alert(1, state="open", severity="high")]
        )
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert delta.escalation_needed is True
        assert len(delta.reopened_alerts) == 1
        assert delta.reopened_alerts[0]["number"] == 1


# ---------------------------------------------------------------------------
# Tests: compute_delta — new groups
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestComputeDeltaNewGroups:
    def test_new_group_detected_for_new_subject(self):
        prev = _make_readout(alerts=[_cs_alert(1, subject="py/rule-a")])
        current = _make_readout(
            alerts=[_cs_alert(1, subject="py/rule-a"), _cs_alert(2, subject="py/rule-b")]
        )
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert len(delta.new_groups) == 1
        assert delta.new_groups[0] == AlertGroupKey(
            source="code_scanning", subject="py/rule-b", branch="main"
        )

    def test_no_new_groups_when_same_subjects(self):
        alerts = [_cs_alert(1, subject="py/rule-a")]
        prev = _make_readout(alerts=alerts)
        current = _make_readout(alerts=alerts)
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert delta.new_groups == []

    def test_same_subject_different_branch_is_new_group(self):
        prev = _make_readout(
            alerts=[_cs_alert(1, subject="py/rule-a", branch="main")]
        )
        current = _make_readout(
            alerts=[
                _cs_alert(1, subject="py/rule-a", branch="main"),
                _cs_alert(2, subject="py/rule-a", branch="feature/x"),
            ]
        )
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert len(delta.new_groups) == 1
        assert delta.new_groups[0].branch == "feature/x"


# ---------------------------------------------------------------------------
# Tests: compute_delta — secret scanning
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestComputeDeltaSecretScanning:
    def test_no_change_in_secret_scanning_status(self):
        prev = _make_readout(secret_scanning_surface_status="redacted")
        current = _make_readout(secret_scanning_surface_status="redacted")
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert delta.secret_scanning_status_change is None

    def test_secret_scanning_status_change_detected(self):
        prev = _make_readout(secret_scanning_surface_status="ok")
        current = _make_readout(secret_scanning_surface_status="redacted")
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert delta.secret_scanning_status_change is not None
        assert "ok" in delta.secret_scanning_status_change
        assert "redacted" in delta.secret_scanning_status_change

    def test_secret_scanning_payload_never_in_delta(self):
        """Secret-scanning alert fields must never appear in delta output."""
        prev = _make_readout(alerts=[])
        current = _make_readout(
            alerts=[
                {
                    "source": "secret_scanning",
                    "number": 5,
                    "state": "open",
                    "secret_type": "github_pat",
                    "secret": "ghp_SENSITIVE",
                    "locations_url": "https://api.github.com/...",
                }
            ]
        )
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        # secret_scanning alerts are excluded from new_alerts entirely
        assert delta.new_alerts == []
        assert delta.escalation_needed is False

    def test_reference_timestamps_captured(self):
        prev = _make_readout(reference_now_utc="2026-05-01T00:00:00Z")
        current = _make_readout(reference_now_utc="2026-05-08T00:00:00Z")
        delta = compute_delta(
            prev_safe=normalize_readout_for_delta(prev),
            current_safe=normalize_readout_for_delta(current),
        )
        assert delta.prev_reference_now_utc == "2026-05-01T00:00:00Z"
        assert delta.current_reference_now_utc == "2026-05-08T00:00:00Z"


# ---------------------------------------------------------------------------
# Tests: _load_readout / SecurityAlertDeltaError
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadReadout:
    def test_raises_on_missing_file(self, tmp_path: Path):
        from audit.security_alert_delta import _load_readout

        with pytest.raises(SecurityAlertDeltaError, match="Cannot read"):
            _load_readout(tmp_path / "nonexistent.json")

    def test_raises_on_invalid_json(self, tmp_path: Path):
        from audit.security_alert_delta import _load_readout

        bad = tmp_path / "bad.json"
        bad.write_text("{ not json", encoding="utf-8")
        with pytest.raises(SecurityAlertDeltaError, match="Invalid JSON"):
            _load_readout(bad)

    def test_raises_on_wrong_schema_version(self, tmp_path: Path):
        from audit.security_alert_delta import _load_readout

        wrong = tmp_path / "wrong.json"
        wrong.write_text(
            json.dumps({"schema_version": "some_other_schema.v1"}), encoding="utf-8"
        )
        with pytest.raises(SecurityAlertDeltaError, match="schema_version"):
            _load_readout(wrong)

    def test_raises_on_non_dict_root(self, tmp_path: Path):
        from audit.security_alert_delta import _load_readout

        arr = tmp_path / "arr.json"
        arr.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        with pytest.raises(SecurityAlertDeltaError, match="JSON object"):
            _load_readout(arr)

    def test_accepts_valid_readout(self, tmp_path: Path):
        from audit.security_alert_delta import _load_readout

        valid = tmp_path / "valid.json"
        valid.write_text(
            json.dumps(_make_readout()), encoding="utf-8"
        )
        result = _load_readout(valid)
        assert result["schema_version"] == "github_security_quality_readout.v1"


# ---------------------------------------------------------------------------
# Tests: build_delta_report
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildDeltaReport:
    def _run(
        self,
        prev_alerts: list[dict],
        current_alerts: list[dict],
        *,
        prev_utc: str = "2026-05-01T00:00:00Z",
        current_utc: str = "2026-05-08T00:00:00Z",
    ) -> dict:
        prev = _make_readout(
            reference_now_utc=prev_utc, alerts=prev_alerts, total_alerts=len(prev_alerts)
        )
        current = _make_readout(
            reference_now_utc=current_utc,
            alerts=current_alerts,
            total_alerts=len(current_alerts),
        )
        prev_safe = normalize_readout_for_delta(prev)
        current_safe = normalize_readout_for_delta(current)
        delta = compute_delta(prev_safe=prev_safe, current_safe=current_safe)
        return build_delta_report(
            prev_path=Path("/prev.json"),
            current_path=Path("/current.json"),
            delta=delta,
            prev_safe=prev_safe,
            current_safe=current_safe,
        )

    def test_schema_version(self):
        report = self._run([], [])
        assert report["schema_version"] == SCHEMA_VERSION

    def test_escalation_needed_flag_false_when_no_critical_high(self):
        report = self._run([], [_cs_alert(1, severity="medium")])
        assert report["escalation_needed"] is False
        assert report["escalation_alert_count"] == 0

    def test_escalation_needed_flag_true_for_new_critical(self):
        report = self._run([], [_cs_alert(1, severity="critical")])
        assert report["escalation_needed"] is True
        assert report["escalation_alert_count"] == 1

    def test_new_alert_count_matches(self):
        report = self._run([], [_cs_alert(1), _dep_alert(2)])
        assert report["new_alert_count"] == 2

    def test_new_alerts_have_required_fields(self):
        report = self._run([], [_cs_alert(42, severity="high")])
        alert = report["new_alerts"][0]
        assert "source" in alert
        assert "number" in alert
        assert "state" in alert
        assert "severity" in alert
        assert "subject" in alert
        assert "branch" in alert
        assert "affected_component" in alert

    def test_no_secret_payload_in_report(self):
        report = self._run(
            [],
            [{"source": "secret_scanning", "number": 1, "secret": "SENSITIVE"}],
        )
        # secret_scanning alert must not appear in new_alerts
        for a in report["new_alerts"]:
            assert "secret" not in a
        assert report["new_alert_count"] == 0

    def test_reference_timestamps_in_report(self):
        report = self._run([], [], prev_utc="2026-05-01T00:00:00Z", current_utc="2026-05-08T00:00:00Z")
        assert report["prev_readout"]["reference_now_utc"] == "2026-05-01T00:00:00Z"
        assert report["current_readout"]["reference_now_utc"] == "2026-05-08T00:00:00Z"


# ---------------------------------------------------------------------------
# Tests: build_markdown_summary
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildMarkdownSummary:
    def _make_report(
        self,
        *,
        escalation_needed: bool = False,
        escalation_alerts: list[dict] | None = None,
        new_alert_count: int = 0,
        new_alerts: list[dict] | None = None,
        resolved_alert_count: int = 0,
        resolved_alerts: list[dict] | None = None,
        new_group_count: int = 0,
        new_groups: list[dict] | None = None,
        secret_scanning_status_change: str | None = None,
    ) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "prev_readout": {
                "path": "/prev.json",
                "reference_now_utc": "2026-05-01T00:00:00Z",
                "status": "PASS",
                "total_alerts": 100,
            },
            "current_readout": {
                "path": "/current.json",
                "reference_now_utc": "2026-05-08T00:00:00Z",
                "status": "PASS",
                "total_alerts": 100 + new_alert_count - resolved_alert_count,
            },
            "new_alert_count": new_alert_count,
            "new_alerts": new_alerts or [],
            "resolved_alert_count": resolved_alert_count,
            "resolved_alerts": resolved_alerts or [],
            "new_group_count": new_group_count,
            "new_groups": new_groups or [],
            "escalation_needed": escalation_needed,
            "escalation_alert_count": len(escalation_alerts or []),
            "escalation_alerts": escalation_alerts or [],
            "secret_scanning_status_change": secret_scanning_status_change,
        }

    def test_escalation_warning_present_when_needed(self):
        report = self._make_report(
            escalation_needed=True,
            escalation_alerts=[
                {"source": "code_scanning", "number": 1, "severity": "critical", "subject": "py/sql-injection", "branch": "main"}
            ],
        )
        md = build_markdown_summary(report)
        assert "ESCALATION" in md

    def test_no_escalation_message_when_not_needed(self):
        report = self._make_report(escalation_needed=False)
        md = build_markdown_summary(report)
        assert "ESCALATION" not in md
        assert "No new Critical/High" in md

    def test_new_groups_table_present_when_groups_exist(self):
        report = self._make_report(
            new_group_count=1,
            new_groups=[{"source": "code_scanning", "subject": "py/rule-a", "branch": "main"}],
        )
        md = build_markdown_summary(report)
        assert "New Alert Groups" in md
        assert "py/rule-a" in md

    def test_no_new_groups_table_when_none(self):
        report = self._make_report(new_group_count=0, new_groups=[])
        md = build_markdown_summary(report)
        assert "New Alert Groups" not in md

    def test_secret_scanning_status_change_mentioned(self):
        report = self._make_report(
            secret_scanning_status_change="prev=ok → current=redacted"
        )
        md = build_markdown_summary(report)
        assert "prev=ok" in md

    def test_secret_scanning_not_mentioned_when_no_change(self):
        report = self._make_report(secret_scanning_status_change=None)
        md = build_markdown_summary(report)
        # The line about secret scanning status change should not appear
        assert "Secret scanning surface change" not in md

    def test_contains_reference_timestamps(self):
        report = self._make_report()
        md = build_markdown_summary(report)
        assert "2026-05-01T00:00:00Z" in md
        assert "2026-05-08T00:00:00Z" in md


# ---------------------------------------------------------------------------
# Tests: generate_delta (integration, uses tmp_path)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGenerateDelta:
    def _write_readout(self, path: Path, readout: dict) -> Path:
        path.write_text(json.dumps(readout), encoding="utf-8")
        return path

    def test_writes_json_only_to_out_dir(self, tmp_path: Path):
        prev_path = self._write_readout(tmp_path / "prev.json", _make_readout(alerts=[]))
        current_path = self._write_readout(
            tmp_path / "current.json", _make_readout(alerts=[_cs_alert(1)])
        )
        out_dir = tmp_path / "output"
        report = generate_delta(
            prev_path=prev_path, current_path=current_path, out_dir=out_dir
        )

        assert (out_dir / "security_alert_delta.json").exists()
        assert not (out_dir / "security_alert_delta.md").exists()
        assert report["new_alert_count"] == 1

    def test_json_output_is_valid_schema_version(self, tmp_path: Path):
        prev_path = self._write_readout(tmp_path / "prev.json", _make_readout(alerts=[]))
        current_path = self._write_readout(
            tmp_path / "current.json", _make_readout(alerts=[])
        )
        out_dir = tmp_path / "output"
        generate_delta(prev_path=prev_path, current_path=current_path, out_dir=out_dir)

        loaded = json.loads((out_dir / "security_alert_delta.json").read_text())
        assert loaded["schema_version"] == SCHEMA_VERSION

    def test_json_output_preserves_safe_alert_identities(self, tmp_path: Path):
        prev_readout = _make_readout(
            status="PARTIAL",
            alerts=[
                _cs_alert(1, state="open", severity="medium"),
                _cs_alert(2, state="dismissed", severity="high"),
            ],
            dependabot_surface_status="unavailable",
        )
        current_readout = _make_readout(
            status="PASS",
            alerts=[
                _cs_alert(2, state="open", severity="high"),
                _cs_alert(3, state="open", severity="medium"),
                _dep_alert(4, severity="low"),
                {
                    "source": "secret_scanning",
                    "number": 8,
                    "state": "open",
                    "secret": "ghp_SENSITIVE",
                    "locations_url": "https://api.github.com/...",
                },
            ],
            dependabot_surface_status="readable",
            secret_scanning_surface_status="redacted",
        )
        prev_path = self._write_readout(tmp_path / "prev.json", prev_readout)
        current_path = self._write_readout(tmp_path / "current.json", current_readout)
        out_dir = tmp_path / "output"

        generate_delta(prev_path=prev_path, current_path=current_path, out_dir=out_dir)

        json_text = (out_dir / "security_alert_delta.json").read_text()
        loaded = json.loads(json_text)
        assert any(alert["number"] == 3 for alert in loaded["new_alerts"])
        assert any(alert["number"] == 1 for alert in loaded["resolved_alerts"])
        assert any(alert["number"] == 2 for alert in loaded["reopened_alerts"])
        assert any(
            source["source"] == "dependabot"
            for source in loaded["surface_status"]["comparison_skipped_sources"]
        )
        assert "ghp_SENSITIVE" not in json_text
        assert "locations_url" not in json_text

    def test_escalation_reflected_in_report(self, tmp_path: Path):
        prev_path = self._write_readout(tmp_path / "prev.json", _make_readout(alerts=[]))
        current_path = self._write_readout(
            tmp_path / "current.json",
            _make_readout(alerts=[_cs_alert(99, severity="critical")]),
        )
        report = generate_delta(
            prev_path=prev_path, current_path=current_path, out_dir=None
        )
        assert report["escalation_needed"] is True

    def test_raises_on_missing_prev(self, tmp_path: Path):
        current_path = self._write_readout(
            tmp_path / "current.json", _make_readout(alerts=[])
        )
        with pytest.raises(SecurityAlertDeltaError, match="Cannot read"):
            generate_delta(
                prev_path=tmp_path / "nonexistent.json", current_path=current_path
            )

    def test_no_out_dir_does_not_write_files(self, tmp_path: Path):
        prev_path = self._write_readout(tmp_path / "prev.json", _make_readout(alerts=[]))
        current_path = self._write_readout(
            tmp_path / "current.json", _make_readout(alerts=[])
        )
        report = generate_delta(prev_path=prev_path, current_path=current_path, out_dir=None)
        # No unexpected files written
        assert not (tmp_path / "security_alert_delta.json").exists()
        assert not (tmp_path / "security_alert_delta.md").exists()
        assert report["schema_version"] == SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Tests: main() CLI
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMain:
    def _write_readout(self, path: Path, readout: dict) -> Path:
        path.write_text(json.dumps(readout), encoding="utf-8")
        return path

    def test_returns_0_when_no_escalation(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
        prev_path = self._write_readout(tmp_path / "prev.json", _make_readout(alerts=[]))
        current_path = self._write_readout(
            tmp_path / "current.json", _make_readout(alerts=[_cs_alert(1, severity="low")])
        )
        exit_code = main([
            "--prev-readout", str(prev_path),
            "--current-readout", str(current_path),
        ])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert captured.out.strip() == "security alert delta json artifact generated"
        assert "Security Alert Delta" not in captured.out

    def test_returns_2_when_escalation_needed(self, tmp_path: Path):
        prev_path = self._write_readout(tmp_path / "prev.json", _make_readout(alerts=[]))
        current_path = self._write_readout(
            tmp_path / "current.json",
            _make_readout(alerts=[_cs_alert(1, severity="critical")]),
        )
        exit_code = main([
            "--prev-readout", str(prev_path),
            "--current-readout", str(current_path),
        ])
        assert exit_code == 2

    def test_returns_1_on_missing_file(self, tmp_path: Path):
        prev_path = self._write_readout(tmp_path / "prev.json", _make_readout(alerts=[]))
        exit_code = main([
            "--prev-readout", str(prev_path),
            "--current-readout", str(tmp_path / "missing.json"),
        ])
        assert exit_code == 1

    def test_writes_out_dir_when_provided(self, tmp_path: Path):
        prev_path = self._write_readout(tmp_path / "prev.json", _make_readout(alerts=[]))
        current_path = self._write_readout(
            tmp_path / "current.json", _make_readout(alerts=[])
        )
        out_dir = tmp_path / "out"
        main([
            "--prev-readout", str(prev_path),
            "--current-readout", str(current_path),
            "--out-dir", str(out_dir),
        ])
        assert (out_dir / "security_alert_delta.json").exists()
        assert not (out_dir / "security_alert_delta.md").exists()
