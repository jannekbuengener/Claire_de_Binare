from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

from tools.arvp_probe_layer import (
    probe_candles,
    probe_db_readonly,
    probe_docker,
    probe_host,
    probe_ledger,
    probe_regime,
    probe_safety,
)

logger = logging.getLogger(__name__)

EXIT_INVALID_USAGE = 2
EXIT_OK = 0
EXIT_CHAIN_FOUND = 10
EXIT_TIMEOUT_NO_CHAIN = 20
EXIT_INTERRUPTED = 30
EXIT_BLOCKED_RUNTIME = 40
EXIT_BLOCKED_DB_READONLY = 41
EXIT_BLOCKED_GOVERNANCE = 42

STATE_RUNNING = "CAMPAIGN_RUNNING"
STATE_CHAIN_FOUND = "CHAIN_FOUND"
STATE_TIMEOUT_NO_CHAIN = "TIMEOUT_NO_CHAIN"
STATE_INTERRUPTED = "INTERRUPTED"
STATE_BLOCKED_RUNTIME = "BLOCKED_RUNTIME"
STATE_BLOCKED_DB_READONLY = "BLOCKED_DB_READONLY"
STATE_BLOCKED_GOVERNANCE = "BLOCKED_GOVERNANCE"

EXIT_CODE_MAP: dict[str, int] = {
    STATE_RUNNING: EXIT_OK,
    STATE_CHAIN_FOUND: EXIT_CHAIN_FOUND,
    STATE_TIMEOUT_NO_CHAIN: EXIT_TIMEOUT_NO_CHAIN,
    STATE_INTERRUPTED: EXIT_INTERRUPTED,
    STATE_BLOCKED_RUNTIME: EXIT_BLOCKED_RUNTIME,
    STATE_BLOCKED_DB_READONLY: EXIT_BLOCKED_DB_READONLY,
    STATE_BLOCKED_GOVERNANCE: EXIT_BLOCKED_GOVERNANCE,
}

REQUIRED_MANIFEST_FIELDS = [
    "schema_version",
    "campaign_id",
    "parent_issue",
    "related_issues",
    "symbol",
    "strategy_id",
    "evidence_class",
    "start_utc",
    "timeout_utc",
    "max_duration_hours",
    "start_criteria",
    "safety_flags",
    "runtime_targets",
    "db_readonly_targets",
    "evidence_doc",
    "evidence_log_jsonl",
    "github_reporting",
    "allowed_statuses",
    "terminal_statuses",
]


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def load_manifest(path: str) -> dict[str, Any]:
    if not os.path.isfile(path):
        raise ValueError(f"manifest file not found: {path}")

    raw: dict[str, Any] | None = None

    if path.endswith((".yaml", ".yml")):
        import yaml

        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    else:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)

    if not isinstance(raw, dict):
        raise ValueError("manifest must be a JSON/YAML object")

    missing = [f for f in REQUIRED_MANIFEST_FIELDS if f not in raw]
    if missing:
        raise ValueError(f"manifest missing required fields: {', '.join(missing)}")

    if raw["schema_version"] != "1.0":
        raise ValueError(f"unsupported schema_version: {raw['schema_version']}")

    return raw


