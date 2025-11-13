# Runbook – Cleanroom Execution Blueprint

## Track 1: Dry-Run-Merge (ohne Löschungen)

### 1. Vorbereitung (Go/No-Go)
1.1 Go-Kriterien: CI zuletzt grün, Inventur-Plan abgenommen, Owner verfügbar.
1.2 No-Go: Offene Security-Funde, fehlendes Backup, Blocker im Risk Register.
1.3 Beweis der Wirkung: Screenshot/Link zum letzten erfolgreichen CI-Run.

### 2. Branch anlegen & Artefakte hinzufügen
2.1 GitHub Desktop Pfad
    - Repository öffnen → `Branch` → `New Branch…` → Name `feature/cleanroom-dryrun`.
    - Dateien hinzufügen (Drag & Drop aus Planung):
      - `docs/CLEANUP_PLAN.md`
      - `docs/MIGRATION_MAP.md`
      - `docs/SECURITY_SANITATION_PLAN.md`
      - `docs/PR_CLEANROOM_DRYRUN.md`
    - .gitignore patchen: Rechtsklick `.gitignore` → „Öffnen in Editor“ → Diff aus Phase II einfügen.
    - Beweis: GitHub Desktop zeigt vier neue Dateien + 1 geänderte `.gitignore`.

2.2 CLI-Äquivalent (Bash / PowerShell)
```bash
git checkout -b feature/cleanroom-dryrun
cp path/to/plans/CLEANUP_PLAN.md docs/CLEANUP_PLAN.md
cp path/to/plans/MIGRATION_MAP.md docs/MIGRATION_MAP.md
cp path/to/plans/SECURITY_SANITATION_PLAN.md docs/SECURITY_SANITATION_PLAN.md
cp path/to/plans/PR_CLEANROOM_DRYRUN.md docs/PR_CLEANROOM_DRYRUN.md
cat <<'EOF' >> .gitignore
## Cleanroom ignore – artifacts & caches
artifacts/
backoffice/artifacts/
evidence/
__pycache__/
.coverage
*.coverage*
*.log
tmp_*
backups/
operations/logs/
*.sqlite*

## Secrets
.env
.env.*
*.pem
*.key
*.pfx
id_*
*.secrets
EOF
git status
```
Beweis: git status listet neue Dateien und geändertes .gitignore.

### 3. Commit & Push
3.1 GitHub Desktop: Summary `chore(cleanroom): add plans + gitignore (dry run)` → Commit → Push origin.
3.2 CLI:
```bash
git add docs/CLEANUP_PLAN.md docs/MIGRATION_MAP.md docs/SECURITY_SANITATION_PLAN.md docs/PR_CLEANROOM_DRYRUN.md .gitignore
git commit -m "chore(cleanroom): add plans + gitignore (dry run)"
git push -u origin feature/cleanroom-dryrun
```
Beweis: Push-Ausgabe Exitcode 0.

### 4. PR erstellen
4.1 Titel: `chore(cleanroom): prepare structure & policy dry run`
4.2 Body: aus `docs/PR_CLEANROOM_DRYRUN.md`.
4.3 Labels: `cleanup`, `documentation`, `security-prep`; Milestone „Cleanroom Phase II Dry-Run“.
4.4 Reviewer `@DevLead`, `@DocsLead`, `@SecurityLead`.
4.5 Beweis: Pull-Request-Link mit Status „Open“.

### 5. Go/No-Go vor Merge
Go: CI grün, Checklist abgezeichnet, keine Secrets.
No-Go: Neue Findings, Review blockiert.
Rollback lokal: `git revert <commit>`; Remote: PR schließen, Branch löschen (`git push origin --delete feature/cleanroom-dryrun`).
Beweis: Merge-Preview frei von roten Checks.


## Track 2: Security-Sanitation (History-Rewrite)

### 1. Vorbereitung (Go/No-Go)
1.1 Mirror-Backup erstellen: `git clone --mirror <REMOTE> repo-cleanroom-backup.git`.
1.2 Freeze kommunizieren (Slack/Teams + Mail).
1.3 Stakeholder & Owner (Security, Ops, Dev) bestätigen Wartungsfenster `<MAINT_WINDOW>`.
1.4 Neues Secret-Set generiert (z. B. `<SECRET_DB_PASSWORD>`).
1.5 Beweis: Backup-Ordner vorhanden + Stakeholder-Leserückmeldung.

### 2. filter-repo/BFG Planung
2.1 Liste der Pfade/Muster: `.env`, `postgres_env.txt`, `postgres_env_runtime.txt`, `.env.*`, `*.pem`, `*.key`, `*.pfx`, `id_*`, `*.secrets`, `*.sqlite*`.
2.2 Befehle vorbereiten:

