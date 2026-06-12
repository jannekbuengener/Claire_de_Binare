# Evidence Class Contract — #3096

**Status:** Canonical
**Scope:** ARVP evidence artifact classification and enforcement
**Design Source:** #3094 `docs/evidence/arvp_deterministic_window_production_3094.md`
**Controlled-Lab Path:** #3127 `docs/evidence/arvp_controlled_lab_evidence_path_3127.md`
**Issue:** #3096

---

## 1. Purpose

Define the four canonical evidence classes, their required metadata, warning banners, and fail-closed enforcement rules for all ARVP evidence artifacts produced or validated by repo surfaces.

---

## 2. Valid Evidence Classes

| ID | Label | Definition | §5.2.4 Gate? | Contract/Proof? | Warning Banner |
|----|-------|-----------|-------------|-----------------|----------------|
| `natural_paper_evidence` | Real paper runtime output under natural market conditions | Paper reference windows produced via real strategy/execution path against live market data; MOCK_TRADING=true, no stimulus, no parameter hack | **Yes** | Yes | *(none — highest class)* |
| `controlled_lab_evidence` | Scenario-backed deterministic evidence from historical or pre-built data packs | Regime scorecards or pipeline artifacts produced from curated scenario packs with known inputs; no real market dependency | **No** | Yes | `⚠ NOT natural_paper_evidence — cannot satisfy §5.2.4` |
| `pipeline_test_evidence` | Synthetic stimulus or fixture-driven pipeline validation | Output from `paper_runtime_stimulus_runner.py` or similar fixture-based runners; proves pipeline works, not that products are complete | **No** | Yes (for pipeline) | `⚠ Pipeline test only — NOT valid for Product-Complete gate` |
| `waiver_decision` | Explicit policy decision accepting non-fulfillment of a gate criterion | Documented governance decision; must list residual uncertainties and mandatory follow-ups | **Only with formal governance vote** | N/A | `⚠ Policy decision — not evidence; requires formal governance vote` |

## 3. Required Metadata

Every ARVP evidence artifact MUST carry at minimum:

```json
{
  "evidence_class": "<one of the 4 valid values>",
  "evidence_class_version": "1.0",
  "produced_by": "<runner-id or tool-name>",
  "produced_at_utc": "<ISO-8601 UTC>"
}
```

### Per-class requirements

| Class | Additional Required Fields |
|-------|---------------------------|
| `natural_paper_evidence` | `campaign_id`, `start_criterion`, `safety_flags` (mock_trading, dry_run, mexc_testnet), `provenance` |
| `controlled_lab_evidence` | `warning_banner` (exact text from §2), `scenario_source`, `reproducibility_contract` |
| `pipeline_test_evidence` | `warning_banner` (exact text from §2), `pipeline_tool`, `fixture_source` |
| `waiver_decision` | `warning_banner` (exact text from §2), `governance_ref`, `residual_uncertainties` |

## 4. Enforcement Rules

1. **Every** ARVP evidence artifact produced or validated by touched surfaces MUST carry exactly one `evidence_class`.

2. `controlled_lab_evidence` REQUIRES the exact warning banner: `⚠ NOT natural_paper_evidence — cannot satisfy §5.2.4`.

3. `pipeline_test_evidence` REQUIRES the exact warning banner: `⚠ Pipeline test only — NOT valid for Product-Complete gate`.

4. `waiver_decision` REQUIRES the exact warning banner: `⚠ Policy decision — not evidence; requires formal governance vote`.

5. **No silent class upgrade.** An artifact labeled `pipeline_test_evidence` can NEVER be interpreted as `natural_paper_evidence` by omission or relabeling.

6. **No missing evidence_class.** Artifacts without `evidence_class` are REJECTED by validation.

7. **No unknown evidence_class.** Any value outside the 4 valid classes is REJECTED by validation.

8. **Fail-closed on missing/unknown.** Validation MUST return a non-zero exit code or raise an exception — never silently pass.

## 5. Runner Labeling

| Runner | Default Evidence Class | Notes |
|--------|----------------------|-------|
| `paper_runtime_stimulus_runner.py` | `pipeline_test_evidence` | Output is synthetic fixture-based, NOT natural paper evidence |
| `paper_reference_window_runner.py` | `natural_paper_evidence` (when chain detected) | Window exported from real correlation_ledger events |
| `arvp_regime_scorecard_runner.py` | Configurable via `--evidence-class` | Must match the input trace/input source class |
| `arvp_chain_detector.py` | `natural_paper_evidence` (on complete chain) | Hard-coded in export trigger — only fires on real chain |

## 6. Safety Boundaries

| Boundary | Status |
|----------|--------|
| LR remains **NO-GO** | Confirmed |
| `controlled_lab_evidence` cannot close #3087 | Confirmed |
| `controlled_lab_evidence` cannot satisfy §5.2.4 | Confirmed |
| `pipeline_test_evidence` is NOT Product-Complete evidence | Confirmed |
| Board stage `trade-capable` is NOT Live-Go | Confirmed |
| No silent class upgrade | Enforced |
| No missing `evidence_class` | Enforced |
| No unknown `evidence_class` | Enforced |
| Product-Complete remains blocked unless `natural_paper_evidence` or formal waiver exists | Confirmed |

---

## 7. References

- #3096 — This enforcement issue
- #3094 — Evidence class definitions (design source)
- #3127 — Controlled-lab evidence path design
- #3087 — Natural-chain blocker (remains OPEN/BLOCKED)
- #2974 — Product-Complete review (§5.2.4 BLOCKED)
- `docs/evidence/arvp_deterministic_window_production_3094.md`
- `docs/evidence/arvp_controlled_lab_evidence_path_3127.md`
- `docs/evidence/arvp_option_e_waiver_split_decision_3087_3095.md`
