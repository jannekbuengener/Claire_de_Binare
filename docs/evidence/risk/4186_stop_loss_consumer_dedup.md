# Evidence: Restart-sicherer Stop-Loss-Consumer mit persistentem Dedup-State (#4186)

**Datum:** 2026-07-31

**Branch:** `dedicated/runtime-risk-issue-4186`

**Base:** `main@379d031d78a045198f4eab5d145459b82d4df3d1`

**Verdict:** `PASS_CONSUMER_DEDUP_MOCK_SHADOW`

**Stop-Loss-Protection:** `UNAVAILABLE` (unverändert)

**LR:** `NO-GO` (unverändert)

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
context_tool_status: available
context_trust_level: none
records_found: none
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
```

`cdb_context_briefing` (briefing_id `f35c22fc72659e48`) antwortete mit
`operator_trust_level=LOW`, `readiness=blocked_missing_context` und ohne
evidence-/claim-/decision-/memory-Records. Symbol-Treffer kamen als
`<mocked>/path/to/...` zurück. Es gibt daher keine DB-gestützte Evidence;
Repo- und GitHub-Wahrheit sind die Basis.

## Scope und Claim-Grenze

Dieser Slice belegt den Pfad **Preis-Trigger → Schutzereignis → genau ein
Reduce-only-Exit-Intent** deterministisch und restart-sicher, ausschließlich
mit Mock-/Fixture-/Shadow-Mitteln.

Er belegt **nicht**:

- Real-Stack-Persistenz (kein Docker-, Redis- oder Postgres-Drill in dieser Session)
- einen produktiven Exit-/Unwind-Adapter (bewusst deaktiviert; Order-seitiger
  Reduce-only-Vertrag gehört zu #4184 / PR #4187, geparkt)

Deshalb bleibt `STOP_LOSS_PROTECTION_STATUS = UNAVAILABLE`. Der Risk-Gate in
`services/risk/service.py` weist schutzbedürftige Signale weiterhin mit
`STOP_LOSS_PROTECTION_UNAVAILABLE` ab. `END_TO_END_PROVEN` ist unzulässig.

## Ausgeführte Schutzszenarien D1–D11

Die Status stammen aus echten Consumer-Läufen des Generators
`python -m tools.safety.stop_loss_consumer_evidence` — nicht aus Testnamen.

| Szenario | Erwartet | Beobachtet | Intents | Status |
|---|---|---|---|---|
| D1 Preisbruch erzeugt einen Exit-Intent | `STOP_LOSS_EXIT_INTENT_EMITTED` | identisch | 1 | `PASS` |
| D2 Doppelte Zustellung desselben Ereignisses | `STOP_LOSS_DUPLICATE_SUPPRESSED` | identisch | 1 | `PASS` |
| D3 Consumer-Restart nach Finalize (Replay) | `STOP_LOSS_DUPLICATE_SUPPRESSED` | identisch | 1 | `PASS` |
| D4 Restart zwischen Prepare und Finalize | `STOP_LOSS_PREPARE_INCOMPLETE` | identisch | 1 (gemeldet) | `PASS` |
| D5 Fehlender Dedup-State | `STOP_LOSS_DEDUP_STATE_MISSING` | identisch | 0 | `PASS` |
| D6 Korrupter Dedup-State | `STOP_LOSS_DEDUP_STATE_CORRUPT` | identisch | 0 | `PASS` |
| D7 Widersprüchlicher Fingerprint | `STOP_LOSS_DEDUP_STATE_CONTRADICTORY` | identisch | 1 (aus D7-Vorlauf) | `PASS` |
| D8 Neues Schutzereignis nach Reopen | `STOP_LOSS_EXIT_INTENT_EMITTED` | identisch | 2 | `PASS` |
| D9 Unbekannter Positionszustand | `STOP_LOSS_POSITION_STATE_UNKNOWN` | identisch | 0 | `PASS` |
| D10 Produktiver Exit-Adapter bleibt gesperrt | `STOP_LOSS_EXIT_INTENT_SINK_FAILED` | identisch | 0 | `PASS` |
| D11 Veraltete Preisbeobachtung | `STOP_LOSS_PRICE_STALE` | identisch | 0 | `PASS` |

Kein Szenario blieb `NOT_RUN`. Keine Positionsvergrößerung und kein Side-Flip
wurde beobachtet.

## Mock-/Shadow-E2E

Fixture `tests/fixtures/stop_loss_shadow_candles.json` (7 × 1m-Candles,
Long @ 100.00, Stop 2 % → 98.00) durch `run_stop_loss_shadow`:

```text
decision_counts: NO_TRIGGER=3, EXIT_INTENT_EMITTED=1, DUPLICATE_SUPPRESSED=3
emitted_intent_count: 1
unique_emitted_intent_count: 1
restarted_before_step: index 4 (unmittelbar nach der Emission in index 3)
productive_adapter_enabled: false
```

Der Replay enthält selbst einen Consumer-Restart: bei Schritt 4 wird eine frische
Consumer-Instanz gegen denselben persistenten State gebaut. Alle Schritte ab dem
Restart bleiben `DUPLICATE_SUPPRESSED` ohne weiteren Intent — der Restart ist
damit im Artefakt belegt, nicht nur im Test.

Zusätzlich belegt in `tests/integration/test_stop_loss_shadow_e2e.py`:
Restart mitten in der Serie erzeugt keinen zweiten Intent, zwei unabhängige
Läufe liefern denselben Report (Determinismus), eine komplett veraltete Serie
triggert gar nicht, und der `DisabledProductiveExitAdapter` blockiert die
Übergabe fail-closed.

## Trigger- und Dedup-Semantik

```text
event_id = "slp-" + sha256(canonical_json({contract_version, symbol, position_id,
           position_side, position_quantity, entry_price, stop_price,
           stop_loss_pct, position_opened_at_ms}))[:32]
