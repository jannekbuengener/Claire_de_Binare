#!/usr/bin/env python3
"""Build local-only issue candidates from security_alert_delta artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INPUT_FILENAME = "security_alert_delta.json"
OUTPUT_FILENAME = "security_alert_issue_candidates.json"
SCHEMA_VERSION = "security_alert_issue_candidates.v1"
DEFAULT_INPUT_PATH = Path("artifacts/security-alert-readout/delta") / INPUT_FILENAME
DEFAULT_OUT_DIR = Path("artifacts/security-alert-readout/delta")
DEFAULT_LABELS = ["type:security", "triage:offen"]
DEDUPE_MARKER_TEMPLATE = "<!-- cdb-security-alert-group:{fingerprint} -->"
ALLOWED_SOURCES = frozenset({"code_scanning", "dependabot"})
REF_2289 = "Refs #2289"
REF_2290 = "Refs #2290"
REF_2292 = "Refs #2292"

_CVE_RE = re.compile(r"^cve-\d{4}-\d+$")
_COMPONENT_KEYS = (
    "affected_component",
    "component",
    "package",
    "package_name",
    "dependency",
    "image",
    "artifact",
    "container_image",
)


class SecurityAlertIssueCandidatesError(ValueError):
    """Raised when candidate generation input is invalid."""


def _to_printable_ascii(value: object, *, max_len: int = 200) -> str:
    raw = str(value)[:max_len]
    return "".join(
        chr(code) for char in raw if 0x20 <= (code := ord(char)) <= 0x7E
    )


def canonicalize(value: object, *, fallback: str = "unknown", max_len: int = 200) -> str:
    if value is None:
        return fallback
    text = _to_printable_ascii(value, max_len=max_len).strip().lower()
    text = " ".join(text.split())
    return text or fallback


def _bounded(value: str, *, limit: int) -> str:
    trimmed = value.strip()
    return trimmed[:limit] if len(trimmed) > limit else trimmed


def severity_band_from(value: object) -> str:
    severity = canonicalize(value)
    if severity in {"critical", "high", "error"}:
        return "high"
    if severity in {"medium", "warning"}:
        return "medium"
    if severity in {"low", "note", "not_provided", "unknown"}:
        return "low"
    return "low"


def _highest_severity(left: str, right: str) -> str:
    rank = {"critical": 4, "high": 3, "error": 3, "medium": 2, "warning": 2, "low": 1, "note": 1}
    left_rank = rank.get(left, 0)
    right_rank = rank.get(right, 0)
    return left if left_rank >= right_rank else right


def _contains_cdb_python_service(component: str) -> bool:
    return component.startswith("library/cdb_")


def _looks_like_trivy_wave(source: str, subject: str, component: str) -> bool:
    if source != "code_scanning":
        return False
    return bool(_CVE_RE.match(subject)) and _contains_cdb_python_service(component)


def _looks_like_grafana_curl(component: str, subject: str) -> bool:
    joined = f"{component} {subject}"
    return "grafana" in joined or "curl" in joined or "libcurl" in joined


def _safe_component_from_mapping(record: dict[str, Any]) -> str:
    for key in _COMPONENT_KEYS:
        raw_value = record.get(key)
        if not isinstance(raw_value, str):
            continue
        candidate = canonicalize(raw_value, fallback="unknown", max_len=180)
        if candidate == "unknown":
            continue
        if "://" in candidate:
            continue
        return candidate
    return "unknown"


def _build_component_index(delta: dict[str, Any]) -> dict[tuple[str, int], str]:
    component_index: dict[tuple[str, int], str] = {}
    for key in ("new_alerts", "reopened_alerts"):
        for alert in _safe_list_dict(delta.get(key, [])):
            source = canonicalize(alert.get("source"))
            number_raw = alert.get("number")
            if not isinstance(number_raw, int):
                continue
            component = _safe_component_from_mapping(alert)
            if component == "unknown":
                continue
            component_index[(source, number_raw)] = component
    return component_index


def _resolve_escalation_component(
    *,
    escalation: dict[str, Any],
    source: str,
    component_index: dict[tuple[str, int], str],
) -> str:
    component = _safe_component_from_mapping(escalation)
    if component != "unknown":
        return component

    number_raw = escalation.get("number")
    if isinstance(number_raw, int):
        return component_index.get((source, number_raw), "unknown")
    return "unknown"


def build_fingerprint(
    *,
    source: str,
    severity_band: str,
    subject: str,
    affected_component: str,
    branch: str,
) -> str:
    seed = "|".join(
        (
            canonicalize(source),
            canonicalize(severity_band),
            canonicalize(subject),
            canonicalize(affected_component),
            canonicalize(branch),
        )
    )
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _build_title(
    *,
    source: str,
    severity: str,
    subject: str,
    affected_component: str,
) -> str:
    source_tag = _bounded(source, limit=24)
    severity_tag = _bounded(severity, limit=16)
    subject_part = _bounded(subject, limit=90)
    component_part = _bounded(affected_component, limit=64)
    return (
        f"[Security][Alert][{source_tag}][{severity_tag}] "
        f"{subject_part} — {component_part}"
    )


def _safe_counts(delta: dict[str, Any]) -> dict[str, int]:
    counts_raw = delta.get("counts", {})
    if not isinstance(counts_raw, dict):
        return {
            "new_alerts": 0,
            "reopened_alerts": 0,
            "new_groups": 0,
            "escalation_alerts": 0,
        }
    return {
        "new_alerts": int(counts_raw.get("new_alerts", 0)),
        "reopened_alerts": int(counts_raw.get("reopened_alerts", 0)),
        "new_groups": int(counts_raw.get("new_groups", 0)),
        "escalation_alerts": int(counts_raw.get("escalation_alerts", 0)),
    }


def _base_candidate(
    *,
    source: str,
    severity: str,
    subject: str,
    affected_component: str,
    branch: str,
    counts: dict[str, int],
    current_reference_now_utc: str,
) -> dict[str, Any]:
    src = canonicalize(source)
    sev = canonicalize(severity)
    sev_band = severity_band_from(sev)
    subj = canonicalize(subject, max_len=180)
    component = canonicalize(affected_component, max_len=180)
    br = canonicalize(branch, max_len=120)

    fingerprint = build_fingerprint(
        source=src,
        severity_band=sev_band,
        subject=subj,
        affected_component=component,
        branch=br,
    )

    references = [REF_2289]
    labels = list(DEFAULT_LABELS)
    if _looks_like_trivy_wave(src, subj, component):
        references.append(REF_2290)
        labels.append("status:blocked")
    if _looks_like_grafana_curl(component, subj):
        references.append(REF_2292)

    dedupe_marker = DEDUPE_MARKER_TEMPLATE.format(fingerprint=fingerprint)
    title = _build_title(
        source=src,
        severity=sev_band,
        subject=subj,
        affected_component=component,
    )
    safe_references = sorted(set(references))
    safe_labels = sorted(set(labels))
    return {
        "fingerprint": fingerprint,
        "source": src,
        "severity": sev,
        "severity_band": sev_band,
        "subject": subj,
        "affected_component": component,
        "branch": br,
        "suggested_title": title,
        "suggested_labels": safe_labels,
        "body_safe_fields": {
            "generated_from_readout": True,
            "current_reference_now_utc": current_reference_now_utc,
            "source": src,
            "severity": sev,
            "severity_band": sev_band,
            "counts": counts,
            "subject": subj,
            "affected_component": component,
            "branch": br,
            "fingerprint": fingerprint,
            "next_action": "Human triage and bounded remediation planning.",
            "references": safe_references,
        },
        "references": safe_references,
        "dedupe_marker": dedupe_marker,
    }


def _extract_current_reference(delta: dict[str, Any]) -> str:
    current = delta.get("sources", {})
    if not isinstance(current, dict):
        return ""
    value = current.get("current_reference_now_utc", "")
    return _to_printable_ascii(value, max_len=40).strip()


def _candidate_from_group(
    *,
    group: dict[str, Any],
    related_escalations: list[dict[str, Any]],
    component_index: dict[tuple[str, int], str],
    counts: dict[str, int],
    current_reference_now_utc: str,
) -> dict[str, Any] | None:
    source = canonicalize(group.get("source"))
    if source not in ALLOWED_SOURCES:
        return None
    subject = canonicalize(group.get("subject"))
    branch = canonicalize(group.get("branch"), fallback="not_provided")

    severity = "not_provided"
    affected_component = "unknown"
    if related_escalations:
        severity = related_escalations[0].get("severity", "not_provided")
        affected_component = _resolve_escalation_component(
            escalation=related_escalations[0],
            source=source,
            component_index=component_index,
        )

    return _base_candidate(
        source=source,
        severity=severity,
        subject=subject,
        affected_component=affected_component,
        branch=branch,
        counts=counts,
        current_reference_now_utc=current_reference_now_utc,
    )


def _candidate_from_escalation(
    *,
    escalation: dict[str, Any],
    component_index: dict[tuple[str, int], str],
    counts: dict[str, int],
    current_reference_now_utc: str,
) -> dict[str, Any] | None:
    source = canonicalize(escalation.get("source"))
    if source not in ALLOWED_SOURCES:
        return None
    affected_component = _resolve_escalation_component(
        escalation=escalation,
        source=source,
        component_index=component_index,
    )
    return _base_candidate(
        source=source,
        severity=canonicalize(escalation.get("severity"), fallback="not_provided"),
        subject=canonicalize(escalation.get("subject")),
        affected_component=affected_component,
        branch=canonicalize(escalation.get("branch"), fallback="not_provided"),
        counts=counts,
        current_reference_now_utc=current_reference_now_utc,
    )


def _merge_candidates(existing: dict[str, Any], incoming: dict[str, Any]) -> None:
    existing["severity"] = _highest_severity(
        str(existing.get("severity", "unknown")),
        str(incoming.get("severity", "unknown")),
    )
    existing["severity_band"] = severity_band_from(existing["severity"])
    existing["suggested_labels"] = sorted(
        set(existing.get("suggested_labels", [])) | set(incoming.get("suggested_labels", []))
    )
    merged_refs = sorted(set(existing.get("references", [])) | set(incoming.get("references", [])))
    existing["references"] = merged_refs
    existing["body_safe_fields"]["references"] = merged_refs
    existing["body_safe_fields"]["severity"] = existing["severity"]
    existing["body_safe_fields"]["severity_band"] = existing["severity_band"]
    existing["suggested_title"] = _build_title(
        source=existing["source"],
        severity=existing["severity_band"],
        subject=existing["subject"],
        affected_component=existing["affected_component"],
    )


def _safe_list_dict(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _normalize_delta_keys(raw: dict[str, Any]) -> dict[str, Any]:
    """Bridge the real security_alert_delta.v1 JSON shape to the keys this module reads.

    The delta module emits ``escalation_alerts`` (not ``escalations``) and flat
    ``*_count`` integer fields (not a ``counts`` dict).  This normalizer adds the
    expected keys when they are absent, leaving existing keys untouched so that
    test fixtures that already use the canonical names are unaffected.
    """
    normalized = dict(raw)

    # escalation_alerts (delta module) → escalations (this module)
    if "escalation_alerts" in raw and "escalations" not in raw:
        normalized["escalations"] = raw["escalation_alerts"]

    # flat *_count ints → counts dict
    if "counts" not in raw and any(
        k in raw for k in ("new_alert_count", "new_group_count", "escalation_alert_count")
    ):
        normalized["counts"] = {
            "new_alerts": int(raw.get("new_alert_count", 0)),
            "reopened_alerts": int(raw.get("reopened_alert_count", 0)),
            "new_groups": int(raw.get("new_group_count", 0)),
            "escalation_alerts": int(raw.get("escalation_alert_count", 0)),
        }

    # current_readout.reference_now_utc → sources.current_reference_now_utc
    if "sources" not in raw and isinstance(raw.get("current_readout"), dict):
        normalized["sources"] = {
            "current_reference_now_utc": raw["current_readout"].get("reference_now_utc", "")
        }

    return normalized


def build_candidates(delta: dict[str, Any]) -> list[dict[str, Any]]:
    schema = str(delta.get("schema_version", ""))
    if not schema.startswith("security_alert_delta"):
        raise SecurityAlertIssueCandidatesError(
            "Invalid input schema; expected security_alert_delta.*"
        )

    delta = _normalize_delta_keys(delta)

    counts = _safe_counts(delta)
    current_reference = _extract_current_reference(delta)
    new_groups = _safe_list_dict(delta.get("new_groups", []))
    escalations = _safe_list_dict(delta.get("escalations", []))
    component_index = _build_component_index(delta)

    by_fingerprint: dict[str, dict[str, Any]] = {}

    for group in new_groups:
        source = canonicalize(group.get("source"))
        subject = canonicalize(group.get("subject"))
        branch = canonicalize(group.get("branch"), fallback="not_provided")
        related_escalations = [
            item
            for item in escalations
            if canonicalize(item.get("source")) == source
            and canonicalize(item.get("subject")) == subject
            and canonicalize(item.get("branch"), fallback="not_provided") == branch
        ]
        candidate = _candidate_from_group(
            group=group,
            related_escalations=related_escalations,
            component_index=component_index,
            counts=counts,
            current_reference_now_utc=current_reference,
        )
        if candidate is None:
            continue
        by_fingerprint[candidate["fingerprint"]] = candidate

    if bool(delta.get("escalation_needed", False)):
        for escalation in escalations:
            candidate = _candidate_from_escalation(
                escalation=escalation,
                component_index=component_index,
                counts=counts,
                current_reference_now_utc=current_reference,
            )
            if candidate is None:
                continue
            fingerprint = candidate["fingerprint"]
            if fingerprint in by_fingerprint:
                _merge_candidates(by_fingerprint[fingerprint], candidate)
            else:
                by_fingerprint[fingerprint] = candidate

    candidates = sorted(
        by_fingerprint.values(),
        key=lambda item: (
            item["source"],
            item["severity_band"],
            item["subject"],
            item["affected_component"],
            item["branch"],
        ),
    )
    return candidates


def build_output_payload(*, delta: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input_schema_version": str(delta.get("schema_version", "")),
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def generate_candidates(*, input_path: Path, out_dir: Path) -> dict[str, Any]:
    try:
        delta = json.loads(input_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SecurityAlertIssueCandidatesError(f"Cannot read input file: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SecurityAlertIssueCandidatesError(f"Invalid JSON input: {exc}") from exc

    if not isinstance(delta, dict):
        raise SecurityAlertIssueCandidatesError("Input JSON root must be an object")

    candidates = build_candidates(delta)
    payload = build_output_payload(delta=delta, candidates=candidates)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / OUTPUT_FILENAME
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build local-only security alert issue candidates from delta JSON."
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT_PATH),
        metavar="PATH",
        help="Path to security_alert_delta.json",
    )
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT_DIR),
        metavar="DIR",
        help="Output directory for security_alert_issue_candidates.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        payload = generate_candidates(
            input_path=Path(args.input),
            out_dir=Path(args.out_dir),
        )
    except SecurityAlertIssueCandidatesError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"security alert issue candidates generated: {payload['candidate_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

