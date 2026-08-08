"""hh_hl window_stability derived evidence (#4374).

Descriptive campaign-aggregate only. No classification thresholds.
Primary run trees remain immutable; this module only reads them.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash
from tools.arvp_vacation.hh_hl_campaign_summary import campaign_summary_path
from tools.arvp_vacation.sensitivity_campaign_state import (
    RUNS_DIRNAME,
    read_json,
    run_dir,
)

SCHEMA_VERSION = "cdb.hh_hl_window_stability.v1"
CALCULATION_VERSION = "hh_hl_window_stability_calc.v1"
OVERLAP_POLICY = "descriptive_non_iid"
DERIVED_FROM = "primary"
WINDOW_STABILITY_ARTIFACT_NAME = "window_stability.json"

RAW_METRICS_USED: tuple[str, ...] = (
    "net_pnl_quote",
    "expectancy_r",
    "max_drawdown_r",
    "closed_trades_total",
    "fees_total_quote",
    "gate_result.status",
)

SERIES_METRIC_KEYS: tuple[str, ...] = (
    "net_pnl_quote",
    "expectancy_r",
    "max_drawdown_r",
    "fees_total_quote",
    "closed_trades_total",
)

SIGN_METRIC_KEYS: tuple[str, ...] = ("net_pnl_quote", "expectancy_r")

BINDING_KEYS: tuple[str, ...] = (
    "campaign_id",
    "issue",
    "authorization_fingerprint",
    "execution_sha",
    "manifest_fingerprint",
    "run_plan_fingerprint",
    "dataset_selection_sha256",
    "dataset_content_fingerprint_digest",
    "physical_parameter_set_fingerprint",
    "campaign_summary_fingerprint",
    "source_run_count",
)


class HhHlWindowStabilityError(ValueError):
    """Fail-closed window_stability build/validate error."""

    def __init__(self, reason_code: str, detail: str = "") -> None:
        self.reason_code = reason_code
        super().__init__(reason_code if not detail else f"{reason_code}: {detail}")


def _as_decimal(value: object, *, field: str, window_id: str) -> Decimal:
    if value is None or isinstance(value, bool):
        raise HhHlWindowStabilityError(
            "WINDOW_STABILITY_MISSING_REQUIRED_METRIC",
            f"{field}@{window_id}",
        )
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise HhHlWindowStabilityError(
            "WINDOW_STABILITY_INVALID_METRIC",
            f"{field}@{window_id}",
        ) from exc


def _as_int(value: object, *, field: str, window_id: str) -> int:
    if isinstance(value, bool) or value is None:
        raise HhHlWindowStabilityError(
            "WINDOW_STABILITY_MISSING_REQUIRED_METRIC",
            f"{field}@{window_id}",
        )
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except (TypeError, ValueError) as exc:
        raise HhHlWindowStabilityError(
            "WINDOW_STABILITY_INVALID_METRIC",
            f"{field}@{window_id}",
        ) from exc


def _to_float(value: Decimal) -> float:
    return float(value)


def _median(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return float(statistics.median(values))


def _quantile(values: Sequence[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    index = (len(ordered) - 1) * q
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return float(ordered[lower])
    weight = index - lower
    return float(ordered[lower] * (1 - weight) + ordered[upper] * weight)


def _series_stats(values: Sequence[float]) -> dict[str, Any]:
    if not values:
        return {
            "median": None,
            "minimum": None,
            "maximum": None,
            "q25": None,
            "q75": None,
            "n": 0,
        }
    return {
        "median": _median(values),
        "minimum": min(values),
        "maximum": max(values),
        "q25": _quantile(values, 0.25),
        "q75": _quantile(values, 0.75),
        "n": len(values),
    }


def _sign_shares(values: Sequence[float]) -> dict[str, Any]:
    n = len(values)
    if n == 0:
        return {
            "positive_share": None,
            "negative_share": None,
            "zero_share": None,
            "n_traded": 0,
        }
    positive = sum(1 for value in values if value > 0)
    negative = sum(1 for value in values if value < 0)
    zero = sum(1 for value in values if value == 0)
    return {
        "positive_share": positive / n,
        "negative_share": negative / n,
        "zero_share": zero / n,
        "n_traded": n,
    }


def _concentration(abs_pnls: Sequence[float]) -> dict[str, Any]:
    total = sum(abs_pnls)
    if total == 0:
        return {
            "top1_abs_pnl_share": None,
            "top3_abs_pnl_share": None,
            "denominator_zero": True,
        }
    ordered = sorted(abs_pnls, reverse=True)
    top1 = ordered[0] / total if ordered else 0.0
    top3 = sum(ordered[:3]) / total
    return {
        "top1_abs_pnl_share": top1,
        "top3_abs_pnl_share": top3,
        "denominator_zero": False,
    }


def _normalize_window_record(record: Mapping[str, Any]) -> dict[str, Any]:
    window_id = str(record.get("window_id") or "").strip()
    if not window_id:
        raise HhHlWindowStabilityError("WINDOW_STABILITY_MISSING_WINDOW_ID")

    payload = record.get("result") if isinstance(record.get("result"), Mapping) else record
    if not isinstance(payload, Mapping):
        raise HhHlWindowStabilityError(
            "WINDOW_STABILITY_MISSING_REQUIRED_METRIC",
            f"result@{window_id}",
        )

    gate = payload.get("gate_result")
    if not isinstance(gate, Mapping) or "status" not in gate:
        raise HhHlWindowStabilityError(
            "WINDOW_STABILITY_MISSING_REQUIRED_METRIC",
            f"gate_result.status@{window_id}",
        )

    closed = _as_int(
        payload.get("closed_trades_total"),
        field="closed_trades_total",
        window_id=window_id,
    )
    return {
        "window_id": window_id,
        "net_pnl_quote": _to_float(
            _as_decimal(payload.get("net_pnl_quote"), field="net_pnl_quote", window_id=window_id)
        ),
        "expectancy_r": _to_float(
            _as_decimal(payload.get("expectancy_r"), field="expectancy_r", window_id=window_id)
        ),
        "max_drawdown_r": _to_float(
            _as_decimal(
                payload.get("max_drawdown_r"),
                field="max_drawdown_r",
                window_id=window_id,
            )
        ),
        "fees_total_quote": _to_float(
            _as_decimal(
                payload.get("fees_total_quote"),
                field="fees_total_quote",
                window_id=window_id,
            )
        ),
        "closed_trades_total": closed,
        "gate_result_status": str(gate.get("status")),
    }


def _validate_bindings(bindings: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in BINDING_KEYS:
        if key not in bindings or bindings[key] in (None, ""):
            raise HhHlWindowStabilityError(
                "WINDOW_STABILITY_BINDING_MISSING",
                key,
            )
        out[key] = bindings[key]
    try:
        out["issue"] = int(out["issue"])
        out["source_run_count"] = int(out["source_run_count"])
    except (TypeError, ValueError) as exc:
        raise HhHlWindowStabilityError(
            "WINDOW_STABILITY_BINDING_INVALID",
            "issue_or_source_run_count",
        ) from exc
    if out["source_run_count"] < 1:
        raise HhHlWindowStabilityError(
            "WINDOW_STABILITY_BINDING_INVALID",
            "source_run_count",
        )
    return out


def build_window_stability(
    *,
    bindings: Mapping[str, Any],
    window_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build descriptive window_stability artifact from Pack-A window records."""
    bind = _validate_bindings(bindings)
    if not window_records:
        raise HhHlWindowStabilityError("WINDOW_STABILITY_EMPTY_WINDOWS")

    normalized = [_normalize_window_record(record) for record in window_records]
    window_ids = [row["window_id"] for row in normalized]
    if len(window_ids) != len(set(window_ids)):
        raise HhHlWindowStabilityError("WINDOW_STABILITY_DUPLICATE_WINDOW")

    expected_count = int(bind["source_run_count"])
    if len(window_ids) != expected_count:
        raise HhHlWindowStabilityError(
            "WINDOW_STABILITY_WINDOW_COUNT_MISMATCH",
            f"got={len(window_ids)} expected={expected_count}",
        )

    ordered = sorted(normalized, key=lambda row: row["window_id"])
    ordered_ids = [row["window_id"] for row in ordered]

    n_total = len(ordered)
    traded_rows = [row for row in ordered if int(row["closed_trades_total"]) > 0]
    n_traded = len(traded_rows)
    n_zero_trade = n_total - n_traded

    series: dict[str, Any] = {}
    for key in SERIES_METRIC_KEYS:
        series[key] = _series_stats([float(row[key]) for row in ordered])

    sign_shares = {
        key: _sign_shares([float(row[key]) for row in traded_rows])
        for key in SIGN_METRIC_KEYS
    }
    concentration = _concentration(
        [abs(float(row["net_pnl_quote"])) for row in ordered]
    )

    gate_hist: dict[str, int] = {}
    for row in ordered:
        status = str(row["gate_result_status"])
        gate_hist[status] = gate_hist.get(status, 0) + 1

    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "calculation_version": CALCULATION_VERSION,
        "campaign_id": str(bind["campaign_id"]),
        "issue": int(bind["issue"]),
        "authorization_fingerprint": str(bind["authorization_fingerprint"]),
        "execution_sha": str(bind["execution_sha"]),
        "manifest_fingerprint": str(bind["manifest_fingerprint"]),
        "run_plan_fingerprint": str(bind["run_plan_fingerprint"]),
        "dataset_selection_sha256": str(bind["dataset_selection_sha256"]),
        "dataset_content_fingerprint_digest": str(
            bind["dataset_content_fingerprint_digest"]
        ),
        "physical_parameter_set_fingerprint": str(
            bind["physical_parameter_set_fingerprint"]
        ),
        "campaign_summary_fingerprint": str(bind["campaign_summary_fingerprint"]),
        "source_run_count": expected_count,
        "window_ids": ordered_ids,
        "raw_metrics_used": list(RAW_METRICS_USED),
        "overlap_policy": OVERLAP_POLICY,
        "derived_from": DERIVED_FROM,
        "metrics": {
            "n_total": n_total,
            "n_traded": n_traded,
            "n_zero_trade": n_zero_trade,
            "series": series,
            "sign_shares": sign_shares,
            "concentration": concentration,
            "gate_status_histogram": dict(sorted(gate_hist.items())),
        },
    }
    return {
        **body,
        "evidence_fingerprint": canonical_hash(body),
    }


