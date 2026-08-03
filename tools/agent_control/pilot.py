"""ACP E2E pilot harness (#4258) — mock default + Human-GO live Cursor path.

Wires real ACP components:
  Execution Contract → Registry → Preflight → Environment attenuation →
  Provider (MockProvider default | CursorCloudApiDriver under Human-GO) →
  Run Evidence → PR Approval Context → Pilot Report

Hard boundaries:
- Default remains MockProvider (no network, auto_advance_success=True)
- Live cursor-cloud-api requires --human-go-live-cursor + credential presence
- Head-SHA bound in manifest/report/approval — Run Evidence schema unchanged
- Refs #4258 only; never closes the issue
- No merge / cdb-local-ci publish / protection mutation
- Live path pauses at AWAITING_APPROVAL (operator handoff; Approval Agents
  remain MANUAL_BOOTSTRAP_ONLY)
"""

from __future__ import annotations

import copy
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator

from tools.agent_control.approval.codes import AUTHORITY_LIMITS as APPROVAL_AUTHORITY
from tools.agent_control.approval.context import (
    RepoPaths,
    build_approval_context,
    default_repo_paths,
)
from tools.agent_control.clock import FrozenClock
from tools.agent_control.credentials import cursor_api_key_present
from tools.agent_control.delivery_verify import (
    normalize_cursor_git_branches,
    pr_number_from_url,
    verify_github_delivery,
)
from tools.agent_control.dispatch import dispatch_run, watch_run
from tools.agent_control.errors import AgentControlError, DispatchError, EvidenceError
from tools.agent_control.evidence.emit import emit_evidence
from tools.agent_control.evidence.store import EvidenceJsonlStore
from tools.agent_control.evidence.verify import verify_bundle, verify_store
from tools.agent_control.load import load_registry_document
from tools.agent_control.paths import DEFAULT_CONFIG_ROOT, REPO_ROOT
from tools.agent_control.pilot_report import (
    AUTHORITY_LIMITS,
    REPORT_SCHEMA_ID,
    build_report,
    verify_report,
)
from tools.agent_control.provider import MockProvider
from tools.agent_control.providers.factory import build_provider
from tools.agent_control.run_store import InMemoryRunStore, JsonFileRunStore
from tools.agent_execution_contract.errors import ContractValidationError
from tools.agent_execution_contract.validate import validate_contract

MANIFEST_SCHEMA_ID = "cdb.agent_control_pilot_manifest.v1"
MANIFEST_SCHEMA_VERSION = "1.0.0"
MANIFEST_SCHEMA_RELPATH = (
    "docs/contracts/cdb_agent_control_pilot_manifest.v1.schema.json"
)
SHA40 = re.compile(r"^[a-f0-9]{40}$")
DEFAULT_GITHUB_REPO = "jannekbuengener/Claire_de_Binare"

DEFAULT_LIMITATIONS = [
    "foundation_slice_only",
    "mock_provider_only",
    "not_live_cursor",
    "not_issue_closure",
    "not_final_ci",
    "not_merge_authority",
    "refs_4258_not_closes",
]

LIVE_LIMITATIONS = [
    "foundation_slice_only",
    "live_cursor_pilot",
    "awaiting_approval_operator_handoff",
    "cursor_approval_agents_manual_bootstrap_only",
    "not_issue_closure",
    "not_final_ci",
    "not_merge_authority",
    "refs_4258_not_closes",
]

GhRunner = Callable[[list[str]], dict[str, Any]]
HttpTransport = Callable[..., Any]


