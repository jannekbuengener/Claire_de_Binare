"""Deterministic #4153 sensitivity campaign analyzer (post-reproduction).

Writes analysis artifacts under ``<evidence_root>/analysis/``.
Does not promote strategies. LR=NO-GO.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash
from core.utils.clock import utcnow as cdb_utcnow

from tools.arvp_vacation.sensitivity_campaign_analyzer_contract import (
    ANALYZER_CONTRACT_VERSION,
    ALLOWED_RESULT_FIELDS,
    SensitivityAnalyzerContractError,
    assert_results_bindings,
    classify_overlap_slots,
    effect_partition,
    ranking_weights_for_slots,
)
from tools.arvp_vacation.sensitivity_campaign_primary_adoption import (
    load_primary_evidence_inventory,
)
from tools.arvp_vacation.sensitivity_campaign_state import (
    CAMPAIGN_PHASE_COMPLETED,
    read_campaign_phase,
    read_json,
    reproduction_comparison_path,
    result_path,
    run_envelope_path,
)

ANALYSIS_DIRNAME = "analysis"
CLASSIFICATIONS = frozenset({"PROMISING", "INCONCLUSIVE", "REJECTED", "BLOCKED"})


class SensitivityAnalyzerError(ValueError):
    def __init__(self, reason_code: str, detail: str = "") -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {detail}" if detail else reason_code)


def _utcnow_iso() -> str:
    now = cdb_utcnow()
    return now.astimezone(now.tzinfo).isoformat().replace("+00:00", "Z")


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return sum(values) / float(len(values))


def load_primary_result_rows(
    evidence_root: Path, *, expected_run_keys: Sequence[str]
) -> list[dict[str, Any]]:
    root = Path(evidence_root)
    rows: list[dict[str, Any]] = []
    for run_key in expected_run_keys:
        rpath = result_path(root, run_key)
        epath = run_envelope_path(root, run_key)
        if not rpath.exists() or not epath.exists():
            raise SensitivityAnalyzerError("ANALYZER_PRIMARY_RESULT_MISSING", run_key)
        result_body = read_json(rpath)
        env_body = read_json(epath)
        metrics = dict(result_body.get("result") or {})
        envelope = dict(env_body.get("envelope") or {})
        rows.append(
            {
                "run_key": run_key,
                "manifest_fingerprint": result_body.get("manifest_fingerprint"),
                "run_plan_fingerprint": result_body.get("run_plan_fingerprint"),
                "authorization_fingerprint": result_body.get(
                    "authorization_fingerprint"
                ),
                "result_fingerprint": result_body.get("result_fingerprint"),
                "slot_id": envelope.get("slot_id") or envelope.get("label"),
                "window_id": envelope.get("window_id"),
                "phase": envelope.get("phase"),
                "label": envelope.get("label"),
                "physical_parameter_set_fingerprint": envelope.get(
                    "physical_parameter_set_fingerprint"
                ),
                "metrics": metrics,
            }
        )
    return rows


def load_reproduction_summary(evidence_root: Path) -> dict[str, Any]:
    root = Path(evidence_root)
    comparisons: list[dict[str, Any]] = []
    for path in sorted(root.glob("runs/*/reproduction/*/comparison.json")):
        body = read_json(path)
        comparisons.append(
            {
                "path": str(path.relative_to(root)).replace("\\", "/"),
                "comparison_fingerprint": (body.get("comparison") or {}).get(
                    "comparison_fingerprint"
                )
                or body.get("comparison_fingerprint"),
                "verdict": (body.get("comparison") or {}).get("verdict")
                or body.get("verdict")
                or body.get("status"),
                "mismatched_fields": (body.get("comparison") or {}).get(
                    "mismatched_fields"
                )
                or body.get("mismatched_fields")
                or [],
                "run_key": path.parts[-4] if len(path.parts) >= 4 else None,
            }
        )
    mismatch_count = sum(1 for c in comparisons if c.get("mismatched_fields"))
    fps = sorted(
        str(c["comparison_fingerprint"])
        for c in comparisons
        if c.get("comparison_fingerprint")
    )
    return {
        "comparison_count": len(comparisons),
        "mismatch_count": mismatch_count,
        "comparisons": comparisons,
        "reproduction_comparison_set_fingerprint": canonical_hash({"fps": fps}),
        "reproduction_pass": len(comparisons) >= 1 and mismatch_count == 0,
    }


def _aggregate_slot_metrics(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    by_slot: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        sid = str(row.get("slot_id") or "")
        if not sid:
            raise SensitivityAnalyzerError("ANALYZER_ROW_MISSING_SLOT_ID")
        by_slot.setdefault(sid, []).append(row)

    out: dict[str, dict[str, Any]] = {}
    metric_keys = (
        "trade_count",
        "turnover",
        "fees",
        "spread",
        "slippage",
        "gross_pnl",
        "net_pnl",
        "profit_factor",
        "expectancy",
        "drawdown",
    )
    for sid, items in sorted(by_slot.items()):
        agg: dict[str, Any] = {
            "slot_id": sid,
            "window_count": len(items),
            "phase": items[0].get("phase"),
            "label": items[0].get("label"),
            "physical_parameter_set_fingerprint": items[0].get(
                "physical_parameter_set_fingerprint"
            ),
        }
        for key in metric_keys:
            vals = [
                v
                for v in (_to_float((i.get("metrics") or {}).get(key)) for i in items)
                if v is not None
            ]
            agg[key] = _mean(vals)
        flags = [
            str((i.get("metrics") or {}).get("overfitting_risk_flag") or "")
            for i in items
        ]
        agg["overfitting_flag_rate"] = (
            sum(1 for f in flags if f and f.upper() not in {"", "FALSE", "0", "NONE"})
            / float(len(flags))
            if flags
            else 0.0
        )
        # Window stability: stdev of net_pnl across windows (population).
        nets = [
            v
            for v in (_to_float((i.get("metrics") or {}).get("net_pnl")) for i in items)
            if v is not None
        ]
        if len(nets) >= 2:
            mu = sum(nets) / len(nets)
            var = sum((x - mu) ** 2 for x in nets) / len(nets)
            agg["net_pnl_window_stdev"] = var**0.5
        else:
            agg["net_pnl_window_stdev"] = None
        out[sid] = agg
    return out


def _classify(
    *,
    campaign_phase: str,
    reproduction: Mapping[str, Any],
    main_effects: Mapping[str, Any],
    interaction_effects: Mapping[str, Any],
) -> dict[str, Any]:
    if campaign_phase != CAMPAIGN_PHASE_COMPLETED:
        return {
            "classification": "BLOCKED",
            "reasons": [f"campaign_phase={campaign_phase}"],
        }
    if not reproduction.get("reproduction_pass"):
        return {
            "classification": "BLOCKED",
            "reasons": ["reproduction_not_pass"],
        }

    ranking = list(main_effects.get("weighted_ranking") or [])
    if not ranking:
        return {
            "classification": "INCONCLUSIVE",
            "reasons": ["empty_main_effect_ranking"],
        }

    top = ranking[0]
    top_net = _to_float(top.get("net_pnl"))
    top_exp = _to_float(top.get("expectancy"))
    top_dd = _to_float(top.get("drawdown"))
    top_of = _to_float(top.get("overfitting_flag_rate")) or 0.0
    top_stdev = _to_float(top.get("net_pnl_window_stdev"))

    reasons: list[str] = []
    if top_net is not None and top_net < 0 and (top_exp is None or top_exp <= 0):
        reasons.append("top_main_effect_negative_net_and_expectancy")
        return {"classification": "REJECTED", "reasons": reasons}
    if top_of >= 0.5:
        reasons.append("high_overfitting_flag_rate")
        return {"classification": "REJECTED", "reasons": reasons}

    ix_rank = list(interaction_effects.get("weighted_ranking") or [])
    ix_positive = 0
    for row in ix_rank[:5]:
        n = _to_float(row.get("net_pnl"))
        if n is not None and n > 0:
            ix_positive += 1

    promising = (
        top_net is not None
        and top_net > 0
        and top_exp is not None
        and top_exp > 0
        and top_of < 0.25
        and (top_stdev is None or (top_net != 0 and abs(top_stdev / top_net) < 2.0))
        and (top_dd is None or top_dd >= -0.5)
    )
    if promising:
        reasons.append("top_main_effect_positive_stable")
        if ix_positive == 0:
            reasons.append("interaction_effects_not_confirming")
            return {"classification": "INCONCLUSIVE", "reasons": reasons}
        reasons.append("interaction_effects_partially_confirming")
        return {"classification": "PROMISING", "reasons": reasons}

    reasons.append("insufficient_signal_for_promising_or_rejected")
    return {"classification": "INCONCLUSIVE", "reasons": reasons}


def analyze_campaign(
    *,
    evidence_root: Path,
    expected_run_keys: Sequence[str],
    manifest_fingerprint: str,
    run_plan_fingerprint: str,
    authorization_fingerprint: str,
) -> dict[str, Any]:
    root = Path(evidence_root)
    phase = read_campaign_phase(root)
    inventory = load_primary_evidence_inventory(root)
    rows = load_primary_result_rows(root, expected_run_keys=expected_run_keys)
    assert_results_bindings(
        results=rows,
        manifest_fingerprint=manifest_fingerprint,
        run_plan_fingerprint=run_plan_fingerprint,
        authorization_fingerprint=authorization_fingerprint,
        expected_run_keys=expected_run_keys,
    )

    overlap = classify_overlap_slots()
    parts = effect_partition(overlap["slots"])
    weights = ranking_weights_for_slots(overlap["slots"])
    slot_agg = _aggregate_slot_metrics(rows)
    reproduction = load_reproduction_summary(root)

    def _rank(slot_ids: Sequence[str]) -> list[dict[str, Any]]:
        ranked: list[dict[str, Any]] = []
        for sid in slot_ids:
            row = dict(slot_agg.get(sid) or {"slot_id": sid})
            row["ranking_weight"] = float(weights.get(sid) or 0.0)
            ranked.append(row)
        ranked.sort(
            key=lambda r: (
                -(_to_float(r.get("net_pnl")) or float("-inf")),
                -(_to_float(r.get("expectancy")) or float("-inf")),
                str(r.get("slot_id")),
            )
        )
        return ranked

    main_effects = {
        "slot_ids": list(parts["main_effect_slot_ids"]),
        "weighted_ranking": _rank(parts["main_effect_slot_ids"]),
        "rules": overlap["rules"],
    }
    interaction_effects = {
        "slot_ids": list(parts["interaction_effect_slot_ids"]),
        "weighted_ranking": _rank(parts["interaction_effect_slot_ids"]),
        "rules": overlap["rules"],
    }

    classification = _classify(
        campaign_phase=phase,
        reproduction=reproduction,
        main_effects=main_effects,
        interaction_effects=interaction_effects,
    )
    if classification["classification"] not in CLASSIFICATIONS:
        raise SensitivityAnalyzerError("ANALYZER_INVALID_CLASSIFICATION")

    analysis_dir = root / ANALYSIS_DIRNAME
    analysis_dir.mkdir(parents=True, exist_ok=True)

    input_inventory = {
        "schema_version": "cdb.sensitivity_campaign_analysis_input.v1",
        "campaign_phase": phase,
        "primary_inventory_fingerprint": inventory.get("inventory_fingerprint"),
        "run_key_digest": inventory.get("run_key_digest"),
        "expected_run_count": len(expected_run_keys),
        "observed_run_count": len(rows),
        "manifest_fingerprint": manifest_fingerprint,
        "run_plan_fingerprint": run_plan_fingerprint,
        "authorization_fingerprint": authorization_fingerprint,
        "analyzer_contract_version": ANALYZER_CONTRACT_VERSION,
        "matrix_slots": overlap["matrix_slots"],
        "physical_parameter_sets": overlap["physical_parameter_sets"],
        "overlaps": overlap["overlaps"],
        "allowed_result_fields": list(ALLOWED_RESULT_FIELDS),
    }
    input_inventory["input_inventory_fingerprint"] = canonical_hash(
        {k: v for k, v in input_inventory.items() if k != "input_inventory_fingerprint"}
    )

    classification_report = {
        "schema_version": "cdb.sensitivity_campaign_classification.v1",
        "classification": classification["classification"],
        "reasons": classification["reasons"],
        "no_automatic_promotion": True,
        "lr_status": "NO-GO",
    }
    classification_report["classification_fingerprint"] = canonical_hash(
        {
            k: v
            for k, v in classification_report.items()
            if k != "classification_fingerprint"
        }
    )

    envelope = {
        "schema_version": "cdb.sensitivity_campaign_analysis_envelope.v1",
        "analyzer_contract_version": ANALYZER_CONTRACT_VERSION,
        "campaign_phase": phase,
        "classification": classification["classification"],
        "input_inventory_fingerprint": input_inventory["input_inventory_fingerprint"],
        "classification_fingerprint": classification_report[
            "classification_fingerprint"
        ],
        "reproduction_comparison_set_fingerprint": reproduction[
            "reproduction_comparison_set_fingerprint"
        ],
        "main_effects_fingerprint": canonical_hash(main_effects),
        "interaction_effects_fingerprint": canonical_hash(interaction_effects),
        "created_at_utc": _utcnow_iso(),
        "lr_status": "NO-GO",
        "writes_primary_results": False,
    }
    envelope["analysis_envelope_fingerprint"] = canonical_hash(
        {
            k: v
            for k, v in envelope.items()
            if k not in {"created_at_utc", "analysis_envelope_fingerprint"}
        }
    )

    artifacts = {
        "analysis_envelope.json": envelope,
        "campaign_input_inventory.json": input_inventory,
        "main_effects.json": main_effects,
        "interaction_effects.json": interaction_effects,
        "classification_report.json": classification_report,
        "reproduction_summary.json": reproduction,
    }
    for name, payload in artifacts.items():
        path = analysis_dir / name
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    report_md = analysis_dir / "analysis_report.md"
    top_main = (main_effects["weighted_ranking"] or [{}])[0]
    report_md.write_text(
        "\n".join(
            [
                "# #4153 Sensitivity Campaign Analysis Report",
                "",
                f"- Classification: `{classification['classification']}`",
                f"- Campaign phase: `{phase}`",
                f"- Matrix: {overlap['matrix_slots']} slots / "
                f"{overlap['physical_parameter_sets']} physical sets / "
                f"{overlap['overlaps']} overlaps",
                f"- Reproduction comparisons: {reproduction['comparison_count']} "
                f"(mismatches={reproduction['mismatch_count']})",
                f"- Top main-effect slot: `{top_main.get('slot_id')}` "
                f"net_pnl={top_main.get('net_pnl')}",
                f"- Reasons: {', '.join(classification['reasons'])}",
                "- Automatic promotion: **forbidden**",
                "- LR status: **NO-GO**",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return {
        "command": "analyze",
        "status": "ANALYZED",
        "classification": classification["classification"],
        "campaign_phase": phase,
        "analysis_dir": str(analysis_dir),
        "analysis_envelope_fingerprint": envelope["analysis_envelope_fingerprint"],
        "lr_status": "NO-GO",
    }
