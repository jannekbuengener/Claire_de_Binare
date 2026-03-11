# Workspace Layout — Canonical Structure (verbindlich)

**Status:** Canonical (seit Dec 2025)
**Owner:** Orchestrator / File-Ops Agent
**Last Updated:** 2025-12-27

---

## Zielbild (Definition of Done)

Die lokale Arbeitsfläche ist **minimalistisch** strukturiert:

```
D:\Dev\Workspaces\Repos\
├── Claire_de_Binare\           # Working Repo (Code/Execution only)
└── Claire_de_Binare_Docs\      # Docs Hub (Single Source of Truth)
```

**Das war's.** Keine weiteren Ordner, Dateien oder Git-Repos auf dieser Ebene.

---

## Rationale

### Vorher (Chaos)

Workspaces Root war:
- ein eigenes Git-Repository
- mit `.cdb_local/`, `.claude/`, `.vscode/`, `.github/`, `LICENSE`, `README.md`, `.coverage`
- nested repos wurden als untracked files behandelt
- Secrets, Tooling, Doku und Code gemischt
- keine klare Trennung von "was gehört wohin"

**Problem:** Drift, Duplizierung, Secrets-Risiko, keine klare Owner-Struktur.

### Nachher (Clean)

1. **Workspaces Root ist kein Repo** — nur ein Container für die 2 Repos
2. **Docs Hub (`Claire_de_Binare_Docs/`)** ist die **Single Source of Truth** für:
   - Governance (`agents/`, `governance/`)
   - Knowledge (`knowledge/`)
   - Agent Definitions (`agents/CLAUDE.md`, etc.)
   - GitHub Actions für Gemini (`.github/workflows/`)
3. **Working Repo (`Claire_de_Binare/`)** enthält **nur Code**:
   - Python Services
   - Dockerfiles
   - Tests
   - CI/CD für Code-Builds
4. **Machine-Local State** lebt in `.local/` im Docs Hub (untracked):
   - `.local/workspaces-root/.cdb_local/` (old tooling)
   - `.local/workspaces-root/.claude/` (Claude CLI config)
   - `.local/workspaces-root/.vscode/` (VSCode workspace settings)

---

## Pfade (Canonical)

### 1. Workspaces Root (Container nur)
```
D:\Dev\Workspaces\Repos\
```
**Regel:** Enthält NUR die 2 Repos. Nichts anderes.

### 2. Docs Hub (Single Source of Truth)
```
D:\Dev\Workspaces\Repos\Claire_de_Binare_Docs\
```

**Struktur:**
```
Claire_de_Binare_Docs/
├── .github/                    # GitHub Actions (Gemini workflows)
├── .local/                     # Machine-local state (UNTRACKED)
│   ├── README.md               # Only tracked file in .local/
│   └── workspaces-root/        # Artifacts from consolidation
│       ├── .cdb_local/         # Old tooling state
│       ├── .claude/            # Claude CLI config
│       ├── .vscode/            # VSCode settings
│       └── legacy/             # LICENSE, README, .gitignore from Workspaces Root
├── agents/                     # Agent definitions (CANONICAL)
│   ├── AGENTS.md               # Registry (authoritative)
│   ├── CLAUDE.md               # Claude role definition
│   ├── CODEX.md                # Codex role definition
│   ├── COPILOT.md              # Copilot role definition
│   └── GEMINI.md               # Gemini role definition
├── knowledge/                  # Knowledge base
│   ├── operations/             # Operational docs (like this file)
│   ├── reviews/                # Review artifacts
│   └── ...
└── governance/                 # Governance artifacts
```

### 3. Working Repo (Code Execution)
```
D:\Dev\Workspaces\Repos\Claire_de_Binare\
```

**Struktur:**
```
Claire_de_Binare/
├── AGENTS.md                   # POINTER to Docs Hub canonical (NOT authoritative)
├── services/                   # Python microservices
├── tests/                      # Unit/Integration/E2E tests
├── Makefile                    # Build commands
└── docker-compose.yml          # Local dev environment
```

**Regel:** Docs/Markdown/Agent-Definitionen gehören NICHT hierher (außer Pointer).

---

## "Was gehört wohin" Mapping

