# Evidence Spec for Issue #748 — Policy Snapshot Binding: policy hash/version in ledger events
Purpose:
- Define a docs-only evidence contract for how implementation proof for policy snapshot binding should be collected and linked in Issue #748.
- Ensure future implementation work can add auditable evidence without changing the issue structure again.

Pass criteria:
- [ ] At least one implementation PR is linked that introduces or updates `policy_id` / hash / version binding for relevant events.
- [ ] At least one CI run or validation run is linked and attributable to the implementation PR(s).
- [ ] At least one spec/ADR/docs reference is linked that documents the intended binding behavior and compatibility expectations.

Evidence plan:
- Expected PR(s): policy snapshot binding implementation PR(s) referencing #748.
- Expected CI runs: workflow runs validating tests/linting for the implementation PR(s), plus any focused validation job if present.
- Expected docs/ADRs: spec/ADR/docs that describe policy hash/version binding, anti-drift intent, and event/ledger linkage.

Current status:
- Spec only (no implementation evidence yet). Date: 2026-02-24
