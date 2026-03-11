# GOVERNANCE_ALIGNMENT_AUDIT_20251216

Date: 2025-12-19
Scope: Docs Hub governance alignment after "Buero" merge (limited to observable files)

## Sources checked
- BUERO_FILES_REVIEW.md (existing report)
- Docs Hub file inventory (current workspace)
- scripts/README_TRANSLATION_INTEGRATION.md (present)

## Observations

### Present
- scripts/README_TRANSLATION_INTEGRATION.md exists and describes translate-issues workflow.

### Missing from Docs Hub (cannot audit)
The following files referenced in BUERO_FILES_REVIEW.md were not found in Docs Hub:
- agents/charters/charter-template.yaml
- agents/roles/AGENTS.md
- agents/roles/CLAUDE.md
- agents/roles/CODEX.md
- agents/roles/COPILOT.md
- agents/roles/GEMINI.md
- agents/roles/roles.yaml
- knowledge/operating_rules/OPERATING_BASELINE.md
- knowledge/operating_rules/INCIDENT_LOOP.md

The workflow file referenced in scripts/README_TRANSLATION_INTEGRATION.md was not found in Docs Hub:
- .github/workflows/translate-issues.yml

## Findings

### MUST
- Provide canonical paths (or confirm removal) for the missing files above so governance alignment can be verified.

### SHOULD
- If translate-issues workflow lives outside Docs Hub, document its canonical location and ownership.

### NICE
- Add frontmatter to scripts/README_TRANSLATION_INTEGRATION.md if governance requires it for classification.

## Notes
- This audit is incomplete due to missing source files.
- No policy decisions made.
