"""Shared helpers for workflow control-plane contract tests (#3844–#3847)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
WORKFLOW_REGISTER_MD = REPO_ROOT / "docs" / "runbooks" / "GITHUB_WORKFLOW_REGISTER.md"
CONTROL_PLANE_REGISTER_JSON = (
    REPO_ROOT / ".github" / "control-plane" / "generated" / "workflow-register.json"
)
REQUIRED_CHECKS_BASELINE = (
    REPO_ROOT / "reports" / "REQUIRED_CHECK_CONTEXTS_BASELINE_main.json"
)

WRITE_PERMISSION_SCOPES = frozenset(
    {
        "issues:write",
        "pull-requests:write",
        "contents:write",
        "id-token:write",
    }
)

FORBIDDEN_TRIGGERS = frozenset({"pull_request_target"})

AUTOMATIC_TRIGGERS = frozenset(
    {
        "push",
        "pull_request",
        "schedule",
        "issues",
        "issue_comment",
        "pull_request_review_comment",
        "repository_dispatch",
        "workflow_run",
    }
)

PARKED_WORKFLOW_FILES = frozenset(
    {
        "control_board_auto_routing.yml",
        "control-board-routing-label-dispatch.yml",
        "auto-label.yml",
        "comprehensive-issue-labeling.yml",
        "issue-governance.yml",
        "gemini-scheduled-triage.yml",
    }
)

FROZEN_LEGACY_WORKFLOW_FILES = frozenset({"ci.yaml"})

ACTIVE_CANONICAL_CI_WORKFLOW = "ci.yml"

REQUIRED_CHECK_CONTEXTS = frozenset(
    {
        "ci (Unit/Integration + Lint gesammelt)",
        "policy-gate",
    }
)

NON_REQUIRED_GUARD_WORKFLOWS = frozenset(
    {
        "docs-hub-guard.yml",
        "docs-conflict-guard.yml",
    }
)

# Repo-true explicit findings: workflows on disk not listed in the markdown register.
# Tests surface these as findings; register correction is a separate follow-up.
KNOWN_UNREGISTERED_WORKFLOWS = frozenset(
    {
        "cdb-context-refresh-report.yml",
        "security-alert-readout.yml",
        "surrealdb-memory-proof.yml",
    }
)


@dataclass(frozen=True)
class WorkflowInventoryFinding:
    kind: str
    detail: str


@dataclass(frozen=True)
class WorkflowInventoryScan:
    disk_workflows: tuple[str, ...]
    register_workflows: tuple[str, ...]
    control_plane_workflows: tuple[str, ...]
    unregistered_on_disk: tuple[str, ...]
    missing_on_disk: tuple[str, ...]
    control_plane_missing_on_disk: tuple[str, ...]
    findings: tuple[WorkflowInventoryFinding, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class WorkflowTriggerPermissionRow:
    filename: str
    triggers: tuple[str, ...]
    write_permissions: tuple[str, ...]
    forbidden_triggers: tuple[str, ...]
    has_explicit_permissions: bool
    has_top_level_permissions: bool
    has_job_level_permissions: bool


def list_workflow_yaml_files(workflows_dir: Path) -> list[str]:
    if not workflows_dir.exists():
        return []
    files = [
        path.name
        for path in workflows_dir.iterdir()
        if path.is_file() and path.suffix in {".yml", ".yaml"}
    ]
    return sorted(files)


def parse_register_table_workflows(register_path: Path) -> list[str]:
    text = register_path.read_text(encoding="utf-8")
    names = re.findall(r"\| `([^`]+\.(?:yml|yaml))` \|", text)
    return sorted(set(names))


def parse_control_plane_register_workflows(register_json_path: Path) -> list[str]:
    payload = json.loads(register_json_path.read_text(encoding="utf-8"))
    units = payload.get("units") or []
    paths: list[str] = []
    for unit in units:
        if not isinstance(unit, dict):
            continue
        workflow_path = unit.get("workflow_path")
        if isinstance(workflow_path, str) and workflow_path.strip():
            paths.append(workflow_path.rsplit("/", 1)[-1])
    return sorted(set(paths))


def load_workflow_yaml(workflow_path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Workflow YAML must be a mapping: {workflow_path}")
    return payload


def extract_on_triggers(workflow: dict[str, Any]) -> set[str]:
    on_section = workflow.get("on") or workflow.get(True)
    if on_section is None:
        return set()
    if isinstance(on_section, str):
        return {on_section}
    if isinstance(on_section, list):
        return {str(item) for item in on_section}
    if isinstance(on_section, dict):
        return {str(key) for key in on_section}
    return set()


def extract_top_level_permissions(workflow: dict[str, Any]) -> dict[str, str]:
    permissions = workflow.get("permissions")
    if permissions is None:
        return {}
    if permissions == {}:
        return {}
    if not isinstance(permissions, dict):
        return {}
    return {str(key): str(value) for key, value in permissions.items()}


def extract_job_level_permissions(workflow: dict[str, Any]) -> dict[str, str]:
    merged: dict[str, str] = {}
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        return merged
    for job_def in jobs.values():
        if not isinstance(job_def, dict):
            continue
        perms = job_def.get("permissions")
        if not isinstance(perms, dict):
            continue
        for scope, level in perms.items():
            merged[str(scope)] = str(level)
    return merged


def extract_effective_permissions(workflow: dict[str, Any]) -> dict[str, str]:
    effective = dict(extract_top_level_permissions(workflow))
    effective.update(extract_job_level_permissions(workflow))
    return effective


def classify_write_permissions(permissions: dict[str, str]) -> set[str]:
    classified: set[str] = set()
    for scope, level in permissions.items():
        if str(level).lower() != "write":
            continue
        token = f"{scope}:write"
        if token in WRITE_PERMISSION_SCOPES:
            classified.add(token)
    return classified


def build_trigger_permission_row(workflow_path: Path) -> WorkflowTriggerPermissionRow:
    workflow = load_workflow_yaml(workflow_path)
    triggers = tuple(sorted(extract_on_triggers(workflow)))
    top_level = extract_top_level_permissions(workflow)
    job_level = extract_job_level_permissions(workflow)
    effective = extract_effective_permissions(workflow)
    write_permissions = tuple(sorted(classify_write_permissions(effective)))
    forbidden = tuple(sorted(FORBIDDEN_TRIGGERS.intersection(set(triggers))))
    return WorkflowTriggerPermissionRow(
        filename=workflow_path.name,
        triggers=triggers,
        write_permissions=write_permissions,
        forbidden_triggers=forbidden,
        has_explicit_permissions=bool(top_level or job_level),
        has_top_level_permissions=bool(top_level),
        has_job_level_permissions=bool(job_level),
    )


def scan_workflow_inventory(
    *,
    workflows_dir: Path,
    register_md_path: Path,
    control_plane_json_path: Path,
) -> WorkflowInventoryScan:
    disk = tuple(list_workflow_yaml_files(workflows_dir))
    register = tuple(parse_register_table_workflows(register_md_path))
    control_plane = tuple(parse_control_plane_register_workflows(control_plane_json_path))

    disk_set = set(disk)
    register_set = set(register)
    control_plane_set = set(control_plane)

    unregistered = tuple(sorted(disk_set - register_set))
    missing_on_disk = tuple(sorted(register_set - disk_set))
    cp_missing = tuple(sorted(control_plane_set - disk_set))

    findings: list[WorkflowInventoryFinding] = []
    for name in unregistered:
        findings.append(
            WorkflowInventoryFinding(
                kind="unregistered_workflow",
                detail=f"{name} exists on disk but is missing from GITHUB_WORKFLOW_REGISTER.md",
            )
        )
    for name in missing_on_disk:
        findings.append(
            WorkflowInventoryFinding(
                kind="register_missing_file",
                detail=f"{name} is listed in GITHUB_WORKFLOW_REGISTER.md but missing on disk",
            )
        )
    for name in cp_missing:
        findings.append(
            WorkflowInventoryFinding(
                kind="control_plane_missing_file",
                detail=(
                    f"{name} is listed in workflow-register.json but missing on disk"
                ),
            )
        )

    return WorkflowInventoryScan(
        disk_workflows=disk,
        register_workflows=register,
        control_plane_workflows=control_plane,
        unregistered_on_disk=unregistered,
        missing_on_disk=missing_on_disk,
        control_plane_missing_on_disk=cp_missing,
        findings=tuple(findings),
    )


REGISTER_STATUS_TOKENS = frozenset(
    {
        "aktiv",
        "manual-only",
        "parked",
        "historisch",
        "**parked**",
    }
)


def parse_register_status_map(register_path: Path) -> dict[str, str]:
    text = register_path.read_text(encoding="utf-8")
    status_map: dict[str, str] = {}
    for line in text.splitlines():
        if not line.startswith("| `") or line.count("|") < 3:
            continue
        cols = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(cols) < 2:
            continue
        filename = cols[0].strip("`")
        if not filename.endswith((".yml", ".yaml")):
            continue
        status = cols[1].lower()
        if status not in {token.lower() for token in REGISTER_STATUS_TOKENS}:
            continue
        status_map[filename] = status
    return status_map


def workflow_has_only_dispatch_trigger(workflow_path: Path) -> bool:
    workflow = load_workflow_yaml(workflow_path)
    triggers = extract_on_triggers(workflow)
    return triggers == {"workflow_dispatch"}


def workflow_declares_forbidden_trigger(workflow_path: Path) -> list[str]:
    workflow = load_workflow_yaml(workflow_path)
    triggers = extract_on_triggers(workflow)
    return sorted(FORBIDDEN_TRIGGERS.intersection(triggers))


def load_required_checks_baseline(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    contexts = payload.get("contexts") or []
    return sorted(
        {
            str(ctx).strip()
            for ctx in contexts
            if isinstance(ctx, str) and str(ctx).strip()
        }
    )
