"""ARVP walk-forward orchestration: rolling chronological replay window core.

Scope (#1851): deterministic, pure walk-forward window orchestration.
No Runtime/DB wiring, no gate integration, no regime aggregation.

Design rules:
  - All inputs are explicit and caller-supplied; no live data access.
  - WalkForwardSpec validation is fail-closed: invalid window configs raise
    WalkForwardError before any run_fn is called.
  - run_walk_forward() is a pure orchestrator; exceptions from run_fn are
    captured as failed WalkForwardWindowResult entries, never propagated.
  - Deterministic: same WalkForwardSpec → identical wf_fingerprint.
  - Manifest is written to output_dir/walk_forward_id/walk_forward_manifest.json.

Fail-closed conditions:
  - windows empty:                     WalkForwardError("windows must not be empty")
  - duplicate window_id:               WalkForwardError("Duplicate window_id: …")
  - windows not strictly ordered:      WalkForwardError("Windows must be strictly ordered …")
  - overlapping windows:               WalkForwardError("Window … overlaps …")
  - invalid role:                      WalkForwardError("Invalid role …")
  - warmup_candles < 0:                WalkForwardError("warmup_candles must be >= 0 …")
  - start_ts_ms > end_ts_ms:           WalkForwardError("start_ts_ms … must be <= end_ts_ms …")

Non-goals:
  - arvp_gate wiring
  - regime scorecard aggregation across windows
  - scenario harness wrapping per window
  - CLI or runner wiring
  - dashboard

relations:
  domain: validation
  upstream:
    - core.replay.canonical_json  (canonical_hash, canonical_json_dumps)
    - core.utils.clock            (utcnow)
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from datetime import timezone
from typing import Any, Callable, Literal

from core.replay.canonical_json import canonical_hash, canonical_json_dumps
from core.utils.clock import utcnow

_WALK_FORWARD_MANIFEST_FILENAME = "walk_forward_manifest.json"
_VALID_ROLES: frozenset[str] = frozenset({"train", "calibrate", "validate"})


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------


class WalkForwardError(ValueError):
    """Raised when walk-forward spec validation, orchestration, or I/O fails."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _utcnow_iso() -> str:
    dt = utcnow()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()


def _require_non_empty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise WalkForwardError(f"{field_name} must be a non-empty string")


# ---------------------------------------------------------------------------
# Domain structs
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WalkForwardWindowSpec:
    """Specification for a single window within a walk-forward run.

    Fields
    ------
    window_id:
        Unique identifier for this window within the walk-forward run.
        Must be a non-empty string.
    start_ts_ms:
        Inclusive window start in milliseconds (UTC epoch).
    end_ts_ms:
        Inclusive window end in milliseconds (UTC epoch).
        Must be >= start_ts_ms.
    warmup_candles:
        Number of candles at the head of the window reserved for indicator
        warm-up. Must be >= 0.
    role:
        Optional window role for train/calibrate/validate sequencing.
        Must be one of "train", "calibrate", "validate", or None.
    """

    window_id: str
    start_ts_ms: int
    end_ts_ms: int
    warmup_candles: int
    role: Literal["train", "calibrate", "validate"] | None = None

    def __post_init__(self) -> None:
        _require_non_empty_string(self.window_id, "window_id")
        if isinstance(self.start_ts_ms, bool) or not isinstance(self.start_ts_ms, int):
            raise WalkForwardError("start_ts_ms must be an int (not bool)")
        if isinstance(self.end_ts_ms, bool) or not isinstance(self.end_ts_ms, int):
            raise WalkForwardError("end_ts_ms must be an int (not bool)")
        if self.start_ts_ms > self.end_ts_ms:
            raise WalkForwardError(
                f"start_ts_ms ({self.start_ts_ms}) must be <= end_ts_ms ({self.end_ts_ms})"
            )
        if isinstance(self.warmup_candles, bool) or not isinstance(self.warmup_candles, int):
            raise WalkForwardError("warmup_candles must be an int (not bool)")
        if self.warmup_candles < 0:
            raise WalkForwardError(
                f"warmup_candles must be >= 0, got {self.warmup_candles}"
            )
        if self.role is not None and self.role not in _VALID_ROLES:
            raise WalkForwardError(
                f"Invalid role {self.role!r}. Allowed: {sorted(_VALID_ROLES)} or None."
            )

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "window_id": self.window_id,
            "start_ts_ms": self.start_ts_ms,
            "end_ts_ms": self.end_ts_ms,
            "warmup_candles": self.warmup_candles,
        }
        if self.role is not None:
            d["role"] = self.role
        return d


