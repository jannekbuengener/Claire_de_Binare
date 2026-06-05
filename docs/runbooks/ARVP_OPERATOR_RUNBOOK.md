# ARVP Operator Runbook

## Purpose / Audience

Operator-taugliche End-to-End-Anleitung fuer ARVP: window selection -> extraction -> replay -> comparison -> calibration -> drift interpretation.

Audience: human operator or session lead who needs the full flow ohne tiefes Code-Diving.

## Hard Safety Boundaries

- ARVP evidence supports spaetere LR-Entscheidungen, authorisiert aber niemals Live-Go oder Echtgeld-Go.
- LR bleibt `NO-GO`.
- `trade-capable` ist Board-/Stage-Fokus, keine Live-Freigabe.
- Keine Runtime-Start-Aktion ohne explizite Human-GO.
- Keine Docker-/Compose-Orchestrierung durch diesen Runbook-Slice.
- Keine DB-Mutation.
- Keine Secrets, DSN-Werte oder Passwoerter in Repo, Issues, PRs oder Logs.
- `POSTGRES_READONLY_PASSWORD_DSN` nur als Env-Var-Name verwenden, nie als Wert.
- `ORDER/FILL`-only ist fuer ARVP nicht ausreichend.
- Comparison-grade braucht `SIGNAL + DECISION + ORDER(paper_) + FILL` mit shared lineage.

## Current ARVP Operating Order

Current repo-backed order:

1. `#2967` readonly setup fuer safe extraction.
2. `#2968` neue paper-prefixed comparison-grade windows produzieren. Human-GO required.
3. `#2969` comparison-grade windows aus `public.correlation_ledger` extrahieren. BLOCKED bis mindestens ein comparison-grade window existiert.
4. `#2971` replay-vs-paper batch compare.
5. `#2973` multi-window drift classification.
6. `#2975` regime scorecards.
7. `#2970` / `#2974` review- und gate-nahe Nachfolgearbeit.

This runbook can start earlier, but it is only execution guidance. It does not clear any gate.

## Inputs and Preconditions

- `strategy_id`: `primary_breakout_v1`
- `symbol`: `BTCUSDT`
- Comparison window: UTC epoch millis `[START_TS_MS, END_TS_MS]`
- Optional filters: `bot_id`, `config_hash`
- Readonly DB access configured outside the repo
- `cdb_readonly` Postgres role exists
- `POSTGRES_READONLY_PASSWORD_DSN` is set in the operator environment
- For runtime work on `#2968`, explicit Human-GO is present

If the window is not comparison-grade, stop before extraction or replay.

## Stage 1: Window selection

Goal: pick a candidate window that is backed by `correlation_ledger` and satisfies the contract.

Selection rules:

- Prefer windows already anchored by repo evidence.
- Prefer windows with known `paper_` ORDER lineage.
- Do not promote `ORDER/FILL` only windows.
- Do not infer comparison-grade from logs or summary tables alone.

Practical checkpoint:

- If the bank only has the pilot `paper_1909_1776991354682`, treat the bank as too small for batch work.
- If no comparison-grade window exists, `#2969` stays blocked.

## Stage 2: Paper reference extraction

Goal: extract a `paper_reference_window.v1` artifact from `public.correlation_ledger`.

Command template:

```bash
python -m services.validation.paper_reference_window_runner \
  --strategy-id primary_breakout_v1 \
  --symbol BTCUSDT \
  --start-ts-ms <START_TS_MS> \
  --end-ts-ms <END_TS_MS> \
  --bot-id <OPTIONAL_BOT_ID> \
  --config-hash <OPTIONAL_CONFIG_HASH> \
  --extracted-by paper_reference_window_runner
```

What the runner does:

- verifies `POSTGRES_READONLY_PASSWORD_DSN`
- verifies `current_user` and `session_user` are `cdb_readonly`
- verifies SELECT-only access on `public.correlation_ledger`
- reads only `correlation_ledger`
- writes `artifacts/paper_reference_windows/paper_reference_window.json`

Interpretation:

- Exit `0`: extraction succeeded.
- Exit `2`: fail-closed validation or contract problem.
- If the runner says the window is unusable, do not force it.

## Stage 3: Replay execution

Goal: produce a deterministic replay artifact for the same logical window.

File-backed replay template:

```bash
python -m services.validation.strategy_replay_runner \
  --dataset-source file \
  --input-candles <PATH_TO_CANDLES_JSON> \
  --strategy-id primary_breakout_v1 \
  --symbol BTCUSDT \
  --adapter-id primary_breakout_runner_v1 \
  --output-dir artifacts/replay_reports \
  --deterministic-verify
```

DB-backed replay template:

```bash
python -m services.validation.strategy_replay_runner \
  --dataset-source db \
  --db-dataset-window <START_TS_MS>:<END_TS_MS> \
  --strategy-id primary_breakout_v1 \
  --symbol BTCUSDT \
  --adapter-id primary_breakout_runner_v1 \
  --output-dir artifacts/replay_reports \
  --deterministic-verify
```

Operator notes:

- Use `--dry-run` only for config syntax checks.
- Use the same logical window as the extracted paper reference.
- Do not mix symbols or strategy IDs.

## Stage 4: Replay-vs-paper comparison

Goal: compare replay output against the extracted paper reference.

Command template:

```bash
python -m services.validation.replay_vs_paper_compare_runner \
  --replay-report artifacts/replay_reports/<RUN_ID>/report.json \
  --paper-reference artifacts/paper_reference_windows/paper_reference_window.json \
  --output-dir artifacts/replay_vs_paper_compare
```

