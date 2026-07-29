# #4184 Reduce-only Unwind Contract Evidence

## Verdict

`PASS_REDUCE_ONLY_PROVEN_MOCK_SHADOW`

Der isolierte Mock-/Shadow-Drill belegt für den Contract
`execution_reduce_only_v1`, dass ein expliziter Reduce-only-Auftrag eine
verifizierte Long- oder Short-Position nie vergrößert und nie über null auf die
Gegenseite dreht.

Dieser Report bindet den getesteten Code-Commit
`d89b833333310fdda81801472944ac20e006240f` vor dem Evidence-Commit. Der nach
dem Evidence-Commit vorgeschriebene Final-HEAD-Lauf ist eine separate Evidence
und darf nicht mit diesem SHA gleichgesetzt werden.

## Run

- Run-ID: `4184_d89b8333_20260729T210152Z`
- Base-SHA: `2a3520794a82e44f7e411372f5fc9800f093bb86`
- Branch: `fix/4184-reduce-only-unwind-contract`
- Raw-Manifest-SHA256:
  `df925c0b90a7865902d4ed60949365b07f5e51bbfc7ffcde6e35198ee6240b1c`
- Maschinenlesbarer Report:
  [`4184_reduce_only_unwind_contract.json`](./4184_reduce_only_unwind_contract.json)

## Safe Mode

| Gate | Wert |
|------|------|
| `DRY_RUN` | `1` |
| `MOCK_TRADING` | `true` |
| `USE_REAL_BALANCE` | `false` |
| BLUE/RED aktiviert | `false` |
| Produktive Credentials | `false` |
| Host-Ports | keine |

## Contract

- Positionsvorzeichen: Long positiv, Short negativ, null ohne Position.
- Mengeneinheit: Base Asset.
- Long-Exit: ausschließlich `SELL` mit explizitem `reduce_only=true`.
- Short-Exit: ausschließlich `BUY` mit explizitem `reduce_only=true`.
- Execution prüft den persistenten Positionsstand vor Submission, reserviert
  die maximal ausführbare Menge unter der `order_id` und kappt übergroße
  Aufträge.
- Finalisierung wendet nur `filled_quantity` einmalig im selben
  PostgreSQL-Transaktionspfad auf die Position an.
- Der DB-Writer persistiert das Trade-Artefakt, wendet einen von Execution
  markierten Reduce-only-Fill aber nicht erneut auf die Position an.
- Fehlender, korrupter oder unlesbarer Positionsstand blockiert vor dem
  Adapter.

## R1–R10

| Szenario | Vorher | Requested | Submitted | Filled | Nachher | Ergebnis |
|----------|--------|-----------|-----------|--------|---------|----------|
| R1 Long Full Exit | `1` | `1` | `1.0` | `1.0` | `0` | PASS |
| R2 Short Full Exit | `-1` | `1` | `1.0` | `1.0` | `0` | PASS |
| R3 Long Partial | `1` | `1` | `1.0` | `0.4` | `0.60000000` | PASS |
| R4 Short Partial | `-1` | `1` | `1.0` | `0.4` | `-0.60000000` | PASS |
| R5 Oversized Long | `1` | `2` | `1.0` | `1.0` | `0` | PASS |
| R6 Oversized Short | `-1` | `2` | `1.0` | `1.0` | `0` | PASS |
| R7 Rejection | `1` | `1` | `1.0` | `0.0` | `1.00000000` | PASS |
| R8 Duplicate | `1` | `0.4` | `0.4` | `0.4` | `0.60000000` | PASS |
| R9 Restart nach Partial | `-1` | `1` | `1.0` | `0.25` | `-0.75000000` | PASS |
| R10 korrupter Position State | `UNKNOWN` | `1` | `0` | `0.0` | `UNKNOWN` | PASS / Adapter nicht aufgerufen |

Über alle Szenarien:

- `position_increase_observed=false`
- `side_flip_observed=false`
- kein `NOT_RUN`

## Cleanup

- Container verbleibend: `0`
- Volumes verbleibend: `0`
- Netzwerke verbleibend: `0`
- Verdict: PASS

## Grenzen

- Der Nachweis gilt ausschließlich für Mock-/Shadow-Execution.
- Der produktive MEXC-Adapter besitzt keinen belegten Reduce-only-Contract und
  bleibt für Reduce-only-Aufträge fail-closed.
- Ein Crash nach persistenter Preparation und vor Finalization bleibt
  fail-closed; die Reservation erfordert dann Reconciliation.
- Stop-Loss Protection bleibt `UNAVAILABLE`; kein Stop-Loss-Consumer und kein
  Preis-Trigger wurden ergänzt.
- Kill-Cancel bleibt außerhalb dieses Slices.
- LR bleibt `NO-GO`; kein Echtgeld- oder Live-Go.