| Artifact Type                | Location                                      | Tracked? |
|------------------------------|-----------------------------------------------|----------|
| Agent Definitions            | `Claire_de_Binare_Docs/agents/`               | ✅ Yes   |
| Governance Docs              | `Claire_de_Binare_Docs/governance/`           | ✅ Yes   |
| Knowledge Articles           | `Claire_de_Binare_Docs/knowledge/`            | ✅ Yes   |
| GitHub Actions (Gemini)      | `Claire_de_Binare_Docs/.github/workflows/`    | ✅ Yes   |
| Code (Services, Tests)       | `Claire_de_Binare/services/`, `tests/`        | ✅ Yes   |
| Tooling Config (.cdb_local)  | `Claire_de_Binare_Docs/.local/workspaces-root/` | ❌ No  |
| IDE Settings (.vscode)       | `Claire_de_Binare_Docs/.local/workspaces-root/` | ❌ No  |
| Secrets (.env, passwords)    | `Claire_de_Binare_Docs/.local/` (NEVER commit) | ❌ No  |
| Ephemeral (.coverage, logs)  | Deleted or `.local/` if needed                | ❌ No  |

---

## Migration History

**Date:** 2025-12-27
**Task:** Workspaces Root Consolidation (ORCHESTRATION_TASK_144)

### What Changed

1. **Destroyed Workspaces Root `.git/` repository** (was creating a 3rd nested repo)
2. **Moved all artifacts:**
   - `.cdb_local/`, `.claude/`, `.vscode/` → `Claire_de_Binare_Docs/.local/workspaces-root/`
   - `.github/` → `Claire_de_Binare_Docs/.github/` (tracked)
   - `LICENSE`, `README.md`, `.gitignore` → `.local/workspaces-root/legacy/`
3. **Deleted ephemeral files:** `.coverage`
4. **Moved canonical AGENTS.md:**
   - From: `Claire_de_Binare/AGENTS.md`
   - To: `Claire_de_Binare_Docs/agents/AGENTS.md`
   - Working Repo now has a pointer file
5. **Updated all path references** in:
   - `agents/AGENTS.md`
   - `agents/CLAUDE.md`
   - `agents/roles/CODEX.md`
   - `agents/COPILOT.md`
   - `agents/GEMINI.md`

### Backup Location

Before consolidation, full backup was created:
```
D:\Dev\Workspaces\Repos\.BACKUP_BEFORE_CONSOLIDATION\
```

---

## Do's & Don'ts

### ✅ Do's
- Keep Workspaces Root clean (only 2 repos)
- Store docs/knowledge in Docs Hub
- Store code in Working Repo
- Store machine-local state in `.local/` (untracked)
- Use absolute paths in documentation
- Update this file when structure changes

### ❌ Don'ts
- Create new Git repos in Workspaces Root
- Commit secrets, credentials, or API keys
- Duplicate agent definitions across repos
- Store docs in Working Repo (except pointers)
- Commit anything in `.local/` (except `.local/README.md`)
- Reference old paths (`.cdb_local/agents/roles/`)

---

## Verification Commands

### Check Workspaces Root is clean
```powershell
cd D:\Dev\Workspaces\Repos
Get-ChildItem -Force | Where-Object { $_.Name -notin @('Claire_de_Binare','Claire_de_Binare_Docs','.BACKUP_BEFORE_CONSOLIDATION','zusatz.txt') }
```
**Expected:** Empty (or only backup/temp files)

### Check .local is not tracked
```powershell
cd D:\Dev\Workspaces\Repos\Claire_de_Binare_Docs
git status --porcelain | Select-String "\.local"
```
**Expected:** Only `.local/README.md` or nothing

### Check path references are updated
```powershell
cd D:\Dev\Workspaces\Repos\Claire_de_Binare_Docs
rg -n "Workspaces\\\.cdb_local" -S
```
**Expected:** No results (old paths removed)

---

## Ownership & Maintenance

- **Orchestrator Agent** coordinates multi-phase consolidations
- **File-Ops Agent** executes moves/deletes
- **Git-Ops Agent** handles .gitignore, commits, PRs
- **Docs-Consolidation Agent** merges duplicates, updates paths
- **Validation Agent** runs verification commands

This document is **living** and should be updated whenever workspace structure changes.

---

## References

- `agents/AGENTS.md` - Agent registry and governance
- `.local/README.md` - Machine-local state documentation
- `knowledge/reviews/DOCS_HUB_CONSOLIDATION_REVIEW.md` - Consolidation review
