## ISSUE 9 — [P2][SIM] Mock Exchange / Execution Simulator (market-like feedback without real market)
Labels: prio:p2, type:sim
Scope:
- Local service or module that mimics exchange API semantics
Description:
- Accept orders; simulate fills/rejects/partial fills/latency/rate limits; deterministic seed mode.
Acceptance Criteria:
- Scenarios: full fill, partial fill, reject, timeout, rate limit, delayed fill
- Deterministic mode (seed) + chaos mode
- Produces order_result events compatible with execution/risk pipeline
Dependencies:
- Enables stronger chaos drills later

---
