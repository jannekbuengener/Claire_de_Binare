# Issue & Comment Translation Integration

**Status:** `RETIRED / NOT PRESENT ON MAIN` (reconciled 2026-06-05)

## Current repo truth

Diese Datei beschreibte einmal eine geplante GitHub-Actions-Integration mit:

- `.github/workflows/translate-issues.yml`
- `scripts/translate.js`

**Beide Artefakte existieren im Working Repo nicht.** Es gibt keinen aktiven Translation-Workflow auf `main`.

## Operator guidance

- Keine Setup-Schritte aus diesem Dokument ausführen.
- Für Issue-/Comment-Automation siehe `.github/README.md` und `docs/runbooks/CONTROL_REGISTER.md`.
- Falls Translation wieder gebraucht wird: neues Issue + expliziter Scope; dieses Dokument nicht als SSOT behandeln.

## Historical note

Der ursprüngliche Entwurf nutzte LibreTranslate (Default) bzw. optional DeepL (`DEEPL_API_KEY`).
Die folgenden Abschnitte bleiben nur als Archiv-Kontext erhalten und sind **nicht operativ**.

<details>
<summary>Archived original overview (do not execute)</summary>

The planned workflow would have translated new/edited issues and comments to German,
posted `[Übersetzung — DE]` bot comments idempotently, and used LibreTranslate or DeepL.

Planned files (never landed on main):

- `.github/workflows/translate-issues.yml`
- `scripts/translate.js`

</details>

## SSOT boundary

- Repo/engineering status: `CURRENT_STATUS.md`
- Live-Readiness: **NO-GO** — `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
