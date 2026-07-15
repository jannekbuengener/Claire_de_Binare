#!/usr/bin/env python3
"""
Read-only branch protection drift checker for main.

This script never applies settings. It only:
1) loads a versioned baseline,
2) fetches current branch protection state,
3) compares deterministically,
4) writes a drift report and exits with a governance-friendly status code.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]


DEFAULT_REPO = "jannekbuengener/Claire_de_Binare"
DEFAULT_BRANCH = "main"
DEFAULT_BASELINE = Path("docs/evidence/reports/BRANCH_PROTECTION_BASELINE_main.json")
DEFAULT_REPORT = Path(
    "artifacts/reports/governance/BRANCH_PROTECTION_DRIFT_REPORT_main.md"
)
DEFAULT_APPLY_PAYLOAD = Path(
    "artifacts/reports/governance/BRANCH_PROTECTION_APPLY_PAYLOAD_main.json"
)

# There are no volatile fields currently removed from comparison.
VOLATILE_PATHS: set[str] = set()

# These arrays are semantically sets in GitHub branch protection APIs.
UNORDERED_LIST_PATHS = {
    "required_status_checks.contexts",
    "required_status_checks.checks",
    "required_pull_request_reviews.dismissal_restrictions.users",
    "required_pull_request_reviews.dismissal_restrictions.teams",
    "required_pull_request_reviews.dismissal_restrictions.apps",
    "required_pull_request_reviews.bypass_pull_request_allowances.users",
    "required_pull_request_reviews.bypass_pull_request_allowances.teams",
    "required_pull_request_reviews.bypass_pull_request_allowances.apps",
    "restrictions.users",
    "restrictions.teams",
    "restrictions.apps",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only branch protection drift check against a versioned baseline."
    )
    parser.add_argument(
        "--repo", default=DEFAULT_REPO, help="owner/repo, default CDB repo"
    )
    parser.add_argument(
        "--branch", default=DEFAULT_BRANCH, help="branch name, default main"
    )
    parser.add_argument(
        "--baseline",
        default=str(DEFAULT_BASELINE),
        help="baseline JSON path (versioned in repo)",
    )
    parser.add_argument(
        "--current-json",
        default=None,
        help="optional current snapshot JSON file (if omitted, fetches live via gh api)",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT),
        help="markdown drift report output path",
    )
    parser.add_argument(
        "--apply-payload-out",
        default=str(DEFAULT_APPLY_PAYLOAD),
        help="manual apply payload JSON output path (never auto-applied)",
    )
    return parser.parse_args()


def run_gh_api(repo: str, branch: str) -> str:
    target = f"repos/{repo}/branches/{branch}/protection"
    proc = subprocess.run(
        ["gh", "api", target],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "Failed to fetch branch protection via gh api:\n"
            f"{proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc.stdout


def load_json(path: Path) -> tuple[str, Any]:
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    return raw, data


def to_sort_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def normalize(value: Any, path: str = "") -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key in sorted(value.keys()):
            next_path = f"{path}.{key}" if path else key
            if next_path in VOLATILE_PATHS:
                continue
            out[key] = normalize(value[key], next_path)
        return out
    if isinstance(value, list):
        normalized_items = [normalize(item, f"{path}[]") for item in value]
        if path in UNORDERED_LIST_PATHS:
            return sorted(normalized_items, key=to_sort_key)
        return normalized_items
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def collect_drift_paths(baseline: Any, current: Any, path: str = "") -> list[str]:
    here = path or "$"
    if type(baseline) is not type(current):  # noqa: E721
        return [here]

    if isinstance(baseline, dict):
        paths: list[str] = []
        keys = sorted(set(baseline.keys()) | set(current.keys()))
        for key in keys:
            next_path = f"{path}.{key}" if path else key
            if key not in baseline or key not in current:
                paths.append(next_path)
                continue
            paths.extend(collect_drift_paths(baseline[key], current[key], next_path))
        return paths

    if isinstance(baseline, list):
        paths = []
        if len(baseline) != len(current):
            paths.append(f"{here}.length")
        for idx, (left, right) in enumerate(zip(baseline, current)):
            paths.extend(collect_drift_paths(left, right, f"{here}[{idx}]"))
        return paths

    if baseline != current:
        return [here]
    return []


def extract_actor_names(items: Any, kind: str) -> list[str]:
    if not isinstance(items, list):
        return []

    values: list[str] = []
    for item in items:
        if isinstance(item, str):
            values.append(item)
            continue
        if not isinstance(item, dict):
            continue
        if kind == "users":
            candidate = item.get("login") or item.get("name")
        elif kind == "teams":
            candidate = item.get("slug") or item.get("name")
        else:  # apps
            candidate = item.get("slug") or item.get("name")
        if isinstance(candidate, str) and candidate:
            values.append(candidate)
    return sorted(dict.fromkeys(values))


def map_allowances(data: Any) -> dict[str, list[str]]:
    if not isinstance(data, dict):
        return {"users": [], "teams": [], "apps": []}
    return {
        "users": extract_actor_names(data.get("users"), "users"),
        "teams": extract_actor_names(data.get("teams"), "teams"),
        "apps": extract_actor_names(data.get("apps"), "apps"),
    }


def map_required_status_checks(data: Any) -> Any:
    if data is None:
        return None
    if not isinstance(data, dict):
        return None
    mapped: dict[str, Any] = {"strict": bool(data.get("strict", False))}

    checks = data.get("checks")
    if isinstance(checks, list) and checks:
        clean_checks: list[dict[str, Any]] = []
        for check in checks:
            if not isinstance(check, dict):
                continue
            context = check.get("context")
            if not isinstance(context, str) or not context:
                continue
            clean: dict[str, Any] = {"context": context}
            if "app_id" in check and check["app_id"] is not None:
                clean["app_id"] = check["app_id"]
            clean_checks.append(clean)
        mapped["checks"] = sorted(
            clean_checks, key=lambda c: (c.get("context", ""), str(c.get("app_id", "")))
        )
        return mapped

    contexts = data.get("contexts")
    if isinstance(contexts, list):
        mapped["contexts"] = sorted([c for c in contexts if isinstance(c, str)])
    return mapped


def map_required_pull_request_reviews(data: Any) -> Any:
    if data is None:
        return None
    if not isinstance(data, dict):
        return None

    mapped: dict[str, Any] = {
        "dismiss_stale_reviews": bool(data.get("dismiss_stale_reviews", False)),
        "require_code_owner_reviews": bool(
            data.get("require_code_owner_reviews", False)
        ),
        "require_last_push_approval": bool(
            data.get("require_last_push_approval", False)
        ),
        "required_approving_review_count": int(
            data.get("required_approving_review_count", 0)
        ),
    }

    if "dismissal_restrictions" in data:
        mapped["dismissal_restrictions"] = map_allowances(
            data.get("dismissal_restrictions")
        )
    if "bypass_pull_request_allowances" in data:
        mapped["bypass_pull_request_allowances"] = map_allowances(
            data.get("bypass_pull_request_allowances")
        )
    return mapped


def enabled_flag(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(value.get("enabled", False))
    return bool(value)


def build_apply_payload(state: Any) -> dict[str, Any]:
    if not isinstance(state, dict):
        raise ValueError("branch protection state must be a JSON object")

    return {
        "required_status_checks": map_required_status_checks(
            state.get("required_status_checks")
        ),
        "enforce_admins": enabled_flag(state.get("enforce_admins")),
        "required_pull_request_reviews": map_required_pull_request_reviews(
            state.get("required_pull_request_reviews")
        ),
        "restrictions": (
            map_allowances(state.get("restrictions"))
            if state.get("restrictions") is not None
            else None
        ),
        "required_linear_history": enabled_flag(state.get("required_linear_history")),
        "allow_force_pushes": enabled_flag(state.get("allow_force_pushes")),
        "allow_deletions": enabled_flag(state.get("allow_deletions")),
        "block_creations": enabled_flag(state.get("block_creations")),
        "required_conversation_resolution": enabled_flag(
            state.get("required_conversation_resolution")
        ),
        "lock_branch": enabled_flag(state.get("lock_branch")),
        "allow_fork_syncing": enabled_flag(state.get("allow_fork_syncing")),
    }


def get_timestamps() -> tuple[str, str]:
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


def write_report(
    report_path: Path,
    repo: str,
    branch: str,
    baseline_path: Path,
    apply_payload_path: Path,
    baseline_hash: str,
    current_hash: str,
    drift_paths: list[str],
    diff_text: str,
    current_source: str,
    required_signatures_enabled: bool,
) -> None:
    berlin_ts, utc_ts = get_timestamps()
    drift_state = "DRIFT DETECTED" if drift_paths else "NO DRIFT"
    summary_lines = (
        "\n".join([f"- `{p}`" for p in drift_paths[:50]]) if drift_paths else "- none"
    )
    if len(drift_paths) > 50:
        summary_lines += f"\n- ... and {len(drift_paths) - 50} more"

    required_signatures_cmd = (
        f"gh api --method POST repos/{repo}/branches/{branch}/protection/required_signatures"
        if required_signatures_enabled
        else f"gh api --method DELETE repos/{repo}/branches/{branch}/protection/required_signatures"
    )

    report = f"""# Branch Protection Drift Report (main)

