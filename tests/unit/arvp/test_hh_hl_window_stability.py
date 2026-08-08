"""Unit tests for hh_hl window_stability derived evidence (#4374).

test_id: tc_hh_hl_window_stability_001
test_type: Bauteil-Test / Schutz-Test
cdb_area: arvp_campaign
issue_ref: #4374
live_relevant: false
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tools.arvp_vacation.hh_hl_window_stability import (
    SCHEMA_VERSION,
    HhHlWindowStabilityError,
    assert_bindings_match,
    build_window_stability,
    validate_window_stability_artifact,
    write_window_stability_artifact,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = PROJECT_ROOT / "docs" / "contracts" / "cdb_hh_hl_window_stability.v1.schema.json"


def _fp(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _bindings(**overrides):
    base = {
        "campaign_id": "arvp-hh-hl-continuation-4374-prep-v1",
        "issue": 4374,
        "authorization_fingerprint": _fp("auth"),
        "execution_sha": "79b150d452a6bebddc5a8f1b0db39c77ebbfe1c3",
        "manifest_fingerprint": _fp("manifest"),
        "run_plan_fingerprint": _fp("run_plan"),
        "dataset_selection_sha256": _fp("dataset_sel"),
        "dataset_content_fingerprint_digest": _fp("dataset_content"),
        "physical_parameter_set_fingerprint": _fp("params"),
        "campaign_summary_fingerprint": _fp("summary"),
        "source_run_count": 3,
    }
    base.update(overrides)
    return base


def _window(
    window_id: str,
    *,
    net_pnl: float,
    expectancy: float,
    drawdown: float = 0.5,
    fees: float = 10.0,
    trades: int = 10,
    gate: str = "NOT_RANKING_READY",
):
    return {
        "window_id": window_id,
        "result": {
            "net_pnl_quote": net_pnl,
            "expectancy_r": expectancy,
            "max_drawdown_r": drawdown,
            "fees_total_quote": fees,
            "closed_trades_total": trades,
            "gate_result": {"status": gate},
        },
    }


def _three_windows(**overrides_by_id):
    defaults = {
        "w_a": dict(net_pnl=-100.0, expectancy=-0.01, trades=10),
        "w_b": dict(net_pnl=-200.0, expectancy=-0.02, trades=20),
        "w_c": dict(net_pnl=-50.0, expectancy=-0.005, trades=5),
    }
    defaults.update(overrides_by_id)
    return [_window(wid, **kwargs) for wid, kwargs in defaults.items()]


@pytest.fixture(scope="module")
def schema_validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


@pytest.mark.unit
def test_identical_inputs_identical_fingerprint(schema_validator):
    bindings = _bindings()
    records = _three_windows()
    a = build_window_stability(bindings=bindings, window_records=records)
    b = build_window_stability(bindings=bindings, window_records=copy.deepcopy(records))
    assert a["evidence_fingerprint"] == b["evidence_fingerprint"]
    assert a["schema_version"] == SCHEMA_VERSION
    schema_validator.validate(a)
    validate_window_stability_artifact(a)


@pytest.mark.unit
def test_shuffled_window_order_same_fingerprint():
    bindings = _bindings()
    records = _three_windows()
    shuffled = [records[2], records[0], records[1]]
    a = build_window_stability(bindings=bindings, window_records=records)
    b = build_window_stability(bindings=bindings, window_records=shuffled)
    assert a["evidence_fingerprint"] == b["evidence_fingerprint"]
    assert a["window_ids"] == ["w_a", "w_b", "w_c"]


@pytest.mark.unit
def test_missing_window_count_fail_closed():
    bindings = _bindings(source_run_count=3)
    records = _three_windows()[:2]
    with pytest.raises(HhHlWindowStabilityError) as exc:
        build_window_stability(bindings=bindings, window_records=records)
    assert exc.value.reason_code == "WINDOW_STABILITY_WINDOW_COUNT_MISMATCH"


@pytest.mark.unit
def test_duplicate_window_fail_closed():
    bindings = _bindings(source_run_count=2)
    records = [
        _window("w_a", net_pnl=-1.0, expectancy=-0.1),
        _window("w_a", net_pnl=-2.0, expectancy=-0.2),
    ]
    with pytest.raises(HhHlWindowStabilityError) as exc:
        build_window_stability(bindings=bindings, window_records=records)
    assert exc.value.reason_code == "WINDOW_STABILITY_DUPLICATE_WINDOW"


@pytest.mark.unit
def test_binding_mismatch_fail_closed():
    artifact = build_window_stability(
        bindings=_bindings(),
        window_records=_three_windows(),
    )
    with pytest.raises(HhHlWindowStabilityError) as exc:
        assert_bindings_match(
            artifact,
            expected_bindings=_bindings(authorization_fingerprint=_fp("other")),
        )
    assert exc.value.reason_code == "WINDOW_STABILITY_BINDING_MISMATCH"


@pytest.mark.unit
def test_parameter_fp_mismatch_fail_closed():
    artifact = build_window_stability(
        bindings=_bindings(),
        window_records=_three_windows(),
    )
    with pytest.raises(HhHlWindowStabilityError) as exc:
        assert_bindings_match(
            artifact,
            expected_bindings=_bindings(
                physical_parameter_set_fingerprint=_fp("other-params")
            ),
        )
    assert exc.value.reason_code == "WINDOW_STABILITY_BINDING_MISMATCH"


@pytest.mark.unit
def test_dataset_fp_mismatch_fail_closed():
    artifact = build_window_stability(
        bindings=_bindings(),
        window_records=_three_windows(),
    )
    with pytest.raises(HhHlWindowStabilityError) as exc:
        assert_bindings_match(
            artifact,
            expected_bindings=_bindings(
                dataset_content_fingerprint_digest=_fp("other-dataset")
            ),
        )
    assert exc.value.reason_code == "WINDOW_STABILITY_BINDING_MISMATCH"


@pytest.mark.unit
def test_missing_required_metric_fail_closed():
    bindings = _bindings(source_run_count=1)
    bad = {
        "window_id": "w_a",
        "result": {
            "net_pnl_quote": -1.0,
            # expectancy_r missing
            "max_drawdown_r": 0.1,
            "fees_total_quote": 1.0,
            "closed_trades_total": 1,
            "gate_result": {"status": "NOT_RANKING_READY"},
        },
    }
    with pytest.raises(HhHlWindowStabilityError) as exc:
        build_window_stability(bindings=bindings, window_records=[bad])
    assert exc.value.reason_code == "WINDOW_STABILITY_MISSING_REQUIRED_METRIC"


@pytest.mark.unit
def test_no_trade_window_excluded_from_sign_shares():
    bindings = _bindings(source_run_count=3)
    records = _three_windows(
        w_b=dict(net_pnl=0.0, expectancy=0.0, trades=0),
    )
    artifact = build_window_stability(bindings=bindings, window_records=records)
    assert artifact["metrics"]["n_zero_trade"] == 1
    assert artifact["metrics"]["n_traded"] == 2
    shares = artifact["metrics"]["sign_shares"]["net_pnl_quote"]
    assert shares["n_traded"] == 2
    assert shares["negative_share"] == 1.0


@pytest.mark.unit
def test_all_zero_trade_null_shares_and_concentration():
    bindings = _bindings(source_run_count=2)
    records = [
        _window("w_a", net_pnl=0.0, expectancy=0.0, trades=0),
        _window("w_b", net_pnl=0.0, expectancy=0.0, trades=0),
    ]
    artifact = build_window_stability(bindings=bindings, window_records=records)
    assert artifact["metrics"]["n_traded"] == 0
    assert artifact["metrics"]["sign_shares"]["net_pnl_quote"]["positive_share"] is None
    assert artifact["metrics"]["concentration"]["denominator_zero"] is True
    assert artifact["metrics"]["concentration"]["top1_abs_pnl_share"] is None


@pytest.mark.unit
def test_extreme_concentration_visible():
    bindings = _bindings(source_run_count=3)
    records = _three_windows(
        w_a=dict(net_pnl=-1000.0, expectancy=-0.1, trades=10),
        w_b=dict(net_pnl=-1.0, expectancy=-0.01, trades=10),
        w_c=dict(net_pnl=-1.0, expectancy=-0.01, trades=10),
    )
    artifact = build_window_stability(bindings=bindings, window_records=records)
    top1 = artifact["metrics"]["concentration"]["top1_abs_pnl_share"]
    assert top1 is not None
    assert top1 > 0.99


@pytest.mark.unit
def test_write_does_not_mutate_primary_result_hashes(tmp_path: Path):
    runs = tmp_path / "runs" / "rk_demo"
    runs.mkdir(parents=True)
    result_path = runs / "result.json"
    payload = {"hello": "world", "net_pnl_quote": -1}
    result_path.write_text(json.dumps(payload), encoding="utf-8")
    before = hashlib.sha256(result_path.read_bytes()).hexdigest()

    artifact = build_window_stability(
        bindings=_bindings(),
        window_records=_three_windows(),
    )
    write_window_stability_artifact(tmp_path, artifact)

    after = hashlib.sha256(result_path.read_bytes()).hexdigest()
    assert before == after
    assert (tmp_path / "window_stability.json").is_file()
