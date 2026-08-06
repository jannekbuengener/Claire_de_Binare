"""hh_hl campaign dataset binding + physical local proof (#4374 / #4375).

Identity binding uses locked Batch-A window IDs. Physical proof reads candles
under a validated window-bank root and hashes via
``core.replay.dataset_identity.content_fingerprint``. Caller-supplied hashes
are never treated as proof.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.replay.binance_window_bank_adapter import (
    BinanceWindowBankAdapterError,
    load_dataset_spec,
    load_window_candles_jsonl,
)
from core.replay.canonical_json import canonical_hash
from core.replay.dataset_identity import (
    collect_forbidden_evidence_keys,
    content_fingerprint,
)
from core.utils.clock import utcnow as cdb_utcnow
from tools.arvp_vacation.sensitivity_campaign_dataset_root import (
    SensitivityDatasetRootError,
    _pick_window_bank_root,
)
from tools.market_data.development_window_selector import (
    LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS,
    LOCKED_DEVELOPMENT_SELECTION_SHA256,
)

DATASET_CONTRACT_VERSION = "cdb.hh_hl_campaign_dataset_binding.v1"
PROOF_SCHEMA_VERSION = "cdb.hh_hl_dataset_local_proof.v1"
DATASET_ROOT_KIND = "binance_window_bank:locked_batch_a_development_39"
DATASET_STATUS_LOCAL_PROOF_REQUIRED = "HOLD_DATASET_BINDING_LOCAL_PROOF_REQUIRED"
DATASET_STATUS_PASS = "DATASET_BINDING_LOCAL_PROOF_PASS"
PROOF_ALGORITHM = "cdb.dataset_identity.content_fingerprint.v1+ordered_window_pairs"
SYMBOL = "BTCUSDT"
VENUE = "binance"
TIMEFRAME = "1m"

_MODULE_PATH = Path(__file__).resolve()
PROJECT_ROOT = _MODULE_PATH.parents[2]


class HhHlDatasetBindingError(ValueError):
    """Fail-closed dataset binding / proof violation."""


@dataclass(frozen=True, slots=True)
class DatasetBindingReceipt:
    schema_version: str
    dataset_contract_version: str
    dataset_root_kind: str
    window_count: int
    ordered_window_ids: tuple[str, ...]
    selection_sha256: str
    per_window_content_fingerprints: Mapping[str, str] | None
    content_fingerprint_digest: str | None
    symbol: str
    venue: str
    timeframe: str
    quality_gate_status: str
    known_limitations: tuple[str, ...]
    local_proof_required: bool
    local_proof_command: str
    proof_algorithm: str | None = None
    proof_code_sha: str | None = None
    proof_timestamp: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "dataset_contract_version": self.dataset_contract_version,
            "dataset_root_kind": self.dataset_root_kind,
            "window_count": self.window_count,
            "ordered_window_ids": list(self.ordered_window_ids),
            "selection_sha256": self.selection_sha256,
            "per_window_content_fingerprints": (
                dict(self.per_window_content_fingerprints)
                if self.per_window_content_fingerprints is not None
                else None
            ),
            "content_fingerprint_digest": self.content_fingerprint_digest,
            "symbol": self.symbol,
            "venue": self.venue,
            "timeframe": self.timeframe,
            "quality_gate_status": self.quality_gate_status,
            "known_limitations": list(self.known_limitations),
            "local_proof_required": self.local_proof_required,
            "local_proof_command": self.local_proof_command,
            "proof_algorithm": self.proof_algorithm,
            "proof_code_sha": self.proof_code_sha,
            "proof_timestamp": self.proof_timestamp,
        }
        return payload


def _assert_window_set(window_ids: Sequence[str]) -> tuple[str, ...]:
    ordered = tuple(window_ids)
    locked = tuple(LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS)
    if len(ordered) != len(set(ordered)):
        dupes = sorted({w for w in ordered if ordered.count(w) > 1})
        raise HhHlDatasetBindingError(f"DUPLICATE_WINDOWS:{dupes}")
    missing = sorted(set(locked) - set(ordered))
    foreign = sorted(set(ordered) - set(locked))
    if missing:
        raise HhHlDatasetBindingError(f"MISSING_WINDOWS:{missing}")
    if foreign:
        raise HhHlDatasetBindingError(f"FOREIGN_WINDOWS:{foreign}")
    if len(ordered) != len(locked):
        raise HhHlDatasetBindingError(
            f"WINDOW_COUNT_MISMATCH:{len(ordered)}!={len(locked)}"
        )
    if ordered != locked:
        raise HhHlDatasetBindingError("WINDOW_ORDER_MISMATCH")
    return ordered


def _digest_from_pairs(ordered_ids: Sequence[str], fps: Mapping[str, str]) -> str:
    return canonical_hash(
        {
            "pairs": [
                {"window_id": wid, "content_fingerprint": fps[wid]}
                for wid in ordered_ids
            ]
        }
    )


def proof_code_sha() -> str:
    raw = _MODULE_PATH.read_bytes()
    return hashlib.sha256(raw).hexdigest()


def _default_limitations_unproven() -> tuple[str, ...]:
    return (
        "Batch-A 39-window bank is identity-bound for planning only; "
        "hh_hl eligibility still requires Design-GO ratification.",
        "Physical content fingerprints are not asserted without local proof.",
        "Single-run #4372 dataset must not be auto-promoted to campaign dataset.",
    )


def build_dataset_binding_receipt(
    *,
    window_ids: Sequence[str] | None = None,
    content_fingerprints_by_window: Mapping[str, str] | None = None,
    dataset_root: Path | None = None,
) -> DatasetBindingReceipt:
    """Identity-only receipt. Never marks PASS from caller-supplied hashes."""
    ordered = _assert_window_set(
        window_ids if window_ids is not None else LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS
    )
    selection = LOCKED_DEVELOPMENT_SELECTION_SHA256

    content_digest: str | None = None
    per_window: Mapping[str, str] | None = None
    if content_fingerprints_by_window is not None:
        fps = dict(content_fingerprints_by_window)
        missing = [wid for wid in ordered if wid not in fps]
        foreign = sorted(set(fps) - set(ordered))
        if missing:
            raise HhHlDatasetBindingError(f"MISSING_CONTENT_FPS:{missing}")
        if foreign:
            raise HhHlDatasetBindingError(f"FOREIGN_CONTENT_FPS:{foreign}")
        for wid, fp in fps.items():
            if not isinstance(fp, str) or len(fp) != 64:
                raise HhHlDatasetBindingError(f"INVALID_CONTENT_FP:{wid}")
        # Caller-supplied fingerprints may be validated for shape only.
        # They MUST NOT clear local_proof_required.
        content_digest = _digest_from_pairs(ordered, fps)
        per_window = {wid: fps[wid] for wid in ordered}
        _ = dataset_root  # ignored for PASS — physical prove_local_dataset only

    proof_cmd = (
        "python -m tools.arvp_vacation.hh_hl_campaign_plan prove-dataset "
        "--dataset-root <LOCAL_WINDOW_BANK_ROOT>"
    )
    return DatasetBindingReceipt(
        schema_version=PROOF_SCHEMA_VERSION,
        dataset_contract_version=DATASET_CONTRACT_VERSION,
        dataset_root_kind=DATASET_ROOT_KIND,
        window_count=len(ordered),
        ordered_window_ids=ordered,
        selection_sha256=selection,
        per_window_content_fingerprints=per_window,
        content_fingerprint_digest=content_digest,
        symbol=SYMBOL,
        venue=VENUE,
        timeframe=TIMEFRAME,
        quality_gate_status=DATASET_STATUS_LOCAL_PROOF_REQUIRED,
        known_limitations=_default_limitations_unproven(),
        local_proof_required=True,
        local_proof_command=proof_cmd,
        proof_algorithm=None,
        proof_code_sha=None,
        proof_timestamp=None,
    )


def _validate_window_meta(window_id: str, spec: Mapping[str, Any]) -> None:
    spec_wid = str(spec.get("window_id") or "")
    if spec_wid and spec_wid != window_id:
        raise HhHlDatasetBindingError(f"WINDOW_ID_MISMATCH:{window_id}:{spec_wid!r}")
    symbol = str(spec.get("symbol") or "")
    if symbol != SYMBOL:
        raise HhHlDatasetBindingError(f"SYMBOL_MISMATCH:{window_id}:{symbol!r}")
    timeframe = str(spec.get("timeframe") or "")
    if timeframe != TIMEFRAME:
        raise HhHlDatasetBindingError(f"TIMEFRAME_MISMATCH:{window_id}:{timeframe!r}")
    venue = str(spec.get("venue") or spec.get("exchange") or VENUE)
    if venue.lower() != VENUE:
        raise HhHlDatasetBindingError(f"VENUE_MISMATCH:{window_id}:{venue!r}")


def prove_local_dataset(
    dataset_root: Path,
    *,
    repo_root: Path | None = None,
) -> DatasetBindingReceipt:
    """Physically read/validate/fingerprint all 39 locked windows under root."""
    root = Path(dataset_root)

    if not root.exists():
        raise HhHlDatasetBindingError(f"DATASET_ROOT_MISSING:{root.name}")
    if not root.is_dir():
        raise HhHlDatasetBindingError(f"DATASET_ROOT_NOT_DIRECTORY:{root.name}")

    repo = Path(repo_root) if repo_root is not None else PROJECT_ROOT
    try:
        bank_root = _pick_window_bank_root(root, repo)
    except SensitivityDatasetRootError as exc:
        raise HhHlDatasetBindingError(str(exc)) from exc

    # Reject foreign locked-inventory pollution: bank may contain extra months,
    # but the bound inventory must be exactly the locked 39 in order.
    ordered = tuple(LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS)
    present_dirs = {p.name for p in bank_root.iterdir() if p.is_dir()}
    missing = [wid for wid in ordered if wid not in present_dirs]
    if missing:
        raise HhHlDatasetBindingError(f"MISSING_WINDOWS:{missing}")

    fps: dict[str, str] = {}
    for window_id in ordered:
        window_dir = bank_root / window_id
        if not window_dir.is_dir():
            raise HhHlDatasetBindingError(f"MISSING_WINDOWS:[{window_id!r}]")
        spec_path = window_dir / "dataset_spec.json"
        candles_path = window_dir / "candles.jsonl"
        try:
            spec = load_dataset_spec(spec_path)
        except BinanceWindowBankAdapterError as exc:
            raise HhHlDatasetBindingError(
                f"WINDOW_SPEC_INVALID:{window_id}:{exc}"
            ) from exc
        _validate_window_meta(window_id, spec)
        try:
            candles = load_window_candles_jsonl(candles_path)
        except BinanceWindowBankAdapterError as exc:
            raise HhHlDatasetBindingError(
                f"WINDOW_CANDLES_INVALID:{window_id}:{exc}"
            ) from exc
        if not candles:
            raise HhHlDatasetBindingError(f"WINDOW_CANDLES_EMPTY:{window_id}")
        try:
            fps[window_id] = content_fingerprint(candles)
        except Exception as exc:  # noqa: BLE001 — map to fail-closed
            raise HhHlDatasetBindingError(
                f"WINDOW_FINGERPRINT_FAILED:{window_id}:{type(exc).__name__}"
            ) from exc

    digest = _digest_from_pairs(ordered, fps)
    now = cdb_utcnow()
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    ts = now.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    receipt = DatasetBindingReceipt(
        schema_version=PROOF_SCHEMA_VERSION,
        dataset_contract_version=DATASET_CONTRACT_VERSION,
        dataset_root_kind=DATASET_ROOT_KIND,
        window_count=len(ordered),
        ordered_window_ids=ordered,
        selection_sha256=LOCKED_DEVELOPMENT_SELECTION_SHA256,
        per_window_content_fingerprints={wid: fps[wid] for wid in ordered},
        content_fingerprint_digest=digest,
        symbol=SYMBOL,
        venue=VENUE,
        timeframe=TIMEFRAME,
        quality_gate_status=DATASET_STATUS_PASS,
        known_limitations=(
            "Physical proof binds candle content via "
            "core.replay.dataset_identity.content_fingerprint.",
            "Absolute dataset-root paths are intentionally omitted from receipts.",
            "Grid/Design/Execution Owner-GOs remain required separately.",
        ),
        local_proof_required=False,
        local_proof_command=(
            "python -m tools.arvp_vacation.hh_hl_campaign_plan prove-dataset "
            "--dataset-root <LOCAL_WINDOW_BANK_ROOT>"
        ),
        proof_algorithm=PROOF_ALGORITHM,
        proof_code_sha=proof_code_sha(),
        proof_timestamp=ts,
    )
    bad = collect_forbidden_evidence_keys(receipt.as_dict())
    if bad:
        raise HhHlDatasetBindingError(f"RECEIPT_FORBIDDEN_KEYS:{bad}")
    # Absolute path leak guard (receipt body only).
    blob = json.dumps(receipt.as_dict(), sort_keys=True)
    if ":\\" in blob or blob.count("/Users/") or "/home/" in blob:
        # Allow none — proof_timestamp/ISO only. Hard fail on drive letters.
        if ":\\" in blob or "/home/" in blob:
            raise HhHlDatasetBindingError("RECEIPT_CONTAINS_ABSOLUTE_PATH")
    return receipt


def validate_pass_receipt(payload: Mapping[str, Any]) -> DatasetBindingReceipt:
    """Validate a PASS receipt for planning consumption. Fail closed."""
    required = (
        "schema_version",
        "dataset_contract_version",
        "dataset_root_kind",
        "window_count",
        "ordered_window_ids",
        "selection_sha256",
        "per_window_content_fingerprints",
        "content_fingerprint_digest",
        "symbol",
        "venue",
        "timeframe",
        "quality_gate_status",
        "local_proof_required",
        "proof_algorithm",
        "proof_code_sha",
        "proof_timestamp",
        "known_limitations",
    )
    missing = [k for k in required if k not in payload]
    if missing:
        raise HhHlDatasetBindingError(f"RECEIPT_FIELDS_MISSING:{missing}")
    if payload.get("quality_gate_status") != DATASET_STATUS_PASS:
        raise HhHlDatasetBindingError(
            f"RECEIPT_NOT_PASS:{payload.get('quality_gate_status')!r}"
        )
    if payload.get("local_proof_required") is not False:
        raise HhHlDatasetBindingError("RECEIPT_LOCAL_PROOF_STILL_REQUIRED")
    if payload.get("selection_sha256") != LOCKED_DEVELOPMENT_SELECTION_SHA256:
        raise HhHlDatasetBindingError("RECEIPT_SELECTION_SHA_MISMATCH")
    if payload.get("symbol") != SYMBOL or payload.get("venue") != VENUE:
        raise HhHlDatasetBindingError("RECEIPT_META_MISMATCH")
    if payload.get("timeframe") != TIMEFRAME:
        raise HhHlDatasetBindingError("RECEIPT_TIMEFRAME_MISMATCH")
    if payload.get("dataset_root_kind") != DATASET_ROOT_KIND:
        raise HhHlDatasetBindingError("RECEIPT_ROOT_KIND_MISMATCH")
    if payload.get("proof_algorithm") != PROOF_ALGORITHM:
        raise HhHlDatasetBindingError("RECEIPT_PROOF_ALGORITHM_MISMATCH")

    ordered = _assert_window_set(list(payload.get("ordered_window_ids") or []))
    fps_raw = payload.get("per_window_content_fingerprints")
    if not isinstance(fps_raw, Mapping):
        raise HhHlDatasetBindingError("RECEIPT_FPS_NOT_OBJECT")
    fps = {str(k): str(v) for k, v in fps_raw.items()}
    missing_fp = [wid for wid in ordered if wid not in fps]
    foreign_fp = sorted(set(fps) - set(ordered))
    if missing_fp:
        raise HhHlDatasetBindingError(f"RECEIPT_MISSING_FPS:{missing_fp}")
    if foreign_fp:
        raise HhHlDatasetBindingError(f"RECEIPT_FOREIGN_FPS:{foreign_fp}")
    for wid, fp in fps.items():
        if len(fp) != 64:
            raise HhHlDatasetBindingError(f"RECEIPT_INVALID_FP:{wid}")
    expected_digest = _digest_from_pairs(ordered, fps)
    if str(payload.get("content_fingerprint_digest")) != expected_digest:
        raise HhHlDatasetBindingError("RECEIPT_CONTENT_DIGEST_MISMATCH")

    bad = collect_forbidden_evidence_keys(dict(payload))
    if bad:
        raise HhHlDatasetBindingError(f"RECEIPT_FORBIDDEN_KEYS:{bad}")

    return DatasetBindingReceipt(
        schema_version=str(payload["schema_version"]),
        dataset_contract_version=str(payload["dataset_contract_version"]),
        dataset_root_kind=str(payload["dataset_root_kind"]),
        window_count=int(payload["window_count"]),
        ordered_window_ids=ordered,
        selection_sha256=str(payload["selection_sha256"]),
        per_window_content_fingerprints={wid: fps[wid] for wid in ordered},
        content_fingerprint_digest=expected_digest,
        symbol=SYMBOL,
        venue=VENUE,
        timeframe=TIMEFRAME,
        quality_gate_status=DATASET_STATUS_PASS,
        known_limitations=tuple(payload.get("known_limitations") or ()),
        local_proof_required=False,
        local_proof_command=str(
            payload.get("local_proof_command")
            or (
                "python -m tools.arvp_vacation.hh_hl_campaign_plan prove-dataset "
                "--dataset-root <LOCAL_WINDOW_BANK_ROOT>"
            )
        ),
        proof_algorithm=PROOF_ALGORITHM,
        proof_code_sha=str(payload.get("proof_code_sha") or ""),
        proof_timestamp=str(payload.get("proof_timestamp") or ""),
    )


def load_pass_receipt(path: Path) -> DatasetBindingReceipt:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise HhHlDatasetBindingError("RECEIPT_ROOT_MUST_BE_OBJECT")
    return validate_pass_receipt(payload)


def write_receipt_atomic(receipt: DatasetBindingReceipt, path: Path) -> Path:
    target = Path(path)
    if target.exists():
        raise HhHlDatasetBindingError(f"RECEIPT_OUT_EXISTS:{target.name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + f".tmp.{os.getpid()}")
    body = json.dumps(receipt.as_dict(), indent=2, sort_keys=True) + "\n"
    tmp.write_text(body, encoding="utf-8")
    os.replace(tmp, target)
    return target


def resolve_default_dataset_root() -> Path | None:
    """Best-effort resolve of the canonical local window bank (no guessing)."""
    candidates: list[Path] = []
    env = os.environ.get("CDB_WINDOW_BANK_ROOT") or os.environ.get("CDB_DATASET_ROOT")
    if env:
        candidates.append(Path(env))
    # Worktree → parent Claire_de_Binare checkout artifacts (common local layout).
    parent_repo = PROJECT_ROOT.parent.parent  # .../Claire_de_Binare
    candidates.extend(
        [
            PROJECT_ROOT
            / "artifacts"
            / "market_data"
            / "window_bank"
            / "binance"
            / "spot"
            / "BTCUSDT"
            / "1m",
            PROJECT_ROOT / "artifacts" / "market_data",
            parent_repo
            / "artifacts"
            / "market_data"
            / "window_bank"
            / "binance"
            / "spot"
            / "BTCUSDT"
            / "1m",
            parent_repo / "artifacts" / "market_data",
        ]
    )
    verified_by_bank: dict[str, Path] = {}
    for cand in candidates:
        try:
            if not cand.exists() or not cand.is_dir():
                continue
            bank = _pick_window_bank_root(cand, PROJECT_ROOT).resolve()
            missing = [
                wid
                for wid in LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS
                if not (bank / wid).is_dir()
            ]
            if missing:
                continue
            key = str(bank)
            # Prefer declaring the exact bank path when available.
            if key not in verified_by_bank or cand.resolve() == bank:
                verified_by_bank[key] = cand.resolve()
        except (SensitivityDatasetRootError, OSError):
            continue
    if len(verified_by_bank) == 1:
        return next(iter(verified_by_bank.values()))
    return None
