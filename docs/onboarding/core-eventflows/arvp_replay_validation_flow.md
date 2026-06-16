# ARVP Replay and Replay-vs-Paper Validation Flow

## Status

Docs-only onboarding artifact. Visual orientation — not authoritative.

## Parent / Issue Refs

- Parent: [#3253 Core-System Eventflow Map Pack](https://github.com/jannekbuengener/Claire_de_Binare/issues/3253)
- Issue: [#3260 Map ARVP Replay and Replay-vs-Paper Validation Flow](https://github.com/jannekbuengener/Claire_de_Binare/issues/3260)

## Purpose

Show the ARVP (Automated Replay Validation Pipeline) flow: from dataset acquisition through deterministic replay, replay-vs-paper comparison, calibration reports, regime scorecards, and finally the ARVP Gate verdict. ARVP is CDB's primary validation mechanism — it produces evidence, not approvals.

## Mermaid Diagram

See [`diagrams/arvp_replay_validation_flow.mmd`](diagrams/arvp_replay_validation_flow.mmd) for the source file.

```mermaid
flowchart TD
    subgraph Dataset["Dataset Layer"]
        DS[Dataset Source<br/>file | db]
        DP[DatasetProvider<br/>FileBacked | DBBacked]
        DQ[DatasetSpec<br/>fingerprint, window]
    end
    subgraph Replay["Replay Execution"]
        HB[Historical Bridge<br/>file-backed historical input]
        SR[Strategy Replay Runner<br/>strategy_backtest_runner.py]
        SC[Scheduler<br/>event-time, speed profiles]
        RR[Replay Reporter<br/>report.json, manifest, audit.log]
    end
    subgraph Compare["Replay-vs-Paper Compare"]
        RC[Replay vs Paper Compare<br/>replay_vs_paper_compare.py]
        SCMP[Shadow Comparison<br/>shadow_comparison.json]
        CR[Calibration Report<br/>simulator_calibration_report.json]
    end
    subgraph Evidence["Evidence / Gate"]
        RS[Regime Scorecards<br/>arvp_regime_scorecard.json]
        AG[ARVP Gate Verdict<br/>pass / fail / blocked]
    end
    DS --> DP
    DP --> DQ
    DQ --> HB
    HB --> SR
    SC --> SR
    SR --> RR
    RR --> RC
    RC --> SCMP
    SCMP --> CR
    RC --> RS
    RS --> AG
    SCMP --> AG
    CR --> AG
```

## What New Developers Must Understand

1. **ARVP is evidence, not release authorization.** A passing ARVP gate means the replay evidence is consistent. It does not authorize paper promotion, live trading, or any operational change.
2. **Replay is offline/validation, not runtime.** Replay runs use historical data and deterministic schedulers. They do not touch Redis, live services, or any runtime component.
3. **Dataset quality is a precondition.** Garbage in, garbage out. The DatasetSpec and DatasetProvider layers validate ordering, tick cadence, and required fields before any replay starts.
4. **Drift must be visible.** Replay-vs-Paper Compare, Calibration Reports, and Regime Scorecards are designed to surface drift between simulated and paper execution. If drift exceeds thresholds, the ARVP gate blocks.
5. **Two dataset sources exist.** File-based (JSON/JSONL) for local validation and DB-based (Postgres `candles_1m`) for production replay. They are mutually exclusive per run.

## Source of Truth / Primary Repo Sources

- [`knowledge/ARCHITECTURE_MAP.md`](../../knowledge/ARCHITECTURE_MAP.md) — Core replay infrastructure, DatasetSpec, DatasetProvider, ARVP gate, comparison tools
- [`core/replay/`](../../core/replay/) — Replay contracts, deterministic loop, envelopes, scheduler, comparison, calibration
- [`services/validation/`](../../services/validation/) — CLI runners for replay, comparison, calibration, scorecards

## Safety Boundaries

- Replay is fully offline. It has no network, Redis, or PostgreSQL access during execution.
- ARVP Gate verdicts are machine-readable but require human interpretation for any promotion decision.
- All replay artifacts are deterministic and fingerprintable.
- Replay never creates or modifies trading state.

## Non-Goals

- Not a strategy validation methodology document
- Not a dataset curation guide
- Not a replacement for operator review of replay results

## Common Failure Modes / Onboarding Traps

| Trap | Reality |
|------|---------|
| Expecting replay to match paper exactly | Replay and paper have different execution contexts. Drift is expected; the question is whether drift is within acceptable thresholds. |
| Assuming dataset file = dataset db equivalence | File-backed and DB-backed datasets may have different timestamps, ordering, or completeness. Always verify source alignment before comparison. |
| Treating ARVP pass as paper promotion approval | ARVP validates replay consistency. Paper promotion requires additional gates, evidence, and human approval. |

## LR NO-GO / Kein Live-Go / Kein Echtgeld-Go

LR remains NO-GO ([`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md)).
Board stage `trade-capable` is not Live-Go.
No Echtgeld-Go.
