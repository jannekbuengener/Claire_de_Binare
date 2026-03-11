# Secrets Sidecar Container (Docker)

Status: CLAUDE_READY
Mode: EXECUTION_ONLY
Labels: [security, secrets, devops]
Milestone: Security / M8

Goal:
Introduce a dedicated secrets sidecar container that loads from local .secrets or CI-provided secrets and exposes them to services only via controlled, read-only mechanisms.

Non-Goals:
- Adopting external cloud secret managers or vault services.
- Storing plaintext secrets in any docker-compose file.
- Changing business logic or trading behavior in services.
- Supporting multiple secret delivery paths beyond the chosen sidecar approach.

Files/Paths to touch:
- docker-compose.yml
- docker-compose.base.yml
- docker-compose.dev.yml
- docker-compose.secrets.yml (new)
- .secrets/ (local, gitignored)
- core/domain/secrets.py
- Claire_de_Binare_Docs/docs/content/security/secrets-sidecar.md

Ordered Steps:
1. Define a single compose fragment (docker-compose.secrets.yml) that runs a secrets sidecar container on all stacks.
2. Mount .secrets/ into the sidecar, validate presence of required files, and expose a read-only volume for /run/secrets.
3. Update compose files to consume secrets from the shared read-only volume without embedding plaintext values.
4. Ensure Windows + Docker Desktop paths work for mounts and that the compose merge order is documented.
5. Standardize secret file names to match current get_secret usage and compose secret names.
6. Add a minimal healthcheck to the sidecar so services wait on secret availability deterministically.
7. Update documentation with a simple startup flow using the compose fragment and required local files.
8. Provide a fallback for CI: sidecar reads secrets from CI-provided environment variables and writes into the shared volume at startup.

Acceptance Criteria:
- docker-compose up works with an empty repo and starts only once .secrets is populated.
- No plaintext secret values appear in any compose file or committed config.
- Services read secrets from /run/secrets via the shared read-only volume.
- Sidecar has a clear, deterministic failure when required secrets are missing.
- The approach works on Windows with Docker Desktop and documented command order.
- The sidecar design does not require changes to service code beyond secret access paths.
- Docs Hub includes a single authoritative setup page for the sidecar flow.

Risks:
- Sidecar startup ordering could cause flakey service boots if not gated.
- Windows file permission semantics could prevent read-only mount behavior.
- CI environments might lack a consistent path for secrets injection.
- Volume sharing could be misconfigured, leading to missing secrets at runtime.

Rollback:
- Revert compose changes to prior secret definitions and remove the sidecar fragment.
- Remove sidecar documentation and keep existing local secret handling.
- Delete any new sidecar-specific scripts or configs if added.
