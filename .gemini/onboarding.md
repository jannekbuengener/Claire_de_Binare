# Gemini Onboarding Router

Wenn ein Gemini-Agent einen `/onboarding`-, `onboarding`-, `onboarding durchführen`-, `mach onboarding`-, `fresh agent onboarding`-Intent oder equivalent erkennt:

1. **Führe aus**: `python -m tools.onboarding_orchestrator`
2. **Starte nicht** `cdb-session-start` oder `onboarding_doctor` als primären Pfad.
3. **Default output is the CDB Onboarding status card.**
4. **Read-only by default.** Do not create `.env`, initialize secrets, initialize context, write reports, create issues, or run Docker unless the user explicitly selects a next option after the status card.
5. **Routing-Hierarchie**: Dieser Router ist der kanonische Gemini-Onboarding-Pfad. Der Gemini-Bootloader in `GEMINI.md` (Repo-Root) verweist ergänzend auf diesen Router.

## Safety Boundaries

- LR remains **NO-GO**
- `trade-capable` ist nicht `Live-Go`
- Keine Echtgeld-Transaktionen
- Keine Runtime-Änderungen
- Keine Secrets in Outputs
