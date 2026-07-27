#!/usr/bin/env python3
"""
Read-only required-check context drift guard.

Compares versioned required contexts baseline (from branch protection) against
contexts derivable from repository workflow job names.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]


DEFAULT_BASELINE = Path(
    "docs/evidence/reports/REQUIRED_CHECK_CONTEXTS_BASELINE_main.json"
)
DEFAULT_WORKFLOWS_DIR = Path(".github/workflows")
DEFAULT_REPORT = Path(
    "artifacts/reports/governance/REQUIRED_CHECK_CONTEXTS_DRIFT_REPORT_main.md"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only drift check for required check contexts on main."
    )
    parser.add_argument(
        "--baseline",
        default=str(DEFAULT_BASELINE),
        help="required-check baseline JSON path",
    )
    parser.add_argument(
        "--workflows-dir",
        default=str(DEFAULT_WORKFLOWS_DIR),
        help="workflow directory to parse",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT),
        help="markdown drift report output path",
    )
    return parser.parse_args()


def _clean_context_list(raw: Any, *, field_name: str) -> list[str]:
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        raise ValueError(f"Baseline field '{field_name}' must be a list")
    return sorted({ctx.strip() for ctx in raw if isinstance(ctx, str) and ctx.strip()})


def load_baseline(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Baseline file not found: {path}")

    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(f"Baseline must be a JSON object: {path}")

    cleaned_contexts = _clean_context_list(
        data.get("contexts", []), field_name="contexts"
    )
    data["contexts"] = cleaned_contexts

    # Optional: Commit Status / external contexts (not workflow job names).
    # Accept either key; normalize onto commit_status_contexts.
    if "commit_status_contexts" in data:
        external_raw = data.get("commit_status_contexts")
        external_field = "commit_status_contexts"
    elif "external_contexts" in data:
        external_raw = data.get("external_contexts")
        external_field = "external_contexts"
    else:
        external_raw = []
        external_field = "commit_status_contexts"
    cleaned_external = _clean_context_list(external_raw, field_name=external_field)
    data["commit_status_contexts"] = cleaned_external
    return data


def _workflow_files(workflows_dir: Path) -> list[Path]:
    if not workflows_dir.exists():
        raise FileNotFoundError(f"Workflows directory not found: {workflows_dir}")

    files = list(workflows_dir.rglob("*.yml")) + list(workflows_dir.rglob("*.yaml"))
    return sorted(files, key=lambda p: p.as_posix())


def derive_context_mapping(
    workflows_dir: Path,
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    mapping: dict[str, list[dict[str, Any]]] = {}
    parse_errors: list[str] = []

    for path in _workflow_files(workflows_dir):
        rel_path = path.as_posix()
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:
            parse_errors.append(f"{rel_path}: {exc}")
            continue

        if not isinstance(payload, dict):
            continue

        workflow_name = payload.get("name")
        if not isinstance(workflow_name, str) or not workflow_name.strip():
            workflow_name = path.stem
        else:
            workflow_name = workflow_name.strip()

        jobs = payload.get("jobs")
        if not isinstance(jobs, dict):
            continue

        for job_id in sorted(jobs.keys()):
            job_cfg = jobs[job_id]
            if not isinstance(job_cfg, dict):
                continue

            raw_name = job_cfg.get("name")
            if isinstance(raw_name, str) and raw_name.strip():
                context_name = raw_name.strip()
                implicit = False
                job_name = raw_name.strip()
            else:
                context_name = str(job_id)
                implicit = True
                job_name = context_name

            entry = {
                "workflow_file": rel_path,
                "workflow_name": workflow_name,
                "job_id": str(job_id),
                "job_name": job_name,
                "implicit": implicit,
            }
            mapping.setdefault(context_name, []).append(entry)

    for context in sorted(mapping.keys()):
        mapping[context] = sorted(
            mapping[context],
            key=lambda e: (
                e["workflow_file"],
                e["job_id"],
                e["job_name"],
                e["workflow_name"],
                e["implicit"],
            ),
        )

    return dict(sorted(mapping.items(), key=lambda kv: kv[0])), parse_errors


def canonical_hash(obj: Any) -> str:
    text = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def now_timestamps() -> tuple[str, str]:
    now_utc = datetime.now(timezone.utc)
    utc_text = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    if ZoneInfo is None:
        berlin_text = utc_text
    else:
        berlin_text = now_utc.astimezone(ZoneInfo("Europe/Berlin")).strftime(
            "%Y-%m-%dT%H:%M:%S%z"
        )
        berlin_text = f"{berlin_text[:-2]}:{berlin_text[-2:]}"
    return berlin_text, utc_text


def _escape_cell(text: str) -> str:
    return text.replace("|", "\\|")


def write_report(
    report_path: Path,
    baseline_path: Path,
    baseline_hash: str,
    current_hash: str,
    required_contexts: list[str],
    derived_contexts: list[str],
    missing_contexts: list[str],
    extra_contexts: list[str],
    commit_status_contexts: list[str],
    mapping: dict[str, list[dict[str, Any]]],
    parse_errors: list[str],
) -> None:
    berlin_ts, utc_ts = now_timestamps()
    commit_status_set = set(commit_status_contexts)

    required_lines = (
        "\n".join(f"- `{ctx}`" for ctx in required_contexts)
        if required_contexts
        else "- none"
    )
    commit_status_lines = (
        "\n".join(f"- `{ctx}`" for ctx in commit_status_contexts)
        if commit_status_contexts
        else "- none"
    )
    missing_lines = (
        "\n".join(f"- `{ctx}`" for ctx in missing_contexts)
        if missing_contexts
        else "- none"
    )
    extra_lines = (
        "\n".join(f"- `{ctx}`" for ctx in extra_contexts)
        if extra_contexts
        else "- none"
    )
    parse_error_lines = (
        "\n".join(f"- `{err}`" for err in parse_errors) if parse_errors else "- none"
    )

    table_lines = [
        "| context | status | workflow_file | job_id | job_name | workflow_name |",
        "|---|---|---|---|---|---|",
    ]
    for context in required_contexts:
        providers = mapping.get(context, [])
        if not providers:
            if context in commit_status_set:
                table_lines.append(
                    f"| `{_escape_cell(context)}` | external/commit-status | n/a | n/a | n/a | n/a |"
                )
            else:
                table_lines.append(
                    f"| `{_escape_cell(context)}` | missing | n/a | n/a | n/a | n/a |"
                )
            continue
        for provider in providers:
            status = "present (implicit)" if provider["implicit"] else "present"
            table_lines.append(
                "| `{context}` | {status} | `{workflow_file}` | `{job_id}` | `{job_name}` | `{workflow_name}` |".format(
                    context=_escape_cell(context),
                    status=status,
                    workflow_file=_escape_cell(provider["workflow_file"]),
                    job_id=_escape_cell(provider["job_id"]),
                    job_name=_escape_cell(provider["job_name"]),
                    workflow_name=_escape_cell(provider["workflow_name"]),
                )
            )

    drift_state = "DRIFT DETECTED" if missing_contexts else "NO DRIFT"
    if missing_contexts:
        what_to_do = (
            "Do NOT rename `job.name` for required contexts; revert the rename "
            "or update branch protection manually. Commit-status / external "
            "contexts listed in the baseline are exempt from workflow mapping."
        )
    elif commit_status_contexts and not any(
        ctx in mapping for ctx in required_contexts if ctx not in commit_status_set
    ):
        what_to_do = (
            "Required contexts are covered by Commit Status / external contexts "
            "and/or workflow job names. Keep publisher and branch-protection "
            "names aligned for commit-status contexts."
        )
    else:
        what_to_do = (
            "Required contexts are currently derivable from workflow job names "
            "or declared as commit-status/external. Keep job-name stability for "
            "workflow-backed required contexts."
        )

    report = f"""# Required Check Contexts Drift Report (main)

