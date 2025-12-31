# Documentation Moved to Docs Hub

**Date**: 2025-12-27
**Issue**: #143
**Decision**: Option A (strict separation)

## Rationale

Working Repo contains **executable code only**. All documentation has been migrated to the Docs Hub for:
- Single Source of Truth
- Minimal drift between docs and code
- Clear ownership and maintenance

## Canonical Documentation Location

**Docs Hub**: `D:\Dev\Workspaces\Repos\Claire_de_Binare_Docs`

## Migrated Files

### Operations & Runbooks
- **DOCKER_STACK_RUNBOOK.md** → `knowledge/operations/DOCKER_STACK_RUNBOOK.md`

### Planning & Roadmaps
- **M7_SKELETON.md** → `knowledge/tasklists/M7_SKELETON.md`

### Security & Compliance
- **DOCKER_HARDENING_REPORT.md** → `knowledge/security/DOCKER_HARDENING_REPORT.md`
- **Docker Container & Image Vulnerability Scan Report.md** → `knowledge/security/DOCKER_VULNERABILITY_SCAN_2025-12-23.md`
- **HARDENING_VERIFICATION.md** → `knowledge/compliance/HARDENING_VERIFICATION.md`

### Architecture & Analysis
- **LEGACY_ANALYSIS.md** → `knowledge/architecture/LEGACY_ANALYSIS.md`
- **LOGS_CONCEPT_ANALYSIS.md** → `knowledge/decisions/LOGS_CONCEPT_ANALYSIS.md`

### Patterns & Templates
- **FUTURE_SERVICES.md** (extracted) → `knowledge/patterns/FUTURE_SERVICES.md`
- **SERVICE_STUB_PATTERN** (extracted) → `knowledge/patterns/SERVICE_STUB_PATTERN.md`

## Quick Access

```powershell
# Open Docs Hub
cd "D:\Dev\Workspaces\Repos\Claire_de_Binare_Docs"

# View operations runbook
cat knowledge/operations/DOCKER_STACK_RUNBOOK.md

# View milestone planning
cat knowledge/tasklists/M7_SKELETON.md

# View security reports
ls knowledge/security/
ls knowledge/compliance/
```

## Related

- **Docs Hub PR**: https://github.com/jannekbuengener/Claire_de_Binare_Docs/pull/16
- **Working Repo PR**: (this PR)
- **Issue**: #143

---

**Working Repo = Code Only**
**Docs Hub = Documentation, Knowledge, Governance**