Expected outputs:

- `shadow_comparison.json`
- `shadow_comparison_summary.md`

Interpretation:

- `aligned` means the pair is usable for downstream calibration.
- `unusable` means the comparison is not fit for calibration; stop and classify the gap.

## Stage 5: Calibration report

Goal: turn an aligned comparison into a calibration artifact.

Command template:

```bash
python -m services.validation.simulator_calibration_report_runner \
  --comparison artifacts/replay_vs_paper_compare/<RUN_ID>/shadow_comparison.json \
  --output-dir artifacts/simulator_calibration
```

Expected outputs:

- `simulator_calibration_report.json`
- `simulator_calibration_summary.md`

Interpretation:

- Use the report to classify drift.
- Do not inflate a single window into a multi-window conclusion.
- If the report is unusable, keep the classification at HOLD.

## Stage 6: Regime scorecards

Goal: produce regime scorecards for the replay run, optionally enriched by comparison data.

Command template:

```bash
python -m services.validation.arvp_regime_scorecard_runner \
  --run-id <RUN_ID> \
  --replay-trace <PATH_TO_REPLAY_TRACE_JSON> \
  --comparison artifacts/replay_vs_paper_compare/<RUN_ID>/shadow_comparison.json \
  --output-dir artifacts/arvp_regime_scorecards
```

Operator notes:

- Point `--replay-trace` at the replay trace JSON emitted by the replay pipeline.
- Do not pass `report.json`; that schema is not accepted by the scorecard runner.
- `--comparison` is optional and only suitable when the JSON already contains regime segments.

Interpretation:

- `status=ok` or `status=insufficient-data` is still an artifact.
- `status=unavailable` means the run did not expose usable regime segments.
- Do not invent regime segmentation where the data does not support it.

## Stage 7: Drift interpretation

Drift labels to use:

- `simulator_optimistic`
- `simulator_pessimistic`
- `timing_delta`
- `execution_semantics_gap`
- `missing_data`

How to read the chain:

- Window selection failed: no comparison-grade candidate exists.
- Extraction failed: the window does not satisfy the paper-reference contract.
- Replay failed: fix the replay input or dataset scope.
- Comparison unusable: the replay/paper pair is not a valid calibration basis.
- Calibration unusable: no honest drift classification can be made yet.
- Regime unavailable: the window does not carry enough regime signal.

## Stop Rules

- Stop if `#2968` lacks explicit Human-GO.
- Stop if `#2969` is being treated as unblocked without a comparison-grade window.
- Stop if the candidate is `ORDER/FILL` only.
- Stop if `paper_` order lineage is missing.
- Stop if `POSTGRES_READONLY_PASSWORD_DSN` is missing or malformed.
- Stop if the runner identity check is not `cdb_readonly`.
- Stop if replay/comparison output is unusable.
- Stop if any step implies Live-Go or Echtgeld-Go.

## Artifact Checklist

- `artifacts/paper_reference_windows/paper_reference_window.json`
- `artifacts/replay_reports/<RUN_ID>/report.json`
- `artifacts/replay_reports/<RUN_ID>/manifest.json`
- `artifacts/replay_reports/<RUN_ID>/audit.log`
- `artifacts/replay_vs_paper_compare/<RUN_ID>/shadow_comparison.json`
- `artifacts/replay_vs_paper_compare/<RUN_ID>/shadow_comparison_summary.md`
- `artifacts/simulator_calibration/<RUN_ID>/simulator_calibration_report.json`
- `artifacts/simulator_calibration/<RUN_ID>/simulator_calibration_summary.md`
- `artifacts/arvp_regime_scorecards/<RUN_ID>/arvp_regime_scorecard.json`
- `artifacts/arvp_regime_scorecards/<RUN_ID>/arvp_regime_scorecard_summary.md`

## Failure / HOLD Classification

| Class | Meaning |
|---|---|
| `HOLD_MISSING_COMPARISON_GRADE_WINDOWS` | No valid comparison-grade window bank yet. |
| `HOLD_RUNNER_FAIL` | Readonly extraction runner failed fail-closed. |
| `HOLD_REPLAY_UNUSABLE` | Replay output cannot be compared honestly. |
| `HOLD_COMPARISON_UNUSABLE` | Replay-vs-paper comparison is not usable. |
| `HOLD_CALIBRATION_UNUSABLE` | Drift cannot be classified from the current pair. |
| `HOLD_REGIME_UNAVAILABLE` | Regime data is not rich enough for a scorecard conclusion. |
| `BLOCKED_HUMAN_GO` | Runtime work needs explicit Human-GO. |
| `BLOCKED_LR` | Any path that implies Live-Go or Echtgeld-Go is blocked. |

## What this runbook does not authorize

- Live-Go
- Echtgeld-Go
- LR upgrade claims
- Docker start/stop
- DB mutation
- Secrets exposure
- Automatic closure of `#2968` or `#2969`

## References

- `docs/roadmaps/ARVP_TO_LIVE_GO_ROADMAP_2026-06.md`
- `docs/governance/arvp_platform.md`
- `docs/governance/arvp_paper_reference_contract.md`
- `docs/evidence/arvp_window_bank_2961_extraction_2026-06-04.md`
- `docs/evidence/arvp_2961_paper_window_runtime_preflight_2026-06-04.md`
- `services/validation/paper_reference_window_runner.py`
- `services/validation/strategy_replay_runner.py`
- `services/validation/replay_vs_paper_compare_runner.py`
- `services/validation/simulator_calibration_report_runner.py`
- `services/validation/arvp_regime_scorecard_runner.py`
