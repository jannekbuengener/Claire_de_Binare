"""Campaign-to-PR Orchestrator v1 (#4366).

Fail-closed path from COMPLETED (or slim closeout) → PR-safe prepared inputs.
Never creates GitHub PRs/branches. Never stages raw ``runs/`` trees.
LR=NO-GO.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence, TextIO

from core.replay.canonical_json import canonical_hash
from core.utils.clock import utcnow as cdb_utcnow

from tools.arvp_vacation.sensitivity_campaign_state import (
    CAMPAIGN_ENVELOPE_NAME,
    CAMPAIGN_PHASE_COMPLETED,
    read_campaign_phase,
    read_json,
)

ORCHESTRATOR_SCHEMA = "cdb.sensitivity_campaign_to_pr_orchestrator.v1"
HANDOFF_SCHEMA = "cdb.sensitivity_campaign_to_pr_delivery_handoff.v1"
CONTRACT_DOC = "docs/strategy/CDB_SENSITIVITY_CAMPAIGN_TO_PR_ORCHESTRATOR_V1.md"
HANDOFF_CONTRACT_DOC = (
    "docs/strategy/CDB_SENSITIVITY_CAMPAIGN_TO_PR_DELIVERY_HANDOFF_V1.md"
)
HANDOFF_FILENAME = "delivery_handoff.json"
DEFAULT_HANDOFF_SUBDIR = "campaign_to_pr"

CLASSIFICATIONS = frozenset({"PROMISING", "INCONCLUSIVE", "REJECTED", "BLOCKED"})

VERDICT_DRY_RUN_PASS = "ORCHESTRATOR_DRY_RUN_PASS"
VERDICT_PREPARE_PASS = "ORCHESTRATOR_PREPARE_PASS"
HANDOFF_READY = "HANDOFF_READY_FOR_EXTERNAL_PR_WRITE"
VERDICT_PR_READY = "PR_READY"
HOLD_PHASE = "HOLD_CAMPAIGN_PHASE_NOT_COMPLETED"
HOLD_CLASS_MISSING = "HOLD_CLASSIFICATION_MISSING"
HOLD_CLASS_INVALID = "HOLD_CLASSIFICATION_INVALID"
HOLD_BINDING = "HOLD_BINDING_MISMATCH"
HOLD_ANALYSIS = "HOLD_ANALYSIS_MISSING"
HOLD_RAW = "HOLD_RAW_RUN_TREE_REJECT"
HOLD_TOKEN = "HOLD_FORBIDDEN_TOKEN"
HOLD_ABS_PATH = "HOLD_ABSOLUTE_PATH_LEAK"
HOLD_HANDOFF_MISSING = "HOLD_HANDOFF_MISSING"
HOLD_OBSERVED = "HOLD_OBSERVED_FACTS_INVALID"
HOLD_BRANCH = "HOLD_BRANCH_MISMATCH"
HOLD_HEAD_PR = "HOLD_HEAD_PR_MISMATCH"
HOLD_FP = "HOLD_EVIDENCE_FINGERPRINT_MISMATCH"
HOLD_PATHS = "HOLD_COMMIT_PATHS_INCOMPLETE"
HOLD_FORBIDDEN_PATH = "HOLD_FORBIDDEN_PATH_IN_COMMIT"
HOLD_ANALYSIS_UNVERIFIED = "HOLD_ANALYSIS_UNVERIFIED"

FORBIDDEN_HANDOFF_ACTIONS = (
    "gh_pr_create",
    "gh_pr_merge",
    "cdb_local_ci_publish",
    "admin_merge",
)
_SHA40_RE = re.compile(r"^[0-9a-f]{40}$")

SLIM_ALLOWLIST: tuple[str, ...] = (
    "CLOSEOUT_CARD.md",
    "primary_evidence_inventory.json",
    "analysis/classification_report.json",
    "analysis/analysis_envelope.json",
    "analysis/analysis_report.md",
    "analysis/campaign_input_inventory.json",
    "analysis/main_effects.json",
    "analysis/interaction_effects.json",
    "analysis/reproduction_summary.json",
)

REQUIRED_ANALYSIS = (
    "analysis/classification_report.json",
    "analysis/analysis_envelope.json",
)

FORBIDDEN_TOKEN_RE = re.compile(
    r"(?i)\b("
    r"stage[\s_-]*b|out[\s_-]*of[\s_-]*sample|\boos\b|stress[\s_-]*test|"
    r"paper[\s_-]*trading|live[\s_-]*go|echtgeld|strategy[\s_-]*promotion|"
    r"lr[\s_-]*go|--admin"
    r")\b"
)

_ABS_PATH_RE = re.compile(r"(?i)(^[A-Za-z]:\\|/Users/|/home/|\\\\)")


class CampaignToPrError(ValueError):
    def __init__(self, reason_code: str, detail: str = "") -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {detail}" if detail else reason_code)


@dataclass(frozen=True)
class BindingPins:
    manifest_fingerprint: str | None = None
    run_plan_fingerprint: str | None = None
    authorization_fingerprint: str | None = None
    bound_main_sha: str | None = None


def _utcnow_iso() -> str:
    now = cdb_utcnow()
    return now.astimezone(now.tzinfo).isoformat().replace("+00:00", "Z")


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    body = read_json(path)
    if not isinstance(body, dict):
        raise CampaignToPrError(HOLD_ANALYSIS, f"non-object json: {path}")
    return body


def _inventory_path(evidence_root: Path) -> Path:
    return Path(evidence_root) / "primary_evidence_inventory.json"


def _classification_path(evidence_root: Path) -> Path:
    return Path(evidence_root) / "analysis" / "classification_report.json"


def _closeout_card_path(evidence_root: Path) -> Path:
    return Path(evidence_root) / "CLOSEOUT_CARD.md"


def is_slim_closeout_package(evidence_root: Path) -> bool:
    root = Path(evidence_root)
    return (
        _inventory_path(root).is_file()
        and _classification_path(root).is_file()
        and _closeout_card_path(root).is_file()
        and not (root / "runs").exists()
    )


def resolve_source_mode(evidence_root: Path) -> str:
    """Return ``completed_namespace`` or ``slim_closeout`` or raise HOLD."""
    root = Path(evidence_root)
    envelope = root / CAMPAIGN_ENVELOPE_NAME
    if envelope.is_file():
        phase = read_campaign_phase(root)
        if phase == CAMPAIGN_PHASE_COMPLETED:
            return "completed_namespace"
        if is_slim_closeout_package(root):
            return "slim_closeout"
        raise CampaignToPrError(
            HOLD_PHASE,
            f"campaign_phase={phase!r}; need COMPLETED or slim closeout package",
        )
    if is_slim_closeout_package(root):
        return "slim_closeout"
    raise CampaignToPrError(
        HOLD_PHASE,
        "missing campaign_envelope.json and not a slim closeout package",
    )


def load_inventory(evidence_root: Path) -> dict[str, Any]:
    path = _inventory_path(evidence_root)
    if not path.is_file():
        raise CampaignToPrError(
            HOLD_ANALYSIS, "primary_evidence_inventory.json missing"
        )
    return _load_json(path)


def load_classification(evidence_root: Path) -> dict[str, Any]:
    path = _classification_path(evidence_root)
    if not path.is_file():
        raise CampaignToPrError(HOLD_CLASS_MISSING, str(path))
    body = _load_json(path)
    classification = str(body.get("classification") or "").strip()
    if not classification:
        raise CampaignToPrError(HOLD_CLASS_MISSING, "classification field empty")
    if classification not in CLASSIFICATIONS:
        raise CampaignToPrError(HOLD_CLASS_INVALID, classification)
    lr = str(body.get("lr_status") or "").strip()
    no_promo = bool(body.get("no_automatic_promotion"))
    if lr and lr != "NO-GO" and not no_promo:
        raise CampaignToPrError(
            HOLD_TOKEN,
            f"classification lr_status={lr!r} without no_automatic_promotion",
        )
    return body


def assert_required_analysis(evidence_root: Path) -> list[str]:
    root = Path(evidence_root)
    missing: list[str] = []
    for rel in REQUIRED_ANALYSIS:
        if not (root / rel).is_file():
            missing.append(rel)
    if missing:
        raise CampaignToPrError(HOLD_ANALYSIS, ",".join(missing))
    present = [rel for rel in SLIM_ALLOWLIST if (root / rel).is_file()]
    return present


def assert_bindings(inventory: Mapping[str, Any], pins: BindingPins) -> None:
    checks = (
        ("manifest_fingerprint", pins.manifest_fingerprint),
        ("run_plan_fingerprint", pins.run_plan_fingerprint),
        ("authorization_fingerprint", pins.authorization_fingerprint),
        ("bound_main_sha", pins.bound_main_sha),
    )
    for key, expected in checks:
        if expected is None:
            continue
        observed = str(inventory.get(key) or "").strip()
        if observed != expected:
            raise CampaignToPrError(
                HOLD_BINDING, f"{key}: expected={expected} observed={observed}"
            )


def assert_no_raw_run_staging(candidate_paths: Sequence[str]) -> None:
    for rel in candidate_paths:
        norm = rel.replace("\\", "/").lstrip("./")
        if norm == "runs" or norm.startswith("runs/"):
            raise CampaignToPrError(HOLD_RAW, norm)


def redact_inventory_for_commit(inventory: Mapping[str, Any]) -> dict[str, Any]:
    """Copy inventory and force repo-relative evidence namespace when absolute."""
    out = dict(inventory)
    ns = str(out.get("allowed_evidence_namespace") or "")
    if _ABS_PATH_RE.search(ns) or ":\\" in ns or ns.startswith("\\\\"):
        # Prefer trailing artifacts/... segment when present.
        marker = "artifacts/"
        idx = ns.replace("\\", "/").find(marker)
        if idx >= 0:
            out["allowed_evidence_namespace"] = ns.replace("\\", "/")[idx:]
        else:
            raise CampaignToPrError(
                HOLD_ABS_PATH,
                "allowed_evidence_namespace is absolute and cannot be redacted",
            )
        out["path_redaction"] = "repo_relative_artifacts_prefix"
    return out


def scan_text_for_forbidden_tokens(text: str, *, context: str) -> None:
    """Fail closed on affirmative Stage-B/Live/promotion claims.

    Negative documentation (Non-goals / \"No Stage-B\") is allowed.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        if lower.startswith(
            ("- no ", "* no ", "- not ", "* not ", "no ", "not ", "never ")
        ):
            continue
        if any(
            marker in lower
            for marker in (
                "non-claim",
                "non-goals",
                "forbidden",
                "banned",
                "explicit non-claims",
                "remains no-go",
                "lr: `no-go`",
                "lr: no-go",
                "lr remains",
            )
        ):
            continue
        if not FORBIDDEN_TOKEN_RE.search(stripped):
            continue
        if re.search(r"(?i)\b(no|not|never|ohne|kein|ban)\b", stripped):
            continue
        raise CampaignToPrError(HOLD_TOKEN, f"{context}: {stripped[:120]}")


