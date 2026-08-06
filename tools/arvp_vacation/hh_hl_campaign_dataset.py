"""hh_hl campaign dataset binding receipt (#4374).

Binds the locked Batch-A 39-window identity for planning. Physical content
fingerprints require local proof and are never invented in cloud sessions.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash
from tools.market_data.development_window_selector import (
    LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS,
    LOCKED_DEVELOPMENT_SELECTION_SHA256,
)

DATASET_CONTRACT_VERSION = "cdb.hh_hl_campaign_dataset_binding.v1"
DATASET_ROOT_KIND = "binance_window_bank:locked_batch_a_development_39"
DATASET_STATUS_LOCAL_PROOF_REQUIRED = "HOLD_DATASET_BINDING_LOCAL_PROOF_REQUIRED"
SYMBOL = "BTCUSDT"
VENUE = "binance"
TIMEFRAME = "1m"


class HhHlDatasetBindingError(ValueError):
    """Fail-closed dataset binding violation."""


@dataclass(frozen=True, slots=True)
class DatasetBindingReceipt:
    dataset_contract_version: str
    dataset_root_kind: str
    window_count: int
    ordered_window_ids: tuple[str, ...]
    selection_sha256: str
    content_fingerprint_digest: str | None
    symbol: str
    venue: str
    timeframe: str
    quality_gate_status: str
    known_limitations: tuple[str, ...]
    local_proof_required: bool
    local_proof_command: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "dataset_contract_version": self.dataset_contract_version,
            "dataset_root_kind": self.dataset_root_kind,
            "window_count": self.window_count,
            "ordered_window_ids": list(self.ordered_window_ids),
            "selection_sha256": self.selection_sha256,
            "content_fingerprint_digest": self.content_fingerprint_digest,
            "symbol": self.symbol,
            "venue": self.venue,
            "timeframe": self.timeframe,
            "quality_gate_status": self.quality_gate_status,
            "known_limitations": list(self.known_limitations),
            "local_proof_required": self.local_proof_required,
            "local_proof_command": self.local_proof_command,
        }


def _assert_window_set(window_ids: Sequence[str]) -> tuple[str, ...]:
    ordered = tuple(window_ids)
    locked = tuple(LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS)
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


def build_dataset_binding_receipt(
    *,
    window_ids: Sequence[str] | None = None,
    content_fingerprints_by_window: Mapping[str, str] | None = None,
    dataset_root: Path | None = None,
) -> DatasetBindingReceipt:
    ordered = _assert_window_set(
        window_ids if window_ids is not None else LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS
    )
    # External Batch-A lock anchor (WP1 / #4030); do not recompute.
    selection = LOCKED_DEVELOPMENT_SELECTION_SHA256

    content_digest: str | None = None
    local_proof_required = True
    quality = DATASET_STATUS_LOCAL_PROOF_REQUIRED
    limitations = [
        "Batch-A 39-window bank is identity-bound for planning only; "
        "hh_hl eligibility still requires Design-GO ratification.",
        "Physical content fingerprints are not asserted without local proof.",
        "Single-run #4372 dataset must not be auto-promoted to campaign dataset.",
    ]

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
        content_digest = canonical_hash(
            {"window_content_fingerprints": [fps[wid] for wid in ordered]}
        )
        if dataset_root is not None and Path(dataset_root).exists():
            local_proof_required = False
            quality = "BOUND_WITH_SUPPLIED_CONTENT_FINGERPRINTS"
            limitations = (
                "Content fingerprints were caller-supplied; local root existence "
                "checked but per-window on-disk rehash is a separate local gate.",
            )

    proof_cmd = (
        "python -m tools.arvp_vacation.hh_hl_campaign_plan prove-dataset "
        "--dataset-root <LOCAL_WINDOW_BANK_ROOT>"
    )
    return DatasetBindingReceipt(
        dataset_contract_version=DATASET_CONTRACT_VERSION,
        dataset_root_kind=DATASET_ROOT_KIND,
        window_count=len(ordered),
        ordered_window_ids=ordered,
        selection_sha256=selection,
        content_fingerprint_digest=content_digest,
        symbol=SYMBOL,
        venue=VENUE,
        timeframe=TIMEFRAME,
        quality_gate_status=quality,
        known_limitations=tuple(limitations),
        local_proof_required=local_proof_required,
        local_proof_command=proof_cmd,
    )
