"""Build the canonical #4153 executable sensitivity campaign manifest."""

from __future__ import annotations

import json
from pathlib import Path

from core.replay.canonical_json import canonical_hash
from core.replay.effective_config_snapshot import build_effective_config_snapshot
from tools.arvp_vacation.batch_a_gate_common import (
    STAGE_A_GATE_CONTRACT_PATH,
    STAGE_B_CONFIRMATION_CONTRACT_PATH,
    compute_gate_contract_sha256,
    load_json_contract,
)
from tools.arvp_vacation.sensitivity_campaign_grid import (
    EXPECTED_RUN_COUNT,
    EXPECTED_UNIQUE_VARIANTS,
    EXPANSION_MODE,
    MAX_RUN_COUNT,
    OWNER_RATIFICATION_COMMENT_ID,
    OWNER_RATIFICATION_URL,
    STRATEGY_ID,
    baseline_param_set,
    interaction_groups_for_manifest,
    parameter_families_for_manifest,
    parameter_grid_for_manifest,
)
from tools.arvp_vacation.sensitivity_experiment_manifest import attach_fingerprint
from tools.market_data.development_window_selector import (
    LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS,
    LOCKED_DEVELOPMENT_SELECTION_SHA256,
)
from tools.validate_parameter_control_policy import (
    POLICY_PATH,
    compute_canonical_json_sha256,
    compute_register_fingerprint,
)

CORRECTNESS = "301bc757be7cb4162db6db114a5c445f2aca392f"
BANK_CANDIDATES = (
    Path(
        "D:/Dev/Workspaces/Repos/Claire_de_Binare/artifacts/market_data/"
        "window_bank/binance/spot/BTCUSDT/1m/window_bank_manifest.json"
    ),
    Path(
        "artifacts/market_data/window_bank/binance/spot/BTCUSDT/1m/window_bank_manifest.json"
    ),
)


