# CDB Office Pack — Taskplan Überblick (beide Repos)
Stand: 2025-12-16 (Europe/Berlin)

## Zielbild
Du willst **Überblick + Kontrolle + delegierbare Ausführung**.  
Daher: **Docs Hub = Canon/Knowledge/Reports**, **Working Repo = Code/Compose/Runtime**.

## Inputs (fix)
- Working Repo: `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare`
- Docs Hub Repo: *per Suche über `DOCS_HUB_INDEX.md` ermitteln* (Phase 0)

---

## Phase 0 — Repo Discovery & Baseline Snapshot
**Outcome:** Claude/Copilot arbeiten mit echten Pfaden + sauberem Ausgangszustand.

### Schritte
1. Docs Hub Pfad finden (PowerShell):
   ```powershell
   $root = "C:\Users\janne\Documents\GitHub\Workspaces"
   Get-ChildItem $root -Directory | Where-Object {
     Test-Path (Join-Path $_.FullName "DOCS_HUB_INDEX.md")
   } | Select-Object FullName
   ```
2. In **beiden Repos**: `git status`, `git branch`, `git log -1`, untracked files.

### DoD (Definition of Done)
- Zwei absolute Pfade (WORKING_REPO + DOCS_HUB_REPO) liegen vor.
- Baseline-Snapshot als Text (Branch + Status + letzter Commit).

---

## Phase 1 — Prompt-Migration `.txt → .md` (Docs Hub)
**Outcome:** Keine aktiven `.txt`-Prompts mehr, alles `.md` mit Frontmatter.

### Schritte
- Alle `.txt` finden (agents/prompts + Root `copilot.txt`, `gemini.txt`).
- 1:1 nach `.md` migrieren (kein Rewriting).
- Frontmatter ergänzen + `#` Titel.
- `.txt` oben als **DEPRECATED** markieren + Link zur `.md`.
- `DOCS_HUB_INDEX.md` Referenzen `.txt` → `.md` aktualisieren.

### DoD
- `.md` existiert für jede `.txt`.
- `.txt` bleibt erhalten, aber deprecated.
- Index referenziert nur noch `.md`.

---

## Phase 2 — Büro-Files Scan (Docs Hub)
**Outcome:** Neue Büro-Dateien sind einsortiert: OK / OK+Hinweis / Konfliktpotenzial.

### Schritte
- Liste der neuen Files (Pfad + Zweck 1 Satz).
- Klassifizieren (OK / OK+Hinweis / Konfliktpotenzial).
- Duplicate-Risiken flaggen (z. B. `governance/CONSTITUTION.md` vs `governance/CDB_CONSTITUTION.md`) — **nur markieren**.

### DoD
- `BUERO_FILES_REVIEW.md` liegt vor (1 Report).

---

## Phase 3 — Weekly Status Digest (Docs Hub)
**Outcome:** Wöchentlich 1 Seite „Was ist wirklich passiert?“.

### Schritte
- Ordner `knowledge/logs/weekly_reports/` anlegen (falls fehlt).
- `weekly_report_TEMPLATE.md` erstellen (max 1 Seite).
- Beispielreport `weekly_report_20251216.md` erstellen.

### DoD
- Template + Beispiel existieren.
- Keine API/Token-Annahmen.

---

## Phase 4 — M7 Skeleton (Working Repo)
**Outcome:** Paper Trading ist als Plan strukturierbar und delegierbar.

### Schritte
- `M7_SKELETON.md` anlegen:
  - 5–8 Cluster (Data/Feed, Signal, Risk, Execution, PSM, Observability, Reporting, Ops)
  - je 3–7 Subtasks mit Akzeptanzkriterien
  - Abhängigkeiten markieren (`depends-on`, `blocked-by`)

### DoD
- Skeleton ist „issue-ready“ (Titel + Akzeptanzkriterium).

---

## Phase 5 — Dockerfile & Stack Hardening (Working Repo) — REPORT FIRST
**Outcome:** Hardening-Backlog mit MUST/SHOULD/NICE + konkrete Diff-Vorschläge (noch nicht anwenden).

### Schritte
- Inventar: Dockerfiles + Compose-Dateien.
- Checks (Dockerfile): non-root, pinned base, minimal deps, no secrets, healthcheck.
- Checks (Compose): read_only, cap_drop, security_opt, resources, networks.
- `DOCKER_HARDENING_REPORT.md` erstellen + Diff-Snippets im Report.

### DoD
- Report existiert.
- Keine Änderungen an Runtime/Compose außer Report-Datei.

---

## Phase 6 — Papertrading Ops Setup + Execution Config (Working Repo)
**Outcome:** Papertrading operational (Start/Stop/Health/Smoke), safe defaults.

### Schritte
- `.env.example` Flags ergänzen (paper/live/dry-run, execution toggles).
- `knowledge/operating_rules/runbook_papertrading.md` erstellen (ausführbar, kurz).
- Validierung: `make docker-up` → `make docker-health` → smoke.

### DoD
- Runbook + `.env.example` Update liegen vor.
- Kein Live-Trading aktiviert, keine Secrets.

---

## Risikosteuerung (hart)
- Hardening: **erst Report**, dann separate Diff-Phase.
- Keine Secrets. Keine Live-Keys. Keine autonomen Merges.
