# EPIC_OVERVIEW: Security: Secrets Governance + Secret Container

Status: CLAUDE_READY
Mode: EXECUTION_ONLY
Labels: [security, secrets, docs]
Milestone: Security / M8

Goal:
Provide a single overview for the six security/secrets issues, their execution order, and the deterministic command sequence to run after each merge.

Issues (ordered):
1. Secret Inventory & Classification (Repo + Runtime) - issue-draft-security-secret-inventory-classification.md
2. Secret Storage Standard: .secrets + .secretsignore + strict .gitignore policy - issue-draft-security-secret-storage-standard.md
3. Secrets Sidecar Container (Docker) - issue-draft-security-secrets-sidecar-container.md
4. Runtime Secret Injection Contract - issue-draft-security-runtime-secret-injection-contract.md
5. CI/CD Integration: GitHub/GitLab Secret Wiring - issue-draft-security-ci-cd-secret-wiring.md
6. Secret Rotation & Incident Runbook - issue-draft-security-secret-rotation-incident-runbook.md

Post-merge command sequence (run from repo root after each issue is merged):
1. python scripts/run_docs_sync.py --dry-run --relocator-report tools/_relocator_report.json --tools-report tools/_tools_report.json
2. python scripts/run_docs_sync.py --relocator-report tools/_relocator_report.json --tools-report tools/_tools_report.json
3. git status -sb

Notes:
- If the dry-run fails, stop and fix baseline issues before proceeding.
- Do not add implementation outside the scope of the merged issue.
