# Evidence: Stop-Loss fail-closed und Kill-/Unwind-Drill (#4182)

**Datum:** 2026-07-29

**Getesteter Code-Commit:** `aab4cb270b0ced190b50898e8e0f809c5ce6934d`

**Run-ID:** `4182_aab4cb27_20260729T114634Z`

**Verdict:** `PASS_FAIL_CLOSED_UNAVAILABLE`

**Stop-Loss-Protection:** `UNAVAILABLE`

**LR:** `NO-GO` (unverändert)

## Brain Evidence

```text
context_tool_status: available
context_trust_level: none
records_found: 0
context_brain_used: false
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
```

## Scope und Claim-Grenze

Der isolierte Mock-/Dry-run-Stack belegt den fail-closed Pfad. Er belegt
**keinen** Stop-Loss-Consumer, Preis-Trigger, persistenten Dedup-State oder
Reduce-only-Execution-Contract. `stop_loss_pct` bleibt `ARTIFACT_ONLY`;
`END_TO_END_PROVEN` ist unzulässig.

Der Stack verwendete einen eindeutigen Compose-Projektnamen, eigene
Redis-/Postgres-/Kill-State-Volumes, keine Host-Ports, temporäre Dummy-Secrets
und keine BLUE-/RED-Aktivierung. Verbindliche Flags:
`DRY_RUN=1`, `MOCK_TRADING=true`, `USE_REAL_BALANCE=false`.

## D1-D8

| Szenario | Ergebnis | Evidenz |
|---|---|---|
| D1 | `PASS` | Explizites `INACTIVE`; synthetische Order erreichte nur Mock-Execution. |
| D2 | `PASS` | `ACTIVE` blockierte Risk-Submission und Execution-Recheck. |
| D3 | `PASS` | Fehlende State-Datei blockierte beide Dienste; kanonisch `KILL_SWITCH_ACTIVE` mit `reason=system_error`. |
| D4 | `PASS` | Korrupter State blieb unverändert und fail-closed. |
| D5 | `PASS` | Risk-/Execution-Restart bei fehlendem State blieb blockierend. |
| D6 | `UNWIND_NOT_PROVEN` | Bestehender Unwind erzeugte einen SELL-Auftrag ohne belegten Reduce-only-Vertrag; Position 0.01 -> 0.01. |
| D7 | `PASS_FAIL_CLOSED_UNAVAILABLE` | Schutzbedürftiges Signal wurde mit `STOP_LOSS_PROTECTION_UNAVAILABLE` vor Order-Erzeugung abgewiesen. |
| D8 | `EXIT_REJECTED_UNWIND_NOT_PROVEN` | Test-only Mock-Rejection hielt die Restposition sichtbar; Position 0.01 -> 0.01. |

Kein Szenario blieb `NOT_RUN`; ein Positionsanstieg wurde nicht beobachtet.

## Maschinenlesbare Evidence

Das reviewte Manifest liegt in
`docs/evidence/risk/4182_stop_loss_kill_unwind_drill.json`. Es enthält
Commit-SHA, Run-ID, Compose- und Image-Hashes, Safe-Mode-Flags,
Szenario-Status, Positionswerte, Rohartefakt-SHA256 und Cleanup-Ergebnis.

Der Report bindet den getesteten Code-Commit. Der nachfolgende Evidence-Commit
ist absichtlich ein anderer SHA; der vollständige Drill muss deshalb am
finalen PR-HEAD erneut ausgeführt werden. Das untracked Rohmanifest dieses
zweiten Laufs ist die exakte Head-SHA-Evidence.

## Cleanup

```text
containers_remaining: 0
volumes_remaining: 0
networks_remaining: 0
cleanup: PASS
run_error: null
```

## Verbleibende Lücken

- kein End-to-End-Stop-Loss-Consumer oder Preis-Trigger
- kein persistenter Dedup-State
- kein belegter Reduce-only-Unwind
- kein belegtes Kill-Cancel
- kein restart-sicherer Stop-Loss

Darum bleibt #4152 offen. Dieses Ergebnis autorisiert weder Live-Trading noch
Echtgeld und ändert das LR-`NO-GO` nicht.
