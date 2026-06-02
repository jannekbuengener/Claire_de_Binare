#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


CONTROL_ISSUE_NUMBER = 1445
ARCHITECTURE_DOCS = [
    "knowledge/ARCHITECTURE_MAP.md",
    "knowledge/governance/SERVICE_CATALOG.md",
]
DISCOVERY_SURFACES = [
    "mcp_navpack_working_repo/ENTRYPOINTS.yaml",
    "mcp_navpack_working_repo/CHEATSHEET.md",
]
RUNBOOK_SURFACES = [
    "docs/runbooks/CONTROL_REGISTER.md",
]
EVIDENCE_SURFACES = [
    "CURRENT_STATUS.md",
    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
]
RUNTIME_REBUILD_COMPOSE_FILES = [
    "infrastructure/compose/compose.blue.yml",
    "infrastructure/compose/compose.red.yml",
    "infrastructure/compose/test.yml",
]
RUNTIME_REBUILD_DOCKERFILES = [
    "services/market/Dockerfile",
    "services/candles/Dockerfile",
    "services/regime/Dockerfile",
    "services/allocation/Dockerfile",
    "services/risk/Dockerfile",
    "services/execution/Dockerfile",
    "services/db_writer/Dockerfile",
    "services/ws/Dockerfile",
    "services/signal/Dockerfile",
    "services/reports/Dockerfile",
    "tools/paper_trading/Dockerfile",
    "infrastructure/compose/Dockerfile.test",
]
RUNTIME_REBUILD_TRIGGER_FILES = RUNTIME_REBUILD_COMPOSE_FILES + RUNTIME_REBUILD_DOCKERFILES
RUNTIME_REBUILD_CI_LAB_FILES = {
    "infrastructure/compose/Dockerfile.test",
    "infrastructure/compose/test.yml",
}
RUNTIME_SERVICE_BY_DOCKERFILE = {
    "services/market/Dockerfile": "cdb_market",
    "services/candles/Dockerfile": "cdb_candles",
    "services/regime/Dockerfile": "cdb_regime",
    "services/allocation/Dockerfile": "cdb_allocation",
    "services/risk/Dockerfile": "cdb_risk",
    "services/execution/Dockerfile": "cdb_execution",
    "services/db_writer/Dockerfile": "cdb_db_writer",
    "services/ws/Dockerfile": "cdb_ws",
    "services/signal/Dockerfile": "cdb_signal",
    "services/reports/Dockerfile": "cdb_reports",
    "tools/paper_trading/Dockerfile": "cdb_paper_runner",
    "infrastructure/compose/Dockerfile.test": "cdb_test_runner",
}
ISSUE_MARKER_TEMPLATE = "<!-- cdb-post-merge-followup-issue:{fingerprint} -->"
COMMENT_MARKER_TEMPLATE = "<!-- cdb-post-merge-followup-comment:pr-{pr_number} -->"
COMMENT_HEADER = "## Post-Merge Follow-up Scan"
CANON_PATTERNS = [
    ("BLACK terminology", re.compile(r"\bBLACK\b")),
    (
        "legacy base/dev runtime start",
        re.compile(r"docker compose .*base\.yml.*dev\.yml.* up -d", re.IGNORECASE),
    ),
    (
        "unqualified docker compose up",
        re.compile(r"docker compose up -d", re.IGNORECASE),
    ),
    (
        "legacy secrets path",
        re.compile(r"(~[/\\]Documents[/\\]\.secrets[/\\]cdb|SECRETS_PATH=.*\.secrets[/\\]cdb)"),
    ),
]


@dataclass
class Finding:
    fingerprint: str
    rule_id: str
    title: str
    classification_input: str
    trigger_files: list[str]
    affected_candidates: list[str]
    evidence_lines: list[str]
    issue_title: str
    labels: list[str]
    force_follow_up_issue: bool = False


def run_command(args: list[str], *, input_text: str | None = None) -> str:
    result = subprocess.run(
        args,
        input=input_text,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(args)}\n{result.stderr.strip()}"
        )
    return result.stdout


class ModelsRateLimitedError(RuntimeError):
    """Raised when gh models run is blocked by GitHub Abuse-/Rate-Limit and retries are exhausted."""


