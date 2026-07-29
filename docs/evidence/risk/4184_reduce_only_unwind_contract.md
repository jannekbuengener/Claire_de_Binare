# #4184 Reduce-only Unwind Contract Evidence

## Verdict

`PASS_REDUCE_ONLY_PROVEN_MOCK_SHADOW`

Der isolierte Mock-/Shadow-Drill belegt für `execution_reduce_only_v1`, dass
ein expliziter Reduce-only-Auftrag eine eindeutig bekannte Long- oder
Short-Position nicht vergrößert und nicht über null auf die Gegenseite dreht.

Dieser Report bindet den getesteten Code-Commit
`dfb8b040961db70ca106144e552ba7813a58f9dd` vor dem Evidence-Commit. Der
Final-HEAD-Lauf nach dem Evidence-Commit ist eine separate Evidence und darf
nicht mit diesem SHA gleichgesetzt werden.

## Run

- Run-ID: `4184_dfb8b040_20260729T231022Z`
- Base-SHA: `2a3520794a82e44f7e411372f5fc9800f093bb86`
- Branch: `fix/4184-reduce-only-unwind-contract`
- Raw-Manifest-SHA256:
  `4b1437090d1b69950f85d2e3c72bc23179ac34e34fd508d54b75067a04527094`
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
- Ein vorhandener persistenter Claim blockiert jede zweite Submission vor dem
  Adapter mit `REDUCE_ONLY_CONCURRENT_CLAIM_BLOCKED`.
- Der eingebaute Mock-Adapter validiert Contract-Version, Richtung, Position
  und maximale Menge unabhängig erneut.
- Finalisierung verlangt denselben Positionsstand wie bei Preparation und
  aktualisiert Größe, aktuellen Preis und realisierten PnL atomar per
  Positions-ID.
- Das Execution-Ledger bindet Fill-Preis und realisierten PnL; der DB-Writer
  prüft beide Werte gegen den persistierten Owner-State und dedupliziert nur
  auf dem partiellen `execution_reduce_only_v1`-Index.
- Adapter-Overfill oder zwischenzeitlich geänderter Positionsstand wird als
  `REDUCE_ONLY_POSITION_INCREASE_BLOCKED` persistiert und nicht als Fill
  publiziert.
- Partielle Fills bleiben als `PARTIALLY_FILLED` inklusive `fill_id`
  serialisiert und erreichen Correlation-FILL sowie Envelope-Evidence.

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
| R9 Restart nach Partial | `-1` | `1` | `1.0` | `0.25` | `-0.75` | PASS / neuer Prozess ruft Adapter nicht auf |
| R10 unbekannter State | `UNKNOWN` | `1` | `0` | `0.0` | `UNKNOWN` | PASS / Adapter nicht aufgerufen |

Zusätzliche PostgreSQL-Negativkontrollen decken Adapter-Overfill, mehrdeutige
offene Positionszeilen, fehlenden Accounting-State, eine Positionsänderung
zwischen Preparation und Finalization sowie DB-Writer-PnL-Bindung und
zweifache Trade-Zustellung ab.

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
- Eine echt konkurrierte DB-Writer-Doppelzustellung wurde nicht separat
  provoziert; die serielle Doppelzustellung und der partielle Unique-Index sind
  belegt.
- Stop-Loss Protection bleibt `UNAVAILABLE`.
- Kill-Cancel bleibt außerhalb dieses Slices.
- LR bleibt `NO-GO`; kein Echtgeld- oder Live-Go.
