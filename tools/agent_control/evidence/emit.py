"""Deterministic emitter for cdb.agent_run_evidence.v1."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path
from typing import Any

from tools.agent_control.errors import EvidenceError
from tools.agent_control.evidence.codes import (
    ALLOWED_ARTIFACT_ROOTS,
    AUTHORITY_LIMITS,
    EVIDENCE_CLASS,
    FORBIDDEN_AUTHORITY_CLAIMS,
    REASON_AUTHORITY_CLAIM,
    REASON_BINDING_MISMATCH,
    REASON_EVIDENCE_INCOMPLETE,
    REASON_LIFECYCLE_NON_MONOTONE,
    REASON_PATH_INVALID,
    REASON_SECRET_DETECTED,
    SCHEMA_ID,
    SCHEMA_VERSION,
)
from tools.agent_control.evidence.digest import (
    attach_bundle_digest,
    derive_evidence_id,
)
from tools.agent_control.evidence.normalize import (
    claim,
    normalize_changed_files,
    normalize_usage_cost,
)
from tools.agent_control.evidence.redact import (
    assert_no_secrets,
    detect_secrets,
    sanitize_result_refs,
    validate_repo_relative_path,
)
from tools.agent_control.evidence.store import EvidenceJsonlStore
from tools.agent_control.evidence.verdict import derive_verdict
from tools.agent_control.run_store import RunStore
from tools.agent_execution_contract.jcs import canonicalize


def _binding_pair(
    value: Any, *, source: str, trust_class: str = "control_plane_observed"
) -> dict[str, Any]:
    return claim(value=value, trust_class=trust_class, source=source)


def _check_lifecycle_monotone(events: list[dict[str, Any]]) -> None:
    prev: str | None = None
    for event in events:
        at = event.get("at")
        if not isinstance(at, str):
            continue
        if prev is not None and at < prev:
            raise EvidenceError(
                REASON_LIFECYCLE_NON_MONOTONE,
                "lifecycle event timestamps are not monotone",
            )
        prev = at


def _artifact_entries(
    result_refs: dict[str, Any],
    *,
    repo_root: Path | None,
) -> list[dict[str, Any]]:
    raw = result_refs.get("artifacts") or []
    if raw in (None, {}):
        raw = []
    if isinstance(raw, dict):
        raw = list(raw.values()) if raw else []
    if not isinstance(raw, list):
        raise EvidenceError(REASON_PATH_INVALID, "artifacts must be a list")
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, str):
            path = validate_repo_relative_path(
                item, allowed_roots=ALLOWED_ARTIFACT_ROOTS
            )
            digest = None
            size = None
            artifact_type = "file"
        elif isinstance(item, dict):
            path = validate_repo_relative_path(
                str(item.get("path") or ""),
                allowed_roots=ALLOWED_ARTIFACT_ROOTS,
            )
            digest = item.get("digest")
            size = item.get("size_bytes")
            artifact_type = item.get("type") or "file"
        else:
            raise EvidenceError(REASON_PATH_INVALID, "invalid artifact entry")
        if repo_root is not None:
            full = (repo_root / path).resolve()
            try:
                full.relative_to(repo_root.resolve())
            except ValueError as exc:
                raise EvidenceError(
                    REASON_PATH_INVALID,
                    "symlink/path escape outside repo root",
                ) from exc
            if full.is_symlink():
                raise EvidenceError(REASON_PATH_INVALID, "symlink artifact rejected")
            if full.is_file() and digest is None:
                digest = "sha256:" + hashlib.sha256(full.read_bytes()).hexdigest()
                size = full.stat().st_size
        out.append(
            {
                "path": path,
                "digest": digest,
                "size_bytes": size,
                "type": artifact_type,
                "provenance": {
                    "trust_class": "provider_reported",
                    "source": "run.result_refs.artifacts",
                    "reference": path,
                    "digest": digest,
                },
            }
        )
    out.sort(key=lambda row: row["path"])
    return out


def _test_entries(result_refs: dict[str, Any]) -> list[dict[str, Any]]:
    raw = result_refs.get("tests") or []
    if not raw:
        return []
    if not isinstance(raw, list):
        raise EvidenceError(REASON_EVIDENCE_INCOMPLETE, "tests must be a list")
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise EvidenceError(REASON_EVIDENCE_INCOMPLETE, "invalid test entry")
        exit_code = item.get("exit_code")
        status = item.get("status")
        evidence_digest = item.get("evidence_digest")
        if status == "PASS" and (exit_code not in (0, "0") or not evidence_digest):
            raise EvidenceError(
                REASON_EVIDENCE_INCOMPLETE,
                "test PASS requires exit_code 0 and evidence_digest",
            )
        out.append(
            {
                "name": item.get("name"),
                "status": status,
                "exit_code": exit_code,
                "evidence_digest": evidence_digest,
                "provenance": {
                    "trust_class": "agent_reported",
                    "source": "run.result_refs.tests",
                    "reference": item.get("name"),
                    "digest": evidence_digest,
                },
            }
        )
    out.sort(key=lambda row: str(row.get("name") or ""))
    return out


def _reject_authority_claims(node: Any, *, path: str = "$") -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            key_s = str(key)
            if key_s in FORBIDDEN_AUTHORITY_CLAIMS and value not in (False, None):
                raise EvidenceError(
                    REASON_AUTHORITY_CLAIM,
                    f"forbidden authority claim at {path}.{key_s}",
                )
            # Explicit false claims for forbidden keys are ok only via authority_limits.
            _reject_authority_claims(value, path=f"{path}.{key_s}")
    elif isinstance(node, list):
        for idx, value in enumerate(node):
            _reject_authority_claims(value, path=f"{path}[{idx}]")


def build_evidence_bundle(
    run: dict[str, Any],
    *,
    repo_root: Path | None = None,
    require_complete_for_pass: bool = True,
) -> dict[str, Any]:
    """Build a deterministic evidence bundle from a persisted run record."""
    if run.get("schema_id") != "cdb.agent_dispatch_run.v1":
        raise EvidenceError(
            REASON_BINDING_MISMATCH,
            "run schema_id must be cdb.agent_dispatch_run.v1",
        )

    # Fail-closed on secrets before any strip/mask. Structural removal alone
    # is not enough for PASS when secret-like content was present on input.
    secret_hits = detect_secrets(run.get("result_refs") or {})
    secret_hits.extend(detect_secrets(run.get("usage") or {}))
    secret_hits.extend(detect_secrets(run.get("lifecycle_events") or []))
    if secret_hits:
        raise EvidenceError(
            REASON_SECRET_DETECTED,
            f"secret-like content at {secret_hits[0]}",
        )
    if run.get("prompt_text") is not None:
        raise EvidenceError(
            REASON_SECRET_DETECTED,
            "prompt_text must never appear on run record or evidence",
        )

    result_refs = sanitize_result_refs(run.get("result_refs") or {})
    assert_no_secrets(run.get("prompt_ref"))

    events = deepcopy(run.get("lifecycle_events") or [])
    _check_lifecycle_monotone(events)

    changed_files = normalize_changed_files(
        (run.get("delivery_receipt") or {}).get("changed_files")
        or result_refs.get("changed_files")
        or []
    )
    for path in changed_files:
        # changed_files may be any repo-relative path (not only artifacts/).
        text = path.replace("\\", "/").strip()
        if text.startswith("/") or ".." in text.split("/"):
            raise EvidenceError(REASON_PATH_INVALID, f"invalid changed_file {path!r}")

    artifacts = _artifact_entries(result_refs, repo_root=repo_root)
    tests = _test_entries(result_refs)

    scenario = run.get("scenario")
    usage = normalize_usage_cost(
        run.get("usage") or {},
        scenario="mock" if run.get("provider_id") == "mock" else scenario,
    )

    incomplete = False
    if require_complete_for_pass and run.get("state") == "PASS":
        if not run.get("contract_digest"):
            incomplete = True
        if not isinstance(run.get("delivery_receipt"), dict) or not run.get(
            "delivery_receipt"
        ):
            incomplete = True
        # Contract-required tests/artifacts with failing evidence => incomplete.
        required_tests = (
            ((run.get("result_refs") or {}).get("required_tests"))
            if isinstance(run.get("result_refs"), dict)
            else None
        )
        if required_tests and not tests:
            incomplete = True
        for test in tests:
            if test.get("status") == "PASS" and (
                test.get("exit_code") not in (0, "0") or not test.get("evidence_digest")
            ):
                incomplete = True
                break
        for art in artifacts:
            if art.get("digest") is None and require_complete_for_pass:
                # Unbound artifact digest on PASS is incomplete.
                incomplete = True
                break

    verdict = derive_verdict(run, incomplete=incomplete)

    id_bindings = {
        "run_id": run["run_id"],
        "attempt": int(run.get("attempt") or 1),
        "contract_id": run.get("contract_id"),
        "contract_digest": run.get("contract_digest"),
        "provider_id": run.get("provider_id"),
        "provider_run_id": run.get("provider_run_id"),
        "idempotency_key": run.get("idempotency_key"),
    }
    evidence_id = derive_evidence_id(id_bindings)

    route = deepcopy(run.get("route") or {})
    receipt = deepcopy(run.get("delivery_receipt") or {})

    bundle: dict[str, Any] = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "evidence_class": EVIDENCE_CLASS,
        "evidence_id": evidence_id,
        "run_id": run["run_id"],
        "attempt": int(run.get("attempt") or 1),
        "request_binding": {
            "idempotency_key": run.get("idempotency_key"),
            "provenance": {
                "trust_class": "control_plane_observed",
                "source": "run.idempotency_key",
                "reference": run.get("idempotency_key"),
                "digest": None,
            },
        },
        "agent": _binding_pair(run.get("agent_id"), source="run.agent_id"),
        "provider": {
            "provider_id": run.get("provider_id"),
            "provider_run_id": run.get("provider_run_id"),
            "provenance": {
                "trust_class": "control_plane_observed",
                "source": "run.provider",
                "reference": run.get("provider_run_id"),
                "digest": None,
            },
        },
        "execution_contract": {
            "contract_id": run.get("contract_id"),
            "contract_digest": run.get("contract_digest"),
            "provenance": {
                "trust_class": "control_plane_observed",
                "source": "run.contract",
                "reference": run.get("contract_id"),
                "digest": run.get("contract_digest"),
            },
        },
        "delivery_context": {
            "issue": run.get("delivery_issue"),
            "target_pr": route.get("target_pr"),
            "target_branch": route.get("target_branch"),
            "source_commit": run.get("source_commit"),
            "delivery_commit": receipt.get("commit"),
            "delivery_status": receipt.get("delivery_status"),
            "provenance": {
                "trust_class": "control_plane_observed",
                "source": "run.route+delivery_receipt",
                "reference": str(route.get("target_pr")),
                "digest": None,
            },
        },
        "environment": {
            "profile_id": run.get("environment_profile_id"),
            "profile_version": run.get("environment_profile_version"),
            "profile_digest": run.get("environment_profile_digest"),
            "provider_config_digest": run.get("provider_config_digest"),
            "preflight_verdict": run.get("environment_preflight_verdict"),
            "provenance": {
                "trust_class": "control_plane_observed",
                "source": "run.environment_bindings",
                "reference": run.get("environment_profile_id"),
                "digest": run.get("environment_profile_digest"),
            },
        },
        "prompt": {
            "prompt_ref": run.get("prompt_ref"),
            "prompt_digest": run.get("prompt_digest"),
            "provenance": {
                "trust_class": "control_plane_observed",
                "source": "run.prompt",
                "reference": run.get("prompt_ref"),
                "digest": run.get("prompt_digest"),
            },
        },
        "lifecycle": {
            "state": run.get("state"),
            "created_at": run.get("created_at"),
            "updated_at": run.get("updated_at"),
            "terminal_reason": run.get("terminal_reason"),
            "terminal_code": run.get("terminal_code"),
            "events": events,
            "provenance": {
                "trust_class": "control_plane_observed",
                "source": "run.lifecycle",
                "reference": run.get("run_id"),
                "digest": None,
            },
        },
        "changed_files": changed_files,
        "tests": tests,
        "artifacts": artifacts,
        "usage": usage,
        "result_refs": result_refs,
        "delivery_verdict": verdict,
        "authority_limits": deepcopy(AUTHORITY_LIMITS),
        "limitations": list(verdict.get("limitations") or []),
    }

    _reject_authority_claims(bundle)
    assert_no_secrets(bundle)
    sealed = attach_bundle_digest(bundle)
    # Byte-stable canonical form for repeated emission.
    return json_loads_canonical(sealed)


def json_loads_canonical(bundle: dict[str, Any]) -> dict[str, Any]:
    import json

    return json.loads(canonicalize(bundle))


def emit_evidence(
    run_id: str,
    store: RunStore,
    *,
    jsonl_path: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    record = store.get(run_id)
    if record is None:
        raise EvidenceError("DISPATCH_RUN_NOT_FOUND", f"unknown run_id: {run_id}")
    bundle = build_evidence_bundle(record, repo_root=repo_root)
    store_result = None
    if jsonl_path is not None:
        store_result = EvidenceJsonlStore(jsonl_path).append_idempotent(bundle)
    return {
        "evidence_class": EVIDENCE_CLASS,
        "verdict": bundle["delivery_verdict"]["verdict"],
        "reason_codes": bundle["delivery_verdict"]["reason_codes"],
        "limitations": bundle["limitations"],
        "bundle": bundle,
        "store": store_result,
    }
