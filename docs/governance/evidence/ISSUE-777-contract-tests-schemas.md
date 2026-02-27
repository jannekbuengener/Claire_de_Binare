# Evidence Spec for Issue #777 — LR-002 Contract Tests for all Redis/Event Schemas
Purpose:
- Define a docs-only evidence target for LR-002 so contract-test evidence can be collected consistently once implementation work lands.
- Capture what counts as proof for schema contract coverage and backward-compatibility checks.

Pass criteria:
- [ ] At least one implementation PR is linked that adds or updates contract tests for Redis/Event schemas in LR-002 scope.
- [ ] At least one CI run is linked showing contract tests or equivalent schema validation checks executing.
- [ ] At least one docs/spec reference is linked that describes schema contracts, payload fixtures, or compatibility expectations.

Evidence plan:
- Expected PR(s): LR-002 contract-test PR(s) or equivalent schema validation PR(s) referencing #777.
- Expected CI runs: workflow runs for test/contract/schema validation jobs on the implementation PR(s).
- Expected docs/ADRs: schema docs, payload contract docs, fixture documentation, or ADRs for contract testing strategy.

Current status:
- Spec only (no implementation evidence yet). Date: 2026-02-24
