# ARVP Option-E / Waiver-or-Split Decision — #3087 / #3095

**Decision Date:** 2026-06-12
**Decision:** **SPLIT** — Option C
**Status:** `DONE_OPTION_E_SPLIT_DECISION_MERGED`
**Escalation Trigger:** 3/3 valid no-chain campaign slots consumed (#3095)
**Design Mandate:** #3094 Option B → E (escalate after 3 campaign failures)

---

## Executive Summary

After 3 valid gated no-chain campaign slots under #3095, Roadmap §5.2.4 (at least one window with non-empty `regime_segments`) remains BLOCKED. No natural paper chain was produced across 3 full-length observed windows (Campaign #1R, #2R, #3). Campaigns #1 and #2 were infrastructure interruptions and do not count as failure slots.

Per #3094 design §Option E, escalation to a waiver/split decision is now mandatory. This document records the Option-E decision.

**Decision:** **Split (C)** — #3087 remains the natural-chain blocker (§5.2.4). A separate controlled-lab evidence path (#3087b) will be created for regime-segment evidence from alternative non-natural sources, explicitly classified as `controlled_lab_evidence` — not as a Product-Complete gate substitute.

**LR remains NO-GO.** No Live-Go / Echtgeld-Go.

---

## Brain Evidence

| Field | Value |
|-------|-------|
| `brain_source` | `repo-only` |
| `brain_status` | `used` |
| `tools_or_queries` | `gh issue view` (3087, 3095, 3094, 3103 — live), `gh pr list --state open`, `git fetch/status`, read of 8 evidence/runbook files |
| `records_or_results` | #3087 OPEN/BLOCKED with 11 comments, #3095 OPEN (campaign execution, 3/3 slots consumed), #3094 CLOSED, #3103 CLOSED, 0 open PRs |
| `repo_crosscheck` | Campaign accounting verified across #3087 comments and `docs/evidence/arvp_volatility_window_campaign_3095_3.md`. Slot consumption confirmed: #1R (Slot 1), #2R (Slot 2), #3 (Slot 3). Interruptions #1/#2 do not count. |
| `impact_on_plan` | Split decision mandated by #3094 design after 3 no-chain failures. Decision C chosen over A/B/D per governance principles. |
| `limitations` | No SurrealDB/Context Brain/DB-backed memory. All claims are repo + GitHub live backed. |

---

## Bootloader / Read-Order Evidence

- `AGENTS.md` root pointer resolved
- `agents/AGENTS.md` canonical registry read
- Read order: `CDB_CONSTITUTION.md`, `CDB_GOVERNANCE.md`, `CDB_AGENT_POLICY.md` (read in prior sessions, unchanged)
- `docs/runbooks/CONTROL_REGISTER.md`: Board stage `trade-capable`, LR NO-GO
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`: LR verdict NO-GO
- `CURRENT_STATUS.md`: Ledger-only, not live truth
- Git truth: HEAD == `origin/main`, clean worktree at session start

---

## Live-Lage (GitHub Live Truth as of 2026-06-12)

| Issue | State | Key Fact |
|-------|-------|----------|
| #3087 | **OPEN** | §5.2.4 BLOCKED — 3 no-chain campaign slots exhausted |
| #3095 | **OPEN** | Campaign execution — 3/3 gated slots consumed, HOLD_DECISION_REQUIRED |
| #3094 | **CLOSED** | Design decision: Option B+C+E, mandate to escalate after 3 failures |
| #3103 | **CLOSED** | Start policy clarified: HIGH_VOL_CHAOTIC restricted |
| Open PRs | **0** | No open pull requests |
| LR | **NO-GO** | LR-AUDIT-STATUS-2026-03-05.md |
| Board Stage | `trade-capable` | ≠ Live-Go per CONTROL_REGISTER.md |

---

## Campaign Accounting

### Complete Campaign History

| Campaign | ID | Result | Chain | Slot? | Basis |
|----------|-----|--------|-------|-------|-------|
| #1 | `arvp_3095_vol_window_20260608_2341` | HOLD_INTERRUPTED_BY_HOST_SHUTDOWN | No | **No** | Host shutdown @~34min — interruption |
| **#1R** | `arvp_3095_vol_window_1r_20260609_1109` | **HOLD_NO_CHAIN** | **No** | **Slot #1** | Full 8h, 0 events, host continuous |
| #2 | `arvp_3095_vol_window_2_20260609_1942` | HOLD_INTERRUPTED_CAMPAIGN_2 | No | **No** | Host reboot @~3h14m — interruption |
| **#2R** | `arvp_3095_vol_window_2r_20260610_1111` | **HOLD_NO_CHAIN** | **No** | **Slot #2** | Full 8h, 0 events, host continuous |
| **#3** | `arvp_3095_vol_window_3_20260611_1301` | **TIMEOUT_NO_CHAIN** | **No** | **Slot #3** | Full 8h 12min, 32 cycles, 0 events |

### Slot Consumption Rules (per #3094 design and #3109 state machine)

| Rule | Applied |
|------|---------|
| Maximum 3 campaigns | ✅ 3 consumed — limit reached |
| `timeout_no_chain` counts as failure | ✅ #1R, #2R, #3 |
| `interrupted` does NOT count | ✅ #1, #2 correctly excluded |
| Early stop on chain found | Not applicable — no chain occurred |
| Escalation after 3 failures | **Triggered — this decision** |

**Effective consumption: 3 of max 3 slots.** No remaining campaign capacity.

---

## Evidence Reviewed

| # | Document | Key Content |
|---|----------|-------------|
| 1 | `arvp_deterministic_window_production_3094.md` | Design decision: Option B + C + E hybrid; campaign policy (max 3, 8h, pre-documented criteria); evidence classes; escalation mandate |
| 2 | `arvp_volatility_window_campaign_3095.md` | Campaign #1 evidence: interrupted @~34min, 0 events, P2+P3 start criteria met |
| 3 | `arvp_volatility_window_campaign_3095_3.md` | Campaign #3 closeout: TIMEOUT_NO_CHAIN, slot #3 consumed, 32 cycles, 0 events |
| 4 | `arvp_volatility_window_start_policy_3103.md` | Start criteria policy: HIGH_VOL_CHAOTIC restricted, P1/P2 threshold, TREND standalone |
| 5 | `arvp_campaign_supervisor_manifest_state_machine.md` | Manifest contract, state definitions, terminal classification, escalation matrix (3 failures → Option E) |
| 6 | `LR-AUDIT-STATUS-2026-03-05.md` | LR NO-GO; P5 `LR-050` remains NO-GO |
| 7 | `CONTROL_REGISTER.md` | Board stage `trade-capable`; LR NO-GO; SSOT boundaries |
| 8 | `CURRENT_STATUS.md` | Repo/engineering ledger; not live truth |

---

## Befund

1. **Keine natürliche Paper-Chain produziert.** `primary_breakout_v1` (0.5% breakout, 15m lookback) hat unter HIGH_VOL_CHAOTIC und gemischten Marktbedingungen in keiner der 3 Campaigns einen SIGNAL→DECISION→ORDER→FILL-Durchlauf erzeugt.

2. **Keine non-empty regime_segments.** Da kein Paper-Window extrahiert werden konnte, existiert kein `paper_reference_window.v1` mit non-empty `regime_segments`.

3. **#3087 §5.2.4 bleibt BLOCKED.** Der Gate ist nicht durch natürliche Marktevidenz erfüllt worden.

4. **Kein technisches Defekt.** Das System funktioniert (DB-Evidenz aller Campaigns bestätigt Laufzeit, Health, Safety-Flags). Der Blocker ist Markt-bedingt: BTCUSDT bewegte sich in keinem der beobachteten Fenster ausreichend für einen 0.5%-Breakout in 15 Minuten.

---

## Decision Options A–D

### A — Hard Block

| Dimension | Assessment |
|-----------|------------|
| Wirkung | #3087 bleibt offen, keine weiteren Campaigns ohne neues Issue/Design |
| Vorteil | Strengste Evidence-Qualität, kein Risiko der Gate-Absenkung |
| Nachteil | System hängt unbestimmt an seltenem Markt-Trigger; kein Fortschritt |
| **Verdikt** | Zu konservativ — ignoriert die Erkenntnis, dass der Gate probabilistisch ist |

### B — Waiver

| Dimension | Assessment |
|-----------|------------|
| Wirkung | §5.2.4 als begrenzten Waiver dokumentieren, nur für Product-Complete-Review |
| Vorteil | Fortschritt möglich, Gate formell adressiert |
| Nachteil | Schwächerer Evidence-Standard; Risiko dass Waiver als Dauerlösung interpretiert wird |
| **Verdikt** | **Nicht empfohlen.** Waiver verbessert LR-Position nicht und schwächt Governance. |

### C — Split (GEWÄHLT)

| Dimension | Assessment |
|-----------|------------|
| Wirkung | #3087 splitten: (a) natural-chain evidence bleibt offen, (b) neues Issue für controlled-lab regime-segment evidence |
| Vorteil | Sauberste Governance. Kein Fake-Abschluss. Paralleler Fortschritt möglich. |
| Nachteil | Mehr Folgearbeit (neues Issue, separate Evidence-Docs) |
| **Verdikt** | **Gewählt.** Erfüllt alle Governance-Anforderungen. |

### D — Hybrid

| Dimension | Assessment |
|-----------|------------|
| Wirkung | #3087 bleibt als natural-chain blocker offen + neues Issue für surrogate evidence |
| Vorteil | #3087 bleibt als harter Blocker sichtbar |
| Nachteil | Weniger saubere Trennung als Split; #3087-Scope wird unklar |
| **Verdikt** | Nachvollziehbar, aber Split (C) trennt Verantwortlichkeiten klarer |

---

## Recommended Decision: C — Split

### Split Contract

**#3087a — Natural-Chain Evidence (unchanged)**
- #3087 bleibt das bestehende Issue
- §5.2.4 bleibt BLOCKED für `natural_paper_evidence`
- Keine weiteren Campaigns ohne neue Hypothese/neues Design
- #3087 bleibt OPEN

**#3087b — Controlled-Lab Regime-Segment Evidence (NEW)**
- Neues Issue für alternative Evidence-Quelle
- Evidence Class: `controlled_lab_evidence` (laut #3094 Klassifikation)
- Kandidaten: historische Scenario-Packs, Simulation, quasi-historische Daten
- **KEIN Product-Complete Gate-Ersatz**
- Explizite Kennzeichnung als nicht-natürliche Evidence in allen Artefakten
- LR-Relevanz: keine (LR bleibt NO-GO)

### Begründung für Split

1. **#3094 Design-Mandat erfüllt:** Option E wurde nach 3 Campaign-Failures eskaliert. Der Split ist die sauberste Governance-Variante.
2. **Evidence-Klassen existieren bereits:** #3094 formalisierte `natural_paper_evidence`, `controlled_lab_evidence`, `pipeline_test_evidence`, `waiver_decision`. Der Split nutzt diese Klassen ohne neue Definitionen.
3. **Kein Fake-Abschluss:** Natural-chain blocker bleibt bestehen. Controlled-lab evidence wird explizit als solche gekennzeichnet.
4. **Produktiver Fortschritt:** Während #3087a auf natürlichen Trigger wartet, kann parallel an kontrollierten Evidence-Quellen gearbeitet werden.
5. **Product-Complete nur mit Caveat:** Kein Product-Complete ohne expliziten Hinweis auf den offenen natural-chain Blocker.

### Explizit Verboten

| Aktion | Begründung |
|--------|------------|
| Live-Go / Echtgeld-Go | LR bleibt NO-GO |
| Synthetic Evidence als natural_paper_evidence | Evidence-Class-Verletzung (#3094) |
| Threshold-Lowering (Breakout < 0.5%) | Parameter-Hack als Gate-Cheat |
| Weitere Campaign ohne neue Hypothese | 3/3 Slots erschöpft; neues Design nötig |
| Product-Complete ohne Caveat | Natural-chain blocker bleibt offen |
| Controlled-lab evidence als Gate-Ersatz | §5.2.4 erfordert natural_paper_evidence |
| Stille Schliessung von #3087 | Muss explizit durch natural chain ODER Governance-Votum |

---

## Impact on #3087

- #3087 bleibt **OPEN** und **BLOCKED** für §5.2.4
- Der natural-chain blocker wird nicht geschlossen
- Split ermöglicht parallelen controlled-lab Pfad ohne #3087-Status zu ändern
- #3087 kann nur geschlossen werden durch:
  a) Erfolgreiche natürliche Paper-Chain (SIGNAL→DECISION→ORDER→FILL) **ODER**
  b) Explizites Governance-Votum (formaler Waiver via Roadmap-Amendment)
- Diese Entscheidung ist KEINE der beiden Optionen — #3087 bleibt offen

## Impact on Product-Complete (#2974)

- **§5.2.4 bleibt BLOCKED** (unverändert)
- Product-Complete (#2974) kann nicht erklärt werden ohne:
  a) Natural-chain evidence mit non-empty regime_segments **ODER**
  b) Formalen Waiver/Roadmap-Amendment mit explizitem Governance-Votum
- Controlled-lab evidence (#3087b) ist **KEIN** Ersatz für §5.2.4
- Eventuelles Product-Complete mit offenem natural-chain Blocker erfordert explizite Caveat im Review-Dokument

## Impact on LR

- **LR bleibt NO-GO** (unverändert)
- Diese Entscheidung verändert das LR-Verdikt nicht
- Board-Stage `trade-capable` ist kein Live-Go
- Keine LR-050-Re-Evaluierung durch diese Entscheidung
- Kein Live-Kapital, keine Echtgeld-Orders

---

## Required Follow-up Issues

| Issue | Title | Scope | Classification |
|-------|-------|-------|----------------|
| #3087b (NEW) | `[ARVP][EVIDENCE] Define controlled-lab regime-segment evidence path (#3087b split)` | Design/Machbarkeit kontrollierter Evidence-Quellen | `controlled_lab_evidence` |
| #3096 (existing) | `[ARVP][POLICY] Evidence class policy enforcement` | Evidence class labels in runners/CI | `policy` |

**Kein Waiver-Issue:** Da Split (C) gewählt wurde, ist kein formaler Waiver nötig. Der natural-chain blocker bleibt bestehen. Ein Waiver wäre nur dann erforderlich, wenn #3087 ohne natürliche Chain geschlossen werden soll.

---

## Forbidden Interpretations

1. **Kein Live-Go.** LR bleibt NO-GO — diese Entscheidung ändert daran nichts.
2. **Kein Echtgeld-Go.** Kein Live-Kapital, keine echten Orders.
3. **Keine Synthetic Evidence als natural-chain Evidence.** Synthetic bleibt synthetic.
4. **Kein Threshold-Lowering rückwirkend.** 0.5% Breakout bleibt.
5. **Keine weitere Campaign ohne neue Hypothese.** 3/3 Slots erschöpft.
6. **Kein Product-Complete ohne Caveat.** Natural-chain blocker muss adressiert sein.
7. **Controlled-lab evidence ist kein Gate-Ersatz.** §5.2.4 bleibt unverändert.
8. **Keine stille Schliessung von #3087.** Nur durch natürliche Chain oder Governance-Votum.
9. **Board `trade-capable` ist kein LR-Go.** Orthogonales System.
10. **Stage-System ist kein LR-Go.** Stage-Aussagen nie als LR-Go lesen.

---

## Safety Boundaries (all affirmed)

| Boundary | Status |
|----------|--------|
| LR remains **NO-GO** | Confirmed |
| No Live-Go / Echtgeld-Go | Confirmed |
| Board `trade-capable` ≠ Live-Go | Confirmed |
| No strategy parameter changes | Confirmed |
| No synthetic evidence as natural paper | Confirmed |
| No silent evidence-class upgrade | Confirmed |
| No secrets in outputs | Confirmed |
| Docs-only, no code changes | Confirmed |
| No runtime/stack/DB mutation | Confirmed |

---

## Validation

```bash
# Diff check
git diff --check

# Safety scan — no 'Closes <issue>' or affirmative LR-GO patterns
# (All LR/live/e match in prohibitions only, never as affirmations)

# Expected: green diff-check, zero prohibited patterns
```

---

## References

- #3087 — Comparison-grade paper reference window (OPEN, BLOCKED)
- #3095 — Volatility-window campaigns (OPEN, 3/3 slots consumed)
- #3094 — Deterministic window production design (CLOSED)
- #3103 — blocked_regimes policy clarification (CLOSED)
- #2974 — Product-complete review (CLOSED, §5.2.4 BLOCKED)
- #1900 — ARVP north-star anchor (OPEN)
- `docs/evidence/arvp_deterministic_window_production_3094.md`
- `docs/evidence/arvp_volatility_window_campaign_3095.md`
- `docs/evidence/arvp_volatility_window_campaign_3095_3.md`
- `docs/evidence/arvp_volatility_window_start_policy_3103.md`
- `docs/runbooks/arvp_campaign_supervisor_manifest_state_machine.md`
- `docs/runbooks/CONTROL_REGISTER.md`
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- `knowledge/governance/CDB_CONSTITUTION.md`
- `knowledge/governance/CDB_AGENT_POLICY.md`

---

## Status

**DONE_OPTION_E_SPLIT_DECISION_MERGED**

- Option-E decision completed per #3094 design mandate.
- Decision: **C — Split** (#3087a natural-chain + #3087b controlled-lab).
- #3087 remains OPEN/BLOCKED for natural paper evidence.
- #3095 campaign execution complete — no further campaigns planned.
- LR remains NO-GO.
- Follow-up: #3087b issue creation (after PR merge).
