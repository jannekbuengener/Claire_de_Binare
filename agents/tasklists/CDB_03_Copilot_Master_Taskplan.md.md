🔧 Konsolidierte Datei (FINAL)
CDB_03_Copilot_Master_Taskplan.md

Das folgende kannst du 1:1 als neue Datei speichern.

# CDB Copilot – Master Taskplan (KANONISCH)
Stand: 2025-12-16

Diese Datei ist die **einzige operative Arbeitsgrundlage für Copilot**.
Sie kombiniert:
- detaillierte Tasklists (Docs Hub + Working Repo)
- Regeln & Acceptance
- die automatische Erstellung von GitHub Issues

---

## Repo-Zuordnung
- **Docs Hub** → Tasks A–C
- **Working Repo** → Tasks D–F

---

# TASK A — Prompt-Migration `.txt → .md` (Docs Hub)

## Scope
- `agents/prompts/*.txt`
- Root: `copilot.txt`, `gemini.txt`

## Steps
1. Alle `.txt` Dateien inventarisieren (Pfad + Größe).
2. Für jede Datei:
   - `.md` anlegen (1:1 Inhalt, kein Rewriting)
   - Frontmatter:
     ```yaml
     ---
     role: prompt
     agent: <COPILOT|GEMINI|CLAUDE|CODEX|UNKNOWN>
     status: migrated
     source: <original filename>
     ---
     ```
   - `# Titel` aus Dateiname ableiten
3. `.txt` **nicht löschen**, sondern:
   - `DEPRECATED` Hinweis + Link zur `.md`
4. `DOCS_HUB_INDEX.md`:
   - `.txt` Referenzen → `.md`

## Acceptance
- Jede `.txt` hat `.md`
- Index referenziert nur `.md`

## Stop
- Agent unklar → STOP + Liste

---

# TASK B — Büro-Files Scan (Docs Hub)

## Steps
1. Liste aller neuen Büro-Files (Pfad + Zweck, 1 Satz).
2. Klassifikation:
   - OK
   - OK+Hinweis
   - Konfliktpotenzial
3. Duplicate-Risiken flaggen (z. B. `CONSTITUTION.md` vs `CDB_CONSTITUTION.md`).
4. Report schreiben: `BUERO_FILES_REVIEW.md`.

## Acceptance
- 1 faktischer Report
- keine Lösungen implementiert

---

# TASK C — Weekly Status Digest (Docs Hub)

## Steps
1. Ordner sicherstellen:


knowledge/logs/weekly_reports/

2. `weekly_report_TEMPLATE.md` (max. 1 Seite).
3. Beispiel:


weekly_report_20251216.md


## Acceptance
- Template + Beispiel vorhanden

---

# TASK D — M7 Skeleton (Working Repo)

## Steps
1. `M7_SKELETON.md` anlegen.
2. Cluster (5–8):
- Data/Feed
- Signal
- Risk
- Execution
- PSM
- Observability
- Reporting
- Ops
3. Pro Cluster:
- 3–7 Subtasks
- Akzeptanzkriterium
- Dependencies markieren

## Acceptance
- Issue-ready Skeleton

---

# TASK E — Docker Hardening REPORT (Working Repo)

## Steps
1. Inventar:
- alle `Dockerfile*`
- alle `docker-compose*.yml`
2. Dockerfile Checks:
- non-root
- pinned base
- minimal deps
- keine Secrets
- Healthcheck
3. Compose Checks:
- `read_only`
- `cap_drop`
- `security_opt: no-new-privileges`
- Resource Limits
- Network Segmentation
4. Report:


DOCKER_HARDENING_REPORT.md


## Acceptance
- **Nur Report**
- keine Runtime-Änderungen

---

# TASK F — Papertrading Ops Setup (Working Repo)

## Steps
1. `.env.example` erweitern:
- MODE=paper (default)
- EXECUTION=dry-run (default)
2. Runbook:


knowledge/operating_rules/runbook_papertrading.md

3. Validierung:
- make docker-up
- make docker-health
- smoke check

## Acceptance
- Safe Defaults
- kein Live-Trading
- keine Secrets

---

# TASK G — GitHub Issues automatisch anlegen (Copilot)

## Ziel
Alle oben definierten Tasks als **strukturierte Issues** anlegen.

## Steps
1. Tasks A–F extrahieren.
2. Pro Task **ein Issue** anlegen:
- Titel: `docs:`, `ops:`, `sec:`, `plan:`
- Beschreibung + Checkliste
- Acceptance Criteria
3. Labels:
- `type:docs`, `type:ops`, `type:security`, `type:plan`
- `prio:P1`, `prio:P2`
- `status:ready`
4. Milestones:
- M7 → Tasks D + F
- M8 → Task E
5. Dependencies:
- Hardening Diff blockiert bis Report abgenommen
- Live-Trading blockiert bis Papertrading fertig

## Output
- Liste aller Issues (Titel + Link)
- Kurzsummary (Issues pro Repo)

## Stop
- Unklarer Scope → Issue `status:blocked`