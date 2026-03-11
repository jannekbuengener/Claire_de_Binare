# Runtime Secret Injection Contract

Status: CLAUDE_READY
Mode: EXECUTION_ONLY
Labels: [security, secrets, devops]
Milestone: Security / M8

Goal:
Define a single, explicit contract for how services obtain secrets at runtime and enforce fail-fast behavior when required secrets are missing. The contract must be deterministic across local, CI, and production execution modes.

Non-Goals:
- Implementing new features unrelated to secret handling.
- Introducing multiple secret resolution strategies beyond the contract.
- Changing service business logic or data pipelines.
- Replacing Docker secrets with external providers.
- Changing deployment topology or container orchestration beyond secret wiring.

Files/Paths to touch:
- core/domain/secrets.py
- services/signal/config.py
- services/risk/config.py
- services/db_writer/db_writer.py
- services/execution/service.py
- docker-compose.yml
- Claire_de_Binare_Docs/docs/content/security/runtime-secret-contract.md

Ordered Steps:
1. Document a single runtime secret contract: required secrets, optional secrets, defaults, and failure modes.
2. Align secret names with docker-compose secrets and get_secret usage so naming is consistent across services and matches .env.example keys.
3. Update service configuration code to validate required secrets at startup and fail fast with clear errors.
4. Standardize error messaging so operators know which secret is missing and where to place it.
5. Ensure no fallback reads from committed files or .env when a secret is required, and document any CI-only fallback explicitly.
6. Add a brief developer checklist in the contract doc for local runs and container runs.
7. Update any existing runtime docs that reference old secret handling patterns.
8. Add a lightweight manual test procedure (documented only) to verify missing secret behavior.

Acceptance Criteria:
- A single contract document exists in the Docs Hub with required and optional secret lists.
- Each service clearly fails fast when a required secret is missing.
- Error messages identify the missing secret name and expected source.
- Services use get_secret consistently with no hidden or inconsistent fallbacks.
- docker-compose secrets and runtime contract names match exactly.
- Docs include a concise verification checklist for local and CI runs.
- No secret values or example real credentials appear in docs or code.
- Any allowed CI-only fallback is documented with scope and limitations.

Risks:
- Tightening validation could break existing local runs until secrets are provided.
- Inconsistent naming may cause confusion or misconfiguration.
- Services might exit too early without clear operator guidance.
- Hidden legacy paths could still expose secret values if not removed.
- CI jobs might fail if required secret naming is not synchronized.

Rollback:
- Revert service validation changes to previous permissive behavior.
- Remove the contract document if it conflicts with existing workflows.
- Restore prior config defaults if required for emergency operation.
