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


def _issue_1827_like_payload() -> dict[str, object]:
    return _payload(
        event_label="task",
        labels=["task"],
        title="[BACKLOG][CURATION] Fix issue-scoped source curation for implementation handoff",
        body=(
            "Die Lane braucht issue-scoped Ranking, Fingerprint, Reuse, dedupe-sicheren Receipt-Kommentar "
            "direkt unter dem Issue, `must_read`/`supporting`/`background`, `constraints`, `watchouts`, "
            "`implementation_targets`, `estimated_tokens` und fail-closed Verhalten. "
            "Downstream `cdb-backlog-anomaly-escalation` darf dabei nicht still kaputt gehen."
        ),
        number=1827,
    )


def test_generic_task_without_issue_scoped_signals_fails_closed() -> None:
    payload = _payload(
        event_label="task",
        labels=["triage:offen", "task"],
        title="Generic task",
        body="Please investigate and come back with a safe next step.",
    )

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is not None
    assert artifact["curation_status"]["state"] == "fail_closed"
    assert artifact["operator_review_needed"] is True
    assert artifact["safe_for_implementation_start"] is False


def test_issue_scoped_keywords_produce_ready_v2_handoff_without_explicit_paths() -> None:
    artifact = backlog_curation.curate_issue_payload(_issue_1827_like_payload(), repo_root=REPO_ROOT)

    assert artifact is not None
    assert artifact["schema_version"] == "v2"
    assert artifact["curation_status"]["state"] == "ready"
    assert artifact["operator_review_needed"] is False
    assert artifact["safe_for_implementation_start"] is True
    assert [item["path"] for item in artifact["handoff"]["must_read"][:2]] == [
        ".github/scripts/backlog_curation.py",
        ".github/workflows/cdb-backlog-curation.yml",
    ]
    assert [item["path"] for item in artifact["handoff"]["implementation_targets"][:2]] == [
        ".github/scripts/backlog_curation.py",
        ".github/workflows/cdb-backlog-curation.yml",
    ]


def test_typed_and_scoped_issue_is_qualified_without_task() -> None:
    payload = _payload(
        event_label="scope:ci",
        labels=["type:bug", "scope:ci"],
        title="CI receipt drift in backlog curation",
        body="The issue needs dedupe-safe receipt comments and artifact handoff compatibility.",
    )

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is not None
    assert artifact["trigger"]["matched_rules"] == ["type:bug", "scope:ci"]
    assert artifact["curation_status"]["state"] in {"ready", "partial"}


def test_non_qualifying_docs_issue_produces_no_artifact() -> None:
    payload = _payload(
        event_label="type:docs",
        labels=["triage:offen", "type:docs"],
        title="Docs-only housekeeping",
    )

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is None


def test_historical_only_references_fail_closed_and_are_excluded() -> None:
    payload = _payload(
        event_label="task",
        labels=["task"],
        body=(
            "See `docs/archive/docs_hub_snapshot/knowledge/ARCHITECTURE_MAP.md` and "
            "`knowledge/logs/sessions/2026-04-17-issue-1645-wave4-minibatch-g2.md`."
        ),
    )

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is not None
    assert artifact["curation_status"]["state"] == "fail_closed"
    assert artifact["ambiguities"]
    assert all(
        "docs/archive/docs_hub_snapshot/knowledge/ARCHITECTURE_MAP.md" != item["path"]
        for item in artifact["sources"]
    )


def test_explicit_repo_paths_are_prioritized_into_must_read() -> None:
    payload = _payload(
        event_label="task",
        labels=["task"],
        title="Reconcile backlog curation implementation surfaces",
        body=(
            "Inspect `.github/scripts/backlog_curation.py` and "
            "`.github/workflows/cdb-backlog-curation.yml` before any other surface."
        ),
    )

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is not None
    assert {
        item["path"] for item in artifact["handoff"]["must_read"][:2]
    } == {
        ".github/scripts/backlog_curation.py",
        ".github/workflows/cdb-backlog-curation.yml",
    }


def test_artifact_contract_contains_required_v2_schema_fields() -> None:
    artifact = backlog_curation.curate_issue_payload(_issue_1827_like_payload(), repo_root=REPO_ROOT)

    assert artifact is not None
    assert set(artifact.keys()) == {
        "schema_version",
        "issue",
        "trigger",
        "curation_status",
        "operator_review_needed",
        "safe_for_implementation_start",
        "fingerprint",
        "read_budget",
        "sources",
        "handoff",
        "execution_hint",
        "ambiguities",
        "reuse",
        "receipt",
        "anomalies",
    }
    assert set(artifact["issue"].keys()) == {"number", "title", "url", "labels", "milestone"}
    assert set(artifact["trigger"].keys()) == {"event_name", "matched_rules"}
    assert set(artifact["curation_status"].keys()) == {"state", "confidence", "summary"}
    assert set(artifact["handoff"].keys()) == {
        "must_read",
        "supporting",
        "background",
        "constraints",
        "watchouts",
        "implementation_targets",
    }
    assert set(artifact["read_budget"].keys()) == {
        "must_read_max",
        "supporting_max",
        "background_max",
        "estimated_tokens",
    }
    assert set(artifact["receipt"].keys()) == {
        "marker",
        "status",
        "fingerprint",
        "top_sources",
        "next_step",
        "artifact_name",
        "artifact_ref",
        "body",
    }
    assert set(artifact["reuse"].keys()) == {
        "fingerprint",
        "receipt_marker",
        "unchanged_issue_can_reuse",
        "strategy",
    }
    assert all(
        set(source.keys()) >= {"path", "priority", "role", "score", "reason", "section_hint", "snippet"}
        for source in artifact["sources"]
    )