@dataclass(frozen=True, slots=True)
class WalkForwardSpec:
    """Specification for a complete walk-forward run.

    Fields
    ------
    walk_forward_id:
        Unique identifier for this walk-forward configuration.
    strategy_id:
        Strategy being validated.
    symbol:
        Trading pair (e.g., "BTCUSDT").
    windows:
        Ordered tuple of WalkForwardWindowSpec. Must be:
        - non-empty
        - unique window_ids
        - strictly chronologically ordered by start_ts_ms
        - non-overlapping (each window's start_ts_ms >= previous end_ts_ms)
        Gaps between windows are explicitly allowed.
    """

    walk_forward_id: str
    strategy_id: str
    symbol: str
    windows: tuple[WalkForwardWindowSpec, ...]

    def __post_init__(self) -> None:
        _require_non_empty_string(self.walk_forward_id, "walk_forward_id")
        _require_non_empty_string(self.strategy_id, "strategy_id")
        _require_non_empty_string(self.symbol, "symbol")
        if not isinstance(self.windows, tuple):
            raise WalkForwardError("windows must be a tuple of WalkForwardWindowSpec")
        if not self.windows:
            raise WalkForwardError("windows must not be empty")
        for w in self.windows:
            if not isinstance(w, WalkForwardWindowSpec):
                raise WalkForwardError(
                    f"Expected WalkForwardWindowSpec in windows, got {type(w).__name__}"
                )
        seen_ids: set[str] = set()
        for w in self.windows:
            if w.window_id in seen_ids:
                raise WalkForwardError(f"Duplicate window_id: {w.window_id!r}")
            seen_ids.add(w.window_id)
        for i in range(1, len(self.windows)):
            prev = self.windows[i - 1]
            curr = self.windows[i]
            if curr.start_ts_ms <= prev.start_ts_ms:
                raise WalkForwardError(
                    f"Windows must be strictly ordered by start_ts_ms: "
                    f"window {curr.window_id!r}.start_ts_ms={curr.start_ts_ms} is not "
                    f"greater than window {prev.window_id!r}.start_ts_ms={prev.start_ts_ms}"
                )
            if curr.start_ts_ms < prev.end_ts_ms:
                raise WalkForwardError(
                    f"Window {curr.window_id!r} overlaps with window {prev.window_id!r}: "
                    f"curr.start_ts_ms={curr.start_ts_ms} < prev.end_ts_ms={prev.end_ts_ms}"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "walk_forward_id": self.walk_forward_id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "windows": [w.to_dict() for w in self.windows],
        }

    def fingerprint(self) -> str:
        """Deterministic 64-char SHA-256 hex of the spec (request identity)."""
        return canonical_hash(self.to_dict())


@dataclass(frozen=True, slots=True)
class WalkForwardWindowResult:
    """Result of executing a single walk-forward window.

    Invariants:
    - failure_reason is required when exit_code != 0
    - failure_reason must be None when exit_code == 0
    """

    window_id: str
    exit_code: int
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty_string(self.window_id, "window_id")
        if isinstance(self.exit_code, bool) or not isinstance(self.exit_code, int):
            raise WalkForwardError("exit_code must be an int (not bool)")
        if self.exit_code != 0 and self.failure_reason is None:
            raise WalkForwardError(
                "failure_reason is required when exit_code != 0"
            )
        if self.exit_code == 0 and self.failure_reason is not None:
            raise WalkForwardError(
                "failure_reason must be None when exit_code == 0"
            )
        if self.failure_reason is not None:
            _require_non_empty_string(self.failure_reason, "failure_reason")

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "window_id": self.window_id,
            "exit_code": self.exit_code,
        }
        if self.failure_reason is not None:
            result["failure_reason"] = self.failure_reason
        return result


