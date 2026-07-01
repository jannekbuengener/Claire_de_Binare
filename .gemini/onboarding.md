# Gemini Onboarding Router

Wenn ein Gemini-Agent einen `/onboarding`-, `onboarding`-, `onboarding durchführen`-, `mach onboarding`-, `fresh agent onboarding`-Intent oder equivalent erkennt:

1. **Führe aus**: `python -m tools.onboarding_orchestrator`
2. **Starte nicht** `cdb-session-start` oder `onboarding_doctor` als primären Pfad.

Wenn der Intent auf eine geführte Generalprobe zielt (`onboarding rehearsal`, `guided rehearsal`,
`rehearsal mode`, `generalprobe`, `tu so als waere ich neuer entwickler`, `reisefuehrer`,
`nicht staendig fragen`, `realitaetsnah simulieren`, `onboarding als test-szenario`):

1. **Führe aus**: `python -m tools.onboarding_simulation --mode guided-rehearsal --role developer`
2. **Guided rehearsal ist kein Setup-GO und kein Live-Go.** Mutierende Schritte werden nur simuliert.
3. **Der Agent führt als Reiseführer autonom.** Kein Fragebogen, keine endlosen Rückfragen.
4. **Nur bei echten Human-Gates rückfragen** (z.B. "Soll ich jetzt wirklich das Setup ausführen?").
5. **Read-only-Prüfungen ausführen** (git, gh view, python tools), wenn sicher und sinnvoll.
6. **Mutierende Schritte (Docker, .env, deps) nur beschreiben und simulieren**, nicht ausführen.
7. **Nach dem guided-rehearsal-Lauf:** KEINE Anschlussfrage, keine Einladung,
   kein "Wenn du willst..." mit Optionen.
   Der letzte Ausgabe-Absatz MUSS ein Abschluss sein: Status, ein naechster Schritt, STOP.

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

## Agent Onboarding Readiness

Optionaler, rein informativer Readiness-Hinweis (kein CI-Gate, kein Blocker).
Kanonische Beschreibung: [`../docs/onboarding/AGENT_COMPATIBILITY_READINESS.md`](../docs/onboarding/AGENT_COMPATIBILITY_READINESS.md).
Externer Scanner `npx -y agent-compatibility@0.1.7 .` ist optional; fehlendes Node/npm/Netz (`ENV_UNAVAILABLE`) ist kein Repo-Defekt. LR bleibt NO-GO.