def test_receipt_marker_uses_fingerprint_and_short_body() -> None:
    artifact = backlog_curation.curate_issue_payload(_issue_1827_like_payload(), repo_root=REPO_ROOT)

    assert artifact is not None
    receipt = artifact["receipt"]
    assert receipt["marker"] == f"<!-- cdb-backlog-curation-receipt:{artifact['fingerprint']} -->"
    assert receipt["status"] == "curation ready"
    assert "Top-Quellen" in receipt["body"]
    assert "Handoff" in receipt["body"]
    assert artifact["fingerprint"] == artifact["reuse"]["fingerprint"]


def test_read_budget_caps_handoff_lists_and_estimated_tokens() -> None:
    artifact = backlog_curation.curate_issue_payload(_issue_1827_like_payload(), repo_root=REPO_ROOT)

    assert artifact is not None
    assert len(artifact["handoff"]["must_read"]) <= artifact["read_budget"]["must_read_max"]
    assert len(artifact["handoff"]["supporting"]) <= artifact["read_budget"]["supporting_max"]
    assert len(artifact["handoff"]["background"]) <= artifact["read_budget"]["background_max"]
    assert artifact["read_budget"]["estimated_tokens"] > 0


def test_missing_explicit_path_creates_strong_broken_reference_anomaly() -> None:
    payload = _payload(
        event_label="task",
        labels=["task"],
        body=(
            "Please validate `.github/workflows/does-not-exist.yml` and "
            "`.github/scripts/backlog_curation.py` for receipt drift."
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


def test_sensitive_context_blocks_public_issue_hints() -> None:
    payload = _payload(
        event_label="task",
        labels=["task", "security"],
        body="Potential secret token exposure in `missing/path/config.yml`; please investigate.",
    )

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is not None
    assert artifact["anomalies"]["contains_sensitive_signals"] is True
    assert artifact["anomalies"]["sensitivity_reasons"]
    assert all(
        finding["public_issue_allowed"] is False for finding in artifact["anomalies"]["findings"]
    )


def test_write_artifact_for_event_sets_receipt_artifact_name_and_coerces_issue_number(tmp_path: Path) -> None:
    payload = _payload(
        event_label="task",
        labels=["task"],
        body="Read `.github/scripts/backlog_curation.py` first.",
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
    written = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert written["issue"]["number"] == 2005
    assert written["receipt"]["artifact_name"] == "backlog-curation-issue-2005"
    assert written["receipt"]["artifact_ref"] == "artifacts/backlog-curation/issue-2005.json"


def test_extract_explicit_repo_paths_rejects_urls_and_windows_drives() -> None:
    result = backlog_curation.extract_explicit_repo_paths(
        "Check https://github.com/jannekbuengener/Claire_de_Binare/blob/main/docs/file.md, "
        "`C:\\Windows\\System32\\config.txt` and `docs/runbooks/CONTROL_REGISTER.md`."
    )
    assert result == ["docs/runbooks/CONTROL_REGISTER.md"]


def test_normalize_path_rejects_path_traversal_and_prefixed_windows_drives() -> None:
    assert backlog_curation.normalize_path("../../../etc/passwd") is None
    assert backlog_curation.normalize_path("/C:\\Users\\file.txt") is None
    assert backlog_curation.normalize_path("./C:\\Users\\file.txt") is None


def test_extract_explicit_repo_paths_from_backticks() -> None:
    result = backlog_curation.extract_explicit_repo_paths(
        "The file `docs/runbooks/CONTROL_REGISTER.md` needs review."
    )
    assert "docs/runbooks/CONTROL_REGISTER.md" in result


def test_extract_explicit_repo_paths_from_markdown_links() -> None:
    result = backlog_curation.extract_explicit_repo_paths(
        "See [docs](docs/runbooks/CONTROL_REGISTER.md) for details."
    )
    assert "docs/runbooks/CONTROL_REGISTER.md" in result


def test_normalize_path_normalizes_relative_paths() -> None:
    result = backlog_curation.normalize_path("./docs/runbooks/CONTROL_REGISTER.md")
    assert result == "docs/runbooks/CONTROL_REGISTER.md"

    result = backlog_curation.normalize_path("/docs/runbooks/CONTROL_REGISTER.md")
    assert result == "docs/runbooks/CONTROL_REGISTER.md"


def test_extract_explicit_repo_paths_adversarial_many_slashes() -> None:
    import time

    adversarial = "a" + "/" * 100 + "b" * 100 + ".txt"
    start = time.time()
    result = backlog_curation.extract_explicit_repo_paths(adversarial)
    elapsed = time.time() - start
    assert elapsed < 1.0, f"Path extraction took {elapsed}s (should complete in <1s)"