Timestamp (Europe/Berlin): `{berlin_ts}`  
Timestamp (UTC): `{utc_ts}`  
State: **{drift_state}**

## Hashes (SHA256)

- Baseline SHA256: `{baseline_hash}`
- Current-derived SHA256: `{current_hash}`

## Inputs

- Baseline file: `{baseline_path.as_posix()}`
- Workflows source: `.github/workflows/**` (read-only parse)

## Required Contexts (Baseline)

{required_lines}

## Commit Status / External Contexts (not workflow jobs)

{commit_status_lines}

## Missing Required Contexts

{missing_lines}

## Extra Derivable Contexts (Informational)

{extra_lines}

## Mapping (required context -> workflow file / job id)

{chr(10).join(table_lines)}

## Parse Errors

{parse_error_lines}

## What To Do

- {what_to_do}
"""
    report_path.write_text(report, encoding="utf-8")


def main() -> int:
    args = parse_args()

    baseline_path = Path(args.baseline)
    workflows_dir = Path(args.workflows_dir)
    report_path = Path(args.report)

    baseline = load_baseline(baseline_path)
    required_contexts = baseline["contexts"]
    commit_status_contexts = baseline.get("commit_status_contexts") or []
    commit_status_set = set(commit_status_contexts)

    mapping, parse_errors = derive_context_mapping(workflows_dir)
    derived_contexts = sorted(mapping.keys())

    # Commit-status / external contexts are required via Branch Protection but
    # are not workflow job names — do not treat them as Missing.
    missing_contexts = sorted(
        [
            ctx
            for ctx in required_contexts
            if ctx not in mapping and ctx not in commit_status_set
        ]
    )
    extra_contexts = sorted(
        [ctx for ctx in derived_contexts if ctx not in required_contexts]
    )

    baseline_hash = canonical_hash(
        {
            "contexts": required_contexts,
            "commit_status_contexts": commit_status_contexts,
        }
    )
    current_hash = canonical_hash({"contexts": derived_contexts, "mapping": mapping})

    write_report(
        report_path=report_path,
        baseline_path=baseline_path,
        baseline_hash=baseline_hash,
        current_hash=current_hash,
        required_contexts=required_contexts,
        derived_contexts=derived_contexts,
        missing_contexts=missing_contexts,
        extra_contexts=extra_contexts,
        commit_status_contexts=commit_status_contexts,
        mapping=mapping,
        parse_errors=parse_errors,
    )

    print(
        "Required contexts: {req} | Derived contexts: {drv} | Missing: {miss} | Extra: {extra}".format(
            req=len(required_contexts),
            drv=len(derived_contexts),
            miss=len(missing_contexts),
            extra=len(extra_contexts),
        )
    )
    print(f"Drift report: {report_path.as_posix()}")

    if missing_contexts:
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON input: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
