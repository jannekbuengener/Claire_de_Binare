#!/usr/bin/env python3
"""
Read-only planning lint for live-readiness phase and issue drift.

This checker keeps the canonical planning files aligned without introducing a
new governance framework:
- `ROADMAP.yaml` remains the phase-order source of truth.
- `LR-TASKS.yaml` entries with explicit phase prefixes must be mapped in the
  matching roadmap phase.
- `ISSUES.md` stays a derived planning index, not a parallel task-status file.

Exit codes:
- 0: no drift
- 2: drift detected
- 1: execution error
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path("docs/live-readiness")
ROADMAP_PATH = ROOT / "ROADMAP.yaml"
TASKS_PATH = ROOT / "LR-TASKS.yaml"
ISSUES_PATH = ROOT / "ISSUES.md"
PHASE_PREFIX_RE = re.compile(r"^(P\d+)\b")
ISSUE_ID_RE = re.compile(r"LR-\d{3}")


def load_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path.as_posix()}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path.as_posix()}")
    return payload


def require_markers(path: Path, markers: list[str]) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path.as_posix()}")
    text = path.read_text(encoding="utf-8")
    missing = [marker for marker in markers if marker not in text]
    return [f"{path.as_posix()}: missing marker {marker!r}" for marker in missing]


def roadmap_issue_contract(
    roadmap: dict,
) -> tuple[list[str], dict[str, list[str]], list[str]]:
    failures: list[str] = []
    issue_order: list[str] = []
    issue_membership: dict[str, list[str]] = {}

    phases = roadmap.get("phases")
    if not isinstance(phases, list):
        return [], {}, ["docs/live-readiness/ROADMAP.yaml: phases must be a list"]

    seen_phase_ids: set[str] = set()
    previous_phase_num: int | None = None

    for index, phase in enumerate(phases):
        if not isinstance(phase, dict):
            failures.append(
                f"docs/live-readiness/ROADMAP.yaml: phase entry at index {index} is not a mapping"
            )
            continue

        phase_id = phase.get("id")
        issues = phase.get("issues")

        if not isinstance(phase_id, str) or not re.fullmatch(r"P\d+", phase_id):
            failures.append(
                "docs/live-readiness/ROADMAP.yaml: phase id must match P<digits> "
                f"(index {index}, found {phase_id!r})"
            )
            continue

        if phase_id in seen_phase_ids:
            failures.append(
                f"docs/live-readiness/ROADMAP.yaml: duplicate phase id {phase_id!r}"
            )
        seen_phase_ids.add(phase_id)

        phase_num = int(phase_id[1:])
        if previous_phase_num is not None and phase_num <= previous_phase_num:
            failures.append(
                "docs/live-readiness/ROADMAP.yaml: phases must be in ascending order "
                f"(found {phase_id} after P{previous_phase_num})"
            )
        previous_phase_num = phase_num

        if not isinstance(issues, list):
            failures.append(
                f"docs/live-readiness/ROADMAP.yaml: {phase_id}.issues must be a list"
            )
            continue

        for issue in issues:
            if not isinstance(issue, str) or not ISSUE_ID_RE.fullmatch(issue):
                failures.append(
                    "docs/live-readiness/ROADMAP.yaml: issue ids must match LR-NNN "
                    f"(phase {phase_id}, found {issue!r})"
                )
                continue
            issue_order.append(issue)
            issue_membership.setdefault(issue, []).append(phase_id)

    for issue_id, phase_ids in issue_membership.items():
        if len(phase_ids) > 1:
            failures.append(
                "docs/live-readiness/ROADMAP.yaml: issue appears in multiple phases "
                f"({issue_id}: {phase_ids})"
            )

    return issue_order, issue_membership, failures


def explicit_phase_tasks(tasks_manifest: dict) -> tuple[dict[str, str], list[str]]:
    failures: list[str] = []
    mapping: dict[str, str] = {}

    tasks = tasks_manifest.get("tasks")
    if not isinstance(tasks, list):
        return {}, ["docs/live-readiness/LR-TASKS.yaml: tasks must be a list"]

    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            failures.append(
                f"docs/live-readiness/LR-TASKS.yaml: task entry at index {index} is not a mapping"
            )
            continue

        task_id = task.get("task_id")
        task_title = task.get("task_title")
        if not isinstance(task_id, str) or not ISSUE_ID_RE.fullmatch(task_id):
            failures.append(
                "docs/live-readiness/LR-TASKS.yaml: task_id must match LR-NNN "
                f"(index {index}, found {task_id!r})"
            )
            continue
        if not isinstance(task_title, str):
            failures.append(
                f"docs/live-readiness/LR-TASKS.yaml: task_title must be a string for {task_id}"
            )
            continue

        match = PHASE_PREFIX_RE.match(task_title)
        if match:
            mapping[task_id] = match.group(1)

    return mapping, failures


def issues_index(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path.as_posix()}")
    text = path.read_text(encoding="utf-8")
    return ISSUE_ID_RE.findall(text)


def lint(
    roadmap_path: Path = ROADMAP_PATH,
    tasks_path: Path = TASKS_PATH,
    issues_path: Path = ISSUES_PATH,
) -> list[str]:
    roadmap = load_yaml(roadmap_path)
    tasks_manifest = load_yaml(tasks_path)

    roadmap_order, roadmap_membership, failures = roadmap_issue_contract(roadmap)
    explicit_tasks, task_failures = explicit_phase_tasks(tasks_manifest)
    failures.extend(task_failures)

    for task_id, expected_phase in explicit_tasks.items():
        actual_phases = roadmap_membership.get(task_id, [])
        if actual_phases != [expected_phase]:
            failures.append(
                f"{roadmap_path.as_posix()}: {task_id} has explicit phase {expected_phase} "
                f"in LR-TASKS.yaml but roadmap membership is {actual_phases or 'missing'}"
            )

    failures.extend(
        require_markers(
            issues_path,
            [
                "Derived planning index only.",
                "ROADMAP.yaml",
                "LR-TASKS.yaml",
                "LR-*-STATE.yaml",
            ],
        )
    )

    issue_index = issues_index(issues_path)
    if issue_index != roadmap_order:
        failures.append(
            f"{issues_path.as_posix()}: roadmap-derived issue order drift "
            f"(expected {roadmap_order}, found {issue_index})"
        )

    return failures


def main() -> int:
    failures = lint()
    if failures:
        print("Live-readiness planning lint detected drift:")
        for failure in failures:
            print(f"- {failure}")
        return 2

    print(
        "Live-readiness planning lint OK: "
        f"{ROADMAP_PATH.as_posix()}, {TASKS_PATH.as_posix()}, {ISSUES_PATH.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
