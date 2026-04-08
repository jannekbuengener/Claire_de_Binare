# Codex Batch 03 Ideas (2025-12-31)
Scope:
- Focus on issues enabling 72h test readiness for a single-session engine validation.

Plan (ordered):
- #356 contracts -> #354 deterministic E2E path -> #230 guard cases -> #224 order_results -> #355 CI back to green -> #172 72h validation gate.

Notes:
- Existing branches for #356/#354/#355/#230 must remain; sync with origin/main to reduce drift.
- CI verification is blocked by #413 (Actions billing); treat as external dependency.
- Drawdown guard needs deterministic equity updates from order_results.
