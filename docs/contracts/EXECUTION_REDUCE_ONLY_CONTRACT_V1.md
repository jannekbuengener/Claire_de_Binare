# Execution Reduce-only Contract v1

Status: Mock-/Shadow-enforced
Contract version: `execution_reduce_only_v1`
Issue: `#4184`

## Definition

`reduce_only=true` bezeichnet einen expliziten Exit-/Unwind-Auftrag. BUY oder
SELL allein besitzt keine Reduce-only-Semantik. Der Contract wird am
Execution-Boundary durch verifizierten persistenten Position State erzwungen,
nicht durch Caller-Metadaten.

Die kanonische Darstellung ist eine signierte Base-Asset-Menge:

- Long: `position > 0`
- Short: `position < 0`
- keine Position: `position == 0`
- Long schließen/reduzieren: `SELL`
- Short schließen/reduzieren: `BUY`

Für jeden angewandten Fill gilt:

`abs(position_after) <= abs(position_before)`

`position_after` behält das Vorzeichen von `position_before` oder ist null.

## Prepare vor Submission

Execution liest und sperrt den offenen Positionsdatensatz, zieht bereits
persistierte `PREPARED`-Reservations ab und berechnet die maximal zulässige
Menge. Ungültige Menge, falsche Seite, null/fehlende/korrupte Position oder
fehlende Adapter-Capability blockieren vor dem Adapter. Ein übergroßer Exit
wird auf die verfügbare Position gekappt.

Der Claim wird vor Submission in `reduce_only_executions` unter der
deterministischen `order_id` persistiert. Eine identische `order_id` wird nicht
erneut submitted.

## Fill, Partial Fill und Rejection

- `FILLED`: nur die tatsächliche `filled_quantity` wird angewandt.
- `PARTIALLY_FILLED`: die Restposition bleibt mit unverändertem Vorzeichen
  sichtbar.
- `REJECTED`, `FAILED`, `CANCELLED`, `ERROR`: Position bleibt unverändert.
- Filled Quantity außerhalb `[0, submitted_quantity]` blockiert die
  Positionsanwendung.
- Ein finalisierter Claim kann nicht erneut auf den Positionsstand angewandt
  werden.

Execution ist für die atomare Positionsänderung eines markierten
Reduce-only-Fills verantwortlich. Der DB-Writer persistiert das Trade-Artefakt,
überspringt aber eine zweite Positionsanwendung, wenn
`position_update_owner=execution_reduce_only_v1` vorliegt.

## Reason Codes

- `REDUCE_ONLY_POSITION_UNKNOWN`
- `REDUCE_ONLY_NO_POSITION`
- `REDUCE_ONLY_INVALID_QUANTITY`
- `REDUCE_ONLY_QUANTITY_CLAMPED`
- `REDUCE_ONLY_SIDE_MISMATCH`
- `REDUCE_ONLY_REJECTED`
- `REDUCE_ONLY_PARTIAL_FILL`
- `REDUCE_ONLY_DUPLICATE_RESULT`
- `REDUCE_ONLY_POSITION_INCREASE_BLOCKED`

## Adaptergrenze

Der Mock-Adapter erklärt und bestätigt `supports_reduce_only=true`. Der
produktive MEXC-Adapter erklärt `supports_reduce_only=false`. Reduce-only wird
außerhalb `MOCK_TRADING=true` fail-closed blockiert; daraus folgt kein
produktiver Adapterbeweis.

## Restart und bekannte Grenze

Persistierte Claims verhindern doppelte Submission und doppelte
Positionsanwendung über einen Execution-Restart. Ein Crash zwischen erfolgreicher
Adapter-Submission und Finalization bleibt absichtlich fail-closed: der
`PREPARED`-Claim reserviert weiter und verlangt Reconciliation. Dieser Contract
implementiert weder Stop-Loss-Consumer noch Kill-Cancel.

Evidence:
[`docs/evidence/risk/4184_reduce_only_unwind_contract.md`](../evidence/risk/4184_reduce_only_unwind_contract.md)
