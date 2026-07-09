# ARVP 24h Natural-Paper Observation — Donchian (#3893)

Status Class: Scoped runtime evidence — **observation COMPLETE**
Issue: [#3893](https://github.com/jannekbuengener/Claire_de_Binare/issues/3893)
Hypothesis: `HYP-NP-DONCHIAN-03`
Parent: [#1900](https://github.com/jannekbuengener/Claire_de_Binare/issues/1900)
Prior: [#3792](https://github.com/jannekbuengener/Claire_de_Binare/issues/3792) (`TIMEOUT_NO_CHAIN`, 8h)
Tracker: [#3742](https://github.com/jannekbuengener/Claire_de_Binare/issues/3742)
Parallel design (orthogonal): [#3912](https://github.com/jannekbuengener/Claire_de_Binare/issues/3912)
Live-Readiness: **NO-GO**
Echtgeld: **not authorized**

**Verdict enum:** `TIMEOUT_NO_CHAIN`

**No-evidence-yet assertion:** No `natural_paper_evidence` claim. Attempt 2 completed the
full 24h window with healthy stack and donchian runtime path verified, but **zero
campaign-scoped** SIGNAL→DECISION→ORDER(paper_)→FILL chains.

---

## 1. RUNTIME-GO

Posted on #3893 before observation start (Attempt 1). Attempt 2 restarted after
`INTERRUPTED_HOST_REBOOT` on Attempt 1 with RUNTIME-RECOVERY-GO.

---

## 2. Campaign attempts

| Attempt | campaign_id | Window (UTC) | Outcome |
|---------|-------------|--------------|---------|
| 1 | `arvp_3893_natural_paper_donchian_24h_20260706_2032` | `2026-07-06T20:32:00Z` → `2026-07-07T20:32:00Z` | `INTERRUPTED_HOST_REBOOT` |
| 2 | `arvp_3893_natural_paper_donchian_24h_restart1_20260707_0217` | `2026-07-07T02:17:00Z` → `2026-07-08T02:17:00Z` | `TIMEOUT_NO_CHAIN` |

Signal path: `cdb_signal` with `SIGNAL_STRATEGY_ID=donchian_breakout_v1` (channel 20/10,
cooldown 30m). Runtime branch: `runtime/3893-donchian-natural-paper-24h`.

---

## 3. Preflight (PASS — Attempt 2)

| Check | Result |
|-------|--------|
| Safety flags (`cdb_execution`) | PASS — MOCK_TRADING=true, USE_REAL_BALANCE=false |
| `cdb_signal` strategy | `donchian_breakout_v1` |
| Risk-gate bypass | **not applied** |
| Parameter tuning | **none** |
| Kill-switch | not triggered during window |

---

## 4. Terminal evaluation (Attempt 2)

**Evaluated at (UTC):** `2026-07-09T12:52:00Z`  
**Evaluator:** Cursor agent (#3912 blocker-slice / #3893 terminal closeout)

| Metric | Count | Source |
|--------|------:|--------|
| Window duration | 24.0h | manifest / GitHub comments |
| Regime | `HIGH_VOL_CHAOTIC` (`risk_off=True`) | `cdb_risk` logs |
| Signals (BUY/SELL/emit path) | 96 | `cdb_signal` logs (window-bounded) |
| Risk blocks (RC_001) | 96 | `cdb_risk` logs (window-bounded) |
| Risk approvals | 0 | `cdb_risk` logs |
| Orders (campaign-scoped chain) | 0 | `correlation_ledger` probe |
| Fills (campaign-scoped chain) | 0 | `correlation_ledger` probe |
| `events_since_campaign_start` | 0 | `tools.arvp_probe_layer --ledger --campaign-start 2026-07-07T02:17:00Z` |
| Supervisor at eval | **not running** | host process scan |

**Classification:** Same negative pattern as #3792 — signals generated under chaotic regime,
all blocked by RC_001, no promotable chain. Hypothesis `HYP-NP-DONCHIAN-03` **falsified**
under frozen Pack-A params (documented negative; no silent retry).

---

## 5. Impact on parent issues

| Issue | Disposition |
|-------|-------------|
| **#3742** | Stays OPEN — §5.2.4 `regime_segments` still unavailable; no extractable chain |
| **#3912** | Scheduling gate cleared after stack baseline restore; parallel pilot unblocked for prep |
| **#1900** | No new promotable natural-paper chain evidence |

---

## 6. Boundaries

- LR **NO-GO** unchanged
- No multi-strategy parallel runtime in this issue
- No Live-Go / Echtgeld-Go
- Stack must return to canonical baseline before #3912 parallel pilot

---

*Terminal evidence recorded 2026-07-09 on `main` @ `0f273b15`.*