def run_all_probes(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    start_utc = manifest.get("start_utc")
    results: list[dict[str, Any]] = []

    results.append({"probe": "host", **probe_host()})
    results.append(
        {
            "probe": "docker",
            **probe_docker(targets=manifest.get("runtime_targets")),
        }
    )
    results.append({"probe": "safety", **probe_safety()})
    results.append({"probe": "db_readonly", **probe_db_readonly()})
    results.append({"probe": "candles", **probe_candles()})
    results.append(
        {
            "probe": "correlation_ledger",
            **probe_ledger(campaign_start_utc=start_utc),
        }
    )
    results.append({"probe": "regime", **probe_regime()})

    return results


def _find_probe(probes: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for p in probes:
        if p.get("probe") == name:
            return p
    return None


def _check_blocked(probes: list[dict[str, Any]], name: str) -> bool:
    p = _find_probe(probes, name)
    return p is not None and p.get("status") in ("blocked",)


def detect_chain(probes: list[dict[str, Any]]) -> bool:
    ledger = _find_probe(probes, "correlation_ledger")
    if ledger is None or ledger.get("status") != "ok":
        return False

    evidence = ledger.get("evidence", {})
    events_by_type = evidence.get("events_by_type_status", [])

    found_types: set[str] = set()
    for entry in events_by_type:
        etype = str(entry.get("event_type", "")).upper()
        if etype == "ORDER" or etype.startswith("ORDER("):
            found_types.add("ORDER")
        else:
            found_types.add(etype)

    required = {"SIGNAL", "DECISION", "ORDER", "FILL"}
    return required.issubset(found_types)


def detect_interruption(probes: list[dict[str, Any]]) -> bool:
    host = _find_probe(probes, "host")
    if host is None or host.get("status") != "ok":
        return False

    evidence = host.get("evidence", {})
    indicators = evidence.get("sleep_wake_indicators", [])
    if indicators and not all(i == "none detected" for i in indicators):
        return True

    uptime = evidence.get("uptime_seconds")
    if uptime is not None and uptime < 3600:
        return True

    return False


def evaluate_state(
    probes: list[dict[str, Any]],
    manifest: dict[str, Any],
    cycle_count: int,
) -> str:
    docker_blocked = _check_blocked(probes, "docker")
    safety_blocked = _check_blocked(probes, "safety")

    if docker_blocked or safety_blocked:
        return STATE_BLOCKED_RUNTIME

    db_blocked = _check_blocked(probes, "db_readonly")
    candles_blocked = _check_blocked(probes, "candles")
    ledger_blocked = _check_blocked(probes, "correlation_ledger")

    if db_blocked or candles_blocked or ledger_blocked:
        return STATE_BLOCKED_DB_READONLY

    safety = _find_probe(probes, "safety")
    if safety is not None and safety.get("status") == "blocked":
        return STATE_BLOCKED_GOVERNANCE

    if detect_chain(probes):
        return STATE_CHAIN_FOUND

    if detect_interruption(probes):
        return STATE_INTERRUPTED

    timeout_utc = manifest.get("timeout_utc")
    if timeout_utc:
        try:
            timeout_dt = _parse_utc(timeout_utc)
            now = datetime.now(timezone.utc)
            if now >= timeout_dt:
                return STATE_TIMEOUT_NO_CHAIN
        except (ValueError, TypeError):
            pass

    return STATE_RUNNING


def _build_cycle_entry(
    cycle: int,
    probes: list[dict[str, Any]],
    state: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    ledger = _find_probe(probes, "correlation_ledger")
    event_count = None
    if ledger is not None:
        ev = ledger.get("evidence", {})
        event_count = ev.get("events_since_campaign_start")

    probe_statuses = {p["probe"]: p.get("status") for p in probes}

    return {
        "observed_at_utc": _utcnow(),
        "cycle": cycle,
        "campaign_id": manifest.get("campaign_id"),
        "state": state,
        "probe_statuses": probe_statuses,
        "event_count_since_start": event_count,
        "chain_detected": state == STATE_CHAIN_FOUND,
        "no_mutation": True,
        "limitations": [],
    }


def write_jsonl_entry(path: str, entry: dict[str, Any]) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def write_status_md(path: str, entry: dict[str, Any], manifest: dict[str, Any]) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    safety = manifest.get("safety_flags", {})
    lines = [
        f"# Campaign Status: {manifest.get('campaign_id', 'unknown')}",
        "",
        f"**Observed at (UTC):** {entry['observed_at_utc']}",
        f"**Cycle:** {entry['cycle']}",
        f"**State:** {entry['state']}",
        "",
        "## Probe Statuses",
    ]
    for probe_name, status in entry.get("probe_statuses", {}).items():
        lines.append(f"- **{probe_name}:** {status}")
    lines += [
        "",
        "## Campaign Info",
        f"- **Symbol:** {manifest.get('symbol', '-')}",
        f"- **Strategy:** {manifest.get('strategy_id', '-')}",
        f"- **Start (UTC):** {manifest.get('start_utc', '-')}",
        f"- **Timeout (UTC):** {manifest.get('timeout_utc', '-')}",
        f"- **Event count since start:** {entry.get('event_count_since_start', '-')}",
        f"- **Chain detected:** {entry.get('chain_detected', False)}",
        "",
        "## Safety Flags",
    ]
    for flag, val in safety.items():
        lines.append(f"- **{flag}:** {val}")
    lines += [
        "",
        "---",
        f"*no_mutation: {entry.get('no_mutation', True)}*",
        "",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def run_loop(
    manifest: dict[str, Any],
    poll_seconds: int,
    max_cycles: int | None,
    once: bool,
    dry_run: bool,
    output_jsonl: str | None,
    status_md: str | None,
) -> int:
    cycle = 0

    while True:
        cycle += 1
        if max_cycles is not None and cycle > max_cycles:
            break

        probes = run_all_probes(manifest)
        state = evaluate_state(probes, manifest, cycle)

        entry = _build_cycle_entry(cycle, probes, state, manifest)

        if not dry_run:
            if output_jsonl:
                write_jsonl_entry(output_jsonl, entry)
            if status_md:
                write_status_md(status_md, entry, manifest)

        if state != STATE_RUNNING:
            exit_code = EXIT_CODE_MAP.get(state, EXIT_OK)
            print(json.dumps(entry, default=str))
            return exit_code

        if once:
            print(json.dumps(entry, default=str))
            return EXIT_OK

        time.sleep(poll_seconds)

    return EXIT_OK


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ARVP Campaign Supervisor \u2014 CLI Polling Loop"
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to campaign manifest (YAML or JSON)",
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=900,
        help="Polling interval in seconds (default: 900)",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=None,
        help="Maximum number of cycles (for tests)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single cycle and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run probes and evaluate state without writing output files",
    )
    parser.add_argument(
        "--output-jsonl",
        default=None,
        help="Path to append-only JSONL evidence log",
    )
    parser.add_argument(
        "--status-md",
        default=None,
        help="Path to Markdown status snapshot file",
    )

    args = parser.parse_args()

    try:
        manifest = load_manifest(args.manifest)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: invalid manifest: {exc}", file=sys.stderr)
        sys.exit(EXIT_INVALID_USAGE)

    exit_code = run_loop(
        manifest=manifest,
        poll_seconds=args.poll_seconds,
        max_cycles=args.max_cycles,
        once=args.once,
        dry_run=args.dry_run,
        output_jsonl=args.output_jsonl,
        status_md=args.status_md,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