**Alternative 1 – git filter-repo**
```bash
git clone <REMOTE> sanitized-repo
cd sanitized-repo
git filter-repo --path .env --path postgres_env.txt --path postgres_env_runtime.txt   --path-glob ".env.*" --path-glob "*.pem" --path-glob "*.key" --path-glob "*.pfx"   --path-glob "id_*" --path-glob "*.secrets" --path-glob "*.sqlite*" --invert-paths
```

**Alternative 2 – BFG Repo-Cleaner**
```bash
java -jar bfg.jar --delete-files ".env,postgres_env.txt,postgres_env_runtime.txt"   --delete-folders ".env"   --delete-files "*.{pem,key,pfx,secrets}"   --delete-files "*.sqlite*"
cd sanitized-repo.git
git reflog expire --expire=now --all && git gc --prune=now --aggressive
```
Beweis: `git status` leer, sensitive Dateien entfernt.

### 3. Verifikation lokal
```bash
gitleaks detect --no-git --source .
pytest -q
docker compose -f compose.yml run --rm cdb_core pytest -q  # Beispiel-Compose-Smoke
```
Beweis: Exitcodes 0, Gitleaks „no leaks detected“.

### 4. Push Protection & Force Push
4.1 GitHub UI → Settings → Code security → Secret scanning (Enable) & Push protection (Enable).
4.2 Force-Push nach Freigabe:
```bash
git push --force-with-lease origin <MAIN>
```
Beweis: GitHub Security Center zeigt „Push protection active“, Force-Push erfolgreich.

### 5. Kommunikation
Mail/Slack auf Basis `COMMS_PACK.md`: Hinweis auf neues Clone-Erfordernis.
Re-Clone-Anleitung senden:
```bash
git clone <REMOTE> cleanroom-new
```
Beweis: Team-Kommentare/Sign-off.

### 6. Rollback
Falls Regression: aus Mirror wiederherstellen:
```bash
git remote add rollback ../repo-cleanroom-backup.git
git push --force origin refs/heads/<MAIN>:refs/heads/<MAIN>
```
Kommunikationstext: „Revert durchgeführt – bitte alte Klone weiterverwenden“.
Beweis: Remote-Historie identisch mit Backup.


## Track 3: Doku-Kuration & Link-Fix

### 1. Aufgabenliste (Moves – keine Ausführung hier)
- `archive/legacy_quickstart/QUICK_START.md` → `docs/quickstart/QUICK_START.md`
- `backoffice/docs/ARCHITEKTUR.md` → `docs/architecture/ARCHITEKTUR.md`
- `backoffice/docs/SECURITY.md` → `docs/security/SECURITY.md`
- `evidence/TEST_RERUN_EVIDENCE_2025-11-11.md` → `docs/reports/TEST_RERUN_EVIDENCE_2025-11-11.md`
- `backoffice/SESSION_MEMO_*` → `docs/meetings/SESSION_MEMO_*.md` (kuratieren)
*(vollständige Liste: `MIGRATION_MAP.md`)*

### 2. Link-Check Script (Entwurf)
```python
#!/usr/bin/env python3
import os, re, sys, requests

root = os.path.join(os.getcwd(), "docs")
pattern = re.compile(r"\[(.*?)\]\((.*?)\)")
broken = []

for dirpath, _, files in os.walk(root):
    for name in files:
        if not name.endswith(".md"):
            continue
        path = os.path.join(dirpath, name)
        with open(path, encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, 1):
                for _, target in pattern.findall(line):
                    if target.startswith("http"):
                        try:
                            resp = requests.head(target, allow_redirects=True, timeout=5)
                            if resp.status_code >= 400:
                                broken.append((path, line_no, target, resp.status_code))
                        except Exception as e:
                            broken.append((path, line_no, target, str(e)))
                    else:
                        abs_target = os.path.normpath(os.path.join(dirpath, target))
                        if not os.path.exists(abs_target):
                            broken.append((path, line_no, target, "missing"))
if broken:
    for entry in broken:
        print("BROKEN", *entry)
    sys.exit(1)
print("All links OK")
```

Beweis: Script liefert „All links OK“ (Exitcode 0).

### 3. PR-Vorlage
- **Titel:** `docs(cleanroom): consolidate documentation tree`
- **Body:**
  - Checkliste (z. B. `- [ ] MIGRATION_MAP abgearbeitet`).
  - Akzeptanzkriterien (404-Check 0, Redundanzen de-dupliziert).
- **Labels:** `documentation`, `cleanup`.
- **Beweis:** PR diff zeigt nur Doc-Moves & Link-Fixes.

### 4. Go/No-Go & Rollback
Go: Sanitation abgeschlossen, MIGRATION_MAP freigegeben, Link-Check grün.
No-Go: Offene PRs, Link-Check liefert Fehler.
Rollback: `git revert` pro Move-Commit oder `git checkout -- docs/<file>` vor Commit.
Beweis: Wiederholter Link-Check nach Rollback zeigt keine Fehler.