Timestamp (Europe/Berlin): `{berlin_ts}`  
Timestamp (UTC): `{utc_ts}`  
Repo: `{repo}`  
Branch: `{branch}`  
State: **{drift_state}**

## Inputs

- Baseline file: `{baseline_path.as_posix()}`
- Current source: `{current_source}`
- Normalization: sorted keys; unordered-list normalization for known set-like arrays; volatile-field stripping: none

## Hashes (SHA256)

- Baseline snapshot hash: `{baseline_hash}`
- Current snapshot hash: `{current_hash}`

## Drift Summary

{summary_lines}

## Unified Diff (normalized JSON)

```diff
{diff_text.rstrip() if diff_text else "(no diff)"}
```

## Manual Apply Commands (maintainer only, never auto-executed)

```bash
gh api repos/{repo}/branches/{branch}/protection > artifacts/reports/governance/BRANCH_PROTECTION_CURRENT_main.json
gh api --method PUT repos/{repo}/branches/{branch}/protection --input {apply_payload_path.as_posix()}
{required_signatures_cmd}
```

Safety note: this checker is read-only and does not run apply commands.
"""
    report_path.write_text(report, encoding="utf-8")


def main() -> int:
    args = parse_args()

    baseline_path = Path(args.baseline)
    report_path = Path(args.report)
    apply_payload_path = Path(args.apply_payload_out)

    if not baseline_path.exists():
        print(f"ERROR: baseline file does not exist: {baseline_path}", file=sys.stderr)
        return 1

    baseline_raw, baseline_data = load_json(baseline_path)
    baseline_norm = normalize(baseline_data)
    baseline_norm_text = canonical_json(baseline_norm)

    if args.current_json:
        current_path = Path(args.current_json)
        if not current_path.exists():
            print(
                f"ERROR: current JSON file does not exist: {current_path}",
                file=sys.stderr,
            )
            return 1
        current_raw, current_data = load_json(current_path)
        current_source = current_path.as_posix()
    else:
        current_raw = run_gh_api(args.repo, args.branch)
        try:
            current_data = json.loads(current_raw)
        except json.JSONDecodeError as exc:
            print(f"ERROR: gh api returned invalid JSON: {exc}", file=sys.stderr)
            return 1
        current_source = "live gh api"

    current_norm = normalize(current_data)
    current_norm_text = canonical_json(current_norm)

    baseline_hash = sha256_text(baseline_norm_text)
    current_hash = sha256_text(current_norm_text)

    diff_text = "".join(
        difflib.unified_diff(
            baseline_norm_text.splitlines(keepends=True),
            current_norm_text.splitlines(keepends=True),
            fromfile="baseline(normalized)",
            tofile="current(normalized)",
        )
    )
    drift_paths = collect_drift_paths(baseline_norm, current_norm)

    apply_payload = build_apply_payload(baseline_data)
    apply_payload_path.write_text(
        json.dumps(apply_payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    signatures_enabled = enabled_flag(
        baseline_data.get("required_signatures", {}).get("enabled", False)
        if isinstance(baseline_data, dict)
        else False
    )
    write_report(
        report_path=report_path,
        repo=args.repo,
        branch=args.branch,
        baseline_path=baseline_path,
        apply_payload_path=apply_payload_path,
        baseline_hash=baseline_hash,
        current_hash=current_hash,
        drift_paths=drift_paths,
        diff_text=diff_text,
        current_source=current_source,
        required_signatures_enabled=signatures_enabled,
    )

    if drift_paths:
        print(f"Drift detected for {len(drift_paths)} field path(s).")
        print(f"Diff report: {report_path.as_posix()}")
        return 2

    print("No drift detected.")
    print(f"Diff report: {report_path.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
