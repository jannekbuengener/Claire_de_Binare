"""Physical dataset-proof tests for hh_hl campaign prep (#4375).

test_id: tc_hh_hl_dataset_proof_001
test_type: Schutz-Test
issue_ref: #4374
live_relevant: false
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.arvp_vacation.hh_hl_campaign_dataset import (
    DATASET_STATUS_LOCAL_PROOF_REQUIRED,
    DATASET_STATUS_PASS,
    HhHlDatasetBindingError,
    build_dataset_binding_receipt,
    load_pass_receipt,
    prove_local_dataset,
    validate_pass_receipt,
    write_receipt_atomic,
)
from tools.arvp_vacation.hh_hl_campaign_manifest import build_hh_hl_draft_manifest
from tools.arvp_vacation.hh_hl_campaign_plan import dry_plan, main
from tools.arvp_vacation.hh_hl_campaign_run_plan import build_hh_hl_run_plan
from tools.market_data.development_window_selector import (
    LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS,
)


def _write_window(bank: Path, window_id: str, *, symbol: str = "BTCUSDT") -> None:
    window_dir = bank / window_id
    window_dir.mkdir(parents=True, exist_ok=True)
    start = 1_500_000_000_000
    end = start + 60_000
    candles = [
        {
            "ts_ms": start,
            "open": 1.0,
            "high": 2.0,
            "low": 0.5,
            "close": 1.5,
            "volume": 10.0,
            "symbol": symbol,
        },
        {
            "ts_ms": end,
            "open": 1.5,
            "high": 2.5,
            "low": 1.0,
            "close": 2.0,
            "volume": 11.0,
            "symbol": symbol,
        },
    ]
    (window_dir / "candles.jsonl").write_text(
        "\n".join(json.dumps(row) for row in candles) + "\n",
        encoding="utf-8",
    )
    spec = {
        "window_id": window_id,
        "dataset_id": window_id,
        "symbol": symbol,
        "timeframe": "1m",
        "start_ts_ms": start,
        "end_ts_ms": end,
        "schema_version": "dataset_spec.v2",
        "source": "file",
    }
    (window_dir / "dataset_spec.json").write_text(
        json.dumps(spec, indent=2) + "\n", encoding="utf-8"
    )


def _mini_bank(tmp_path: Path) -> Path:
    bank = tmp_path / "window_bank" / "binance" / "spot" / "BTCUSDT" / "1m"
    for wid in LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS:
        _write_window(bank, wid)
    return bank


@pytest.mark.unit
def test_prove_dataset_cli_requires_dataset_root():
    with pytest.raises(SystemExit):
        main(["prove-dataset"])


@pytest.mark.unit
def test_prove_dataset_cli_rejects_unknown_arg(tmp_path: Path):
    with pytest.raises(SystemExit):
        main(["prove-dataset", "--dataset-root", str(tmp_path), "--nope", "x"])


@pytest.mark.unit
def test_prove_dataset_missing_and_file_root(tmp_path: Path):
    missing = tmp_path / "nope"
    assert main(["prove-dataset", "--dataset-root", str(missing)]) == 2
    file_root = tmp_path / "file.txt"
    file_root.write_text("x", encoding="utf-8")
    assert main(["prove-dataset", "--dataset-root", str(file_root)]) == 2


@pytest.mark.unit
def test_prove_local_dataset_pass_and_repeatable(tmp_path: Path):
    bank = _mini_bank(tmp_path)
    market_data = tmp_path  # parent of window_bank
    a = prove_local_dataset(market_data)
    b = prove_local_dataset(market_data)
    assert a.quality_gate_status == DATASET_STATUS_PASS
    assert a.local_proof_required is False
    assert a.window_count == 39
    assert a.content_fingerprint_digest == b.content_fingerprint_digest
    assert a.per_window_content_fingerprints is not None
    assert len(a.per_window_content_fingerprints) == 39
    blob = json.dumps(a.as_dict())
    assert ":\\" not in blob
    assert "C:" not in blob


@pytest.mark.unit
def test_prove_missing_foreign_duplicate_and_symbol(tmp_path: Path):
    bank = _mini_bank(tmp_path)
    # missing
    (bank / LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS[0]).rename(
        tmp_path / "removed_window"
    )
    with pytest.raises(HhHlDatasetBindingError, match="MISSING_WINDOWS"):
        prove_local_dataset(tmp_path)
    # restore + foreign not required to block (extra months allowed in bank)
    (tmp_path / "removed_window").rename(
        bank / LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS[0]
    )
    _write_window(bank, "binance_1m_month_2099_01")  # foreign extra ok
    prove_local_dataset(tmp_path)  # still PASS

    # bad symbol
    _write_window(bank, LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS[1], symbol="ETHUSDT")
    with pytest.raises(
        HhHlDatasetBindingError, match="WINDOW_SPEC_INVALID|SYMBOL_MISMATCH"
    ):
        prove_local_dataset(tmp_path)


@pytest.mark.unit
def test_caller_supplied_hashes_never_pass(tmp_path: Path):
    receipt = build_dataset_binding_receipt(
        content_fingerprints_by_window={
            w: "a" * 64 for w in LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS
        },
        dataset_root=tmp_path,
    )
    assert receipt.local_proof_required is True
    assert receipt.quality_gate_status == DATASET_STATUS_LOCAL_PROOF_REQUIRED


@pytest.mark.unit
def test_receipt_validation_and_plan_binding(tmp_path: Path):
    bank_parent = tmp_path
    _mini_bank(bank_parent)
    receipt = prove_local_dataset(bank_parent)
    out = tmp_path / "receipt.json"
    write_receipt_atomic(receipt, out)
    loaded = load_pass_receipt(out)

    # tamper digest
    bad = loaded.as_dict()
    bad["content_fingerprint_digest"] = "0" * 64
    with pytest.raises(
        HhHlDatasetBindingError, match="RECEIPT_CONTENT_DIGEST_MISMATCH"
    ):
        validate_pass_receipt(bad)

    plan_hold = dry_plan(repo_root=Path(__file__).resolve().parents[3])
    assert plan_hold["dataset_binding_status"] == DATASET_STATUS_LOCAL_PROOF_REQUIRED
    assert plan_hold["local_proof_required"] is True

    plan_pass = dry_plan(
        repo_root=Path(__file__).resolve().parents[3],
        dataset_receipt_path=out,
    )
    assert plan_pass["writes"] is False
    assert plan_pass["replays"] is False
    assert plan_pass["campaign_execution_authorized"] is False
    assert plan_pass["execution_sha"] is None
    assert plan_pass["dataset_binding_status"] == DATASET_STATUS_PASS
    assert plan_pass["local_proof_required"] is False
    assert plan_pass["grid_status"] == "HOLD_CAMPAIGN_GRID_OWNER_RATIFICATION_REQUIRED"
    assert (
        DATASET_STATUS_LOCAL_PROOF_REQUIRED not in plan_pass["non_executable_reasons"]
    )
    assert (
        "HOLD_CAMPAIGN_GRID_OWNER_RATIFICATION_REQUIRED"
        in plan_pass["non_executable_reasons"]
    )

    # Digests change when receipt is bound.
    assert plan_pass["manifest_fingerprint"] != plan_hold["manifest_fingerprint"]
    assert plan_pass["run_plan_fingerprint"] != plan_hold["run_plan_fingerprint"]

    manifest = build_hh_hl_draft_manifest(dataset_receipt=loaded)
    plan = build_hh_hl_run_plan(
        manifest=manifest, planning_sha="a" * 40, dataset_receipt=loaded
    )
    assert plan.dataset_status == DATASET_STATUS_PASS
