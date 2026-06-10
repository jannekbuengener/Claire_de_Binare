from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from typing import Any

from core.utils.clock import utcnow

logger = logging.getLogger(__name__)

CHAIN_STATUSES = [
    "no_events",
    "signal_only",
    "signal_decision",
    "signal_decision_order",
    "complete_chain",
    "malformed_chain",
]

REQUIRED_TYPES = ["SIGNAL", "DECISION", "ORDER", "FILL"]
KNOWN_TYPES = {"SIGNAL", "DECISION", "ORDER", "FILL", "ORDER(paper_)"}


def _utcnow() -> str:
    return utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_event_type(raw: str) -> str:
    upper = raw.upper()
    if upper == "ORDER" or upper.startswith("ORDER("):
        return "ORDER"
    return upper


def _parse_ts(ts: Any) -> datetime | None:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    return None


def is_malformed(event: dict) -> str | None:
    if not isinstance(event, dict):
        return "event is not a dict"
    etype = event.get("event_type")
    if not etype or not isinstance(etype, str):
        return "missing or invalid event_type"
    norm = normalize_event_type(etype)
    if norm not in KNOWN_TYPES and etype not in KNOWN_TYPES:
        return f"unknown event_type: {etype}"
    ts = event.get("ts_ms")
    if ts is None:
        return "missing ts_ms"
    if isinstance(ts, str) and not ts.strip():
        return "empty ts_ms"
    return None


