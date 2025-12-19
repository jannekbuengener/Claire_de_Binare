# enforce-root-baseline.ps1

**Purpose:** Enforce Working Repo root baseline - prevent governance files from polluting execution-only workspace.

## Overview

This script validates that the Working Repo root contains ONLY execution/infrastructure files, preventing governance violations that compromise the "Execution Only" principle.

## Usage

### Validation (Dry Run)
```powershell
.\tools\enforce-root-baseline.ps1 -DryRun
```

### Live Enforcement Check  
```powershell
.\tools\enforce-root-baseline.ps1
```

### Auto-Cleanup (Future)
```powershell
.\tools\enforce-root-baseline.ps1 -AutoCleanup -Force
```

## Allowed in Working Repo Root

### ✅ Infrastructure Files
- `Makefile`, `docker-compose*.yml`, `.dockerignore`
- `requirements*.txt`, `pytest.ini`
- `.gitignore`, `.gitlab-ci.yml`, `.gitleaksignore`
- `.mcp.json`, `mcp-config*.toml`

### ✅ Directories  
- `services/`, `core/`, `infrastructure/`, `tests/`, `tools/`, `scripts/`
- `.git/`, `.vscode/`, `.github/`
- `.ruff_cache/`, `__pycache__/`

### ❌ Governance Violations
- Agent files: `AGENTS.md`, `CLAUDE.md`, `CODEX.md`, etc.
- Documentation: `*_SETUP.md`, `*_GUIDE.md`, `QUICKSTART*.md`
- Knowledge files: `*_AUDIT*.md`, `*_REPORT*.md`
- Session files: `DISCUSSION_*.md`, `*HANDOFF*.md`

## Integration

### In CI/CD Pipeline
```yaml
validate-baseline:
  script:
    - pwsh tools/enforce-root-baseline.ps1
```

### In Makefile
```makefile
baseline-check:
	@pwsh tools/enforce-root-baseline.ps1 -DryRun

baseline-enforce:
	@pwsh tools/enforce-root-baseline.ps1
```

## Exit Codes

- `0` → Root baseline CLEAN (all files are execution/infrastructure compliant)
- `1` → Governance violations detected (requires manual action)

## Governance Rationale

**Canon Rule:** Working Repo = Execution Only  
**Docs Hub:** Canon, Knowledge, Governance  

This script enforces the strict separation and prevents "drift" back to mixed governance/execution.

## Migration Suggestions

When violations are found, the script suggests canonical locations:
- Agent files → Workspace `/agents/roles/`
- Setup guides → Docs Hub `/agents/setup/`  
- Knowledge → Docs Hub `/knowledge/`
- Sessions → Docs Hub `/_legacy_quarantine/sessions/`

---

**Replaces:** `sync-agents.ps1` (obsolete - violated governance rules)  
**Implements:** Root baseline enforcement for governance compliance