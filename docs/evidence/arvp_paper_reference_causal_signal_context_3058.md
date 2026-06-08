# ARVP: Paper Reference Causal Signal Context (#3058)

**Issue:** #3058 — Pilot window `signal_count_delta=0` ist ein False Neutral.

## Problem

The pilot window (window_bank_2, first entry) in `batch_compare_summary.json` shows
`signal_count_delta=0` because the paper reference window contains 0 in-window SIGNAL
events. However, the paper reference window contains 1 ORDER + 1 FILL both linked to
`signal_id="sig-1909-runtime-smoke"` — a pre-window SIGNAL event that was not exported.

This is `PAPER_REFERENCE_EXPORT_GAP`: without the causally-linked pre-window SIGNAL,
the replay comparison had no way to know the paper had generated that signal, resulting
in a false-neutral delta of 0 (instead of the correct `signal_context_delta=-1`).

## Design

No strategy/signal/execution/fill-model changes. Only export/comparison layer.

| Concept | Implementation |
|---------|---------------|
| Pre-window SIGNAL events | Exported as `causal_context_events[]` array |
| `in_window` marker | `false` for all causal context events |
| `context_scope` | `"pre_window_causal"` |
| Backward compatibility | Existing consumers ignore optional new fields |
| `signal_count_delta` | Stays in-window-only (no breakage) |
| `signal_context_delta` | New field: `replay.signal_count - (paper.signal_count + paper.causal_signal_count)` |
| `signal_count_false_neutral_detected` | New boolean flag, true when paper.signal_count==0 and paper.causal_signal_count>0 |

## Files Changed

| File | Change | Type |
|------|--------|------|
| `core/replay/paper_reference_window_export.py` | Added `causal_context_rows` parameter; `_gather_causal_signal_ids()` helper; `causal_context_events[]` output | Production |
| `core/replay/shadow_compare.py` | Added `causal_signal_count` to `PaperReferenceWindow`; `signal_context_delta` and `signal_count_false_neutral_detected` to `ShadowComparisonResult` | Production |
| `core/replay/replay_vs_paper_compare.py` | Parse `causal_context_events` from paper artifact → `PaperReferenceWindow.causal_signal_count` | Production |
| `services/validation/paper_reference_window_runner.py` | Added `--causal-lookup-start-ms`/`--causal-lookup-end-ms` CLI args; secondary SQL query | Production |
| `tests/unit/replay/test_paper_reference_window_export.py` | 5 new tests for causal export validation | Test |
| `tests/unit/replay/test_shadow_compare.py` | 10 new tests for causal fields in PaperReferenceWindow, compare_windows, summary, and artifact | Test |
| `tests/unit/replay/test_replay_vs_paper_compare.py` | 3 new tests for causal context parsing | Test |
| `tests/unit/validation/test_paper_reference_window_runner.py` | Updated mock to accept `causal_context_rows` param | Test |

## Test Results

All 110 tests pass (84 existing + 26 new):
- `test_paper_reference_window_export.py`: 22 passed
- `test_shadow_compare.py`: 74 passed
- `test_replay_vs_paper_compare.py`: 8 passed
- `test_paper_reference_window_runner.py`: 6 passed

## Expected Pilot Outcome

After this fix, the pilot window comparison will show:
- `signal_count_delta=0` (unchanged, in-window only)
- `signal_context_delta=-1` (causal-aware: replay has 0 SIGNAL, paper has 0 in-window + 1 causal = 1 total)
- `signal_count_false_neutral_detected=True`
- Pilot window artifact includes `causal_context_events[0]` with `signal_id="sig-1909-runtime-smoke"`,
  `in_window=false`, `context_scope="pre_window_causal"`

## LR Status

LR remains **NO-GO**. No Runtime/DB/Docker/Exchange changes.