class ChainDetector:
    def __init__(
        self,
        events: list[dict] | None = None,
        events_by_type_status: list[dict] | None = None,
        campaign_start_utc: str | None = None,
        strict_lineage: bool = False,
    ):
        self._events = events or []
        self._events_by_type_status = events_by_type_status or []
        self._campaign_start_utc = campaign_start_utc
        self._strict_lineage = strict_lineage

    def classify(self) -> str:
        raw_types: set[str] = set()

        if self._events:
            for ev in self._events:
                raw_types.add(normalize_event_type(ev.get("event_type", "")))
        elif self._events_by_type_status:
            for entry in self._events_by_type_status:
                raw_types.add(normalize_event_type(entry.get("event_type", "")))
        else:
            return "no_events"

        has_malformed = any(is_malformed(ev) for ev in self._events)
        if has_malformed and self._events:
            return "malformed_chain"

        if not raw_types:
            return "no_events"

        if REQUIRED_TYPES[3] in raw_types:
            if raw_types.issuperset(REQUIRED_TYPES):
                return "complete_chain"
        if REQUIRED_TYPES[2] in raw_types:
            if raw_types.issuperset(REQUIRED_TYPES[:3]):
                return "signal_decision_order"
        if REQUIRED_TYPES[1] in raw_types:
            if raw_types.issuperset(REQUIRED_TYPES[:2]):
                return "signal_decision"
        if REQUIRED_TYPES[0] in raw_types:
            return "signal_only"

        return "signal_only"

    def detect(self) -> dict[str, Any]:
        chain_status = self.classify()
        complete = chain_status == "complete_chain"

        sorted_events: list[dict] = []
        for ev in self._events:
            parsed_ts = _parse_ts(ev.get("ts_ms"))
            if parsed_ts:
                sorted_events.append((parsed_ts, ev))
        sorted_events.sort(key=lambda x: x[0])

        seen_ids: set[str] = set()
        deduped: list[dict] = []
        for _, ev in sorted_events:
            eid = ev.get("id")
            if eid is not None:
                eid_str = str(eid)
                if eid_str in seen_ids:
                    continue
                seen_ids.add(eid_str)
            deduped.append(ev)
        sorted_events = deduped

        event_ids: list[str] | None = None
        if self._events:
            ids = []
            for ev in sorted_events:
                eid = ev.get("id")
                if eid is not None:
                    ids.append(str(eid))
            if ids:
                event_ids = ids

        first_ts = None
        last_ts = None
        if sorted_events:
            first_parsed = _parse_ts(sorted_events[0].get("ts_ms"))
            last_parsed = _parse_ts(sorted_events[-1].get("ts_ms"))
            if first_parsed:
                first_ts = first_parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
            if last_parsed:
                last_ts = last_parsed.strftime("%Y-%m-%dT%H:%M:%SZ")

        observed_norm: set[str] = set()
        for ev in self._events:
            observed_norm.add(normalize_event_type(ev.get("event_type", "")))
        for entry in self._events_by_type_status:
            observed_norm.add(normalize_event_type(entry.get("event_type", "")))

        missing = [t for t in REQUIRED_TYPES if t not in observed_norm]

        limitations: list[str] = []

        if self._strict_lineage and complete and self._events:
            lineage_hashes = set()
            for ev in self._events:
                lh = ev.get("lineage_hash")
                if lh:
                    lineage_hashes.add(str(lh))
            if len(lineage_hashes) > 1:
                limitations.append(f"multiple lineage_hashes: {lineage_hashes}")
            elif len(lineage_hashes) == 0:
                limitations.append("no lineage_hash data available")

        if not self._events:
            limitations.append("aggregated counts only; no individual events")

        bad_count = sum(1 for ev in self._events if is_malformed(ev))
        if bad_count > 0:
            limitations.append(f"{bad_count} malformed event(s)")

        result: dict[str, Any] = {
            "chain_status": chain_status,
            "complete": complete,
            "event_count": len(self._events) if self._events else None,
            "event_ids": event_ids,
            "first_event_ts": first_ts,
            "last_event_ts": last_ts,
            "missing_steps": missing,
            "observed_types": sorted(observed_norm),
            "limitations": limitations,
            "no_mutation": True,
            "observed_at_utc": _utcnow(),
        }

        if complete:
            result["export_trigger"] = self._build_export_trigger()

        return result

    def _build_export_trigger(self) -> dict[str, Any]:
        sorted_events: list[dict] = []
        for ev in self._events:
            parsed_ts = _parse_ts(ev.get("ts_ms"))
            if parsed_ts:
                sorted_events.append((parsed_ts, ev))
        sorted_events.sort(key=lambda x: x[0])
        seen_ids: set[str] = set()
        sorted_unique: list[dict] = []
        for _, ev in sorted_events:
            eid = ev.get("id")
            if eid is not None:
                eid_str = str(eid)
                if eid_str in seen_ids:
                    continue
                seen_ids.add(eid_str)
            sorted_unique.append(ev)
        sorted_events = sorted_unique

        window_start = None
        window_end = None
        if sorted_events:
            first_parsed = _parse_ts(sorted_events[0].get("ts_ms"))
            last_parsed = _parse_ts(sorted_events[-1].get("ts_ms"))
            if first_parsed:
                window_start = first_parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
            if last_parsed:
                window_end = last_parsed.strftime("%Y-%m-%dT%H:%M:%SZ")

        return {
            "export_candidate": True,
            "suggested_window_start_utc": window_start,
            "suggested_window_end_utc": window_end,
            "source_campaign_id": None,
            "evidence_class": "natural_paper_evidence",
            "next_tools": [
                "paper_reference_window.v1 export",
                "replay-vs-paper compare",
                "simulator calibration",
                "regime scorecard",
            ],
        }

    @classmethod
    def from_probe_result(
        cls, probe_result: dict[str, Any], strict_lineage: bool = False
    ) -> ChainDetector:
        evidence = probe_result.get("evidence", {})
        events = evidence.get("events", None)
        events_by_type = evidence.get("events_by_type_status", None)
        campaign_start = evidence.get("campaign_start_utc", None)
        return cls(
            events=events,
            events_by_type_status=events_by_type,
            campaign_start_utc=campaign_start,
            strict_lineage=strict_lineage,
        )


def load_events(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        events = data.get("events") or data.get("event_ids") or data.get("results")
        if isinstance(events, list):
            return events
        for key in ("correlation_ledger", "ledger"):
            sub = data.get(key, {})
            if isinstance(sub, dict):
                ev = sub.get("evidence", {}).get("events") or sub.get(
                    "evidence", {}
                ).get("event_ids")
                if isinstance(ev, list):
                    return ev
    return []


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ARVP Chain Detector \u2014 classify correlation_ledger chains"
    )
    parser.add_argument(
        "--ledger-input",
        help="Path to JSON file with ledger events or full probe output",
    )
    parser.add_argument(
        "--classify-only",
        action="store_true",
        help="Only output chain classification (no full detect result)",
    )
    parser.add_argument(
        "--strict-lineage",
        action="store_true",
        help="Require shared lineage_hash for complete_chain",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    if not args.ledger_input:
        parser.print_help()
        sys.exit(1)

    raw_events = load_events(args.ledger_input)
    detector = ChainDetector(events=raw_events, strict_lineage=args.strict_lineage)

    if args.classify_only:
        print(detector.classify())
    else:
        result = detector.detect()
        result["source_file"] = args.ledger_input
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
