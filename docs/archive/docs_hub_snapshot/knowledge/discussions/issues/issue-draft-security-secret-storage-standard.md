# Secret Storage Standard: .secrets + .secretsignore + strict .gitignore policy

Status: CLAUDE_READY
Mode: EXECUTION_ONLY
Labels: [security, secrets, devops, docs]
Milestone: Security / M8

Goal:
Define and enforce one deterministic local secret location and ignore policy so secrets never enter git while remaining easy to use on Windows and Docker Desktop. The standard must be simple enough for new developers to follow without guesswork.

Non-Goals:
- Migrating or rotating existing secrets in this issue.
- Implementing CI/CD secret wiring (handled elsewhere).
- Introducing multiple secret storage options or fallbacks.
- Changing service behavior beyond secret location rules.

Files/Paths to touch:
- .gitignore
- .secretsignore
- .env.example
- docker-compose.yml
- docker-compose.base.yml
- docker-compose.dev.yml
- .gitleaks.toml (new, if used for deny patterns)
- Claire_de_Binare_Docs/docs/content/security/secret-storage-standard.md
- Claire_de_Binare_Docs/docs/content/security/secret-storage-quickstart.md

Ordered Steps:
1. Declare the canonical local secret root as .secrets/ in repo root, matching current compose secret file references.
2. Define the required secret file names (e.g., redis_password, postgres_password, grafana_password) and permitted file extensions.
3. Update .gitignore to ensure .secrets/ and all .env variants remain ignored, while keeping .env.example tracked.
4. Update .secretsignore to allow scanner false positives only where necessary, and keep it minimal.
5. Add deny patterns for common key formats in a single scanner config (e.g., .gitleaks.toml) to block accidental commits.
6. Document the storage standard in the Docs Hub, including where secrets live and which files are allowed.
7. Add a short quickstart that shows how to create .secrets/ and populate required files locally.
8. Define a simple verification checklist: git status clean, scanner passes, no secret paths in tracked files.

Acceptance Criteria:
- .secrets/ and .env* do not appear in git status after local creation.
- .env.example remains tracked and contains only placeholders.
- Scanner allowlist (.secretsignore) remains minimal and documented.
- Deny patterns for common secret formats are configured and reviewed.
- Docs Hub contains a storage standard and a quickstart with Windows-friendly steps.
- Docker compose references still align with the declared secret file names.
- No new secret storage location is introduced outside the canonical .secrets/ path.
- The quickstart includes a basic sanity check for required secret files.

Risks:
- Overly strict deny patterns could block valid commits.
- Under-specified allowlist could allow sensitive false negatives.
- Existing local setups may require migration from legacy locations.
- Windows path quirks could cause confusion if not documented clearly.

Rollback:
- Revert .gitignore/.secretsignore changes to prior behavior.
- Remove the scanner config file if it causes widespread false positives.
- Remove the new Docs Hub pages and keep existing documentation unchanged.
