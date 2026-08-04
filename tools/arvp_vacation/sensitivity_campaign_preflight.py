"""Replay-only sensitivity campaign readiness preflight (#4153).

Machine-readable fail-closed gate for a future sensitivity campaign.
Does not run campaigns, touch holdouts, or implement Effective-Config (#4151).

CLI:
  python -m tools.arvp_vacation.sensitivity_campaign_preflight
  python -m tools.arvp_vacation.sensitivity_campaign_preflight --manifest PATH
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from core.replay.canonical_json import canonical_hash
from core.replay.dataset_identity import (
    CONTENT_IDENTITY_SCHEMA_VERSION,
    assert_content_payload_secret_safe,
    collect_forbidden_evidence_keys,
)
from core.replay.execution_economics_v1 import (
    CONTRACT_VERSION as ECONOMICS_CONTRACT_VERSION,
)
from tools.arvp_vacation.batch_a_gate_common import (
    STAGE_A_GATE_CONTRACT_PATH,
    STAGE_B_CONFIRMATION_CONTRACT_PATH,
    compute_gate_contract_sha256,
    load_json_contract,
)
from tools.arvp_vacation.sensitivity_campaign_grid import (
    EXPECTED_RUN_COUNT,
    EXPECTED_UNIQUE_VARIANTS,
    MAX_RUN_COUNT,
    STRATEGY_ID,
    SensitivityGridError,
    assert_manifest_matches_ratified_grid,
    expand_runs,
    expand_variants,
    variant_breakdown,
)
from tools.arvp_vacation.sensitivity_experiment_manifest import (
    MANIFEST_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION_V11,
    SensitivityManifestError,
    assert_executable_consistency,
    assert_manifest_secret_safe,
    fingerprint_manifest,
    load_manifest,
    validate_manifest_schema,
)
from tools.market_data.development_window_selector import (
    EXCLUDED_OVERLAP_CLASSES,
    EXCLUDED_PURPOSES,
    LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS,
    LOCKED_DEVELOPMENT_SELECTION_SHA256,
)
from tools.validate_parameter_control_policy import (
    POLICY_PATH,
    SCHEMA_PATH as POLICY_SCHEMA_PATH,
    compute_canonical_json_sha256,
    compute_register_fingerprint,
    validate as validate_parameter_control_policy,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

VERDICT_READY = "READY_FOR_REPLAY_SENSITIVITY"
VERDICT_READY_CAMPAIGN = "READY_FOR_REPLAY_SENSITIVITY_CAMPAIGN"
VERDICT_BLOCKED = "BLOCKED_EXPERIMENT_NOT_READY"
VERDICT_INVALID = "INVALID_EXPERIMENT_MANIFEST"
VERDICT_FROZEN = "FROZEN_BOUNDARY_VIOLATION"
VERDICT_HOLDOUT = "HOLDOUT_ACCESS_BLOCKED"

CORRECTNESS_BASELINE_SHA_DEFAULT = "301bc757be7cb4162db6db114a5c445f2aca392f"

READINESS_SCHEMA_VERSION = "cdb.sensitivity_campaign_readiness.v1"

ALLOWED_CHANGE_AUTHORITIES = frozenset(
    {"RESEARCH_ALLOWED", "CONDITIONAL_AFTER_EVIDENCE"}
)
ALLOWED_COMPACT_DECISIONS = frozenset(
    {"ALLOW_REPLAY_RESEARCH", "CONDITIONAL_AFTER_EVIDENCE"}
)

# Parameter family tokens that must never appear in a sensitivity experiment.
FORBIDDEN_BOUNDARY_FAMILY_TOKENS = frozenset(
    {
        "stage_a_gate",
        "stage_b_gate",
        "stage-a-gate",
        "stage-b-gate",
        "oos",
        "out_of_sample",
        "stress_gate",
        "risk_limit",
        "position_limit",
        "exposure_limit",
        "drawdown_limit",
        "kill_switch",
        "kill-switch",
        "live_boundary",
        "echtgeld",
        "paper_capital",
    }
)

EFFECTIVE_CONFIG_REQUIRED_SECTIONS = (
    "schema_version",
    "compose",
    "environment_redacted",
    "risk",
    "allocation",
    "regime",
    "signal",
    "execution",
    "override_order",
    "snapshot_fingerprint",
)

EFFECTIVE_CONFIG_MODULE_REL = Path("core/replay/effective_config_snapshot.py")
EFFECTIVE_CONFIG_SCHEMA_REL = Path(
    "docs/contracts/cdb_effective_config_snapshot.v1.schema.json"
)

REGIME_SIGNAL_ANCHORS = (
    Path("tools/market_data/assign_regime_offline.py"),
    Path("services/regime/models.py"),
    Path("services/regime/service.py"),
    Path("tests/unit/market_data/test_assign_regime_offline_unknown_4188.py"),
    Path("docs/contracts/execution_economics_gross_to_net.v1.schema.json"),
)

ECONOMICS_SCHEMA_REL = Path(
    "docs/contracts/execution_economics_gross_to_net.v1.schema.json"
)
ECONOMICS_DOC_REL = Path("docs/contracts/EXECUTION_ECONOMICS_GROSS_TO_NET_V1.md")

ALLOWED_CLAIMS = (
    "Machine-readable fail-closed readiness preflight exists for #4153.",
    "Experiment manifest contract is versioned and deterministically fingerprintable.",
    "Frozen boundaries and holdout access are technically blocked.",
    "Effective-Config snapshot capability is present and secret-safe (#4151).",
    "CDB-052 rankability/warmup provenance fail-closed gate is modeled.",
    "Repo preflight may reach READY_FOR_REPLAY_SENSITIVITY when all gates PASS.",
)

FORBIDDEN_CLAIMS = (
    "The sensitivity campaign has been executed.",
    "Parameters have been investigated.",
    "A candidate is promising or profitable.",
    "Stage-A has been passed.",
    "Replay evidence proves paper, live, or echtgeld readiness.",
    "Historical #4151 ACs for window-parity, DQ-verdict binding, gap/OOO, "
    "and rankability provenance are fully closed by Effective-Config alone.",
    "RESEARCH_ALLOWED is a promotion, paper, live, or echtgeld authorization.",
)


@dataclass(frozen=True, slots=True)
class GateResult:
    status: str
    detail: str
    evidence_refs: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "detail": self.detail,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class EffectiveConfigCapability:
    """Injectable Effective-Config capability (real capability still #4151)."""

    available: bool
    detail: str
    validate_snapshot: Callable[[Mapping[str, Any]], None] | None = None


def _gate_pass(detail: str, *refs: str) -> GateResult:
    return GateResult("PASS", detail, refs)


def _gate_blocked(detail: str, *refs: str) -> GateResult:
    return GateResult("BLOCKED", detail, refs)


def _gate_invalid(detail: str, *refs: str) -> GateResult:
    return GateResult("INVALID", detail, refs)


def discover_effective_config_capability(
    repo_root: Path,
) -> EffectiveConfigCapability:
    """Probe for #4151 Effective-Config capability (module + schema + validator)."""
    module_path = repo_root / EFFECTIVE_CONFIG_MODULE_REL
    schema_path = repo_root / EFFECTIVE_CONFIG_SCHEMA_REL
    missing: list[str] = []
    if not module_path.exists():
        missing.append(str(EFFECTIVE_CONFIG_MODULE_REL.as_posix()))
    if not schema_path.exists():
        missing.append(str(EFFECTIVE_CONFIG_SCHEMA_REL.as_posix()))
    if missing:
        return EffectiveConfigCapability(
            available=False,
            detail=(
                "Full Effective-Config snapshot capability missing (#4151 deferred "
                f"after PR #4243): {', '.join(missing)}"
            ),
        )
    try:
        from core.replay.effective_config_snapshot import (
            validate_effective_config_snapshot,
        )
    except Exception as exc:  # noqa: BLE001 — fail-closed capability probe
        return EffectiveConfigCapability(
            available=False,
            detail=f"Effective-Config module present but not importable: {exc}",
        )
    return EffectiveConfigCapability(
        available=True,
        detail="Effective-Config capability present (module+schema+validator)",
        validate_snapshot=validate_effective_config_snapshot,
    )


def _resolve_repo_effective_config_snapshot(
    repo_root: Path,
    *,
    capability: EffectiveConfigCapability,
    snapshot: Mapping[str, Any] | None,
) -> Mapping[str, Any] | None:
    """Use supplied snapshot or build repo-default when capability is available."""
    if snapshot is not None:
        return snapshot
    if not capability.available:
        return None
    try:
        from core.replay.effective_config_snapshot import (
            build_effective_config_snapshot,
        )
    except Exception:  # noqa: BLE001
        return None
    try:
        return build_effective_config_snapshot(repo_root)
    except Exception:  # noqa: BLE001 — leave gate blocked with missing evidence
        return None


def validate_effective_config_snapshot_structure(
    snapshot: Mapping[str, Any],
) -> None:
    """Fail-closed structural check for a complete secret-safe config snapshot."""
    if not isinstance(snapshot, Mapping):
        raise ValueError("effective config snapshot must be an object")
    missing = [k for k in EFFECTIVE_CONFIG_REQUIRED_SECTIONS if k not in snapshot]
    if missing:
        raise ValueError(
            "incomplete effective config snapshot; missing sections: "
            + ", ".join(missing)
        )
    # Surface-only / parameter-hash-only snapshots are rejected.
    superficial_only = set(snapshot.keys()) <= {
        "parameter_hash",
        "env_subset",
        "dataset_fingerprint",
        "schema_version",
        "snapshot_fingerprint",
    }
    if superficial_only:
        raise ValueError(
            "superficial effective config snapshot rejected "
            "(parameter/env/dataset hash alone is insufficient)"
        )
    for section in ("compose", "risk", "allocation", "regime", "signal", "execution"):
        value = snapshot.get(section)
        if not isinstance(value, Mapping) or not value:
            raise ValueError(
                f"effective config section '{section}' must be non-empty object"
            )
    override = snapshot.get("override_order")
    if not isinstance(override, Sequence) or isinstance(override, (str, bytes)):
        raise ValueError("override_order must be a non-string sequence")
    if not override:
        raise ValueError("override_order must be non-empty")
    assert_content_payload_secret_safe(snapshot)
    fp = snapshot.get("snapshot_fingerprint")
    if not isinstance(fp, str) or len(fp) != 64:
        raise ValueError("snapshot_fingerprint must be 64-char hex")


def check_parameter_control_canon(repo_root: Path) -> GateResult:
    policy_path = repo_root / POLICY_PATH.relative_to(PROJECT_ROOT)
    schema_path = repo_root / POLICY_SCHEMA_PATH.relative_to(PROJECT_ROOT)
    if not policy_path.exists() or not schema_path.exists():
        return _gate_blocked(
            "Parameter-control policy or schema missing",
            str(policy_path),
            str(schema_path),
        )
    # Run validator against repo-local paths by temporarily relying on module
    # defaults when repo_root matches PROJECT_ROOT; otherwise load + fingerprint.
    doc = json.loads(policy_path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        return _gate_blocked("Parameter-control policy root must be object")
    try:
        errors = validate_parameter_control_policy(
            policy_path=policy_path,
            schema_path=schema_path,
        )
        if errors:
            return _gate_blocked(
                "Parameter-control validator failed: " + "; ".join(errors[:5]),
                str(policy_path),
            )
    except Exception as exc:  # noqa: BLE001 — fail-closed surface
        return _gate_blocked(f"Parameter-control validation error: {exc}")

    if doc.get("status") != "canonical":
        return _gate_blocked("Parameter-control status is not canonical")
    default_policy = doc.get("default_policy") or {}
    if default_policy.get("stage_a_b_oos_stress_gates") != "frozen":
        return _gate_blocked("stage_a_b_oos_stress_gates must be frozen")
    if default_policy.get("risk_and_live_boundaries") != "frozen":
        return _gate_blocked("risk_and_live_boundaries must be frozen")
    fp = compute_register_fingerprint(doc)
    return _gate_pass(
        f"Parameter-control canon OK; register_fingerprint={fp}",
        str(policy_path.relative_to(repo_root)),
        f"register_fingerprint:{fp}",
    )


def check_regime_signal_correctness(repo_root: Path) -> GateResult:
    missing = [
        str(p.as_posix()) for p in REGIME_SIGNAL_ANCHORS if not (repo_root / p).exists()
    ]
    if missing:
        return _gate_blocked(
            "Regime/signal correctness anchors missing: " + ", ".join(missing),
            *missing,
        )
    # Fail-closed: UNKNOWN path must remain explicit (no silent legacy PASS).
    models_text = (repo_root / "services/regime/models.py").read_text(encoding="utf-8")
    if "UNKNOWN" not in models_text:
        return _gate_blocked(
            "services/regime/models.py missing fail-closed UNKNOWN anchor"
        )
    offline_text = (repo_root / "tools/market_data/assign_regime_offline.py").read_text(
        encoding="utf-8"
    )
    if "UNKNOWN" not in offline_text:
        return _gate_blocked(
            "assign_regime_offline.py missing fail-closed UNKNOWN anchor"
        )
    return _gate_pass(
        "Regime/signal correctness anchors present (UNKNOWN fail-closed)",
        *[str(p.as_posix()) for p in REGIME_SIGNAL_ANCHORS],
    )


def check_execution_economics(repo_root: Path) -> GateResult:
    schema_path = repo_root / ECONOMICS_SCHEMA_REL
    doc_path = repo_root / ECONOMICS_DOC_REL
    module_path = repo_root / "core/replay/execution_economics_v1.py"
    if not schema_path.exists() or not doc_path.exists() or not module_path.exists():
        return _gate_blocked(
            "Execution-economics contract surfaces missing",
            str(ECONOMICS_SCHEMA_REL.as_posix()),
            str(ECONOMICS_DOC_REL.as_posix()),
            "core/replay/execution_economics_v1.py",
        )
    if ECONOMICS_CONTRACT_VERSION != "execution_economics_gross_to_net.v1":
        return _gate_blocked(
            f"Unexpected economics contract version: {ECONOMICS_CONTRACT_VERSION}"
        )
    return _gate_pass(
        f"Execution-economics contract present; version={ECONOMICS_CONTRACT_VERSION}",
        str(ECONOMICS_SCHEMA_REL.as_posix()),
        f"contract_version:{ECONOMICS_CONTRACT_VERSION}",
    )


def check_dataset_provenance_capability(repo_root: Path) -> GateResult:
    identity = repo_root / "core/replay/dataset_identity.py"
    provider = repo_root / "core/replay/dataset_provider.py"
    if not identity.exists() or not provider.exists():
        return _gate_blocked(
            "Dataset identity/provider surfaces missing",
            "core/replay/dataset_identity.py",
            "core/replay/dataset_provider.py",
        )
    text = identity.read_text(encoding="utf-8")
    if "content_fingerprint" not in text or "request_fingerprint" not in text:
        return _gate_blocked(
            "dataset_identity.py missing request/content fingerprint API"
        )
    if CONTENT_IDENTITY_SCHEMA_VERSION not in text:
        return _gate_blocked("dataset content identity schema version missing")
    return _gate_pass(
        "Dataset request/content fingerprint capability present",
        "core/replay/dataset_identity.py",
        f"identity_schema:{CONTENT_IDENTITY_SCHEMA_VERSION}",
    )


def check_cdb052_rankability_provenance(repo_root: Path) -> GateResult:
    """CDB-052 technical readiness: rankability/warmup provenance fail-closed.

    Does not run campaigns, score parameters, or claim CDB-049..051 work.
    """
    module_rel = Path("tools/arvp_vacation/candle_rankability.py")
    gate_rel = Path("tools/arvp_vacation/batch_a_gate_common.py")
    test_rel = Path("tests/unit/arvp/test_candle_rankability.py")
    module_path = repo_root / module_rel
    gate_path = repo_root / gate_rel
    test_path = repo_root / test_rel
    missing = [
        str(p.as_posix())
        for p in (module_rel, gate_rel, test_rel)
        if not (repo_root / p).exists()
    ]
    if missing:
        return _gate_blocked(
            "CDB-052 rankability surfaces missing: " + ", ".join(missing),
            *missing,
        )

    required_symbols = (
        "FLAG_STALE_MANIFEST_FALLBACK_BLOCKED",
        "FLAG_MANIFEST_MISSING",
        "FLAG_RANKABILITY_PROVENANCE_MISSING",
        "enforce_rankability_provenance",
        "assert_rankability_provenance",
        "resolve_candle_rankability",
    )
    module_text = module_path.read_text(encoding="utf-8")
    absent = [name for name in required_symbols if name not in module_text]
    if absent:
        return _gate_blocked(
            "CDB-052 candle_rankability missing symbols: " + ", ".join(absent),
            str(module_rel.as_posix()),
        )

    gate_text = gate_path.read_text(encoding="utf-8")
    if "enforce_rankability_provenance" not in gate_text:
        return _gate_blocked(
            "record_is_rankable does not wire enforce_rankability_provenance",
            str(gate_rel.as_posix()),
        )
    if "is not True" not in gate_text:
        return _gate_blocked(
            "record_is_rankable missing explicit rankable is True fail-closed check",
            str(gate_rel.as_posix()),
        )

    test_text = test_path.read_text(encoding="utf-8")
    for anchor in (
        "FLAG_STALE_MANIFEST_FALLBACK_BLOCKED",
        "stale_manifest",
        "content_fingerprint",
        "warmup",
    ):
        if anchor not in test_text:
            return _gate_blocked(
                f"CDB-052 negative-test anchor missing: {anchor}",
                str(test_rel.as_posix()),
            )

    try:
        from tools.arvp_vacation.batch_a_gate_common import record_is_rankable
        from tools.arvp_vacation.candle_rankability import (
            FLAG_STALE_MANIFEST_FALLBACK_BLOCKED,
            enforce_rankability_provenance,
            resolve_candle_rankability,
        )
    except Exception as exc:  # noqa: BLE001
        return _gate_blocked(f"CDB-052 modules not importable: {exc}")

    # Behavioral: absent rankable / missing provenance must not pass scorer gate.
    if record_is_rankable({"closed_trades_total": 5}):
        return _gate_blocked(
            "record_is_rankable still treats missing rankable as truthy"
        )
    if record_is_rankable(
        {
            "rankable": True,
            "closed_trades_total": 5,
            # no warmup_provenance
        }
    ):
        return _gate_blocked(
            "record_is_rankable accepts rankable=true without provenance"
        )

    # Behavioral: silent manifest fallback remains blocked.
    blocked = resolve_candle_rankability(
        dataset_summary={
            "candles_total": 100,
            "candles_live": 66,
            "content_fingerprint": "a" * 64,
        },
        strategy_id="breakout_volatility_filter_v1",
        campaign_id="batch_a_stage_a_d0a4e72d_20260713",
        parameter_fingerprint="abc",
        campaign_source_sha="d0a4e72d10fced72a5fb2d2edf1e40f3c80f417a",
        repo_root=repo_root,
    )
    if FLAG_STALE_MANIFEST_FALLBACK_BLOCKED not in blocked.rankability_blocking_flags:
        return _gate_blocked(
            "stale manifest fallback is not blocked for Batch-A campaign"
        )
    if blocked.warmup_provenance.get("silent_manifest_fallback") is not False:
        return _gate_blocked("silent_manifest_fallback must be explicitly False")

    # Positive bound fixture: fully bound provenance must enforce cleanly.
    bound = resolve_candle_rankability(
        dataset_summary={
            "candles_total": 44640,
            "candles_live": 44606,
            "warmup_candles": 34,
            "content_fingerprint": "a" * 64,
        },
        strategy_id="breakout_volatility_filter_v1",
        campaign_id="batch_a_stage_a_d0a4e72d_20260713",
        parameter_fingerprint="abc",
        campaign_source_sha="d0a4e72d10fced72a5fb2d2edf1e40f3c80f417a",
        repo_root=repo_root,
    )
    if bound.rankability_blocking_flags:
        return _gate_blocked(
            "bound CDB-052 fixture unexpectedly blocking: "
            + ",".join(bound.rankability_blocking_flags)
        )
    try:
        enforce_rankability_provenance(
            current={
                "content_fingerprint": "a" * 64,
                "warmup_bars": 34,
                "parameter_fingerprint": "abc",
                "campaign_source_sha": "d0a4e72d10fced72a5fb2d2edf1e40f3c80f417a",
            },
            evidence=bound.warmup_provenance,
        )
    except Exception as exc:  # noqa: BLE001
        return _gate_blocked(f"bound provenance enforce failed: {exc}")

    if not record_is_rankable(
        {
            "rankable": True,
            "closed_trades_total": 5,
            "warmup_provenance": bound.warmup_provenance,
            "rankability_blocking_flags": [],
            "not_rankable_reasons": [],
        }
    ):
        return _gate_blocked("scorer rejects valid bound rankability provenance")

    return _gate_pass(
        "CDB-052 rankability/warmup provenance fail-closed and wired",
        str(module_rel.as_posix()),
        str(gate_rel.as_posix()),
        str(test_rel.as_posix()),
    )


def check_effective_config_provenance(
    repo_root: Path,
    *,
    capability: EffectiveConfigCapability | None = None,
    snapshot: Mapping[str, Any] | None = None,
) -> GateResult:
    cap = capability or discover_effective_config_capability(repo_root)
    if not cap.available:
        return _gate_blocked(cap.detail, str(EFFECTIVE_CONFIG_MODULE_REL.as_posix()))
    if snapshot is None:
        return _gate_blocked(
            "Effective-Config capability markers present but no complete snapshot "
            "evidence supplied"
        )
    validator = cap.validate_snapshot or validate_effective_config_snapshot_structure
    try:
        validator(snapshot)
    except Exception as exc:  # noqa: BLE001
        return _gate_blocked(f"Effective-Config snapshot rejected: {exc}")
    return _gate_pass(
        "Effective-Config snapshot structure validated",
        f"snapshot_fingerprint:{snapshot.get('snapshot_fingerprint')}",
    )


def check_frozen_boundaries_repo(repo_root: Path) -> GateResult:
    stage_a_path = repo_root / STAGE_A_GATE_CONTRACT_PATH.relative_to(PROJECT_ROOT)
    stage_b_path = repo_root / STAGE_B_CONFIRMATION_CONTRACT_PATH.relative_to(
        PROJECT_ROOT
    )
    if not stage_a_path.exists() or not stage_b_path.exists():
        return _gate_blocked("Frozen Stage-A/B gate contracts missing")
    stage_a = load_json_contract(stage_a_path)
    stage_b = load_json_contract(stage_b_path)
    sa_fp = compute_gate_contract_sha256(stage_a)
    sb_fp = compute_gate_contract_sha256(stage_b)
    if stage_a.get("development_window_count") != 39:
        return _gate_blocked("Stage-A development_window_count drift")
    return _gate_pass(
        "Frozen Stage-A/B gate contracts present and hashable",
        f"stage_a_gate_contract_sha256:{sa_fp}",
        f"stage_b_confirmation_contract_sha256:{sb_fp}",
    )


def check_holdout_isolation_repo(repo_root: Path) -> GateResult:
    if len(LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS) != 39:
        return _gate_blocked("Locked development window count != 39")
    if not LOCKED_DEVELOPMENT_SELECTION_SHA256:
        return _gate_blocked("Locked development selection SHA missing")
    # Ensure holdout purposes remain excluded in selector source.
    selector = repo_root / "tools/market_data/development_window_selector.py"
    text = selector.read_text(encoding="utf-8")
    for purpose in sorted(EXCLUDED_PURPOSES):
        if purpose not in text:
            return _gate_blocked(f"Holdout purpose '{purpose}' missing from selector")
    return _gate_pass(
        "Holdout isolation lock present (39 development windows)",
        f"selection_sha256:{LOCKED_DEVELOPMENT_SELECTION_SHA256}",
        f"excluded_purposes:{sorted(EXCLUDED_PURPOSES)}",
    )


def _lookup_parameter_rule(
    policy: Mapping[str, Any], parameter_id: str
) -> Mapping[str, Any] | None:
    for rule in policy.get("rules") or []:
        if isinstance(rule, Mapping) and rule.get("parameter_id") == parameter_id:
            return rule
    return None


def _authority_allowed(rule: Mapping[str, Any]) -> bool:
    authority = rule.get("change_authority")
    compact = (rule.get("analysis") or {}).get("compact_decision")
    if authority in ALLOWED_CHANGE_AUTHORITIES:
        return True
    if compact in ALLOWED_COMPACT_DECISIONS:
        return True
    return False


def _scan_holdout_illicit_keys(
    manifest: Mapping[str, Any],
) -> GateResult | None:
    """Detect explicit holdout window references before schema validation."""
    for illicit_key in (
        "oos_windows",
        "stress_windows",
        "stage_b_windows",
        "validation_windows",
        "out_of_sample_windows",
    ):
        if illicit_key in manifest:
            return GateResult(
                "BLOCKED",
                f"Holdout reference key forbidden: {illicit_key}",
                (illicit_key,),
            )
    return None


def validate_manifest_against_repo(
    manifest: Mapping[str, Any],
    repo_root: Path,
    *,
    capability: EffectiveConfigCapability | None = None,
    effective_config_snapshot: Mapping[str, Any] | None = None,
) -> tuple[str, dict[str, GateResult], list[str]]:
    """Validate a concrete manifest. Returns verdict, gates, blocking reasons."""
    gates: dict[str, GateResult] = {}
    blocking: list[str] = []

    # Holdout illicit keys must be blocked even when schema would reject them.
    illicit = _scan_holdout_illicit_keys(manifest)
    if illicit is not None:
        gates["holdout_isolation"] = illicit
        return VERDICT_HOLDOUT, gates, [f"holdout_key:{illicit.evidence_refs[0]}"]

    try:
        validate_manifest_schema(manifest)
        assert_manifest_secret_safe(manifest)
        assert_executable_consistency(manifest)
        gates["schema"] = _gate_pass("Manifest schema valid")
    except SensitivityManifestError as exc:
        gates["schema"] = _gate_invalid(str(exc))
        return VERDICT_INVALID, gates, [str(exc)]

    executable = manifest.get("executable") is True
    schema_version = manifest.get("schema_version")

    # Dataset provenance in manifest
    dataset = manifest.get("dataset_identity") or {}
    req_fp = dataset.get("request_fingerprint")
    content_fp = dataset.get("content_fingerprint")
    if not content_fp:
        gates["dataset_provenance"] = _gate_blocked(
            "Missing dataset content_fingerprint"
        )
        blocking.append("missing_content_fingerprint")
    elif not req_fp:
        gates["dataset_provenance"] = _gate_blocked(
            "Missing dataset request_fingerprint"
        )
        blocking.append("missing_request_fingerprint")
    elif req_fp == content_fp:
        gates["dataset_provenance"] = _gate_blocked(
            "request_fingerprint must not be reused as content_fingerprint"
        )
        blocking.append("request_as_content_fingerprint")
    else:
        gates["dataset_provenance"] = _gate_pass(
            "Request and content fingerprints present and separated",
            f"request:{req_fp}",
            f"content:{content_fp}",
        )

    # Parameter control fingerprints + authority
    policy_path = repo_root / POLICY_PATH.relative_to(PROJECT_ROOT)
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    expected_fp = compute_register_fingerprint(policy)
    expected_canonical = compute_canonical_json_sha256(policy_path)
    declared_pc = (manifest.get("parameter_control") or {}).get("register_fingerprint")
    declared_canonical = (manifest.get("parameter_control") or {}).get(
        "canonical_json_sha256"
    )
    if declared_pc != expected_fp:
        gates["parameter_control"] = _gate_blocked(
            "Manifest parameter_control.register_fingerprint does not match policy",
            f"expected:{expected_fp}",
            f"declared:{declared_pc}",
        )
        blocking.append("parameter_control_fingerprint_mismatch")
    elif (
        executable
        and declared_canonical is not None
        and declared_canonical != expected_canonical
    ):
        gates["parameter_control"] = _gate_blocked(
            "Manifest parameter_control.canonical_json_sha256 does not match policy",
            f"expected:{expected_canonical}",
            f"declared:{declared_canonical}",
        )
        blocking.append("parameter_control_canonical_mismatch")
    else:
        bad_rules: list[str] = []
        unknown: list[str] = []
        for family in manifest.get("parameter_families") or []:
            family_id = str(family.get("family_id") or "")
            lowered = family_id.lower()
            if any(token in lowered for token in FORBIDDEN_BOUNDARY_FAMILY_TOKENS):
                gates["frozen_boundaries"] = GateResult(
                    "BLOCKED",
                    f"Forbidden frozen-boundary family_id: {family_id}",
                    (family_id,),
                )
                return VERDICT_FROZEN, gates, [f"forbidden_family:{family_id}"]
            for pid in family.get("parameter_ids") or []:
                rule = _lookup_parameter_rule(policy, pid)
                if rule is None:
                    unknown.append(pid)
                    continue
                if not _authority_allowed(rule):
                    bad_rules.append(
                        f"{pid}:{rule.get('change_authority')}/"
                        f"{(rule.get('analysis') or {}).get('compact_decision')}"
                    )
                declared_auth = family.get("change_authority")
                if declared_auth not in ALLOWED_CHANGE_AUTHORITIES:
                    bad_rules.append(f"{pid}:declared_authority={declared_auth}")
        if unknown:
            gates["parameter_control"] = _gate_blocked(
                "Unknown parameter rules: " + ", ".join(unknown)
            )
            blocking.append("unknown_parameter_rule")
        elif bad_rules:
            gates["parameter_control"] = _gate_blocked(
                "Parameter authority not allowed for replay research: "
                + ", ".join(bad_rules)
            )
            blocking.append("parameter_authority_denied")
        else:
            gates["parameter_control"] = _gate_pass(
                "Parameter-control fingerprint and authorities OK",
                f"register_fingerprint:{expected_fp}",
            )

    # Execution economics version
    declared_econ = manifest.get("execution_economics_contract_version")
    if declared_econ != ECONOMICS_CONTRACT_VERSION:
        gates["execution_economics"] = _gate_blocked(
            f"Economics contract version mismatch: {declared_econ}"
        )
        blocking.append("economics_version_mismatch")
    else:
        gates["execution_economics"] = _gate_pass(
            f"Economics contract version={ECONOMICS_CONTRACT_VERSION}"
        )

    # Frozen gate fingerprints
    stage_a = load_json_contract(
        repo_root / STAGE_A_GATE_CONTRACT_PATH.relative_to(PROJECT_ROOT)
    )
    stage_b = load_json_contract(
        repo_root / STAGE_B_CONFIRMATION_CONTRACT_PATH.relative_to(PROJECT_ROOT)
    )
    sa_fp = compute_gate_contract_sha256(stage_a)
    sb_fp = compute_gate_contract_sha256(stage_b)
    frozen = manifest.get("frozen_boundaries") or {}
    if frozen.get("stage_a_gate_contract_sha256") != sa_fp:
        gates["frozen_boundaries"] = GateResult(
            "BLOCKED",
            "Stage-A gate fingerprint mismatch / mutation",
            (
                f"expected:{sa_fp}",
                f"declared:{frozen.get('stage_a_gate_contract_sha256')}",
            ),
        )
        return VERDICT_FROZEN, gates, ["stage_a_gate_fingerprint_mismatch"]
    if frozen.get("stage_b_confirmation_contract_sha256") != sb_fp:
        gates["frozen_boundaries"] = GateResult(
            "BLOCKED",
            "Stage-B confirmation fingerprint mismatch / mutation",
            (
                f"expected:{sb_fp}",
                f"declared:{frozen.get('stage_b_confirmation_contract_sha256')}",
            ),
        )
        return VERDICT_FROZEN, gates, ["stage_b_gate_fingerprint_mismatch"]
    if frozen.get("stage_a_b_oos_stress_gates") != "frozen":
        gates["frozen_boundaries"] = GateResult(
            "BLOCKED",
            "stage_a_b_oos_stress_gates must remain frozen",
            (),
        )
        return VERDICT_FROZEN, gates, ["gates_unfrozen"]
    if frozen.get("risk_and_live_boundaries") != "frozen":
        gates["frozen_boundaries"] = GateResult(
            "BLOCKED",
            "risk_and_live_boundaries must remain frozen",
            (),
        )
        return VERDICT_FROZEN, gates, ["risk_live_unfrozen"]
    gates["frozen_boundaries"] = _gate_pass(
        "Frozen gate/boundary fingerprints match repo contracts",
        f"stage_a:{sa_fp}",
        f"stage_b:{sb_fp}",
    )

    # Holdout isolation
    windows = manifest.get("development_windows") or {}
    window_ids = tuple(windows.get("window_ids") or ())
    locked = set(LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS)
    declared = set(window_ids)
    holdout = manifest.get("holdout_denylist") or {}
    excluded = set(holdout.get("excluded_purposes") or [])
    if windows.get("purpose") != "development":
        gates["holdout_isolation"] = GateResult(
            "BLOCKED",
            "development_windows.purpose must be development",
            (),
        )
        return VERDICT_HOLDOUT, gates, ["non_development_purpose"]
    if declared != locked:
        gates["holdout_isolation"] = GateResult(
            "BLOCKED",
            "Window set must equal the locked 39 Stage-A development windows",
            (
                f"extra:{sorted(declared - locked)}",
                f"missing:{sorted(locked - declared)}",
            ),
        )
        return VERDICT_HOLDOUT, gates, ["window_set_mismatch"]
    if windows.get("selection_sha256") != LOCKED_DEVELOPMENT_SELECTION_SHA256:
        gates["holdout_isolation"] = GateResult(
            "BLOCKED",
            "development selection_sha256 mismatch",
            (),
        )
        return VERDICT_HOLDOUT, gates, ["selection_sha_mismatch"]
    if not EXCLUDED_PURPOSES.issubset(excluded):
        gates["holdout_isolation"] = GateResult(
            "BLOCKED",
            "holdout_denylist.excluded_purposes incomplete",
            (),
        )
        return VERDICT_HOLDOUT, gates, ["holdout_denylist_incomplete"]
    gates["holdout_isolation"] = _gate_pass(
        "Holdout isolation OK (exactly 39 development windows)",
        f"selection_sha256:{LOCKED_DEVELOPMENT_SELECTION_SHA256}",
    )

    # Effective config
    efc_fp = manifest.get("effective_config_snapshot_fingerprint")
    if not efc_fp:
        gates["effective_config"] = _gate_blocked(
            "Missing effective_config_snapshot_fingerprint"
        )
        blocking.append("missing_effective_config_fingerprint")
    else:
        gates["effective_config"] = check_effective_config_provenance(
            repo_root,
            capability=capability,
            snapshot=effective_config_snapshot,
        )
        if gates["effective_config"].status != "PASS":
            blocking.append("effective_config_not_ready")
        elif (
            isinstance(effective_config_snapshot, Mapping)
            and effective_config_snapshot.get("snapshot_fingerprint") != efc_fp
        ):
            gates["effective_config"] = _gate_blocked(
                "Manifest effective_config_snapshot_fingerprint does not match "
                "live snapshot",
                f"declared:{efc_fp}",
                f"live:{effective_config_snapshot.get('snapshot_fingerprint')}",
            )
            blocking.append("effective_config_fingerprint_mismatch")

    # Regime / economics / dataset capability still required for READY
    gates["regime_signal"] = check_regime_signal_correctness(repo_root)
    if gates["regime_signal"].status != "PASS":
        blocking.append("regime_signal_not_ready")
    # execution_economics already checked version; also repo presence
    econ_repo = check_execution_economics(repo_root)
    if econ_repo.status != "PASS":
        gates["execution_economics"] = econ_repo
        blocking.append("economics_repo_not_ready")
    ds_cap = check_dataset_provenance_capability(repo_root)
    if ds_cap.status != "PASS":
        gates["dataset_capability"] = ds_cap
        blocking.append("dataset_capability_not_ready")
    else:
        gates["dataset_capability"] = ds_cap

    cdb052 = check_cdb052_rankability_provenance(repo_root)
    gates["cdb052_rankability_provenance"] = cdb052
    if cdb052.status != "PASS":
        blocking.append("cdb052_rankability_not_ready")

    if executable and schema_version == MANIFEST_SCHEMA_VERSION_V11:
        _apply_executable_campaign_gates(
            manifest,
            repo_root,
            gates=gates,
            blocking=blocking,
        )

    if blocking:
        # Prefer specific verdicts already returned; else blocked.
        if any(g.status == "INVALID" for g in gates.values()):
            return VERDICT_INVALID, gates, blocking
        return VERDICT_BLOCKED, gates, blocking
    if executable and schema_version == MANIFEST_SCHEMA_VERSION_V11:
        return VERDICT_READY_CAMPAIGN, gates, []
    return VERDICT_READY, gates, []


def _git_is_ancestor(repo_root: Path, ancestor_sha: str, descendant_sha: str) -> bool:
    import subprocess

    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "merge-base",
                "--is-ancestor",
                ancestor_sha,
                descendant_sha,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return proc.returncode == 0


def _git_head_sha(repo_root: Path) -> str | None:
    import subprocess

    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    sha = proc.stdout.strip()
    return sha if len(sha) == 40 else None


def _apply_executable_campaign_gates(
    manifest: Mapping[str, Any],
    repo_root: Path,
    *,
    gates: dict[str, GateResult],
    blocking: list[str],
) -> None:
    """Additional fail-closed gates for executable v1.1 campaign manifests."""
    try:
        assert_manifest_matches_ratified_grid(manifest)
        gates["ratified_grid"] = _gate_pass(
            "Manifest matches Owner grid ratification 5175526900"
        )
    except SensitivityGridError as exc:
        gates["ratified_grid"] = _gate_blocked(str(exc))
        blocking.append("ratified_grid_mismatch")

    baseline_sha = str(manifest.get("correctness_baseline_sha") or "")
    head_sha = _git_head_sha(repo_root)
    if len(baseline_sha) != 40:
        gates["correctness_baseline"] = _gate_blocked(
            "correctness_baseline_sha missing or malformed"
        )
        blocking.append("correctness_baseline_missing")
    elif head_sha is None:
        gates["correctness_baseline"] = _gate_blocked(
            "Unable to resolve HEAD for correctness baseline ancestry check"
        )
        blocking.append("correctness_baseline_head_unresolved")
    elif not _git_is_ancestor(repo_root, baseline_sha, head_sha):
        gates["correctness_baseline"] = _gate_blocked(
            "correctness_baseline_sha is not an ancestor of HEAD",
            f"baseline:{baseline_sha}",
            f"head:{head_sha}",
        )
        blocking.append("correctness_baseline_not_ancestor")
    else:
        gates["correctness_baseline"] = _gate_pass(
            "Correctness baseline is ancestor of HEAD",
            f"baseline:{baseline_sha}",
            f"head:{head_sha}",
        )

    strategies = list(manifest.get("strategies") or [])
    if strategies != [STRATEGY_ID]:
        gates["strategy_set"] = _gate_blocked(
            f"strategies must be exactly [{STRATEGY_ID}]"
        )
        blocking.append("strategy_set_mismatch")
    else:
        gates["strategy_set"] = _gate_pass(f"Strategy set exact: {STRATEGY_ID}")

    # Window bindings provenance
    bindings = list(manifest.get("window_bindings") or [])
    windows = manifest.get("development_windows") or {}
    window_ids = tuple(windows.get("window_ids") or ())
    if len(bindings) != 39:
        gates["window_bindings"] = _gate_blocked(
            f"window_bindings count {len(bindings)} != 39"
        )
        blocking.append("window_bindings_count")
    else:
        binding_ids = [str(b.get("window_id")) for b in bindings]
        if tuple(binding_ids) != tuple(window_ids):
            gates["window_bindings"] = _gate_blocked(
                "window_bindings order/ids must match development_windows.window_ids"
            )
            blocking.append("window_bindings_order")
        elif any(
            not str(b.get("content_fingerprint") or "")
            or len(str(b.get("content_fingerprint"))) != 64
            for b in bindings
        ):
            gates["window_bindings"] = _gate_blocked(
                "each window_binding requires 64-hex content_fingerprint"
            )
            blocking.append("window_bindings_content_fp")
        elif any(b.get("purpose") != "development" for b in bindings):
            gates["window_bindings"] = _gate_blocked(
                "window_bindings purpose must be development"
            )
            blocking.append("window_bindings_purpose")
        else:
            gates["window_bindings"] = _gate_pass(
                "39 window bindings present with content fingerprints"
            )

    # Expansion determinism
    try:
        variants = expand_variants()
        breakdown = variant_breakdown(variants)
        runs = expand_runs(
            campaign_id=str(manifest.get("campaign_id")),
            window_ids=list(window_ids),
        )
        if breakdown["unique_total"] != EXPECTED_UNIQUE_VARIANTS:
            raise SensitivityGridError(
                f"unique variants {breakdown['unique_total']} != 21"
            )
        if len(runs) != EXPECTED_RUN_COUNT:
            raise SensitivityGridError(f"runs {len(runs)} != 819")
        expansion = manifest.get("expansion") or {}
        if expansion.get("expected_run_count") != EXPECTED_RUN_COUNT:
            raise SensitivityGridError("expected_run_count manifest mismatch")
        if expansion.get("max_run_count") != MAX_RUN_COUNT:
            raise SensitivityGridError("max_run_count manifest mismatch")
        gates["run_expansion"] = _gate_pass(
            "Deterministic expansion yields 21 variants / 819 runs",
            f"breakdown:{breakdown}",
        )
    except SensitivityGridError as exc:
        gates["run_expansion"] = _gate_blocked(str(exc))
        blocking.append("run_expansion_mismatch")

    # Manifest fingerprint self-check
    declared_fp = manifest.get("manifest_fingerprint")
    computed_fp = fingerprint_manifest(manifest)
    if declared_fp != computed_fp:
        gates["manifest_fingerprint"] = _gate_blocked(
            "Embedded manifest_fingerprint mismatch",
            f"declared:{declared_fp}",
            f"computed:{computed_fp}",
        )
        blocking.append("manifest_fingerprint_mismatch")
    else:
        gates["manifest_fingerprint"] = _gate_pass(
            "Manifest fingerprint matches canonical body hash",
            f"manifest_fingerprint:{computed_fp}",
        )

    bans = manifest.get("explicit_bans") or {}
    for key in (
        "holdout",
        "oos",
        "stress",
        "stage_b",
        "paper",
        "live",
        "echtgeld",
        "orders",
        "campaign_execution_auto_start",
    ):
        if bans.get(key) is not True:
            gates["replay_boundaries"] = _gate_blocked(
                f"explicit_bans.{key} must be true"
            )
            blocking.append(f"boundary_{key}")
            break
    else:
        if manifest.get("execution_mode") != "replay_only":
            gates["replay_boundaries"] = _gate_blocked(
                "execution_mode must be replay_only"
            )
            blocking.append("execution_mode")
        else:
            gates["replay_boundaries"] = _gate_pass(
                "Replay-only boundaries and capital/safety bans enforced"
            )

    output = manifest.get("output_contract") or {}
    if not output.get("evidence_namespace") or not output.get("artifact_root_template"):
        gates["output_contract"] = _gate_blocked("output_contract incomplete")
        blocking.append("output_contract")
    else:
        gates["output_contract"] = _gate_pass("Output/evidence contract present")


def run_repo_preflight(
    repo_root: Path | None = None,
    *,
    capability: EffectiveConfigCapability | None = None,
    effective_config_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run readiness gates against the live repository (no campaign runs)."""
    root = repo_root or PROJECT_ROOT
    cap = capability or discover_effective_config_capability(root)
    resolved_snapshot = _resolve_repo_effective_config_snapshot(
        root,
        capability=cap,
        snapshot=effective_config_snapshot,
    )
    gates: dict[str, GateResult] = {
        "parameter_control": check_parameter_control_canon(root),
        "regime_signal": check_regime_signal_correctness(root),
        "execution_economics": check_execution_economics(root),
        "dataset_provenance": check_dataset_provenance_capability(root),
        "cdb052_rankability_provenance": check_cdb052_rankability_provenance(root),
        "effective_config": check_effective_config_provenance(
            root,
            capability=cap,
            snapshot=resolved_snapshot,
        ),
        "frozen_boundaries": check_frozen_boundaries_repo(root),
        "holdout_isolation": check_holdout_isolation_repo(root),
    }
    blocking = [
        f"{name}:{gate.detail}" for name, gate in gates.items() if gate.status != "PASS"
    ]
    if blocking:
        verdict = VERDICT_BLOCKED
    else:
        verdict = VERDICT_READY

    evidence: dict[str, Any] = {
        "locked_development_selection_sha256": LOCKED_DEVELOPMENT_SELECTION_SHA256,
        "execution_economics_contract_version": ECONOMICS_CONTRACT_VERSION,
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "content_identity_schema_version": CONTENT_IDENTITY_SCHEMA_VERSION,
        "excluded_purposes": sorted(EXCLUDED_PURPOSES),
        "excluded_overlap_classes": sorted(EXCLUDED_OVERLAP_CLASSES),
        "effective_config_capability_available": cap.available,
    }
    if isinstance(resolved_snapshot, Mapping):
        fp = resolved_snapshot.get("snapshot_fingerprint")
        if isinstance(fp, str):
            evidence["effective_config_snapshot_fingerprint"] = fp
    return build_readiness_report(
        verdict=verdict,
        gates=gates,
        evidence=evidence,
        blocking_reasons=blocking,
        manifest_fingerprint=None,
    )


def run_manifest_preflight(
    manifest: Mapping[str, Any],
    repo_root: Path | None = None,
    *,
    capability: EffectiveConfigCapability | None = None,
    effective_config_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = repo_root or PROJECT_ROOT
    cap = capability or discover_effective_config_capability(root)
    resolved_snapshot = _resolve_repo_effective_config_snapshot(
        root,
        capability=cap,
        snapshot=effective_config_snapshot,
    )
    verdict, gates, blocking = validate_manifest_against_repo(
        manifest,
        root,
        capability=cap,
        effective_config_snapshot=resolved_snapshot,
    )
    try:
        mfp = fingerprint_manifest(manifest)
    except Exception:  # noqa: BLE001
        mfp = None
    evidence = {
        "execution_economics_contract_version": ECONOMICS_CONTRACT_VERSION,
        "locked_development_selection_sha256": LOCKED_DEVELOPMENT_SELECTION_SHA256,
        "manifest_schema_version": manifest.get("schema_version")
        or MANIFEST_SCHEMA_VERSION,
    }
    if isinstance(resolved_snapshot, Mapping):
        live_fp = resolved_snapshot.get("snapshot_fingerprint")
        if isinstance(live_fp, str):
            evidence["effective_config_snapshot_fingerprint"] = live_fp
    return build_readiness_report(
        verdict=verdict,
        gates=gates,
        evidence=evidence,
        blocking_reasons=blocking,
        manifest_fingerprint=mfp,
    )


def build_readiness_report(
    *,
    verdict: str,
    gates: Mapping[str, GateResult],
    evidence: Mapping[str, Any],
    blocking_reasons: Sequence[str],
    manifest_fingerprint: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": READINESS_SCHEMA_VERSION,
        "issue_ref": "#4153",
        "verdict": verdict,
        "gates": {name: gate.as_dict() for name, gate in gates.items()},
        "evidence": dict(evidence),
        "blocking_reasons": list(blocking_reasons),
        "manifest_fingerprint": manifest_fingerprint,
        "lr_status": "NO-GO",
        "allowed_claims": list(ALLOWED_CLAIMS),
        "forbidden_claims": list(FORBIDDEN_CLAIMS),
        "report_fingerprint": canonical_hash(
            {
                "verdict": verdict,
                "gates": {k: v.as_dict() for k, v in sorted(gates.items())},
                "blocking_reasons": list(blocking_reasons),
                "manifest_fingerprint": manifest_fingerprint,
            }
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Replay-only sensitivity campaign readiness preflight (#4153)"
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (default: detected from module path)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Optional experiment manifest to validate (synthetic/non-executable)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit readiness report as JSON on stdout",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    root = args.repo_root or PROJECT_ROOT

    if args.manifest is not None:
        manifest = load_manifest(args.manifest)
        report = run_manifest_preflight(manifest, root)
    else:
        report = run_repo_preflight(root)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"verdict={report['verdict']}")
        for name, gate in report["gates"].items():
            print(f"  gate.{name}={gate['status']}: {gate['detail']}")
        if report.get("blocking_reasons"):
            print("blocking_reasons:")
            for reason in report["blocking_reasons"]:
                print(f"  - {reason}")
        print(f"lr_status={report['lr_status']}")
        print("claims: readiness-preflight-only; no campaign execution")

    return 0 if report["verdict"] in {VERDICT_READY, VERDICT_READY_CAMPAIGN} else 2


if __name__ == "__main__":
    sys.exit(main())
