from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPT_PATH = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "scripts"
    / "post_merge_followup_scanner.py"
)
SPEC = importlib.util.spec_from_file_location("post_merge_followup_scanner", SCRIPT_PATH)
assert SPEC is not None
scanner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = scanner
assert SPEC.loader is not None
SPEC.loader.exec_module(scanner)


def _pr(files: list[str], *, number: int = 2142) -> dict:
    return {
        "number": number,
        "title": "test PR",
        "url": f"https://github.example/pr/{number}",
        "files": [{"path": path} for path in files],
    }


def _diff(path: str, removed: list[str], added: list[str]) -> str:
    lines = [
        f"diff --git a/{path} b/{path}",
        f"--- a/{path}",
        f"+++ b/{path}",
    ]
    lines.extend(f"-{line}" for line in removed)
    lines.extend(f"+{line}" for line in added)
    return "\n".join(lines)


def _finding_by_rule(findings: list, rule_id: str):
    return next((finding for finding in findings if finding.rule_id == rule_id), None)


def test_runtime_dockerfile_change_requires_deterministic_followup_issue() -> None:
    path = "services/risk/Dockerfile"
    findings = scanner.detect_findings(
        _pr([path]),
        _diff(path, ["RUN pip install -r requirements.txt"], ["RUN pip install --no-cache-dir -r requirements.txt"]),
    )

    finding = _finding_by_rule(findings, "docker_runtime_rebuild_followup_required")

    assert finding is not None
    assert finding.force_follow_up_issue is True
    assert finding.trigger_files == [path]
    assert finding.labels == ["scope:infra", "agent:codex"]


def test_ci_lab_dockerfile_change_adds_scope_ci_label() -> None:
    path = "infrastructure/compose/Dockerfile.test"
    findings = scanner.detect_findings(
        _pr([path]),
        _diff(path, ["RUN pip install -r requirements.txt"], ["RUN pip install --no-cache-dir -r requirements.txt"]),
    )

    finding = _finding_by_rule(findings, "docker_runtime_rebuild_followup_required")

    assert finding is not None
    assert finding.labels == ["scope:infra", "agent:codex", "scope:ci"]


def test_ci_lab_compose_change_adds_scope_ci_label() -> None:
    path = "infrastructure/compose/test.yml"
    findings = scanner.detect_findings(
        _pr([path]),
        _diff(
            path,
            ["      dockerfile: services/risk/Dockerfile"],
            ["      dockerfile: infrastructure/compose/Dockerfile.test"],
        ),
    )

    finding = _finding_by_rule(findings, "docker_runtime_rebuild_followup_required")

    assert finding is not None
    assert finding.labels == ["scope:infra", "agent:codex", "scope:ci"]


def test_blue_compose_build_change_requires_runtime_rebuild_followup() -> None:
    path = "infrastructure/compose/compose.blue.yml"
    findings = scanner.detect_findings(
        _pr([path]),
        _diff(
            path,
            ["      dockerfile: services/risk/Dockerfile"],
            ["      dockerfile: services/execution/Dockerfile"],
        ),
    )

    finding = _finding_by_rule(findings, "docker_runtime_rebuild_followup_required")

    assert finding is not None
    assert finding.force_follow_up_issue is True
    assert "unknown / inspect compose file" in " ".join(finding.evidence_lines)
    assert "cdb_risk" not in " ".join(finding.evidence_lines)
    assert "cdb_execution" not in " ".join(finding.evidence_lines)


def test_digest_only_compose_image_change_does_not_emit_runtime_rebuild_followup() -> None:
    path = "infrastructure/compose/compose.red.yml"
    old_digest = "a" * 64
    new_digest = "b" * 64
    findings = scanner.detect_findings(
        _pr([path]),
        _diff(
            path,
            [f"    image: prom/prometheus:v3.11.2@sha256:{old_digest}"],
            [f"    image: prom/prometheus:v3.11.2@sha256:{new_digest}"],
        ),
    )

    assert _finding_by_rule(findings, "docker_runtime_rebuild_followup_required") is None


def test_docs_only_change_does_not_emit_runtime_rebuild_followup() -> None:
    path = "docs/runbooks/CDB_POST_MERGE_FOLLOWUP_SCANNER.md"
    findings = scanner.detect_findings(
        _pr([path]),
        _diff(path, ["old note"], ["new note"]),
    )

    assert _finding_by_rule(findings, "docker_runtime_rebuild_followup_required") is None


def test_runtime_rebuild_fingerprint_is_stable_for_same_pr_rule_and_files() -> None:
    path = "services/signal/Dockerfile"
    pr = _pr([path], number=2200)
    diff_text = _diff(path, ["RUN pip install -r requirements.txt"], ["RUN pip install --no-cache-dir -r requirements.txt"])

    first = _finding_by_rule(
        scanner.detect_findings(pr, diff_text),
        "docker_runtime_rebuild_followup_required",
    )
    second = _finding_by_rule(
        scanner.detect_findings(pr, diff_text),
        "docker_runtime_rebuild_followup_required",
    )

    assert first is not None
    assert second is not None
    assert first.fingerprint == second.fingerprint


def test_forced_runtime_rebuild_followup_does_not_call_model_classifier(monkeypatch) -> None:
    path = "services/risk/Dockerfile"
    finding = _finding_by_rule(
        scanner.detect_findings(
            _pr([path]),
            _diff(path, ["RUN pip install -r requirements.txt"], ["RUN pip install --no-cache-dir -r requirements.txt"]),
        ),
        "docker_runtime_rebuild_followup_required",
    )
    assert finding is not None

    def fail_classifier(**_kwargs):
        raise AssertionError("model classifier must not be called for forced findings")

    monkeypatch.setattr(scanner, "classify_finding", fail_classifier)

    classification = scanner.classification_for_finding(
        prompt_file=Path(".github/prompts/cdb-control-followup.prompt.yml"),
        finding=finding,
    )

    assert classification["classification"] == "follow_up_issue"
    assert classification["confidence"] == 1.0
    assert classification["affected_artifacts"] == finding.affected_candidates


def test_model_classifier_accepts_json_wrapped_in_markdown_fence(monkeypatch) -> None:
    finding = scanner.Finding(
        fingerprint="abc",
        rule_id="discovery_surface_drift",
        title="Discovery drift",
        classification_input="repo-backed finding",
        trigger_files=["docs/index.md"],
        affected_candidates=["docs/index.md"],
        evidence_lines=[],
        issue_title="Update discovery surfaces",
        labels=["scope:docs"],
    )

    def fenced_json(*_args, **_kwargs):
        return """```json
{
  "classification": "report_only",
  "confidence": 0.5,
  "affected_artifacts": ["docs/index.md"],
  "suggested_next_step": "Record the observation."
}
```"""

    monkeypatch.setattr(scanner, "run_command", fenced_json)

    classification = scanner.classify_finding(
        prompt_file=Path(".github/prompts/cdb-control-followup.prompt.yml"),
        finding=finding,
    )

    assert classification["classification"] == "report_only"
    assert classification["affected_artifacts"] == ["docs/index.md"]
