# ARVP P2 Test Map

Scope: Issue #3824 (parent #3820).

Machine-readable map:

- `.github/control-plane/generated/agent-arvp-test-map.json`
- Contract: `tests/unit/arvp/test_arvp_test_map_contract.py`

The map links **behavior → service → test → fixture** for the seven required
meta-child surfaces:

- runtime_chain
- replay_paper_calibration
- campaign_supervisor
- scenario_packs
- window_qualification
- evidence_mapping
- negative_controls

Guards:

- `coverage: partial` — no complete-coverage claim
- `known_unmapped_arvp_surfaces` lists probe layer, github reporter, and
  natural-paper observation gaps
- missing mappings are explicit findings in contract tests

LR remains **NO-GO**.
