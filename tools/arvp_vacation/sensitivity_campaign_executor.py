"""Executor interface + fake executor for #4153 sensitivity campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol


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
    """Production guard: real strategy replay must not be invoked in this slice."""

    def execute(self, envelope: RunEnvelope) -> RunResult:
        raise RuntimeError(
            "REAL_REPLAY_EXECUTOR_DISABLED_IN_EXECUTION_CONTRACT_SLICE: "
            f"refused run_key={envelope.run_key}"
        )
