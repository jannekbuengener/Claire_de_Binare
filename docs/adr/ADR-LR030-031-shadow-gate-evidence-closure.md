# ADR: LR-030/031 Shadow-Gate Evidence Closure

## Status

**ACCEPT WITH FOLLOW-UP** — 2026-03-09

## Context

LR-030 (Shadow-Gate Hardening) und LR-031 (Shadow Metrics/Evidence) härten den Shadow-Mode-Enforcement in der Execution-Pipeline. Der Shadow-Gate in Execution ist ein Defense-in-Depth-Layer: Er blockiert Orders mit `run_mode=shadow`, falls der vorgelagerte Risk-Layer einen ALLOW produziert.

In 3 Shadow-Soak-Runs (5m/20m/30m, Live-MEXC-Daten) wurde `execution_shadow_blocked_total = 0` beobachtet. Der Risk-Layer hat in den beobachteten Runs sämtliche Signale blockiert, bevor sie den Execution-Service erreichten. Im aktuellen CI-/Shadow-Setup wurde kein belastbar reproduzierbarer natürlicher ALLOW-Pfad durch den Risk-Layer nachgewiesen.

## Current Evidence

**Code (verifiziert):**

- Shadow-Gate: `services/execution/service.py:340-364` — `run_mode=shadow` → REJECTED + `shadow_blocked` Counter + auditierbares Result
- Kill-Switch: Fail-closed Defense-in-Depth Gate in Execution
- Unwind-Suppression: `service.py:2064-2070` (proaktiv), `service.py:2127-2134` (reaktiv) — early-return in Shadow-Mode
- `run_mode`-Propagation: `risk/models.py:167-172` — Decision Contract Bundle → top-level `run_mode`
- `_resolve_contract_run_mode()`: `service.py:532-554` — Candidate-Chain (Override → Payload → ENV → Default)

**Tests (verifiziert):**

- 11 Shadow-Gate Tests in `test_execution_shadow_gate.py`: Gate-Block, Kill-Switch (inkl. Fail-Closed), run_mode-Fallback, MOCK_TRADING-Unabhängigkeit
- 4 Unwind-Suppression Tests in `test_shadow_unwind_suppression.py`: proaktiv/reaktiv + Paper-Regression

**Soak-Evidence (beobachtet):**

- 3 Runs (5m/20m/30m): `gate_status: PASS`, alle Required Services healthy
- In 3 Shadow-Soak-Runs beobachtet: Zero Fills, Zero Exposure, Zero Approved Orders
- `signals_received: 108/108/137`, `orders_blocked: 108/108/137`, `orders_approved: 0`
- `execution_shadow_blocked_total: 0`, `execution_orders_received_total: 0`
- `TRADING_MODE=shadow` im Workflow-Override aktiv

**ALLOW-Pfad (plausibel, nicht artefaktbasiert hart belegt):**

- Im aktuellen CI-/Shadow-Setup wurde kein belastbar reproduzierbarer natürlicher ALLOW-Pfad nachgewiesen
- Identifizierte Blocker: RC_020/RC_021 (kein Account-State-Provider im CI), RC_001 (Regime), RC_010 (Signal-Qualität-Schwellen)
- Die Blocker-Analyse basiert auf Code-Review und DB-Auswertung; nicht alle Einzelwerte sind als heruntergeladene Artefakte verfügbar

**PRs:** #1124 (LR-030+031, Commit `685ec4a`), #1125 (30m Soak Extension, Commit `06439ac`)

## Decision

**ACCEPT WITH FOLLOW-UP.**

LR-030 und LR-031 gelten als fachlich abgeschlossen.

Shadow-Mode-Enforcement in Execution ist durch Code-Review, deterministische Unit-Tests und funktionierende Evidence-Infrastruktur belastbar nachgewiesen. Die Shadow-Soak-Runs belegen den Betrieb mit Live-Daten; in den beobachteten Runs wurden Zero Execution und Zero Exposure festgestellt.

Der fehlende operative Nachweis `execution_shadow_blocked_total > 0` ist im aktuellen CI-/Shadow-Setup kein Closure-Blocker, da der Execution-Shadow-Gate ein Defense-in-Depth-Layer ist und der vorgelagerte Risk-Layer in den beobachteten Runs sämtliche Signale blockiert hat.

Ein zusätzlicher operativer Shadow-Block-Nachweis kann als separater, nicht blockierender Follow-up-Scope über einen deterministischen Integration-/Replay-Path ergänzt werden.

## Why this is acceptable

1. **Unit-Tests sind der stärkere Nachweis:** Für einen Defense-in-Depth-Gate, der nur bei vorgelagertem Layer-Versagen feuert, sind deterministische Unit-Tests belastbarer als ein zufälliger operativer Trigger in einem Soak-Run.

2. **Zero Execution ist das primäre Schutzziel:** LR-030 soll verhindern, dass im Shadow-Mode Orders ausgeführt werden. In 3 Soak-Runs mit Live-Marktdaten wurde beobachtet: `fills = 0`, `exposure = 0.0`. Das Schutzziel ist erfüllt.

3. **Der fehlende Counter ist erwartetes Verhalten im beobachteten Setup:** `execution_shadow_blocked_total = 0` bedeutet, dass der Risk-Layer in den beobachteten Runs korrekt funktioniert hat und keine Orders durchgelassen hat.

4. **Ein erzwungener Nachweis wäre weniger ehrlich:** Risk-Gates im CI aufzuweichen, nur um `execution_shadow_blocked_total > 0` zu erzeugen, würde die Governance-Integrität untergraben.

## Non-Goals

- Risk-Thresholds im CI aufweichen, um einen ALLOW zu erzwingen
- Echte API-Keys oder Account-State-Provider im CI-Runner
- Weitere Re-Runs ohne strukturelle Änderung am Setup
- Bypass-Pfade oder versteckte Umgehungen im produktiven Code
- Absolute Aussagen über die grundsätzliche Unmöglichkeit eines ALLOW

## Follow-Up Scope

- **Optional: Deterministischer Integration-Test** — Synthetischer ALLOW-Payload, der den Shadow-Block in Execution verifiziert. Eigenes Issue, kein Gate für LR-030/031.
- **Operative Beobachtung im Paper-Betrieb** — Wenn Account-State verfügbar ist und Risk einen ALLOW produziert, wird `execution_shadow_blocked_total > 0` sichtbar.
- **#706 Shadow+Soak Evidence Indexing** — Artefakt-Indexierung und maschinelle Auswertbarkeit.

## Next Steps

- [ ] Dieses ADR committen
- [ ] LR-030 und LR-031 Issues schließen
- [ ] Optional: Follow-up Issue für deterministischen Integration-Test anlegen
- [ ] #706 als nächsten Scope starten
