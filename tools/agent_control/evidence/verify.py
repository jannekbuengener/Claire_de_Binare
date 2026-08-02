"""Bundle and JSONL store verification for cdb.agent_run_evidence.v1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from tools.agent_control.errors import EvidenceError
from tools.agent_control.evidence.codes import (
    REASON_DUPLICATE_RUN_ATTEMPT,
    REASON_SCHEMA_INVALID,
    SCHEMA_ID,
)
from tools.agent_control.evidence.digest import verify_bundle_digest
from tools.agent_control.evidence.redact import assert_no_secrets
from tools.agent_control.evidence.store import EvidenceJsonlStore
from tools.agent_control.paths import REPO_ROOT

SCHEMA_PATH = REPO_ROOT / "docs" / "contracts" / "cdb_agent_run_evidence.v1.schema.json"


def load_evidence_schema() -> dict[str, Any]:
    with SCHEMA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_bundle_schema(bundle: dict[str, Any]) -> None:
    if bundle.get("schema_id") != SCHEMA_ID:
        raise EvidenceError(
            REASON_SCHEMA_INVALID,
            f"unexpected schema_id {bundle.get('schema_id')!r}",
        )
    validator = Draft202012Validator(load_evidence_schema())
    errors = sorted(validator.iter_errors(bundle), key=lambda err: list(err.path))
    if not errors:
        return
    first = errors[0]
    path = ".".join(str(part) for part in first.path) or "<root>"
    code = REASON_SCHEMA_INVALID
    if "Additional properties are not allowed" in first.message:
        code = "EVIDENCE_UNKNOWN_FIELD"
    raise EvidenceError(code, f"{path}: {first.message}")


def verify_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(bundle, dict):
        raise EvidenceError(REASON_SCHEMA_INVALID, "bundle must be an object")
    validate_bundle_schema(bundle)
    digest = verify_bundle_digest(bundle)
    assert_no_secrets(bundle)
    return {
        "ok": True,
        "evidence_id": bundle.get("evidence_id"),
        "bundle_digest": digest,
        "verdict": (bundle.get("delivery_verdict") or {}).get("verdict"),
        "evidence_class": bundle.get("evidence_class"),
        "limitations": bundle.get("limitations") or [],
    }


def verify_store(path: Path) -> dict[str, Any]:
    store = EvidenceJsonlStore(path)
    records = store.read_all()
    seen_ids: dict[str, str] = {}
    seen_run_attempts: set[tuple[str, int]] = set()
    verified: list[dict[str, Any]] = []
    for record in records:
        result = verify_bundle(record)
        eid = str(record.get("evidence_id"))
        digest = str(record.get("bundle_digest"))
        if eid in seen_ids and seen_ids[eid] != digest:
            raise EvidenceError(
                "EVIDENCE_ID_DIGEST_COLLISION",
                f"duplicate evidence_id with digest mismatch: {eid}",
            )
        seen_ids[eid] = digest
        key = (str(record.get("run_id")), int(record.get("attempt") or 0))
        if key in seen_run_attempts:
            raise EvidenceError(
                REASON_DUPLICATE_RUN_ATTEMPT,
                f"duplicate run/attempt pair: {key}",
            )
        seen_run_attempts.add(key)
        verified.append(result)
    return {
        "ok": True,
        "count": len(verified),
        "records": verified,
        "path": str(path),
    }


def load_bundle_file(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise EvidenceError(REASON_SCHEMA_INVALID, "bundle file must be an object")
    return payload
