"""CDB-050 DQ verdict binding to content identity — non-tautological matrix."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.market_data.historical_common import (
    DQ_CONTENT_FINGERPRINT_MISMATCH,
    DQ_CONTENT_FINGERPRINT_MISSING,
    DQ_EVIDENCE_CONTENT_MISMATCH,
    HistoricalProbeError,
    NormalizedCandle,
    assert_dq_content_binding,
    build_quality_report,
    content_fingerprint_for_candle_rows,
    content_fingerprint_for_normalized,
    dq_report_from_dataset_spec,
    enforce_dq_content_binding,
)

pytestmark = pytest.mark.unit

_BASE = 1_700_000_000_000


def _candles(n: int = 3, *, close0: str = "100.5") -> list[NormalizedCandle]:
    out: list[NormalizedCandle] = []
    for i in range(n):
        out.append(
            NormalizedCandle(
                ts_ms=_BASE + i * 60_000,
                open="100.0",
                high="101.0",
                low="99.0",
                close=close0 if i == 0 else "100.5",
                volume="1.0",
                quote_volume=None,
                trade_count=None,
                symbol="BTCUSDT",
                venue="binance",
                timeframe="1m",
                source_type="test",
                source_file_sha256="d" * 64,
            )
        )
    return out


def _rows(candles: list[NormalizedCandle]) -> list[dict]:
    return [
        {
            "ts_ms": c.ts_ms,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
        }
        for c in candles
    ]


def _report_for(candles: list[NormalizedCandle]) -> dict:
    return build_quality_report(
        candles,
        start_ts_ms=_BASE,
        end_ts_ms=_BASE + (len(candles) - 1) * 60_000,
        step_ms=60_000,
        source_hash="e" * 64,
    )


# --- Positive ---


def test_cdb050_dq_verdict_binds_content_fingerprint() -> None:
    candles = _candles()
    report = _report_for(candles)
    expected = content_fingerprint_for_normalized(candles)
    assert report["content_fingerprint"] == expected
    assert report["content_binding_schema"] == "cdb.dq_content_binding.v1"
    assert_dq_content_binding(report, content_fingerprint=expected)


def test_cdb050_triple_match_verdict_evidence_dataset() -> None:
    candles = _candles()
    report = _report_for(candles)
    evidence = {
        "content_fingerprint": content_fingerprint_for_normalized(candles),
        "evidence_links": ["docs/runbooks/example.md"],
    }
    bound = enforce_dq_content_binding(
        report=report, candles=candles, evidence=evidence
    )
    assert bound == report["content_fingerprint"]


def test_cdb050_identical_repeat_is_deterministic() -> None:
    candles = _candles()
    report = _report_for(candles)
    a = enforce_dq_content_binding(report=report, candles=candles)
    b = enforce_dq_content_binding(report=report, candles=list(candles))
    assert a == b


def test_cdb050_nonsemantic_evidence_links_do_not_change_binding() -> None:
    candles = _candles()
    report = _report_for(candles)
    evidence_a = {
        "content_fingerprint": report["content_fingerprint"],
        "evidence_links": ["a.md"],
    }
    evidence_b = {
        "content_fingerprint": report["content_fingerprint"],
        "evidence_links": ["b.md", "c.md"],
    }
    assert enforce_dq_content_binding(
        report=report, candles=candles, evidence=evidence_a
    ) == enforce_dq_content_binding(report=report, candles=candles, evidence=evidence_b)


# --- Negative ---


def test_cdb050_changed_content_makes_verdict_stale() -> None:
    candles = _candles()
    report = _report_for(candles)
    altered = _candles(close0="999.0")
    new_fp = content_fingerprint_for_normalized(altered)
    with pytest.raises(HistoricalProbeError) as exc:
        assert_dq_content_binding(report, content_fingerprint=new_fp)
    assert exc.value.code == DQ_CONTENT_FINGERPRINT_MISMATCH


def test_cdb050_same_request_fingerprint_cannot_override_content_mismatch() -> None:
    """Request-FP equality must not sanitize a content mismatch (CDB-050)."""
    candles_a = _candles(close0="100.5")
    candles_b = _candles(close0="200.5")
    report = _report_for(candles_a)
    # Same synthetic "request" token for both — must still fail on content.
    request_fp = "r" * 64
    assert request_fp  # present, but irrelevant to binding
    with pytest.raises(HistoricalProbeError) as exc:
        enforce_dq_content_binding(report=report, candles=candles_b)
    assert exc.value.code == DQ_CONTENT_FINGERPRINT_MISMATCH


def test_cdb050_same_window_id_cannot_override_content_mismatch() -> None:
    candles_a = _candles(close0="100.5")
    candles_b = _candles(close0="300.5")
    report = _report_for(candles_a)
    report_with_window = {**report, "window_id": "binance_1m_month_2021_01"}
    with pytest.raises(HistoricalProbeError) as exc:
        enforce_dq_content_binding(
            report={**report_with_window, "window_id": "binance_1m_month_2021_01"},
            candles=candles_b,
        )
    assert exc.value.code == DQ_CONTENT_FINGERPRINT_MISMATCH


def test_cdb050_same_filepath_changed_candles_mismatch(tmp_path: Path) -> None:
    candles_a = _candles(close0="100.5")
    candles_b = _candles(close0="400.5")
    path = tmp_path / "candles.jsonl"
    path.write_text(
        "\n".join(json.dumps(r) for r in _rows(candles_a)) + "\n", encoding="utf-8"
    )
    report = _report_for(candles_a)
    # Same path string stamped into report metadata must not override content.
    report = {**report, "file_path": str(path)}
    with pytest.raises(HistoricalProbeError) as exc:
        enforce_dq_content_binding(report=report, candles=candles_b)
    assert exc.value.code == DQ_CONTENT_FINGERPRINT_MISMATCH


def test_cdb050_missing_binding_blocks() -> None:
    with pytest.raises(HistoricalProbeError) as exc:
        assert_dq_content_binding(
            {"verdict": "STRICT_COMPLETE"}, content_fingerprint="a" * 64
        )
    assert exc.value.code == DQ_CONTENT_FINGERPRINT_MISSING


def test_cdb050_evidence_missing_content_fingerprint() -> None:
    candles = _candles()
    report = _report_for(candles)
    with pytest.raises(HistoricalProbeError) as exc:
        enforce_dq_content_binding(
            report=report,
            candles=candles,
            evidence={"verdict": "STRICT_COMPLETE"},
        )
    assert exc.value.code == DQ_CONTENT_FINGERPRINT_MISSING


def test_cdb050_verdict_matches_evidence_but_not_dataset() -> None:
    candles_a = _candles(close0="100.5")
    candles_b = _candles(close0="500.5")
    report = _report_for(candles_a)
    evidence = {"content_fingerprint": report["content_fingerprint"]}
    with pytest.raises(HistoricalProbeError) as exc:
        enforce_dq_content_binding(report=report, candles=candles_b, evidence=evidence)
    assert exc.value.code in {
        DQ_CONTENT_FINGERPRINT_MISMATCH,
        DQ_EVIDENCE_CONTENT_MISMATCH,
    }


def test_cdb050_verdict_matches_dataset_evidence_differs() -> None:
    candles = _candles()
    report = _report_for(candles)
    evidence = {"content_fingerprint": "0" * 64}
    with pytest.raises(HistoricalProbeError) as exc:
        enforce_dq_content_binding(report=report, candles=candles, evidence=evidence)
    assert exc.value.code == DQ_EVIDENCE_CONTENT_MISMATCH


def test_cdb050_stale_evidence_after_candle_change() -> None:
    candles = _candles(close0="100.5")
    report = _report_for(candles)
    evidence = {"content_fingerprint": report["content_fingerprint"]}
    altered = _candles(close0="600.5")
    with pytest.raises(HistoricalProbeError) as exc:
        enforce_dq_content_binding(report=report, candles=altered, evidence=evidence)
    assert exc.value.code in {
        DQ_CONTENT_FINGERPRINT_MISMATCH,
        DQ_EVIDENCE_CONTENT_MISMATCH,
    }


def test_cdb050_warmup_content_change_breaks_binding() -> None:
    """Warmup rows participate in canonical content identity."""
    full = _candles(n=5, close0="100.5")
    report = _report_for(full)
    # Change only the first (warmup) candle close.
    mutated = _candles(n=5, close0="100.5")
    mutated[0] = NormalizedCandle(
        ts_ms=mutated[0].ts_ms,
        open=mutated[0].open,
        high=mutated[0].high,
        low=mutated[0].low,
        close="777.0",
        volume=mutated[0].volume,
        quote_volume=None,
        trade_count=None,
        symbol="BTCUSDT",
        venue="binance",
        timeframe="1m",
        source_type="test",
        source_file_sha256="d" * 64,
    )
    assert content_fingerprint_for_normalized(
        full
    ) != content_fingerprint_for_normalized(mutated)
    with pytest.raises(HistoricalProbeError) as exc:
        enforce_dq_content_binding(report=report, candles=mutated)
    assert exc.value.code == DQ_CONTENT_FINGERPRINT_MISMATCH


def test_cdb050_request_content_confusion_rejected() -> None:
    candles = _candles()
    report = _report_for(candles)
    # Passing request fingerprint as content must fail closed.
    with pytest.raises(HistoricalProbeError) as exc:
        assert_dq_content_binding(report, content_fingerprint="r" * 64)
    assert exc.value.code == DQ_CONTENT_FINGERPRINT_MISMATCH


def test_cdb050_request_hash_alone_insufficient_mismatch_param() -> None:
    candles = _candles()
    with pytest.raises(HistoricalProbeError) as exc:
        build_quality_report(
            candles,
            start_ts_ms=_BASE,
            end_ts_ms=_BASE + 120_000,
            step_ms=60_000,
            source_hash="e" * 64,
            content_fingerprint="0" * 64,
        )
    assert exc.value.code == DQ_CONTENT_FINGERPRINT_MISMATCH


def test_cdb050_empty_actual_fingerprint_missing() -> None:
    with pytest.raises(HistoricalProbeError) as exc:
        assert_dq_content_binding(
            {"content_fingerprint": "a" * 64}, content_fingerprint="  "
        )
    assert exc.value.code == DQ_CONTENT_FINGERPRINT_MISSING


def test_cdb050_dq_report_from_spec_requires_verdict() -> None:
    assert dq_report_from_dataset_spec({"window_id": "x"}) is None
    report = dq_report_from_dataset_spec(
        {
            "data_quality_verdict": "STRICT_COMPLETE",
            "content_fingerprint": "a" * 64,
        }
    )
    assert report is not None
    assert report["verdict"] == "STRICT_COMPLETE"
    assert report["content_fingerprint"] == "a" * 64


def test_cdb050_spec_without_content_fp_fails_on_enforce() -> None:
    candles = _candles()
    report = dq_report_from_dataset_spec({"data_quality_verdict": "STRICT_COMPLETE"})
    assert report is not None
    with pytest.raises(HistoricalProbeError) as exc:
        enforce_dq_content_binding(report=report, candles=candles)
    assert exc.value.code == DQ_CONTENT_FINGERPRINT_MISSING


def test_cdb050_row_fingerprint_matches_normalized() -> None:
    candles = _candles()
    assert content_fingerprint_for_normalized(
        candles
    ) == content_fingerprint_for_candle_rows(_rows(candles))


def test_cdb050_consumer_window_bank_materialize_binding(tmp_path: Path) -> None:
    from tools.market_data.binance_window_bank import WindowSpec, _write_window_dataset

    candles = [
        {
            "ts_ms": _BASE + i * 60_000,
            "open": "1",
            "high": "1",
            "low": "1",
            "close": "1",
            "volume": "1",
            "regime_id": 0,
        }
        for i in range(5)
    ]
    window = WindowSpec(
        window_id="cdb050_test_window",
        start_ts_ms=_BASE,
        end_ts_ms=_BASE + 4 * 60_000,
        candle_count=5,
        dataset_fingerprint="",
        regime_distribution={"0": {"count": 5}},
        source_months=("2021-01",),
        overlap_class="monthly",
        evidence_class="controlled_lab_evidence",
        purpose="development",
        quality_verdict="STRICT_COMPLETE",
        candles_path="",
        spec_path="",
    )
    # Redirect IMPORT layout under tmp via writing under artifacts path of tmp.
    # _write_window_dataset uses repo_root / artifacts / ...
    spec_path = _write_window_dataset(tmp_path, window, candles)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    assert "content_fingerprint" in spec
    expected = content_fingerprint_for_candle_rows(candles)
    assert spec["content_fingerprint"] == expected
    enforce_dq_content_binding(
        report=dq_report_from_dataset_spec(spec),  # type: ignore[arg-type]
        candles=candles,
    )


def test_cdb050_adapter_rejects_stale_content_fp(tmp_path: Path) -> None:
    from core.replay.binance_window_bank_adapter import (
        BinanceWindowBankAdapterError,
        load_binance_window_dataset,
    )

    window_id = "cdb050_stale"
    root = tmp_path / window_id
    root.mkdir()
    candles = [
        {
            "ts_ms": _BASE + i * 60_000,
            "open": "1",
            "high": "1",
            "low": "1",
            "close": "1",
            "volume": "1",
            "regime_id": 0,
        }
        for i in range(5)
    ]
    (root / "candles.jsonl").write_text(
        "\n".join(json.dumps(c) for c in candles) + "\n", encoding="utf-8"
    )
    (root / "dataset_spec.json").write_text(
        json.dumps(
            {
                "window_id": window_id,
                "symbol": "BTCUSDT",
                "timeframe": "1m",
                "start_ts_ms": candles[0]["ts_ms"],
                "end_ts_ms": candles[-1]["ts_ms"],
                "file_path": str(root / "candles.jsonl"),
                "data_quality_verdict": "STRICT_COMPLETE",
                "content_fingerprint": "0" * 64,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(BinanceWindowBankAdapterError, match="DQ content binding"):
        load_binance_window_dataset(
            window_id,
            warmup_candles=1,
            repo_root=tmp_path,
            window_bank_root=tmp_path,
        )


def test_cdb050_runner_file_sidecar_mismatch(tmp_path: Path) -> None:
    from services.validation.strategy_replay_runner import (
        ARVPReplayConfig,
        ReplayRunnerError,
        _load_dataset_result,
    )

    candles = [
        {
            "ts_ms": _BASE + i * 60_000,
            "open": "1",
            "high": "1",
            "low": "1",
            "close": "1",
            "volume": "1",
        }
        for i in range(5)
    ]
    path = tmp_path / "candles.jsonl"
    path.write_text("\n".join(json.dumps(c) for c in candles) + "\n", encoding="utf-8")
    (tmp_path / "quality_report.json").write_text(
        json.dumps(
            {
                "verdict": "STRICT_COMPLETE",
                "content_fingerprint": "0" * 64,
            }
        ),
        encoding="utf-8",
    )
    config = ARVPReplayConfig(
        dataset_source="file",
        input_candles_file=str(path),
        output_directory=str(tmp_path / "out"),
        entry_lookback_minutes=1,
        exit_lookback_minutes=1,
    )
    with pytest.raises(ReplayRunnerError, match="DQ content binding"):
        _load_dataset_result(config, warmup_count=1)


def test_cdb050_runner_file_sidecar_pass(tmp_path: Path) -> None:
    from services.validation.strategy_replay_runner import (
        ARVPReplayConfig,
        _load_dataset_result,
    )

    candles = [
        {
            "ts_ms": _BASE + i * 60_000,
            "open": "1",
            "high": "1",
            "low": "1",
            "close": "1",
            "volume": "1",
        }
        for i in range(5)
    ]
    path = tmp_path / "candles.jsonl"
    path.write_text("\n".join(json.dumps(c) for c in candles) + "\n", encoding="utf-8")
    live_fp = content_fingerprint_for_candle_rows(candles)
    (tmp_path / "quality_report.json").write_text(
        json.dumps(
            {
                "verdict": "STRICT_COMPLETE",
                "content_fingerprint": live_fp,
            }
        ),
        encoding="utf-8",
    )
    config = ARVPReplayConfig(
        dataset_source="file",
        input_candles_file=str(path),
        output_directory=str(tmp_path / "out"),
        entry_lookback_minutes=1,
        exit_lookback_minutes=1,
    )
    result = _load_dataset_result(config, warmup_count=1)
    assert result.content_fingerprint == live_fp
