from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / ".github" / "scripts" / "backlog_curation.py"

_SPEC = importlib.util.spec_from_file_location("backlog_curation", SCRIPT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
backlog_curation = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = backlog_curation
_SPEC.loader.exec_module(backlog_curation)


def _payload(
    *,
    event_label: str,
    labels: list[str],
    title: str = "Sample issue",
    body: str = "",
    milestone: str | None = None,
    number: int | str = 1794,
) -> dict[str, object]:
    issue_labels = [{"name": label} for label in labels]
    issue: dict[str, object] = {
        "number": number,
        "title": title,
        "body": body,
        "html_url": f"https://github.com/jannekbuengener/Claire_de_Binare/issues/{number}",
        "labels": issue_labels,
        "milestone": None if milestone is None else {"title": milestone},
    }
    return {"action": "labeled", "label": {"name": event_label}, "issue": issue}


def test_task_issue_is_qualified_with_partial_artifact() -> None:
    payload = _payload(event_label="task", labels=["triage:offen", "task"])

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is not None
    assert artifact["curation_status"]["state"] == "partial"
    assert artifact["issue"]["labels"] == ["triage:offen", "task"]


def test_typed_and_scoped_issue_is_qualified() -> None:
    payload = _payload(
        event_label="scope:ci",
        labels=["type:bug", "scope:ci"],
        title="CI routing drift in workflow register",
        body="Check `.github/README.md` against `docs/runbooks/GITHUB_WORKFLOW_REGISTER.md`.",
    )

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is not None
    assert artifact["trigger"]["matched_rules"] == ["type:bug", "scope:ci"]
    assert artifact["curation_status"]["state"] == "ready"


def test_relevant_event_label_without_full_qualification_produces_no_artifact() -> None:
    payload = _payload(event_label="type:bug", labels=["type:bug"])

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is None


def test_manual_override_context_curate_qualifies_issue() -> None:
    payload = _payload(
        event_label="context:curate",
        labels=["context:curate"],
        body="Please inspect `docs/runbooks/CONTROL_REGISTER.md`.",
    )

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is not None
    assert artifact["trigger"]["manual_override"] is True
    assert artifact["curation_status"]["state"] == "ready"


def test_non_qualifying_docs_issue_produces_no_artifact() -> None:
    payload = _payload(
        event_label="type:docs",
        labels=["triage:offen", "type:docs"],
        title="Docs-only housekeeping",
    )

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is None


def test_historical_only_references_force_fail_closed() -> None:
    payload = _payload(
        event_label="context:curate",
        labels=["context:curate"],
        body=(
            "See `docs/archive/docs_hub_snapshot/knowledge/ARCHITECTURE_MAP.md` and "
            "`knowledge/logs/sessions/2026-04-17-issue-1645-wave4-minibatch-g2.md`."
        ),
    )

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is not None
    assert artifact["curation_status"]["state"] == "fail_closed"
    assert artifact["ambiguities"]


def test_historical_paths_are_excluded_from_sources() -> None:
    payload = _payload(
        event_label="context:curate",
        labels=["context:curate"],
        body=(
            "Relevant context might be `docs/archive/docs_hub_snapshot/knowledge/ARCHITECTURE_MAP.md` "
            "plus `knowledge/ARCHITECTURE_MAP.md`."
        ),
    )

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is not None
    source_paths = [source["path"] for source in artifact["sources"]]
    assert "docs/archive/docs_hub_snapshot/knowledge/ARCHITECTURE_MAP.md" not in source_paths
    assert "knowledge/ARCHITECTURE_MAP.md" in source_paths


def test_explicit_valid_repo_paths_are_prioritized_before_default_tiers() -> None:
    payload = _payload(
        event_label="task",
        labels=["task"],
        title="Reconcile control-plane surfaces",
        body=(
            "Inspect `.github/README.md` and `docs/runbooks/GITHUB_WORKFLOW_REGISTER.md` "
            "before the broader control surfaces."
        ),
    )

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is not None
    source_paths = [source["path"] for source in artifact["sources"]]
    assert source_paths[:2] == [
        ".github/README.md",
        "docs/runbooks/GITHUB_WORKFLOW_REGISTER.md",
    ]


def test_write_artifact_for_event_creates_expected_file(tmp_path: Path) -> None:
    payload = _payload(
        event_label="task",
        labels=["task"],
        body="Read `docs/runbooks/CONTROL_REGISTER.md` first.",
        number=2004,
    )

    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(payload), encoding="utf-8")
    artifact_dir = tmp_path / "artifacts"

    artifact_path = backlog_curation.write_artifact_for_event(
        event_path=event_path,
        repo_root=REPO_ROOT,
        artifact_dir=artifact_dir,
    )

    assert artifact_path == artifact_dir / "issue-2004.json"
    assert artifact_path is not None and artifact_path.exists()