def is_gh_models_rate_limit_error(stderr: str) -> bool:
    """Detect whether stderr indicates a GitHub Models Rate-Limit or Abuse-Detection error."""
    if not stderr:
        return False
    lower = stderr.lower()
    signatures = [
        "rate limited",
        "rate limit",
        "abuse detection mechanism",
        "<title>rate limit",
        "retry after",
    ]
    return any(sig in lower for sig in signatures)


MAX_RETRY_AFTER_CAP_SECONDS = 120


def _parse_retry_after_seconds(stderr: str) -> int:
    """Extract retry-after duration in seconds from stderr like '(retry after 1m0s)'.
    Capped at MAX_RETRY_AFTER_CAP_SECONDS to avoid blocking the workflow
    when the server returns a long retry-after (e.g. 30m)."""
    match = re.search(r"retry after\s+(?:(\d+)m)?(\d+)s", stderr, re.IGNORECASE)
    if match:
        minutes = int(match.group(1)) if match.group(1) else 0
        seconds = int(match.group(2))
        raw = minutes * 60 + seconds
        return min(raw, MAX_RETRY_AFTER_CAP_SECONDS)
    return min(60, MAX_RETRY_AFTER_CAP_SECONDS)


MAX_GH_MODELS_RETRIES = 3
RETRY_BACKOFF_SECONDS = [30, 60, 120]


def run_models_with_retry(
    prompt_file: Path,
    finding_input: str,
    *,
    max_retries: int = MAX_GH_MODELS_RETRIES,
) -> str:
    last_error: str | None = None
    for attempt in range(1, max_retries + 1):
        args = [
            "gh",
            "models",
            "run",
            "--file",
            str(prompt_file),
            "--var",
            f"input={finding_input}",
        ]
        result = subprocess.run(
            args,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=120,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout
        combined = (result.stderr or "") + (result.stdout or "")
        if is_gh_models_rate_limit_error(combined):
            last_error = combined.strip()
            if attempt < max_retries:
                delay = _parse_retry_after_seconds(combined)
                time.sleep(delay)
                continue
            raise ModelsRateLimitedError(
                f"gh models run rate-limited after {max_retries} retries:\n{last_error}"
            )
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(args)}\n{result.stderr.strip()}"
        )

    raise RuntimeError("unreachable")


def run_gh_repo(repo: str, args: list[str], *, input_text: str | None = None) -> str:
    full_args = ["gh"] + args + ["--repo", repo]
    return run_command(full_args, input_text=input_text)


def run_gh_api(args: list[str], *, input_text: str | None = None) -> str:
    return run_command(["gh", "api"] + args, input_text=input_text)