def build_closeout_card(
    *,
    classification: str,
    source_mode: str,
    inventory: Mapping[str, Any],
    issue_number: int,
) -> str:
    return (
        f"# Campaign-to-PR Orchestrator Closeout (#{issue_number})\n\n"
        f"- schema: `{ORCHESTRATOR_SCHEMA}`\n"
        f"- source_mode: `{source_mode}`\n"
        f"- classification: `{classification}`\n"
        f"- campaign_id: `{inventory.get('campaign_id')}`\n"
        f"- inventory_fingerprint: `{inventory.get('inventory_fingerprint')}`\n"
        f"- run_key_digest: `{inventory.get('run_key_digest')}`\n"
        f"- bound_main_sha: `{inventory.get('bound_main_sha')}`\n"
        f"- lr_status: `NO-GO`\n"
        f"- no_automatic_promotion: true\n\n"
        "## Explicit non-claims\n\n"
        "- No Stage-B / OOS / Stress / Paper / Live / Echtgeld\n"
        "- No strategy promotion / LR Go\n"
        "- Raw `runs/` trees are not packaged\n"
        "- This orchestrator does not create GitHub PRs by itself\n"
    )


def build_batch_pr_body(
    *,
    issue_number: int,
    commit_sha: str,
    classification: str,
    output_rel: str,
    batch_key: str = "validation-research",
    lane: str = "validation-research",
    validation_profile: str = "validation-research-v1",
    objective_key: str | None = None,
    contract_key: str = "validation-research-v1",
) -> str:
    objective = objective_key or f"issue-{issue_number}"
    sha = commit_sha if re.fullmatch(r"[0-9a-f]{40}", commit_sha) else ("0" * 40)
    return f"""<!-- cdb-batch-pr:v1
policy_id: cdb-pr-routing-v1
batch_key: {batch_key}
lane: {lane}
base_branch: main
validation_profile: {validation_profile}
merge_mode: batch
steward_state: accepting_slices
objective_key: {objective}
planned_issues: #{issue_number}
contract_keys: {contract_key}
risk_flags: none
-->

## Summary

- Campaign-to-PR Orchestrator v1 (`{ORCHESTRATOR_SCHEMA}`)
- Verified classification `{classification}` and slim evidence package
- Prepared PR inputs only (no auto PR create / no merge)

## Delivered

- Contract: `{CONTRACT_DOC}`
- Slim package path (repo-relative intent): `{output_rel}`
- CLI: `python -m tools.arvp_vacation.sensitivity_campaign_to_pr`

## Test plan

- [x] unit tests for HOLD paths + happy-path package shape
- [ ] dry-run against slim closeout fixture (operator)

## Non-goals

- No Stage-B / OOS / Stress / Paper / Live / Echtgeld
- No raw `runs/` trees committed
- No strategy promotion / LR Go
- No `cdb-local-ci` publish / merge in this slice

## Remaining uncertainty

- GitHub PR create remains a separate Plan-GO step after `cdb-pr-router`

## CDB Batch Ledger

| Issue | Status | Commit | Targeted Validation | Risk Class | Restunsicherheit |
| --- | --- | --- | --- | --- | --- |
| #{issue_number} | SLICE_DELIVERED | {sha} | unit arvp orchestrator | validation-research | no auto PR create |

Closes #{issue_number}

Refs #{issue_number}
"""


