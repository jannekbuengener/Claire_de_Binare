from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from jsonschema.validators import validator_for

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = PROJECT_ROOT / "docs" / "contracts"

_CANDIDATE_SCHEMA_PATH = (
    CONTRACTS_DIR / "profitability_candidate_contract.v1.schema.json"
)
_DATA_QUALITY_SCHEMA_PATH = (
    CONTRACTS_DIR / "profitability_dataset_quality_report.v1.schema.json"
)
_REPLAY_SCHEMA_PATH = CONTRACTS_DIR / "profitability_replay_report.v1.schema.json"
_SCENARIO_SCHEMA_PATH = (
    CONTRACTS_DIR / "profitability_scenario_stress_summary.v1.schema.json"
)
_ECONOMICS_SCHEMA_PATH = (
    CONTRACTS_DIR / "profitability_execution_economics_assessment.v1.schema.json"
)
_HARVESTER_SCHEMA_PATH = CONTRACTS_DIR / "profitability_harvester_ref.v1.schema.json"
_COMPARE_SCHEMA_PATH = CONTRACTS_DIR / "shadow_comparison.v1.schema.json"
_SCORECARD_SCHEMA_PATH = CONTRACTS_DIR / "arvp_regime_scorecard.v1.schema.json"
_PACKET_SCHEMA_PATH = CONTRACTS_DIR / "profitability_evidence_packet.v1.schema.json"

_DEFAULT_SAFETY_BOUNDARIES = (
    "LR remains NO-GO.",
    "Board stage trade-capable is not Live-Go.",
    "Evidence packets are research-only and do not authorize paper or live execution.",
    "No automatic candidate promotion is authorized.",
)


class ProfitabilityEvidencePacketAssemblerError(ValueError):
    """Raised when packet assembly cannot complete safely."""


@dataclass(frozen=True, slots=True)
class ValidatedJsonDocument:
    artifact_role: str
    path: Path
    display_path: str
    sha256: str
    schema_ref: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class AssemblyResult:
    packet: dict[str, Any]
    markdown: str


def _deterministic_json_dumps(payload: Any, *, pretty: bool = False) -> str:
    kwargs: dict[str, Any] = {
        "ensure_ascii": True,
        "sort_keys": True,
    }
    if pretty:
        kwargs["indent"] = 2
    else:
        kwargs["separators"] = (",", ":")
    return json.dumps(payload, **kwargs)


