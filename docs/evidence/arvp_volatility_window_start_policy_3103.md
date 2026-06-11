# ARVP Volatility-Window Start Policy — #3103

**Status:** Canonical
**Entscheidungsdatum:** 2026-06-11
**Scope:** Policy / Evidence — keine Code-, Runtime-, Docker- oder DB-Änderung
**Parent:** #3103 — Clarify volatility-window start criteria when regime is blocked for trading
**Gilt für:** Campaign #3 und alle späteren ARVP campaign supervisor runs

---

## 1. Start Criteria (Campaign Start nur erlaubt bei mindestens einem)

### Primary — Volatilitäts-Thresholds

| ID | Kriterium | Beschreibung |
|----|-----------|--------------|
| **P1** | Rolling 15m BTCUSDT high-low range >= 0.35% | Kurzfristige Volatilität |
| **P2** | Rolling 60m BTCUSDT high-low range >= 0.75% | Mittel-/längerfristige Volatilität |

### Primary — Regime

| ID | Kriterium | Beschreibung |
|----|-----------|--------------|
| **P3** | Regime TREND mit directional plausibility | Trendphase mit nachvollziehbarer Richtung; reicht als alleiniges Startsignal |

### P3 (TREND) gilt als Standalone-Startsignal

Wenn das Regime Service `TREND` meldet und eine directional plausibility (konsistente Richtung über mindestens 3 Kerzen) vorliegt, darf ein Campaign-Start allein auf Basis von P3 erfolgen — ohne zusätzlichen P1/P2-Threshold.

---

## 2. HIGH_VOL_CHAOTIC — Eingeschränkt

### Grundsatz

`HIGH_VOL_CHAOTIC` allein ist **kein gültiges Startkriterium**.

### Erlaubter Start unter HIGH_VOL_CHAOTIC

Ein Campaign-Start während `HIGH_VOL_CHAOTIC` ist nur erlaubt, wenn **alle** folgenden Bedingungen erfüllt sind:

1. **P1 oder P2 ist erfüllt** — der jeweilige rolling range threshold muss erreicht sein
2. **Keine Safety-Blocker aktiv** — MOCK_TRADING=true, DRY_RUN=true, MEXC_TESTNET=true, USE_REAL_BALANCE=false sind verifiziert
3. **Keine Governance-Blocker aktiv** — kein aktives STOP-Signal, keine offenen Governance-Violations, kein Human-Gate-Veto

### Warum diese Einschränkung?

`HIGH_VOL_CHAOTIC` (regime_id=2) ist in `blocked_regimes` per Strategy-Contract (PRIMARY_BREAKOUT_V1.md). Ein Signal kann während dieses Regimes feuern, aber die DECISION-Gate kann den Eintritt ablehnen. Ein Campaign-Start, der ausschliesslich auf `HIGH_VOL_CHAOTIC` basiert, riskiert eine unvollständige SIGNAL→DECISION→ORDER→FILL-Kette.

Der Threshold-Overlay (P1 oder P2) reduziert dieses Risiko: wenn der Markt trotz chaotischer Klassifikation ausreichende Volatilität aufweist, steigt die Wahrscheinlichkeit einer vollständigen Kette.

---

## 3. Campaign #3 — Anwendung

Für Campaign #3 (der nächste geplante supervisor-run unter #3095) gelten diese Criteria verbindlich:

- Start nur bei P1, P2, oder P3 (TREND mit directional plausibility)
- HIGH_VOL_CHAOTIC allein: **kein Start**
- HIGH_VOL_CHAOTIC + P1/P2 erfüllt + keine Blocker: **Start erlaubt**

---

## 4. Explizit Verboten

| Aktion | Begründung |
|--------|------------|
| Threshold-Lowering (z. B. P1 < 0.35%, P2 < 0.75%) | Parameter-Hack als Gate-Cheat; entwertet Evidence-Qualität |
| Synthetic Evidence als natürliches Paper-Evidence | Evidence-Class-Verletzung (#3094); synthetic ≠ natural |
| HIGH_VOL_CHAOTIC als alleiniges Startkriterium | Risiko unvollständiger Chain; blocked_regimes-Konflikt |
| Live-Go / Echtgeld-Go aus Campaign-Status ableiten | LR bleibt NO-GO; trade-capable ist kein Live-Go |
| Stille Ignorierung dieser Policy (Start ohne dokumentiertes Kriterium) | Anti-Cherry-Pick Verletzung |

---

## 5. Safety Boundaries (alle bestätigt)

| Boundary | Status |
|----------|--------|
| LR bleibt **NO-GO** | Bestätigt — docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md |
| Board `trade-capable` ≠ Live-Go | Bestätigt — docs/runbooks/CONTROL_REGISTER.md |
| Kein Echtgeld-Go | Bestätigt |
| Kein Threshold-Lowering | Explizit verboten (§4) |
| Keine Synthetic Evidence | Explizit verboten (§4) |
| Keine Runtime-/Code-/DB-Änderung | Scope dieser Policy |
| Keine Strategieparameter-Änderung | Scope dieser Policy |

---

## 6. Referenzen

- #3103 — Dieses Issue (Policy-Klärung)
- #3094 — Deterministic window production design (docs/evidence/arvp_deterministic_window_production_3094.md)
- #3095 — Campaign execution issue (nächster supervisor-run)
- #3087 — Comparison-grade paper reference window
- #3109 — Campaign supervisor manifest + state machine (docs/runbooks/arvp_campaign_supervisor_manifest_state_machine.md)
- docs/runbooks/CONTROL_REGISTER.md — Board stage trade-capable, LR NO-GO
- docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md — LR verdict NO-GO
- knowledge/contracts/PRIMARY_BREAKOUT_V1.md — Strategy contract, blocked_regimes
