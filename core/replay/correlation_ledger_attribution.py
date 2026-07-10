"""Correlation ledger campaign/lane attribution helpers (ARVP P1 telemetry)."""

from __future__ import annotations

import os
from typing import Any, Mapping

CDB_CAMPAIGN_ID_ENV = "CDB_CAMPAIGN_ID"

DECISION_BLOCK = "BLOCK"
DECISION_ALLOW = "ALLOW"

NO_CHAIN_REASON_NO_SIGNALS = "NO_SIGNALS_OR_GATE_IDLE"
NO_CHAIN_REASON_RISK_BLOCKED = "RISK_BLOCKED_NO_PROMOTABLE_CHAIN"


def resolve_campaign_id() -> str | None:
    raw = os.getenv(CDB_CAMPAIGN_ID_ENV, "").strip()
    return raw or None


def _payload_config_hash(payload: Mapping[str, Any]) -> str | None:
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        raw = metadata.get("config_hash")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    raw_top = payload.get("config_hash")
    if isinstance(raw_top, str) and raw_top.strip():
        return raw_top.strip()
    return None


def _payload_bot_id(payload: Mapping[str, Any]) -> str | None:
    raw = payload.get("bot_id")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        raw_meta = metadata.get("bot_id")
        if isinstance(raw_meta, str) and raw_meta.strip():
            return raw_meta.strip()
    return None


def _payload_strategy_id(payload: Mapping[str, Any]) -> str | None:
    raw = payload.get("strategy_id")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        snapshot = metadata.get("config_snapshot")
        if isinstance(snapshot, dict):
            raw_snap = snapshot.get("strategy_id")
            if isinstance(raw_snap, str) and raw_snap.strip():
                return raw_snap.strip()
    return None


def _payload_campaign_id(payload: Mapping[str, Any]) -> str | None:
    raw = payload.get("campaign_id")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        raw_meta = metadata.get("campaign_id")
        if isinstance(raw_meta, str) and raw_meta.strip():
            return raw_meta.strip()
    return None


def build_signal_ledger_payload(signal_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return correlation_ledger payload for SIGNAL with campaign attribution."""
    payload = dict(signal_payload)
    campaign_id = resolve_campaign_id()
    if campaign_id:
        payload["campaign_id"] = campaign_id
    return payload


def build_decision_ledger_payload(
    evidence: Mapping[str, Any],
    *,
    signal: Any,
    decision: str,
    reason_code: str | None,
) -> dict[str, Any]:
    """Return correlation_ledger payload for DECISION with lane attribution."""
    payload = dict(evidence)
    payload["decision"] = decision
    if reason_code is not None:
        payload["reason_code"] = reason_code
    strategy_id = getattr(signal, "strategy_id", None)
    bot_id = getattr(signal, "bot_id", None)
    if strategy_id:
        payload["strategy_id"] = strategy_id
    if bot_id:
        payload["bot_id"] = bot_id
    metadata = getattr(signal, "metadata", None)
    if isinstance(metadata, dict):
        config_hash = metadata.get("config_hash")
        if isinstance(config_hash, str) and config_hash.strip():
            payload.setdefault("metadata", {})
            if isinstance(payload["metadata"], dict):
                payload["metadata"]["config_hash"] = config_hash.strip()
    campaign_id = resolve_campaign_id()
    if campaign_id:
        payload["campaign_id"] = campaign_id
    return payload


def _row_matches_lane(
    row: Mapping[str, Any],
    *,
    bot_id: str | None,
    strategy_id: str | None,
    campaign_id: str | None,
    config_hash: str | None,
) -> bool:
    payload = row.get("payload")
    if not isinstance(payload, dict):
        payload = {}
    if bot_id and _payload_bot_id(payload) != bot_id:
        return False
    if strategy_id and _payload_strategy_id(payload) != strategy_id:
        return False
    if campaign_id and _payload_campaign_id(payload) != campaign_id:
        return False
    if config_hash and _payload_config_hash(payload) != config_hash:
        return False
    return True


def derive_no_chain_reason(summary: Mapping[str, Any]) -> str | None:
    signals = int(summary.get("signals_emitted") or 0)
    orders = int(summary.get("orders") or 0)
    fills = int(summary.get("fills") or 0)
    blocks_total = int(summary.get("blocks_total") or 0)

    if signals == 0:
        return NO_CHAIN_REASON_NO_SIGNALS
    if fills > 0 or orders > 0:
        return None
    if blocks_total > 0:
        return NO_CHAIN_REASON_RISK_BLOCKED
    return None


def aggregate_lane_campaign_evidence(
    rows: list[Mapping[str, Any]],
    *,
    bot_id: str | None = None,
    strategy_id: str | None = None,
    campaign_id: str | None = None,
    config_hash: str | None = None,
) -> dict[str, Any]:
    """Aggregate per-lane campaign evidence from correlation_ledger rows."""
    filtered = [
        row
        for row in rows
        if _row_matches_lane(
            row,
            bot_id=bot_id,
            strategy_id=strategy_id,
            campaign_id=campaign_id,
            config_hash=config_hash,
        )
    ]

    signals_emitted = 0
    decisions_total = 0
    approvals = 0
    blocks_total = 0
    blocks_by_reason: dict[str, int] = {}
    orders = 0
    fills = 0

    for row in filtered:
        event_type = str(row.get("event_type") or "").upper()
        payload = row.get("payload")
        if not isinstance(payload, dict):
            payload = {}

        if event_type == "SIGNAL":
            signals_emitted += 1
            continue
        if event_type == "DECISION":
            decisions_total += 1
            decision = str(payload.get("decision") or "").upper()
            reason_code = payload.get("reason_code")
            if decision == DECISION_BLOCK:
                blocks_total += 1
                if isinstance(reason_code, str) and reason_code.strip():
                    code = reason_code.strip()
                    blocks_by_reason[code] = blocks_by_reason.get(code, 0) + 1
            elif decision == DECISION_ALLOW:
                approvals += 1
            continue
        if event_type == "ORDER":
            orders += 1
            continue
        if event_type == "FILL":
            fills += 1

    summary: dict[str, Any] = {
        "campaign_id": campaign_id,
        "bot_id": bot_id,
        "strategy_id": strategy_id,
        "config_hash": config_hash,
        "signals_emitted": signals_emitted,
        "decisions_total": decisions_total,
        "approvals": approvals,
        "blocks_total": blocks_total,
        "blocks_by_reason": blocks_by_reason,
        "orders": orders,
        "fills": fills,
        "no_chain_reason": None,
    }
    summary["no_chain_reason"] = derive_no_chain_reason(summary)
    return summary
