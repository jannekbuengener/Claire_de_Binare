# Architecture Reconcile Batch (#4012 / #4020 / #4023 / #4026)

**Date:** 2026-07-13  
**Batch issues:** [#4012](https://github.com/jannekbuengener/Claire_de_Binare/issues/4012), [#4020](https://github.com/jannekbuengener/Claire_de_Binare/issues/4020), [#4023](https://github.com/jannekbuengener/Claire_de_Binare/issues/4023), [#4026](https://github.com/jannekbuengener/Claire_de_Binare/issues/4026)  
**LR:** NO-GO

---

## Brain Evidence

| Field | Value |
|---|---|
| brain_source | repo-only |
| brain_status | not-used |
| context_brain_attempted | true |
| context_brain_used | false |
| repo_fallback_reason | insufficient_evidence |
| records_found | none |

Repo/GitHub live evidence used for all classifications and closure proof.

---

## Live baseline

| Item | Value |
|---|---|
| origin/main (batch base) | `5be4b0bc75899d8c464edcea275d780f266cad8a` |
| PR #4028 | MERGED (#4006 hygiene evidence) |
| Issue #4006 | CLOSED |

### Source PRs

| PR | Merge SHA | Trigger surface |
|---|---|---|
| #4011 | `49eb754672efab7c497e681d40e36590a61508cc` | `services/README.md`, README navigation |
| #4018 | `60ddf8b30d472eeabd37f6016b75a985f9aa18aa` | `core/README.md` navigation |
| #4022 | `f9e0cb0a6025d6cb8b5843c68e3e74619f4b48f8` | `arvp_candidate_evidence_assembler.py` |
| #4025 | `f13419acc1cfbb4b65833a86b5f083d255be1e22` | `profitability_league_table_report_assembler.py` |

---

## Befund je Issue

### #4012 — `NO_DRIFT_FALSE_POSITIVE`

- PR #4011 changed README link guards and navigation blocks only.
- Diff on `services/README.md`: relative links + Navigation section; no service topology, ports, data flow, or deployment change.
- **Catalog delta:** none (by design).

### #4020 — `NO_DRIFT_FALSE_POSITIVE`

- PR #4018 changed `core/README.md` navigation and SSOT link formatting only.
- No new core modules, contracts, or runtime behavior.
- **Catalog delta:** none (by design).

### #4023 — `REAL_DRIFT_RECONCILED`

- PR #4022 introduced offline library `services/validation/arvp_candidate_evidence_assembler.py` and CLI `tools/arvp_vacation/candidate_evidence_assembly.py`.
- **Catalog delta:** ARCHITECTURE_MAP + SERVICE_CATALOG rows + validation/vacation README coverage.

### #4026 — `REAL_DRIFT_RECONCILED`

- PR #4025 introduced offline library `services/validation/profitability_league_table_report_assembler.py` and CLI `tools/arvp_vacation/league_table_report.py`.
- Distinct from existing `profitability_league_scorer.py` (Formula v1 scorer CLI without ARVP governance layer).
- **Catalog delta:** ARCHITECTURE_MAP + SERVICE_CATALOG rows + scorer/assembler distinction in READMEs.

---

## Scanner false-positive analysis (#4012 / #4020)

Rule: `architecture_service_catalog_drift` in [`.github/scripts/post_merge_followup_scanner.py`](../../.github/scripts/post_merge_followup_scanner.py).

- Trigger: any change under `services/` or `core/` without simultaneous touch of `knowledge/ARCHITECTURE_MAP.md` or `knowledge/governance/SERVICE_CATALOG.md`.
- Why it fired: README files live under `services/` and `core/` and were classified as service/runtime surfaces.
- Why semantically wrong here: path-prefix rule cannot distinguish navigation-only Markdown from structural architecture changes.
- Follow-up issue recommended for scanner precision (README/navigation-only suppression); not fixed in this batch.

---

## Truth- und Ownership-Matrix

| Komponente | Quelle | Rolle | Inputs | Outputs | Owner | Runtime/Persistenz | Contract |
|---|---|---|---|---|---|---|---|
| Vacation Runner | `tools/arvp_vacation/coordinator.py` | Offline batch orchestration | manifest, datasets | queue_state, job artifacts | ARVP tools | Offline local artifacts | queue/manifest contracts |
| Strategy Metric Extraction | `tools/arvp_vacation/strategy_metric_extraction.py` | Normalize replay metrics | queue_state / job outputs | `arvp_strategy_metrics.v1` | ARVP tools | Offline | `arvp_strategy_metrics.v1` |
| Candidate Evidence Assembler | `services/validation/arvp_candidate_evidence_assembler.py` | Aggregate metrics → PEPs | `arvp_strategy_metrics.v1` | `profitability_evidence_packet.v1` bundle | Validation lib | Offline optional files | `profitability_evidence_packet.v1` |
| League Table Report Assembler | `services/validation/profitability_league_table_report_assembler.py` | Governance-safe comparison table | PEP bundle | `profitability_league_table_report.v1` | Validation lib | Offline optional files | `profitability_league_table_report.v1` |
| League Scorer (existing) | `services/validation/profitability_league_scorer.py` | Formula v1 scoring helper/CLI | PEP(s) | report-shaped JSON | Validation lib | Offline | `profitability_league_table_report.v1` |

No component in this pipeline is a deployed network service. None authorize live capital, strategy GO, or official winners without rankability gates.

---

## Offline pipeline

Vacation Runner → Strategy Metric Extraction → `arvp_strategy_metrics.v1` → Candidate Evidence Assembly → `profitability_evidence_packet.v1` → League Table Report Assembly → `profitability_league_table_report.v1`

Boundaries: research-only, LR NO-GO, `ranking_ready=false` on cross-venue research packets, no trading execution.

---

## Changed files (this batch)

- `knowledge/ARCHITECTURE_MAP.md`
- `knowledge/governance/SERVICE_CATALOG.md`
- `services/validation/README.md`
- `tools/arvp_vacation/README.md` (new)
- `docs/evidence/architecture_reconcile_4012_4020_4023_4026.md` (this file)
- `tests/unit/docs/test_architecture_catalog_arvp_contract.py`
- `knowledge/logs/sessions/2026-07-13-4012-architecture-reconcile-batch.md`

---

## Validation

Recorded at delivery time in session log and PR body.

---

## Safety Boundaries

- LR remains **NO-GO**
- No runtime, trading, DB, MCP, or live-capital scope
- Documentation-only reconcile; no product code or schema changes

---

## Non-goals

- Scanner code changes
- Productive Python/contract/fixture edits
- #4006 hygiene continuation
- PR #3755

---

## Restunsicherheiten

- Markdown/Mermaid rendering checked manually during review; not CI-enforced.
- Full-campaign hash examples remain in source evidence docs and depend on local artifacts.