def test_write_artifact_for_event_coerces_digit_string_issue_number(tmp_path: Path) -> None:
    payload = _payload(
        event_label="task",
        labels=["task"],
        body="Read `docs/runbooks/CONTROL_REGISTER.md` first.",
        number="2005",
    )

    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(payload), encoding="utf-8")
    artifact_dir = tmp_path / "artifacts"

    artifact_path = backlog_curation.write_artifact_for_event(
        event_path=event_path,
        repo_root=REPO_ROOT,
        artifact_dir=artifact_dir,
    )

    assert artifact_path == artifact_dir / "issue-2005.json"
    assert artifact_path is not None and artifact_path.exists()


def test_write_artifact_for_event_rejects_non_numeric_issue_number(tmp_path: Path) -> None:
    payload = _payload(
        event_label="task",
        labels=["task"],
        body="Read `docs/runbooks/CONTROL_REGISTER.md` first.",
        number="v2.0.0",
    )

    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(payload), encoding="utf-8")
    artifact_dir = tmp_path / "artifacts"

    artifact_path = backlog_curation.write_artifact_for_event(
        event_path=event_path,
        repo_root=REPO_ROOT,
        artifact_dir=artifact_dir,
    )

    assert artifact_path is None


def test_artifact_contract_contains_required_schema_fields() -> None:
    payload = _payload(
        event_label="task",
        labels=["task"],
        body="Read `.github/README.md` and `docs/runbooks/GITHUB_WORKFLOW_REGISTER.md`.",
    )

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is not None
    assert set(artifact.keys()) == {
        "schema_version",
        "issue",
        "trigger",
        "curation_status",
        "sources",
        "execution_hint",
        "ambiguities",
        "anomalies",
    }
    assert set(artifact["issue"].keys()) == {"number", "title", "url", "labels", "milestone"}
    assert set(artifact["trigger"].keys()) == {"event_name", "matched_rules", "manual_override"}
    assert set(artifact["curation_status"].keys()) == {"state", "confidence", "summary"}
    assert set(artifact["execution_hint"].keys()) == {
        "recommended_first_step",
        "suggested_read_order",
        "suggested_next_action",
    }
    assert set(artifact["anomalies"].keys()) == {
        "schema_version",
        "contains_sensitive_signals",
        "sensitivity_reasons",
        "counts_by_strength",
        "findings",
    }
    assert all(
        set(source.keys()) == {"path", "category", "reason", "confidence", "must_read", "priority"}
        for source in artifact["sources"]
    )
    priorities = [source["priority"] for source in artifact["sources"]]
    read_order = [source["path"] for source in artifact["sources"]]
    assert priorities == list(range(1, len(priorities) + 1))
    assert artifact["execution_hint"]["suggested_read_order"] == read_order


def test_missing_explicit_path_creates_strong_broken_reference_anomaly() -> None:
    payload = _payload(
        event_label="context:curate",
        labels=["context:curate"],
        body=(
            "Please validate `.github/workflows/does-not-exist.yml` and "
            "`docs/runbooks/CONTROL_REGISTER.md` for drift."
        ),
    )

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is not None
    anomalies = artifact["anomalies"]["findings"]
    broken = [item for item in anomalies if item["type"] == "broken_reference"]
    assert len(broken) == 1
    finding = broken[0]
    assert finding["strength"] == "strong"
    assert finding["escalation_hint"] == "follow_up_candidate"
    assert finding["minimum_evidence_met"] is True


def test_weak_missing_runbook_signal_is_report_only_hint() -> None:
    payload = _payload(
        event_label="scope:ci",
        labels=["type:bug", "scope:ci"],
        body="Workflow trigger might be stale after a recent change.",
    )

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is not None
    anomalies = artifact["anomalies"]["findings"]
    missing_runbook = [item for item in anomalies if item["type"] == "missing_runbook"]
    assert len(missing_runbook) == 1
    finding = missing_runbook[0]
    assert finding["strength"] == "weak"
    assert finding["escalation_hint"] == "report_only"


