# Branch Protection Strategy

**Status:** ⚠️ BLOCKED (GitHub Free Tier Limitation)
**Issue:** #353
**Created:** 2025-12-30
**Author:** Claude (Session Lead)

---

## Executive Summary

Branch Protection für `main` erfordert **GitHub Pro** ($4/Monat) oder **Public Repository**.

**Aktuelle Situation:**
- Repository: `jannekbuengener/Claire_de_Binare` (private)
- GitHub Plan: Free Tier
- Branch Protection: ❌ Nicht verfügbar (HTTP 403)
- Repository Rulesets: ❌ Nicht verfügbar (HTTP 403)

**Optionen:**
1. GitHub Pro erwerben → Vollständiger Branch Protection
2. Repository public machen → Branch Protection kostenlos
3. Free-Tier-Workarounds → Teilweise Governance (siehe unten)

---

## Option 1: GitHub Pro Branch Protection (Ideal)

**Kosten:** ~$4/Monat pro User
**Verfügbare Features:**
- Required Pull Request Reviews
- Required Status Checks
- Enforce Admins
- Restrict Push Access
- Force Push Protection
- Commit Signing Requirements

### Aktivierung (wenn GitHub Pro verfügbar)

```bash
# Branch Protection via gh CLI
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection -X PUT \
  --input - <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["CI/CD Pipeline", "Delivery Gate", "E2E Smoke"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
```

**Required Status Checks (P0):**
- `CI/CD Pipeline` — Unit + Integration Tests
- `Delivery Gate` — Contract Validation
- `E2E Smoke` — End-to-End Pipeline Test

**Evidence:** Screenshot/Export von Branch Protection Settings

---

## Option 2: Repository Public (Kostenlos)

**Kosten:** $0
**Trade-off:** Code ist öffentlich sichtbar

### Aktivierung

```bash
# Repository auf Public setzen (Achtung: Irreversibel ohne Support)
gh repo edit jannekbuengener/Claire_de_Binare --visibility public

# Branch Protection aktivieren (siehe Option 1 Commands)
```

**Risiko-Bewertung:**
- ✅ Kein Business-Secret-Code (Open-Source-Trading-Bot)
- ⚠️ Secrets/Keys in `.env` → müssen aus History entfernt werden
- ⚠️ Issue-Tracker wird öffentlich

---

## Option 3: Free-Tier-Workarounds (Teilweise Governance)

Wenn GitHub Pro/Public nicht möglich sind, gibt es **3 Workarounds**:

### 3a) CODEOWNERS Datei (Free Tier ✅)

Erzwingt Reviews, aber **nicht** PRs.

**Datei:** `.github/CODEOWNERS`

```bash
# Global Owner (alle Dateien)
* @jannekbuengener

# Critical Files (explizit)
/.github/workflows/* @jannekbuengener
/infrastructure/compose/* @jannekbuengener
/services/*/service.py @jannekbuengener
/docs/governance/* @jannekbuengener
```

**Limitation:** User kann immer noch direkt auf `main` pushen (aber GitHub UI zeigt "Review required")

---

### 3b) GitHub Actions Workflow (Free Tier ✅)

Simuliert Branch Protection via CI/CD.

**Datei:** `.github/workflows/branch_protection.yml`

```yaml
name: Branch Protection (Workflow-based)

on:
  push:
    branches:
      - main

jobs:
  block-direct-push:
    runs-on: ubuntu-latest
    steps:
      - name: Check if push is from PR merge
        run: |
          if [[ "${{ github.event.head_commit.message }}" != *"Merge pull request"* ]]; then
            echo "❌ ERROR: Direct push to main detected!"
            echo "Branch Protection Policy: PRs only on main"
            echo "Use 'gh pr create' instead of direct push"
            exit 1
          fi

      - name: Evidence
        run: |
          echo "✅ Push originated from PR merge"
          echo "Commit: ${{ github.sha }}"
          echo "Author: ${{ github.actor }}"
```

**Limitation:** Workflow läuft **nach** dem Push (Post-Merge-Blocker, aber besser als nichts)

---

### 3c) Pre-Push Git Hook (Lokal)

Blockiert direkte Pushes **vor** dem Upload.

**Datei:** `.git/hooks/pre-push` (lokal, nicht in Repo)

```bash
#!/bin/bash
# Pre-Push Hook: Block direct pushes to main

current_branch=$(git symbolic-ref --short HEAD)

if [ "$current_branch" = "main" ]; then
  echo "❌ ERROR: Direct push to main is blocked!"
  echo "Branch Protection Policy: Use PRs only"
  echo ""
  echo "Workflow:"
  echo "  1. Create feature branch: gh issue develop <issue-number> -c"
  echo "  2. Make changes + commit"
  echo "  3. Push branch: git push origin <branch-name>"
  echo "  4. Create PR: gh pr create"
  echo ""
  echo "Emergency Bypass (nur für kritische Fixes):"
  echo "  git commit -m \"[EMERGENCY] Fix critical issue\""
  exit 1
fi
```

**Aktivierung:**

```bash
chmod +x .git/hooks/pre-push
```

**PowerShell (Windows):**

```powershell
# Pre-Push Hook für Windows
$hookPath = ".git\hooks\pre-push"
$hookContent = @"
#!/bin/bash
current_branch=`$(git symbolic-ref --short HEAD)
if [ "`$current_branch" = "main" ]; then
  echo "❌ ERROR: Direct push to main is blocked!"
  echo "Branch Protection Policy: Use PRs only"
  exit 1
fi
"@
Set-Content -Path $hookPath -Value $hookContent -Encoding UTF8
```

**Limitation:** Nur lokal (jeder Contributor muss Hook installieren)

---

## Recommended Approach (Current State)

**Short-Term (Today):**
1. ✅ Erstelle CODEOWNERS Datei (#3a)
2. ✅ Erstelle Workflow-based Protection (#3b)
3. ✅ Dokumentiere Pre-Push Hook (#3c)
4. ✅ Issue #353 als "PARTIAL" markieren (Workarounds aktiv, echter Branch Protection blockiert)

**Long-Term (M8/M9 vor Production):**
- 🎯 GitHub Pro erwerben ($4/Monat)
- 🎯 Echte Branch Protection aktivieren
- 🎯 Required Status Checks erzwingen

---

## Evidence

**GitHub API Response (2025-12-30):**

```
$ gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection
{
  "message": "Upgrade to GitHub Pro or make this repository public to enable this feature.",
  "documentation_url": "https://docs.github.com/rest/branches/branch-protection#get-branch-protection",
  "status": "403"
}
```

**Repository Status:**
- Visibility: Private
- GitHub Plan: Free
- Branch Protection Available: ❌ No
- Repository Rulesets Available: ❌ No

---

## Action Items

### Immediate (Issue #353)

- [x] Dokumentation erstellt (`docs/governance/branch_protection.md`)
- [ ] CODEOWNERS Datei erstellen (`.github/CODEOWNERS`)
- [ ] Workflow-based Protection (`branch_protection.yml`)
- [ ] Pre-Push Hook dokumentieren (README Section)
- [ ] Issue #353 als "PARTIAL" committen + PR

### Future (M8/M9)

- [ ] GitHub Pro Plan evaluieren
- [ ] Branch Protection aktivieren (wenn Pro verfügbar)
- [ ] Required Status Checks konfigurieren
- [ ] Admin Bypass Policy dokumentieren

---

## References

- GitHub Docs: [Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- GitHub Pricing: [Pro Plan Features](https://github.com/pricing)
- Issue: #353