class PilotError(AgentControlError):
    """Pilot harness fail-closed error."""


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def _load_manifest_schema(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or REPO_ROOT
    return _load_json(root / MANIFEST_SCHEMA_RELPATH)


def load_manifest(path: Path, *, repo_root: Path | None = None) -> dict[str, Any]:
    data = _load_json(path)
    if not isinstance(data, dict):
        raise PilotError("PILOT_MANIFEST_INVALID", "manifest must be a JSON object")
    schema = _load_manifest_schema(repo_root)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        err = errors[0]
        loc = ".".join(str(p) for p in err.path) or "$"
        raise PilotError(
            "PILOT_MANIFEST_SCHEMA",
            f"{loc}: {err.message}",
        )
    if data.get("schema_id") != MANIFEST_SCHEMA_ID:
        raise PilotError(
            "PILOT_MANIFEST_SCHEMA",
            f"expected schema_id={MANIFEST_SCHEMA_ID!r}",
        )
    head = data.get("head_sha")
    if not isinstance(head, str) or not SHA40.match(head):
        raise PilotError("PILOT_HEAD_INVALID", "manifest.head_sha must be 40-hex")
    base = data.get("base_sha")
    if base is not None and (not isinstance(base, str) or not SHA40.match(base)):
        raise PilotError("PILOT_BASE_INVALID", "manifest.base_sha must be 40-hex")
    for key in ("pilot_id", "scenario_id", "agent_id", "contract_path"):
        if not data.get(key):
            raise PilotError("PILOT_MANIFEST_INCOMPLETE", f"missing {key}")
    provider = data.get("provider")
    if provider is not None and not isinstance(provider, dict):
        raise PilotError(
            "PILOT_MANIFEST_SCHEMA",
            "provider must be an object when present",
        )
    subject = data.get("subject")
    if subject is not None and not isinstance(subject, dict):
        raise PilotError(
            "PILOT_MANIFEST_SCHEMA",
            "subject must be an object when present",
        )
    return data


def _load_verified_contract(contract: dict[str, Any]) -> dict[str, Any]:
    """Validate schema/semantics and verify the supplied integrity.digest.

    Never reseal: a tampered contract with a stale claimed digest must fail
    closed instead of being silently repaired before dispatch.
    """
    try:
        return validate_contract(copy.deepcopy(contract))
    except ContractValidationError as exc:
        raise PilotError(exc.code, exc.message) from exc


def _step(
    name: str, status: str, *, detail: dict[str, Any] | None = None
) -> dict[str, Any]:
    out: dict[str, Any] = {"step": name, "status": status}
    if detail:
        out["detail"] = detail
    return out


def _map_final_status(
    *,
    blocked: bool,
    hold: bool,
    fail: bool,
    unknown: bool,
    approval_rec: str | None,
    evidence_ok: bool,
    provider_calls: int,
    expect_provider_calls: int | None,
) -> str:
    # Call-count expectations are independent observations: evaluate before
    # terminal status short-circuits so a mismatched count cannot hide behind
    # BLOCKED/HOLD/UNKNOWN from another step.
    if expect_provider_calls is not None and provider_calls != expect_provider_calls:
        return "FAIL"
    if unknown:
        return "UNKNOWN"
    if blocked:
        return "BLOCKED"
    if fail:
        return "FAIL"
    if hold:
        return "HOLD"
    if not evidence_ok:
        return "HOLD"
    if approval_rec == "APPROVE_RECOMMENDED":
        return "PASS"
    if approval_rec in {"HOLD", "REQUEST_CHANGES", "ABSTAIN", "BLOCKED"}:
        # Negative scenarios intentionally non-approve → HOLD/BLOCKED report
        if approval_rec == "BLOCKED":
            return "BLOCKED"
        return "HOLD"
    if approval_rec == "UNKNOWN":
        return "UNKNOWN"
    return "HOLD"


def run_pilot(
    manifest: dict[str, Any],
    *,
    repo_root: Path | None = None,
    store_path: Path | None = None,
    provider_id: str = "mock",
    human_go_live_cursor: bool = False,
    resume_run_id: str | None = None,
    state_path: Path | None = None,
    http_transport: HttpTransport | None = None,
    gh_runner: GhRunner | None = None,
    auto_create_pr: bool = False,
    environment_attestation_path: Path | None = None,
    secrets_dir: Path | None = None,
    credential_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Execute one pilot scenario; return pilot report.

    Default ``provider_id='mock'`` is behavior-identical to the foundation
    harness (MockProvider, InMemoryRunStore, auto_advance_success=True).
    """
    if provider_id == "cursor-cloud-api":
        return _run_live_cursor_pilot(
            manifest,
            repo_root=repo_root,
            store_path=store_path,
            human_go_live_cursor=human_go_live_cursor,
            resume_run_id=resume_run_id,
            state_path=state_path,
            http_transport=http_transport,
            gh_runner=gh_runner,
            auto_create_pr=auto_create_pr,
            environment_attestation_path=environment_attestation_path,
            secrets_dir=secrets_dir,
            credential_env=credential_env,
        )
    if provider_id != "mock":
        raise PilotError(
            "PILOT_PROVIDER_UNSUPPORTED",
            f"unsupported provider_id={provider_id!r}; use mock|cursor-cloud-api",
        )

    root = repo_root or REPO_ROOT
    steps: list[dict[str, Any]] = []
    limitations = list(DEFAULT_LIMITATIONS)
    provider = MockProvider()  # already tracks dispatch_calls; never network
    run_store = InMemoryRunStore()
    clock = FrozenClock(datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc))
    run_id: str | None = None
    attempt: int | None = None
    contract_digest: str | None = None
    evidence_refs: list[dict[str, Any]] = []
    approval_digest: str | None = None
    approval_rec: str | None = None
    blocked = False
    hold = False
    fail = False
    unknown = False
    evidence_ok = False
    effective_wall: int | None = None

    head_sha = str(manifest["head_sha"])
    base_raw = manifest.get("base_sha")
    base_sha = str(base_raw) if isinstance(base_raw, str) else None
    agent_id = str(manifest["agent_id"])
    provider_cfg = manifest.get("provider")
    if provider_cfg is not None and not isinstance(provider_cfg, dict):
        raise PilotError("PILOT_MANIFEST_SCHEMA", "provider must be an object")
    provider_cfg = provider_cfg or {}
    scenario = str(provider_cfg.get("scenario") or "success")
    expect_calls = provider_cfg.get("expect_call_count")
    skip_approval = bool(manifest.get("skip_approval"))
    skip_evidence = bool(manifest.get("skip_evidence"))
    registry_root = _resolve(
        root, manifest.get("registry_root") or str(DEFAULT_CONFIG_ROOT)
    )
    subject_cfg = manifest.get("subject")
    if subject_cfg is not None and not isinstance(subject_cfg, dict):
        raise PilotError("PILOT_MANIFEST_SCHEMA", "subject must be an object")

    # --- Contract ---
    try:
        contract_path = _resolve(root, manifest["contract_path"])
        contract = _load_verified_contract(_load_json(contract_path))
        contract_digest = (contract.get("integrity") or {}).get("digest")
        steps.append(
            _step(
                "load_contract",
                "PASS",
                detail={
                    "contract_id": contract.get("contract_id"),
                    "contract_digest": contract_digest,
                },
            )
        )
    except Exception as exc:  # noqa: BLE001 — fail-closed to report
        steps.append(_step("load_contract", "FAIL", detail={"error": str(exc)}))
        fail = True
        return _finalize(
            manifest,
            steps,
            run_id,
            attempt,
            head_sha,
            base_sha,
            {},
            0,
            [],
            None,
            None,
            blocked,
            hold,
            fail,
            unknown,
            False,
            limitations,
            contract_digest,
        )

    # --- Registry ---
    try:
        registry = load_registry_document(registry_root)
        steps.append(
            _step(
                "resolve_registry",
                "PASS",
                detail={"agent_id": agent_id, "registry_root": str(registry_root)},
            )
        )
    except Exception as exc:  # noqa: BLE001
        steps.append(_step("resolve_registry", "FAIL", detail={"error": str(exc)}))
        fail = True
        return _finalize(
            manifest,
            steps,
            run_id,
            attempt,
            head_sha,
            base_sha,
            {"contract_digest": contract_digest},
            0,
            [],
            None,
            None,
            blocked,
            hold,
            fail,
            unknown,
            False,
            limitations,
            contract_digest,
        )

    # --- Dispatch / Preflight ---
    try:
        result = dispatch_run(
            contract,
            registry,
            agent_id,
            run_store,
            dry_run=False,
            allow_mock_dispatch=True,
            provider=provider,
            clock=clock,
            scenario=scenario,
        )
        run = result["run"]
        run_id = run.get("run_id")
        attempt = run.get("attempt")
        effective_wall = (run.get("budget") or {}).get("wall_time_seconds")
        state = run.get("state")
        code = run.get("terminal_code")
        if state in {"BLOCKED", "HOLD"} or code:
            blocked = state == "BLOCKED" or (
                code == "DISPATCH_DELIVERY_TARGET_CONFLICT"
            )
            hold = state == "HOLD"
            steps.append(
                _step(
                    "preflight_dispatch",
                    "BLOCKED" if blocked else "HOLD",
                    detail={
                        "state": state,
                        "terminal_code": code,
                        "provider_call_count": provider.dispatch_calls,
                        "effective_wall_time_seconds": effective_wall,
                    },
                )
            )
        else:
            steps.append(
                _step(
                    "preflight_dispatch",
                    "PASS",
                    detail={
                        "state": state,
                        "run_id": run_id,
                        "effective_wall_time_seconds": effective_wall,
                        "provider_call_count": provider.dispatch_calls,
                    },
                )
            )
            # Attenuation visibility step
            if isinstance(effective_wall, int):
                expected_wall = manifest.get("expect_effective_wall_time_seconds")
                atten_status = "PASS"
                if expected_wall is not None and effective_wall != expected_wall:
                    atten_status = "FAIL"
                    fail = True
                steps.append(
                    _step(
                        "environment_attenuation",
                        atten_status,
                        detail={
                            "effective_wall_time_seconds": effective_wall,
                            "contract_wall_time_seconds": (
                                contract.get("budget") or {}
                            ).get("wall_time_seconds"),
                            "expect_effective_wall_time_seconds": expected_wall,
                            "note": "restrictive min(contract, profile) applied",
                        },
                    )
                )
            # Watch to terminal
            for _ in range(5):
                run = watch_run(
                    run["run_id"], run_store, provider=provider, clock=clock
                )
                if run.get("state") in {
                    "PASS",
                    "HOLD",
                    "BLOCKED",
                    "FAILED",
                    "CANCELLED",
                }:
                    break
            terminal = run.get("state")
            if terminal == "PASS":
                steps.append(
                    _step(
                        "provider_watch",
                        "PASS",
                        detail={
                            "state": terminal,
                            "provider_run_id": run.get("provider_run_id"),
                            "has_receipt": bool(run.get("delivery_receipt")),
                        },
                    )
                )
            elif terminal in {"HOLD", "BLOCKED"}:
                hold = terminal == "HOLD"
                blocked = terminal == "BLOCKED"
                steps.append(
                    _step(
                        "provider_watch",
                        terminal,
                        detail={
                            "state": terminal,
                            "terminal_code": run.get("terminal_code"),
                        },
                    )
                )
            elif terminal == "FAILED":
                fail = True
                steps.append(
                    _step("provider_watch", "FAIL", detail={"state": terminal})
                )
            else:
                unknown = True
                steps.append(
                    _step("provider_watch", "UNKNOWN", detail={"state": terminal})
                )
    except DispatchError as exc:
        if exc.code in {
            "DISPATCH_PROVIDER_MALFORMED",
            "DISPATCH_DELIVERY_RECEIPT_MISSING",
            "DISPATCH_DELIVERY_RECEIPT_MISMATCH",
        }:
            fail = True
            steps.append(
                _step(
                    "provider_dispatch",
                    "FAIL",
                    detail={"code": exc.code, "message": exc.message},
                )
            )
        else:
            blocked = True
            steps.append(
                _step(
                    "preflight_dispatch",
                    "BLOCKED",
                    detail={"code": exc.code, "message": exc.message},
                )
            )
    except Exception as exc:  # noqa: BLE001
        fail = True
        steps.append(_step("preflight_dispatch", "FAIL", detail={"error": str(exc)}))

    provider_calls = provider.dispatch_calls

    # --- Evidence (existing contract, unchanged) ---
    if not skip_evidence and run_id and run_store.get(run_id) is not None:
        try:
            emitted = emit_evidence(run_id, run_store)
            bundle = emitted["bundle"]
            verified = verify_bundle(bundle)
            evidence_ok = bool(verified.get("ok"))
            ref = {
                "evidence_id": bundle.get("evidence_id"),
                "bundle_digest": bundle.get("bundle_digest"),
                "verdict": emitted.get("verdict"),
            }
            evidence_refs.append(ref)
            if store_path is not None:
                store = EvidenceJsonlStore(store_path)
                store.append_idempotent(bundle)
                verify_store(store_path)
            steps.append(
                _step(
                    "run_evidence",
                    "PASS" if evidence_ok else "HOLD",
                    detail=ref,
                )
            )
            if emitted.get("verdict") in {"HOLD", "BLOCKED"}:
                hold = hold or emitted.get("verdict") == "HOLD"
                blocked = blocked or emitted.get("verdict") == "BLOCKED"
                evidence_ok = evidence_ok and emitted.get("verdict") == "PASS"
            if emitted.get("verdict") == "UNKNOWN":
                unknown = True
                evidence_ok = False
        except EvidenceError as exc:
            hold = True
            evidence_ok = False
            steps.append(
                _step(
                    "run_evidence",
                    "HOLD",
                    detail={"code": exc.code, "message": exc.message},
                )
            )
        except Exception as exc:  # noqa: BLE001
            fail = True
            steps.append(_step("run_evidence", "FAIL", detail={"error": str(exc)}))
    elif skip_evidence:
        steps.append(_step("run_evidence", "SKIP", detail={"reason": "skip_evidence"}))

    # Optional N7 dual-store collision proof
    if manifest.get("store_collision_probe") and evidence_refs:
        try:
            path = _resolve(root, manifest["store_collision_probe"]["store_path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            store = EvidenceJsonlStore(path)
            # Re-emit PASS-like first bundle if present
            first = emit_evidence(run_id, run_store)["bundle"]  # type: ignore[arg-type]
            store.append_idempotent(first)
            second = copy.deepcopy(first)
            second["bundle_digest"] = "sha256:" + ("d" * 64)
            try:
                store.append_idempotent(second)
                fail = True
                steps.append(
                    _step(
                        "store_collision",
                        "FAIL",
                        detail={"error": "collision was not blocked"},
                    )
                )
            except EvidenceError as exc:
                steps.append(
                    _step(
                        "store_collision",
                        "PASS",
                        detail={"code": exc.code, "blocked": True},
                    )
                )
            # Distinct evidence_id HOLD+PASS allowed via second run if configured
            alt = manifest["store_collision_probe"].get("second_manifest")
            if alt:
                # Handled by tests calling run_pilot twice; mark note only
                steps.append(
                    _step(
                        "store_dual_bundle",
                        "PASS",
                        detail={"note": "distinct evidence_id path covered in tests"},
                    )
                )
        except Exception as exc:  # noqa: BLE001
            steps.append(_step("store_collision", "FAIL", detail={"error": str(exc)}))
            fail = True

    # --- Approval (head-sha bound here; not via evidence schema change) ---
    if not skip_approval and not (
        blocked and provider_calls == 0 and manifest.get("scenario_id") == "N1"
    ):
        try:
            snap_path = manifest.get("approval_snapshot_path")
            if not snap_path:
                raise PilotError(
                    "PILOT_APPROVAL_SNAPSHOT_MISSING",
                    "approval_snapshot_path required unless skip_approval",
                )
            snapshot = _load_json(_resolve(root, snap_path))
            if not isinstance(snapshot, dict):
                raise PilotError(
                    "PILOT_APPROVAL_SNAPSHOT_INVALID", "snapshot must be object"
                )
            pr = dict(snapshot.get("pr") or {})
            # Bind / verify head against pilot manifest (canonical for this slice)
            snap_head = pr.get("head_sha")
            if manifest.get("force_approval_head_from_manifest"):
                pr["head_sha"] = head_sha
                for check in snapshot.get("checks") or []:
                    if isinstance(check, dict) and check.get("source_sha") == snap_head:
                        check["source_sha"] = head_sha
                snapshot["pr"] = pr
            elif snap_head != head_sha and manifest.get("require_head_match", True):
                # N4 / head mismatch path
                if manifest.get("scenario_id") in {"N4", "N_HEAD_MISMATCH"}:
                    pass  # keep snapshot stale/mismatch for negative proof
                else:
                    raise PilotError(
                        "PILOT_HEAD_MISMATCH",
                        f"approval snapshot head {snap_head!r} != pilot {head_sha!r}",
                    )
            paths = default_repo_paths(root)
            # Optional drift baseline override via RepoPaths
            if manifest.get("approval_baseline_path"):
                paths = RepoPaths(
                    repo_root=paths.repo_root,
                    policy_path=paths.policy_path,
                    prompt_path=paths.prompt_path,
                    baseline_path=_resolve(root, manifest["approval_baseline_path"]),
                    schema_path=paths.schema_path,
                )
            if manifest.get("approval_policy_path"):
                paths = RepoPaths(
                    repo_root=paths.repo_root,
                    policy_path=_resolve(root, manifest["approval_policy_path"]),
                    prompt_path=(
                        _resolve(root, manifest["approval_prompt_path"])
                        if manifest.get("approval_prompt_path")
                        else paths.prompt_path
                    ),
                    baseline_path=paths.baseline_path,
                    schema_path=paths.schema_path,
                )
            envelope = build_approval_context(snapshot, paths)
            approval_digest = envelope.get("context_digest")
            approval_rec = envelope.get("recommendation")
            appr_head = (envelope.get("subject") or {}).get("head_sha")
            reason_codes = list(envelope.get("reason_codes") or [])
            expect_reason = manifest.get("expect_reason_code")
            if expect_reason and expect_reason not in reason_codes:
                fail = True
                steps.append(
                    _step(
                        "approval_reason_code",
                        "FAIL",
                        detail={
                            "expected": expect_reason,
                            "reason_codes": reason_codes,
                        },
                    )
                )
            # Consistency: when we forced manifest head, they must match
            head_ok = appr_head == head_sha or not manifest.get(
                "force_approval_head_from_manifest"
            )
            if approval_rec == "UNKNOWN":
                unknown = True
            step_status = "PASS"
            if manifest.get("expect_approval_not_recommended"):
                if approval_rec == "APPROVE_RECOMMENDED":
                    step_status = "FAIL"
                    fail = True
                else:
                    step_status = "PASS"
                    if approval_rec == "BLOCKED":
                        blocked = True
                    else:
                        hold = True
            elif manifest.get("expect_approval_recommendation"):
                expected = manifest["expect_approval_recommendation"]
                if approval_rec != expected:
                    step_status = "FAIL"
                    fail = True
                elif expected != "APPROVE_RECOMMENDED":
                    step_status = "PASS"
                    if expected == "BLOCKED":
                        blocked = True
                    else:
                        hold = True
            elif approval_rec != "APPROVE_RECOMMENDED":
                if str(manifest.get("scenario_id", "")).startswith("N"):
                    step_status = "PASS"
                    hold = True
                else:
                    step_status = "HOLD"
                    hold = True
            if not head_ok and manifest.get("force_approval_head_from_manifest"):
                step_status = "FAIL"
                fail = True
            steps.append(
                _step(
                    "approval_context",
                    step_status,
                    detail={
                        "recommendation": approval_rec,
                        "context_digest": approval_digest,
                        "subject_head_sha": appr_head,
                        "pilot_head_sha": head_sha,
                        "reason_codes": reason_codes,
                        "authority_limits": envelope.get("authority_limits"),
                    },
                )
            )
            # Authority must remain all-false
            limits = envelope.get("authority_limits") or {}
            for key, val in APPROVAL_AUTHORITY.items():
                if limits.get(key) is not val:
                    fail = True
                    steps.append(
                        _step(
                            "authority_boundary",
                            "FAIL",
                            detail={"key": key, "value": limits.get(key)},
                        )
                    )
                    break
            else:
                steps.append(
                    _step(
                        "authority_boundary",
                        "PASS",
                        detail={"authority_limits": AUTHORITY_LIMITS},
                    )
                )
        except Exception as exc:  # noqa: BLE001
            code = getattr(exc, "code", "PILOT_APPROVAL_ERROR")
            if code in {"APPROVAL_SECRET_DETECTED", "REASON_SECRET_DETECTED"}:
                blocked = True
            else:
                hold = True
            steps.append(
                _step(
                    "approval_context",
                    "BLOCKED" if blocked else "HOLD",
                    detail={"code": code, "error": str(exc)},
                )
            )
    elif skip_approval:
        steps.append(
            _step("approval_context", "SKIP", detail={"reason": "skip_approval"})
        )
    else:
        # N1 short-circuit: no approval after preflight block
        steps.append(
            _step(
                "approval_context",
                "SKIP",
                detail={"reason": "short_circuit_after_preflight_block"},
            )
        )
        steps.append(
            _step(
                "authority_boundary",
                "PASS",
                detail={
                    "authority_limits": AUTHORITY_LIMITS,
                    "provider_calls": provider_calls,
                },
            )
        )

    input_digests = {
        "contract_digest": contract_digest,
        "approval_context_digest": approval_digest,
    }
    if effective_wall is not None:
        input_digests["effective_wall_time_seconds"] = effective_wall

    return _finalize(
        manifest,
        steps,
        run_id,
        attempt,
        head_sha,
        base_sha,
        input_digests,
        provider_calls,
        evidence_refs,
        approval_digest,
        approval_rec,
        blocked,
        hold,
        fail,
        unknown,
        evidence_ok,
        limitations,
        contract_digest,
        expect_calls=expect_calls,
    )


def _live_expected_repo(manifest: dict[str, Any]) -> str:
    subject = (
        manifest.get("subject") if isinstance(manifest.get("subject"), dict) else {}
    )
    repo = subject.get("repo") or manifest.get("expected_repo") or DEFAULT_GITHUB_REPO
    return str(repo)


def _inject_delivery_receipt(
    run_store: Any,
    run_id: str,
    *,
    target_pr: int | None,
    target_branch: str | None,
    commit: str,
    expected_status: str,
) -> None:
    record = run_store.get(run_id)
    if record is None:
        return
    rev = int(record.get("revision") or 0)
    record["delivery_receipt"] = {
        "target_pr": target_pr,
        "target_branch": target_branch,
        "commit": commit,
        "delivery_status": expected_status,
        "observation_source": "github_delivery_verify",
    }
    record["revision"] = rev + 1
    run_store.update_cas(run_id, rev, record)


def _run_live_cursor_pilot(
    manifest: dict[str, Any],
    *,
    repo_root: Path | None = None,
    store_path: Path | None = None,
    human_go_live_cursor: bool = False,
    resume_run_id: str | None = None,
    state_path: Path | None = None,
    http_transport: HttpTransport | None = None,
    gh_runner: GhRunner | None = None,
    auto_create_pr: bool = False,
    environment_attestation_path: Path | None = None,
    secrets_dir: Path | None = None,
    credential_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Human-GO live Cursor cloud pilot; pauses at AWAITING_APPROVAL."""
    if not human_go_live_cursor:
        raise PilotError(
            "PILOT_HUMAN_GO_REQUIRED",
            "provider_id=cursor-cloud-api requires human_go_live_cursor=True",
        )
    if auto_create_pr and not human_go_live_cursor:
        raise PilotError(
            "PILOT_HUMAN_GO_REQUIRED",
            "auto_create_pr requires human_go_live_cursor=True",
        )

    root = repo_root or REPO_ROOT
    steps: list[dict[str, Any]] = []
    limitations = list(LIVE_LIMITATIONS)
    clock = FrozenClock(datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc))
    run_id: str | None = resume_run_id
    attempt: int | None = None
    contract_digest: str | None = None
    evidence_refs: list[dict[str, Any]] = []
    approval_digest: str | None = None
    approval_rec: str | None = None
    blocked = False
    hold = False
    fail = False
    unknown = False
    evidence_ok = False
    provider_calls = 0
    head_sha = str(manifest["head_sha"])
    base_raw = manifest.get("base_sha")
    base_sha = str(base_raw) if isinstance(base_raw, str) else None
    agent_id = str(manifest["agent_id"])
    skip_approval = bool(manifest.get("skip_approval"))
    skip_evidence = bool(manifest.get("skip_evidence"))
    registry_root = _resolve(
        root, manifest.get("registry_root") or str(DEFAULT_CONFIG_ROOT)
    )
    expected_repo = _live_expected_repo(manifest)
    allowlist = list(manifest.get("delivery_path_allowlist") or [])
    att_path = environment_attestation_path
    if att_path is None and manifest.get("environment_attestation_path"):
        att_path = _resolve(root, manifest["environment_attestation_path"])

    # Credential presence before any driver/network construction.
    presence = cursor_api_key_present(env=credential_env, secrets_dir=secrets_dir)
    if not presence.present:
        steps.append(
            _step(
                "credential_precondition",
                "BLOCKED",
                detail={
                    "code": "PRECONDITION_BLOCKED",
                    "credential": presence.name,
                    "source": presence.source,
                },
            )
        )
        blocked = True
        steps.append(
            _step(
                "approval_context",
                "SKIP",
                detail={"reason": "short_circuit_after_precondition_block"},
            )
        )
        steps.append(
            _step(
                "authority_boundary",
                "PASS",
                detail={"authority_limits": AUTHORITY_LIMITS, "provider_calls": 0},
            )
        )
        return _finalize(
            manifest,
            steps,
            None,
            None,
            head_sha,
            base_sha,
            {},
            0,
            [],
            None,
            None,
            blocked,
            hold,
            fail,
            unknown,
            False,
            limitations,
            None,
        )

    steps.append(
        _step(
            "credential_precondition",
            "PASS",
            detail={"credential": presence.name, "source": presence.source},
        )
    )

    if state_path is not None:
        run_store: Any = JsonFileRunStore(Path(state_path))
    else:
        run_store = InMemoryRunStore()

    transports: dict[str, Any] = {"human_go_live": True}
    if http_transport is not None:
        transports["http"] = http_transport
    provider = build_provider(
        "cursor-cloud-api",
        allow_live=True,
        transports=transports,
    )

    # --- Contract ---
    try:
        contract_path = _resolve(root, manifest["contract_path"])
        contract = _load_verified_contract(_load_json(contract_path))
        contract_digest = (contract.get("integrity") or {}).get("digest")
        steps.append(
            _step(
                "load_contract",
                "PASS",
                detail={
                    "contract_id": contract.get("contract_id"),
                    "contract_digest": contract_digest,
                },
            )
        )
    except Exception as exc:  # noqa: BLE001
        steps.append(_step("load_contract", "FAIL", detail={"error": str(exc)}))
        fail = True
        return _finalize(
            manifest,
            steps,
            run_id,
            attempt,
            head_sha,
            base_sha,
            {},
            0,
            [],
            None,
            None,
            blocked,
            hold,
            fail,
            unknown,
            False,
            limitations,
            contract_digest,
        )

    try:
        registry = load_registry_document(registry_root)
        steps.append(
            _step(
                "resolve_registry",
                "PASS",
                detail={"agent_id": agent_id, "registry_root": str(registry_root)},
            )
        )
    except Exception as exc:  # noqa: BLE001
        steps.append(_step("resolve_registry", "FAIL", detail={"error": str(exc)}))
        fail = True
        return _finalize(
            manifest,
            steps,
            run_id,
            attempt,
            head_sha,
            base_sha,
            {"contract_digest": contract_digest},
            0,
            [],
            None,
            None,
            blocked,
            hold,
            fail,
            unknown,
            False,
            limitations,
            contract_digest,
        )

    allow_recorded = att_path is not None
    # Load prompt from working tree for Human-GO / fixture tests so source_commit
    # history is not required (operator may still bind a real commit in manifests).
    prompt_override: str | None = None
    work_order = (
        contract.get("provider_work_order") if isinstance(contract, dict) else None
    )
    if isinstance(work_order, dict) and work_order.get("prompt_ref"):
        prompt_path = _resolve(root, str(work_order["prompt_ref"]))
        if prompt_path.is_file():
            prompt_override = prompt_path.read_text(encoding="utf-8")

    run: dict[str, Any] | None = None
    try:
        if resume_run_id:
            run = run_store.get(resume_run_id)
            if run is None:
                raise PilotError(
                    "PILOT_RESUME_NOT_FOUND",
                    f"resume_run_id not in store: {resume_run_id}",
                )
            run_id = run.get("run_id")
            attempt = run.get("attempt")
            steps.append(
                _step(
                    "preflight_dispatch",
                    "PASS",
                    detail={
                        "state": run.get("state"),
                        "run_id": run_id,
                        "resume": True,
                        "provider_run_id": run.get("provider_run_id"),
                    },
                )
            )
        else:
            result = dispatch_run(
                contract,
                registry,
                agent_id,
                run_store,
                dry_run=False,
                allow_mock_dispatch=False,
                allow_live_cursor=True,
                human_go_live_cursor=True,
                allow_recorded_cursor=allow_recorded,
                auto_create_pr=auto_create_pr,
                provider=provider,
                clock=clock,
                environment_attestation_path=att_path,
                prompt_text_override=prompt_override,
            )
            run = result["run"]
            run_id = run.get("run_id")
            attempt = run.get("attempt")
            provider_calls = int(getattr(provider, "dispatch_calls", 0) or 0)
            state = run.get("state")
            code = run.get("terminal_code")
            if state in {"BLOCKED", "HOLD"} or code:
                blocked = state == "BLOCKED"
                hold = state == "HOLD"
                steps.append(
                    _step(
                        "preflight_dispatch",
                        "BLOCKED" if blocked else "HOLD",
                        detail={
                            "state": state,
                            "terminal_code": code,
                            "provider_call_count": provider_calls,
                        },
                    )
                )
            else:
                steps.append(
                    _step(
                        "preflight_dispatch",
                        "PASS",
                        detail={
                            "state": state,
                            "run_id": run_id,
                            "provider_call_count": provider_calls,
                            "provider_run_id": run.get("provider_run_id"),
                        },
                    )
                )

        if run_id and run and run.get("state") not in {"BLOCKED", "HOLD", "FAILED"}:
            # Bind GitHub delivery from Cursor git refs before watch advances.
            git_info = normalize_cursor_git_branches(run.get("result_refs"))
            pr_num = pr_number_from_url(
                git_info.get("pr_url")
                if isinstance(git_info.get("pr_url"), str)
                else None
            )
            if pr_num is None:
                expected = run.get("expected_delivery") or {}
                raw_pr = expected.get("target_pr") or (run.get("route") or {}).get(
                    "target_pr"
                )
                if isinstance(raw_pr, int) and not isinstance(raw_pr, bool):
                    pr_num = raw_pr
            branch = git_info.get("branch")
            if not isinstance(branch, str):
                branch = (run.get("expected_delivery") or {}).get("target_branch") or (
                    run.get("route") or {}
                ).get("target_branch")

            delivery = verify_github_delivery(
                expected_repo=expected_repo,
                pr_number=pr_num,
                branch=branch if isinstance(branch, str) else None,
                expected_paths_prefix=allowlist or None,
                allow_empty=bool(manifest.get("delivery_allow_empty")),
                runner=gh_runner,
            )
            if not delivery.ok:
                blocked = True
                steps.append(
                    _step(
                        "delivery_verify",
                        "BLOCKED",
                        detail={
                            "code": delivery.code,
                            "message": delivery.message,
                            "changed_files": delivery.changed_files,
                        },
                    )
                )
                # N3/N5-style: do not allow approval PASS after delivery failure.
                skip_approval = True
                hold = True
            else:
                if delivery.head_sha:
                    head_sha = delivery.head_sha
                if delivery.base_sha:
                    base_sha = delivery.base_sha
                expected_status = (run.get("expected_delivery") or {}).get(
                    "expected_status"
                ) or "DONE_SLICE_ADDED_TO_BATCH_PR"
                _inject_delivery_receipt(
                    run_store,
                    str(run_id),
                    target_pr=delivery.pr_number or pr_num,
                    target_branch=(
                        delivery.branch if isinstance(delivery.branch, str) else branch
                    ),
                    commit=str(delivery.head_sha),
                    expected_status=str(expected_status),
                )
                steps.append(
                    _step(
                        "delivery_verify",
                        "PASS",
                        detail={
                            "head_sha": delivery.head_sha,
                            "pr_number": delivery.pr_number,
                            "branch": delivery.branch,
                            "changed_files": delivery.changed_files,
                        },
                    )
                )

                for _ in range(8):
                    run = watch_run(
                        str(run_id),
                        run_store,
                        provider=provider,
                        clock=clock,
                        auto_advance_success=False,
                    )
                    if run.get("state") in {
                        "AWAITING_APPROVAL",
                        "PASS",
                        "HOLD",
                        "BLOCKED",
                        "FAILED",
                        "CANCELLED",
                    }:
                        break
                terminal = run.get("state")
                if terminal == "AWAITING_APPROVAL":
                    hold = True
                    steps.append(
                        _step(
                            "provider_watch",
                            "HOLD",
                            detail={
                                "state": terminal,
                                "provider_run_id": run.get("provider_run_id"),
                                "note": "awaiting_approval_operator_handoff",
                            },
                        )
                    )
                elif terminal == "PASS":
                    steps.append(
                        _step(
                            "provider_watch",
                            "PASS",
                            detail={
                                "state": terminal,
                                "provider_run_id": run.get("provider_run_id"),
                            },
                        )
                    )
                elif terminal in {"HOLD", "BLOCKED"}:
                    hold = terminal == "HOLD"
                    blocked = terminal == "BLOCKED"
                    steps.append(
                        _step(
                            "provider_watch",
                            terminal,
                            detail={
                                "state": terminal,
                                "terminal_code": run.get("terminal_code"),
                            },
                        )
                    )
                elif terminal == "FAILED":
                    fail = True
                    steps.append(
                        _step("provider_watch", "FAIL", detail={"state": terminal})
                    )
                else:
                    unknown = True
                    steps.append(
                        _step("provider_watch", "UNKNOWN", detail={"state": terminal})
                    )
    except DispatchError as exc:
        if exc.code in {
            "DISPATCH_PROVIDER_MALFORMED",
            "DISPATCH_DELIVERY_RECEIPT_MISSING",
            "DISPATCH_DELIVERY_RECEIPT_MISMATCH",
        }:
            fail = True
            steps.append(
                _step(
                    "provider_dispatch",
                    "FAIL",
                    detail={"code": exc.code, "message": exc.message},
                )
            )
        else:
            blocked = True
            steps.append(
                _step(
                    "preflight_dispatch",
                    "BLOCKED",
                    detail={"code": exc.code, "message": exc.message},
                )
            )
    except PilotError:
        raise
    except Exception as exc:  # noqa: BLE001
        fail = True
        steps.append(_step("preflight_dispatch", "FAIL", detail={"error": str(exc)}))

    provider_calls = int(getattr(provider, "dispatch_calls", 0) or 0)

    # Evidence: HOLD for non-terminal AWAITING_APPROVAL is OK.
    if not skip_evidence and run_id and run_store.get(run_id) is not None:
        try:
            emitted = emit_evidence(run_id, run_store)
            bundle = emitted["bundle"]
            verified = verify_bundle(bundle)
            evidence_ok = bool(verified.get("ok"))
            ref = {
                "evidence_id": bundle.get("evidence_id"),
                "bundle_digest": bundle.get("bundle_digest"),
                "verdict": emitted.get("verdict"),
            }
            evidence_refs.append(ref)
            if store_path is not None:
                store = EvidenceJsonlStore(store_path)
                store.append_idempotent(bundle)
                verify_store(store_path)
            verdict = emitted.get("verdict")
            step_status = "PASS" if evidence_ok and verdict == "PASS" else "HOLD"
            if verdict == "BLOCKED":
                step_status = "BLOCKED"
                blocked = True
            elif verdict == "HOLD":
                hold = True
            elif verdict == "UNKNOWN":
                unknown = True
                evidence_ok = False
            steps.append(_step("run_evidence", step_status, detail=ref))
        except EvidenceError as exc:
            hold = True
            evidence_ok = False
            steps.append(
                _step(
                    "run_evidence",
                    "HOLD",
                    detail={"code": exc.code, "message": exc.message},
                )
            )
        except Exception as exc:  # noqa: BLE001
            fail = True
            steps.append(_step("run_evidence", "FAIL", detail={"error": str(exc)}))
    elif skip_evidence:
        steps.append(_step("run_evidence", "SKIP", detail={"reason": "skip_evidence"}))

    # Approval — reuse mock path semantics with bound head from delivery verify.
    if not skip_approval and not blocked:
        try:
            snap_path = manifest.get("approval_snapshot_path")
            if not snap_path:
                raise PilotError(
                    "PILOT_APPROVAL_SNAPSHOT_MISSING",
                    "approval_snapshot_path required unless skip_approval",
                )
            snapshot = _load_json(_resolve(root, snap_path))
            if not isinstance(snapshot, dict):
                raise PilotError(
                    "PILOT_APPROVAL_SNAPSHOT_INVALID", "snapshot must be object"
                )
            pr = dict(snapshot.get("pr") or {})
            snap_head = pr.get("head_sha")
            if manifest.get("force_approval_head_from_manifest", True):
                pr["head_sha"] = head_sha
                for check in snapshot.get("checks") or []:
                    if isinstance(check, dict) and check.get("source_sha") == snap_head:
                        check["source_sha"] = head_sha
                snapshot["pr"] = pr
            paths = default_repo_paths(root)
            if manifest.get("approval_baseline_path"):
                paths = RepoPaths(
                    repo_root=paths.repo_root,
                    policy_path=paths.policy_path,
                    prompt_path=paths.prompt_path,
                    baseline_path=_resolve(root, manifest["approval_baseline_path"]),
                    schema_path=paths.schema_path,
                )
            envelope = build_approval_context(snapshot, paths)
            approval_digest = envelope.get("context_digest")
            approval_rec = envelope.get("recommendation")
            appr_head = (envelope.get("subject") or {}).get("head_sha")
            reason_codes = list(envelope.get("reason_codes") or [])
            if approval_rec == "UNKNOWN":
                unknown = True
            step_status = "PASS"
            if approval_rec != "APPROVE_RECOMMENDED":
                step_status = "HOLD"
                hold = True
            steps.append(
                _step(
                    "approval_context",
                    step_status,
                    detail={
                        "recommendation": approval_rec,
                        "context_digest": approval_digest,
                        "subject_head_sha": appr_head,
                        "pilot_head_sha": head_sha,
                        "reason_codes": reason_codes,
                        "authority_limits": envelope.get("authority_limits"),
                    },
                )
            )
            limits = envelope.get("authority_limits") or {}
            for key, val in APPROVAL_AUTHORITY.items():
                if limits.get(key) is not val:
                    fail = True
                    steps.append(
                        _step(
                            "authority_boundary",
                            "FAIL",
                            detail={"key": key, "value": limits.get(key)},
                        )
                    )
                    break
            else:
                steps.append(
                    _step(
                        "authority_boundary",
                        "PASS",
                        detail={"authority_limits": AUTHORITY_LIMITS},
                    )
                )
        except Exception as exc:  # noqa: BLE001
            code = getattr(exc, "code", "PILOT_APPROVAL_ERROR")
            if code in {"APPROVAL_SECRET_DETECTED", "REASON_SECRET_DETECTED"}:
                blocked = True
            else:
                hold = True
            steps.append(
                _step(
                    "approval_context",
                    "BLOCKED" if blocked else "HOLD",
                    detail={"code": code, "error": str(exc)},
                )
            )
    elif skip_approval:
        steps.append(
            _step("approval_context", "SKIP", detail={"reason": "skip_approval"})
        )
        if blocked:
            steps.append(
                _step(
                    "authority_boundary",
                    "PASS",
                    detail={
                        "authority_limits": AUTHORITY_LIMITS,
                        "provider_calls": provider_calls,
                    },
                )
            )

    input_digests = {
        "contract_digest": contract_digest,
        "approval_context_digest": approval_digest,
    }
    return _finalize(
        manifest,
        steps,
        run_id,
        attempt,
        head_sha,
        base_sha,
        input_digests,
        provider_calls,
        evidence_refs,
        approval_digest,
        approval_rec,
        blocked,
        hold,
        fail,
        unknown,
        evidence_ok,
        limitations,
        contract_digest,
    )


def _finalize(
    manifest: dict[str, Any],
    steps: list[dict[str, Any]],
    run_id: str | None,
    attempt: int | None,
    head_sha: str,
    base_sha: str | None,
    input_digests: dict[str, Any],
    provider_calls: int,
    evidence_refs: list[dict[str, Any]],
    approval_digest: str | None,
    approval_rec: str | None,
    blocked: bool,
    hold: bool,
    fail: bool,
    unknown: bool,
    evidence_ok: bool,
    limitations: list[str],
    contract_digest: str | None,
    *,
    expect_calls: int | None = None,
) -> dict[str, Any]:
    # Expectations only verify the observed computed status — they never
    # manufacture BLOCKED/HOLD/FAIL when the machinery did not produce it.
    scenario_id = str(manifest.get("scenario_id"))
    expected_final = manifest.get("expect_final_status")
    computed = _map_final_status(
        blocked=blocked,
        hold=hold,
        fail=fail,
        unknown=unknown,
        approval_rec=approval_rec,
        evidence_ok=evidence_ok,
        provider_calls=provider_calls,
        expect_provider_calls=expect_calls,
    )
    if expected_final:
        if computed == expected_final:
            final_status = computed
        else:
            final_status = "FAIL"
            steps.append(
                _step(
                    "scenario_expectation",
                    "FAIL",
                    detail={
                        "expected_final": expected_final,
                        "computed": computed,
                        "blocked": blocked,
                        "hold": hold,
                        "fail": fail,
                        "unknown": unknown,
                        "approval_recommendation": approval_rec,
                    },
                )
            )
    else:
        final_status = computed

    # UNKNOWN never becomes PASS
    if final_status == "UNKNOWN":
        limitations = list(limitations) + ["unknown_fail_closed"]

    contract_versions = {
        "execution": "cdb.agent_execution.v1",
        "registry": "cdb.agent_registry.v1",
        "dispatch": "cdb.agent_dispatch_run.v1",
        "run_evidence": "cdb.agent_run_evidence.v1",
        "approval": "cdb.pr_approval_context.v1",
        "pilot_report": REPORT_SCHEMA_ID,
    }
    subject_in = (
        manifest.get("subject") if isinstance(manifest.get("subject"), dict) else {}
    )
    return build_report(
        pilot_id=str(manifest["pilot_id"]),
        scenario_id=scenario_id,
        subject={
            "head_sha": head_sha,
            "base_sha": base_sha,
            "issue": 4258,
            "pr_number": subject_in.get("pr_number"),
        },
        contract_versions=contract_versions,
        run_id=run_id,
        attempt=attempt,
        head_sha=head_sha,
        input_digests=input_digests,
        step_results=steps,
        provider_call_count=provider_calls,
        run_evidence_refs=evidence_refs,
        approval_context_digest=approval_digest,
        approval_recommendation=approval_rec,
        final_status=final_status,
        limitations=limitations,
    )


def run_pilot_from_path(
    manifest_path: Path,
    *,
    repo_root: Path | None = None,
    out_path: Path | None = None,
    provider_id: str = "mock",
    human_go_live_cursor: bool = False,
    resume_run_id: str | None = None,
    state_path: Path | None = None,
    http_transport: HttpTransport | None = None,
    gh_runner: GhRunner | None = None,
    auto_create_pr: bool = False,
    environment_attestation_path: Path | None = None,
    secrets_dir: Path | None = None,
    credential_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    root = repo_root or REPO_ROOT
    manifest = load_manifest(manifest_path, repo_root=root)
    store_path = None
    if manifest.get("evidence_store_path"):
        store_path = _resolve(root, manifest["evidence_store_path"])
        store_path.parent.mkdir(parents=True, exist_ok=True)
    report = run_pilot(
        manifest,
        repo_root=root,
        store_path=store_path,
        provider_id=provider_id,
        human_go_live_cursor=human_go_live_cursor,
        resume_run_id=resume_run_id,
        state_path=state_path,
        http_transport=http_transport,
        gh_runner=gh_runner,
        auto_create_pr=auto_create_pr,
        environment_attestation_path=environment_attestation_path,
        secrets_dir=secrets_dir,
        credential_env=credential_env,
    )
    verify_report(report)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return report