def main() -> int:
    bank_path = next(p for p in BANK_CANDIDATES if p.exists())
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    rows = bank.get("windows") or bank.get("entries") or []
    if isinstance(rows, dict):
        rows = list(rows.values())
    by_id = {(r.get("window_id") or r.get("id")): r for r in rows}

    window_ids = list(LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS)
    bindings: list[dict] = []
    content_fps: list[str] = []
    for wid in window_ids:
        row = by_id[wid]
        cfp = row.get("dataset_fingerprint") or row.get("content_fingerprint")
        if not cfp or len(str(cfp)) != 64:
            raise SystemExit(f"missing content fingerprint for {wid}")
        content_fps.append(str(cfp))
        binding = {
            "window_id": wid,
            "symbol": "BTCUSDT",
            "timeframe": "1m",
            "start_ts_ms": int(row["start_ts_ms"]),
            "end_ts_ms": int(row["end_ts_ms"]),
            "content_fingerprint": str(cfp),
            "purpose": "development",
            "overlap_class": "monthly",
            "quality_verdict": str(row.get("quality_verdict") or "UNKNOWN"),
        }
        candle_count = int(row.get("candle_count") or 0)
        if candle_count > 0:
            binding["candle_count"] = candle_count
        bindings.append(binding)

    request_fp = canonical_hash(
        {
            "selection_sha256": LOCKED_DEVELOPMENT_SELECTION_SHA256,
            "window_ids": window_ids,
            "window_bank_identity": "binance/spot/BTCUSDT/1m",
        }
    )
    content_fp = canonical_hash({"window_content_fingerprints": content_fps})
    if request_fp == content_fp:
        raise SystemExit("request/content fingerprint collision")

    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    register_fp = compute_register_fingerprint(policy)
    canonical_sha = compute_canonical_json_sha256(POLICY_PATH)
    efc = build_effective_config_snapshot(Path("."))["snapshot_fingerprint"]
    stage_a = compute_gate_contract_sha256(
        load_json_contract(STAGE_A_GATE_CONTRACT_PATH)
    )
    stage_b = compute_gate_contract_sha256(
        load_json_contract(STAGE_B_CONFIRMATION_CONTRACT_PATH)
    )
    baseline_params = baseline_param_set()

    manifest = {
        "schema_version": "cdb.sensitivity_experiment_manifest.v1.1",
        "campaign_id": "arvp-sensitivity-4153-v1",
        "campaign_version": "4153.v1",
        "issue_ref": "#4153",
        "parent_issue_ref": "#4147",
        "correctness_baseline_sha": CORRECTNESS,
        "source_commit": CORRECTNESS,
        "baseline": {
            "strategy_id": STRATEGY_ID,
            "scenario_id": "baseline",
            "label": "owner-ratified-pb1-baseline",
            "notes": "Owner Grid Ratification comment 5175526900; replay-only.",
            "parameters": {
                "entry_lookback_minutes": baseline_params["entry_lookback_minutes"],
                "exit_lookback_minutes": baseline_params["exit_lookback_minutes"],
                "breakout_buffer": baseline_params["breakout_buffer"],
                "min_minutes_between_entries": baseline_params[
                    "min_minutes_between_entries"
                ],
            },
        },
        "strategies": [STRATEGY_ID],
        "parameter_families": parameter_families_for_manifest(),
        "parameter_grid": parameter_grid_for_manifest(),
        "design": {
            "one_factor_at_a_time": True,
            "interaction_groups": interaction_groups_for_manifest(),
        },
        "expansion": {
            "mode": EXPANSION_MODE,
            "unique_variant_count": EXPECTED_UNIQUE_VARIANTS,
            "expected_run_count": EXPECTED_RUN_COUNT,
            "max_run_count": MAX_RUN_COUNT,
            "window_count": 39,
            "strategy_count": 1,
            "formula": (
                "window_count × strategy_count × unique_variant_count = "
                "39 × 1 × 21 = 819"
            ),
            "duplicate_policy": (
                "OFAT skips baseline-equivalent values; interaction combos are "
                "not deduplicated against OFAT (phase-distinguished matrix slots)"
            ),
        },
        "run_key_contract": {
            "algorithm": "sha256",
            "formula": (
                "sha256(campaign_id|window_id|strategy_id|"
                "canonical_json(full_param_set)|scenario_id|phase|label)"
            ),
        },
        "development_windows": {
            "window_count": 39,
            "window_ids": window_ids,
            "selection_sha256": LOCKED_DEVELOPMENT_SELECTION_SHA256,
            "purpose": "development",
            "window_bank_identity": "binance/spot/BTCUSDT/1m",
            "symbol": "BTCUSDT",
            "timeframe": "1m",
            "warmup_policy": "primary_breakout_v1_max_lookback_minutes",
        },
        "window_bindings": bindings,
        "dataset_identity": {
            "request_fingerprint": request_fp,
            "content_fingerprint": content_fp,
            "identity_schema_version": "cdb.dataset_content_identity.v1",
            "dataset_ref": "binance_window_bank:locked_batch_a_development_39",
        },
        "effective_config_snapshot_fingerprint": efc,
        "parameter_control": {
            "policy_schema_version": "cdb.parameter_control_policy.register.v1",
            "register_fingerprint": register_fp,
            "canonical_json_sha256": canonical_sha,
        },
        "execution_economics_contract_version": "execution_economics_gross_to_net.v1",
        "frozen_boundaries": {
            "stage_a_gate_contract_sha256": stage_a,
            "stage_b_confirmation_contract_sha256": stage_b,
            "stage_a_b_oos_stress_gates": "frozen",
            "risk_and_live_boundaries": "frozen",
        },
        "seed_rules": {
            "deterministic": True,
            "seed_namespace": "cdb.sensitivity.4153.v1",
            "seed_formula": "sha256(campaign_id|window_id|variant_id)",
        },
        "allowed_result_fields": [
            "gate_reason",
            "regime_distribution",
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
            "main_effect",
            "interaction_effect",
            "overfitting_risk_flag",
        ],
        "holdout_denylist": {
            "excluded_purposes": ["validation", "out_of_sample", "stress"],
            "excluded_overlap_classes": ["quarterly", "yearly"],
        },
        "explicit_bans": {
            "promotion": True,
            "paper": True,
            "live": True,
            "echtgeld": True,
            "orders": True,
            "exchange_execution": True,
            "testnet_orders": True,
            "balance_usage": True,
            "position_mutation": True,
            "risk_limit_mutation": True,
            "kill_switch_mutation": True,
            "stop_loss_mutation": True,
            "stage_b": True,
            "oos": True,
            "stress": True,
            "holdout": True,
            "campaign_execution_auto_start": True,
            "campaign_execution": True,
        },
        "execution_mode": "replay_only",
        "output_contract": {
            "evidence_namespace": "artifacts/arvp_sensitivity/4153",
            "artifact_root_template": "artifacts/arvp_sensitivity/4153/{campaign_id}",
            "notes": (
                "Namespace reserved for a future Owner Campaign-GO session; "
                "this slice does not create run artifacts."
            ),
        },
        "owner_ratification": {
            "issue_comment_id": OWNER_RATIFICATION_COMMENT_ID,
            "url": OWNER_RATIFICATION_URL,
            "status": "DONE_4153_PARAMETER_GRID_RATIFIED",
            "correctness_baseline_sha": CORRECTNESS,
        },
        "lr_status": "NO-GO",
        "executable": True,
    }

    manifest = attach_fingerprint(manifest)
    out = Path("config/arvp/sensitivity_campaign_4153_v1.json")
    out.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {out}")
    print(f"fingerprint={manifest['manifest_fingerprint']}")
    print(f"efc={efc}")
    print(f"register={register_fp}")
    print(f"bindings={len(bindings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
