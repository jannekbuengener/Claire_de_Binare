"""Unit tests for core.replay.resampling (#1852)."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from core.replay.resampling import (
    _STABILITY_ARTIFACT_FILENAME,
    ReplayKPIBlock,
    ResamplingConfig,
    ResamplingError,
    ResamplingStabilityArtifact,
    compute_resampling_stability,
    write_resampling_stability_artifact,
)

_RUN_ID = "replay-aabbccddeeff-0001"
_DATASET_FP = "a" * 64
_EXECUTION_PROV = "bt-" + "b" * 16


def _block(
    block_id: str,
    *,
    source_run_id: str = _RUN_ID,
    dataset_fingerprint: str = _DATASET_FP,
    execution_provenance_id: str = _EXECUTION_PROV,
    signal_count: int = 4,
    fill_count: int = 3,
    reject_count: int = 1,
    pnl_sum: str = "0.50000000",
) -> ReplayKPIBlock:
    return ReplayKPIBlock(
        block_id=block_id,
        source_run_id=source_run_id,
        dataset_fingerprint=dataset_fingerprint,
        execution_provenance_id=execution_provenance_id,
        signal_count=signal_count,
        fill_count=fill_count,
        reject_count=reject_count,
        pnl_sum=Decimal(pnl_sum),
    )


def _config(**overrides: object) -> ResamplingConfig:
    fields: dict[str, object] = {
        "method": "block_bootstrap",
        "sample_count": 16,
        "sample_block_count": 1,
        "seed": 11,
        "selected_kpis": ("signal_count", "pnl_sum", "fill_rate"),
    }
    fields.update(overrides)
    return ResamplingConfig(**fields)


class TestResamplingConfig:
    def test_valid_config(self) -> None:
        config = _config()
        assert config.method == "block_bootstrap"
        assert config.sample_count == 16

    def test_unsupported_method_raises(self) -> None:
        with pytest.raises(ResamplingError, match="Unsupported resampling method"):
            _config(method="regime_weighted")

    def test_empty_kpis_raises(self) -> None:
        with pytest.raises(ResamplingError, match="selected_kpis must be a non-empty tuple"):
            _config(selected_kpis=())

    def test_duplicate_kpi_raises(self) -> None:
        with pytest.raises(ResamplingError, match="Duplicate KPI"):
            _config(selected_kpis=("pnl_sum", "pnl_sum"))

    def test_unsupported_kpi_raises(self) -> None:
        with pytest.raises(ResamplingError, match="Unsupported KPI"):
            _config(selected_kpis=("win_rate",))

    def test_negative_seed_raises(self) -> None:
        with pytest.raises(ResamplingError, match="seed must be a non-negative int"):
            _config(seed=-1)


class TestReplayKPIBlock:
    def test_valid_block(self) -> None:
        block = _block("day-001")
        assert block.block_id == "day-001"
        assert block.pnl_sum == Decimal("0.50000000")

    def test_invalid_run_id_raises(self) -> None:
        with pytest.raises(ResamplingError, match="source_run_id"):
            _block("day-001", source_run_id="bad-run")

    def test_float_pnl_raises(self) -> None:
        with pytest.raises(ResamplingError, match="pnl_sum must be a Decimal"):
            ReplayKPIBlock(
                block_id="day-001",
                source_run_id=_RUN_ID,
                dataset_fingerprint=_DATASET_FP,
                execution_provenance_id=_EXECUTION_PROV,
                signal_count=1,
                fill_count=1,
                reject_count=0,
                pnl_sum=1.5,  # type: ignore[arg-type]
            )


class TestComputeResamplingStability:
    def test_deterministic_same_inputs_same_output(self) -> None:
        blocks = [
            _block("day-001", signal_count=4, fill_count=3, reject_count=1, pnl_sum="0.5"),
            _block("day-002", signal_count=5, fill_count=4, reject_count=1, pnl_sum="0.8"),
            _block("day-003", signal_count=3, fill_count=1, reject_count=2, pnl_sum="-0.2"),
            _block("day-004", signal_count=6, fill_count=5, reject_count=1, pnl_sum="1.1"),
        ]
        config = _config(sample_block_count=4)

        first = compute_resampling_stability(blocks, config=config)
        second = compute_resampling_stability(blocks, config=config)

        assert first.to_dict() == second.to_dict()

    def test_baseline_metrics_reflect_source_blocks(self) -> None:
        blocks = [
            _block("day-001", signal_count=4, fill_count=3, reject_count=1, pnl_sum="0.5"),
            _block("day-002", signal_count=5, fill_count=4, reject_count=1, pnl_sum="0.8"),
        ]
        artifact = compute_resampling_stability(
            blocks,
            config=_config(sample_count=8, sample_block_count=2),
        )

        assert artifact.baseline_metrics["signal_count"] == "9"
        assert artifact.baseline_metrics["pnl_sum"] == "1.30000000"
        assert artifact.baseline_metrics["fill_rate"] == "0.77777778"

    def test_source_provenance_pinned(self) -> None:
        blocks = [_block("day-001"), _block("day-002")]
        artifact = compute_resampling_stability(
            blocks,
            config=_config(sample_block_count=2),
        )

        assert artifact.source_provenance.source_run_id == _RUN_ID
        assert artifact.source_provenance.run_count == 1
        assert artifact.source_provenance.block_count == 2
        assert len(artifact.source_provenance.input_fingerprint) == 64

    def test_operator_summary_present(self) -> None:
        blocks = [_block("day-001"), _block("day-002")]
        artifact = compute_resampling_stability(
            blocks,
            config=_config(sample_block_count=2),
        )

        assert "method=block_bootstrap" in artifact.operator_summary[0]
        assert any("fill_rate" in line for line in artifact.operator_summary)

    def test_mixed_source_run_id_rejected(self) -> None:
        blocks = [
            _block("day-001", source_run_id=_RUN_ID),
            _block("day-002", source_run_id="replay-ffffffffffff-0001"),
        ]
        with pytest.raises(ResamplingError, match="same source_run_id"):
            compute_resampling_stability(blocks, config=_config(sample_block_count=2))

    def test_mixed_dataset_fingerprint_rejected(self) -> None:
        blocks = [
            _block("day-001"),
            _block("day-002", dataset_fingerprint="c" * 64),
        ]
        with pytest.raises(ResamplingError, match="same dataset_fingerprint"):
            compute_resampling_stability(blocks, config=_config(sample_block_count=2))

    def test_invalid_block_type_rejected(self) -> None:
        with pytest.raises(ResamplingError, match="ReplayKPIBlock"):
            compute_resampling_stability(["bad"], config=_config())  # type: ignore[list-item]

    def test_empty_blocks_rejected(self) -> None:
        with pytest.raises(ResamplingError, match="blocks must not be empty"):
            compute_resampling_stability([], config=_config())

    def test_output_type_is_artifact(self) -> None:
        artifact = compute_resampling_stability([_block("day-001")], config=_config(sample_block_count=1))
        assert isinstance(artifact, ResamplingStabilityArtifact)
        assert artifact.resampling_method == "block_bootstrap"

    def test_sample_block_count_must_match_input_size(self) -> None:
        blocks = [_block("day-001"), _block("day-002")]
        with pytest.raises(ResamplingError, match="sample_block_count must equal len\\(blocks\\)"):
            compute_resampling_stability(blocks, config=_config(sample_block_count=1))


class TestWriteResamplingStabilityArtifact:
    def _artifact(self) -> ResamplingStabilityArtifact:
        blocks = [
            _block("day-001", signal_count=4, fill_count=3, reject_count=1, pnl_sum="0.5"),
            _block("day-002", signal_count=5, fill_count=4, reject_count=1, pnl_sum="0.8"),
            _block("day-003", signal_count=3, fill_count=1, reject_count=2, pnl_sum="-0.2"),
        ]
        return compute_resampling_stability(blocks, config=_config(sample_block_count=3))

    def test_writes_json_artifact(self, tmp_path: Path) -> None:
        artifact = self._artifact()
        write_resampling_stability_artifact(artifact, tmp_path)

        out = tmp_path / _STABILITY_ARTIFACT_FILENAME
        assert out.exists()
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "replay_resampling_stability.v1"
        assert payload["resampling_method"] == "block_bootstrap"

    def test_deterministic_file_content(self, tmp_path: Path) -> None:
        artifact = self._artifact()
        out = tmp_path / _STABILITY_ARTIFACT_FILENAME
        write_resampling_stability_artifact(artifact, tmp_path)
        content_one = out.read_text(encoding="utf-8")
        out.unlink()
        write_resampling_stability_artifact(artifact, tmp_path)
        content_two = out.read_text(encoding="utf-8")
        assert content_one == content_two

    def test_fail_closed_on_io_error(self, tmp_path: Path) -> None:
        artifact = self._artifact()
        blocker = tmp_path / "blocker"
        blocker.write_text("block", encoding="utf-8")
        with pytest.raises(ResamplingError, match="Failed to write"):
            write_resampling_stability_artifact(artifact, blocker)

    def test_invalid_artifact_type_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ResamplingError, match="ResamplingStabilityArtifact"):
            write_resampling_stability_artifact("bad", tmp_path)  # type: ignore[arg-type]
