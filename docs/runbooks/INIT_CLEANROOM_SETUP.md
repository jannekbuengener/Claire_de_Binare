# INIT_CLEANROOM_SETUP.md

> Zweck: Erstkonfiguration des **Cleanroom-Repositories** für produktiven Einsatz – ohne Push/History-Änderungen.  
> Kontext: Neues lokales Repo unter `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binaire_Cleanroom`.

---

## 1) Repository-Health & Backup
**Ziel:** Jeder Change ist nachvollziehbar und reversibel.

- **Mirror-Backup (lokal, manuell):**
  ```powershell
  cd "C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binaire_Cleanroom"
  git rev-parse --short HEAD
  cd..
  git clone --mirror "C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binaire_Cleanroom" ".\_backup\cleanroom.mirror.git"
  ```
- **Datei-Backup (GFS-Empfehlung):**  
  Zielpfad `D:\DevBackups\auto\{yyyy-mm-dd}` – 14 tägliche, 8 wöchentliche, 6 monatliche Snapshots.
- **Health-Report (optional):** JSON mit Größe, Dauer, Exitcodes der Backups in `backups\health\report.json`.

---

## 2) Branch-Policy & Commits
**Ziel:** Saubere PR-Flows, eindeutige Historie.

- **Branch-Namen:**  
  - `cleanroom/docs-*` (Dokumoves)  
  - `cleanroom/security-*` (Sanitation/Policies)  
  - `cleanroom/ops-*` (Runbooks/CI/Infra)  
- **Commit-Konvention (Kurzform):**  
  - `init(cleanroom): …` – Initiale Struktur/Runbooks  
  - `docs(cleanroom): …` – Dokumentation/Linkfixes  
  - `security(cleanroom): …` – Secret/Policy-Anpassungen  
  - `chore(cleanroom): …` – Housekeeping
- **PR-Regeln (Empfehlung):**  
  - 1 Reviewer je Kategorie (Docs/Security/Dev)  
  - CI grün Pflicht (Lint, Tests, Secret-Scan)

---

## 3) Runbooks einbinden
**Ziel:** Operative Exekution ist standardisiert.

- **Ablage:** `docs/runbooks/` (Index vorhanden)  
- **Dry-Run-PR (ohne Löschungen):** Inhalte aus `RUNBOOK_CLEANROOM_EXEC.md` – Track 1.  
- **Security-Sanitation (koordiniert):** `SECURITY_SANITATION_PLAN.md` + Runbook Track 2.  
- **Doku-Kuration:** `MIGRATION_MAP.md` + Link-Checker aus Runbook Track 3.

---

## 4) GitHub-Setup (erst nach erster Push-Initialisierung)
**Ziel:** Schutzmechanismen aktivieren, bevor größere Arbeiten starten.
1. **Repository anlegen (GitHub Web):** `claire_de_binaire_cleanroom` (privat empfohlen).  
2. **Security aktivieren:** Settings → Code security →  
   - *Secret scanning* **Enable**  
   - *Push protection* **Enable**  
3. **Branch Protection:**  
   - `main`: Require PR, Require status checks (CI), Dismiss stale reviews, Block force pushes.  
4. **Dependabot (optional):** `.github/dependabot.yml` hinzufügen.

---

## 5) CI/Checks (leichtgewichtiger Start)
**Ziel:** Minimal lauffähige Pipeline.
- **Vorlage (empfohlen):** `.github/workflows/ci.yaml` mit Jobs:  
  1) `lint` (ruff/black), 2) `test` (pytest -q), 3) `secrets` (gitleaks detect), 4) `security` (bandit -q)  
- **Artefakte ausklammern:** `.gitignore` deckt `artifacts/`, `__pycache__/`, `.coverage` etc. ab.

---

## 6) Secrets & Beispiele
**Ziel:** Keine produktiven Secrets im Repo.
- **Behalte nur:** `.env.example`, `docker/**/.env.example` mit Platzhaltern.  
- **Keine Klartext-Secrets:** `.env`, `postgres_env*.txt`, `*.pem`, `*.key`, `*.pfx`, `*.sqlite*` sind ignoriert.  
- **Rotation-Policy:** Bei späterer Übernahme aus Alt-Repo → sofort rotieren & *filter-repo* in separatem Clone pro Runbook.

---

## 7) Sanitation- und Doku-Tracks orchestrieren
**Ziel:** Schrittweiser, risikoarmer Merge.
- **PR #1 (Dry-Run):** `.gitignore`-Patch + Docs-Struktur + Policies – *keine Löschungen*.  
- **PR #2 (Security-Sanitation):** Rotation + History-Rewrite (koordiniert, Force-Push erwartet).  
- **PR #3 (Docs-Kuration):** Virtuelle Moves realisieren, Linkcheck „0 broken“.  

---

## 8) Tagging & Release
**Ziel:** Abschluss der Cleanroom-Phase transparent machen.
- **Tag:** `v1.0.0-cleanroom` (nach Merge aller Tracks)  
- **Release Notes (Snippet):**
  - Doku konsolidiert nach Blueprint
  - Security Sanitation aktiv (Push Protection an)
  - `.gitignore` erweitert (Artefakte/Secrets)
  - CI grün (Lint, Tests, Security, Secrets)

---

## 9) Nächste Schritte (operativ)
- [ ] `cleanroom/docs-dryrun` Branch erstellen und PR eröffnen  
- [ ] GitHub-Security aktivieren (Secret scanning + Push protection)  
- [ ] CI minimal anschalten (Lint/Test/Secret)  
- [ ] Roadmap N+1: Implementierung der Services (Backoffice) gemäß `rebuild.md`

---

## 10) Quick-Checks (Go/No-Go)
**Go:** Repo sauber, Runbooks vollständig, `.gitignore` aktiv, keine Secrets.  
**No-Go:** Fehlende Backups, offene Security-Funde, unklare Owner/Zeiten für Sanitation.

---

### Anhang A – Minimaler CI-Workflow (Beispiel)
```yaml
name: ci
on:
  pull_request:
  push:
    branches: [ main ]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install ruff
      - run: ruff check .

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt || true
      - run: pytest -q || true

  secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          curl -sSL https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_$(uname -s)_x64.tar.gz | tar -xz
          ./gitleaks detect --no-git --source .
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install bandit
      - run: bandit -q -r . || true
```

---

**Status:** Vorlage ist produktionsfähig, bewusst minimal-invasiv.  
**Owner (empfohlen):** Project Manager (Orchestrierung), Dev Lead (CI), Security Lead (Sanitation).
