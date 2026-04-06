# Session Log: Issue #1411 — Secrets-/Runbook-/Evidence-Canon-Reconcile

**Date:** 2026-03-31
**Issue:** #1411
**Scope:** docs(secrets): reconcile active runbooks and evidence to BLUE+RED / SECRETS_PATH canon

---

## Was getan wurde

- **`knowledge/governance/SECRETS_POLICY.md`** — Vollständig neugeschrieben. `.cdb_local/.secrets/.env.compose` und bash-Setup-Instructions durch `~/Documents/.secrets/.cdb` / `Rotate-Secrets.ps1`-Pfad ersetzt.
- **`governance/SECRETS_POLICY.md`** (root) — Gleiche Bereinigung. Auf kanonische `knowledge/`-Version verwiesen.
- **`knowledge/governance/SECRET_ROTATION_POLICY.md`** — Incident-Playbook Step 4: `stack_up.ps1` → BLUE+RED compose. "Stack Startup (B-lite)"-Abschnitt als `[LEGACY COMPAT]` markiert. `cdb-secrets-sync.ps1` als Legacy-Compat-Verweis markiert.
- **`tools/secrets/README.md`** — Integration-Abschnitt: `.env.runtime`-Auto-Load als `[LEGACY COMPAT]` markiert. `cdb-secrets-sync.ps1` und `set_secrets.ps1` als Legacy-Compat klargestellt.
- **`tools/secrets/EVIDENCE.md`** — Acceptance-Table-Row "B-lite integration" → "Stack-Start nach Rotation / BLUE+RED compose". Verification Section 9: `stack_up.ps1` → BLUE+RED compose commands.
- **`tools/secrets/evidence/sample_apply_output.md`** — "Next steps" in Sample-Output: `stack_up.ps1` → BLUE+RED compose commands (entspricht aktuellem Tool-Output).
- **`tools/secrets/evidence/sample_export_output.md`** — "Next step" in Sample-Output und "Stack Startup (B-lite Integration)"-Abschnitt: `stack_up.ps1` → BLUE+RED compose, als `[LEGACY COMPAT]` markiert.
- **`tools/stack_boot.ps1`** — Secrets-Check (Schritt 3): `.secrets/` und `.cdb_local/.secrets/` → `~/Documents/.secrets/.cdb/` korrigiert. Fix-Instructions aktualisiert.
- **`infrastructure/scripts/manage_secrets.ps1`** — `$secretDir`: `.cdb_local/.secrets` → `~/Documents/.secrets/.cdb` (kanonischer Pfad).
- **`knowledge/content/ONBOARDING_QUICK_START.md`** — Setup-Schritt 4 und "Wie funktionieren Secrets"-Abschnitt: `.cdb_local.secrets/` → `~/Documents/.secrets/.cdb/`.
- **`knowledge/security/SECURITY_HARDENING.md`** — MEXC-Secrets YAML: `../.cdb_local/.secrets/` → `${SECRETS_PATH}`. Rotation-Instructions: PowerShell mit kanonischem Pfad. Emergency-Stop-Commands: `docker-compose` → `docker compose`.
- **`knowledge/compliance/HARDENING_VERIFICATION.md`** — Secret-File-Pfade, Compliance-Tabelle, Runbook-Beispiel, Criterion-G-Block: alle `.cdb_local/.secrets/` → `~/Documents/.secrets/.cdb/` bzw. BLUE+RED. `stack_up.ps1` als `[LEGACY COMPAT]` markiert.
- **`knowledge/operations/DOCKER_STACK_RUNBOOK.md`** — Runbook-Beispiele (Section "Secret File Errors"), Step 4 in Security-Incident, Appendix-Pfadliste: `.cdb_local/.secrets/` → `~/Documents/.secrets/.cdb/`.
- **`knowledge/ARCHITECTURE_COCKPIT.md`** — Change-Safety-Note: `.cdb_local/.secrets` → `~/Documents/.secrets/.cdb`.
- **`CONTRIBUTING.md`** — Setup-Abschnitt: `.cdb_local/.secrets/.env.compose` + `stack_up.ps1` → `Rotate-Secrets.ps1 apply` + BLUE+RED compose.
- **`infrastructure/compose/COMPOSE_LAYERS.md`** — Secret-Management-Abschnitt: `.cdb_local/.secrets/` → `~/Documents/.secrets/.cdb/` via `${SECRETS_PATH}`.

---

## Bewusst nicht angefasst

- `docs/archive/` — Explizit ausgeschlossen.
- `knowledge/staging/`, `knowledge/reviews/`, `knowledge/context_build/` — Explizit ausgeschlossen.
- `knowledge/logs/sessions/` — Historische Session-Logs, keine Arbeitsanweisungen.
- `infrastructure/scripts/stack_up.ps1` — Script-Logik bleibt; ist Legacy/Compat-Pfad. `.env.runtime`-Auto-Load technisch noch aktiv (nicht gelöscht), aber in allen Docs als `[LEGACY COMPAT]` markiert.
- `infrastructure/scripts/run_e2e.ps1` — `.env.runtime`-Referenzen sind intern/kommentar-basiert; Script-Header sagt explizit "Runtime-/Operator-Pfad (BLUE+RED) is NOT used here." Kein Handlungsbedarf.
- `tools/cdb-secrets-sync.ps1` — Script-Logik bleibt (synct `.cdb_local → .secrets`); als Legacy-Compat in README markiert.
- `tools/set_secrets.ps1` — Schreibt in Repo-lokales `.secrets/` (Legacy-Pfad). Script-Logik bleibt; in README als "Legacy-Pfad" deklariert.
- `knowledge/SYSTEM_INVARIANTS.md` — `stack_up.ps1`-Referenz ist reine Implementierungsnotiz für TLS, keine Operator-Anweisung.
- `knowledge/security/DOCKER_HARDENING_REPORT.md` — Sicherheits-Audit-Report von 2025-12-27; passive Dokumentation, kein Operator-Arbeitsfluss.
- `docs/env/index.md` — Bereits korrekt: `stack_up.ps1` als Legacy explizit markiert.

---

## Definition of Done — Status

- ✅ Aktive Secrets-/Runbook-/Evidence-Doku folgt konsistent `~/Documents/.secrets/.cdb` + BLUE+RED compose
- ✅ `.cdb_local/.secrets`, Repo-`.secrets`, `.env.runtime`, `stack_up.ps1` stehen nicht mehr als normale Arbeitsanweisung in aktiven Secrets-/Rotation-/Evidence-Flows
- ✅ Verbleibende Legacy-Verweise klar als `[LEGACY COMPAT]` oder "nicht kanonisch" markiert
- ✅ Diff fokussiert auf #1411, keine Archive/Discovery/Architektur-Ausweitung
