# Session 38 — Manual-Approval-Queue: Dependency-Bumps

**Datum:** 2026-04-07
**Scope:** 5 Dependabot-PRs aus der Manual-Approval-Queue

---

## Ziel

Manual-Approval-Queue abarbeiten: alle 5 Dependency-Bumps auf current main bringen, Breaking-Change-Risiko bewerten, mergebar machen.

---

## PRs und Befunde

- **#1115** — `tabulate` 0.9.0 → 0.10.0 (`requirements-dev.txt`)
  - Einzige Nutzung: `infrastructure/scripts/query_analytics.py` mit Standard-API (`headers="keys"`, `tablefmt="grid"`, `floatfmt`)
  - Breaking Change (PRESERVE_STERILITY global → Funktion) nicht genutzt
  - Risiko: null
  - Aktion: `manual-approval` Label, @dependabot rebase, auto-merge gesetzt
  - Status: **wartet auf CODEOWNER-Approval**

- **#1367** — `ruff` 0.15.2 → 0.15.8 (`requirements-dev.txt`)
  - Config: `select = ["E", "F"]`, kein `preview = true`
  - Alle neuen Regeln (RUF050/072/073): Preview-Only + nicht in `select` → inaktiv
  - CI-Nutzung: `ruff check .` in `ci.yml`, bereits grün mit 0.15.8
  - Risiko: null
  - Aktion: `manual-approval` Label, @dependabot rebase, auto-merge gesetzt
  - Status: **wartet auf CODEOWNER-Approval**

- **#1147** — `black` 26.1.0 → 26.3.1 (`requirements-dev.txt`)
  - `ci.yaml`-Pfad mit `black==23.12.1`: Legacy-Pipeline, kein PR-Trigger, kein Blocker
  - Canonical `ci.yml`: `black --config pyproject.toml --check`, bereits grün
  - Config: `line-length=88`, `py312`, kein exotisches Setting
  - Risiko: null
  - Aktion: `manual-approval` Label, @dependabot rebase, auto-merge gesetzt
  - Status: **wartet auf CODEOWNER-Approval**

- **#1179** — `pyyaml` 6.0.2 → 6.0.3 (`requirements-dev.txt`)
  - Alle Nutzungsstellen: `safe_load`, `dump`, `safe_load_all` — Standard-API
  - 6.0.3: nur Python-3.14/free-threading-Support, keine API-Änderungen
  - Risiko: null
  - Aktion: `manual-approval` Label, @dependabot rebase, auto-merge gesetzt
  - Status: **wartet auf CODEOWNER-Approval**

- **#1365** — `pytest-cov` 4.1.0 → 7.1.0 (`requirements-dev.txt`)
  - Breaking Change (subprocess measurement entfernt): kein `.coveragerc`, kein `[tool.coverage]`, kein `patch=subprocess`
  - Canonical `ci.yml`: `pytest -q` ohne `--cov` — pytest-cov im Gate gar nicht aktiv
  - e2e-Workflows: `--no-cov` explizit gesetzt
  - Risiko: null trotz großem Versionssprung
  - Aktion: `manual-approval` Label, @dependabot rebase, auto-merge gesetzt, CODEOWNER approved
  - **Status: MERGED — 4eec57ab (`#1365`)**

---

## Merge-Ergebnis

- Gemergt: PR #1365 — squash-SHA `4eec57ab`
- Offen (auto-merge aktiv, CODEOWNER-Approval ausstehend): #1115, #1367, #1147, #1179

---

## Restunsicherheiten

- PRs #1115/#1367/#1147/#1179 warten auf CODEOWNER-Approval — kein technischer Blocker, rein prozessual
