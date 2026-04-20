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
    number: int = 1794,
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
    assert (
        "docs/archive/docs_hub_snapshot/knowledge/ARCHITECTURE_MAP.md"
        not in source_paths
    )
    assert "knowledge/ARCHITECTURE_MAP.md" in source_paths


def test_version_strings_do_not_degrade_partial_curation() -> None:
    payload = _payload(
        event_label="context:curate",
        labels=["context:curate"],
        body="Validate against Python 3.12.1 and the v2.0.0 rollout notes before implementation.",
    )

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is not None
    assert artifact["curation_status"]["state"] == "partial"
    assert artifact["ambiguities"] == []


def test_core_and_docs_contract_paths_are_tier4_context() -> None:
    payload = _payload(
        event_label="task",
        labels=["task"],
        body=(
            "Inspect `core/contracts/decision_contract_v1.py` and "
            "`docs/contracts/strategy_validation_report_v1.schema.json`."
        ),
    )

    artifact = backlog_curation.curate_issue_payload(payload, repo_root=REPO_ROOT)

    assert artifact is not None
    source_map = {source["path"]: source for source in artifact["sources"]}
    assert (
        source_map["core/contracts/decision_contract_v1.py"]["category"] == "contract"
    )
    assert (
        source_map["core/contracts/decision_contract_v1.py"]["reason"]
        == "Explicitly referenced in the issue and clearly relevant as contract/validation/strategy context."
    )
    assert source_map["core/contracts/decision_contract_v1.py"]["confidence"] == 0.95
    assert (
        source_map["docs/contracts/strategy_validation_report_v1.schema.json"][
            "category"
        ]
        == "contract"
    )
    assert (
        source_map["docs/contracts/strategy_validation_report_v1.schema.json"][
            "confidence"
        ]
        == 0.95
    )


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


def test_write_artifact_for_event_returns_none_for_invalid_issue_number(
    tmp_path: Path,
) -> None:
    payload = _payload(
        event_label="task",
        labels=["task"],
        body="Read `docs/runbooks/CONTROL_REGISTER.md` first.",
        number=2004,
    )
    payload["issue"]["number"] = "v2.0.0"

    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(payload), encoding="utf-8")
    artifact_dir = tmp_path / "artifacts"

    artifact_path = backlog_curation.write_artifact_for_event(
        event_path=event_path,
        repo_root=REPO_ROOT,
        artifact_dir=artifact_dir,
    )

    assert artifact_path is None
    assert list(artifact_dir.glob("issue-*.json")) == []


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
    }
    assert set(artifact["issue"].keys()) == {
        "number",
        "title",
        "url",
        "labels",
        "milestone",
    }
    assert set(artifact["trigger"].keys()) == {
        "event_name",
        "matched_rules",
        "manual_override",
    }
    assert set(artifact["curation_status"].keys()) == {"state", "confidence", "summary"}
    assert set(artifact["execution_hint"].keys()) == {
        "recommended_first_step",
        "suggested_read_order",
        "suggested_next_action",
    }
    assert all(
        set(source.keys())
        == {"path", "category", "reason", "confidence", "must_read", "priority"}
        for source in artifact["sources"]
    )
    priorities = [source["priority"] for source in artifact["sources"]]
    read_order = [source["path"] for source in artifact["sources"]]
    assert priorities == list(range(1, len(priorities) + 1))
    assert artifact["execution_hint"]["suggested_read_order"] == read_order