def validate_window_stability_artifact(artifact: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute fingerprint and enforce schema constants fail-closed."""
    if artifact.get("schema_version") != SCHEMA_VERSION:
        raise HhHlWindowStabilityError("WINDOW_STABILITY_SCHEMA_MISMATCH")
    if artifact.get("calculation_version") != CALCULATION_VERSION:
        raise HhHlWindowStabilityError("WINDOW_STABILITY_CALC_VERSION_MISMATCH")
    if artifact.get("overlap_policy") != OVERLAP_POLICY:
        raise HhHlWindowStabilityError("WINDOW_STABILITY_OVERLAP_POLICY_INVALID")
    if artifact.get("derived_from") != DERIVED_FROM:
        raise HhHlWindowStabilityError("WINDOW_STABILITY_DERIVED_FROM_INVALID")

    body = {k: v for k, v in artifact.items() if k != "evidence_fingerprint"}
    expected_fp = canonical_hash(body)
    actual_fp = str(artifact.get("evidence_fingerprint") or "")
    if actual_fp != expected_fp:
        raise HhHlWindowStabilityError(
            "WINDOW_STABILITY_FINGERPRINT_MISMATCH",
            f"got={actual_fp} expected={expected_fp}",
        )
    return dict(artifact)


def assert_bindings_match(
    artifact: Mapping[str, Any],
    *,
    expected_bindings: Mapping[str, Any],
) -> None:
    """Fail closed when artifact bindings diverge from expected campaign bind."""
    bind = _validate_bindings(expected_bindings)
    for key in BINDING_KEYS:
        left = artifact.get(key)
        right = bind[key]
        if key in {"issue", "source_run_count"}:
            if int(left) != int(right):
                raise HhHlWindowStabilityError(
                    "WINDOW_STABILITY_BINDING_MISMATCH",
                    key,
                )
        elif str(left) != str(right):
            raise HhHlWindowStabilityError(
                "WINDOW_STABILITY_BINDING_MISMATCH",
                key,
            )


def _extract_result_payload(raw: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = raw.get("result")
    if isinstance(nested, Mapping):
        return nested
    return raw


def load_window_records_from_primary_root(
    evidence_root: Path,
    *,
    expected_run_keys: Sequence[str],
) -> list[dict[str, Any]]:
    """Read Pack-A metrics from primary run result.json files (read-only)."""
    root = Path(evidence_root)
    if not root.is_dir():
        raise HhHlWindowStabilityError(
            "WINDOW_STABILITY_EVIDENCE_ROOT_MISSING",
            str(root),
        )

    keys = list(expected_run_keys)
    if len(keys) != len(set(keys)):
        raise HhHlWindowStabilityError("WINDOW_STABILITY_DUPLICATE_EXPECTED_KEY")

    records: list[dict[str, Any]] = []
    for run_key in keys:
        directory = run_dir(root, run_key)
        result_path = directory / "result.json"
        if not result_path.is_file():
            raise HhHlWindowStabilityError(
                "WINDOW_STABILITY_MISSING_WINDOW",
                run_key,
            )
        raw = read_json(result_path)
        if not isinstance(raw, Mapping):
            raise HhHlWindowStabilityError(
                "WINDOW_STABILITY_INVALID_RESULT",
                run_key,
            )
        payload = _extract_result_payload(raw)
        envelope_path = directory / "run_envelope.json"
        window_id = ""
        if envelope_path.is_file():
            envelope = read_json(envelope_path)
            if isinstance(envelope, Mapping):
                window_id = str(envelope.get("window_id") or "")
        if not window_id:
            # Fallback: last path segment of run_key (campaign|window|...).
            parts = str(run_key).split("|")
            window_id = parts[1] if len(parts) >= 2 else str(run_key)
        records.append(
            {
                "window_id": window_id,
                "run_key": run_key,
                "result": dict(payload),
            }
        )
    return records


def build_window_stability_from_primary_root(
    *,
    evidence_root: Path,
    bindings: Mapping[str, Any],
    expected_run_keys: Sequence[str],
) -> dict[str, Any]:
    """Build stability artifact from a bound primary evidence root (read-only)."""
    records = load_window_records_from_primary_root(
        evidence_root,
        expected_run_keys=expected_run_keys,
    )
    return build_window_stability(bindings=bindings, window_records=records)


def write_window_stability_artifact(
    evidence_root: Path,
    artifact: Mapping[str, Any],
) -> Path:
    """Write derived stability artifact beside campaign summary; never mutates runs/."""
    validated = validate_window_stability_artifact(artifact)
    root = Path(evidence_root)
    root.mkdir(parents=True, exist_ok=True)
    # Guard: refuse to write inside a runs/ leaf.
    if root.name == RUNS_DIRNAME:
        raise HhHlWindowStabilityError("WINDOW_STABILITY_REFUSE_WRITE_IN_RUNS")
    out = root / WINDOW_STABILITY_ARTIFACT_NAME
    # Atomic-ish write without touching run trees.
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(validated, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(out)
    return out


def _cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build/validate cdb.hh_hl_window_stability.v1 from primary evidence "
            "(read-only; no primary mutation)."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build_p = sub.add_parser("build", help="Build stability artifact from primary root")
    build_p.add_argument("--evidence-root", required=True, type=Path)
    build_p.add_argument("--bindings-json", required=True, type=Path)
    build_p.add_argument("--run-keys-json", required=True, type=Path)
    build_p.add_argument(
        "--write",
        action="store_true",
        help="Write window_stability.json under evidence-root",
    )

    validate_p = sub.add_parser("validate", help="Validate an existing artifact")
    validate_p.add_argument("--artifact", required=True, type=Path)

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "validate":
        raw = json.loads(Path(args.artifact).read_text(encoding="utf-8"))
        validated = validate_window_stability_artifact(raw)
        print(json.dumps({"ok": True, "evidence_fingerprint": validated["evidence_fingerprint"]}))
        return 0

    bindings = json.loads(Path(args.bindings_json).read_text(encoding="utf-8"))
    run_keys = json.loads(Path(args.run_keys_json).read_text(encoding="utf-8"))
    if not isinstance(run_keys, list):
        raise HhHlWindowStabilityError("WINDOW_STABILITY_RUN_KEYS_INVALID")
    artifact = build_window_stability_from_primary_root(
        evidence_root=Path(args.evidence_root),
        bindings=bindings,
        expected_run_keys=[str(k) for k in run_keys],
    )
    if args.write:
        path = write_window_stability_artifact(Path(args.evidence_root), artifact)
        # Ensure campaign summary presence is not required, but refuse if runs missing.
        _ = campaign_summary_path(Path(args.evidence_root))
        print(json.dumps({"ok": True, "path": str(path), **artifact}, sort_keys=True))
    else:
        print(json.dumps(artifact, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
