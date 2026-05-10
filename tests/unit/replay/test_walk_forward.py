"""Unit tests for core/replay/walk_forward.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from core.replay.walk_forward import (
    WalkForwardError,
    WalkForwardManifest,
    WalkForwardSpec,
    WalkForwardWindowResult,
    WalkForwardWindowSpec,
    run_walk_forward,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _window(
    window_id: str = "w1",
    start_ts_ms: int = 0,
    end_ts_ms: int = 1000,
    warmup_candles: int = 0,
    role: str | None = None,
) -> WalkForwardWindowSpec:
    return WalkForwardWindowSpec(
        window_id=window_id,
        start_ts_ms=start_ts_ms,
        end_ts_ms=end_ts_ms,
        warmup_candles=warmup_candles,
        role=role,  # type: ignore[arg-type]
    )


def _spec(
    walk_forward_id: str = "wf-test",
    strategy_id: str = "strategy_x",
    symbol: str = "BTCUSDT",
    windows: tuple[WalkForwardWindowSpec, ...] | None = None,
) -> WalkForwardSpec:
    if windows is None:
        windows = (
            _window("w1", 0, 1000),
            _window("w2", 2000, 3000),
        )
    return WalkForwardSpec(
        walk_forward_id=walk_forward_id,
        strategy_id=strategy_id,
        symbol=symbol,
        windows=windows,
    )


def _success_fn(w: WalkForwardWindowSpec) -> WalkForwardWindowResult:
    return WalkForwardWindowResult(window_id=w.window_id, exit_code=0)


def _failure_fn(w: WalkForwardWindowSpec) -> WalkForwardWindowResult:
    return WalkForwardWindowResult(
        window_id=w.window_id, exit_code=1, failure_reason="simulated failure"
    )


# ---------------------------------------------------------------------------
# WalkForwardWindowSpec validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWalkForwardWindowSpec:
    def test_valid_construction(self) -> None:
        w = _window("w1", 0, 500, 10, "train")
        assert w.window_id == "w1"
        assert w.start_ts_ms == 0
        assert w.end_ts_ms == 500
        assert w.warmup_candles == 10
        assert w.role == "train"

    def test_role_none_allowed(self) -> None:
        w = _window("w1", 0, 500, 0, None)
        assert w.role is None

    def test_all_valid_roles(self) -> None:
        for role in ("train", "calibrate", "validate"):
            w = _window("w1", 0, 500, 0, role)
            assert w.role == role

    def test_invalid_role_fail_closed(self) -> None:
        with pytest.raises(WalkForwardError, match="Invalid role"):
            _window(role="optimize")

    def test_empty_window_id_fail_closed(self) -> None:
        with pytest.raises(WalkForwardError, match="window_id"):
            _window(window_id="")

    def test_whitespace_window_id_fail_closed(self) -> None:
        with pytest.raises(WalkForwardError, match="window_id"):
            _window(window_id="   ")

    def test_start_greater_than_end_fail_closed(self) -> None:
        with pytest.raises(WalkForwardError, match="start_ts_ms.*must be <= end_ts_ms"):
            _window(start_ts_ms=1000, end_ts_ms=500)

    def test_equal_start_end_allowed(self) -> None:
        w = _window(start_ts_ms=500, end_ts_ms=500)
        assert w.start_ts_ms == w.end_ts_ms

    def test_negative_warmup_fail_closed(self) -> None:
        with pytest.raises(WalkForwardError, match="warmup_candles must be >= 0"):
            _window(warmup_candles=-1)

    def test_zero_warmup_allowed(self) -> None:
        w = _window(warmup_candles=0)
        assert w.warmup_candles == 0

    def test_bool_exit_code_rejected_for_start(self) -> None:
        with pytest.raises(WalkForwardError, match="start_ts_ms must be an int"):
            WalkForwardWindowSpec(
                window_id="w1",
                start_ts_ms=True,  # type: ignore[arg-type]
                end_ts_ms=1000,
                warmup_candles=0,
            )

    def test_bool_warmup_rejected(self) -> None:
        with pytest.raises(WalkForwardError, match="warmup_candles must be an int"):
            WalkForwardWindowSpec(
                window_id="w1",
                start_ts_ms=0,
                end_ts_ms=1000,
                warmup_candles=True,  # type: ignore[arg-type]
            )

    def test_to_dict_omits_none_role(self) -> None:
        w = _window("w1", 0, 500, 5, None)
        d = w.to_dict()
        assert "role" not in d

    def test_to_dict_includes_role_when_set(self) -> None:
        w = _window("w1", 0, 500, 5, "validate")
        d = w.to_dict()
        assert d["role"] == "validate"

    def test_to_dict_shape(self) -> None:
        w = _window("w1", 100, 200, 3, "train")
        d = w.to_dict()
        assert d == {
            "window_id": "w1",
            "start_ts_ms": 100,
            "end_ts_ms": 200,
            "warmup_candles": 3,
            "role": "train",
        }


# ---------------------------------------------------------------------------
# WalkForwardSpec validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWalkForwardSpec:
    def test_valid_two_window_spec(self) -> None:
        spec = _spec()
        assert spec.walk_forward_id == "wf-test"
        assert len(spec.windows) == 2

    def test_single_window_allowed(self) -> None:
        spec = _spec(windows=(_window("w1", 0, 1000),))
        assert len(spec.windows) == 1

    def test_empty_windows_fail_closed(self) -> None:
        with pytest.raises(WalkForwardError, match="windows must not be empty"):
            _spec(windows=())

    def test_duplicate_window_id_fail_closed(self) -> None:
        with pytest.raises(WalkForwardError, match="Duplicate window_id"):
            _spec(
                windows=(
                    _window("w1", 0, 1000),
                    _window("w1", 2000, 3000),
                )
            )

    def test_overlap_fail_closed(self) -> None:
        with pytest.raises(WalkForwardError, match="overlaps"):
            _spec(
                windows=(
                    _window("w1", 0, 2000),
                    _window("w2", 1000, 3000),
                )
            )

    def test_reverse_order_fail_closed(self) -> None:
        with pytest.raises(WalkForwardError, match="strictly ordered"):
            _spec(
                windows=(
                    _window("w1", 2000, 3000),
                    _window("w2", 0, 1000),
                )
            )

    def test_gap_between_windows_allowed(self) -> None:
        spec = _spec(
            windows=(
                _window("w1", 0, 1000),
                _window("w2", 5000, 6000),
            )
        )
        assert len(spec.windows) == 2

    def test_adjacent_windows_allowed(self) -> None:
        spec = _spec(
            windows=(
                _window("w1", 0, 1000),
                _window("w2", 1000, 2000),
            )
        )
        assert spec.windows[1].start_ts_ms == spec.windows[0].end_ts_ms

    def test_three_windows_with_roles_valid(self) -> None:
        spec = _spec(
            windows=(
                _window("train", 0, 10000, role="train"),
                _window("calibrate", 10000, 20000, role="calibrate"),
                _window("validate", 20000, 30000, role="validate"),
            )
        )
        assert len(spec.windows) == 3

    def test_empty_walk_forward_id_fail_closed(self) -> None:
        with pytest.raises(WalkForwardError, match="walk_forward_id"):
            WalkForwardSpec(
                walk_forward_id="",
                strategy_id="s",
                symbol="BTCUSDT",
                windows=(_window(),),
            )

    def test_empty_strategy_id_fail_closed(self) -> None:
        with pytest.raises(WalkForwardError, match="strategy_id"):
            WalkForwardSpec(
                walk_forward_id="wf-1",
                strategy_id="",
                symbol="BTCUSDT",
                windows=(_window(),),
            )

    def test_windows_not_tuple_fail_closed(self) -> None:
        with pytest.raises(WalkForwardError, match="windows must be a tuple"):
            WalkForwardSpec(
                walk_forward_id="wf-1",
                strategy_id="s",
                symbol="BTCUSDT",
                windows=[_window()],  # type: ignore[arg-type]
            )

    def test_fingerprint_is_64_char_hex(self) -> None:
        fp = _spec().fingerprint()
        assert len(fp) == 64
        assert all(c in "0123456789abcdef" for c in fp)

    def test_fingerprint_deterministic(self) -> None:
        assert _spec().fingerprint() == _spec().fingerprint()

    def test_fingerprint_differs_for_different_specs(self) -> None:
        fp1 = _spec(walk_forward_id="wf-a").fingerprint()
        fp2 = _spec(walk_forward_id="wf-b").fingerprint()
        assert fp1 != fp2

    def test_to_dict_shape(self) -> None:
        spec = _spec()
        d = spec.to_dict()
        assert d["walk_forward_id"] == "wf-test"
        assert d["strategy_id"] == "strategy_x"
        assert d["symbol"] == "BTCUSDT"
        assert len(d["windows"]) == 2


# ---------------------------------------------------------------------------
# WalkForwardWindowResult validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWalkForwardWindowResult:
    def test_success_result(self) -> None:
        r = WalkForwardWindowResult(window_id="w1", exit_code=0)
        assert r.succeeded is True
        assert r.failure_reason is None

    def test_failure_result(self) -> None:
        r = WalkForwardWindowResult(window_id="w1", exit_code=1, failure_reason="err")
        assert r.succeeded is False

    def test_failure_requires_reason(self) -> None:
        with pytest.raises(WalkForwardError, match="failure_reason is required"):
            WalkForwardWindowResult(window_id="w1", exit_code=1)

    def test_success_must_not_have_reason(self) -> None:
        with pytest.raises(WalkForwardError, match="failure_reason must be None"):
            WalkForwardWindowResult(window_id="w1", exit_code=0, failure_reason="x")

    def test_exit_code_bool_rejected(self) -> None:
        with pytest.raises(WalkForwardError, match="not bool"):
            WalkForwardWindowResult(window_id="w1", exit_code=True)  # type: ignore[arg-type]

    def test_empty_failure_reason_rejected(self) -> None:
        with pytest.raises(WalkForwardError, match="failure_reason"):
            WalkForwardWindowResult(window_id="w1", exit_code=1, failure_reason="   ")

    def test_to_dict_omits_none_failure_reason(self) -> None:
        d = WalkForwardWindowResult(window_id="w1", exit_code=0).to_dict()
        assert "failure_reason" not in d

    def test_to_dict_includes_failure_reason(self) -> None:
        d = WalkForwardWindowResult(
            window_id="w1", exit_code=2, failure_reason="timeout"
        ).to_dict()
        assert d["failure_reason"] == "timeout"


# ---------------------------------------------------------------------------
# run_walk_forward — success paths
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRunWalkForwardSuccess:
    def test_all_windows_succeed(self, tmp_path: Path) -> None:
        spec = _spec(
            windows=(
                _window("w1", 0, 1000),
                _window("w2", 2000, 3000),
                _window("w3", 4000, 5000),
            )
        )
        manifest = run_walk_forward(spec, run_fn=_success_fn, output_dir=tmp_path)

        assert manifest.windows_total == 3
        assert manifest.succeeded_count == 3
        assert manifest.failed_count == 0
        assert all(r.succeeded for r in manifest.window_results)

    def test_window_ids_preserved_in_order(self, tmp_path: Path) -> None:
        spec = _spec(
            windows=(
                _window("alpha", 0, 1000),
                _window("beta", 2000, 3000),
            )
        )
        manifest = run_walk_forward(spec, run_fn=_success_fn, output_dir=tmp_path)
        assert manifest.window_results[0].window_id == "alpha"
        assert manifest.window_results[1].window_id == "beta"

    def test_mixed_success_and_failure(self, tmp_path: Path) -> None:
        def mixed_fn(w: WalkForwardWindowSpec) -> WalkForwardWindowResult:
            if w.window_id == "w2":
                return WalkForwardWindowResult(
                    window_id=w.window_id, exit_code=1, failure_reason="bad data"
                )
            return WalkForwardWindowResult(window_id=w.window_id, exit_code=0)

        spec = _spec(
            windows=(
                _window("w1", 0, 1000),
                _window("w2", 2000, 3000),
                _window("w3", 4000, 5000),
            )
        )
        manifest = run_walk_forward(spec, run_fn=mixed_fn, output_dir=tmp_path)
        assert manifest.succeeded_count == 2
        assert manifest.failed_count == 1

    def test_single_window_run(self, tmp_path: Path) -> None:
        spec = _spec(windows=(_window("only", 0, 9999),))
        manifest = run_walk_forward(spec, run_fn=_success_fn, output_dir=tmp_path)
        assert manifest.windows_total == 1
        assert manifest.succeeded_count == 1

    def test_manifest_walk_forward_id_matches_spec(self, tmp_path: Path) -> None:
        spec = _spec(walk_forward_id="wf-unique-42")
        manifest = run_walk_forward(spec, run_fn=_success_fn, output_dir=tmp_path)
        assert manifest.walk_forward_id == "wf-unique-42"

    def test_manifest_fingerprint_matches_spec(self, tmp_path: Path) -> None:
        spec = _spec()
        manifest = run_walk_forward(spec, run_fn=_success_fn, output_dir=tmp_path)
        assert manifest.wf_fingerprint == spec.fingerprint()


# ---------------------------------------------------------------------------
# run_walk_forward — fail-closed paths
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRunWalkForwardFailClosed:
    def test_run_fn_exception_captured_not_raised(self, tmp_path: Path) -> None:
        def exploding_fn(w: WalkForwardWindowSpec) -> WalkForwardWindowResult:
            raise RuntimeError("dataset missing")

        spec = _spec(windows=(_window("w1", 0, 1000),))
        manifest = run_walk_forward(spec, run_fn=exploding_fn, output_dir=tmp_path)

        assert manifest.failed_count == 1
        assert manifest.succeeded_count == 0
        result = manifest.window_results[0]
        assert not result.succeeded
        assert result.failure_reason is not None
        assert "RuntimeError" in result.failure_reason
        assert "dataset missing" in result.failure_reason

    def test_run_fn_exception_no_message_captured(self, tmp_path: Path) -> None:
        def silent_fn(w: WalkForwardWindowSpec) -> WalkForwardWindowResult:
            raise ValueError()

        spec = _spec(windows=(_window("w1", 0, 1000),))
        manifest = run_walk_forward(spec, run_fn=silent_fn, output_dir=tmp_path)
        result = manifest.window_results[0]
        assert result.failure_reason is not None
        assert "ValueError" in result.failure_reason

    def test_run_fn_wrong_return_type_raises(self, tmp_path: Path) -> None:
        def bad_fn(w: WalkForwardWindowSpec) -> Any:
            return {"window_id": w.window_id}

        spec = _spec(windows=(_window("w1", 0, 1000),))
        with pytest.raises(WalkForwardError, match="must return WalkForwardWindowResult"):
            run_walk_forward(spec, run_fn=bad_fn, output_dir=tmp_path)

    def test_run_fn_mismatched_window_id_raises(self, tmp_path: Path) -> None:
        def mismatched_fn(w: WalkForwardWindowSpec) -> WalkForwardWindowResult:
            return WalkForwardWindowResult(window_id="wrong-id", exit_code=0)

        spec = _spec(windows=(_window("w1", 0, 1000),))
        with pytest.raises(WalkForwardError, match="window_id="):
            run_walk_forward(spec, run_fn=mismatched_fn, output_dir=tmp_path)

    def test_later_windows_still_run_after_failure(self, tmp_path: Path) -> None:
        """Exceptions in window N do not stop window N+1 from executing."""
        call_log: list[str] = []

        def logging_fn(w: WalkForwardWindowSpec) -> WalkForwardWindowResult:
            call_log.append(w.window_id)
            if w.window_id == "w1":
                raise RuntimeError("first window fails")
            return WalkForwardWindowResult(window_id=w.window_id, exit_code=0)

        spec = _spec(
            windows=(
                _window("w1", 0, 1000),
                _window("w2", 2000, 3000),
            )
        )
        manifest = run_walk_forward(spec, run_fn=logging_fn, output_dir=tmp_path)
        assert call_log == ["w1", "w2"]
        assert manifest.failed_count == 1
        assert manifest.succeeded_count == 1

    def test_wrong_spec_type_raises(self, tmp_path: Path) -> None:
        with pytest.raises(WalkForwardError, match="Expected WalkForwardSpec"):
            run_walk_forward(
                "not-a-spec",  # type: ignore[arg-type]
                run_fn=_success_fn,
                output_dir=tmp_path,
            )


# ---------------------------------------------------------------------------
# run_walk_forward — determinism
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRunWalkForwardDeterminism:
    def test_wf_fingerprint_is_deterministic(self, tmp_path: Path) -> None:
        spec = _spec()
        m1 = run_walk_forward(spec, run_fn=_success_fn, output_dir=tmp_path / "run1")
        m2 = run_walk_forward(spec, run_fn=_success_fn, output_dir=tmp_path / "run2")
        assert m1.wf_fingerprint == m2.wf_fingerprint

    def test_fingerprint_differs_for_different_specs(self, tmp_path: Path) -> None:
        spec_a = _spec(walk_forward_id="wf-a")
        spec_b = _spec(walk_forward_id="wf-b")
        m_a = run_walk_forward(spec_a, run_fn=_success_fn, output_dir=tmp_path / "a")
        m_b = run_walk_forward(spec_b, run_fn=_success_fn, output_dir=tmp_path / "b")
        assert m_a.wf_fingerprint != m_b.wf_fingerprint

    def test_fingerprint_differs_when_windows_change(self, tmp_path: Path) -> None:
        spec1 = _spec(windows=(_window("w1", 0, 1000),))
        spec2 = _spec(windows=(_window("w1", 0, 2000),))
        assert spec1.fingerprint() != spec2.fingerprint()


# ---------------------------------------------------------------------------
# run_walk_forward — manifest artifact
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRunWalkForwardManifestArtifact:
    def test_manifest_file_written(self, tmp_path: Path) -> None:
        spec = _spec()
        run_walk_forward(spec, run_fn=_success_fn, output_dir=tmp_path)
        manifest_path = tmp_path / spec.walk_forward_id / "walk_forward_manifest.json"
        assert manifest_path.exists()

    def test_manifest_file_is_valid_json(self, tmp_path: Path) -> None:
        spec = _spec()
        run_walk_forward(spec, run_fn=_success_fn, output_dir=tmp_path)
        manifest_path = tmp_path / spec.walk_forward_id / "walk_forward_manifest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_manifest_file_content_matches_returned_manifest(
        self, tmp_path: Path
    ) -> None:
        spec = _spec()
        manifest = run_walk_forward(spec, run_fn=_success_fn, output_dir=tmp_path)
        manifest_path = tmp_path / spec.walk_forward_id / "walk_forward_manifest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))

        assert data["walk_forward_id"] == manifest.walk_forward_id
        assert data["wf_fingerprint"] == manifest.wf_fingerprint
        assert data["windows_total"] == manifest.windows_total
        assert data["succeeded_count"] == manifest.succeeded_count
        assert data["failed_count"] == manifest.failed_count
        assert len(data["window_results"]) == manifest.windows_total

    def test_artifact_root_points_to_wf_dir(self, tmp_path: Path) -> None:
        spec = _spec(walk_forward_id="wf-artifact-check")
        manifest = run_walk_forward(spec, run_fn=_success_fn, output_dir=tmp_path)
        expected_root = str(tmp_path / "wf-artifact-check")
        assert manifest.artifact_root == expected_root

    def test_manifest_written_with_failed_windows(self, tmp_path: Path) -> None:
        spec = _spec(windows=(_window("w1", 0, 1000),))
        run_walk_forward(spec, run_fn=_failure_fn, output_dir=tmp_path)
        manifest_path = tmp_path / spec.walk_forward_id / "walk_forward_manifest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert data["failed_count"] == 1
        assert data["window_results"][0]["failure_reason"] == "simulated failure"

    def test_idempotent_reruns_write_stable_fingerprint(
        self, tmp_path: Path
    ) -> None:
        spec = _spec()
        m1 = run_walk_forward(spec, run_fn=_success_fn, output_dir=tmp_path / "r1")
        m2 = run_walk_forward(spec, run_fn=_success_fn, output_dir=tmp_path / "r2")
        assert m1.wf_fingerprint == m2.wf_fingerprint
        assert m1.windows_total == m2.windows_total
        assert m1.succeeded_count == m2.succeeded_count
