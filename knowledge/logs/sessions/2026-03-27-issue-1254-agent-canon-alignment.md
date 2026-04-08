# Session Log — 2026-03-27 — Issue #1254 Agent Canon/Status Alignment

**Topic:** #1254 — Review and propagate canon/status entrypoint alignment across remaining agent docs
**PR:** #1289 — merged 2026-03-27T13:53:27Z (commit `6d650a2`)
**Result:** DONE / Issue closed

---

## Was getan wurde

Follow-up zu #1232/#1233. Root `AGENTS.md`, `agents/AGENTS.md` und `agents/roles/CODEX.md` waren bereits aligned.

Verbleibende Drift bereinigt in 4 Dateien:

| Datei | Änderung |
|---|---|
| `agents/roles/GEMINI.md` | +Status-Dateien in MUST READ FIRST; +Canon/Status-Guardrail-Einzeiler; hardcodierten Snapshot-Text durch Canon-Pointer ersetzt |
| `agents/roles/COPILOT.md` | +Status-Pointer-Einzeiler nach MUST READ FIRST |
| `agents/CLAUDE.md` | +`docs/meta/WORKING_REPO_CANON.md` in MUST READ FIRST |
| `agents/roles/CLAUDE.md` | +`docs/meta/WORKING_REPO_CANON.md` in MUST READ FIRST; Section-10-Divergenz bereinigt |

## Bekanntes Nachfolgeproblem

Lokaler `main` divergiert von `origin/main` (3 Commits `76e04ba`, `7ca5f61`, `a471670` lokal vorhanden, nicht auf remote). Ursache: Codex-Parallelaktivität. Muss separat bereinigt werden (`git reset --hard origin/main` nach Prüfung).
