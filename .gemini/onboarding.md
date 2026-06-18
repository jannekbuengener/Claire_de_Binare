# Gemini Onboarding Router

Wenn ein Gemini-Agent einen `/onboarding`-, `onboarding`-, `onboarding durchführen`-, `mach onboarding`-, `fresh agent onboarding`-Intent oder equivalent erkennt:

1. **Führe aus**: `python -m tools.onboarding_orchestrator`
2. **Starte nicht** `cdb-session-start` oder `onboarding_doctor` als primären Pfad.
3. **Default output is the CDB Onboarding status card.**
4. **Read-only by default.** Do not create `.env`, initialize secrets, initialize context, write reports, create issues, or run Docker unless the user explicitly selects a next option after the status card.
5. **Routing-Hierarchie**: Dieser Router ist der kanonische Gemini-Onboarding-Pfad. Der Gemini-Bootloader in `GEMINI.md` (Repo-Root) verweist ergänzend auf diesen Router.
6. **Antwortvertrag**: Berichte nur `Status`, `State`, warnings, `allowed_next_actions`, `check_scope` und `skipped_checks`.
7. **Evidence-Abgrenzung (Pflicht)**: Trenne sauber zwischen geprüften und nicht geprüften Bereichen:
   - Ohne ausgeführte `git`/`gh`/`check`-Kommandos: "Repo-/Canon-Prüfung durchgeführt; GitHub-/Check-Live nicht geprüft."
   - Mit Live-Kommandos: "GitHub-/Repo-Live geprüft: <konkrete Kommandos und Ergebnis>."
   - `CURRENT_STATUS.md` ist Engineering-Ledger, nicht Live-Wahrheit.
   - LR-SSOT ist `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.
8. **Wording Contract**: Vermeide verbotene Phrasen:
   - Nicht: "Live-Wahrheit geprüft: Ja" (nur mit konkreten Kommandos)
   - Nicht: "trade-capable ist deaktiviert/aktiviert" (Board-Stage, kein Schalter)
   - Nicht: "alle systemischen Invarianten erfasst" (nach Teilreads)
   - Nicht: "CURRENT_STATUS.md ist Live-Wahrheit" (ist Ledger)
   - Nicht: "trade-capable erlaubt Live" / "ist Live-Go"
9. **Keine Management-Zusammenfassung**: Keine freie, zu selbstbewusste Zusammenfassung ohne Evidence-Abgrenzung.
10. **Keine erfundenen Optionen**: kein Legacy-Setup-Ast, keine Umnummerierung, keine direkte Setup-Ausfuehrung nach `check-only`.

## Safety Boundaries

- LR remains **NO-GO**
- `trade-capable` ist Board-/Stage-Kontext, kein Live-Go
- Keine Echtgeld-Transaktionen
- Keine Runtime-Änderungen
- Keine Secrets in Outputs