```

Beobachtender Tick (`observed_price`, `observed_at_ms`, `price_source`) ist
**nicht** Teil der Identität → alle Ticks unter demselben scharfen Stop bilden ein
Schutzereignis. Neue Position, neue Positions-Epoche, geänderte Menge oder neu
gesetzter Stop → neues Ereignis, das nicht von einem alten Dedup-Eintrag
verschluckt wird (D8).

Zwei-Phasen-Persistenz `PREPARED → FINALIZED` mit atomarem Temp-Rename. Ein
`PREPARED`-Rest nach Restart bedeutet „Zustellung unbewiesen" und blockiert
dauerhaft, statt einen zweiten Intent zu erzeugen (D4).

## Maschinenlesbare Evidence

`docs/evidence/risk/4186_stop_loss_consumer_dedup.json`
(Schema `cdb-stop-loss-consumer-evidence/v1`) enthält Commit-SHA,
Contract-Versionen, Protection-Status, Evidence-Gaps, alle Szenario-Ergebnisse,
den Shadow-Report und die Safety-Boundaries.

Der Manifest-Generator ist gegen Drift getestet
(`tests/unit/safety/stop_loss/test_evidence_manifest.py`): das committete
Artefakt muss zum aktuellen Verhalten passen.

Der Manifest-`commit_sha` bindet den Code-Commit, auf dem der Lauf erfolgte;
`worktree_dirty` weist aus, ob dieser SHA exakt gilt. Das Manifest wird deshalb
**nach** dem Code-Commit generiert und separat nachgeführt: `commit_sha` zeigt
auf den Commit, der den bewiesenen Code enthält, bei `worktree_dirty: false`.
Ein späterer Head (z. B. Review-Fixes) erfordert eine erneute Generierung.

## Grenzen

```text
lr_verdict: NO-GO
live_go: false
echtgeld_go: false
productive_adapter_enabled: false
productive_queue_enabled: false
productive_db_write: false
real_stack_persistence_proven: false
risk_limits_changed: false
```

- Keine Risk-, Exposure-, Drawdown- oder Positionsgrenze verändert.
- Keine produktive DB-Migration, keine MCP-Mutation, keine BLUE/RED-Änderung.
- PR #4187 und Issue #4184 unberührt.
- Board-Stage `trade-capable` ist kein Live-Go.
