# Replay-vs-Paper Comparison Summary

Status:           aligned
Replay run:       replay-8049a7afc831-0001
Paper reference:  paper_reference_window_runner@2026-04-27T20:16:53.967407+00:00
Symbol:           BTCUSDT
Strategy:         primary_breakout_v1
Fingerprint:      a0bf77b41e5adec14b079e7c40a430627f970c7c3c10eb2e1ed09262edd22b04

## Window Alignment
Replay:  2026-04-24T00:42:00+00:00 – 2026-04-24T00:43:00+00:00
Paper:   2026-04-24T00:42:00+00:00 – 2026-04-24T00:43:00+00:00

## Count Deltas (replay − paper)
Signal count delta (in-window):  +0
Signal context delta (causal):   -1
Order count delta:               -1
Fill count delta:                -1
Reject delta:        only available when explicit reject data exists.
Unfilled order delta: informational proxy, not treated as reject evidence.
Unfilled order delta: +0


## Signal False Neutral
signal_count_delta=0 is a false neutral — paper had causal pre-window
SIGNAL events that are not visible in the in-window count.
causal_signal_count on paper side: paper_reference_window_runner@2026-04-27T20:16:53.967407+00:00 not directly available here.