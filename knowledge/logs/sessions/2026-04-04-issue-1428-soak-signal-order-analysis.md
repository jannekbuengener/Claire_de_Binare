# Session Log — 2026-04-04 — Issue #1428: Soak Signal/Order/Trade Analyse

## Ziel

Klaeren, ob konstante `orders`/`trades` bei steigendem `signals`-Count im LR-040-Soak erwartetes Verhalten oder ein Defekt ist.

## Durchgefuehrte Schritte

- Alle `db_growth_*.txt` Snapshots aus `artifacts/soak_test_20260401_114850/` gelesen
- `run_intent.txt` geprueft: `lr040`
- Signal-Service analysiert: `SIGNAL_THRESHOLD_PCT: 0.005` (0.5%) in `compose.red.yml:68`
- Risk-Service Decision Contract V1 analysiert: `signal_pct_change_15m_min: 0.03` (3.0%) in `services/risk/service.py:172`
- Compose-Konfiguration geprueft: kein `RUN_MODE`/`TRADING_MODE` gesetzt, Default "paper"
- Execution-Service Shadow-Gate geprueft: `services/execution/service.py:340-364`
- Soak-Monitor DB-Query geprueft: `soak_monitor.sh:549-551` — nur `orders`/`trades`/`signals` COUNT(*)
- LR-040 DoD geprueft: Stabilitaets-Soak, kein Trading-Throughput-Kriterium

## Ergebnis

**Erwartetes Verhalten.** Schwellenasymmetrie Signal (0.5%) vs Risk (3.0%) — Faktor 6x. Bei normalem Markt blockiert der Decision Contract 100% der Signale. orders/trades = 10504/9963 sind Altbestand aus frueheren Paper-Runs.

## Aktionen

- Issue-Kommentar mit vollstaendiger Analyse gepostet
- Issue #1428 geschlossen (completed)
- Kein Code-Fix noetig

## Verbesserungsvorschlag (nicht umgesetzt)

`blocked_decisions`-Count in Soak-Monitor DB-Growth-Query aufnehmen — wuerde das Muster bei kuenftigen Runs sofort erklaerbar machen.

## Commits

Keine.