@dataclass(frozen=True, slots=True)
class WalkForwardManifest:
    """Manifest of a completed walk-forward orchestration run."""

    walk_forward_id: str
    wf_fingerprint: str
    windows_total: int
    succeeded_count: int
    failed_count: int
    window_results: tuple[WalkForwardWindowResult, ...]
    started_at_utc: str
    finished_at_utc: str
    artifact_root: str

    def __post_init__(self) -> None:
        _require_non_empty_string(self.walk_forward_id, "walk_forward_id")
        _require_non_empty_string(self.wf_fingerprint, "wf_fingerprint")
        _require_non_empty_string(self.artifact_root, "artifact_root")
        if not isinstance(self.window_results, tuple):
            raise WalkForwardError("window_results must be a tuple")
        if self.windows_total != len(self.window_results):
            raise WalkForwardError(
                "windows_total must equal len(window_results)"
            )
        if self.succeeded_count + self.failed_count != self.windows_total:
            raise WalkForwardError(
                "succeeded_count + failed_count must equal windows_total"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "walk_forward_id": self.walk_forward_id,
            "wf_fingerprint": self.wf_fingerprint,
            "windows_total": self.windows_total,
            "succeeded_count": self.succeeded_count,
            "failed_count": self.failed_count,
            "started_at_utc": self.started_at_utc,
            "finished_at_utc": self.finished_at_utc,
            "artifact_root": self.artifact_root,
            "window_results": [r.to_dict() for r in self.window_results],
        }


# ---------------------------------------------------------------------------
# Manifest I/O
# ---------------------------------------------------------------------------


def _write_walk_forward_manifest(
    wf_dir: pathlib.Path, manifest: WalkForwardManifest
) -> None:
    try:
        wf_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = wf_dir / _WALK_FORWARD_MANIFEST_FILENAME
        manifest_path.write_text(
            canonical_json_dumps(manifest.to_dict()),
            encoding="utf-8",
        )
    except OSError as exc:
        raise WalkForwardError(
            f"Failed to write walk-forward manifest to {wf_dir}: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_walk_forward(
    spec: WalkForwardSpec,
    *,
    run_fn: Callable[[WalkForwardWindowSpec], WalkForwardWindowResult],
    output_dir: pathlib.Path | str,
) -> WalkForwardManifest:
    """Orchestrate a walk-forward run deterministically.

    Executes run_fn for each window in the order defined by spec.windows.
    Exceptions from run_fn are captured as failed WalkForwardWindowResult
    entries — they are never silently propagated to the caller.

    The manifest is written to output_dir/walk_forward_id/walk_forward_manifest.json.

    Args:
        spec: WalkForwardSpec defining the windows and run parameters.
        run_fn: Callable that executes a single window and returns a
            WalkForwardWindowResult. The returned result's window_id must
            match the input WalkForwardWindowSpec.window_id. Returning the
            wrong type or a mismatched window_id raises WalkForwardError.
            All other exceptions are captured and recorded as failures.
        output_dir: Root directory for walk-forward output.

    Returns:
        WalkForwardManifest with all window results and a written manifest.

    Raises:
        WalkForwardError: If spec is invalid, run_fn returns the wrong type
            or a mismatched window_id, or the manifest write fails.
    """
    if not isinstance(spec, WalkForwardSpec):
        raise WalkForwardError(
            f"Expected WalkForwardSpec, got {type(spec).__name__}"
        )

    output_path = pathlib.Path(output_dir)
    started_at = _utcnow_iso()
    wf_fingerprint = spec.fingerprint()

    results: list[WalkForwardWindowResult] = []

    for window_spec in spec.windows:
        try:
            result = run_fn(window_spec)
        except Exception as exc:
            raw_msg = str(exc).strip()
            failure_msg = (
                raw_msg if raw_msg else f"{type(exc).__name__} (no message)"
            )
            result = WalkForwardWindowResult(
                window_id=window_spec.window_id,
                exit_code=1,
                failure_reason=f"run_fn raised {type(exc).__name__}: {failure_msg}",
            )
        else:
            if not isinstance(result, WalkForwardWindowResult):
                raise WalkForwardError(
                    f"run_fn must return WalkForwardWindowResult, "
                    f"got {type(result).__name__} for window {window_spec.window_id!r}"
                )
            if result.window_id != window_spec.window_id:
                raise WalkForwardError(
                    f"run_fn returned result with window_id={result.window_id!r} "
                    f"but expected {window_spec.window_id!r}"
                )
        results.append(result)

    finished_at = _utcnow_iso()
    succeeded = sum(1 for r in results if r.succeeded)
    failed = len(results) - succeeded
    wf_dir = output_path / spec.walk_forward_id

    manifest = WalkForwardManifest(
        walk_forward_id=spec.walk_forward_id,
        wf_fingerprint=wf_fingerprint,
        windows_total=len(results),
        succeeded_count=succeeded,
        failed_count=failed,
        window_results=tuple(results),
        started_at_utc=started_at,
        finished_at_utc=finished_at,
        artifact_root=str(wf_dir),
    )

    _write_walk_forward_manifest(wf_dir, manifest)
    return manifest
