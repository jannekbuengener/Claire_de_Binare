# Secret Inventory & Classification (Repo + Runtime)

Status: CLAUDE_READY
Mode: EXECUTION_ONLY
Labels: [security, secrets, docs]
Milestone: Security / M8

Goal:
Create a single, canonical inventory of every secret source used by the repo, runtime containers, and CI, with a clear classification and ownership mapping.

Non-Goals:
- Removing or rotating secrets in this issue.
- Adding new secret storage tooling or providers.
- Changing Docker compose behavior or service startup logic.
- Implementing scanners beyond documenting what to scan.

Files/Paths to touch:
- SECURITY_ISSUES.md
- .env.example
- .secretsignore
- docker-compose.yml
- docker-compose.base.yml
- docker-compose.dev.yml
- core/domain/secrets.py
- services/*/config.py
- Claire_de_Binare_Docs/docs/content/security/secret-inventory.md
- Claire_de_Binare_Docs/data/secret-inventory.yaml

Ordered Steps:
1. Scan the working repo for .env, .env.*, and any files matching secret patterns (tokens, keys, passwords) and record findings without values.
2. Inspect Docker compose files for env_file usage, secrets declarations, and any inline environment variables that reference secret material.
3. Review service configs and core/domain/secrets.py to list every runtime secret name and its consumer service.
4. Review CI definitions (.gitlab-ci.yml and .github/workflows/*) for required secret variable names and any secret-consuming jobs.
5. Inspect local secret stores that may exist (.secrets/ in repo root and Workspaces/.cdb_local/.secrets) to classify location and scope.
6. Normalize naming: map all variants to a single canonical secret name and note source of truth and rotation owner.
7. Produce secret-inventory.md describing the classification model (runtime vs CI vs local), owners, and allowed storage locations.
8. Produce secret-inventory.yaml with a machine-readable list for tooling (name, scope, consumer, source, owner, rotation cadence).

Acceptance Criteria:
- A single canonical inventory doc exists in the Docs Hub with no secret values.
- A machine-readable inventory file exists with the same canonical names and scopes.
- Every secret referenced by docker-compose or service config appears in the inventory.
- Every CI secret variable referenced in pipelines is listed with scope and owner.
- Local-only stores are documented as locations, not copied into the repo.
- Classification clearly distinguishes runtime, CI/CD, and local developer secrets.
- Inventory includes rotation ownership and expected cadence per secret class.

Risks:
- Missing non-obvious secrets embedded in docs or scripts.
- Over-including false positives that create noise and maintenance overhead.
- Revealing sensitive metadata if descriptions are too detailed.
- Inventory drift if not tied to subsequent enforcement work.

Rollback:
- Revert the new inventory files from the Docs Hub.
- Remove any references added to SECURITY_ISSUES.md if scoped incorrectly.
- Leave the repository code and configuration unchanged.
