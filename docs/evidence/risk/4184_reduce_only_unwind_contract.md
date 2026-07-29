# #4184 Reduce-only Unwind Contract Evidence

## Verdict

`PASS_REDUCE_ONLY_PROVEN_MOCK_SHADOW`

Der isolierte Mock-/Shadow-Drill belegt für `execution_reduce_only_v1`, dass
ein expliziter Reduce-only-Auftrag eine eindeutig bekannte Long- oder
Short-Position nicht vergrößert und nicht über null auf die Gegenseite dreht.

Dieser Report bindet den getesteten Code-Commit
`c0d41fe1513521482764ad415817f84c010182a1` vor dem Evidence-Commit. Der
Final-HEAD-Lauf nach dem Evidence-Commit ist eine separate Evidence und darf
nicht mit diesem SHA gleichgesetzt werden.

## Run

- Run-ID: `4184_c0d41fe1_20260729T215022Z`
- Base-SHA: `2a3520794a82e44f7e411372f5fc9800f093bb86`
- Branch: `fix/4184-reduce-only-unwind-contract`
- Raw-Manifest-SHA256:
  `3949e3fbf532cbeec7c30f70e7e97c498dac804e8c40cba24cc244e5987dfbee`
- Maschinenlesbarer Report:
  [`4184_reduce_only_unwind_contract.json`](./4184_reduce_only_unwind_contract.json)

## Safe Mode

| Gate | Wert |
|------|------|
| `DRY_RUN` | `1`, im Execution-Runtime verifiziert |
| `MOCK_TRADING` | `true`, im Execution-Runtime verifiziert |
| `USE_REAL_BALANCE` | `false` |
| BLUE/RED aktiviert | `false` |
| Produktive Credentials | `false` |
| Host-Ports | keine |

## Contract

- Positionsvorzeichen: Long positiv, Short negativ, null ohne Position.
- Mengeneinheit: Base Asset.
- Long-Exit: ausschließlich `SELL` mit explizitem `reduce_only=true`.
- Short-Exit: ausschließlich `BUY` mit explizitem `reduce_only=true`.
- Execution verlangt genau eine offene, accounting-fähige Position, reserviert
  die maximal ausführbare Menge persistent und kappt übergroße Aufträge vor
  Adapteraufruf.
- Der eingebaute Mock-Adapter validiert Contract-Version, Richtung, Position
  und maximale Menge unabhängig erneut.
- Finalisierung verlangt denselben Positionsstand wie bei Preparation und
  aktualisiert Größe, aktuellen Preis und realisierten PnL atomar per
  Positions-ID.
- Adapter-Overfill oder zwischenzeitlich geänderter Positionsstand wird als
  `REDUCE_ONLY_POSITION_INCREASE_BLOCKED` persistiert und nicht als Fill
  publiziert.
- Der DB-Writer persistiert den durch Execution berechneten
  `realized_pnl_delta`, wendet den Positionseffekt aber nicht erneut an.

## R1-R10

| Szenario | Vorher | Requested | Submitted | Filled | Nachher | Ergebnis |
|----------|--------|-----------|-----------|--------|---------|----------|
| R1 Long Full Exit | `1` | `1` | `1.0` | `1.0` | `0` | PASS |
| R2 Short Full Exit | `-1` | `1` | `1.0` | `1.0` | `0` | PASS |
| R3 Long Partial | `1` | `1` | `1.0` | `0.4` | `0.60000000` | PASS |
| R4 Short Partial | `-1` | `1` | `1.0` | `0.4` | `-0.60000000` | PASS |
| R5 Oversized Long | `1` | `2` | `1.0` | `1.0` | `0` | PASS / Clamp belegt |
| R6 Oversized Short | `-1` | `2` | `1.0` | `1.0` | `0` | PASS / Clamp belegt |
| R7 Rejection | `1` | `1` | `1.0` | `0.0` | `1.00000000` | PASS |
| R8 Duplicate Result | `1` | `0.4` | `0.4` | `0.4` | `0.60000000` | PASS / zweites Finalize blockiert |
| R9 Restart nach Partial | `-1` | `1` | `0.25` | `0.25` | `-0.75` | PASS / neuer Prozess ruft Adapter nicht auf |
| R10 unbekannter State | `UNKNOWN` | `1` | `0` | `0.0` | `UNKNOWN` | PASS / Adapter nicht aufgerufen |

Zusätzliche PostgreSQL-Negativkontrollen decken Adapter-Overfill, mehrdeutige
offene Positionszeilen, fehlenden Accounting-State und eine Positionsänderung
zwischen Preparation und Finalization ab.

Über alle R1-R10-Szenarien:

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
  fail-closed; die Reservation erfordert Reconciliation.
- Stop-Loss Protection bleibt `UNAVAILABLE`.
- Kill-Cancel bleibt außerhalb dieses Slices.
- LR bleibt `NO-GO`; kein Echtgeld- oder Live-Go.
