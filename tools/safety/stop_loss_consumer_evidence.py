"""Generate stop-loss consumer dedup evidence (Issue #4186).

Executes the protection scenarios against the real library code in a temporary
directory and writes a machine-readable evidence manifest. The manifest is not a
transcript of test names: every scenario status comes from an actual consumer
run in this process.

Usage:
    python -m tools.safety.stop_loss_consumer_evidence \
        --output docs/evidence/risk/4186_stop_loss_consumer_dedup.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Callable, Optional

from core.safety.stop_loss import (
    DEDUP_STATE_SCHEMA_VERSION,
    EXIT_INTENT_SCHEMA_VERSION,
    SHADOW_REPORT_SCHEMA_VERSION,
    STOP_LOSS_TRIGGER_CONTRACT_VERSION,
    DedupRecordState,
    DisabledProductiveExitAdapter,
    FileStopLossDedupStore,
    PositionSide,
    PositionSnapshot,
    PriceObservation,
    RecordingExitIntentSink,
    StopLossConsumeDecision,
    StopLossConsumer,
    StopLossReason,
    StopLossTriggerConfig,
    candle_observations,
    run_stop_loss_shadow,
)
from core.safety.stop_loss_protection import (
    STOP_LOSS_PROTECTION_EVIDENCE,
    STOP_LOSS_PROTECTION_STATUS,
    stop_loss_protection_evidence_gaps,
)
from core.utils.clock import utcnow

EVIDENCE_SCHEMA_VERSION = "cdb-stop-loss-consumer-evidence/v1"

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FIXTURE = _REPO_ROOT / "tests" / "fixtures" / "stop_loss_shadow_candles.json"

NOW_MS = 1_800_000_400_000


@dataclass(frozen=True)
class ScenarioResult:
    """Outcome of one executed protection scenario."""

    scenario_id: str
    title: str
    expected: str
    observed: str
    intents_emitted: int
    status: str

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "expected": self.expected,
            "observed": self.observed,
            "intents_emitted": self.intents_emitted,
            "status": self.status,
        }


def _position() -> PositionSnapshot:
    return PositionSnapshot(
        symbol="BTCUSDT",
        side=PositionSide.LONG,
        quantity=Decimal("0.5"),
        entry_price=Decimal("100.00"),
        position_id="pos-4186-evidence-1",
        opened_at_ms=NOW_MS - 300_000,
    )


def _observation(
    price: str, *, observed_at_ms: int = NOW_MS - 1_000
) -> PriceObservation:
    return PriceObservation(
        symbol="BTCUSDT",
        price=Decimal(price),
        observed_at_ms=observed_at_ms,
        source="evidence.market_state:BTCUSDT",
    )


def _config() -> StopLossTriggerConfig:
    return StopLossTriggerConfig(stop_loss_pct=Decimal("0.02"))


def _consumer(store, sink) -> StopLossConsumer:
    return StopLossConsumer(
        store=store, sink=sink, config=_config(), clock_ms=lambda: NOW_MS
    )


def _initialized_store(workdir: Path, name: str) -> FileStopLossDedupStore:
    store = FileStopLossDedupStore(workdir / f"{name}.json")
    store.initialize()
    return store


def _scenario(
    scenario_id: str,
    title: str,
    expected: str,
    runner: Callable[[Path], tuple[str, int]],
    workdir: Path,
) -> ScenarioResult:
    observed, intents = runner(workdir)
    return ScenarioResult(
        scenario_id=scenario_id,
        title=title,
        expected=expected,
        observed=observed,
        intents_emitted=intents,
        status="PASS" if observed == expected else "FAIL",
    )


def _d1_trigger_to_intent(workdir: Path) -> tuple[str, int]:
    store = _initialized_store(workdir, "d1")
    sink = RecordingExitIntentSink()
    outcome = _consumer(store, sink).consume(_position(), _observation("97.50"))
    return outcome.reason_code, len(sink.intents)


def _d2_double_delivery(workdir: Path) -> tuple[str, int]:
    store = _initialized_store(workdir, "d2")
    sink = RecordingExitIntentSink()
    consumer = _consumer(store, sink)
    consumer.consume(_position(), _observation("97.50"))
    outcome = consumer.consume(_position(), _observation("97.50"))
    return outcome.reason_code, len(sink.intents)


def _d3_restart_after_finalize(workdir: Path) -> tuple[str, int]:
    path = workdir / "d3.json"
    FileStopLossDedupStore(path).initialize()
    first_sink = RecordingExitIntentSink()
    _consumer(FileStopLossDedupStore(path), first_sink).consume(
        _position(), _observation("97.50")
    )
    restarted_sink = RecordingExitIntentSink()
    outcome = _consumer(FileStopLossDedupStore(path), restarted_sink).consume(
        _position(), _observation("97.50")
    )
    return outcome.reason_code, len(first_sink.intents) + len(restarted_sink.intents)


def _d4_restart_between_prepare_and_finalize(workdir: Path) -> tuple[str, int]:
    path = workdir / "d4.json"
    FileStopLossDedupStore(path).initialize()

    class FinalizeCrashStore(FileStopLossDedupStore):
        def finalize(self, record):
            raise RuntimeError("simulated crash before finalize")

    crashed_sink = RecordingExitIntentSink()
    _consumer(FinalizeCrashStore(path), crashed_sink).consume(
        _position(), _observation("97.50")
    )
    stored = FileStopLossDedupStore(path).load(
        json.loads(path.read_text(encoding="utf-8"))["records"].popitem()[0]
    )
    assert stored.state is DedupRecordState.PREPARED

    restarted_sink = RecordingExitIntentSink()
    outcome = _consumer(FileStopLossDedupStore(path), restarted_sink).consume(
        _position(), _observation("97.50")
    )
    return outcome.reason_code, len(crashed_sink.intents) + len(restarted_sink.intents)


def _d5_missing_state(workdir: Path) -> tuple[str, int]:
    store = FileStopLossDedupStore(workdir / "d5_never_initialized.json")
    sink = RecordingExitIntentSink()
    outcome = _consumer(store, sink).consume(_position(), _observation("97.50"))
    return outcome.reason_code, len(sink.intents)


def _d6_corrupt_state(workdir: Path) -> tuple[str, int]:
    path = workdir / "d6.json"
    path.write_text("{ this is not json", encoding="utf-8")
    sink = RecordingExitIntentSink()
    outcome = _consumer(FileStopLossDedupStore(path), sink).consume(
        _position(), _observation("97.50")
    )
    return outcome.reason_code, len(sink.intents)


def _d7_contradictory_state(workdir: Path) -> tuple[str, int]:
    path = workdir / "d7.json"
    FileStopLossDedupStore(path).initialize()
    sink = RecordingExitIntentSink()
    consumer = _consumer(FileStopLossDedupStore(path), sink)
    emitted = consumer.consume(_position(), _observation("97.50"))

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["records"][emitted.event_id]["fingerprint"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")

    outcome = consumer.consume(_position(), _observation("97.50"))
    return outcome.reason_code, len(sink.intents)


def _d8_newer_event_not_swallowed(workdir: Path) -> tuple[str, int]:
    store = _initialized_store(workdir, "d8")
    sink = RecordingExitIntentSink()
    consumer = _consumer(store, sink)
    consumer.consume(_position(), _observation("97.50"))
    reopened = replace(
        _position(),
        position_id="pos-4186-evidence-2",
        opened_at_ms=NOW_MS - 10_000,
        entry_price=Decimal("99.00"),
    )
    outcome = consumer.consume(reopened, _observation("96.00"))
    return outcome.reason_code, len(sink.intents)


def _d9_unknown_position_state(workdir: Path) -> tuple[str, int]:
    store = _initialized_store(workdir, "d9")
    sink = RecordingExitIntentSink()
    unknown = replace(_position(), side=PositionSide.UNKNOWN)
    outcome = _consumer(store, sink).consume(unknown, _observation("97.50"))
    return outcome.reason_code, len(sink.intents)


def _d10_productive_adapter_disabled(workdir: Path) -> tuple[str, int]:
    store = _initialized_store(workdir, "d10")
    sink = DisabledProductiveExitAdapter()
    outcome = _consumer(store, sink).consume(_position(), _observation("97.50"))
    return outcome.reason_code, 0


def _d11_stale_price(workdir: Path) -> tuple[str, int]:
    store = _initialized_store(workdir, "d11")
    sink = RecordingExitIntentSink()
    stale = _observation("97.50", observed_at_ms=NOW_MS - 500_000)
    outcome = _consumer(store, sink).consume(_position(), stale)
    return outcome.reason_code, len(sink.intents)


_SCENARIOS = (
    (
        "D1",
        "Price breach produces one exit intent",
        StopLossReason.EXIT_INTENT_EMITTED,
        _d1_trigger_to_intent,
    ),
    (
        "D2",
        "Double delivery of the same event",
        StopLossReason.DUPLICATE_SUPPRESSED,
        _d2_double_delivery,
    ),
    (
        "D3",
        "Consumer restart after finalize (replay)",
        StopLossReason.DUPLICATE_SUPPRESSED,
        _d3_restart_after_finalize,
    ),
    (
        "D4",
        "Consumer restart between prepare and finalize",
        StopLossReason.PREPARE_INCOMPLETE,
        _d4_restart_between_prepare_and_finalize,
    ),
    (
        "D5",
        "Missing dedup state",
        StopLossReason.DEDUP_STATE_MISSING,
        _d5_missing_state,
    ),
    (
        "D6",
        "Corrupt dedup state",
        StopLossReason.DEDUP_STATE_CORRUPT,
        _d6_corrupt_state,
    ),
    (
        "D7",
        "Contradictory dedup fingerprint",
        StopLossReason.DEDUP_STATE_CONTRADICTORY,
        _d7_contradictory_state,
    ),
    (
        "D8",
        "Newer protection event after reopen",
        StopLossReason.EXIT_INTENT_EMITTED,
        _d8_newer_event_not_swallowed,
    ),
    (
        "D9",
        "Unknown position state",
        StopLossReason.POSITION_STATE_UNKNOWN,
        _d9_unknown_position_state,
    ),
    (
        "D10",
        "Productive exit adapter stays disabled",
        StopLossReason.EXIT_INTENT_SINK_FAILED,
        _d10_productive_adapter_disabled,
    ),
    ("D11", "Stale price observation", StopLossReason.PRICE_STALE, _d11_stale_price),
)


def run_scenarios(workdir: Path) -> list[ScenarioResult]:
    """Execute every protection scenario and return its real outcome."""
    return [
        _scenario(scenario_id, title, expected.value, runner, workdir)
        for scenario_id, title, expected, runner in _SCENARIOS
    ]


def run_shadow_report(workdir: Path) -> dict:
    """Replay the committed candle fixture through the consumer."""
    payload = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    raw_position = payload["position"]
    position = PositionSnapshot(
        symbol=raw_position["symbol"],
        side=PositionSide(raw_position["side"]),
        quantity=Decimal(raw_position["quantity"]),
        entry_price=Decimal(raw_position["entry_price"]),
        position_id=raw_position["position_id"],
        opened_at_ms=raw_position["opened_at_ms"],
    )
    store = _initialized_store(workdir, "shadow")
    report = run_stop_loss_shadow(
        position=position,
        observations=candle_observations(payload["candles"], symbol=position.symbol),
        config=StopLossTriggerConfig(
            stop_loss_pct=Decimal(payload["stop_loss_pct"]),
            max_price_age_ms=payload["max_price_age_ms"],
        ),
        store=store,
        sink=RecordingExitIntentSink(),
        restart_before_indices=tuple(payload.get("shadow_restart_before_indices", ())),
    )
    return report.to_dict()


def _git(*args: str) -> Optional[str]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None


def _commit_sha() -> str:
    """HEAD at generation time — the commit the evidenced code belongs to."""
    head = _git("rev-parse", "HEAD")
    return head.strip() if head is not None else "unknown"


def _worktree_dirty() -> Optional[bool]:
    """True when tracked files differ from HEAD, so ``commit_sha`` is not exact.

    Returns ``None`` when git is unavailable: an unknown dirty state must not be
    reported as clean.
    """
    status = _git("status", "--porcelain", "--untracked-files=no")
    if status is None:
        return None
    return bool(status.strip())


def build_manifest(*, include_timestamp: bool = True) -> dict:
    """Run all scenarios plus the shadow replay and build the evidence manifest."""
    with tempfile.TemporaryDirectory(prefix="cdb-4186-") as tmp:
        workdir = Path(tmp)
        scenarios = run_scenarios(workdir)
        shadow = run_shadow_report(workdir)

    scenario_pass = all(result.status == "PASS" for result in scenarios)
    shadow_pass = (
        shadow["emitted_intent_count"] == 1
        and shadow["unique_emitted_intent_count"] == 1
        and shadow["productive_adapter_enabled"] is False
    )
    verdict = (
        "PASS_CONSUMER_DEDUP_MOCK_SHADOW"
        if scenario_pass and shadow_pass
        else "FAIL_CONSUMER_DEDUP_EVIDENCE"
    )

    manifest = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "issue": 4186,
        "commit_sha": _commit_sha(),
        "worktree_dirty": _worktree_dirty(),
        "verdict": verdict,
        "contract_versions": {
            "trigger": STOP_LOSS_TRIGGER_CONTRACT_VERSION,
            "exit_intent": EXIT_INTENT_SCHEMA_VERSION,
            "dedup_state": DEDUP_STATE_SCHEMA_VERSION,
            "shadow_report": SHADOW_REPORT_SCHEMA_VERSION,
        },
        "stop_loss_protection_status": STOP_LOSS_PROTECTION_STATUS.value,
        "stop_loss_protection_evidence": {
            "trigger_contract_proven": STOP_LOSS_PROTECTION_EVIDENCE.trigger_contract_proven,
            "consumer_proven": STOP_LOSS_PROTECTION_EVIDENCE.consumer_proven,
            "persistent_dedup_proven": STOP_LOSS_PROTECTION_EVIDENCE.persistent_dedup_proven,
            "restart_replay_proven": STOP_LOSS_PROTECTION_EVIDENCE.restart_replay_proven,
            "real_stack_persistence_proven": (
                STOP_LOSS_PROTECTION_EVIDENCE.real_stack_persistence_proven
            ),
            "productive_exit_path_proven": (
                STOP_LOSS_PROTECTION_EVIDENCE.productive_exit_path_proven
            ),
        },
        "stop_loss_protection_evidence_gaps": list(
            stop_loss_protection_evidence_gaps()
        ),
        "scenarios": [result.to_dict() for result in scenarios],
        "shadow_run": shadow,
        "boundaries": {
            "lr_verdict": "NO-GO",
            "live_go": False,
            "echtgeld_go": False,
            "productive_adapter_enabled": False,
            "productive_queue_enabled": False,
            "productive_db_write": False,
            "real_stack_persistence_proven": False,
            "risk_limits_changed": False,
        },
    }
    if include_timestamp:
        manifest["generated_at_utc"] = utcnow().isoformat()
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=_REPO_ROOT
        / "docs"
        / "evidence"
        / "risk"
        / "4186_stop_loss_consumer_dedup.json",
        help="Path of the evidence manifest to write.",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Print the manifest without writing it.",
    )
    args = parser.parse_args(argv)

    manifest = build_manifest()
    rendered = json.dumps(manifest, indent=2, sort_keys=True) + "\n"

    if args.print_only:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"{manifest['verdict']} -> {args.output}")

    return 0 if manifest["verdict"].startswith("PASS") else 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
