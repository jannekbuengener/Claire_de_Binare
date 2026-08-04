"""Executor interface + fake/real adapters for #4153 sensitivity campaign."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

REQUIRED_PARAM_KEYS = (
    "entry_lookback_minutes",
    "exit_lookback_minutes",
    "breakout_buffer",
    "min_minutes_between_entries",
)
ALLOWED_IDENTITY_PARAM_KEYS = frozenset({"scenario_id", "strategy_id"})
ALLOWED_PARAM_KEYS = frozenset(REQUIRED_PARAM_KEYS) | ALLOWED_IDENTITY_PARAM_KEYS

DEFAULT_ADAPTER_ID = "primary_breakout_runner_v1"
DEFAULT_SYMBOL = "BTCUSDT"
DEFAULT_SPEEDUP = "instant"


@dataclass(frozen=True, slots=True)
class RunEnvelope:
    run_key: str
    campaign_id: str
    manifest_fingerprint: str
    execution_sha: str
    window_id: str
    strategy_id: str
    parameters: dict[str, Any]
    slot_id: str
    phase: str
    label: str
    physical_parameter_set_fingerprint: str
    effective_config_fingerprint: str
    dataset_content_fingerprint: str
    seed: str
    output_dir: str
    run_plan_fingerprint: str
    authorization_fingerprint: str
    attempt: int = 1
    reproduction_attempt: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_key": self.run_key,
            "campaign_id": self.campaign_id,
            "manifest_fingerprint": self.manifest_fingerprint,
            "execution_sha": self.execution_sha,
            "window_id": self.window_id,
            "strategy_id": self.strategy_id,
            "parameters": dict(self.parameters),
            "slot_id": self.slot_id,
            "phase": self.phase,
            "label": self.label,
            "physical_parameter_set_fingerprint": (
                self.physical_parameter_set_fingerprint
            ),
            "effective_config_fingerprint": self.effective_config_fingerprint,
            "dataset_content_fingerprint": self.dataset_content_fingerprint,
            "seed": self.seed,
            "output_dir": self.output_dir,
            "run_plan_fingerprint": self.run_plan_fingerprint,
            "authorization_fingerprint": self.authorization_fingerprint,
            "attempt": self.attempt,
            "reproduction_attempt": self.reproduction_attempt,
        }


@dataclass(frozen=True, slots=True)
class RunResult:
    exit_code: int
    metrics: dict[str, Any] = field(default_factory=dict)
    detail: str = ""


class CampaignRunExecutor(Protocol):
    def execute(self, envelope: RunEnvelope) -> RunResult:
        """Execute a single bound replay run. Must not relax campaign bans."""


class FakeExecutor:
    """Deterministic in-memory executor for tests. Never runs real replays."""

    def __init__(
        self,
        *,
        fail_keys: set[str] | None = None,
        metrics_factory: Any = None,
    ) -> None:
        self.calls: list[RunEnvelope] = []
        self.fail_keys = set(fail_keys or set())
        self.metrics_factory = metrics_factory

    def execute(self, envelope: RunEnvelope) -> RunResult:
        self.calls.append(envelope)
        required = (
            "run_key",
            "campaign_id",
            "manifest_fingerprint",
            "execution_sha",
            "window_id",
            "strategy_id",
            "parameters",
            "slot_id",
            "phase",
            "label",
            "physical_parameter_set_fingerprint",
            "effective_config_fingerprint",
            "dataset_content_fingerprint",
            "seed",
            "output_dir",
        )
        missing = [
            k for k in required if not getattr(envelope, k, None) and k != "parameters"
        ]
        if envelope.parameters is None:
            missing.append("parameters")
        if missing:
            return RunResult(exit_code=2, detail=f"incomplete envelope: {missing}")
        if envelope.run_key in self.fail_keys:
            return RunResult(exit_code=1, detail="injected failure", metrics={})
        if self.metrics_factory is not None:
            metrics = dict(self.metrics_factory(envelope))
        else:
            metrics = {
                "gate_reason": "OK",
                "regime_distribution": {"TREND": 1},
                "trade_count": 0,
                "turnover": "0",
                "fees": "0",
                "spread": "0",
                "slippage": "0",
                "gross_pnl": "0",
                "net_pnl": "0",
                "profit_factor": "0",
                "expectancy": "0",
                "drawdown": "0",
                "main_effect": None,
                "interaction_effect": None,
                "overfitting_risk_flag": False,
            }
        return RunResult(exit_code=0, metrics=metrics, detail="fake_ok")


class RefusingRealExecutor:
    """Explicit refuse adapter (tests / emergency hold). Prefer StrategyReplayCampaignExecutor."""

    def execute(self, envelope: RunEnvelope) -> RunResult:
        raise RuntimeError(
            "REAL_REPLAY_EXECUTOR_DISABLED_IN_EXECUTION_CONTRACT_SLICE: "
            f"refused run_key={envelope.run_key}"
        )


ReplayInvoker = Callable[[Any], int]
MetricsLoader = Callable[[Path], dict[str, Any]]


def _default_metrics_loader(output_dir: Path) -> dict[str, Any]:
    """Best-effort metrics extraction from strategy_replay_runner artifacts."""
    metrics: dict[str, Any] = {
        "gate_reason": "OK",
        "regime_distribution": {},
        "trade_count": 0,
        "turnover": "0",
        "fees": "0",
        "spread": "0",
        "slippage": "0",
        "gross_pnl": "0",
        "net_pnl": "0",
        "profit_factor": "0",
        "expectancy": "0",
        "drawdown": "0",
        "main_effect": None,
        "interaction_effect": None,
        "overfitting_risk_flag": False,
    }
    candidates = sorted(output_dir.rglob("*_metrics.json"))
    if not candidates:
        summary = output_dir / "scenario_comparison_summary.md"
        if summary.exists():
            metrics["gate_reason"] = "ARTIFACTS_PRESENT_NO_METRICS_JSON"
        return metrics
    try:
        payload = json.loads(candidates[0].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return metrics
    if not isinstance(payload, dict):
        return metrics
    for key in list(metrics.keys()):
        if key in payload:
            metrics[key] = payload[key]
    return metrics


class StrategyReplayCampaignExecutor:
    """Real replay adapter: maps a bound RunEnvelope to ARVPReplayConfig.

    Invokes ``services.validation.strategy_replay_runner.run_arvp_replay`` with
    ``dataset_source=binance_window`` and envelope parameters. Does not touch
    paper supervisors, exchange APIs, or order paths.

    Execution remains blocked upstream without a live-verified Owner-GO.
    """

    def __init__(
        self,
        *,
        replay_invoker: ReplayInvoker | None = None,
        metrics_loader: MetricsLoader | None = None,
        adapter_id: str = DEFAULT_ADAPTER_ID,
        symbol: str = DEFAULT_SYMBOL,
        speedup_profile: str = DEFAULT_SPEEDUP,
    ) -> None:
        self._replay_invoker = replay_invoker
        self._metrics_loader = metrics_loader or _default_metrics_loader
        self._adapter_id = adapter_id
        self._symbol = symbol
        self._speedup_profile = speedup_profile
        self.calls: list[RunEnvelope] = []
        self.last_config: Any | None = None

    def _resolve_invoker(self) -> ReplayInvoker:
        if self._replay_invoker is not None:
            return self._replay_invoker
        from services.validation.strategy_replay_runner import (  # lazy
            run_arvp_replay,
        )

        return run_arvp_replay

    def build_replay_config(self, envelope: RunEnvelope) -> Any:
        """Build ARVPReplayConfig from a fully bound RunEnvelope (no loose overrides)."""
        if envelope.strategy_id != "primary_breakout_v1":
            raise ValueError(f"EXECUTOR_STRATEGY_UNSUPPORTED:{envelope.strategy_id}")
        if not envelope.authorization_fingerprint:
            raise ValueError("EXECUTOR_AUTHORIZATION_FINGERPRINT_REQUIRED")
        if not envelope.window_id or ".." in envelope.window_id:
            raise ValueError("EXECUTOR_WINDOW_ID_INVALID")
        params = dict(envelope.parameters or {})
        missing = [k for k in REQUIRED_PARAM_KEYS if k not in params]
        if missing:
            raise ValueError(f"EXECUTOR_PARAMETERS_INCOMPLETE:{missing}")
        # Reject unknown parameter keys (no loose config injection).
        unexpected = sorted(set(params) - ALLOWED_PARAM_KEYS)
        if unexpected:
            raise ValueError(f"EXECUTOR_PARAMETERS_UNEXPECTED:{unexpected}")
        if params.get("strategy_id") not in (None, "primary_breakout_v1"):
            raise ValueError(
                f"EXECUTOR_STRATEGY_PARAM_MISMATCH:{params.get('strategy_id')}"
            )

        from services.validation.strategy_replay_runner import ARVPReplayConfig

        output_dir = Path(envelope.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        # Persist the bound envelope beside the run for audit/repro.
        bound_path = output_dir / "bound_run_envelope.json"
        bound_path.write_text(
            json.dumps(envelope.as_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return ARVPReplayConfig(
            dataset_source="binance_window",
            binance_window_id=str(envelope.window_id),
            strategy_id=str(envelope.strategy_id),
            adapter_id=self._adapter_id,
            symbol=self._symbol,
            speedup_profile=self._speedup_profile,
            output_directory=str(output_dir / "replay"),
            entry_lookback_minutes=int(params["entry_lookback_minutes"]),
            exit_lookback_minutes=int(params["exit_lookback_minutes"]),
            breakout_buffer=float(params["breakout_buffer"]),
            min_minutes_between_entries=int(params["min_minutes_between_entries"]),
            dry_run=False,
            scenario_ids=("baseline",),
            scenario_group_id=f"sensitivity_{envelope.slot_id}",
        )

    def execute(self, envelope: RunEnvelope) -> RunResult:
        self.calls.append(envelope)
        try:
            config = self.build_replay_config(envelope)
        except ValueError as exc:
            return RunResult(exit_code=2, detail=str(exc), metrics={})
        self.last_config = config
        invoker = self._resolve_invoker()
        try:
            exit_code = int(invoker(config))
        except Exception as exc:  # noqa: BLE001 — map to fail-closed run result
            return RunResult(
                exit_code=2,
                detail=f"EXECUTOR_REPLAY_RAISED:{type(exc).__name__}:{exc}",
                metrics={},
            )
        metrics = self._metrics_loader(Path(envelope.output_dir))
        return RunResult(
            exit_code=exit_code,
            metrics=dict(metrics),
            detail="strategy_replay_ok" if exit_code == 0 else "strategy_replay_failed",
        )
