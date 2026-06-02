"""Control Room read-only signal layer v1 — side-effect-free domain component.

Issues:
    #2802 — [PHASE-2][SURREALDB][SLICE-6] Visual control-room read-only signal layer
    Parent: #2778 (Phase-2 epic)
    Epic: #1976

Scope:
    Aggregate operator-visible status/warning/guardrail signals from in-memory
    Phase-2 artifacts (Context Package v2, hybrid ranking, decision replay v2,
    Agent OS readiness, operator certification). Deterministic, stable-sorted output.
    No DB access. No SurrealDB SDK. No MCP. No networking. No file writes.

Guardrails:
    - Signal layer is orientation, not authorization.
    - LR remains NO-GO; no Live-Go; no Echtgeld-Go.
    - No automatic code, issue, or runtime action from signal output.
    - Orthogonal to Wave-19 control_room_view_builder (9 visual view types).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash
from core.utils.clock import utcnow

SCHEMA_VERSION = "control-room-signal-layer/v1"

SEVERITIES: frozenset[str] = frozenset(
    {"PASS", "WARN", "FAIL", "BLOCKED", "SKIPPED", "UNKNOWN"}
)

_SEVERITY_RANK: dict[str, int] = {
    "BLOCKED": 6,
    "FAIL": 5,
    "WARN": 4,
    "UNKNOWN": 3,
    "SKIPPED": 2,
    "PASS": 1,
}

GUARDRAILS: tuple[str, ...] = (
    "Control-room signals are orientation, not authorization.",
    "LR remains NO-GO; no Live-Go.",
    "No Echtgeld-Go.",
    "No automatic code, issue, or runtime action from signal output.",
    "Board stage trade-capable does not imply live capital or strategy approval.",
    "Weak or unresolved evidence must not be presented as verified.",
)

_ADOPTION_STATUSES: frozenset[str] = frozenset(
    {"pass", "warn", "fail", "blocked", "skipped"}
)
_FINAL_VERDICTS: frozenset[str] = frozenset({"certified", "fail"})

_SENSITIVE_KEY_RE = re.compile(
    r"(token|secret|password|api[_-]?key|credential|private[_-]?key|auth)",
    re.IGNORECASE,
)

_SECRET_VALUE_RE = re.compile(
    r"(Bearer\s+\S+|sk-[A-Za-z0-9_-]{8,}|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)",
    re.IGNORECASE,
)

_URL_QUERY_SECRET_RE = re.compile(
    r"[?&](?:token|api[_-]?key|secret|password|credential|auth)=[^&\s#\"']+",
    re.IGNORECASE,
)

# Positive authorization wording only (negated guardrails like "no Live-Go" are allowed).
_FORBIDDEN_OUTPUT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?<!no )(?<!not )live[- ]go(?!\s*;)", re.IGNORECASE),
    re.compile(r"(?<!no )(?<!not )echtgeld[- ]go", re.IGNORECASE),
    re.compile(r"approved for trading", re.IGNORECASE),
    re.compile(r"authorized for live", re.IGNORECASE),
)


class ControlRoomSignalLayerError(ValueError):
    """Raised when signal-layer inputs are invalid or unsafe."""


@dataclass(frozen=True)
class ControlRoomSignalLayerRequest:
    generated_for_scope: str
    context_package: Mapping[str, Any] | None = None
    ranked_results: Sequence[Mapping[str, Any]] | None = None
    decision_replay: Mapping[str, Any] | None = None
    agent_os_readiness: Mapping[str, Any] | None = None
    operator_certification: Mapping[str, Any] | None = None
    generated_at_or_as_of: str | None = None


def _utc_now_iso() -> str:
    return utcnow().isoformat()


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return str(value).strip() or None


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _is_sensitive_key(key: str) -> bool:
    return bool(_SENSITIVE_KEY_RE.search(key))


def _looks_like_secret_value(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return False
    return bool(_SECRET_VALUE_RE.search(text) or _URL_QUERY_SECRET_RE.search(text))


def _redact_value(key: str, value: Any, path: str, summary: list[dict[str, str]]) -> Any:
    if _is_sensitive_key(key) or _looks_like_secret_value(value):
        summary.append(
            {
                "path": path,
                "field": key,
                "redaction_type": "sensitive_key"
                if _is_sensitive_key(key)
                else "secret_value_pattern",
            }
        )
        return "[REDACTED]"
    if isinstance(value, dict):
        return _redact_mapping(value, path, summary)
    if isinstance(value, list):
        return [
            _redact_value(key, item, f"{path}[{index}]", summary)
            for index, item in enumerate(value)
        ]
    return value


def _redact_mapping(
    raw: Mapping[str, Any],
    path: str,
    summary: list[dict[str, str]],
) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in raw.items():
        key_text = str(key)
        if key_text.startswith("_"):
            continue
        child_path = f"{path}.{key_text}" if path else key_text
        redacted[key_text] = _redact_value(key_text, value, child_path, summary)
    return redacted


def _redact_card_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    summary: list[dict[str, str]] = []
    return _redact_mapping(payload, "signal_card", summary)


def _severity_rank(severity: str) -> int:
    return _SEVERITY_RANK.get(severity, 0)


def _card_sort_key(card: Mapping[str, Any]) -> tuple[int, str, str]:
    severity = _as_str(card.get("severity")) or "UNKNOWN"
    card_id = _as_str(card.get("card_id")) or ""
    source = _as_str(card.get("source")) or ""
    return (-_severity_rank(severity), card_id, source)


def _sanitize_free_text(text: str) -> str:
    if _looks_like_secret_value(text):
        return "[REDACTED]"
    if _SECRET_VALUE_RE.search(text) or _URL_QUERY_SECRET_RE.search(text):
        return "[REDACTED]"
    if _SENSITIVE_KEY_RE.search(text):
        return "[REDACTED]"
    return text


def _make_card(
    *,
    card_id: str,
    source: str,
    severity: str,
    title: str,
    detail: str = "",
    caveats: Sequence[str] | None = None,
    skip_reason: str | None = None,
) -> dict[str, Any]:
    if severity not in SEVERITIES:
        severity = "UNKNOWN"
    payload: dict[str, Any] = {
        "card_id": card_id,
        "source": source,
        "severity": severity,
        "title": title,
        "detail": _sanitize_free_text(detail),
    }
    if caveats:
        payload["caveats"] = sorted(
            {_sanitize_free_text(str(c)) for c in caveats if c}
        )
    if skip_reason:
        payload["skip_reason"] = _sanitize_free_text(skip_reason)
    return _redact_card_payload(payload)


def _resolve_ranked_results(
    request: ControlRoomSignalLayerRequest,
) -> list[Mapping[str, Any]]:
    if request.ranked_results is not None:
        return [item for item in request.ranked_results if isinstance(item, Mapping)]
    package = request.context_package
    if package is None:
        return []
    ranked_context = package.get("ranked_context")
    if isinstance(ranked_context, Mapping):
        results = ranked_context.get("results")
        if isinstance(results, list):
            return [item for item in results if isinstance(item, Mapping)]
    return []


def _extract_from_context_package(
    package: Mapping[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[str], list[str], list[str], list[str]]:
    cards: list[dict[str, Any]] = []
    blocking: list[str] = []
    warnings: list[str] = []
    required_validation: list[str] = []
    limitations: list[str] = []

    if package is None:
        limitations.append("context_package_not_provided")
        return cards, blocking, warnings, required_validation, limitations

    limitations.extend(
        str(item)
        for item in sorted(set(_as_list(package.get("limitations"))))
        if item
    )

    for limitation in limitations:
        if "not_provided" in limitation or "unverified" in limitation:
            warnings.append(f"context package limitation: {limitation}")
            cards.append(
                _make_card(
                    card_id="context_package.limitation",
                    source="context_package",
                    severity="WARN",
                    title="Context package limitation",
                    detail=limitation,
                )
            )

    redaction = _as_list(package.get("redaction_summary"))
    if redaction:
        warnings.append(
            f"context package redacted {len(redaction)} field(s); verify source artifacts"
        )
        cards.append(
            _make_card(
                card_id="context_package.redaction",
                source="context_package",
                severity="WARN",
                title="Context package redaction applied",
                detail=f"{len(redaction)} redacted field(s) in package build",
            )
        )

    return cards, blocking, warnings, required_validation, limitations


def _extract_from_ranking(
    ranked: Sequence[Mapping[str, Any]],
    *,
    had_explicit_ranking_input: bool,
) -> tuple[list[dict[str, Any]], list[str], list[str], list[str]]:
    cards: list[dict[str, Any]] = []
    warnings: list[str] = []
    required_validation: list[str] = []
    limitations: list[str] = []

    if not ranked:
        if had_explicit_ranking_input:
            limitations.append("ranked_results_empty")
        else:
            limitations.append("ranked_results_not_provided")
        return cards, warnings, required_validation, limitations

    for index, row in enumerate(ranked):
        stable_id = (
            _as_str(row.get("source_ref"))
            or _as_str(row.get("result_id"))
            or f"rank-{index}"
        )
        explanation = row.get("ranking_explanation")
        if not isinstance(explanation, Mapping):
            explanation = {}

        row_warnings = sorted(
            set(_as_str(w) or "" for w in _as_list(row.get("warnings")))
            | set(_as_str(w) or "" for w in _as_list(explanation.get("warnings")))
        )
        row_warnings = [w for w in row_warnings if w]

        caveats = sorted(
            set(
                str(c)
                for c in _as_list(explanation.get("caveats"))
                if c
            )
        )

        severity = "PASS"
        if row_warnings or caveats:
            severity = "WARN"
        if _as_bool(row.get("inferred")):
            severity = "WARN"
            if "Result is inferred; verify against repo or live evidence." not in caveats:
                caveats.append(
                    "Result is inferred; verify against repo or live evidence."
                )

        if severity == "WARN":
            for warning in row_warnings:
                warnings.append(
                    _sanitize_free_text(
                        f"ranking {_sanitize_free_text(stable_id)}: "
                        f"{_sanitize_free_text(warning)}"
                    )
                )
            required_validation.append(
                _sanitize_free_text(
                    f"Verify ranking result {stable_id} against repo or verified evidence"
                )
            )

        cards.append(
            _make_card(
                card_id=f"ranking.{stable_id}",
                source="hybrid_retrieval_ranking",
                severity=severity,
                title=f"Ranking signal: {stable_id}",
                detail=f"score={explanation.get('final_score', row.get('score', 'n/a'))}",
                caveats=caveats or None,
            )
        )

    return cards, warnings, required_validation, limitations


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _extract_from_decision_replay(
    replay: Mapping[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[str], list[str], list[str]]:
    cards: list[dict[str, Any]] = []
    warnings: list[str] = []
    required_validation: list[str] = []
    limitations: list[str] = []

    if replay is None:
        limitations.append("decision_replay_not_provided")
        return cards, warnings, required_validation, limitations

    replay_id = _as_str(replay.get("replay_id")) or _as_str(
        replay.get("primary_decision_id")
    ) or "replay"

    unresolved = [
        _as_str(ref) or ""
        for ref in _as_list(replay.get("unresolved_evidence_refs"))
        if _as_str(ref)
    ]
    if not unresolved:
        evidence_chain = replay.get("evidence_chain")
        if isinstance(evidence_chain, Mapping):
            unresolved = [
                _as_str(ref) or ""
                for ref in _as_list(evidence_chain.get("unresolved"))
                if _as_str(ref)
            ]

    evidence_warnings = sorted(
        set(_as_str(w) or "" for w in _as_list(replay.get("evidence_warnings")) if w)
    )
    replay_warnings = sorted(
        set(_as_str(w) or "" for w in _as_list(replay.get("warnings")) if w)
    )

    resolution_status = _as_str(replay.get("evidence_resolution_status")) or ""

    if unresolved:
        detail = f"{len(unresolved)} unresolved evidence ref(s)"
        warnings.append(f"decision replay {replay_id}: {detail}")
        required_validation.append(
            f"Resolve or document unresolved evidence refs for replay {replay_id}"
        )
        cards.append(
            _make_card(
                card_id=f"decision_replay.{replay_id}.unresolved_evidence",
                source="decision_replay",
                severity="WARN",
                title="Unresolved evidence in decision replay",
                detail=detail,
                caveats=unresolved[:5],
            )
        )

    for warning in evidence_warnings + replay_warnings:
        if "unresolved" in warning.lower():
            warnings.append(f"decision replay {replay_id}: {warning}")
            cards.append(
                _make_card(
                    card_id=f"decision_replay.{replay_id}.warning",
                    source="decision_replay",
                    severity="WARN",
                    title="Decision replay evidence warning",
                    detail=warning,
                )
            )

    if resolution_status and resolution_status.lower() not in {
        "resolved",
        "complete",
        "ok",
    }:
        warnings.append(
            f"decision replay {replay_id}: evidence_resolution_status={resolution_status}"
        )
        cards.append(
            _make_card(
                card_id=f"decision_replay.{replay_id}.resolution",
                source="decision_replay",
                severity="WARN",
                title="Evidence resolution incomplete",
                detail=resolution_status,
            )
        )

    replay_limitations = _as_list(replay.get("limitations"))
    for item in sorted(set(str(x) for x in replay_limitations if x)):
        limitations.append(f"decision_replay:{item}")

    return cards, warnings, required_validation, limitations


def _extract_from_readiness(
    readiness: Mapping[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[str], list[str], list[str], list[str]]:
    cards: list[dict[str, Any]] = []
    blocking: list[str] = []
    warnings: list[str] = []
    required_validation: list[str] = []
    limitations: list[str] = []

    if readiness is None:
        limitations.append("agent_os_readiness_not_provided")
        return cards, blocking, warnings, required_validation, limitations

    level = _as_str(readiness.get("readiness_level")) or "unknown"
    readiness_id = _as_str(readiness.get("readiness_id")) or "readiness"

    for finding in sorted(_as_str(f) or "" for f in _as_list(readiness.get("blocking_findings")) if f):
        blocking.append(f"agent os readiness: {finding}")
        cards.append(
            _make_card(
                card_id=f"readiness.{readiness_id}.blocking",
                source="agent_os_readiness",
                severity="BLOCKED",
                title="Agent OS readiness blocking finding",
                detail=finding,
            )
        )

    for finding in sorted(_as_str(f) or "" for f in _as_list(readiness.get("weak_findings")) if f):
        warnings.append(f"agent os readiness: {finding}")
        cards.append(
            _make_card(
                card_id=f"readiness.{readiness_id}.weak",
                source="agent_os_readiness",
                severity="WARN",
                title="Agent OS readiness weak finding",
                detail=finding,
            )
        )

    for missing in sorted(
        _as_str(m) or "" for m in _as_list(readiness.get("missing_inputs")) if m
    ):
        limitations.append(f"readiness_missing:{missing}")
        cards.append(
            _make_card(
                card_id=f"readiness.{readiness_id}.missing",
                source="agent_os_readiness",
                severity="UNKNOWN",
                title="Agent OS readiness missing input",
                detail=missing,
            )
        )

    for validation in sorted(
        _as_str(v) or "" for v in _as_list(readiness.get("required_validation")) if v
    ):
        required_validation.append(validation)

    if level == "blocked" and not blocking:
        blocking.append("agent os readiness level is blocked")

    if level == "blocked":
        cards.append(
            _make_card(
                card_id=f"readiness.{readiness_id}.level",
                source="agent_os_readiness",
                severity="BLOCKED",
                title="Agent OS readiness blocked",
                detail=f"readiness_level={level}",
            )
        )
    elif level == "weak":
        warnings.append(f"agent os readiness level is {level}")
        cards.append(
            _make_card(
                card_id=f"readiness.{readiness_id}.level",
                source="agent_os_readiness",
                severity="WARN",
                title="Agent OS readiness weak",
                detail=f"readiness_level={level}",
            )
        )

    return cards, blocking, warnings, required_validation, limitations


def _extract_from_certification(
    cert: Mapping[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[str], list[str], list[str], list[str]]:
    cards: list[dict[str, Any]] = []
    blocking: list[str] = []
    warnings: list[str] = []
    required_validation: list[str] = []
    limitations: list[str] = []

    if cert is None:
        limitations.append("operator_certification_not_provided")
        return cards, blocking, warnings, required_validation, limitations

    adoption_status = _as_str(cert.get("adoption_status", ""))
    adoption_lower = adoption_status.lower() if adoption_status else ""
    final_verdict = _as_str(cert.get("final_verdict", ""))
    final_lower = final_verdict.lower() if final_verdict else ""

    for item in _as_list(cert.get("blocked_checks_with_reason")):
        if not isinstance(item, Mapping):
            continue
        check = _as_str(item.get("check", "?"))
        reason = _as_str(item.get("reason", ""))
        detail = f"{check}" + (f" — {reason}" if reason else "")
        blocking.append(
            _sanitize_free_text(f"operator certification blocked: {detail}")
        )
        cards.append(
            _make_card(
                card_id=f"certification.blocked.{check}",
                source="operator_certification",
                severity="BLOCKED",
                title="Operator certification blocked check",
                detail=detail,
            )
        )

    for gate in _as_list(cert.get("gate_matrix")):
        if not isinstance(gate, Mapping):
            continue
        status = (_as_str(gate.get("status")) or "").lower()
        check_id = _as_str(gate.get("check_id", "?"))
        detail = _as_str(gate.get("detail", ""))
        if status == "blocked":
            msg = f"gate blocked: {check_id}" + (f" — {detail}" if detail else "")
            blocking.append(_sanitize_free_text(f"operator certification {msg}"))
            cards.append(
                _make_card(
                    card_id=f"certification.gate.{check_id}",
                    source="operator_certification",
                    severity="BLOCKED",
                    title="Operator certification gate blocked",
                    detail=msg,
                )
            )
        elif status == "fail" and gate.get("blocking") is True:
            msg = f"gate fail (blocking): {check_id}" + (f" — {detail}" if detail else "")
            blocking.append(_sanitize_free_text(f"operator certification {msg}"))
            cards.append(
                _make_card(
                    card_id=f"certification.gate.{check_id}",
                    source="operator_certification",
                    severity="FAIL",
                    title="Operator certification gate fail",
                    detail=msg,
                )
            )
        elif status == "fail":
            msg = f"gate fail (non-blocking): {check_id}" + (f" — {detail}" if detail else "")
            warnings.append(_sanitize_free_text(f"operator certification {msg}"))
            required_validation.append(
                "Document non-blocking certification gate failures before adoption claims"
            )
            cards.append(
                _make_card(
                    card_id=f"certification.gate.{check_id}",
                    source="operator_certification",
                    severity="WARN",
                    title="Operator certification gate warn",
                    detail=msg,
                )
            )

    if final_lower == "fail":
        blocking.append("operator certification final_verdict=fail")
        cards.append(
            _make_card(
                card_id="certification.final_verdict",
                source="operator_certification",
                severity="FAIL",
                title="Operator certification failed",
                detail="final_verdict=fail",
            )
        )

    if adoption_lower in {"fail", "blocked"}:
        blocking.append(f"operator certification adoption_status={adoption_lower}")
        severity = "BLOCKED" if adoption_lower == "blocked" else "FAIL"
        cards.append(
            _make_card(
                card_id="certification.adoption_status",
                source="operator_certification",
                severity=severity,
                title="Operator certification adoption blocked",
                detail=f"adoption_status={adoption_lower}",
            )
        )
        required_validation.append(
            "Operator certification failed; re-run make context-certify after remediation"
        )

    if adoption_lower == "warn":
        warnings.append("operator certification adoption_status=warn")
        required_validation.append(
            "Document adoption caveats before claiming Context/Memory operator readiness"
        )
        cards.append(
            _make_card(
                card_id="certification.adoption_status",
                source="operator_certification",
                severity="WARN",
                title="Operator certification adoption warn",
                detail="adoption_status=warn",
            )
        )

    if adoption_lower == "skipped":
        skip_reason = "adoption_status=skipped"
        for item in _as_list(cert.get("skipped_checks_with_reason")):
            if isinstance(item, Mapping):
                reason = _as_str(item.get("reason"))
                if reason:
                    skip_reason = reason
                    break
        warnings.append("operator certification adoption_status=skipped")
        cards.append(
            _make_card(
                card_id="certification.adoption_status",
                source="operator_certification",
                severity="SKIPPED",
                title="Operator certification skipped",
                detail="adoption_status=skipped",
                skip_reason=skip_reason,
            )
        )

    if adoption_lower and adoption_lower not in _ADOPTION_STATUSES:
        msg = f"operator certification invalid adoption_status: {adoption_status!r}"
        warnings.append(msg)
        required_validation.append(
            "adoption_status must be one of: pass, warn, fail, blocked, skipped"
        )
        cards.append(
            _make_card(
                card_id="certification.adoption_status.invalid",
                source="operator_certification",
                severity="WARN",
                title="Operator certification invalid adoption status",
                detail=msg,
            )
        )

    if final_lower and final_lower not in _FINAL_VERDICTS:
        msg = f"operator certification invalid final_verdict: {final_verdict!r}"
        warnings.append(msg)
        required_validation.append(
            "Include valid final_verdict (certified or fail) from make context-certify"
        )
        cards.append(
            _make_card(
                card_id="certification.final_verdict.invalid",
                source="operator_certification",
                severity="WARN",
                title="Operator certification invalid final verdict",
                detail=msg,
            )
        )

    if not final_lower:
        msg = "operator certification incomplete: missing final_verdict"
        warnings.append(msg)
        required_validation.append(
            "Include final_verdict from make context-certify output; "
            "adoption_status alone is not CertifyReport proof."
        )
        cards.append(
            _make_card(
                card_id="certification.final_verdict.missing",
                source="operator_certification",
                severity="WARN",
                title="Operator certification missing final verdict",
                detail=msg,
            )
        )

    skipped_checks = _as_list(cert.get("skipped_checks_with_reason"))
    if skipped_checks and adoption_lower != "skipped":
        count = sum(1 for item in skipped_checks if isinstance(item, Mapping))
        if count:
            warnings.append(
                f"operator certification has {count} skipped check(s); document skip reasons"
            )

    return cards, blocking, warnings, required_validation, limitations


def _build_source_artifacts(request: ControlRoomSignalLayerRequest) -> list[dict[str, str]]:
    ranked = _resolve_ranked_results(request)
    entries = [
        ("context_package", "present" if request.context_package is not None else "missing"),
        (
            "ranked_results",
            "present"
            if request.ranked_results is not None or ranked
            else "missing",
        ),
        (
            "decision_replay",
            "present" if request.decision_replay is not None else "missing",
        ),
        (
            "agent_os_readiness",
            "present" if request.agent_os_readiness is not None else "missing",
        ),
        (
            "operator_certification",
            "present" if request.operator_certification is not None else "missing",
        ),
    ]
    return [
        {"artifact": name, "status": status}
        for name, status in sorted(entries, key=lambda item: item[0])
    ]


def _merge_guardrails(
    request: ControlRoomSignalLayerRequest,
) -> list[str]:
    merged = list(GUARDRAILS)
    package = request.context_package
    if isinstance(package, Mapping):
        for item in _as_list(package.get("guardrails")):
            text = _as_str(item)
            if text and text not in merged:
                merged.append(text)
    readiness = request.agent_os_readiness
    if isinstance(readiness, Mapping):
        for item in _as_list(readiness.get("guardrails")):
            text = _as_str(item)
            if text and text not in merged:
                merged.append(text)
    return sorted(set(merged))


def _derive_summary_status(
    *,
    signal_cards: Sequence[Mapping[str, Any]],
    blocking_findings: Sequence[str],
    warnings: Sequence[str],
    limitations: Sequence[str],
    any_input_present: bool,
) -> str:
    if blocking_findings:
        card_severities = [
            _as_str(card.get("severity")) or "UNKNOWN" for card in signal_cards
        ]
        if "BLOCKED" in card_severities:
            return "BLOCKED"
        return "FAIL"

    card_severities = [_as_str(card.get("severity")) or "UNKNOWN" for card in signal_cards]
    if "FAIL" in card_severities:
        return "FAIL"
    if "BLOCKED" in card_severities:
        return "BLOCKED"

    if not any_input_present:
        return "UNKNOWN"

    if limitations and not warnings and "PASS" not in card_severities:
        if all(s in {"SKIPPED", "UNKNOWN"} for s in card_severities if s):
            return "UNKNOWN"
        return "WARN"

    if warnings or "WARN" in card_severities:
        return "WARN"

    if card_severities and all(s == "PASS" for s in card_severities):
        return "PASS"

    if card_severities and all(s == "SKIPPED" for s in card_severities):
        return "SKIPPED"

    if limitations:
        return "WARN"

    return "UNKNOWN"


def _assert_no_forbidden_phrases(payload: Mapping[str, Any]) -> None:
    from core.replay.canonical_json import canonical_json_dumps

    text = canonical_json_dumps(payload)
    for pattern in _FORBIDDEN_OUTPUT_PATTERNS:
        if pattern.search(text):
            raise ControlRoomSignalLayerError(
                f"signal output contains forbidden authorization phrase: {pattern.pattern!r}"
            )


def build_control_room_signal_layer_v1(
    request: ControlRoomSignalLayerRequest,
) -> dict[str, Any]:
    """Build a read-only control-room signal envelope from in-memory artifacts."""
    scope = _as_str(request.generated_for_scope)
    if not scope:
        raise ControlRoomSignalLayerError("generated_for_scope is required")

    generated_at = request.generated_at_or_as_of or _utc_now_iso()

    cards: list[dict[str, Any]] = []
    blocking_findings: list[str] = []
    warnings: list[str] = []
    required_validation: list[str] = []
    limitations: list[str] = []

    cp_cards, cp_block, cp_warn, cp_rv, cp_lim = _extract_from_context_package(
        request.context_package
    )
    cards.extend(cp_cards)
    blocking_findings.extend(cp_block)
    warnings.extend(cp_warn)
    required_validation.extend(cp_rv)
    limitations.extend(cp_lim)

    ranked = _resolve_ranked_results(request)
    rk_cards, rk_warn, rk_rv, rk_lim = _extract_from_ranking(
        ranked,
        had_explicit_ranking_input=request.ranked_results is not None,
    )
    cards.extend(rk_cards)
    warnings.extend(rk_warn)
    required_validation.extend(rk_rv)
    limitations.extend(rk_lim)

    dr_cards, dr_warn, dr_rv, dr_lim = _extract_from_decision_replay(
        request.decision_replay
    )
    cards.extend(dr_cards)
    warnings.extend(dr_warn)
    required_validation.extend(dr_rv)
    limitations.extend(dr_lim)

    ar_cards, ar_block, ar_warn, ar_rv, ar_lim = _extract_from_readiness(
        request.agent_os_readiness
    )
    cards.extend(ar_cards)
    blocking_findings.extend(ar_block)
    warnings.extend(ar_warn)
    required_validation.extend(ar_rv)
    limitations.extend(ar_lim)

    cert_cards, cert_block, cert_warn, cert_rv, cert_lim = _extract_from_certification(
        request.operator_certification
    )
    cards.extend(cert_cards)
    blocking_findings.extend(cert_block)
    warnings.extend(cert_warn)
    required_validation.extend(cert_rv)
    limitations.extend(cert_lim)

    signal_cards = sorted(cards, key=_card_sort_key)
    blocking_findings = sorted(
        {_sanitize_free_text(item) for item in blocking_findings if item}
    )
    warnings = sorted({_sanitize_free_text(item) for item in warnings if item})
    required_validation = sorted(
        {_sanitize_free_text(item) for item in required_validation if item}
    )
    limitations = sorted(set(limitations))

    any_input_present = any(
        [
            request.context_package is not None,
            request.ranked_results is not None,
            bool(ranked),
            request.decision_replay is not None,
            request.agent_os_readiness is not None,
            request.operator_certification is not None,
        ]
    )

    summary_status = _derive_summary_status(
        signal_cards=signal_cards,
        blocking_findings=blocking_findings,
        warnings=warnings,
        limitations=limitations,
        any_input_present=any_input_present,
    )

    guardrails = _merge_guardrails(request)
    source_artifacts = _build_source_artifacts(request)

    hash_input = {
        "schema_version": SCHEMA_VERSION,
        "generated_for_scope": scope,
        "source_artifacts": source_artifacts,
        "summary_status": summary_status,
        "signal_cards": signal_cards,
        "blocking_findings": blocking_findings,
        "warnings": warnings,
        "required_validation": required_validation,
        "guardrails": guardrails,
        "limitations": limitations,
    }
    content_hash = canonical_hash(hash_input)

    envelope: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_for_scope": scope,
        "generated_at_or_as_of": generated_at,
        "source_artifacts": source_artifacts,
        "summary_status": summary_status,
        "signal_cards": signal_cards,
        "blocking_findings": blocking_findings,
        "warnings": warnings,
        "required_validation": required_validation,
        "guardrails": guardrails,
        "limitations": limitations,
        "determinism": {
            "hash_algorithm": "canonical_sha256",
            "wall_clock_excluded": True,
            "content_hash": content_hash,
        },
    }

    _assert_no_forbidden_phrases(envelope)
    return envelope