def write_slim_package(
    *,
    evidence_root: Path,
    output_dir: Path,
    inventory: Mapping[str, Any],
    source_mode: str,
    classification: str,
    issue_number: int,
    present_rels: Sequence[str],
) -> list[str]:
    root = Path(evidence_root)
    out = Path(output_dir)
    if out.exists() and any(out.iterdir()):
        raise CampaignToPrError(HOLD_RAW, f"output_dir not empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    assert_no_raw_run_staging(present_rels)

    redacted = redact_inventory_for_commit(inventory)
    inv_path = out / "primary_evidence_inventory.json"
    inv_path.write_text(
        json.dumps(redacted, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    written.append("primary_evidence_inventory.json")

    for rel in present_rels:
        if rel == "primary_evidence_inventory.json":
            continue
        if rel == "CLOSEOUT_CARD.md":
            continue
        src = root / rel
        if not src.is_file():
            continue
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        written.append(rel)

    card = build_closeout_card(
        classification=classification,
        source_mode=source_mode,
        inventory=redacted,
        issue_number=issue_number,
    )
    scan_text_for_forbidden_tokens(card, context="CLOSEOUT_CARD.md")
    (out / "CLOSEOUT_CARD.md").write_text(card, encoding="utf-8")
    if "CLOSEOUT_CARD.md" not in written:
        written.append("CLOSEOUT_CARD.md")

    assert_no_raw_run_staging(written)
    if (out / "runs").exists():
        raise CampaignToPrError(HOLD_RAW, "output contains runs/")
    return sorted(set(written))


def run_orchestrator(
    *,
    evidence_root: Path,
    mode: str,
    output_dir: Path | None = None,
    pins: BindingPins | None = None,
    issue_number: int = 4366,
    batch_key: str = "validation-research",
    commit_sha: str = "0" * 40,
    output_rel: str = "docs/evidence/arvp/campaign-to-pr/",
) -> dict[str, Any]:
    """Execute dry-run or prepare-pr-inputs. Raises CampaignToPrError on HOLD."""
    root = Path(evidence_root)
    pins = pins or BindingPins()
    source_mode = resolve_source_mode(root)
    inventory = load_inventory(root)
    assert_bindings(inventory, pins)
    classification_body = load_classification(root)
    classification = str(classification_body["classification"])
    present = assert_required_analysis(root)
    # Prefer existing allowlisted files; inventory always required.
    if "primary_evidence_inventory.json" not in present:
        present.append("primary_evidence_inventory.json")
    if _closeout_card_path(root).is_file() and "CLOSEOUT_CARD.md" not in present:
        present.append("CLOSEOUT_CARD.md")
    assert_no_raw_run_staging(present)

    report: dict[str, Any] = {
        "schema_version": ORCHESTRATOR_SCHEMA,
        "mode": mode,
        "source_mode": source_mode,
        "classification": classification,
        "campaign_id": inventory.get("campaign_id"),
        "inventory_fingerprint": inventory.get("inventory_fingerprint"),
        "run_key_digest": inventory.get("run_key_digest"),
        "present_allowlist": sorted(present),
        "lr_status": "NO-GO",
        "no_automatic_promotion": True,
        "created_at_utc": _utcnow_iso(),
    }

    if mode == "dry-run":
        report["verdict"] = VERDICT_DRY_RUN_PASS
        report["report_fingerprint"] = canonical_hash(report)
        return report

    if mode != "prepare-pr-inputs":
        raise CampaignToPrError(HOLD_TOKEN, f"unknown mode={mode!r}")
    if output_dir is None:
        raise CampaignToPrError(HOLD_ANALYSIS, "--output-dir required for prepare")

    written = write_slim_package(
        evidence_root=root,
        output_dir=Path(output_dir),
        inventory=inventory,
        source_mode=source_mode,
        classification=classification,
        issue_number=issue_number,
        present_rels=present,
    )
    body = build_batch_pr_body(
        issue_number=issue_number,
        commit_sha=commit_sha,
        classification=classification,
        output_rel=output_rel,
        batch_key=batch_key,
    )
    scan_text_for_forbidden_tokens(body, context="pr_body.md")
    body_path = Path(output_dir) / "pr_body.md"
    body_path.write_text(body, encoding="utf-8")
    written.append("pr_body.md")

    report["verdict"] = VERDICT_PREPARE_PASS
    report["written"] = sorted(set(written))
    report["output_dir"] = str(Path(output_dir))
    report["report_fingerprint"] = canonical_hash(
        {k: v for k, v in report.items() if k != "report_fingerprint"}
    )
    (Path(output_dir) / "orchestrator_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def _package_fingerprint(output_dir: Path, written: Sequence[str]) -> str:
    parts: list[str] = []
    root = Path(output_dir)
    for rel in sorted(set(written)):
        if rel == HANDOFF_FILENAME:
            continue
        path = root / rel
        if not path.is_file():
            continue
        digest = canonical_hash({"path": rel, "bytes": path.read_bytes().hex()})
        parts.append(f"{rel}:{digest}")
    return canonical_hash({"files": parts})


def build_delivery_handoff(
    *,
    issue_number: int,
    inventory: Mapping[str, Any],
    classification: str,
    prepare_report: Mapping[str, Any],
    output_dir: Path,
    written: Sequence[str],
    batch_key: str,
    output_rel: str,
) -> dict[str, Any]:
    pkg_fp = _package_fingerprint(output_dir, written)
    expected_commit_paths = sorted(
        {rel for rel in written if rel != HANDOFF_FILENAME}
        | {
            f"{output_rel.rstrip('/')}/{rel}"
            for rel in written
            if rel != HANDOFF_FILENAME
        }
    )
    body: dict[str, Any] = {
        "schema_version": HANDOFF_SCHEMA,
        "handoff_status": HANDOFF_READY,
        "contract_doc": HANDOFF_CONTRACT_DOC,
        "orchestrator_schema": ORCHESTRATOR_SCHEMA,
        "issue_number": int(issue_number),
        "campaign_id": inventory.get("campaign_id"),
        "classification": classification,
        "inventory_fingerprint": inventory.get("inventory_fingerprint"),
        "run_key_digest": inventory.get("run_key_digest"),
        "manifest_fingerprint": inventory.get("manifest_fingerprint"),
        "authorization_fingerprint": inventory.get("authorization_fingerprint"),
        "bound_main_sha": inventory.get("bound_main_sha"),
        "slim_package": {
            "output_dir": str(Path(output_dir)),
            "output_rel": output_rel,
            "written": sorted(set(written)),
            "package_fingerprint": pkg_fp,
        },
        "pr_body_relpath": "pr_body.md",
        "orchestrator_report_fingerprint": prepare_report.get("report_fingerprint"),
        "routing_hints": {
            "batch_key": batch_key,
            "lane": "validation-research",
            "validation_profile": "validation-research-v1",
            "note": "live cdb-pr-router decision wins; do not resurrect deleted branches",
            "anti_repush": True,
        },
        "forbidden_actions": list(FORBIDDEN_HANDOFF_ACTIONS),
        "expected_commit_paths": expected_commit_paths,
        "expected_package_relative_paths": sorted(
            rel for rel in written if rel != HANDOFF_FILENAME
        ),
        "verification_protocol": "verify-delivery",
        "github_write_owner": "external_agent_or_control_plane",
        "lr_status": "NO-GO",
        "no_automatic_promotion": True,
        "created_at_utc": _utcnow_iso(),
    }
    body["handoff_fingerprint"] = canonical_hash(
        {k: v for k, v in body.items() if k != "handoff_fingerprint"}
    )
    return body


def prepare_delivery(
    *,
    evidence_root: Path,
    output_dir: Path,
    pins: BindingPins | None = None,
    issue_number: int = 4366,
    batch_key: str = "validation-research",
    commit_sha: str = "0" * 40,
    output_rel: str = "docs/evidence/arvp/campaign-to-pr/",
) -> dict[str, Any]:
    """Verify analysis, write slim package + machine-readable delivery handoff.

    Does not call ``gh``. Does not create PRs.
    """
    root = Path(evidence_root)
    pins = pins or BindingPins()
    # Fail closed if analysis/classification cannot be verified.
    try:
        classification_body = load_classification(root)
        present = assert_required_analysis(root)
    except CampaignToPrError as exc:
        if exc.reason_code in {
            HOLD_CLASS_MISSING,
            HOLD_CLASS_INVALID,
            HOLD_ANALYSIS,
        }:
            raise CampaignToPrError(HOLD_ANALYSIS_UNVERIFIED, str(exc)) from exc
        raise
    classification = str(classification_body["classification"])
    inventory = load_inventory(root)
    assert_bindings(inventory, pins)

    prepare = run_orchestrator(
        evidence_root=root,
        mode="prepare-pr-inputs",
        output_dir=Path(output_dir),
        pins=pins,
        issue_number=issue_number,
        batch_key=batch_key,
        commit_sha=commit_sha,
        output_rel=output_rel,
    )
    written = list(prepare.get("written") or [])
    handoff = build_delivery_handoff(
        issue_number=issue_number,
        inventory=inventory,
        classification=classification,
        prepare_report=prepare,
        output_dir=Path(output_dir),
        written=written,
        batch_key=batch_key,
        output_rel=output_rel,
    )
    handoff_path = Path(output_dir) / HANDOFF_FILENAME
    handoff_path.write_text(
        json.dumps(handoff, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    written.append(HANDOFF_FILENAME)
    return {
        "schema_version": ORCHESTRATOR_SCHEMA,
        "verdict": HANDOFF_READY,
        "classification": classification,
        "present_allowlist": sorted(present),
        "prepare": prepare,
        "handoff": handoff,
        "handoff_path": str(handoff_path),
        "written": sorted(set(written)),
        "lr_status": "NO-GO",
        "forbidden_actions": list(FORBIDDEN_HANDOFF_ACTIONS),
    }


def load_handoff(path: Path) -> dict[str, Any]:
    if not Path(path).is_file():
        raise CampaignToPrError(HOLD_HANDOFF_MISSING, str(path))
    body = _load_json(Path(path))
    if body.get("schema_version") != HANDOFF_SCHEMA:
        raise CampaignToPrError(
            HOLD_HANDOFF_MISSING, f"schema={body.get('schema_version')!r}"
        )
    if body.get("handoff_status") != HANDOFF_READY:
        raise CampaignToPrError(
            HOLD_HANDOFF_MISSING, f"handoff_status={body.get('handoff_status')!r}"
        )
    return body


def verify_delivery(
    *,
    handoff_path: Path,
    observed_facts: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify agent-supplied observed git/PR facts against handoff → PR_READY.

    Never invokes ``gh``. Observed facts must be supplied by the external agent.
    """
    handoff = load_handoff(handoff_path)
    obs = dict(observed_facts)

    branch = str(obs.get("branch_name") or "").strip()
    if not branch:
        raise CampaignToPrError(HOLD_BRANCH, "branch_name empty")
    if branch == "batch/validation-research-issue-4366":
        # Anti-repush: resurrecting the squash-deleted foundation branch is forbidden.
        raise CampaignToPrError(
            HOLD_BRANCH,
            "anti-repush: do not resurrect deleted branch "
            "batch/validation-research-issue-4366",
        )

    head = str(obs.get("head_sha") or "").strip().lower()
    pr_head = str(obs.get("pr_head_sha") or "").strip().lower()
    if not _SHA40_RE.fullmatch(head) or not _SHA40_RE.fullmatch(pr_head):
        raise CampaignToPrError(HOLD_OBSERVED, "head_sha/pr_head_sha must be 40-hex")
    if head != pr_head:
        raise CampaignToPrError(HOLD_HEAD_PR, f"head={head} pr_head={pr_head}")

    try:
        pr_number = int(obs.get("pr_number"))
    except (TypeError, ValueError) as exc:
        raise CampaignToPrError(HOLD_OBSERVED, "pr_number invalid") from exc
    if pr_number <= 0:
        raise CampaignToPrError(HOLD_OBSERVED, "pr_number must be positive")

    pr_base = str(obs.get("pr_base") or "").strip()
    if pr_base != "main":
        raise CampaignToPrError(HOLD_OBSERVED, f"pr_base={pr_base!r} (want main)")

    paths_raw = obs.get("commit_paths")
    if not isinstance(paths_raw, list) or not paths_raw:
        raise CampaignToPrError(HOLD_OBSERVED, "commit_paths missing")
    commit_paths = {str(p).replace("\\", "/").lstrip("./") for p in paths_raw}
    assert_no_raw_run_staging(sorted(commit_paths))
    for p in commit_paths:
        if p == "runs" or p.startswith("runs/"):
            raise CampaignToPrError(HOLD_FORBIDDEN_PATH, p)

    expected = {
        str(p).replace("\\", "/")
        for p in (handoff.get("expected_package_relative_paths") or [])
    }
    # Accept either package-relative or output_rel-prefixed paths.
    output_rel = str(
        (handoff.get("slim_package") or {}).get("output_rel") or ""
    ).rstrip("/")
    missing: list[str] = []
    for rel in sorted(expected):
        prefixed = f"{output_rel}/{rel}" if output_rel else rel
        if rel not in commit_paths and prefixed not in commit_paths:
            missing.append(rel)
    if missing:
        raise CampaignToPrError(HOLD_PATHS, ",".join(missing))

    observed_fp = str(obs.get("slim_package_fingerprint") or "").strip()
    expected_fp = str(
        (handoff.get("slim_package") or {}).get("package_fingerprint") or ""
    )
    if not observed_fp or observed_fp != expected_fp:
        raise CampaignToPrError(
            HOLD_FP, f"expected={expected_fp} observed={observed_fp}"
        )

    result = {
        "schema_version": HANDOFF_SCHEMA,
        "verdict": VERDICT_PR_READY,
        "handoff_fingerprint": handoff.get("handoff_fingerprint"),
        "issue_number": handoff.get("issue_number"),
        "pr_number": pr_number,
        "branch_name": branch,
        "head_sha": head,
        "pr_head_sha": pr_head,
        "classification": handoff.get("classification"),
        "inventory_fingerprint": handoff.get("inventory_fingerprint"),
        "slim_package_fingerprint": expected_fp,
        "forbidden_actions": list(FORBIDDEN_HANDOFF_ACTIONS),
        "lr_status": "NO-GO",
        "verified_at_utc": _utcnow_iso(),
    }
    result["verification_fingerprint"] = canonical_hash(
        {k: v for k, v in result.items() if k != "verification_fingerprint"}
    )
    return result


def _emit(payload: Mapping[str, Any], stream: TextIO) -> None:
    stream.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.arvp_vacation.sensitivity_campaign_to_pr",
        description=(
            "Campaign-to-PR Orchestrator v1 (#4366). "
            "Dry-run / prepare slim PR inputs. No GitHub PR create. LR=NO-GO."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--evidence-root", type=Path, required=True)
        p.add_argument("--expected-manifest-fp", default=None)
        p.add_argument("--expected-run-plan-fp", default=None)
        p.add_argument("--expected-authorization-fp", default=None)
        p.add_argument("--expected-bound-main-sha", default=None)
        p.add_argument("--issue", type=int, default=4366)

    p_dry = sub.add_parser("dry-run", help="Validate preconditions; write nothing")
    add_common(p_dry)

    p_prep = sub.add_parser(
        "prepare-pr-inputs",
        help="Write slim evidence package + pr_body.md (no gh pr create)",
    )
    add_common(p_prep)
    p_prep.add_argument("--output-dir", type=Path, required=True)
    p_prep.add_argument("--batch-key", default="validation-research")
    p_prep.add_argument("--commit-sha", default="0" * 40)
    p_prep.add_argument(
        "--output-rel",
        default="docs/evidence/arvp/campaign-to-pr/",
        help="Repo-relative path recorded in PR body draft",
    )

    p_del = sub.add_parser(
        "prepare-delivery",
        help=(
            "Verify analysis + write slim package + delivery_handoff.json "
            "(no gh pr create)"
        ),
    )
    add_common(p_del)
    p_del.add_argument("--output-dir", type=Path, required=True)
    p_del.add_argument("--batch-key", default="validation-research")
    p_del.add_argument("--commit-sha", default="0" * 40)
    p_del.add_argument(
        "--output-rel",
        default="docs/evidence/arvp/campaign-to-pr/",
    )

    p_ver = sub.add_parser(
        "verify-delivery",
        help=(
            "Verify agent-supplied observed git/PR facts against handoff → PR_READY "
            "(no gh calls)"
        ),
    )
    p_ver.add_argument("--handoff", type=Path, required=True)
    p_ver.add_argument(
        "--observed-json",
        type=Path,
        required=True,
        help="Agent-produced observed facts JSON (branch/head/pr/paths/fingerprint)",
    )
    return parser


def _pins_from_args(args: argparse.Namespace) -> BindingPins:
    return BindingPins(
        manifest_fingerprint=args.expected_manifest_fp,
        run_plan_fingerprint=args.expected_run_plan_fp,
        authorization_fingerprint=args.expected_authorization_fp,
        bound_main_sha=args.expected_bound_main_sha,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        if args.command == "dry-run":
            payload = run_orchestrator(
                evidence_root=args.evidence_root,
                mode="dry-run",
                pins=_pins_from_args(args),
                issue_number=args.issue,
            )
            _emit(payload, sys.stdout)
            return 0
        if args.command == "prepare-pr-inputs":
            payload = run_orchestrator(
                evidence_root=args.evidence_root,
                mode="prepare-pr-inputs",
                output_dir=args.output_dir,
                pins=_pins_from_args(args),
                issue_number=args.issue,
                batch_key=args.batch_key,
                commit_sha=args.commit_sha,
                output_rel=args.output_rel,
            )
            _emit(payload, sys.stdout)
            return 0
        if args.command == "prepare-delivery":
            payload = prepare_delivery(
                evidence_root=args.evidence_root,
                output_dir=args.output_dir,
                pins=_pins_from_args(args),
                issue_number=args.issue,
                batch_key=args.batch_key,
                commit_sha=args.commit_sha,
                output_rel=args.output_rel,
            )
            _emit(payload, sys.stdout)
            return 0
        if args.command == "verify-delivery":
            observed = json.loads(Path(args.observed_json).read_text(encoding="utf-8"))
            if not isinstance(observed, dict):
                raise CampaignToPrError(HOLD_OBSERVED, "observed-json must be object")
            payload = verify_delivery(
                handoff_path=args.handoff, observed_facts=observed
            )
            _emit(payload, sys.stdout)
            return 0
        parser.error(f"unknown command {args.command!r}")
        return 2
    except CampaignToPrError as exc:
        schema = (
            HANDOFF_SCHEMA
            if getattr(args, "command", "") in {"prepare-delivery", "verify-delivery"}
            else ORCHESTRATOR_SCHEMA
        )
        _emit(
            {
                "schema_version": schema,
                "verdict": exc.reason_code,
                "ok": False,
                "detail": str(exc),
                "lr_status": "NO-GO",
            },
            sys.stdout,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