def test_sensitive_context_blocks_public_issue_hints() -> None:
    payload = _payload(
        event_label="context:curate",
        labels=["context:curate", "security"],
        body=(
            "Potential secret token exposure in `missing/path/config.yml`; "
            "please investigate."
        ),
    )

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is not None
    assert artifact["anomalies"]["contains_sensitive_signals"] is True
    assert artifact["anomalies"]["sensitivity_reasons"]
    assert all(
        finding["public_issue_allowed"] is False for finding in artifact["anomalies"]["findings"]
    )


def test_semver_tokens_are_not_treated_as_missing_repo_paths() -> None:
    payload = _payload(
        event_label="context:curate",
        labels=["context:curate"],
        body="Investigate migration constraints around Python 3.12.1 and v2.0.0 releases.",
    )

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is not None
    assert artifact["curation_status"]["state"] == "partial"
    assert not any(
        finding["type"] == "broken_reference" for finding in artifact["anomalies"]["findings"]
    )


def test_core_contract_path_is_classified_as_tier4_contract_source() -> None:
    payload = _payload(
        event_label="context:curate",
        labels=["context:curate"],
        body="Inspect `core/contracts/decision_contract_v1.py` for contract compatibility.",
    )

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is not None
    source = next(
        item
        for item in artifact["sources"]
        if item["path"] == "core/contracts/decision_contract_v1.py"
    )
    assert source["category"] == "contract"
    assert source["confidence"] == 0.95


def test_extract_explicit_repo_paths_from_backticks() -> None:
    """Test path extraction from backtick-delimited text."""
    result = backlog_curation.extract_explicit_repo_paths(
        "The file `docs/runbooks/CONTROL_REGISTER.md` needs review."
    )
    assert "docs/runbooks/CONTROL_REGISTER.md" in result


def test_extract_explicit_repo_paths_from_markdown_links() -> None:
    """Test path extraction from markdown link syntax."""
    result = backlog_curation.extract_explicit_repo_paths(
        "See [docs](docs/runbooks/CONTROL_REGISTER.md) for details."
    )
    assert "docs/runbooks/CONTROL_REGISTER.md" in result


def test_extract_explicit_repo_paths_rejects_urls() -> None:
    """Test that HTTP/HTTPS URLs are rejected."""
    result = backlog_curation.extract_explicit_repo_paths(
        "Check https://github.com/jannekbuengener/Claire_de_Binare/blob/main/docs/file.md"
    )
    assert not any("github.com" in path for path in result)


def test_extract_explicit_repo_paths_rejects_windows_drive_paths() -> None:
    r"""Test that Windows drive paths (e.g., C:\path) are rejected."""
    result = backlog_curation.extract_explicit_repo_paths(
        "Config in `C:\\Windows\\System32\\config.txt` and `docs/config.md`"
    )
    assert "docs/config.md" in result
    assert not any("Windows" in path for path in result)


def test_normalize_path_rejects_windows_drive_with_leading_slash() -> None:
    r"""Test that Windows drive paths with prefixes like /C:\path are normalized and rejected."""
    # This tests the fix for the review comment about drive-path order
    result = backlog_curation.normalize_path("/C:\\Users\\file.txt")
    assert result is None


def test_normalize_path_rejects_windows_drive_with_leading_dot_slash() -> None:
    r"""Test that Windows drive paths with ./ prefix are normalized and rejected."""
    result = backlog_curation.normalize_path("./C:\\Users\\file.txt")
    assert result is None


def test_normalize_path_handles_path_traversal() -> None:
    """Test that path traversal attempts (../) are rejected."""
    result = backlog_curation.normalize_path("../../../etc/passwd")
    assert result is None


def test_normalize_path_normalizes_relative_paths() -> None:
    """Test that leading ./ and / are stripped."""
    result = backlog_curation.normalize_path("./docs/runbooks/CONTROL_REGISTER.md")
    assert result == "docs/runbooks/CONTROL_REGISTER.md"

    result = backlog_curation.normalize_path("/docs/runbooks/CONTROL_REGISTER.md")
    assert result == "docs/runbooks/CONTROL_REGISTER.md"


def test_extract_explicit_repo_paths_adversarial_many_slashes() -> None:
    """Test that adversarial input with many slashes doesn't cause performance issues."""
    # This tests robustness against ReDoS
    import time

    adversarial = "a" + "/" * 100 + "b" * 100 + ".txt"
    start = time.time()
    result = backlog_curation.extract_explicit_repo_paths(adversarial)
    elapsed = time.time() - start
    assert elapsed < 1.0, f"Path extraction took {elapsed}s (should complete in <1s)"