def _sha256_hex(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def _sha256_ref(raw_bytes: bytes) -> str:
    return f"sha256:{_sha256_hex(raw_bytes)}"


def _normalize_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _normalize_schema_ref(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def _load_schema(schema_path: Path) -> dict[str, Any]:
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ProfitabilityEvidencePacketAssemblerError(
            f"Failed to read schema {schema_path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ProfitabilityEvidencePacketAssemblerError(
            f"Invalid JSON in schema {schema_path}: {exc}"
        ) from exc


def _read_json_payload(path: Path) -> tuple[bytes, dict[str, Any]]:
    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        raise ProfitabilityEvidencePacketAssemblerError(
            f"Failed to read JSON input {path}: {exc}"
        ) from exc

    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ProfitabilityEvidencePacketAssemblerError(
            f"Invalid UTF-8 in JSON input {path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ProfitabilityEvidencePacketAssemblerError(
            f"Invalid JSON in {path}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise ProfitabilityEvidencePacketAssemblerError(
            f"JSON input {path} must be an object"
        )

    return raw_bytes, payload


def _sorted_validation_errors(errors: list[Any]) -> list[Any]:
    return sorted(
        errors,
        key=lambda err: (
            ".".join(str(part) for part in err.path),
            ".".join(str(part) for part in err.schema_path),
            err.message,
        ),
    )


def _validate_payload_against_schema(
    payload: dict[str, Any],
    *,
    schema_path: Path,
    artifact_role: str,
) -> None:
    schema = _load_schema(schema_path)
    validator_cls = validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    errors = _sorted_validation_errors(list(validator.iter_errors(payload)))
    if errors:
        first = errors[0]
        path = ".".join(str(part) for part in first.path) or "<root>"
        raise ProfitabilityEvidencePacketAssemblerError(
            f"Schema mismatch for {artifact_role} against {_normalize_schema_ref(schema_path)} "
            f"at {path}: {first.message}"
        )


def _validate_document(
    artifact_role: str,
    path: Path,
    schema_path: Path,
) -> ValidatedJsonDocument:
    raw_bytes, payload = _read_json_payload(path)
    _validate_payload_against_schema(
        payload, schema_path=schema_path, artifact_role=artifact_role
    )
    return ValidatedJsonDocument(
        artifact_role=artifact_role,
        path=path.resolve(),
        display_path=_normalize_path(path),
        sha256=_sha256_ref(raw_bytes),
        schema_ref=_normalize_schema_ref(schema_path),
        payload=payload,
    )


def _parse_generated_at_utc(raw_value: str) -> str:
    candidate = raw_value.strip()
    if not candidate:
        raise ProfitabilityEvidencePacketAssemblerError(
            "--generated-at-utc must be a non-empty UTC timestamp"
        )

    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ProfitabilityEvidencePacketAssemblerError(
            f"--generated-at-utc must be ISO-8601 UTC: {exc}"
        ) from exc

    if parsed.tzinfo is None:
        raise ProfitabilityEvidencePacketAssemblerError(
            "--generated-at-utc must include an explicit UTC offset"
        )

    normalized = parsed.astimezone(UTC)
    return normalized.isoformat().replace("+00:00", "Z")


def _require_mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProfitabilityEvidencePacketAssemblerError(f"{name} must be a JSON object")
    return value


def _require_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProfitabilityEvidencePacketAssemblerError(
            f"{name} must be a non-empty string"
        )
    return value.strip()


def _require_number(value: object, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ProfitabilityEvidencePacketAssemblerError(f"{name} must be a number")
    return float(value)


def _require_non_negative_number(value: object, name: str) -> float:
    result = _require_number(value, name)
    if result < 0.0:
        raise ProfitabilityEvidencePacketAssemblerError(f"{name} must be >= 0")
    return result


def _require_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ProfitabilityEvidencePacketAssemblerError(f"{name} must be an integer")
    return value


def _require_non_negative_int(value: object, name: str) -> int:
    result = _require_int(value, name)
    if result < 0:
        raise ProfitabilityEvidencePacketAssemblerError(f"{name} must be >= 0")
    return result


def _optional_string(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _require_string(value, name)


def _optional_number(value: object, name: str) -> float | None:
    if value is None:
        return None
    return _require_number(value, name)


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _slugify_for_packet_id(raw_value: str) -> str:
    allowed: list[str] = []
    for char in raw_value.lower():
        if char.isalnum():
            allowed.append(char)
        elif char in {"-", "_", " ", "/", "."}:
            allowed.append("-")
    slug = "".join(allowed).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    if not slug:
        slug = "packet"
    return slug


def _build_packet_id(
    candidate_id: str, generated_at: str, source_artifacts: list[dict[str, Any]]
) -> str:
    slug = _slugify_for_packet_id(candidate_id.removeprefix("cand-"))[:48]
    digest = _sha256_hex(
        _deterministic_json_dumps(
            {
                "candidate_id": candidate_id,
                "generated_at": generated_at,
                "source_artifacts": source_artifacts,
            }
        ).encode("utf-8")
    )[:12]
    return f"pep-{slug}-{digest}"


def _build_source_artifacts(
    documents: list[ValidatedJsonDocument],
) -> list[dict[str, Any]]:
    return [
        {
            "artifact_role": doc.artifact_role,
            "path": doc.display_path,
            "schema_ref": doc.schema_ref,
            "sha256": doc.sha256,
        }
        for doc in documents
    ]


def _validate_cross_document_consistency(
    candidate_contract: ValidatedJsonDocument,
    data_quality_report: ValidatedJsonDocument,
    replay_report: ValidatedJsonDocument,
    scenario_stress_summary: ValidatedJsonDocument,
    economics_assessment: ValidatedJsonDocument,
    harvester_ref: ValidatedJsonDocument,
    replay_vs_paper_compare: ValidatedJsonDocument | None,
    regime_scorecard: ValidatedJsonDocument | None,
) -> None:
    candidate_payload = candidate_contract.payload
    candidate_id = _require_string(
        candidate_payload.get("candidate_id"), "candidate_contract.candidate_id"
    )
    timeframe = _require_string(
        candidate_payload.get("timeframe"), "candidate_contract.timeframe"
    )
    symbol_universe = candidate_payload.get("symbol_universe")
    if not isinstance(symbol_universe, list) or not symbol_universe:
        raise ProfitabilityEvidencePacketAssemblerError(
            "candidate_contract.symbol_universe must be a non-empty list"
        )

    data_quality = data_quality_report.payload
    dq_symbol = _require_string(
        data_quality.get("symbol"), "data_quality_report.symbol"
    )
    dq_timeframe = _require_string(
        data_quality.get("timeframe"), "data_quality_report.timeframe"
    )
    if dq_symbol not in symbol_universe:
        raise ProfitabilityEvidencePacketAssemblerError(
            "data_quality_report.symbol must exist in candidate_contract.symbol_universe"
        )
    if dq_timeframe != timeframe:
        raise ProfitabilityEvidencePacketAssemblerError(
            "data_quality_report.timeframe must match candidate_contract.timeframe"
        )

    replay_payload = replay_report.payload
    replay_candidate_id = _require_string(
        replay_payload.get("candidate_id"), "replay_report.candidate_id"
    )
    replay_symbol = _require_string(
        replay_payload.get("symbol"), "replay_report.symbol"
    )
    replay_timeframe = _require_string(
        replay_payload.get("timeframe"), "replay_report.timeframe"
    )
    if replay_candidate_id != candidate_id:
        raise ProfitabilityEvidencePacketAssemblerError(
            "replay_report.candidate_id must match candidate_contract.candidate_id"
        )
    if replay_symbol not in symbol_universe:
        raise ProfitabilityEvidencePacketAssemblerError(
            "replay_report.symbol must exist in candidate_contract.symbol_universe"
        )
    if replay_timeframe != timeframe:
        raise ProfitabilityEvidencePacketAssemblerError(
            "replay_report.timeframe must match candidate_contract.timeframe"
        )

    scenario_payload = scenario_stress_summary.payload
    if (
        _require_string(
            scenario_payload.get("candidate_id"), "scenario_stress_summary.candidate_id"
        )
        != candidate_id
    ):
        raise ProfitabilityEvidencePacketAssemblerError(
            "scenario_stress_summary.candidate_id must match candidate_contract.candidate_id"
        )

    economics_payload = economics_assessment.payload
    if (
        _require_string(
            economics_payload.get("candidate_id"),
            "execution_economics_assessment.candidate_id",
        )
        != candidate_id
    ):
        raise ProfitabilityEvidencePacketAssemblerError(
            "execution_economics_assessment.candidate_id must match candidate_contract.candidate_id"
        )

    harvester_payload = harvester_ref.payload
    harvester_candidate_id = _optional_string(
        harvester_payload.get("candidate_id"), "harvester_ref.candidate_id"
    )
    if harvester_candidate_id is not None and harvester_candidate_id != candidate_id:
        raise ProfitabilityEvidencePacketAssemblerError(
            "harvester_ref.candidate_id must match candidate_contract.candidate_id"
        )

    replay_run_id = _require_string(
        replay_payload.get("replay_run_id"), "replay_report.replay_run_id"
    )
    if replay_vs_paper_compare is not None:
        compare_payload = replay_vs_paper_compare.payload
        compare_run_id = _require_string(
            compare_payload.get("replay_run_id"),
            "replay_vs_paper_compare.replay_run_id",
        )
        if compare_run_id != replay_run_id:
            raise ProfitabilityEvidencePacketAssemblerError(
                "replay_vs_paper_compare.replay_run_id must match replay_report.replay_run_id"
            )

    if regime_scorecard is not None:
        scorecard_payload = regime_scorecard.payload
        scorecard_run_id = _require_string(
            scorecard_payload.get("run_id"), "regime_scorecard.run_id"
        )
        if scorecard_run_id != replay_run_id:
            raise ProfitabilityEvidencePacketAssemblerError(
                "regime_scorecard.run_id must match replay_report.replay_run_id"
            )


def _extract_replay_metrics(
    replay_report: Mapping[str, Any],
) -> dict[str, float | int | bool | str]:
    raw_avg_win = replay_report.get("avg_win")
    raw_avg_loss = replay_report.get("avg_loss")
    if raw_avg_win is None:
        raise ProfitabilityEvidencePacketAssemblerError(
            "replay_report.avg_win must be explicit; null is not packet-compatible"
        )
    if raw_avg_loss is None:
        raise ProfitabilityEvidencePacketAssemblerError(
            "replay_report.avg_loss must be explicit; null is not packet-compatible"
        )

    avg_loss = abs(_require_number(raw_avg_loss, "replay_report.avg_loss"))

    return {
        "replay_run_id": _require_string(
            replay_report.get("replay_run_id"), "replay_report.replay_run_id"
        ),
        "strategy_id": _require_string(
            replay_report.get("strategy_id"), "replay_report.strategy_id"
        ),
        "symbol": _require_string(replay_report.get("symbol"), "replay_report.symbol"),
        "timeframe": _require_string(
            replay_report.get("timeframe"), "replay_report.timeframe"
        ),
        "generated_at": _require_string(
            replay_report.get("generated_at"), "replay_report.generated_at"
        ),
        "gross_return": _require_number(
            replay_report.get("gross_return"), "replay_report.gross_return"
        ),
        "profit_factor": _require_non_negative_number(
            replay_report.get("profit_factor"), "replay_report.profit_factor"
        ),
        "expectancy": _require_number(
            replay_report.get("expectancy"), "replay_report.expectancy"
        ),
        "win_rate": _require_non_negative_number(
            replay_report.get("win_rate"), "replay_report.win_rate"
        ),
        "avg_win": _require_non_negative_number(raw_avg_win, "replay_report.avg_win"),
        "avg_loss": avg_loss,
        "max_drawdown": _require_non_negative_number(
            replay_report.get("max_drawdown"), "replay_report.max_drawdown"
        ),
        "loss_streak": _require_non_negative_int(
            replay_report.get("loss_streak"), "replay_report.loss_streak"
        ),
        "trade_count": _require_non_negative_int(
            replay_report.get("trade_count"), "replay_report.trade_count"
        ),
        "deterministic_replay_ok": bool(replay_report.get("deterministic_replay_ok")),
        "data_integrity_ok": bool(replay_report.get("data_integrity_ok")),
    }


def _build_regime_scorecard_block(
    regime_scorecard: ValidatedJsonDocument | None,
    missing_evidence: list[dict[str, str]],
) -> dict[str, Any]:
    if regime_scorecard is None:
        missing_evidence.append(
            {
                "artifact_role": "regime_scorecard",
                "classification": "OPTIONAL_NOT_PROVIDED",
                "summary": "No regime scorecard input was provided; packet uses status=unavailable.",
            }
        )
        return {
            "status": "unavailable",
            "artifact_ref": None,
            "summary": "Regime scorecard input was not provided to the assembler.",
        }

    payload = regime_scorecard.payload
    raw_status = _require_string(payload.get("status"), "regime_scorecard.status")
    status = raw_status.replace("-", "_")
    segments = payload.get("segments")
    if not isinstance(segments, list):
        raise ProfitabilityEvidencePacketAssemblerError(
            "regime_scorecard.segments must be a list"
        )

    if status != "ok":
        missing_evidence.append(
            {
                "artifact_role": "regime_scorecard",
                "classification": "UNAVAILABLE_FROM_INPUT",
                "summary": f"Regime scorecard status is {raw_status}; packet propagates this as {status}.",
            }
        )

    return {
        "status": status,
        "artifact_ref": regime_scorecard.display_path,
        "summary": (
            f"Regime scorecard status={raw_status}; source={_require_string(payload.get('source'), 'regime_scorecard.source')}; "
            f"segments={len(segments)}."
        ),
    }


def _safe_decimal_string_to_float(value: object, name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError as exc:
            raise ProfitabilityEvidencePacketAssemblerError(
                f"{name} must be a decimal string when present"
            ) from exc
    return _require_number(value, name)


def _classify_replay_vs_paper(
    replay_vs_paper_compare: ValidatedJsonDocument | None,
    missing_evidence: list[dict[str, str]],
) -> tuple[str, str]:
    if replay_vs_paper_compare is None:
        missing_evidence.append(
            {
                "artifact_role": "replay_vs_paper_compare",
                "classification": "OPTIONAL_NOT_PROVIDED",
                "summary": (
                    "No replay-vs-paper comparison input was provided; "
                    "packet uses replay_vs_paper_status=not_run and simulator_drift=not_assessed."
                ),
            }
        )
        return "not_run", "not_assessed"

    payload = replay_vs_paper_compare.payload
    status = _require_string(payload.get("status"), "replay_vs_paper_compare.status")
    alignment_issue = _optional_string(
        payload.get("alignment_issue"), "replay_vs_paper_compare.alignment_issue"
    )

    if status == "unusable":
        classification = "UNUSABLE_INPUT"
        replay_status = "ambiguous_drift"
        simulator_drift = "unusable"
        if alignment_issue and alignment_issue.startswith("missing_reference"):
            classification = "MISSING_REFERENCE"
            replay_status = "missing_reference"
            simulator_drift = "not_assessed"
        missing_evidence.append(
            {
                "artifact_role": "replay_vs_paper_compare",
                "classification": classification,
                "summary": alignment_issue
                or "Replay-vs-paper comparison was unusable.",
            }
        )
        return replay_status, simulator_drift

    signal_false_neutral = bool(
        payload.get("signal_count_false_neutral_detected", False)
    )
    if signal_false_neutral:
        missing_evidence.append(
            {
                "artifact_role": "replay_vs_paper_compare",
                "classification": "AMBIGUOUS_ALIGNMENT",
                "summary": "Replay-vs-paper compare flagged signal_count_false_neutral_detected=true.",
            }
        )
        return "ambiguous_drift", "ambiguous"

    order_delta = _require_int(
        payload.get("order_count_delta"), "replay_vs_paper_compare.order_count_delta"
    )
    fill_delta = _require_int(
        payload.get("fill_count_delta"), "replay_vs_paper_compare.fill_count_delta"
    )
    fill_rate_delta = _safe_decimal_string_to_float(
        payload.get("fill_rate_delta"), "replay_vs_paper_compare.fill_rate_delta"
    )

    if (
        order_delta == 0
        and fill_delta == 0
        and (fill_rate_delta is None or fill_rate_delta == 0.0)
    ):
        return "aligned", "none"
    if (
        fill_delta < 0
        or order_delta < 0
        or (fill_rate_delta is not None and fill_rate_delta < 0.0)
    ):
        return "pessimistic_drift", "pessimistic"
    if (
        fill_delta > 0
        or order_delta > 0
        or (fill_rate_delta is not None and fill_rate_delta > 0.0)
    ):
        return "optimistic_drift", "optimistic"
    return "ambiguous_drift", "ambiguous"


def _build_scenario_results(
    scenario_stress_summary: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    raw_results = scenario_stress_summary.get("scenario_results")
    if not isinstance(raw_results, list) or not raw_results:
        raise ProfitabilityEvidencePacketAssemblerError(
            "scenario_stress_summary.scenario_results must be a non-empty list"
        )

    scenario_results: list[dict[str, Any]] = []
    summaries: list[str] = []
    for index, raw_result in enumerate(raw_results):
        result = _require_mapping(
            raw_result, f"scenario_stress_summary.scenario_results[{index}]"
        )
        max_drawdown_delta = result.get("max_drawdown_delta")
        if isinstance(max_drawdown_delta, (int, float)) and not isinstance(
            max_drawdown_delta, bool
        ):
            if float(max_drawdown_delta) < 0.0:
                raise ProfitabilityEvidencePacketAssemblerError(
                    "scenario_stress_summary.max_drawdown_delta must be >= 0 to fit profitability_evidence_packet.v1"
                )

        scenario_id = _require_string(
            result.get("scenario_id"), f"scenario_results[{index}].scenario_id"
        )
        status = _require_string(
            result.get("status"), f"scenario_results[{index}].status"
        )
        impact_summary = _require_string(
            result.get("impact_summary"), f"scenario_results[{index}].impact_summary"
        )
        notes = (
            f"domain={_require_string(result.get('domain'), f'scenario_results[{index}].domain')}; "
            f"severity={_require_string(result.get('severity'), f'scenario_results[{index}].severity')}; "
            f"impact={impact_summary}"
        )

        scenario_results.append(
            {
                "scenario_id": scenario_id,
                "status": status,
                "net_return": _optional_number(
                    result.get("net_return_delta"),
                    f"scenario_results[{index}].net_return_delta",
                ),
                "max_drawdown": _optional_number(
                    max_drawdown_delta,
                    f"scenario_results[{index}].max_drawdown_delta",
                ),
                "notes": notes,
            }
        )
        summaries.append(f"{scenario_id}: {status}")
    return scenario_results, summaries


def _build_coverage_readiness(
    *,
    data_quality_report: Mapping[str, Any],
    replay_metrics: Mapping[str, Any],
    scenario_stress_summary: Mapping[str, Any],
    economics_assessment: Mapping[str, Any],
    regime_scorecard_block: Mapping[str, Any],
    replay_vs_paper_status: str,
    harvester_ref: Mapping[str, Any],
) -> dict[str, Any]:
    data_quality_verdict = _require_string(
        data_quality_report.get("quality_verdict"),
        "data_quality_report.quality_verdict",
    )
    overall_stress_outcome = _require_string(
        scenario_stress_summary.get("overall_stress_outcome"),
        "scenario_stress_summary.overall_stress_outcome",
    )
    assessment_status = _require_string(
        economics_assessment.get("assessment_status"),
        "execution_economics_assessment.assessment_status",
    )
    ranking_ready = bool(economics_assessment.get("ranking_ready"))
    replay_ready = bool(replay_metrics["data_integrity_ok"]) and bool(
        replay_metrics["deterministic_replay_ok"]
    )
    regime_ready = regime_scorecard_block["status"] == "ok"
    replay_vs_paper_ready = replay_vs_paper_status == "aligned"
    harvester_refs = harvester_ref.get("source_run_refs")
    harvester_ready = isinstance(harvester_refs, list) and len(harvester_refs) > 0
    data_quality_ready = data_quality_verdict not in {"FAIL", "BLOCKED"}
    scenario_ready = overall_stress_outcome not in {"BLOCKED"}
    economics_ready = assessment_status not in {"FAIL", "BLOCKED"} and ranking_ready

    coverage_report_ready = all(
        [data_quality_ready, replay_ready, scenario_ready, harvester_ready]
    )
    ranking_inputs_complete = all(
        [
            data_quality_ready,
            replay_ready,
            scenario_ready,
            economics_ready,
            replay_vs_paper_ready,
            regime_ready,
        ]
    )

    return {
        "coverage_report_ready": coverage_report_ready,
        "ranking_inputs_complete": ranking_inputs_complete,
        "data_quality_ready": data_quality_ready,
        "economics_ready": economics_ready,
        "scenario_ready": scenario_ready,
        "replay_ready": replay_ready,
        "replay_vs_paper_ready": replay_vs_paper_ready,
        "regime_scorecard_ready": regime_ready,
        "harvester_refs_ready": harvester_ready,
        "summary": (
            "coverage_report_ready="
            f"{coverage_report_ready}; ranking_inputs_complete={ranking_inputs_complete}; "
            f"replay_vs_paper_ready={replay_vs_paper_ready}; regime_scorecard_ready={regime_ready}."
        ),
    }


def _build_recommendation(
    *,
    candidate_contract: Mapping[str, Any],
    economics_assessment: Mapping[str, Any],
    coverage_readiness: Mapping[str, Any],
) -> str:
    candidate_status = _require_string(
        candidate_contract.get("status"), "candidate_contract.status"
    )
    if candidate_status == "UNSAFE":
        return "UNSAFE"
    if candidate_status == "REJECTED":
        return "REJECT"
    if candidate_status in {"PARKED", "STALE", "SUPERSEDED"}:
        return "PARK"
    if not bool(coverage_readiness.get("ranking_inputs_complete")):
        return "NO_RECOMMENDATION"
    if not bool(economics_assessment.get("ranking_ready")):
        return "PARK"
    return "NO_RECOMMENDATION"


def build_profitability_evidence_packet(
    *,
    candidate_contract: ValidatedJsonDocument,
    data_quality_report: ValidatedJsonDocument,
    replay_report: ValidatedJsonDocument,
    scenario_stress_summary: ValidatedJsonDocument,
    economics_assessment: ValidatedJsonDocument,
    harvester_ref: ValidatedJsonDocument,
    generated_at_utc: str,
    replay_vs_paper_compare: ValidatedJsonDocument | None = None,
    regime_scorecard: ValidatedJsonDocument | None = None,
) -> AssemblyResult:
    _validate_cross_document_consistency(
        candidate_contract,
        data_quality_report,
        replay_report,
        scenario_stress_summary,
        economics_assessment,
        harvester_ref,
        replay_vs_paper_compare,
        regime_scorecard,
    )

    replay_metrics = _extract_replay_metrics(replay_report.payload)
    missing_evidence: list[dict[str, str]] = []
    regime_scorecard_block = _build_regime_scorecard_block(
        regime_scorecard, missing_evidence
    )
    replay_vs_paper_status, simulator_drift = _classify_replay_vs_paper(
        replay_vs_paper_compare, missing_evidence
    )
    scenario_results, scenario_summaries = _build_scenario_results(
        scenario_stress_summary.payload
    )

    source_documents = [
        candidate_contract,
        data_quality_report,
        replay_report,
        scenario_stress_summary,
        economics_assessment,
        harvester_ref,
    ]
    if replay_vs_paper_compare is not None:
        source_documents.append(replay_vs_paper_compare)
    if regime_scorecard is not None:
        source_documents.append(regime_scorecard)

    source_artifacts = _build_source_artifacts(source_documents)
    harvester_payload = harvester_ref.payload
    coverage_readiness = _build_coverage_readiness(
        data_quality_report=data_quality_report.payload,
        replay_metrics=replay_metrics,
        scenario_stress_summary=scenario_stress_summary.payload,
        economics_assessment=economics_assessment.payload,
        regime_scorecard_block=regime_scorecard_block,
        replay_vs_paper_status=replay_vs_paper_status,
        harvester_ref=harvester_payload,
    )

    candidate_payload = candidate_contract.payload
    economics_payload = economics_assessment.payload
    data_quality_payload = data_quality_report.payload
    packet = {
        "schema_version": "profitability_evidence_packet.v1",
        "evidence_packet_id": _build_packet_id(
            _require_string(
                candidate_payload.get("candidate_id"), "candidate_contract.candidate_id"
            ),
            generated_at_utc,
            source_artifacts,
        ),
        "candidate_id": _require_string(
            candidate_payload.get("candidate_id"), "candidate_contract.candidate_id"
        ),
        "generated_at": generated_at_utc,
        "dataset_id": _require_string(
            data_quality_payload.get("dataset_id"), "data_quality_report.dataset_id"
        ),
        "dataset_fingerprint": _require_string(
            data_quality_payload.get("dataset_fingerprint"),
            "data_quality_report.dataset_fingerprint",
        ),
        "source_run_refs": _dedupe_preserve_order(
            [
                *[
                    _require_string(value, "harvester_ref.source_run_refs[]")
                    for value in harvester_payload.get("source_run_refs", [])
                ],
                replay_report.display_path,
                scenario_stress_summary.display_path,
                economics_assessment.display_path,
                *(
                    [replay_vs_paper_compare.display_path]
                    if replay_vs_paper_compare is not None
                    else []
                ),
                *(
                    [regime_scorecard.display_path]
                    if regime_scorecard is not None
                    else []
                ),
            ]
        ),
        "gross_return": replay_metrics["gross_return"],
        "net_return": _require_number(
            economics_payload.get("net_return"),
            "execution_economics_assessment.net_return",
        ),
        "fees": _require_non_negative_number(
            _require_mapping(
                economics_payload.get("cost_breakdown"),
                "execution_economics_assessment.cost_breakdown",
            ).get("fees"),
            "execution_economics_assessment.cost_breakdown.fees",
        ),
        "spread_cost": _require_non_negative_number(
            _require_mapping(
                economics_payload.get("cost_breakdown"),
                "execution_economics_assessment.cost_breakdown",
            ).get("spread_cost"),
            "execution_economics_assessment.cost_breakdown.spread_cost",
        ),
        "slippage_cost": _require_non_negative_number(
            _require_mapping(
                economics_payload.get("cost_breakdown"),
                "execution_economics_assessment.cost_breakdown",
            ).get("slippage_cost"),
            "execution_economics_assessment.cost_breakdown.slippage_cost",
        ),
        "profit_factor": replay_metrics["profit_factor"],
        "expectancy": replay_metrics["expectancy"],
        "win_rate": replay_metrics["win_rate"],
        "avg_win": replay_metrics["avg_win"],
        "avg_loss": replay_metrics["avg_loss"],
        "max_drawdown": replay_metrics["max_drawdown"],
        "loss_streak": replay_metrics["loss_streak"],
        "trade_count": replay_metrics["trade_count"],
        "regime_scorecard": regime_scorecard_block,
        "scenario_results": scenario_results,
        "replay_vs_paper_status": replay_vs_paper_status,
        "simulator_drift": simulator_drift,
        "risk_blocks": _require_non_negative_int(
            harvester_payload.get("risk_blocks"), "harvester_ref.risk_blocks"
        ),
        "kill_switch_events": _require_non_negative_int(
            harvester_payload.get("kill_switch_events"),
            "harvester_ref.kill_switch_events",
        ),
        "recommendation": _build_recommendation(
            candidate_contract=candidate_payload,
            economics_assessment=economics_payload,
            coverage_readiness=coverage_readiness,
        ),
        "limitations": _dedupe_preserve_order(
            [
                *[
                    _require_string(v, "candidate_contract.limitations[]")
                    for v in candidate_payload.get("limitations", [])
                ],
                *[
                    _require_string(v, "data_quality_report.limitations[]")
                    for v in data_quality_payload.get("limitations", [])
                ],
                *[
                    _require_string(v, "execution_economics_assessment.limitations[]")
                    for v in economics_payload.get("limitations", [])
                ],
                *[
                    _require_string(v, "scenario_stress_summary.limitations[]")
                    for v in scenario_stress_summary.payload.get("limitations", [])
                ],
                *[
                    _require_string(v, "harvester_ref.limitations[]")
                    for v in harvester_payload.get("limitations", [])
                ],
                *[entry["summary"] for entry in missing_evidence],
                "Assembler is offline and deterministic; no network, runtime, Docker, DB, Redis, secrets, or scheduler access was used.",
            ]
        ),
        "safety_boundaries": _dedupe_preserve_order(
            [
                *[
                    _require_string(v, "candidate_contract.execution_assumptions[]")
                    for v in candidate_payload.get("execution_assumptions", [])
                ],
                *[
                    _require_string(v, "harvester_ref.safety_boundaries[]")
                    for v in harvester_payload.get("safety_boundaries", [])
                ],
                *_DEFAULT_SAFETY_BOUNDARIES,
            ]
        ),
        "source_artifacts": source_artifacts,
        "missing_evidence": missing_evidence,
        "coverage_readiness": coverage_readiness,
    }

    _validate_payload_against_schema(
        packet,
        schema_path=_PACKET_SCHEMA_PATH,
        artifact_role="profitability_evidence_packet",
    )

    markdown = build_profitability_evidence_packet_markdown(
        packet=packet,
        candidate_contract=candidate_contract,
        data_quality_report=data_quality_report,
        replay_report=replay_report,
        scenario_stress_summary=scenario_stress_summary,
        economics_assessment=economics_assessment,
        harvester_ref=harvester_ref,
        replay_vs_paper_compare=replay_vs_paper_compare,
        regime_scorecard=regime_scorecard,
        scenario_summaries=scenario_summaries,
    )
    return AssemblyResult(packet=packet, markdown=markdown)


def build_profitability_evidence_packet_markdown(
    *,
    packet: Mapping[str, Any],
    candidate_contract: ValidatedJsonDocument,
    data_quality_report: ValidatedJsonDocument,
    replay_report: ValidatedJsonDocument,
    scenario_stress_summary: ValidatedJsonDocument,
    economics_assessment: ValidatedJsonDocument,
    harvester_ref: ValidatedJsonDocument,
    replay_vs_paper_compare: ValidatedJsonDocument | None,
    regime_scorecard: ValidatedJsonDocument | None,
    scenario_summaries: list[str],
) -> str:
    coverage = _require_mapping(
        packet.get("coverage_readiness"), "packet.coverage_readiness"
    )
    missing_evidence = packet.get("missing_evidence")
    if not isinstance(missing_evidence, list):
        raise ProfitabilityEvidencePacketAssemblerError(
            "packet.missing_evidence must be a list"
        )

    source_artifacts = packet.get("source_artifacts")
    if not isinstance(source_artifacts, list):
        raise ProfitabilityEvidencePacketAssemblerError(
            "packet.source_artifacts must be a list"
        )

    harvester_payload = harvester_ref.payload
    lines = [
        "# Profitability Evidence Packet Summary",
        "",
        "## Candidate",
        "",
        f"- Candidate ID: `{packet['candidate_id']}`",
        f"- Evidence Packet ID: `{packet['evidence_packet_id']}`",
        f"- Generated At: `{packet['generated_at']}`",
        f"- Recommendation: `{packet['recommendation']}`",
        "",
        "## Source Artifacts",
        "",
    ]

    for artifact in source_artifacts:
        artifact_map = _require_mapping(artifact, "packet.source_artifacts[]")
        lines.append(
            "- "
            f"`{_require_string(artifact_map.get('artifact_role'), 'packet.source_artifacts[].artifact_role')}`: "
            f"`{_require_string(artifact_map.get('path'), 'packet.source_artifacts[].path')}` "
            f"({ _require_string(artifact_map.get('sha256'), 'packet.source_artifacts[].sha256') }, "
            f"schema `{_require_string(artifact_map.get('schema_ref'), 'packet.source_artifacts[].schema_ref')}`)"
        )

    lines += [
        "",
        "## Data Quality",
        "",
        f"- Dataset ID: `{packet['dataset_id']}`",
        f"- Dataset Fingerprint: `{packet['dataset_fingerprint']}`",
        f"- Quality Verdict: `{_require_string(data_quality_report.payload.get('quality_verdict'), 'data_quality_report.quality_verdict')}`",
        "",
        "## Replay Summary",
        "",
        f"- Replay Report: `{replay_report.display_path}`",
        f"- Gross Return: `{packet['gross_return']}`",
        f"- Profit Factor: `{packet['profit_factor']}`",
        f"- Expectancy: `{packet['expectancy']}`",
        f"- Trade Count: `{packet['trade_count']}`",
        "",
        "## Execution Economics",
        "",
        f"- Economics Assessment: `{economics_assessment.display_path}`",
        f"- Net Return: `{packet['net_return']}`",
        f"- Fees / Spread / Slippage: `{packet['fees']}` / `{packet['spread_cost']}` / `{packet['slippage_cost']}`",
        f"- Ranking Ready: `{bool(economics_assessment.payload.get('ranking_ready'))}`",
        "",
        "## Scenario Summary",
        "",
        f"- Scenario Stress Summary: `{scenario_stress_summary.display_path}`",
    ]
    lines.extend([f"- {summary}" for summary in scenario_summaries])

    lines += [
        "",
        "## Harvester Provenance",
        "",
        f"- Harvester Ref: `{harvester_ref.display_path}`",
    ]
    for ref in harvester_payload.get("source_run_refs", []):
        lines.append(
            f"- Source Run Ref: `{_require_string(ref, 'harvester_ref.source_run_refs[]')}`"
        )

    lines += [
        "",
        "## Optional Evidence",
        "",
        f"- Replay-vs-Paper Compare: `{replay_vs_paper_compare.display_path if replay_vs_paper_compare is not None else 'not provided'}`",
        f"- Replay-vs-Paper Status: `{packet['replay_vs_paper_status']}`",
        f"- Simulator Drift: `{packet['simulator_drift']}`",
        f"- Regime Scorecard: `{regime_scorecard.display_path if regime_scorecard is not None else 'not provided'}`",
        f"- Regime Scorecard Status: `{_require_mapping(packet.get('regime_scorecard'), 'packet.regime_scorecard')['status']}`",
        "",
        "## Missing Evidence Classification",
        "",
    ]
    if missing_evidence:
        for entry in missing_evidence:
            entry_map = _require_mapping(entry, "packet.missing_evidence[]")
            lines.append(
                "- "
                f"`{_require_string(entry_map.get('artifact_role'), 'packet.missing_evidence[].artifact_role')}` "
                f"=> `{_require_string(entry_map.get('classification'), 'packet.missing_evidence[].classification')}`: "
                f"{_require_string(entry_map.get('summary'), 'packet.missing_evidence[].summary')}"
            )
    else:
        lines.append("- None")

    lines += [
        "",
        "## Coverage Readiness",
        "",
        f"- Coverage Report Ready: `{bool(coverage.get('coverage_report_ready'))}`",
        f"- Ranking Inputs Complete: `{bool(coverage.get('ranking_inputs_complete'))}`",
        f"- Data Quality Ready: `{bool(coverage.get('data_quality_ready'))}`",
        f"- Economics Ready: `{bool(coverage.get('economics_ready'))}`",
        f"- Scenario Ready: `{bool(coverage.get('scenario_ready'))}`",
        f"- Replay-vs-Paper Ready: `{bool(coverage.get('replay_vs_paper_ready'))}`",
        f"- Regime Scorecard Ready: `{bool(coverage.get('regime_scorecard_ready'))}`",
        f"- Summary: {_require_string(coverage.get('summary'), 'packet.coverage_readiness.summary')}",
        "",
        "## Safety",
        "",
        "- Non-live, non-promotion safety statement: This packet is research-only evidence. "
        "It does not authorize paper trading, live trading, candidate promotion, runtime changes, or capital scaling.",
    ]
    for boundary in packet.get("safety_boundaries", []):
        lines.append(f"- {_require_string(boundary, 'packet.safety_boundaries[]')}")

    return "\n".join(lines) + "\n"


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="profitability_evidence_packet_assembler",
        description=(
            "Build a deterministic offline profitability_evidence_packet.v1 from "
            "explicit validated local inputs."
        ),
    )
    parser.add_argument("--candidate-contract", required=True, type=Path)
    parser.add_argument("--data-quality-report", required=True, type=Path)
    parser.add_argument("--replay-report", required=True, type=Path)
    parser.add_argument("--scenario-stress-summary", required=True, type=Path)
    parser.add_argument("--execution-economics-assessment", required=True, type=Path)
    parser.add_argument("--harvester-ref", required=True, type=Path)
    parser.add_argument("--replay-vs-paper-compare", type=Path)
    parser.add_argument("--regime-scorecard", type=Path)
    parser.add_argument("--generated-at-utc", required=True)
    parser.add_argument("--out-json", required=True, type=Path)
    parser.add_argument("--out-md", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_argument_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 1

    try:
        candidate_contract = _validate_document(
            "candidate_contract", args.candidate_contract, _CANDIDATE_SCHEMA_PATH
        )
        data_quality_report = _validate_document(
            "data_quality_report", args.data_quality_report, _DATA_QUALITY_SCHEMA_PATH
        )
        replay_report = _validate_document(
            "replay_report", args.replay_report, _REPLAY_SCHEMA_PATH
        )
        scenario_stress_summary = _validate_document(
            "scenario_stress_summary",
            args.scenario_stress_summary,
            _SCENARIO_SCHEMA_PATH,
        )
        execution_economics_assessment = _validate_document(
            "execution_economics_assessment",
            args.execution_economics_assessment,
            _ECONOMICS_SCHEMA_PATH,
        )
        harvester_ref = _validate_document(
            "harvester_ref", args.harvester_ref, _HARVESTER_SCHEMA_PATH
        )
        replay_vs_paper_compare = (
            _validate_document(
                "replay_vs_paper_compare",
                args.replay_vs_paper_compare,
                _COMPARE_SCHEMA_PATH,
            )
            if args.replay_vs_paper_compare is not None
            else None
        )
        regime_scorecard = (
            _validate_document(
                "regime_scorecard", args.regime_scorecard, _SCORECARD_SCHEMA_PATH
            )
            if args.regime_scorecard is not None
            else None
        )

        generated_at_utc = _parse_generated_at_utc(args.generated_at_utc)
        result = build_profitability_evidence_packet(
            candidate_contract=candidate_contract,
            data_quality_report=data_quality_report,
            replay_report=replay_report,
            scenario_stress_summary=scenario_stress_summary,
            economics_assessment=execution_economics_assessment,
            harvester_ref=harvester_ref,
            generated_at_utc=generated_at_utc,
            replay_vs_paper_compare=replay_vs_paper_compare,
            regime_scorecard=regime_scorecard,
        )

        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(
            _deterministic_json_dumps(result.packet) + "\n",
            encoding="utf-8",
        )
        args.out_md.write_text(result.markdown, encoding="utf-8")
    except ProfitabilityEvidencePacketAssemblerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        "OK: profitability evidence packet assembled "
        f"(packet_id={result.packet['evidence_packet_id']}, candidate_id={result.packet['candidate_id']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