def sha16(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def is_archived_or_historical(path: str) -> bool:
    prefixes = (
        "docs/archive/",
        "knowledge/logs/",
        "reports/",
    )
    return path.startswith(prefixes)


def is_active_surface(path: str) -> bool:
    return not is_archived_or_historical(path)


def parse_added_lines(diff_text: str) -> dict[str, list[str]]:
    added: dict[str, list[str]] = {}
    current_file: str | None = None
    for raw_line in diff_text.splitlines():
        if raw_line.startswith("+++ b/"):
            current_file = raw_line[6:]
            added.setdefault(current_file, [])
            continue
        if raw_line.startswith("diff --git "):
            current_file = None
            continue
        if current_file is None:
            continue
        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            added[current_file].append(raw_line[1:])
    return added


def parse_changed_lines(diff_text: str) -> dict[str, list[tuple[str, str]]]:
    changed: dict[str, list[tuple[str, str]]] = {}
    current_file: str | None = None
    for raw_line in diff_text.splitlines():
        if raw_line.startswith("+++ b/"):
            current_file = raw_line[6:]
            changed.setdefault(current_file, [])
            continue
        if raw_line.startswith("diff --git "):
            current_file = None
            continue
        if current_file is None:
            continue
        if raw_line.startswith(("+", "-")) and not raw_line.startswith(("+++", "---")):
            changed[current_file].append((raw_line[0], raw_line[1:]))
    return changed


def relative_paths(files: list[dict[str, Any]]) -> list[str]:
    return [entry["path"] for entry in files]


def touched(files: list[str], paths: list[str]) -> bool:
    wanted = set(paths)
    return any(path in wanted for path in files)


def touched_prefix(files: list[str], prefixes: tuple[str, ...]) -> bool:
    return any(path.startswith(prefixes) for path in files)


def shortlist(paths: list[str], *, limit: int = 4) -> list[str]:
    if len(paths) <= limit:
        return paths
    return paths[:limit]


def unique_sorted(values: list[str]) -> list[str]:
    return sorted(set(values))


def strip_image_digest(image_ref: str) -> str:
    return re.sub(r"@sha256:[0-9a-f]{64}$", "", image_ref.strip(), flags=re.IGNORECASE)


def normalize_image_change_line(line: str) -> str | None:
    compose_match = re.match(r"^\s*image:\s*(?P<ref>\S+)\s*$", line)
    if compose_match:
        return f"image:{strip_image_digest(compose_match.group('ref'))}"

    dockerfile_match = re.match(
        r"^\s*FROM\s+(?P<ref>\S+)(?:\s+AS\s+(?P<alias>\S+))?\s*$",
        line,
        flags=re.IGNORECASE,
    )
    if dockerfile_match:
        alias = dockerfile_match.group("alias")
        suffix = f" AS {alias}" if alias else ""
        return f"FROM {strip_image_digest(dockerfile_match.group('ref'))}{suffix}"

    return None


def is_digest_only_image_change(changes: list[tuple[str, str]]) -> bool:
    if not changes:
        return False

    removed: list[str] = []
    added: list[str] = []
    saw_digest_reference = False

    for sign, line in changes:
        normalized = normalize_image_change_line(line)
        if normalized is None:
            return False
        if "@sha256:" in line.lower():
            saw_digest_reference = True
        if sign == "-":
            removed.append(normalized)
        elif sign == "+":
            added.append(normalized)

    return saw_digest_reference and removed == added


def service_runtime_changes_are_digest_only(
    service_runtime_files: list[str],
    *,
    changed_lines: dict[str, list[tuple[str, str]]],
) -> bool:
    return bool(service_runtime_files) and all(
        is_digest_only_image_change(changed_lines.get(path, [])) for path in service_runtime_files
    )


def runtime_rebuild_trigger_files(active_files: list[str]) -> list[str]:
    return [path for path in active_files if path in RUNTIME_REBUILD_TRIGGER_FILES]


def runtime_services_for_trigger_files(
    trigger_files: list[str],
    changed_lines: dict[str, list[tuple[str, str]]],
) -> list[str]:
    services: list[str] = []
    for path in trigger_files:
        service = RUNTIME_SERVICE_BY_DOCKERFILE.get(path)
        if service:
            services.append(service)

    return unique_sorted(services)


def runtime_rebuild_labels(trigger_files: list[str]) -> list[str]:
    labels = ["scope:infra", "agent:codex"]
    if any(path in RUNTIME_REBUILD_CI_LAB_FILES for path in trigger_files):
        labels.append("scope:ci")
    return labels


def build_finding(
    *,
    pr_number: int,
    rule_id: str,
    title: str,
    classification_input: str,
    trigger_files: list[str],
    affected_candidates: list[str],
    evidence_lines: list[str],
    issue_title: str,
    labels: list[str],
    force_follow_up_issue: bool = False,
) -> Finding:
    key = "|".join([str(pr_number), rule_id] + sorted(trigger_files))
    return Finding(
        fingerprint=sha16(key),
        rule_id=rule_id,
        title=title,
        classification_input=classification_input.strip(),
        trigger_files=trigger_files,
        affected_candidates=affected_candidates,
        evidence_lines=evidence_lines,
        issue_title=issue_title,
        labels=labels,
        force_follow_up_issue=force_follow_up_issue,
    )


def detect_findings(pr: dict[str, Any], diff_text: str) -> list[Finding]:
    findings: list[Finding] = []
    files = relative_paths(pr["files"])
    active_files = [path for path in files if is_active_surface(path)]
    pr_number = pr["number"]
    pr_url = pr["url"]
    pr_title = pr["title"]
    added_lines = parse_added_lines(diff_text)
    changed_lines = parse_changed_lines(diff_text)

    service_runtime_files = [
        path
        for path in active_files
        if path.startswith("services/")
        or path.startswith("core/")
        or path.startswith("infrastructure/database/")
        or path
        in {
            "infrastructure/compose/compose.blue.yml",
            "infrastructure/compose/compose.red.yml",
            "infrastructure/compose/SERVICE_MAPPING.md",
            "infrastructure/compose/COMPOSE_LAYERS.md",
        }
    ]
    digest_only_service_runtime_change = service_runtime_changes_are_digest_only(
        service_runtime_files,
        changed_lines=changed_lines,
    )
    if (
        service_runtime_files
        and not digest_only_service_runtime_change
        and not touched(active_files, ARCHITECTURE_DOCS)
    ):
        trigger_files = shortlist(service_runtime_files)
        affected_candidates = trigger_files + ARCHITECTURE_DOCS
        finding_input = f"""
PR #{pr_number} ({pr_title}) changed service/runtime surfaces {", ".join(trigger_files)}, but did not update knowledge/ARCHITECTURE_MAP.md or knowledge/governance/SERVICE_CATALOG.md. Evidence is repo-backed from the merged PR diff {pr_url}. Affected artifacts are {", ".join(affected_candidates)}. The likely follow-up is a small, documentation-only architecture/service-catalog reconciliation if drift is real.
        """
        findings.append(
            build_finding(
                pr_number=pr_number,
                rule_id="architecture_service_catalog_drift",
                title="Service/runtime change without architecture catalog follow-up",
                classification_input=finding_input,
                trigger_files=trigger_files,
                affected_candidates=affected_candidates,
                evidence_lines=[],
                issue_title=f"Reconcile architecture docs after PR #{pr_number} service/runtime changes",
                labels=["scope:docs", "type:docs", "agent:codex"],
            )
        )

    runtime_rebuild_files = runtime_rebuild_trigger_files(active_files)
    runtime_rebuild_change_is_digest_only = service_runtime_changes_are_digest_only(
        runtime_rebuild_files,
        changed_lines=changed_lines,
    )
    if runtime_rebuild_files and not runtime_rebuild_change_is_digest_only:
        trigger_files = shortlist(runtime_rebuild_files)
        has_compose_trigger = any(path in RUNTIME_REBUILD_COMPOSE_FILES for path in runtime_rebuild_files)
        services = runtime_services_for_trigger_files(runtime_rebuild_files, changed_lines)
        service_note = ", ".join(services) if services else "unknown from changed lines"
        if has_compose_trigger:
            service_note = "unknown / inspect compose file"
        evidence_lines = [
            f"Runtime trigger files: {', '.join(trigger_files)}",
            f"Affected runtime services: {service_note}",
            "Operator action required: prüfen, ob BLUE/RED runtime rebuild/recreate nötig ist.",
            "No automatic docker compose up, rebuild, recreate, restart, live enable, or trading action is authorized.",
        ]
        finding_input = f"""
PR #{pr_number} ({pr_title}) changed Docker/Compose runtime build surfaces {", ".join(trigger_files)}. Evidence is repo-backed from the merged PR diff {pr_url}. Affected runtime services inferred from active BLUE/RED and CI-lab build references: {service_note}. This deterministic follow-up must create a narrow operator issue to review whether a manual runtime rebuild/recreate is needed. The issue must not run Docker commands, must not auto-restart services, must not imply live-readiness, and must not authorize Echtgeld or live trading.

Manual operator hints only, not executed by this workflow. Replace <service> with the affected service and run only after explicit operator GO in the matching runtime context:
- docker compose -f infrastructure/compose/compose.blue.yml up -d --build --force-recreate <service>
- docker compose -f infrastructure/compose/compose.red.yml up -d --build --force-recreate <service>
        """
        findings.append(
            build_finding(
                pr_number=pr_number,
                rule_id="docker_runtime_rebuild_followup_required",
                title="Docker runtime rebuild/recreate follow-up required",
                classification_input=finding_input,
                trigger_files=trigger_files,
                affected_candidates=runtime_rebuild_files,
                evidence_lines=evidence_lines,
                issue_title=f"Review runtime rebuild/recreate need after PR #{pr_number} Docker changes",
                labels=runtime_rebuild_labels(runtime_rebuild_files),
                force_follow_up_issue=True,
            )
        )

    control_runtime_files = [
        path
        for path in active_files
        if path.startswith(".github/workflows/")
        or path.startswith(".github/scripts/")
        or path in {"infrastructure/monitoring/alerts.yml", "infrastructure/monitoring/prometheus.yml"}
    ]
    support_followup_touched = touched(active_files, RUNBOOK_SURFACES + EVIDENCE_SURFACES) or touched_prefix(
        active_files, ("docs/runbooks/", "docs/operations/", "docs/ci/")
    )
    if control_runtime_files and not support_followup_touched:
        trigger_files = shortlist(control_runtime_files)
        affected_candidates = trigger_files + RUNBOOK_SURFACES
        finding_input = f"""
PR #{pr_number} ({pr_title}) changed workflow/control surfaces {", ".join(trigger_files)}, but no runbook or evidence companion was changed in docs/runbooks/, docs/operations/, docs/ci/, CURRENT_STATUS.md, or docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md. Evidence is repo-backed from merged PR diff {pr_url}. Affected artifacts are {", ".join(affected_candidates)}. If a small control-note or runbook follow-up is clearly needed, treat it as a separate fix package; otherwise keep it in the control thread.
        """
        findings.append(
            build_finding(
                pr_number=pr_number,
                rule_id="runbook_evidence_followup_drift",
                title="Workflow/control change without runbook or evidence follow-up",
                classification_input=finding_input,
                trigger_files=trigger_files,
                affected_candidates=affected_candidates,
                evidence_lines=[],
                issue_title=f"Reconcile control docs after PR #{pr_number} workflow changes",
                labels=["scope:ci", "scope:docs", "type:docs", "agent:codex"],
            )
        )

    discovery_trigger_files = [
        path
        for path in active_files
        if path.startswith(".github/workflows/")
        or path.startswith("docs/runbooks/")
        or path in ARCHITECTURE_DOCS
        or path in {"README.md", "docs/index.md", "services/README.md", "infrastructure/compose/README.md"}
    ]
    if discovery_trigger_files and not touched(active_files, DISCOVERY_SURFACES):
        trigger_files = shortlist(discovery_trigger_files)
        affected_candidates = trigger_files + DISCOVERY_SURFACES
        finding_input = f"""
PR #{pr_number} ({pr_title}) changed front-door or operator-facing surfaces {", ".join(trigger_files)}, but did not touch mcp_navpack_working_repo/ENTRYPOINTS.yaml or mcp_navpack_working_repo/CHEATSHEET.md. Evidence is repo-backed from merged PR diff {pr_url}. Affected artifacts are {", ".join(affected_candidates)}. This may leave discovery surfaces stale, but the need for a repo change is not proven from the diff alone.
        """
        findings.append(
            build_finding(
                pr_number=pr_number,
                rule_id="discovery_surface_drift",
                title="Possible discovery-surface drift after operator-facing changes",
                classification_input=finding_input,
                trigger_files=trigger_files,
                affected_candidates=affected_candidates,
                evidence_lines=[],
                issue_title=f"Update discovery surfaces after PR #{pr_number}",
                labels=["scope:docs", "type:docs", "agent:codex"],
            )
        )

    canon_hits: list[tuple[str, str, str]] = []
    for path, lines in added_lines.items():
        if not is_active_surface(path):
            continue
        if path.startswith(("tests/", "docs/archive/", "knowledge/logs/")):
            continue
        for line in lines:
            for label, pattern in CANON_PATTERNS:
                if pattern.search(line):
                    canon_hits.append((path, label, line.strip()))
    if canon_hits:
        seen_files: list[str] = []
        evidence_lines: list[str] = []
        for path, label, line in canon_hits[:6]:
            if path not in seen_files:
                seen_files.append(path)
            evidence_lines.append(f"{path}: {label}: {line}")
        trigger_files = shortlist(seen_files)
        joined_evidence = "; ".join(evidence_lines)
        finding_input = f"""
PR #{pr_number} ({pr_title}) reintroduced active-surface canon or terminology drift. Repo-backed added lines show: {joined_evidence}. Evidence comes directly from merged PR diff {pr_url}. The likely fix is a small, separate clean-up in the touched active files only.
        """
        findings.append(
            build_finding(
                pr_number=pr_number,
                rule_id="canon_terminology_drift",
                title="Canon or terminology drift reintroduced in active surfaces",
                classification_input=finding_input,
                trigger_files=trigger_files,
                affected_candidates=trigger_files,
                evidence_lines=evidence_lines,
                issue_title=f"Remove reintroduced canon drift after PR #{pr_number}",
                labels=["scope:docs", "type:docs", "agent:codex"],
            )
        )

    unique: dict[str, Finding] = {}
    for finding in findings:
        unique[finding.fingerprint] = finding
    return list(unique.values())


def classify_finding(
    *,
    prompt_file: Path,
    finding: Finding,
) -> dict[str, Any]:
    raw = run_models_with_retry(
        prompt_file=prompt_file,
        finding_input=finding.classification_input,
    )
    if not raw.strip():
        raise RuntimeError(
            "gh models run returned empty response — models API unavailable or quota exceeded"
        )
    payload = json.loads(extract_json_payload(raw))
    if payload.get("classification") not in {"report_only", "follow_up_issue", "unclear"}:
        raise RuntimeError("classifier returned invalid classification")
    confidence = payload.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise RuntimeError("classifier returned invalid confidence")
    affected = payload.get("affected_artifacts")
    if not isinstance(affected, list) or not all(isinstance(item, str) and item for item in affected):
        raise RuntimeError("classifier returned invalid affected_artifacts")
    normalized_affected: list[str] = []
    for item in affected:
        cleaned = item.strip()
        if cleaned and cleaned not in normalized_affected:
            normalized_affected.append(cleaned)
    payload["affected_artifacts"] = normalized_affected
    next_step = payload.get("suggested_next_step")
    if not isinstance(next_step, str) or not next_step:
        raise RuntimeError("classifier returned invalid suggested_next_step")
    return payload


def extract_json_payload(raw: str) -> str:
    stripped = raw.strip()
    fence_match = re.fullmatch(r"```(?:json)?\s*(?P<payload>.*?)\s*```", stripped, re.DOTALL)
    if fence_match:
        return fence_match.group("payload").strip()
    return stripped


def classification_for_finding(
    *,
    prompt_file: Path,
    finding: Finding,
) -> dict[str, Any]:
    if finding.force_follow_up_issue:
        return {
            "classification": "follow_up_issue",
            "confidence": 1.0,
            "affected_artifacts": finding.affected_candidates,
            "suggested_next_step": (
                "Open a narrow operator follow-up to review whether a manual "
                "BLUE/RED runtime rebuild or recreate is needed; do not run "
                "Docker commands automatically."
            ),
        }

    return classify_finding(prompt_file=prompt_file, finding=finding)


def gh_repo_json(repo: str, args: list[str]) -> Any:
    return json.loads(run_gh_repo(repo, args))


def gh_api_json(args: list[str], *, input_text: str | None = None) -> Any:
    return json.loads(run_gh_api(args, input_text=input_text))


def find_existing_issue(repo: str, marker: str) -> dict[str, Any] | None:
    issues = gh_api_json(
        [
            f"repos/{repo}/issues?state=all&per_page=100",
        ],
    )
    flattened: list[dict[str, Any]]
    if isinstance(issues, list):
        flattened = [issue for issue in issues if isinstance(issue, dict)]
    else:
        flattened = [issues] if isinstance(issues, dict) else []
    matches = [
        issue
        for issue in flattened
        if "pull_request" not in issue and marker in (issue.get("body") or "")
    ]
    if not matches:
        return None
    matches.sort(key=lambda issue: issue.get("created_at") or "", reverse=True)
    return matches[0]


def ensure_issue(
    *,
    repo: str,
    pr: dict[str, Any],
    finding: Finding,
    classification: dict[str, Any],
) -> dict[str, Any]:
    marker = ISSUE_MARKER_TEMPLATE.format(fingerprint=finding.fingerprint)
    existing = find_existing_issue(repo, marker)
    if existing is not None:
        return {
            "action": "existing_open" if existing.get("state") == "open" else "existing_closed",
            "number": existing.get("number"),
            "url": existing.get("html_url"),
        }

    publication_basis = (
        "deterministic follow-up issue"
        if finding.force_follow_up_issue
        else "classifier follow-up issue"
    )
    effective_classification = (
        "follow_up_issue" if finding.force_follow_up_issue else classification["classification"]
    )
    guardrails_block = ""
    if finding.force_follow_up_issue:
        guardrails_block = (
            f"### Guardrails\n\n"
            f"- Operator prüfen: rebuild/recreate nötig?\n"
            f"- No automatic Docker runtime command is executed by this workflow.\n"
            f"- No auto-restart, no live-readiness upgrade, no Echtgeld-GO, no live trading enablement.\n\n"
            f"### Manual operator hints (not executed)\n\n"
            f"```bash\n"
            f"docker compose -f infrastructure/compose/compose.blue.yml up -d --build --force-recreate <service>\n"
            f"docker compose -f infrastructure/compose/compose.red.yml up -d --build --force-recreate <service>\n"
            f"```\n\n"
            f"Replace `<service>` with the affected service and run only after explicit "
            f"operator GO in the matching runtime context.\n\n"
        )
    affected = "\n".join(f"- `{path}`" for path in classification["affected_artifacts"])
    body = (
        f"## Post-Merge Follow-up Finding\n\n"
        f"{marker}\n\n"
        f"- Source PR: #{pr['number']} ({pr['url']})\n"
        f"- Rule: `{finding.rule_id}`\n"
        f"- Classification: `{effective_classification}`\n"
        f"- Confidence: `{classification['confidence']}`\n\n"
        f"- Publication basis: `{publication_basis}`\n\n"
        f"{guardrails_block}"
        f"### Why this is a small follow-up\n\n"
        f"{classification['suggested_next_step']}\n\n"
        f"### Affected artifacts\n\n"
        f"{affected}\n\n"
        f"### Repo-backed evidence\n\n"
        f"{finding.classification_input}\n"
    )

    args = [
        "issue",
        "create",
        "--title",
        finding.issue_title,
        "--body",
        body,
    ]
    for label in finding.labels:
        args.extend(["--label", label])
    url = run_gh_repo(repo, args).strip()
    number = int(url.rstrip("/").split("/")[-1])
    return {"action": "created", "number": number, "url": url}


def load_issue_comments(repo: str, issue_number: int) -> list[dict[str, Any]]:
    comments = gh_api_json(
        [
            f"repos/{repo}/issues/{issue_number}/comments?per_page=100",
        ],
    )
    if isinstance(comments, list):
        flattened = [comment for comment in comments if isinstance(comment, dict)]
    else:
        flattened = [comments] if isinstance(comments, dict) else []
    return flattened


def upsert_control_comment(
    *,
    repo: str,
    pr: dict[str, Any],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    marker = COMMENT_MARKER_TEMPLATE.format(pr_number=pr["number"])
    body_lines = [
        COMMENT_HEADER,
        "",
        marker,
        "",
        f"- PR: #{pr['number']} ({pr['url']})",
        f"- Title: {pr['title']}",
        f"- Findings: {len(findings)}",
        "",
    ]
    for finding in findings:
        body_lines.extend(
            [
                f"### {finding['title']}",
                "",
                f"- Rule: `{finding['rule_id']}`",
                f"- Classification: `{finding['classification']['classification']}`",
                f"- Confidence: `{finding['classification']['confidence']}`",
                f"- Affected artifacts: `{', '.join(finding['classification']['affected_artifacts'])}`",
                f"- Suggested next step: {finding['classification']['suggested_next_step']}",
                "",
            ]
        )
    body = "\n".join(body_lines).strip() + "\n"
    body_json = json.dumps({"body": body})

    comments = load_issue_comments(repo, CONTROL_ISSUE_NUMBER)
    existing = next((comment for comment in comments if marker in (comment.get("body") or "")), None)
    if existing is None:
        response = gh_api_json(
            [
                "--method",
                "POST",
                f"repos/{repo}/issues/{CONTROL_ISSUE_NUMBER}/comments",
                "--input",
                "-",
            ],
            input_text=body_json,
        )
        return {"action": "created", "url": response.get("html_url"), "body": body}

    response = gh_api_json(
        [
            "--method",
            "PATCH",
            f"repos/{repo}/issues/comments/{existing['id']}",
            "--input",
            "-",
        ],
        input_text=body_json,
    )
    return {"action": "updated", "url": response.get("html_url"), "body": body}


def build_summary(result: dict[str, Any]) -> str:
    pr = result["pr"]
    status = result.get("status", "completed")
    lines = [
        "# CDB Post-Merge Follow-up Scan",
        "",
        f"- Status: `{status}`",
        f"- PR: #{pr['number']} ({pr['url']})",
        f"- Title: {pr['title']}",
        f"- Mode: `{result['publish_mode']}`",
        f"- Candidate findings: `{result['candidate_count']}`",
        f"- Classified findings: `{len(result['findings'])}`",
        "",
    ]
    if status == "degraded_rate_limited":
        lines.extend(
            [
                "## Degraded: Rate Limited",
                "",
                "The GitHub Models API returned a rate-limit or abuse-detection error. "
                "Model classification was not available for one or more findings. "
                "No blind follow-up issues were created based on unavailable model output.",
                "Run the scanner manually via `workflow_dispatch` when the rate limit resets.",
                "",
            ]
        )

    if not result["findings"]:
        lines.extend(
            [
                "## Result",
                "",
                "No repo-backed follow-up finding was emitted by the deterministic V1 rules.",
                "",
            ]
        )
        return "\n".join(lines)

    for finding in result["findings"]:
        cls = finding["classification"]
        degraded_note = ""
        if finding.get("degraded_reason") == "rate_limited":
            degraded_note = " (degraded — model classification unavailable)"
        lines.extend(
            [
                f"## {finding['title']}{degraded_note}",
                "",
                f"- Rule: `{finding['rule_id']}`",
                f"- Classification: `{cls['classification']}`",
                f"- Confidence: `{cls['confidence']}`",
                f"- Affected artifacts: `{', '.join(cls['affected_artifacts'])}`",
                f"- Suggested next step: {cls['suggested_next_step']}",
            ]
        )
        if finding.get("publication"):
            publication = finding["publication"]
            lines.append(f"- Publication: `{publication['action']}`")
            if publication.get("url"):
                lines.append(f"- URL: {publication['url']}")
        lines.append("")
    if result.get("control_comment"):
        lines.extend(
            [
                "## Control Comment",
                "",
                f"- Action: `{result['control_comment']['action']}`",
                f"- URL: {result['control_comment'].get('url', 'n/a')}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(result_file: Path, summary_file: Path, result: dict[str, Any]) -> None:
    result_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    summary_file.write_text(build_summary(result), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan merged PRs for small post-merge follow-up drift")
    parser.add_argument("--repo", required=True, help="GitHub repo in owner/name form")
    parser.add_argument("--pr-number", required=True, type=int, help="Merged PR number to inspect")
    parser.add_argument("--prompt-file", required=True, type=Path)
    parser.add_argument("--result-file", required=True, type=Path)
    parser.add_argument("--summary-file", required=True, type=Path)
    parser.add_argument(
        "--publish-mode",
        choices=["dry_run", "publish"],
        default="dry_run",
        help="Whether to publish comments/issues or only write artifacts",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pr = gh_repo_json(
        args.repo,
        [
            "pr",
            "view",
            str(args.pr_number),
            "--json",
            "number,title,url,mergedAt,files",
        ],
    )
    if not pr.get("mergedAt"):
        raise RuntimeError(f"PR #{args.pr_number} is not merged; scanner is merged-PR only")

    diff_text = run_gh_repo(args.repo, ["pr", "diff", str(args.pr_number)])
    candidates = detect_findings(pr, diff_text)

    results: list[dict[str, Any]] = []
    comment_findings: list[dict[str, Any]] = []
    degraded: bool = False
    for finding in candidates:
        try:
            classification = classification_for_finding(
                prompt_file=args.prompt_file,
                finding=finding,
            )
        except ModelsRateLimitedError:
            degraded = True
            degraded_classification = {
                "classification": "unclear",
                "confidence": 0.0,
                "affected_artifacts": finding.affected_candidates,
                "suggested_next_step": (
                    "No model classification available — scanner was rate-limited. "
                    "No blind follow-up issue was created. Re-run the scanner "
                    "manually when the rate limit resets."
                ),
            }
            item = asdict(finding)
            item["classification"] = degraded_classification
            item["degraded_reason"] = "rate_limited"
            results.append(item)
            continue

        item = asdict(finding)
        item["classification"] = classification
        if args.publish_mode == "publish":
            if finding.force_follow_up_issue or classification["classification"] == "follow_up_issue":
                item["publication"] = ensure_issue(
                    repo=args.repo,
                    pr=pr,
                    finding=finding,
                    classification=classification,
                )
            else:
                comment_findings.append(item)
        results.append(item)

    control_comment: dict[str, Any] | None = None
    if args.publish_mode == "publish" and comment_findings:
        control_comment = upsert_control_comment(
            repo=args.repo,
            pr=pr,
            findings=comment_findings,
        )

    status = "degraded_rate_limited" if degraded else "completed"
    payload = {
        "repo": args.repo,
        "publish_mode": args.publish_mode,
        "pr": {
            "number": pr["number"],
            "title": pr["title"],
            "url": pr["url"],
            "mergedAt": pr["mergedAt"],
        },
        "status": status,
        "candidate_count": len(candidates),
        "findings": results,
        "control_comment": control_comment,
    }
    write_outputs(args.result_file, args.summary_file, payload)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - fail-closed entrypoint
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
